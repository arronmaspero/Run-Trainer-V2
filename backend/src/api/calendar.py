import json
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from google.genai import types

from src.models import get_db
from src.api.auth import get_current_user
from src.models.user import User, AthleteProfile
from src.models.plan import TrainingPlan, TrainingSession
from src.models.changelog import PlanChangeLog
from src.services.planner_service import get_gemini_client

router = APIRouter(prefix="/plans", tags=["calendar"])

class MoveSessionRequest(BaseModel):
    session_id: str
    new_date: str  # YYYY-MM-DD

class RebalanceItem(BaseModel):
    session_id: str = Field(description="The unique ID of the training session being rescheduled")
    date: str = Field(description="The proposed new date in YYYY-MM-DD format")

class RebalanceResponseSchema(BaseModel):
    proposed_changes: List[RebalanceItem] = Field(description="Chronological list of proposed session rescheduling shifts")

class RebalanceRequest(BaseModel):
    plan_id: str
    week_number: Optional[int] = None
    confirm: bool = False

def check_plan_imbalance(plan_id: str, db: Session) -> tuple[bool, List[str]]:
    # Fetch all sessions for this plan, ordered by date
    sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan_id
    ).order_by(TrainingSession.date).all()
    
    warnings = []
    is_imbalanced = False
    
    # Hard run types
    hard_types = {"intervals", "tempo", "long run"}
    
    # Group sessions by date
    by_date = {}
    for s in sessions:
        by_date.setdefault(s.date, []).append(s)
        
    # Check for same-day multiple workouts (excluding rest days)
    for dt, day_sessions in by_date.items():
        run_sessions = [s for s in day_sessions if s.type.lower() != "rest"]
        if len(run_sessions) > 1:
            is_imbalanced = True
            warnings.append(f"Multiple active workouts scheduled on {dt.isoformat()}.")
                
    # Sort dates to check consecutive days
    sorted_dates = sorted(by_date.keys())
    for i in range(len(sorted_dates) - 1):
        d1 = sorted_dates[i]
        d2 = sorted_dates[i+1]
        if (d2 - d1).days == 1:
            # Check if both days have hard workouts
            h1 = [s for s in by_date[d1] if s.type.lower() in hard_types]
            h2 = [s for s in by_date[d2] if s.type.lower() in hard_types]
            if h1 and h2:
                is_imbalanced = True
                warnings.append(
                    f"Consecutive hard runs scheduled on {d1.isoformat()} ({h1[0].type}) "
                    f"and {d2.isoformat()} ({h2[0].type}). We recommend inserting a recovery/rest day."
                )
                
    return is_imbalanced, warnings

@router.post("/sessions/move")
def move_session(
    data: MoveSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Retrieve the session
    session = db.query(TrainingSession).filter(TrainingSession.id == data.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found"
        )
        
    # Verify ownership of the plan
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == session.plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this training plan"
        )
        
    # Parse new date
    try:
        new_date_obj = datetime.strptime(data.new_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD."
        )
        
    # Ensure new date is within plan duration range
    if new_date_obj < plan.start_date or new_date_obj > plan.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposed date lies outside plan range ({plan.start_date} to {plan.end_date})."
        )
        
    old_date = session.date
    old_date_str = old_date.isoformat()
    
    # Check if there is already another session on the target date
    target_session = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id,
        TrainingSession.date == new_date_obj,
        TrainingSession.id != session.id
    ).first()
    
    swapped = False
    swapped_session_id = None
    
    if target_session:
        swapped = True
        swapped_session_id = target_session.id
        
        # Log the swap moves
        log_entry_1 = PlanChangeLog(
            plan_id=plan.id,
            user_id=current_user.id,
            change_type="drag_and_drop",
            old_value_json=json.dumps({"session_id": session.id, "date": old_date_str}),
            new_value_json=json.dumps({"session_id": session.id, "date": data.new_date}),
            reason="Manual drag-and-drop session swap (moved out)",
            is_ai_generated=False,
            is_user_approved=True
        )
        log_entry_2 = PlanChangeLog(
            plan_id=plan.id,
            user_id=current_user.id,
            change_type="drag_and_drop",
            old_value_json=json.dumps({"session_id": target_session.id, "date": data.new_date}),
            new_value_json=json.dumps({"session_id": target_session.id, "date": old_date_str}),
            reason="Manual drag-and-drop session swap (swapped in)",
            is_ai_generated=False,
            is_user_approved=True
        )
        db.add(log_entry_1)
        db.add(log_entry_2)
        
        # Execute swap
        session.date = new_date_obj
        target_session.date = old_date
    else:
        # Normal move
        log_entry = PlanChangeLog(
            plan_id=plan.id,
            user_id=current_user.id,
            change_type="drag_and_drop",
            old_value_json=json.dumps({"session_id": session.id, "date": old_date_str}),
            new_value_json=json.dumps({"session_id": session.id, "date": data.new_date}),
            reason="Manual drag-and-drop session move",
            is_ai_generated=False,
            is_user_approved=True
        )
        db.add(log_entry)
        session.date = new_date_obj
        
    db.commit()
    
    # Verify validation rules
    is_imbalanced, warnings = check_plan_imbalance(plan.id, db)
    
    return {
        "status": "success",
        "swapped": swapped,
        "swapped_session_id": swapped_session_id,
        "swapped_session_new_date": old_date_str,
        "is_imbalanced": is_imbalanced,
        "warnings": warnings
    }

