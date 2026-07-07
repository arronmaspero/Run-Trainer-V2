import json
from datetime import datetime, date, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
from src.config import settings
from src.models.plan import TrainingPlan, TrainingSession

# Define the structured output schema for individual training sessions
class SessionResponseSchema(BaseModel):
    date: str = Field(description="The date of the session in YYYY-MM-DD format")
    type: str = Field(description="The type of the session (Easy, Recovery, Intervals, Tempo, Long Run, Strength, Rest)")
    name: str = Field(description="Short title of the workout session")
    description: str = Field(description="Detailed overview of the workout steps, warm-up, sets, reps, and recovery jog details")
    duration_minutes: int = Field(description="Total estimated duration in minutes")
    distance_miles: float = Field(description="Planned distance in miles, 0.0 if not applicable (e.g. Rest, Strength)")
    warm_up: List[str] = Field(default=[], description="Warm-up instruction steps as a list of strings, e.g. ['Run 1.5 miles easy.']. Empty list if none.")
    main_set: List[str] = Field(default=[], description="Main workout set instruction steps as a list of strings, e.g. ['Run 2.0 miles at tempo pace.']. Empty list if none.")
    cool_down: List[str] = Field(default=[], description="Cool-down instruction steps as a list of strings, e.g. ['Run 1.5 miles easy.']. Empty list if none.")
    target_pace_range: str = Field(description="Pace range per mile, e.g. 7:25-7:40, 9:00-10:00, or 'N/A'")
    target_hr_zone: str = Field(description="Target Heart Rate zone, e.g. Zone 2, Zone 4, or 'N/A'")
    target_rpe: int = Field(description="Rating of Perceived Exertion (1 to 10)")
    garmin_instructions_text: str = Field(description="Step-by-step Garmin Connect manual setup steps")

# Define the structured output schema for the entire training plan
class PlanResponseSchema(BaseModel):
    weeks_count: int = Field(description="Total weeks in the training plan")
    total_mileage: float = Field(description="Total cumulative plan mileage")
    sessions: List[SessionResponseSchema] = Field(description="Complete chronological list of daily sessions")

# Define the structured output schema for plan updates
class PlanUpdateResponseSchema(BaseModel):
    explanation: str = Field(description="A brief explanation of how the training plan has been adapted and what changes were made (2-3 sentences)")
    sessions: List[SessionResponseSchema] = Field(description="The updated list of future sessions, starting from today until the end of the plan")

def get_gemini_client():
    if not settings.GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY is not set in environment or config")
    return genai.Client(api_key=settings.GEMINI_API_KEY)

