from sqlalchemy import Column, String, DateTime, Enum, JSON, Integer
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class RESTAuthType(enum.Enum):
    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER = "bearer"
    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"


class RESTConnectorStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class RESTConnector(Base):
    __tablename__ = "rest_connectors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    method = Column(String, default="GET")
    headers = Column(JSON, default=dict)
    auth_type = Column(Enum(RESTAuthType), default=RESTAuthType.NONE)
    auth_config = Column(JSON, default=dict)
    field_mappings = Column(JSON, nullable=False)
    pagination = Column(JSON, default=dict)
    polling_interval_minutes = Column(Integer, default=60)
    status = Column(Enum(RESTConnectorStatus), default=RESTConnectorStatus.PAUSED)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<RESTConnector(id={self.id}, name={self.name}, url={self.url})>"
