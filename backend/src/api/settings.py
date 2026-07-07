import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.models import get_db
from src.api.auth import get_current_user
from src.models.user import User, AthleteProfile
from src.models.activity import ConnectedAccount, Activity
from src.models.plan import TrainingPlan, TrainingSession

router = APIRouter(prefix="/settings", tags=["settings"])

@router.delete("/strava")
def revoke_strava(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find connected accounts for Strava
    accounts = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == current_user.id,
        ConnectedAccount.provider == "strava"
    ).all()
    
    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No connected Strava account found."
        )
        
    for account in accounts:
        db.delete(account)
        
    db.commit()
    return {"status": "success", "message": "Strava integration revoked successfully."}

@router.get("/export")
def export_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = current_user.profile
    profile_data = {}
    if profile:
        profile_data = {
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            "gender": profile.gender,
            "resting_heart_rate": profile.resting_heart_rate,
            "max_heart_rate": profile.max_heart_rate,
            "threshold_heart_rate": profile.threshold_heart_rate,
            "vo2_max": profile.vo2_max,
            "weekly_volume_miles": profile.weekly_volume_miles,
            "runs_per_week": profile.runs_per_week,
            "long_run_day": profile.long_run_day,
            "unavailable_days": profile.unavailable_days,
            "injury_notes": profile.injury_notes,
        }

    # Fetch Connected accounts (exclude sensitive tokens)
    accounts = db.query(ConnectedAccount).filter(ConnectedAccount.user_id == current_user.id).all()
    accounts_data = [
        {
            "provider": acc.provider,
            "last_sync_at": acc.last_sync_at.isoformat() if acc.last_sync_at else None,
            "scopes": acc.scopes
        }
        for acc in accounts
    ]

    # Fetch Activities
    activities = db.query(Activity).filter(Activity.user_id == current_user.id).all()
    activities_data = [
        {
            "strava_activity_id": act.strava_activity_id,
            "type": act.type,
            "start_date": act.start_date.isoformat() if act.start_date else None,
            "distance_miles": act.distance_miles,
            "moving_time_seconds": act.moving_time_seconds,
            "elapsed_time_seconds": act.elapsed_time_seconds,
            "elevation_gain_feet": act.elevation_gain_feet,
            "average_heart_rate": act.average_heart_rate,
            "average_cadence": act.average_cadence,
        }
        for act in activities
    ]

    # Fetch Plans & Sessions
    plans = db.query(TrainingPlan).filter(TrainingPlan.user_id == current_user.id).all()
    plans_data = []
    for plan in plans:
        sessions = db.query(TrainingSession).filter(TrainingSession.plan_id == plan.id).all()
        sessions_data = [
            {
                "date": s.date.isoformat(),
                "type": s.type,
                "name": s.name,
                "description": s.description,
                "duration_minutes": s.duration_minutes,
                "distance_miles": s.distance_miles,
                "target_pace_range": s.target_pace_range,
                "target_hr_zone": s.target_hr_zone,
                "target_rpe": s.target_rpe,
                "status": s.status,
            }
            for s in sessions
        ]
        
        plans_data.append({
            "race_name": plan.race_name,
            "race_date": plan.race_date.isoformat() if plan.race_date else None,
            "race_distance_miles": plan.race_distance_miles,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "style": plan.style,
            "status": plan.status,
            "sessions": sessions_data
        })

    export_payload = {
        "user": {
            "name": current_user.name,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "profile": profile_data,
        "connected_accounts": accounts_data,
        "activities": activities_data,
        "plans": plans_data
    }

    return export_payload

@router.delete("/account")
def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.delete(current_user)
    db.commit()
    return {"status": "success", "message": "Your user account and all associated training data have been permanently deleted."}
