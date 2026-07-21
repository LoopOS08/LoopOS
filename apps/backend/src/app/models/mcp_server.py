from sqlalchemy import Column, String, DateTime, Enum, JSON, Integer, Boolean
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class MCPTransportType(enum.Enum):
    STDIO = "stdio"
    SSE = "sse"


class MCPServerStatus(enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    transport_type = Column(Enum(MCPTransportType), nullable=False, default=MCPTransportType.SSE)
    url = Column(String, nullable=True)
    command = Column(String, nullable=True)
    args = Column(JSON, default=list)
    auth_token = Column(String, nullable=True)
    enabled_tools = Column(JSON, default=list)
    discovered_tools = Column(JSON, default=list)
    status = Column(Enum(MCPServerStatus), default=MCPServerStatus.DISCONNECTED)
    polling_interval_minutes = Column(Integer, default=60)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<MCPServer(id={self.id}, name={self.name}, transport={self.transport_type})>"