def lookup_race_details(race_name: str, race_date: str) -> str:
    """Lookup race details using Gemini Search Grounding."""
    if not race_name:
        return "No specific race provided."
    
    client = get_gemini_client()
    prompt = (
        f"Search for details on the race '{race_name}' scheduled on or around '{race_date}'. "
        f"Provide a summary of the course terrain, total elevation profile/gain, track surface, "
        f"average temperature/weather in that location, and any unique course characteristics. "
        f"Be concise."
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return response.text
    except Exception as e:
        # Fallback if search fails
        return f"Could not fetch live details for '{race_name}' due to: {str(e)}. Fallback to generic plan constraints."

def generate_ai_training_plan(
    user_id: str,
    race_name: Optional[str],
    race_date: Optional[str],
    race_distance: str,
    target_time: Optional[str],
    weekly_volume: float,
    runs_per_week: int,
    long_run_day: str,
    unavailable_days: str,
    style: str,
    db: Session,
    additional_notes: Optional[str] = None
) -> TrainingPlan:
    # 1. Fetch race details using grounding if applicable
    race_info = ""
    if race_name and race_date:
        race_info = lookup_race_details(race_name, race_date)
        
    # 2. Formulate prompt for Gemini
    start_date = date.today() + timedelta(days=1) # start tomorrow
    
    # Resolve end_date
    if race_date:
        end_date = datetime.strptime(race_date, "%Y-%m-%d").date()
    else:
        # Default 12 week plan if no race date is specified
        end_date = start_date + timedelta(weeks=12)
        
    weeks_count = max(1, int((end_date - start_date).days / 7))
    
    prompt = (
        f"You are a professional, evidence-informed running coach generating a training plan. "
        f"User Details:\n"
        f"- Target Goal: {race_distance} race. Race Name: {race_name or 'N/A'}. Race Date: {end_date.isoformat()}.\n"
        f"- Target Time Goal: {target_time or 'N/A'}\n"
        f"- Current Weekly Running Volume: {weekly_volume} miles\n"
        f"- Target Runs per Week: {runs_per_week} runs\n"
        f"- Preferred Long Run Day: {long_run_day}\n"
        f"- Days Unavailable to Train: {unavailable_days}\n"
        f"- Plan Training Style: {style} (conservative, balanced, ambitious)\n"
        f"- Plan Start Date: {start_date.isoformat()} to End Date: {end_date.isoformat()} ({weeks_count} weeks)\n\n"
        f"Course & Race Grounding Details:\n{race_info}\n\n"
        f"Plan Design Rules:\n"
        f"1. Generate a session for EVERY single day between {start_date.isoformat()} and {end_date.isoformat()}.\n"
        f"2. Rest days should be explicitly set as type='Rest', name='Rest Day', distance_miles=0.0.\n"
        f"3. Do not increase weekly mileage by more than 10% compared to the previous week.\n"
        f"4. Schedule quality runs (Intervals/Tempo) on available days. Never back-to-back hard runs.\n"
        f"5. Ensure long runs are placed on {long_run_day}.\n"
        f"6. Make sure to generate Garmin manual creation steps for each non-rest session.\n"
        f"7. Style must match the selected training style ({style}).\n"
    )

    if additional_notes and additional_notes.strip():
        prompt += f"\nAdditional Athlete Notes (treat these as high-priority constraints):\n{additional_notes.strip()}\n"

    
    client = get_gemini_client()
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PlanResponseSchema
        )
    )
    
    # 3. Parse JSON structured response
    plan_data = PlanResponseSchema.model_validate_json(response.text)
    
    # 4. Save to Database
    # Map distance name to miles float
    distance_lower = race_distance.lower().strip()
    distance_miles = 26.2
    if "half" in distance_lower:
        distance_miles = 13.1
    elif "10k" in distance_lower:
        distance_miles = 6.2
    elif "5k" in distance_lower:
        distance_miles = 3.1
    elif "marathon" in distance_lower:
        distance_miles = 26.2
    else:
        # Try to parse a custom numeric distance from the string
        try:
            import re
            match = re.search(r"([0-9]+(?:\.[0-9]+)?)", distance_lower)
            if match:
                val = float(match.group(1))
                if "km" in distance_lower or "kilometer" in distance_lower:
                    distance_miles = round(val * 0.621371, 2)
                else:
                    distance_miles = val
        except Exception as e:
            distance_miles = 26.2
    
    # Try parsing target time to seconds
    target_time_seconds = None
    if target_time:
        try:
            parts = target_time.split(":")
            if len(parts) == 3:
                target_time_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except:
            pass

    # Create new TrainingPlan record
    db_plan = TrainingPlan(
        user_id=user_id,
        race_name=race_name,
        race_date=end_date,
        race_distance_miles=distance_miles,
        target_time_seconds=target_time_seconds,
        start_date=start_date,
        end_date=end_date,
        style=style,
        status="active"
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    
    # Save training sessions
    for session in plan_data.sessions:
        session_date = datetime.strptime(session.date, "%Y-%m-%d").date()
        db_session = TrainingSession(
            plan_id=db_plan.id,
            date=session_date,
            type=session.type,
            name=session.name,
            description=session.description,
            duration_minutes=session.duration_minutes,
            distance_miles=session.distance_miles,
            warm_up_json=json.dumps(session.warm_up) if session.warm_up else "[]",
            main_set_json=json.dumps(session.main_set) if session.main_set else "[]",
            cool_down_json=json.dumps(session.cool_down) if session.cool_down else "[]",
            target_pace_range=session.target_pace_range,
            target_hr_zone=session.target_hr_zone,
            target_rpe=session.target_rpe,
            garmin_instructions_text=session.garmin_instructions_text,
            status="planned"
        )
        db.add(db_session)
        
    db.commit()
    return db_plan


def preview_plan_update(
    user_id: str,
    difficulty_feedback: str,  # 'easy', 'normal', 'hard'
    user_comments: Optional[str],
    db: Session
) -> PlanUpdateResponseSchema:
    # 1. Fetch active training plan
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == user_id,
        TrainingPlan.status == "active"
    ).first()
    if not plan:
        raise Exception("No active training plan found to update")

    # 2. Fetch all sessions ordered by date
    sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id
    ).order_by(TrainingSession.date).all()

    # 3. Grounding race details if applicable
    race_info = ""
    if plan.race_name and plan.race_date:
        race_info = lookup_race_details(plan.race_name, plan.race_date.isoformat())

    # 4. Partition sessions into past and future
    today_val = date.today()
    past_sessions = []
    future_sessions = []
    
    for s in sessions:
        s_data = {
            "date": s.date.isoformat(),
            "type": s.type,
            "name": s.name,
            "description": s.description,
            "distance_miles": s.distance_miles,
            "duration_minutes": s.duration_minutes,
            "status": s.status
        }
        if s.date < today_val:
            past_sessions.append(s_data)
        else:
            future_sessions.append(s_data)

    # 5. Formulate adaptive coach prompt
    difficulty_instructions = ""
    if difficulty_feedback == "hard":
        difficulty_instructions = (
            "The athlete is STRUGGLING and finding the workouts too hard. "
            "You MUST adapt the remaining plan defensively to prevent injury/burnout:\n"
            "- Reduce weekly cumulative mileage targets for all future weeks by 15-25%.\n"
            "- Scale down future long run distances and reduce intensity of speed/tempo runs.\n"
            "- Prescribe wider, more conservative pace targets and easier heart rate zones."
        )
    elif difficulty_feedback == "easy":
        difficulty_instructions = (
            "The athlete is finding the workouts too EASY and is knocking it out of the park. "
            "You should safely progress the remaining plan to match their higher fitness capacity:\n"
            "- Increase future weekly cumulative mileage targets by 5-10% (do not exceed the 10% week-over-week growth limit from the previous week's base).\n"
            "- Add slightly longer long runs or slightly faster target pace ranges for quality/tempo/long run workouts.\n"
            "- Keep the structure structured and safe."
        )
    else:
        difficulty_instructions = (
            "The athlete is finding the workouts JUST RIGHT and on track. "
            "Keep the existing volume progression trend intact, but adjust sessions to satisfy any specific user requests/comments below."
        )

    comments_instruction = f"User Request Comments:\n\"{user_comments}\"\n" if user_comments else "No specific comments/requests were provided."

    prompt = (
        f"You are a professional, evidence-informed running coach adapting an active training plan.\n"
        f"Today's date is: {today_val.isoformat()}\n"
        f"Plan details:\n"
        f"- Target Goal: {plan.race_distance_miles} miles. Name: {plan.race_name or 'N/A'}. Date: {plan.race_date.isoformat() if plan.race_date else 'N/A'}.\n"
        f"- Style: {plan.style}\n"
        f"- Start Date: {plan.start_date.isoformat()} to End Date: {plan.end_date.isoformat()}\n\n"
        f"Course & Race Grounding Details:\n{race_info}\n\n"
        f"Historical Workouts (Past days - DO NOT modify these, they are already done/locked):\n"
        f"{json.dumps(past_sessions, indent=2)}\n\n"
        f"Current Planned Workouts (Future days - you will recreate/modify these):\n"
        f"{json.dumps(future_sessions, indent=2)}\n\n"
        f"Athlete Feedback:\n"
        f"- Difficulty feedback: {difficulty_feedback} ({difficulty_instructions})\n"
        f"- {comments_instruction}\n\n"
        f"Your Task:\n"
        f"1. Generate the updated list of training sessions for all remaining days from {today_val.isoformat()} to the plan end date {plan.end_date.isoformat()}.\n"
        f"2. You must generate a session for EVERY single day in this future range. Rest days should be explicitly set (type='Rest', name='Rest Day', distance_miles=0.0).\n"
        f"3. Apply the difficulty adaptations (reducing/increasing volume and intensity) and strictly honor any custom request comments (e.g. rescheduling to different days, or formatting changes).\n"
        f"4. Provide a clear, encouraging 2-3 sentence coaching explanation of what you updated and why (e.g., 'I scaled down your Wednesday intervals by 15% to help your legs recover, and shifted your long runs to Saturdays as requested. Keep up the good work!')."
    )

    client = get_gemini_client()
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PlanUpdateResponseSchema
        )
    )

    return PlanUpdateResponseSchema.model_validate_json(response.text)


