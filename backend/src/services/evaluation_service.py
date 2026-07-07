import json
from datetime import datetime, date, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
from src.config import settings
from src.models.plan import TrainingPlan, TrainingSession, WeeklyEvaluation
from src.models.activity import Activity
from src.services.strava_service import sync_strava_activities

# Define Pydantic schema for structured output
class MatchedSessionSchema(BaseModel):
    session_id: str = Field(description="The unique database ID of the planned training session")
    strava_activity_id: Optional[str] = Field(None, description="The unique Strava activity ID matched to this session, or null if unmatched")
    status: str = Field(description="The updated status: 'completed' if matched to an activity, 'skipped' if unmatched in the past, or 'planned' if in the future and unmatched")
    explanation: str = Field(description="A brief sentence explaining the matching or why it was skipped/planned")

class WeekEvaluationSchema(BaseModel):
    week_number: int = Field(description="The training week number (1-indexed)")
    commentary: str = Field(description="AI coach's weekly performance commentary and feedback for the athlete (1-3 encouraging sentences)")
    matches: List[MatchedSessionSchema] = Field(description="Matches for the planned sessions in this week")

class PlanEvaluationSchema(BaseModel):
    weeks: List[WeekEvaluationSchema] = Field(description="List of weekly evaluations for all elapsed/current weeks")

def get_gemini_client():
    if not settings.GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY is not set in environment or config")
    return genai.Client(api_key=settings.GEMINI_API_KEY)

