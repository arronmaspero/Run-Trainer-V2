import json
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.models.user import User, AthleteProfile
from src.models.plan import TrainingPlan, TrainingSession, WeeklyEvaluation
from src.models.activity import Activity
from src.models.chat_message import ChatMessage
from src.services.planner_service import get_gemini_client, apply_plan_update

class ChatMessageResponse(BaseModel):
    id: str
    sender: str
    text: str
    timestamp: str
    has_proposed_changes: bool = False

def build_athlete_context(user_id: str, db: Session) -> Dict[str, Any]:
    """Gather all relevant context about the athlete, plan, workouts, and evaluations."""
    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == user_id).first()
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == user_id,
        TrainingPlan.status == "active"
    ).first()

    if not plan:
        raise Exception("No active training plan found for athlete")

    sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id
    ).order_by(TrainingSession.date).all()

    evaluations = db.query(WeeklyEvaluation).filter(
        WeeklyEvaluation.plan_id == plan.id
    ).order_by(WeeklyEvaluation.week_number).all()

    activities = db.query(Activity).filter(
        Activity.user_id == user_id
    ).order_by(Activity.start_date.desc()).limit(10).all()

    today_str = date.today().isoformat()
    past_sessions = []
    future_sessions = []

    for s in sessions:
        s_dict = {
            "date": s.date.isoformat(),
            "type": s.type,
            "name": s.name,
            "distance_miles": s.distance_miles,
            "duration_minutes": s.duration_minutes,
            "target_pace_range": s.target_pace_range,
            "status": s.status
        }
        if s.date.isoformat() < today_str:
            past_sessions.append(s_dict)
        else:
            future_sessions.append(s_dict)

    profile_dict = {}
    if profile:
        profile_dict = {
            "weekly_volume_miles": profile.weekly_volume_miles,
            "runs_per_week": profile.runs_per_week,
            "long_run_day": profile.long_run_day,
            "unavailable_days": profile.unavailable_days,
            "resting_hr": profile.resting_heart_rate,
            "max_hr": profile.max_heart_rate,
            "threshold_hr": profile.threshold_heart_rate,
            "vo2_max": profile.vo2_max
        }

    eval_list = [{"week_number": e.week_number, "commentary": e.commentary} for e in evaluations]
    act_list = [{
        "name": a.name,
        "date": a.start_date.isoformat() if a.start_date else "N/A",
        "distance_miles": round(a.distance_meters / 1609.34, 2) if a.distance_meters else 0.0,
        "moving_time_mins": round(a.moving_time_seconds / 60, 1) if a.moving_time_seconds else 0
    } for a in activities]

    return {
        "user_name": user.name if user else "Runner",
        "profile": profile_dict,
        "plan": {
            "id": plan.id,
            "race_name": plan.race_name,
            "race_date": plan.race_date.isoformat() if plan.race_date else "N/A",
            "race_distance_miles": plan.race_distance_miles,
            "style": plan.style,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat()
        },
        "today_date": today_str,
        "past_sessions_count": len(past_sessions),
        "recent_past_sessions": past_sessions[-7:], # Last 7 past sessions
        "upcoming_future_sessions": future_sessions[:14], # Next 14 planned sessions
        "recent_activities": act_list[:5],
        "weekly_evaluations": eval_list
    }


def get_chat_history(user_id: str, db: Session) -> List[ChatMessageResponse]:
    """Retrieve persistent conversation history for the athlete's active plan."""
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == user_id,
        TrainingPlan.status == "active"
    ).first()
    if not plan:
        return []

    messages = db.query(ChatMessage).filter(
        ChatMessage.plan_id == plan.id
    ).order_by(ChatMessage.timestamp.asc()).all()

    return [
        ChatMessageResponse(
            id=m.id,
            sender=m.sender,
            text=m.text,
            timestamp=m.timestamp.isoformat(),
            has_proposed_changes=bool(m.proposed_changes_json)
        )
        for m in messages
    ]


