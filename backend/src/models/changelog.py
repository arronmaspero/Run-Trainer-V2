import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.models import Base

class PlanChangeLog(Base):
    __tablename__ = "plan_changelog"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey("training_plans.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    change_type = Column(String(100), nullable=False) # e.g., drag_and_drop, ai_rebalance, injury_mode
    old_value_json = Column(String(4000), nullable=True)
    new_value_json = Column(String(4000), nullable=True)
    reason = Column(String(1000), nullable=True)
    is_ai_generated = Column(Boolean, default=False)
    is_user_approved = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    plan = relationship("TrainingPlan", back_populates="changelog")
    user = relationship("User")
