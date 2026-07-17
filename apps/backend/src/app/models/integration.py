from sqlalchemy import Column, String, DateTime, Enum, JSON
from sqlalchemy.sql import func
import enum
from app.db.database import Base
import uuid


class SourceTool(enum.Enum):
    SLACK = "slack"
    GMAIL = "gmail"
    HUBSPOT = "hubspot"
    LINEAR = "linear"
    NOTION = "notion"
    GITHUB = "github"
    STRIPE = "stripe"
    ZOOM = "zoom"
    GOOGLE_DRIVE = "google_drive"
    JIRA = "jira"
    SALESFORCE = "salesforce"
    TEAMS = "teams"
    ASANA = "asana"
    QUICKBOOKS = "quickbooks"
    INTERCOM = "intercom"


class IntegrationStatus(enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class Integration(Base):
    __tablename__ = "integrations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    source_tool = Column(Enum(SourceTool), nullable=False)
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.DISCONNECTED)
    credentials_encrypted = Column(String, nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Integration(id={self.id}, tool={self.source_tool}, status={self.status})>"