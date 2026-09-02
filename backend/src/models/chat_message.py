import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.models import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey("training_plans.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    sender = Column(String(20), nullable=False) # 'user' or 'coach'
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    proposed_changes_json = Column(Text, nullable=True) # JSON payload of concrete session changes if coach proposed plan updates

    # Relationships
    plan = relationship("TrainingPlan")
    user = relationship("User")
