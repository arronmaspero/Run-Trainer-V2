from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.models import get_db
from src.api.auth import get_current_user
from src.models.user import User, AthleteProfile
from src.models.plan import TrainingPlan, TrainingSession, WeeklyEvaluation
from src.services.planner_service import generate_ai_training_plan
from src.services.strava_service import sync_strava_activities
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/plans", tags=["plans"])

class OnboardingAndPlanRequest(BaseModel):
    # Profile inputs
    weekly_volume_miles: float
    runs_per_week: int
    long_run_day: str
    unavailable_days: str # e.g. "Monday,Wednesday"
    injury_notes: Optional[str] = None
    gender: Optional[str] = None
    
    # Goal inputs
    race_name: Optional[str] = None
    race_date: Optional[str] = None # YYYY-MM-DD
    race_distance: str # "5k", "10k", "half marathon", "marathon"
    target_time: Optional[str] = None # HH:MM:SS
    style: str = "balanced" # conservative, balanced, ambitious
    additional_notes: Optional[str] = None # Free-text additional constraints from the athlete

class PlanUpdateRequest(BaseModel):
    difficulty_feedback: str # 'easy', 'normal', 'hard'
    user_comments: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    date: str
    type: str
    name: str
    description: str
    duration_minutes: int
    distance_miles: Optional[float]
    target_pace_range: Optional[str]
    target_hr_zone: Optional[str]
    target_rpe: Optional[int]
    garmin_instructions_text: Optional[str]
    status: str

    class Config:
        from_attributes = True

class PlanResponse(BaseModel):
    id: str
    race_name: Optional[str]
    race_date: Optional[str]
    race_distance_miles: float
    start_date: str
    end_date: str
    style: str
    status: str

    class Config:
        from_attributes = True

@router.post("/generate", response_model=PlanResponse)
def generate_plan(
    data: OnboardingAndPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Save or update AthleteProfile first
        profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == current_user.id).first()
        if not profile:
            profile = AthleteProfile(user_id=current_user.id)
            db.add(profile)
            
        profile.weekly_volume_miles = data.weekly_volume_miles
        profile.runs_per_week = data.runs_per_week
        profile.long_run_day = data.long_run_day
        profile.unavailable_days = data.unavailable_days
        profile.injury_notes = data.injury_notes
        profile.gender = data.gender
        
        # Deactivate previous plans if any
        db.query(TrainingPlan).filter(
            TrainingPlan.user_id == current_user.id,
            TrainingPlan.status == "active"
        ).update({"status": "archived"})
        
        db.commit()
        
        # Generate new plan with Gemini
        db_plan = generate_ai_training_plan(
            user_id=current_user.id,
            race_name=data.race_name,
            race_date=data.race_date,
            race_distance=data.race_distance,
            target_time=data.target_time,
            weekly_volume=data.weekly_volume_miles,
            runs_per_week=data.runs_per_week,
            long_run_day=data.long_run_day,
            unavailable_days=data.unavailable_days,
            style=data.style,
            db=db,
            additional_notes=data.additional_notes
        )
        
        # Trigger Strava activity sync (non-blocking — plan generation always succeeds)
        try:
            sync_strava_activities(current_user.id, db)
        except Exception as strava_err:
            import logging
            logging.getLogger(__name__).warning(f"Strava sync skipped: {strava_err}")

        # Convert dates to ISO strings for pydantic
        return PlanResponse(
            id=db_plan.id,
            race_name=db_plan.race_name,
            race_date=db_plan.race_date.isoformat() if db_plan.race_date else None,
            race_distance_miles=db_plan.race_distance_miles,
            start_date=db_plan.start_date.isoformat(),
            end_date=db_plan.end_date.isoformat(),
            style=db_plan.style,
            status=db_plan.status
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate plan: {str(e)}"
        )

@router.get("/active")
def get_active_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == current_user.id,
        TrainingPlan.status == "active"
    ).first()
    
    if not plan:
        return {"plan": None, "sessions": [], "weekly_evaluations": []}
        
    sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == plan.id
    ).order_by(TrainingSession.date).all()
    
    evaluations = db.query(WeeklyEvaluation).filter(
        WeeklyEvaluation.plan_id == plan.id
    ).order_by(WeeklyEvaluation.week_number).all()
    
    return {
        "plan": {
            "id": plan.id,
            "race_name": plan.race_name,
            "race_date": plan.race_date.isoformat() if plan.race_date else None,
            "race_distance_miles": plan.race_distance_miles,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "style": plan.style,
            "status": plan.status
        },
        "sessions": [
            {
                "id": s.id,
                "date": s.date.isoformat(),
                "type": s.type,
                "name": s.name,
                "description": s.description,
                "duration_minutes": s.duration_minutes,
                "distance_miles": s.distance_miles,
                "target_pace_range": s.target_pace_range,
                "target_hr_zone": s.target_hr_zone,
                "target_rpe": s.target_rpe,
                "garmin_instructions_text": s.garmin_instructions_text,
                "status": s.status
            }
            for s in sessions
        ],
        "weekly_evaluations": [
            {
                "week_number": ev.week_number,
                "commentary": ev.commentary
            }
            for ev in evaluations
        ]
    }

@router.post("/evaluate")
def evaluate_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from src.services.evaluation_service import evaluate_plan_progress
    try:
        evaluations = evaluate_plan_progress(current_user.id, db)
        return {
            "status": "success",
            "evaluations": [
                {
                    "week_number": ev.week_number,
                    "commentary": ev.commentary
                }
                for ev in evaluations
            ]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/update/preview")
def preview_update(
    request: PlanUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from src.services.planner_service import preview_plan_update
    try:
        preview_data = preview_plan_update(
            user_id=current_user.id,
            difficulty_feedback=request.difficulty_feedback,
            user_comments=request.user_comments,
            db=db
        )
        return {
            "status": "success",
            "explanation": preview_data.explanation,
            "sessions": [
                {
                    "date": s.date,
                    "type": s.type,
                    "name": s.name,
                    "description": s.description,
                    "duration_minutes": s.duration_minutes,
                    "distance_miles": s.distance_miles,
                    "target_pace_range": s.target_pace_range,
                    "target_hr_zone": s.target_hr_zone,
                    "target_rpe": s.target_rpe,
                    "garmin_instructions_text": s.garmin_instructions_text
                }
                for s in preview_data.sessions
            ]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/update/apply")
def apply_update(
    request: PlanUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from src.services.planner_service import apply_plan_update
    try:
        plan = apply_plan_update(
            user_id=current_user.id,
            difficulty_feedback=request.difficulty_feedback,
            user_comments=request.user_comments,
            db=db
        )
        return {"status": "success", "plan_id": plan.id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/push-garmin")
def sync_to_garmin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from src.services.garmin_service import push_plan_to_garmin
    try:
        res = push_plan_to_garmin(user_id=current_user.id, db=db)
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


