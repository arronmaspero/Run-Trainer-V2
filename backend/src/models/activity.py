import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.models import Base

class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False, default="strava")
    access_token = Column(String(255), nullable=False)
    refresh_token = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    scopes = Column(String(255), nullable=True)
    last_sync_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="connected_accounts")

class Activity(Base):
    __tablename__ = "activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    strava_activity_id = Column(String(100), unique=True, nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=True)  # Activity name from Strava e.g. "Morning Run"
    type = Column(String(50), nullable=False, default="run")
    start_date = Column(DateTime, nullable=False)
    distance_miles = Column(Float, nullable=False)
    moving_time_seconds = Column(Integer, nullable=False)
    elapsed_time_seconds = Column(Integer, nullable=False)
    elevation_gain_feet = Column(Float, nullable=False, default=0.0)
    average_heart_rate = Column(Integer, nullable=True)
    average_cadence = Column(Float, nullable=True)
    splits_json = Column(String(4000), nullable=True) # JSON details of splits/laps
    gps_polyline = Column(String(4000), nullable=True) # Encoded polyline GPS path
    matched_session_id = Column(String(36), ForeignKey("training_sessions.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="activities")
    session = relationship("TrainingSession", back_populates="matched_activity", foreign_keys=[matched_session_id])
