from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.sql import func
import enum
from app.db.database import Base
import uuid


class Priority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Spec(Base):
    __tablename__ = "specs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    decision_id = Column(String, ForeignKey("decisions.id"), nullable=False)
    title = Column(String, nullable=False)
    context = Column(String, nullable=False)
    acceptance_criteria = Column(JSON, default=list)
    dependencies = Column(JSON, default=list)
    estimated_effort = Column(String, nullable=False)
    suggested_assignee = Column(String, nullable=False)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    external_ticket_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Spec(id={self.id}, title={self.title}, priority={self.priority})>"