def apply_plan_update(
    user_id: str,
    difficulty_feedback: str,
    user_comments: Optional[str],
    db: Session
) -> TrainingPlan:
    # 1. Generate updated future sessions first using Gemini
    update_data = preview_plan_update(user_id, difficulty_feedback, user_comments, db)

    # 2. Fetch active training plan
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == user_id,
        TrainingPlan.status == "active"
    ).first()
    if not plan:
        raise Exception("No active training plan found to update")

    today_val = date.today()

    # 3. Fetch old future sessions for change-logging
    old_future_sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id,
        TrainingSession.date >= today_val
    ).order_by(TrainingSession.date).all()

    old_values = [
        {
            "id": s.id,
            "date": s.date.isoformat(),
            "type": s.type,
            "name": s.name,
            "distance_miles": s.distance_miles,
            "status": s.status
        }
        for s in old_future_sessions
    ]

    # 4. Perform database operations inside transaction
    # Delete old future sessions
    db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id,
        TrainingSession.date >= today_val
    ).delete()

    # Insert new future sessions
    new_values = []
    for session in update_data.sessions:
        session_date = datetime.strptime(session.date, "%Y-%m-%d").date()
        db_session = TrainingSession(
            plan_id=plan.id,
            date=session_date,
            type=session.type,
            name=session.name,
            description=session.description,
            duration_minutes=session.duration_minutes,
            distance_miles=session.distance_miles,
            warm_up_json=json.dumps(session.warm_up) if session.warm_up else "[]",
            main_set_json=json.dumps(session.main_set) if session.main_set else "[]",
            cool_down_json=json.dumps(session.cool_down) if session.cool_down else "[]",
            target_pace_range=session.target_pace_range,
            target_hr_zone=session.target_hr_zone,
            target_rpe=session.target_rpe,
            garmin_instructions_text=session.garmin_instructions_text,
            status="planned"
        )
        db.add(db_session)
        new_values.append({
            "date": session.date,
            "type": session.type,
            "name": session.name,
            "distance_miles": session.distance_miles
        })

    # Log the change
    from src.models.changelog import PlanChangeLog
    log_entry = PlanChangeLog(
        plan_id=plan.id,
        user_id=user_id,
        change_type="ai_adaptive_update",
        old_value_json=json.dumps(old_values),
        new_value_json=json.dumps(new_values),
        reason=f"Difficulty: {difficulty_feedback}. Comments: {user_comments or 'None'}. Coach Explanation: {update_data.explanation}",
        is_ai_generated=True,
        is_user_approved=True
    )
    db.add(log_entry)
    
    db.commit()
    return plan