@router.post("/rebalance")
def rebalance_plan(
    data: RebalanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.id == data.plan_id,
        TrainingPlan.user_id == current_user.id
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training plan not found"
        )
        
    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == current_user.id).first()
    unavailable_days = profile.unavailable_days if profile else ""
    long_run_day = profile.long_run_day if profile else "Sunday"
    
    # Fetch all active sessions ordered by date
    sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id
    ).order_by(TrainingSession.date).all()
    
    # Calculate starting Monday of the plan
    plan_start = plan.start_date
    start_day = plan_start.weekday() # 0 = Monday, ..., 6 = Sunday
    plan_monday = plan_start - timedelta(days=start_day)
    
    week_number = data.week_number
    if week_number:
        # Rebalance a specific week W
        week_start = plan_monday + timedelta(weeks=week_number - 1)
        week_end = week_start + timedelta(days=6)
        
        target_sessions = [s for s in sessions if week_start <= s.date <= week_end]
        
        # Context: 3 days before week starts (Fri-Sun of W-1) and 3 days after week ends (Mon-Wed of W+1)
        prev_week_start = week_start - timedelta(days=3)
        next_week_end = week_end + timedelta(days=3)
        
        context_sessions = [
            s for s in sessions
            if (prev_week_start <= s.date < week_start) or (week_end < s.date <= next_week_end)
        ]
        allowed_range_desc = f"from {week_start.isoformat()} to {week_end.isoformat()} (Week {week_number})"
    else:
        # Rebalance all upcoming/future sessions
        today = date.today()
        target_sessions = [s for s in sessions if s.date >= today]
        context_sessions = []
        allowed_range_desc = f"from {plan.start_date.isoformat()} to {plan.end_date.isoformat()} (Plan duration)"
        
    if not target_sessions:
        return {
            "status": "success",
            "message": "No sessions to rebalance",
            "warnings": [],
            "proposed_changes": []
        }
        
    # Formulate Gemini prompt for smart session rebalancing
    target_info = "\n".join([
        f"- ID: {s.id} | Current Date: {s.date.isoformat()} | Type: {s.type} | Name: {s.name}"
        for s in target_sessions
    ])
    
    context_info = "\n".join([
        f"- FIXED Date: {s.date.isoformat()} | Type: {s.type} | Name: {s.name}"
        for s in context_sessions
    ]) if context_sessions else "None"
    
    prompt = (
        f"You are an evidence-informed running coach rebalancing a training plan's session schedule.\n\n"
        f"User Constraints:\n"
        f"- Unavailable training days: {unavailable_days}\n"
        f"- Preferred long run day: {long_run_day}\n"
        f"- Target race: {plan.race_name or 'N/A'} on {plan.race_date.isoformat() if plan.race_date else 'N/A'}\n\n"
        f"Target Sessions to Reschedule (you MUST assign new dates to these):\n{target_info}\n\n"
        f"Contextual Fixed Sessions (adjacent weeks' sessions, you MUST NOT change these dates, they are read-only reference):\n{context_info}\n\n"
        f"Instructions:\n"
        f"1. Rearrange the dates of the Target Sessions only so that:\n"
        f"   - No consecutive days have hard quality workouts (Intervals, Tempo, Long Run), including across week boundaries (i.e. compare with Contextual Fixed Sessions).\n"
        f"   - Long runs should reside on {long_run_day}.\n"
        f"   - No workouts are scheduled on unavailable days ({unavailable_days}).\n"
        f"   - Absolutely MUST NOT place more than one session on any single day (every training session must be assigned a unique date; no two sessions can share the same date under any circumstances).\n"
        f"   - All rescheduled dates for Target Sessions must remain strictly within their allowed range ({allowed_range_desc}).\n"
        f"2. Keep the session details (names, descriptions, and durations) unchanged; only shift their calendar date.\n"
        f"3. Return the proposed updates mapping each target session ID to its recommended new date."
    )
    
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RebalanceResponseSchema
            )
        )
        ai_data = RebalanceResponseSchema.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini rebalancing model query failed: {str(e)}"
        )
        
    proposed_map = {item.session_id: item.date for item in ai_data.proposed_changes}
    
    # Construct preview payload mapping proposed changes
    proposed_changes_preview = []
    for s in target_sessions:
        new_date_str = proposed_map.get(s.id)
        if new_date_str and new_date_str != s.date.isoformat():
            proposed_changes_preview.append({
                "session_id": s.id,
                "name": s.name,
                "type": s.type,
                "old_date": s.date.isoformat(),
                "new_date": new_date_str
            })
            
    # Calculate live validation warning rules for user reference
    _, warnings = check_plan_imbalance(plan.id, db)
    
    if data.confirm:
        # Save change log audit trail
        old_schedule = {s.id: s.date.isoformat() for s in target_sessions}
        new_schedule = {s.id: proposed_map.get(s.id, s.date.isoformat()) for s in target_sessions}
        
        log_entry = PlanChangeLog(
            plan_id=plan.id,
            user_id=current_user.id,
            change_type="ai_rebalance",
            old_value_json=json.dumps(old_schedule),
            new_value_json=json.dumps(new_schedule),
            reason=f"AI-powered schedule rebalance recommendation accepted for Week {week_number}" if week_number else "AI-powered schedule rebalance recommendation accepted",
            is_ai_generated=True,
            is_user_approved=True
        )
        db.add(log_entry)
        
        # Apply changes
        for s in target_sessions:
            new_date_str = proposed_map.get(s.id)
            if new_date_str:
                try:
                    s.date = datetime.strptime(new_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
        db.commit()
        return {
            "status": "success",
            "message": "AI Rebalance applied successfully",
            "warnings": warnings,
            "proposed_changes": proposed_changes_preview
        }
    else:
        return {
            "status": "preview",
            "warnings": warnings,
            "proposed_changes": proposed_changes_preview
        }
