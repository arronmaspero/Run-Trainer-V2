from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from src.models import get_db
from src.models.user import User
from src.services.auth_service import hash_password, verify_password, create_user_session, get_user_from_session
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str

    class Config:
        from_attributes = True

# Dependency to get current user from header
def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    token = authorization.split(" ")[1]
    user = get_user_from_session(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Session has expired or is invalid"
        )
    return user

@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Create user
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login")
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    token = create_user_session(user.id)
    return {
        "session_token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

from typing import Optional
from datetime import date

class ProfileUpdate(BaseModel):
    name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    resting_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    threshold_heart_rate: Optional[int] = None
    vo2_max: Optional[float] = None
    strava_client_id: Optional[str] = None
    strava_client_secret: Optional[str] = None

@router.get("/profile")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = current_user.profile
    
    # Check connected accounts
    strava_connected = any(acc.provider == "strava" for acc in current_user.connected_accounts)
    
    garmin_acc = next((acc for acc in current_user.connected_accounts if acc.provider == "garmin"), None)
    garmin_connected = garmin_acc is not None
    garmin_email = garmin_acc.access_token if garmin_acc else None
    
    return {
        "name": current_user.name,
        "email": current_user.email,
        "date_of_birth": profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None,
        "gender": profile.gender if profile else None,
        "resting_heart_rate": profile.resting_heart_rate if profile else None,
        "max_heart_rate": profile.max_heart_rate if profile else None,
        "threshold_heart_rate": profile.threshold_heart_rate if profile else None,
        "vo2_max": profile.vo2_max if profile else None,
        "strava_client_id": profile.strava_client_id if profile else None,
        "strava_client_secret": profile.strava_client_secret if profile else None,
        "strava_connected": strava_connected,
        "garmin_connected": garmin_connected,
        "garmin_email": garmin_email
    }


@router.put("/profile")
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.name = data.name
    
    profile = current_user.profile
    if not profile:
        from src.models.user import AthleteProfile
        profile = AthleteProfile(user_id=current_user.id)
        db.add(profile)
        
    profile.date_of_birth = data.date_of_birth
    profile.gender = data.gender
    profile.resting_heart_rate = data.resting_heart_rate
    profile.max_heart_rate = data.max_heart_rate
    profile.threshold_heart_rate = data.threshold_heart_rate
    profile.vo2_max = data.vo2_max
    profile.strava_client_id = data.strava_client_id
    profile.strava_client_secret = data.strava_client_secret
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Profile updated successfully",
        "user": {
            "name": current_user.name,
            "email": current_user.email
        }
    }
