from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from app.db.database import Base
import uuid


class Outcome(Base):
    __tablename__ = "outcomes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    agent_action_id = Column(String, ForeignKey("agent_actions.id"), nullable=False)
    goal_metric_before = Column(Float, nullable=False)
    goal_metric_after = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False)
    human_feedback = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Outcome(id={self.id}, success={self.success}, delta={self.delta})>"