def evaluate_plan_progress(user_id: str, db: Session) -> List[WeeklyEvaluation]:
    # 1. Fetch active training plan
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == user_id,
        TrainingPlan.status == "active"
    ).first()
    if not plan:
        raise Exception("No active training plan found to evaluate")

    # 2. Calculate the Monday of Week 1
    # plan.start_date is a datetime.date
    start_date = plan.start_date
    distance_to_monday = start_date.weekday() # 0 = Mon, 6 = Sun
    plan_monday = start_date - timedelta(days=distance_to_monday)

    # 3. Trigger Strava Activity Sync since plan_monday
    # Convert plan_monday to datetime at midnight
    sync_start_dt = datetime.combine(plan_monday, datetime.min.time())
    try:
        sync_strava_activities(user_id, db, start_date=sync_start_dt)
    except Exception as sync_err:
        import logging
        logging.getLogger(__name__).warning(f"Strava sync during evaluation skipped/failed: {sync_err}")

    # 4. Fetch all sessions and activities
    sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id
    ).all()

    activities = db.query(Activity).filter(
        Activity.user_id == user_id,
        Activity.start_date >= sync_start_dt
    ).all()

    # Group sessions and activities by week
    today = date.today()
    elapsed_weeks = max(1, ((today - plan_monday).days // 7) + 1)
    
    # We will pass the data up to the current week
    weeks_data = {}
    for w in range(1, elapsed_weeks + 1):
        weeks_data[w] = {
            "planned": [],
            "completed_strava": []
        }

    # Populate planned sessions
    for s in sessions:
        diff_days = (s.date - plan_monday).days
        w_num = max(1, (diff_days // 7) + 1)
        if w_num in weeks_data:
            weeks_data[w_num]["planned"].append({
                "id": s.id,
                "date": s.date.isoformat(),
                "type": s.type,
                "name": s.name,
                "description": s.description,
                "distance_miles": s.distance_miles,
                "duration_minutes": s.duration_minutes,
                "target_pace_range": s.target_pace_range,
                "target_hr_zone": s.target_hr_zone,
                "status": s.status
            })

    # Populate Strava activities
    for a in activities:
        # a.start_date is a datetime, convert to date to do diff
        act_date = a.start_date.date()
        diff_days = (act_date - plan_monday).days
        w_num = max(1, (diff_days // 7) + 1)
        if w_num in weeks_data:
            weeks_data[w_num]["completed_strava"].append({
                "id": a.id,
                "strava_activity_id": a.strava_activity_id,
                "date": act_date.isoformat(),
                "name": a.name,
                "type": a.type,
                "distance_miles": round(a.distance_miles, 2),
                "moving_time_minutes": round(a.moving_time_seconds / 60.0, 1),
                "average_heart_rate": a.average_heart_rate,
                "average_cadence": a.average_cadence
            })

    # 5. Formulate Prompt
    prompt = (
        f"You are an AI Running Coach evaluating the compliance and performance of the runner's training plan.\n"
        f"Today's date is: {today.isoformat()}\n"
        f"Plan Start Date: {plan.start_date.isoformat()}\n"
        f"Monday of Week 1: {plan_monday.isoformat()}\n\n"
        f"For each week, you are given the planned sessions and the actual Strava activities completed. "
        f"Compare them and output the matching relations and a coaching commentary summarizing their progress.\n\n"
        f"Matching Rules:\n"
        f"1. Match a planned session to an actual activity if the runner completed it. The match does not have to be exactly on the same day or distance, but should match the purpose of the workout (e.g. matching an Easy Run session to an actual easy-paced run, or a Long Run to a longer distance run).\n"
        f"2. Note that the official plan sessions start on the plan start date. However, since the evaluation week starts on Monday of Week 1, the runner might have completed workouts earlier in this week (even before the official plan start date). If an actual run in Week 1 matches the purpose of a Week 1 session, you should match them and mark the session as 'completed', even if the run occurred before the plan's official start date.\n"
        f"3. A planned session in the future (today or later) that the runner has already completed earlier this week should be matched and marked 'completed'.\n"
        f"4. For past planned sessions (before today) that are NOT matched to any activity, mark status='skipped'.\n"
        f"5. For future planned sessions (today and after today) that are NOT matched to any activity, mark status='planned'.\n"
        f"6. For matched sessions, mark status='completed' and link the actual Strava activity ID.\n"
        f"7. Write an encouraging and insightful weekly commentary (1-3 sentences) summarizing how the user did on their training plan for that week.\n\n"
        f"Training Weeks Data:\n"
    )

    for w_num, data_dict in sorted(weeks_data.items()):
        prompt += f"--- Week {w_num} ---\n"
        prompt += f"Planned Sessions:\n{json.dumps(data_dict['planned'], indent=2)}\n"
        prompt += f"Actual Strava Runs:\n{json.dumps(data_dict['completed_strava'], indent=2)}\n\n"

    # Call Gemini client
    client = get_gemini_client()
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PlanEvaluationSchema
        )
    )

    eval_data = PlanEvaluationSchema.model_validate_json(response.text)

    # 6. Apply matches to DB & save commentaries
    session_map = {s.id: s for s in sessions}
    activity_map = {a.id: a for a in activities}

    saved_evaluations = []

    for week_eval in eval_data.weeks:
        w_num = week_eval.week_number
        
        # Save or update WeeklyEvaluation record
        db_eval = db.query(WeeklyEvaluation).filter(
            WeeklyEvaluation.plan_id == plan.id,
            WeeklyEvaluation.week_number == w_num
        ).first()

        if not db_eval:
            db_eval = WeeklyEvaluation(
                plan_id=plan.id,
                week_number=w_num,
                commentary=week_eval.commentary
            )
            db.add(db_eval)
        else:
            db_eval.commentary = week_eval.commentary

        saved_evaluations.append(db_eval)

        # Update session status and match links
        for m in week_eval.matches:
            db_session = session_map.get(m.session_id)
            if db_session:
                # Update status
                db_session.status = m.status
                
                # If matched to a Strava activity, link it
                if m.strava_activity_id:
                    # Find activity with this strava_activity_id
                    db_act = db.query(Activity).filter(
                        Activity.strava_activity_id == str(m.strava_activity_id)
                    ).first()
                    if db_act:
                        db_act.matched_session_id = db_session.id
                        # Clear other matches to this session to maintain 1-to-1 if any
                        db.query(Activity).filter(
                            Activity.matched_session_id == db_session.id,
                            Activity.id != db_act.id
                        ).update({"matched_session_id": None})
                else:
                    # Unlinked session, ensure no activity points to it
                    db.query(Activity).filter(
                        Activity.matched_session_id == db_session.id
                    ).update({"matched_session_id": None})

    db.commit()
    return saved_evaluations
