from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base
import uuid


class Decision(Base):
    __tablename__ = "decisions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    artifact_id = Column(String, ForeignKey("artifacts.id"), nullable=False)
    content = Column(String, nullable=False)
    decision_maker = Column(String, nullable=False)
    decision_date = Column(DateTime(timezone=True), nullable=False)
    outcome = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Decision(id={self.id}, maker={self.decision_maker})>"