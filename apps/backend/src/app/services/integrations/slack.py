import httpx
import json
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType
import logging

logger = logging.getLogger(__name__)


class SlackIntegration(BaseIntegration):
    """
    Slack Integration following three-phase pattern:
    1. OAuth 2.0 Authentication
    2. Events API (webhook) + Web API (polling)
    3. Normalization to standard artifact format
    """
    
    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.SLACK
    
    @property
    def webhook_events(self) -> List[str]:
        return [
            'message',
            'reaction_added',
            'member_joined_channel',
            'app_mention',
            'file_shared',
            'thread_broadcast'
        ]
    
    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.base_url = "https://slack.com/api"
        self._http_client = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def authenticate(self) -> bool:
        """Validate Slack credentials using auth.test"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            if not access_token:
                logger.error("No access token in credentials")
                return False
            
            client = await self._get_http_client()
            response = await client.post(
                f"{self.base_url}/auth.test",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            data = response.json()
            
            if not data.get('ok'):
                logger.error(f"Slack auth.test failed: {data.get('error')}")
                return False
            
            logger.info(f"Slack authentication successful for team: {data.get('team')}")
            return True
            
        except Exception as e:
            logger.error(f"Slack authentication failed: {e}")
            return False
    
    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """
        Process Slack Events API webhook
        Handles: message, reaction_added, member_joined_channel, app_mention
        """
        try:
            event_type = event_data.get('type')
            event = event_data.get('event', {})
            
            # Handle URL verification challenge
            if event_type == 'url_verification':
                logger.info("Received Slack URL verification challenge")
                return None
            
            # Handle different event types
            if event_type == 'event_callback':
                inner_event = event_data.get('event', {})
                inner_event_type = inner_event.get('type')
                
                if inner_event_type == 'message':
                    return await self._process_message_event(inner_event)
                elif inner_event_type == 'reaction_added':
                    return await self._process_reaction_event(inner_event)
                elif inner_event_type == 'member_joined_channel':
                    return await self._process_member_joined_event(inner_event)
                elif inner_event_type == 'app_mention':
                    return await self._process_app_mention_event(inner_event)
                elif inner_event_type == 'file_shared':
                    return await self._process_file_shared_event(inner_event)
                else:
                    logger.debug(f"Unhandled Slack event type: {inner_event_type}")
                    return None
            
            logger.warning(f"Unknown Slack webhook structure: {event_type}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to process Slack webhook: {e}")
            return None
    
    async def _process_message_event(self, event: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Slack message event"""
        try:
            # Skip bot messages and messages without text
            if event.get('subtype') in ['bot_message', 'message_changed', 'message_deleted']:
                return None
            
            text = event.get('text', '')
            if not text:
                return None
            
            # Get user info
            user_id = event.get('user')
            user_info = await self._get_user_info(user_id)
            
            # Get channel info
            channel_id = event.get('channel')
            channel_info = await self._get_channel_info(channel_id)
            
            # Handle thread replies
            thread_ts = event.get('thread_ts')
            if thread_ts and thread_ts != event.get('ts'):
                parent_ts = thread_ts
                text = f"(thread reply) {text}"
            else:
                parent_ts = None
            
            # Build normalized content
            channel_name = channel_info.get('name', 'unknown')
            user_name = user_info.get('real_name', user_info.get('name', 'Unknown'))
            
            normalized_content = f"{user_name} said in #{channel_name}: {text}"
            
            # Build metadata
            metadata = {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'user_id': user_id,
                'timestamp': event.get('ts'),
                'thread_parent_ts': parent_ts,
                'subtype': event.get('subtype'),
                'reaction_count': len(event.get('reactions', []))
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.MESSAGE,
                external_id=event.get('ts'),  # Use timestamp as unique ID
                content=normalized_content,
                author=user_name,
                author_email=user_info.get('email', ''),
                source_created_at=datetime.fromtimestamp(float(event.get('ts'))),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Slack message event: {e}")
            return None
    
    async def _process_reaction_event(self, event: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Slack reaction_added event"""
        try:
            reaction = event.get('reaction')
            user_id = event.get('user')
            item = event.get('item')
            
            # Get user info
            user_info = await self._get_user_info(user_id)
            
            # Build normalized content
            user_name = user_info.get('real_name', user_info.get('name', 'Unknown'))
            normalized_content = f"{user_name} reacted with :{reaction}: to a message"
            
            # Build metadata
            metadata = {
                'reaction': reaction,
                'user_id': user_id,
                'item_type': item.get('type'),
                'item_channel': item.get('channel'),
                'item_ts': item.get('ts')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.MESSAGE,
                external_id=f"reaction_{event.get('event_ts')}",
                content=normalized_content,
                author=user_name,
                author_email=user_info.get('email', ''),
                source_created_at=datetime.fromtimestamp(float(event.get('event_ts'))),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Slack reaction event: {e}")
            return None
    
    async def _process_member_joined_event(self, event: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Slack member_joined_channel event"""
        try:
            user_id = event.get('user')
            channel_id = event.get('channel')
            
            # Get user and channel info
            user_info = await self._get_user_info(user_id)
            channel_info = await self._get_channel_info(channel_id)
            
            # Build normalized content
            user_name = user_info.get('real_name', user_info.get('name', 'Unknown'))
            channel_name = channel_info.get('name', 'unknown')
            normalized_content = f"{user_name} joined #{channel_name}"
            
            # Build metadata
            metadata = {
                'user_id': user_id,
                'channel_id': channel_id,
                'channel_name': channel_name,
                'inviter_id': event.get('inviter')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.MESSAGE,
                external_id=f"join_{event.get('event_ts')}",
                content=normalized_content,
                author=user_name,
                author_email=user_info.get('email', ''),
                source_created_at=datetime.fromtimestamp(float(event.get('event_ts'))),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Slack member joined event: {e}")
            return None
    
    async def _process_app_mention_event(self, event: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Slack app_mention event"""
        try:
            text = event.get('text', '')
            user_id = event.get('user')
            
            # Get user info
            user_info = await self._get_user_info(user_id)
            
            # Get channel info
            channel_id = event.get('channel')
            channel_info = await self._get_channel_info(channel_id)
            
            # Build normalized content
            channel_name = channel_info.get('name', 'unknown')
            user_name = user_info.get('real_name', user_info.get('name', 'Unknown'))
            normalized_content = f"{user_name} mentioned the app in #{channel_name}: {text}"
            
            # Build metadata
            metadata = {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'user_id': user_id,
                'timestamp': event.get('ts'),
                'mention_type': 'app_mention'
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.MESSAGE,
                external_id=f"mention_{event.get('ts')}",
                content=normalized_content,
                author=user_name,
                author_email=user_info.get('email', ''),
                source_created_at=datetime.fromtimestamp(float(event.get('ts'))),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Slack app mention event: {e}")
            return None
    
    async def _process_file_shared_event(self, event: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Slack file_shared event"""
        try:
            file_id = event.get('file_id')
            user_id = event.get('user')
            
            # Get file info
            file_info = await self._get_file_info(file_id)
            user_info = await self._get_user_info(user_id)
            
            # Build normalized content
            user_name = user_info.get('real_name', user_info.get('name', 'Unknown'))
            file_title = file_info.get('title', 'unknown')
            normalized_content = f"{user_name} shared a file: {file_title}"
            
            # Build metadata
            metadata = {
                'file_id': file_id,
                'file_title': file_title,
                'file_type': file_info.get('filetype'),
                'file_size': file_info.get('size'),
                'user_id': user_id,
                'timestamp': event.get('event_ts')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.MESSAGE,
                external_id=f"file_{event.get('event_ts')}",
                content=normalized_content,
                author=user_name,
                author_email=user_info.get('email', ''),
                source_created_at=datetime.fromtimestamp(float(event.get('event_ts'))),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Slack file shared event: {e}")
            return None
    
    async def _get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information from Slack API"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            response = await client.post(
                f"{self.base_url}/users.info",
                headers={"Authorization": f"Bearer {access_token}"},
                data={"user": user_id}
            )
            
            data = response.json()
            
            if data.get('ok'):
                return data.get('user', {})
            else:
                logger.warning(f"Failed to get user info for {user_id}: {data.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {}
    
    async def _get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information from Slack API"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            response = await client.post(
                f"{self.base_url}/conversations.info",
                headers={"Authorization": f"Bearer {access_token}"},
                data={"channel": channel_id}
            )
            
            data = response.json()
            
            if data.get('ok'):
                return data.get('channel', {})
            else:
                logger.warning(f"Failed to get channel info for {channel_id}: {data.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return {}
    
    async def _get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file information from Slack API"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            response = await client.post(
                f"{self.base_url}/files.info",
                headers={"Authorization": f"Bearer {access_token}"},
                data={"file": file_id}
            )
            
            data = response.json()
            
            if data.get('ok'):
                return data.get('file', {})
            else:
                logger.warning(f"Failed to get file info for {file_id}: {data.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return {}
    
    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """
        Poll for missed data using Slack Web API
        Also used for initial history backfill
        """
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            
            # Get list of conversations
            conversations_response = await client.post(
                f"{self.base_url}/conversations.list",
                headers={"Authorization": f"Bearer {access_token}"},
                data={"types": "public_channel,private_channel,mpim,im"}
            )
            
            conversations_data = conversations_response.json()
            
            if not conversations_data.get('ok'):
                logger.error(f"Failed to get conversations: {conversations_data.get('error')}")
                return []
            
            artifacts = []
            channels = conversations_data.get('channels', [])
            
            # Poll each channel for new messages
            for channel in channels[:20]:  # Limit to 20 channels for performance
                channel_id = channel.get('id')
                
                # Get conversation history
                history_params = {
                    "channel": channel_id,
                    "limit": 100
                }
                
                if since:
                    # Convert to Unix timestamp
                    history_params["oldest"] = since.timestamp()
                
                history_response = await client.post(
                    f"{self.base_url}/conversations.history",
                    headers={"Authorization": f"Bearer {access_token}"},
                    data=history_params
                )
                
                history_data = history_response.json()
                
                if history_data.get('ok'):
                    messages = history_data.get('messages', [])
                    
                    for message in messages:
                        # Process each message
                        event = {
                            'type': 'message',
                            'ts': message.get('ts'),
                            'user': message.get('user'),
                            'text': message.get('text'),
                            'channel': channel_id,
                            'subtype': message.get('subtype'),
                            'thread_ts': message.get('thread_ts'),
                            'reactions': message.get('reactions', [])
                        }
                        
                        artifact = await self._process_message_event(event)
                        if artifact:
                            artifacts.append(artifact)
            
            logger.info(f"Polled {len(artifacts)} artifacts from Slack")
            return artifacts
            
        except Exception as e:
            logger.error(f"Slack data polling failed: {e}")
            return []
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """
        Normalize raw Slack event to standard artifact format
        This is a synchronous version used for testing
        """
        # For async operations, use process_webhook instead
        raise NotImplementedError("Use process_webhook for async normalization")
    
    def get_oauth_url(self, redirect_uri: str) -> str:
        """Generate Slack OAuth URL"""
        from app.core.config import settings
        client_id = settings.SLACK_CLIENT_ID or self.settings.get('slack_client_id')
        scopes = "channels:history,channels:read,users:read,reactions:read,chat:write,files:read"
        
        return (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}"
            f"&scope={scopes}"
            f"&redirect_uri={redirect_uri}"
        )
    
    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens"""
        try:
            from app.core.config import settings
            client_id = settings.SLACK_CLIENT_ID or self.settings.get('slack_client_id')
            client_secret = settings.SLACK_CLIENT_SECRET or self.settings.get('slack_client_secret')
            
            client = await self._get_http_client()
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            
            data = response.json()
            
            if not data.get('ok'):
                raise Exception(f"OAuth exchange failed: {data.get('error')}")
            
            credentials = {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'team_id': data.get('team').get('id'),
                'team_name': data.get('team').get('name'),
                'token_type': data.get('token_type'),
                'scope': data.get('scope')
            }
            
            logger.info(f"Successfully exchanged OAuth code for Slack team: {credentials.get('team_name')}")
            return credentials
            
        except Exception as e:
            logger.error(f"Slack OAuth exchange failed: {e}")
            raise
    
    def validate_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """
        Validate Slack webhook signature
        """
        try:
            from app.core.config import settings
            signing_secret = settings.SLACK_SIGNING_SECRET or self.settings.get('slack_signing_secret')
            
            if not signing_secret:
                logger.warning("No Slack signing secret configured")
                return False
            
            # Split signature into version and hash
            version, hash_value = signature.split('=', 1)
            
            # Create expected hash
            expected_hash = hmac.new(
                signing_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare hashes
            is_valid = hmac.compare_digest(expected_hash, hash_value)
            
            if not is_valid:
                logger.warning("Invalid Slack webhook signature")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Slack signature validation failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
