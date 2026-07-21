from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import hmac
import json
import logging
from uuid import uuid4
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType

logger = logging.getLogger(__name__)


class ZapierBridgeIntegration(BaseIntegration):
    """
    Zapier/Make Bridge - Receives webhook events from Zapier and Make (formerly Integromat).
    
    Zapier and Make can connect to 5,000+ apps. This bridge lets users configure
    a webhook URL in Zapier/Make that sends events to LoopOS, which are then
    normalized into artifacts and routed through the agent pipeline.
    """

    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.webhook_secret = settings.get('webhook_secret', '') if settings else ''
        self.default_artifact_type_str = settings.get('artifact_type', 'message') if settings else 'message'

    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.ZAPIER

    @property
    def webhook_events(self) -> List[str]:
        return ['hook.trigger', 'hook.fire']

    @property
    def is_make(self) -> bool:
        """Check if this is configured for Make (vs Zapier)"""
        return (self.settings or {}).get('platform', '').lower() == 'make'

    def validate_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """Validate webhook signature using HMAC-SHA256"""
        if not self.webhook_secret:
            return True  # No validation configured
        try:
            expected = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(f'sha256={expected}', signature)
        except Exception as e:
            logger.error(f"Webhook signature validation failed: {e}")
            return False

    async def authenticate(self) -> bool:
        """Zapier/Make bridge is always authenticated if configured"""
        return bool(self.webhook_secret)

    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process incoming webhook event from Zapier or Make"""
        try:
            return self.normalize_event(event_data)
        except Exception as e:
            logger.error(f"Failed to process webhook event: {e}")
            return None

    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """Zapier/Make bridge doesn't poll - it's purely webhook-driven"""
        return []

    def _determine_artifact_type(self, event_data: Dict[str, Any]) -> ArtifactType:
        """Determine the artifact type from the event data"""
        event_type = event_data.get('type', '') or event_data.get('event', '') or ''
        event_type_lower = event_type.lower()

        type_mapping = {
            'message': ArtifactType.MESSAGE,
            'email': ArtifactType.EMAIL,
            'ticket': ArtifactType.TICKET,
            'deal': ArtifactType.DEAL,
            'document': ArtifactType.DOCUMENT,
            'commit': ArtifactType.COMMIT,
            'call': ArtifactType.CALL,
            'transaction': ArtifactType.TRANSACTION,
            'meeting': ArtifactType.MEETING,
            'review': ArtifactType.REVIEW,
            'comment': ArtifactType.COMMENT,
            'build': ArtifactType.BUILD,
        }

        for key, artifact_type in type_mapping.items():
            if key in event_type_lower:
                return artifact_type

        return ArtifactType(self.default_artifact_type_str)

    def _detect_source_tool(self, event_data: Dict[str, Any]) -> SourceTool:
        """Detect the original source tool from Zapier/Make metadata"""
        source = event_data.get('source_tool', '') or event_data.get('source', '') or ''
        fields = event_data.get('fields', {}) or {}

        app_name = (
            source.lower()
            or fields.get('app_name', '').lower()
            or event_data.get('app', '').lower()
        )

        source_mapping = {
            'slack': SourceTool.SLACK,
            'gmail': SourceTool.GMAIL,
            'hubspot': SourceTool.HUBSPOT,
            'linear': SourceTool.LINEAR,
            'notion': SourceTool.NOTION,
            'github': SourceTool.GITHUB,
            'stripe': SourceTool.STRIPE,
            'zoom': SourceTool.ZOOM,
            'google_drive': SourceTool.GOOGLE_DRIVE,
            'jira': SourceTool.JIRA,
            'salesforce': SourceTool.SALESFORCE,
            'teams': SourceTool.TEAMS,
            'asana': SourceTool.ASANA,
            'quickbooks': SourceTool.QUICKBOOKS,
            'intercom': SourceTool.INTERCOM,
            'make': SourceTool.MAKE,
        }

        for key, tool in source_mapping.items():
            if key in app_name:
                return tool

        return SourceTool.MAKE if self.is_make else SourceTool.ZAPIER

    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """Convert Zapier/Make event to NormalizedArtifact"""
        data = raw_event.get('data', raw_event)
        fields = data.get('fields', data) if isinstance(data, dict) else data

        if isinstance(fields, dict):
            content = (
                fields.get('content')
                or fields.get('text')
                or fields.get('description')
                or fields.get('body')
                or fields.get('message')
                or json.dumps(raw_event)
            )
            author = (
                fields.get('author')
                or fields.get('sender')
                or fields.get('created_by')
                or fields.get('name')
                or 'zapier-bridge'
            )
            author_email = (
                fields.get('author_email')
                or fields.get('email')
                or fields.get('sender_email')
                or 'zapier@loopos.internal'
            )
            external_id = (
                fields.get('id')
                or fields.get('external_id')
                or fields.get('event_id')
                or str(uuid4())
            )
            timestamp_str = (
                fields.get('timestamp')
                or fields.get('date')
                or fields.get('created_at')
                or fields.get('source_created_at')
                or ''
            )
        else:
            content = str(fields)
            author = 'zapier-bridge'
            author_email = 'zapier@loopos.internal'
            external_id = str(uuid4())
            timestamp_str = ''

        try:
            source_created_at = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.utcnow()
        except (ValueError, TypeError):
            source_created_at = datetime.utcnow()

        artifact_type = self._determine_artifact_type(raw_event)
        detected_source = self._detect_source_tool(raw_event)

        return NormalizedArtifact(
            company_id=self.company_id,
            source_tool=detected_source,
            artifact_type=artifact_type,
            external_id=str(external_id),
            content=str(content),
            author=str(author),
            author_email=str(author_email),
            source_created_at=source_created_at,
            metadata={
                'platform': 'make' if self.is_make else 'zapier',
                'raw_event': raw_event
            }
        )

    def get_oauth_url(self, redirect_uri: str) -> str:
        raise NotImplementedError("Zapier/Make bridge uses webhook configuration, not OAuth")

    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        raise NotImplementedError("Zapier/Make bridge uses webhook configuration, not OAuth")
