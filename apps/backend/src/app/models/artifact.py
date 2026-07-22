from sqlalchemy import Column, String, DateTime, Enum, JSON, Float
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.integration import SourceTool
import enum
import uuid


class ArtifactType(enum.Enum):
    MESSAGE = "message"
    EMAIL = "email"
    TICKET = "ticket"
    DEAL = "deal"
    DOCUMENT = "document"
    COMMIT = "commit"
    CALL = "call"
    TRANSACTION = "transaction"
    MEETING = "meeting"
    REVIEW = "review"
    COMMENT = "comment"
    BUILD = "build"


class Artifact(Base):
    __tablename__ = "artifacts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, nullable=False, index=True)
    source_tool = Column(Enum(SourceTool), nullable=False, index=True)
    artifact_type = Column(Enum(ArtifactType), nullable=False, index=True)
    external_id = Column(String, nullable=False, index=True)
    content = Column(String, nullable=False)
    author = Column(String, nullable=False)
    author_email = Column(String, nullable=False)
    source_created_at = Column(DateTime(timezone=True), nullable=False)
    artifact_metadata = Column("metadata", JSON, default=dict)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Artifact(id={self.id}, type={self.artifact_type}, source={self.source_tool})>"