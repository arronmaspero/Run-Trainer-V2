from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from src.config import settings
from src.models import get_db
from src.api.auth import get_current_user
from src.models.user import User
from src.services.strava_service import get_strava_auth_url, exchange_strava_code

router = APIRouter(prefix="/strava", tags=["strava"])

@router.get("/connect-url")
def get_connect_url(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from src.services.strava_service import get_strava_client_credentials
    client_id, client_secret = get_strava_client_credentials(current_user.id, db)
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strava API credentials (Client ID, Client Secret) are not configured. Please configure them in your profile settings to connect to Strava."
        )
    url = get_strava_auth_url(current_user.id, client_id)
    return {"url": url}

@router.get("/callback")
def strava_callback(
    code: str = Query(...),
    state: str = Query(...), # state contains the user_id
    db: Session = Depends(get_db)
):
    try:
        # State contains the user ID
        result = exchange_strava_code(code, state, db)
        # Redirect user back to the frontend profile page
        return RedirectResponse(url="/#profile")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect Strava: {str(e)}"
        )

@router.get("/test")
def test_strava_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        from src.services.strava_service import get_active_strava_token
        import httpx
        token = get_active_strava_token(current_user.id, db)
        headers = {"Authorization": f"Bearer {token}"}
        res = httpx.get("https://www.strava.com/api/v3/athlete", headers=headers)
        if res.status_code != 200:
            return {"status": "error", "message": f"Strava API error: {res.text}"}
        athlete_data = res.json()
        name = f"{athlete_data.get('firstname', '')} {athlete_data.get('lastname', '')}".strip()
        return {
            "status": "success",
            "message": f"Connection active! Authenticated as: {name}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/activities")
def list_strava_activities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return all stored Strava activities for the current user, newest first."""
    from src.models.activity import Activity
    activities = (
        db.query(Activity)
        .filter(Activity.user_id == current_user.id)
        .order_by(Activity.start_date.desc())
        .all()
    )

    def fmt_time(seconds: int) -> str:
        if not seconds:
            return "0:00:00"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    def fmt_pace(distance_miles: float, moving_time_seconds: int) -> str:
        if not distance_miles or not moving_time_seconds:
            return "N/A"
        pace_seconds = moving_time_seconds / distance_miles
        m = int(pace_seconds // 60)
        s = int(pace_seconds % 60)
        return f"{m}:{s:02d} /mi"

    return [
        {
            "id": a.id,
            "strava_activity_id": a.strava_activity_id,
            "name": a.name or "Activity",
            "type": a.type,
            "start_date": a.start_date.isoformat() if a.start_date else None,
            "distance_miles": round(a.distance_miles, 2),
            "moving_time_seconds": a.moving_time_seconds,
            "moving_time_formatted": fmt_time(a.moving_time_seconds),
            "pace": fmt_pace(a.distance_miles, a.moving_time_seconds),
            "elevation_gain_feet": round(a.elevation_gain_feet, 1),
            "average_heart_rate": a.average_heart_rate,
            "average_cadence": a.average_cadence,
        }
        for a in activities
    ]


@router.get("/activities/{activity_id}")
def get_strava_activity(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return full detail for a single stored Strava activity including splits."""
    import json
    from src.models.activity import Activity

    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == current_user.id
    ).first()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    def fmt_time(seconds: int) -> str:
        if not seconds:
            return "0:00:00"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    def fmt_pace(distance_miles: float, moving_time_seconds: int) -> str:
        if not distance_miles or not moving_time_seconds:
            return "N/A"
        pace_seconds = moving_time_seconds / distance_miles
        m = int(pace_seconds // 60)
        s = int(pace_seconds % 60)
        return f"{m}:{s:02d} /mi"

    # Parse splits JSON
    splits = []
    if activity.splits_json:
        try:
            raw_splits = json.loads(activity.splits_json)
            for i, sp in enumerate(raw_splits):
                split_dist_m = sp.get("distance", 0)
                split_dist_mi = split_dist_m * 0.000621371
                split_time = sp.get("moving_time", 0)
                splits.append({
                    "lap": i + 1,
                    "distance": round(split_dist_mi, 2),
                    "moving_time_formatted": fmt_time(split_time),
                    "pace": fmt_pace(split_dist_mi, split_time),
                    "average_heartrate": sp.get("average_heartrate"),
                    "elevation_difference": round(sp.get("elevation_difference", 0) * 3.28084, 1),
                })
        except Exception:
            splits = []

    return {
        "id": activity.id,
        "strava_activity_id": activity.strava_activity_id,
        "name": activity.name or "Activity",
        "type": activity.type,
        "start_date": activity.start_date.isoformat() if activity.start_date else None,
        "distance_miles": round(activity.distance_miles, 2),
        "moving_time_seconds": activity.moving_time_seconds,
        "moving_time_formatted": fmt_time(activity.moving_time_seconds),
        "elapsed_time_formatted": fmt_time(activity.elapsed_time_seconds),
        "pace": fmt_pace(activity.distance_miles, activity.moving_time_seconds),
        "elevation_gain_feet": round(activity.elevation_gain_feet, 1),
        "average_heart_rate": activity.average_heart_rate,
        "average_cadence": activity.average_cadence,
        "matched_session_id": activity.matched_session_id,
        "splits": splits,
    }
