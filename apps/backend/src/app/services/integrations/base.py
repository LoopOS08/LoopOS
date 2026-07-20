from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.integration import SourceTool, IntegrationStatus
from app.models.artifact import ArtifactType
from app.services.artifact_store import artifact_store_service
from app.services.encryption import encryption_service
import logging

logger = logging.getLogger(__name__)


@dataclass
class NormalizedArtifact:
    """Standardized artifact structure across all integrations"""
    company_id: str
    source_tool: SourceTool
    artifact_type: ArtifactType
    external_id: str
    content: str
    author: str
    author_email: str
    source_created_at: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'company_id': self.company_id,
            'source_tool': self.source_tool.value,
            'artifact_type': self.artifact_type.value,
            'external_id': self.external_id,
            'content': self.content,
            'author': self.author,
            'author_email': self.author_email,
            'source_created_at': self.source_created_at.isoformat(),
            'metadata': self.metadata
        }


class BaseIntegration(ABC):
    """
    Base class for all integrations following the three-phase pattern:
    1. Authentication
    2. Data Ingestion (webhook + poller)
    3. Normalization
    """
    
    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        self.company_id = company_id
        self.credentials_encrypted = credentials_encrypted
        self.settings = settings or {}
        self._credentials = None
        
    @property
    @abstractmethod
    def source_tool(self) -> SourceTool:
        """Return the source tool enum for this integration"""
        pass
    
    @property
    @abstractmethod
    def webhook_events(self) -> List[str]:
        """Return list of webhook events this integration handles"""
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Phase 1: Authentication
        Validate credentials and establish connection
        """
        pass
    
    @abstractmethod
    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """
        Phase 2: Data Ingestion (Primary - Webhook)
        Process incoming webhook event and return normalized artifact
        """
        pass
    
    @abstractmethod
    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """
        Phase 2: Data Ingestion (Secondary - Poller)
        Poll for missed or historical data
        """
        pass
    
    @abstractmethod
    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """
        Phase 3: Normalization
        Convert raw tool-specific event to normalized artifact
        """
        pass
    
    async def get_credentials(self) -> Dict[str, Any]:
        """
        Decrypt and cache credentials
        """
        if self._credentials is None:
            self._credentials = encryption_service.decrypt_credentials(self.credentials_encrypted)
        return self._credentials
    
    async def store_artifact(self, db: AsyncSession, artifact: NormalizedArtifact) -> bool:
        """
        Store normalized artifact in the artifact store
        Handles deduplication via external_id
        """
        try:
            # Check for existing artifact
            existing = await artifact_store_service.get_artifact_by_external_id(
                db, 
                artifact.company_id,
                artifact.source_tool,
                artifact.external_id
            )
            
            if existing:
                # Update existing artifact
                await artifact_store_service.update_artifact(
                    db,
                    existing,
                    content=artifact.content,
                    metadata=artifact.metadata
                )
                logger.info(f"Updated artifact {artifact.external_id} for {self.source_tool.value}")
            else:
                # Create new artifact
                await artifact_store_service.create_artifact(
                    db,
                    company_id=artifact.company_id,
                    source_tool=artifact.source_tool,
                    artifact_type=artifact.artifact_type,
                    external_id=artifact.external_id,
                    content=artifact.content,
                    author=artifact.author,
                    author_email=artifact.author_email,
                    source_created_at=artifact.source_created_at,
                    metadata=artifact.metadata
                )
                logger.info(f"Created artifact {artifact.external_id} for {self.source_tool.value}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to store artifact: {e}")
            return False
    
    async def handle_webhook(self, db: AsyncSession, event_data: Dict[str, Any]) -> bool:
        """
        Complete webhook handling pipeline
        """
        try:
            # Process webhook
            artifact = await self.process_webhook(event_data)
            
            if not artifact:
                logger.warning(f"Webhook processing returned no artifact for {self.source_tool.value}")
                return False
            
            # Store artifact
            return await self.store_artifact(db, artifact)
            
        except Exception as e:
            logger.error(f"Webhook handling failed for {self.source_tool.value}: {e}")
            return False
    
    async def sync_data(self, db: AsyncSession, since: Optional[datetime] = None) -> int:
        """
        Complete sync pipeline for polling
        Returns number of artifacts synced
        """
        try:
            # Poll for data
            artifacts = await self.poll_data(since)
            
            if not artifacts:
                logger.info(f"No new data to sync for {self.source_tool.value}")
                return 0
            
            # Store all artifacts
            success_count = 0
            for artifact in artifacts:
                if await self.store_artifact(db, artifact):
                    success_count += 1
            
            logger.info(f"Synced {success_count}/{len(artifacts)} artifacts for {self.source_tool.value}")
            return success_count
            
        except Exception as e:
            logger.error(f"Data sync failed for {self.source_tool.value}: {e}")
            return 0
    
    def validate_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """
        Validate webhook signature (override in implementations that support it)
        Default implementation returns True (no validation)
        """
        return True
    
    @abstractmethod
    def get_oauth_url(self, redirect_uri: str) -> str:
        """
        Generate OAuth URL for initial connection
        """
        pass
    
    @abstractmethod
    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange OAuth code for access/refresh tokens
        """
        pass
    
    async def refresh_credentials(self) -> bool:
        """
        Refresh OAuth tokens if needed (override in implementations)
        Default implementation returns True (no refresh needed)
        """
        return True
