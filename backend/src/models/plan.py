import uuid
from sqlalchemy import Column, String, Float, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.models import Base

class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    race_name = Column(String(255), nullable=True)
    race_date = Column(Date, nullable=True)
    race_distance_miles = Column(Float, nullable=False)
    target_time_seconds = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    style = Column(String(50), nullable=False, default="balanced") # conservative, balanced, ambitious
    status = Column(String(50), nullable=False, default="active") # active, completed, archived

    # Relationships
    user = relationship("User", back_populates="plans")
    sessions = relationship("TrainingSession", back_populates="plan", cascade="all, delete-orphan")
    changelog = relationship("PlanChangeLog", back_populates="plan", cascade="all, delete-orphan")
    weekly_evaluations = relationship("WeeklyEvaluation", back_populates="plan", cascade="all, delete-orphan")

class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey("training_plans.id"), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(50), nullable=False) # Easy, Recovery, Intervals, Tempo, Long Run, Strength, Rest
    name = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=0)
    distance_miles = Column(Float, nullable=True)
    warm_up_json = Column(String(1000), nullable=True)
    main_set_json = Column(String(1000), nullable=True)
    cool_down_json = Column(String(1000), nullable=True)
    target_pace_range = Column(String(50), nullable=True)
    target_hr_zone = Column(String(50), nullable=True)
    target_rpe = Column(Integer, nullable=True)
    garmin_instructions_text = Column(String(2000), nullable=True)
    status = Column(String(50), nullable=False, default="planned") # planned, completed, skipped

    # Relationships
    plan = relationship("TrainingPlan", back_populates="sessions")
    matched_activity = relationship("Activity", back_populates="session", uselist=False)

class WeeklyEvaluation(Base):
    __tablename__ = "weekly_evaluations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey("training_plans.id"), nullable=False)
    week_number = Column(Integer, nullable=False)
    commentary = Column(String(2000), nullable=False)

    # Relationships
    plan = relationship("TrainingPlan", back_populates="weekly_evaluations")

