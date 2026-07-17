from sqlalchemy import Column, String, DateTime, Enum, Float, ForeignKey
from sqlalchemy.sql import func
import enum
from app.db.database import Base
import uuid


class GoalOperator(enum.Enum):
    LESS_THAN = "less_than"
    GREATER_THAN = "greater_than"
    EQUAL_TO = "equal_to"


class GoalStatus(enum.Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"


class Goal(Base):
    __tablename__ = "goals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    metric_name = Column(String, nullable=False)
    target_value = Column(Float, nullable=False)
    operator = Column(Enum(GoalOperator), nullable=False)
    current_value = Column(Float, nullable=False)
    status = Column(Enum(GoalStatus), default=GoalStatus.ON_TRACK)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Goal(id={self.id}, metric={self.metric_name}, status={self.status})>"