def handle_user_chat_message(user_id: str, message_text: str, db: Session) -> Dict[str, Any]:
    """Process a user message, query Gemini AI coach with context, and store response."""
    context = build_athlete_context(user_id, db)
    plan_id = context["plan"]["id"]

    # 1. Store user message in DB
    user_msg = ChatMessage(
        plan_id=plan_id,
        user_id=user_id,
        sender="user",
        text=message_text,
        timestamp=datetime.utcnow()
    )
    db.add(user_msg)
    db.commit()

    # 2. Retrieve recent conversation history (up to last 15 messages)
    history_records = db.query(ChatMessage).filter(
        ChatMessage.plan_id == plan_id
    ).order_by(ChatMessage.timestamp.asc()).all()

    conversation_formatted = []
    for msg in history_records:
        role_label = "Runner" if msg.sender == "user" else "AI Coach"
        conversation_formatted.append(f"{role_label}: {msg.text}")

    history_str = "\n".join(conversation_formatted)

    # 3. Formulate Gemini prompt
    system_instructions = (
        "You are AuraRun's expert AI Running Coach having an interactive conversation with your athlete.\n"
        "Your role is to listen to their feedback, discuss workout adjustments, explain training science, "
        "and help refine their training plan collaboratively.\n\n"
        "ATHLETE & PLAN CONTEXT:\n"
        f"{json.dumps(context, indent=2)}\n\n"
        "CONVERSATION RULES:\n"
        "1. Be warm, supportive, evidence-based, and encouraging.\n"
        "2. Keep responses clear and readable (use short bullet points or paragraph breaks).\n"
        "3. If the athlete asks questions or expresses preferences (e.g. shift long run day, lighten Thursdays, focus on 10k pace), "
        "explain the coaching tradeoffs and clearly propose specific changes to their schedule.\n"
        "4. If you and the runner reach an agreement or if the runner asks you to update/change their plan, explicitly summarize the agreed changes in your message.\n"
        "5. Respond directly in character as the AI Coach."
    )

    full_prompt = (
        f"{system_instructions}\n\n"
        f"RECENT CONVERSATION HISTORY:\n"
        f"{history_str}\n\n"
        f"AI Coach:"
    )

    client = get_gemini_client()
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=full_prompt
        )
        ai_reply_text = response.text.strip()
    except Exception as e:
        ai_reply_text = f"I'm sorry, I ran into an issue reflecting on your training data: {str(e)}. How can I assist you with your schedule?"

    # Detect if AI coach is summarizing/proposing concrete plan changes
    # We flag proposed changes if keywords indicate a clear plan modification proposal
    lower_reply = ai_reply_text.lower()
    has_proposed_changes = any(k in lower_reply for k in ["agreed", "i will update", "i can change", "propose", "suggest updating", "adjusting your plan", "reschedule"])

    # 4. Save AI coach response in DB
    coach_msg = ChatMessage(
        plan_id=plan_id,
        user_id=user_id,
        sender="coach",
        text=ai_reply_text,
        timestamp=datetime.utcnow(),
        proposed_changes_json=json.dumps({"summary": ai_reply_text}) if has_proposed_changes else None
    )
    db.add(coach_msg)
    db.commit()
    db.refresh(coach_msg)

    return {
        "id": coach_msg.id,
        "sender": "coach",
        "text": ai_reply_text,
        "timestamp": coach_msg.timestamp.isoformat(),
        "has_proposed_changes": has_proposed_changes
    }


def apply_chat_discussed_changes(user_id: str, db: Session) -> Dict[str, Any]:
    """Extract agreed changes from chat history and apply them to future plan sessions."""
    history = get_chat_history(user_id, db)
    if not history:
        raise Exception("No conversation history found to derive plan changes.")

    # Collect user & coach chat excerpts
    recent_dialogue = [f"{m.sender.upper()}: {m.text}" for m in history[-8:]]
    summary_comments = (
        "Apply agreed changes discussed in AI Coach conversation:\n" +
        "\n".join(recent_dialogue)
    )

    # Use existing apply_plan_update service which uses Gemini to adapt future sessions
    updated_plan = apply_plan_update(
        user_id=user_id,
        difficulty_feedback="normal",
        user_comments=summary_comments,
        db=db
    )

    return {
        "status": "success",
        "message": "Your training plan has been successfully updated based on your conversation with your AI Coach!"
    }
