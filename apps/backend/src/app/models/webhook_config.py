from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.db.database import Base
import uuid


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    source_tool = Column(String, nullable=False)
    webhook_secret = Column(String, nullable=False)
    webhook_url_path = Column(String, nullable=False, unique=True)
    artifact_type = Column(String, default="message")
    enabled = Column(Boolean, default=True)
    last_event_at = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<WebhookConfig(id={self.id}, tool={self.source_tool}, company={self.company_id})>"
