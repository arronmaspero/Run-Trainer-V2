import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Date, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models import Base

# A helper to support SQLite (where UUID type is not native, we fallback to String)
def get_uuid_type():
    return String(36)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    consent_status = Column(Boolean, default=False)

    # Relationships
    profile = relationship("AthleteProfile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    connected_accounts = relationship("ConnectedAccount", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("TrainingPlan", back_populates="user", cascade="all, delete-orphan")

class AthleteProfile(Base):
    __tablename__ = "athlete_profiles"

    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(50), nullable=True)
    resting_heart_rate = Column(Integer, nullable=True)
    max_heart_rate = Column(Integer, nullable=True)
    threshold_heart_rate = Column(Integer, nullable=True)
    vo2_max = Column(Float, nullable=True)
    weekly_volume_miles = Column(Float, nullable=False, default=0.0)
    runs_per_week = Column(Integer, nullable=False, default=3)
    long_run_day = Column(String(50), nullable=False, default="Sunday")
    unavailable_days = Column(String(255), nullable=True, default="") # Comma-separated list of weekdays
    injury_notes = Column(String(1000), nullable=True)
    strava_client_id = Column(String(255), nullable=True)
    strava_client_secret = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="profile")
