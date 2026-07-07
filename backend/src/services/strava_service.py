import httpx
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from src.config import settings
from src.models.activity import ConnectedAccount

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

def get_strava_client_credentials(user_id: str, db: Session) -> tuple:
    from src.models.user import AthleteProfile
    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == user_id).first()
    client_id = (profile.strava_client_id or "").strip() if profile else ""
    client_secret = (profile.strava_client_secret or "").strip() if profile else ""
    
    # Fallback to settings
    if not client_id:
        client_id = settings.STRAVA_CLIENT_ID
    if not client_secret:
        client_secret = settings.STRAVA_CLIENT_SECRET
        
    return client_id, client_secret

def get_strava_auth_url(user_id: str, client_id: str) -> str:
    # Build authorization URL redirecting to local server API callback
    redirect_uri = "http://localhost:8000/api/v1/strava/callback"
    return (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=activity:read_all&"
        f"state={user_id}"
    )

def exchange_strava_code(code: str, user_id: str, db: Session) -> dict:
    # Exchange authorization code for tokens
    client_id, client_secret = get_strava_client_credentials(user_id, db)
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code"
    }
    
    # Send request
    response = httpx.post(STRAVA_TOKEN_URL, data=payload)
    if response.status_code != 200:
        raise Exception(f"Strava token exchange failed: {response.text}")
        
    data = response.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    expires_at = datetime.utcfromtimestamp(data["expires_at"])
    athlete_name = f"{data.get('athlete', {}).get('firstname', '')} {data.get('athlete', {}).get('lastname', '')}".strip()
    
    # Save/update ConnectedAccount in database
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == user_id,
        ConnectedAccount.provider == "strava"
    ).first()
    
    if not account:
        account = ConnectedAccount(user_id=user_id, provider="strava")
        db.add(account)
        
    account.access_token = access_token
    account.refresh_token = refresh_token
    account.expires_at = expires_at
    account.scopes = "activity:read_all"
    account.last_sync_at = datetime.utcnow()
    
    db.commit()
    return {"status": "connected", "athlete_name": athlete_name}

def get_active_strava_token(user_id: str, db: Session) -> str:
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == user_id,
        ConnectedAccount.provider == "strava"
    ).first()
    
    if not account:
        raise Exception("Strava is not connected for this user")
        
    # Check if token is expired or expires in next 5 minutes
    if account.expires_at <= datetime.utcnow() + timedelta(minutes=5):
        # Refresh token
        client_id, client_secret = get_strava_client_credentials(user_id, db)
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token"
        }
        response = httpx.post(STRAVA_TOKEN_URL, data=payload)
        if response.status_code != 200:
            raise Exception(f"Strava token refresh failed: {response.text}")
            
        data = response.json()
        account.access_token = data["access_token"]
        account.refresh_token = data["refresh_token"]
        account.expires_at = datetime.utcfromtimestamp(data["expires_at"])
        db.commit()
        
    return account.access_token


def sync_strava_activities(user_id: str, db: Session, start_date: Optional[datetime] = None) -> int:
    """Fetch Strava activities starting from start_date (or default 90 days ago) and upsert into the Activity table.
    Returns the number of activities synced. Silently skips if Strava is not connected."""
    import json
    from datetime import timezone
    from src.models.activity import Activity

    # Get a valid token — will raise if not connected
    token = get_active_strava_token(user_id, db)

    # Calculate Unix epoch timestamp
    if start_date:
        after_epoch = int(start_date.replace(tzinfo=timezone.utc).timestamp())
    else:
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        after_epoch = int(ninety_days_ago.replace(tzinfo=timezone.utc).timestamp())

    response = httpx.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": 100, "after": after_epoch},
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Strava activities fetch failed: {response.text}")

    activities_data = response.json()
    synced = 0

    for item in activities_data:
        strava_id = str(item.get("id", ""))
        if not strava_id:
            continue

        # Distance: Strava returns metres — convert to miles
        distance_metres = item.get("distance", 0.0)
        distance_miles = distance_metres * 0.000621371

        # Elevation: Strava returns metres — convert to feet
        elevation_metres = item.get("total_elevation_gain", 0.0)
        elevation_feet = elevation_metres * 3.28084

        # Parse start date
        start_date_str = item.get("start_date", "")
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            start_date = datetime.utcnow()

        # Splits (laps) — store as JSON string
        splits_raw = item.get("splits_metric", item.get("splits_standard", []))
        splits_json = json.dumps(splits_raw) if splits_raw else None

        # Average HR and cadence
        avg_hr = item.get("average_heartrate")
        avg_cadence = item.get("average_cadence")
        if avg_cadence:
            avg_cadence = avg_cadence * 2  # Strava cadence is per leg, double for SPM

        # Upsert: find existing or create new
        existing = db.query(Activity).filter(
            Activity.strava_activity_id == strava_id
        ).first()

        if existing:
            # Update in place
            existing.name = item.get("name", "")
            existing.start_date = start_date
            existing.distance_miles = distance_miles
            existing.moving_time_seconds = item.get("moving_time", 0)
            existing.elapsed_time_seconds = item.get("elapsed_time", 0)
            existing.elevation_gain_feet = elevation_feet
            existing.average_heart_rate = int(avg_hr) if avg_hr else None
            existing.average_cadence = round(avg_cadence, 1) if avg_cadence else None
            existing.splits_json = splits_json
        else:
            activity = Activity(
                strava_activity_id=strava_id,
                user_id=user_id,
                name=item.get("name", ""),
                type=item.get("type", "Run").lower(),
                start_date=start_date,
                distance_miles=distance_miles,
                moving_time_seconds=item.get("moving_time", 0),
                elapsed_time_seconds=item.get("elapsed_time", 0),
                elevation_gain_feet=elevation_feet,
                average_heart_rate=int(avg_hr) if avg_hr else None,
                average_cadence=round(avg_cadence, 1) if avg_cadence else None,
                splits_json=splits_json
            )
            db.add(activity)

        synced += 1

    db.commit()
    return synced
