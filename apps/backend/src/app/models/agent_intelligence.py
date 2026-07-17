from sqlalchemy import Column, String, DateTime, JSON, Float
from sqlalchemy.sql import func
from app.db.database import Base
import uuid


class AgentIntelligence(Base):
    __tablename__ = "agent_intelligence"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    agent_name = Column(String, nullable=False, index=True)
    successful_patterns = Column(JSON, default=dict)
    failed_patterns = Column(JSON, default=dict)
    success_rate = Column(Float, default=0.0)
    sample_size = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<AgentIntelligence(id={self.id}, agent={self.agent_name}, success_rate={self.success_rate})>"