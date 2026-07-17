from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
import enum
from app.db.database import Base
import uuid


class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AgentAction(Base):
    __tablename__ = "agent_actions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    agent_name = Column(String, nullable=False, index=True)
    action_type = Column(String, nullable=False)
    context = Column(JSON, default=dict)
    reasoning = Column(String, nullable=False)
    output = Column(JSON, default=dict)
    artifact_ids = Column(JSON, default=list)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=True)
    requires_human_approval = Column(Boolean, default=False)
    approval_status = Column(Enum(ApprovalStatus), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<AgentAction(id={self.id}, agent={self.agent_name}, type={self.action_type})>"