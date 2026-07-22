import httpx
import base64
import json
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType
import logging

logger = logging.getLogger(__name__)


class GmailPrivacyController:
    def __init__(self, settings: Dict[str, Any]):
        self.admin_emails: Set[str] = set(settings.get('authorized_accounts', []))
        self.opted_out: Set[str] = set(settings.get('opted_out_users', []))
        self.purge_raw_after_hours: int = settings.get('purge_raw_after_hours', 24)
        self.privacy_enabled: bool = settings.get('privacy_enabled', True)

    def is_account_authorized(self, email: str) -> bool:
        if not self.privacy_enabled:
            return True
        if not self.admin_emails:
            return True
        return email in self.admin_emails

    def is_user_opted_out(self, email: str) -> bool:
        return email in self.opted_out

    def should_process_email(self, email: str) -> bool:
        return self.is_account_authorized(email) and not self.is_user_opted_out(email)

    def redact_pii(self, content: str) -> str:
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        content = re.sub(email_pattern, '[email redacted]', content)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        content = re.sub(phone_pattern, '[phone redacted]', content)
        return content

    def get_privacy_metadata(self) -> Dict[str, Any]:
        return {
            'privacy_mode': 'enabled' if self.privacy_enabled else 'disabled',
            'purge_raw_after_hours': self.purge_raw_after_hours,
            'accounts_authorized': len(self.admin_emails),
            'users_opted_out': len(self.opted_out)
        }


class GmailIntegration(BaseIntegration):
    """Gmail Integration - three-phase pattern with privacy controls"""

    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.GMAIL

    @property
    def webhook_events(self) -> List[str]:
        return [
            'MESSAGE_ADDED',
            'MESSAGE_DELETED',
            'LABEL_ADDED',
            'LABEL_REMOVED'
        ]

    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.base_url = "https://gmail.googleapis.com/gmail/v1"
        self._http_client = None
        self.privacy = GmailPrivacyController(settings or {})

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def authenticate(self) -> bool:
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            if not access_token:
                logger.error("No access token in credentials")
                return False
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/users/me/profile",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 200:
                profile = response.json()
                email = profile.get('emailAddress', '')
                if not self.privacy.should_process_email(email):
                    logger.warning(f"Gmail account {email} not authorized or opted out")
                    return False
                logger.info(f"Gmail authentication successful for: {email}")
                return True
            logger.error(f"Gmail authentication failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False

    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        try:
            message = event_data.get('message', {})
            data_str = message.get('data')
            if not data_str:
                logger.warning("No data in Gmail webhook")
                return None
            decoded_data = base64.b64decode(data_str).decode('utf-8')
            notification = json.loads(decoded_data)
            email_address = notification.get('emailAddress')
            history_id = notification.get('historyId')

            if not self.privacy.should_process_email(email_address):
                logger.info(f"Gmail privacy filter: skipping {email_address}")
                return None

            return await self._fetch_and_process_message(email_address, history_id)
        except Exception as e:
            logger.error(f"Failed to process Gmail webhook: {e}")
            return None
    
    async def _fetch_and_process_message(self, email_address: str, history_id: str) -> Optional[NormalizedArtifact]:
        """Fetch message details and process"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            
            # Get history changes
            history_response = await client.get(
                f"{self.base_url}/users/me/history",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"startHistoryId": history_id}
            )
            
            if history_response.status_code != 200:
                logger.error(f"Failed to fetch Gmail history: {history_response.status_code}")
                return None
            
            history_data = history_response.json()
            history_records = history_data.get('history', [])
            
            if not history_records:
                return None
            
            # Process the most recent history record
            latest_history = history_records[0]
            messages_added = latest_history.get('messagesAdded', [])
            
            if not messages_added:
                return None
            
            # Process the first added message
            message_added = messages_added[0]
            message_id = message_added.get('message', {}).get('id')
            
            # Fetch full message details
            message_response = await client.get(
                f"{self.base_url}/users/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "full"}
            )
            
            if message_response.status_code != 200:
                logger.error(f"Failed to fetch Gmail message: {message_response.status_code}")
                return None
            
            message_data = message_response.json()
            return await self._process_message(message_data)
            
        except Exception as e:
            logger.error(f"Failed to fetch and process Gmail message: {e}")
            return None
    
    async def _process_message(self, message_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        try:
            headers = {}
            for header in message_data.get('payload', {}).get('headers', []):
                headers[header['name']] = header['value']
            
            subject = headers.get('Subject', '(no subject)')
            from_header = headers.get('From', '')
            to_header = headers.get('To', '')
            date_header = headers.get('Date', '')
            
            sender_name, sender_email = self._parse_email_address(from_header)
            recipients = self._parse_email_addresses(to_header)
            body = self._extract_message_body(message_data.get('payload', {}))
            message_date = self._parse_date(date_header)

            content = f"Email from {sender_name} ({sender_email}) to {', '.join(recipients)}: {subject}\n\n{body}"

            if self.privacy.privacy_enabled:
                content = self.privacy.redact_pii(content)
                logger.debug(f"PII redacted for message {message_data.get('id')}")

            metadata = {
                'message_id': message_data.get('id'),
                'thread_id': message_data.get('threadId'),
                'subject': subject,
                'from': from_header,
                'to': to_header,
                'cc': headers.get('Cc', ''),
                'bcc': headers.get('Bcc', ''),
                'labels': message_data.get('labelIds', []),
                'snippet': message_data.get('snippet', ''),
                'has_attachments': self._has_attachments(message_data.get('payload', {})),
                'privacy_applied': self.privacy.privacy_enabled,
                'purge_raw_after_hours': self.privacy.purge_raw_after_hours
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.EMAIL,
                external_id=message_data.get('id'),
                content=content,
                author=sender_name,
                author_email=sender_email,
                source_created_at=message_date,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Failed to process Gmail message: {e}")
            return None
    
    def _parse_email_address(self, email_string: str) -> tuple[str, str]:
        """Parse email address string into name and email"""
        if '<' in email_string and '>' in email_string:
            # Format: "Name <email@domain.com>"
            name_part = email_string[:email_string.index('<')].strip()
            email_part = email_string[email_string.index('<')+1:email_string.index('>')].strip()
            name = name_part.strip('"')
            return name, email_part
        else:
            # Just email address
            return '', email_string.strip()
    
    def _parse_email_addresses(self, email_string: str) -> List[str]:
        """Parse multiple email addresses"""
        if not email_string:
            return []
        
        addresses = []
        for addr in email_string.split(','):
            if '<' in addr and '>' in addr:
                email_part = addr[addr.index('<')+1:addr.index('>')].strip()
                addresses.append(email_part)
            else:
                addresses.append(addr.strip())
        
        return addresses
    
    def _extract_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload"""
        # Try to get body from main part
        body = payload.get('body', {}).get('data')
        if body:
            return base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
        
        # Try parts
        parts = payload.get('parts', [])
        for part in parts:
            # Try text/plain
            if part.get('mimeType') == 'text/plain':
                body = part.get('body', {}).get('data')
                if body:
                    return base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
            
            # Recursively check nested parts
            nested_body = self._extract_message_body(part)
            if nested_body:
                return nested_body
        
        return ''
    
    def _parse_date(self, date_string: str) -> datetime:
        """Parse RFC 2822 date string"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_string)
        except Exception as e:
            logger.warning(f"Failed to parse date: {date_string}")
            return datetime.utcnow()
    
    def _has_attachments(self, payload: Dict[str, Any]) -> bool:
        """Check if message has attachments"""
        parts = payload.get('parts', [])
        for part in parts:
            if part.get('filename'):
                return True
            # Check nested parts
            if self._has_attachments(part):
                return True
        return False
    
    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """
        Poll for missed data using Gmail History API
        Also used for initial backfill
        """
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            
            # Get current history ID if no since parameter
            if not since:
                profile_response = await client.get(
                    f"{self.base_url}/users/me/profile",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                profile_data = profile_response.json()
                current_history_id = profile_data.get('historyId')
                
                # Get history from 24 hours ago
                since = datetime.utcnow() - timedelta(hours=24)
            
            # List messages since the specified date
            messages_response = await client.get(
                f"{self.base_url}/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": f"after:{since.strftime('%Y/%m/%d')}",
                    "maxResults": 50
                }
            )
            
            messages_data = messages_response.json()
            messages = messages_data.get('messages', [])
            
            artifacts = []
            
            # Fetch and process each message
            for message_ref in messages:
                message_id = message_ref.get('id')
                
                message_response = await client.get(
                    f"{self.base_url}/users/me/messages/{message_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"format": "full"}
                )
                
                if message_response.status_code == 200:
                    message_data = message_response.json()
                    artifact = await self._process_message(message_data)
                    if artifact:
                        artifacts.append(artifact)
            
            logger.info(f"Polled {len(artifacts)} artifacts from Gmail")
            return artifacts
            
        except Exception as e:
            logger.error(f"Gmail data polling failed: {e}")
            return []
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """
        Normalize raw Gmail event to standard artifact format
        This is a synchronous version used for testing
        """
        # For async operations, use process_webhook instead
        raise NotImplementedError("Use process_webhook for async normalization")
    
    def get_oauth_url(self, redirect_uri: str) -> str:
        """Generate Google OAuth URL"""
        from app.core.config import settings
        client_id = settings.GOOGLE_CLIENT_ID or self.settings.get('google_client_id')
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar.readonly"
        ]
        
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={' '.join(scopes)}"
            f"&response_type=code"
            f"&access_type=offline"
            f"&prompt=consent"
        )
    
    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens"""
        try:
            from app.core.config import settings
            client_id = settings.GOOGLE_CLIENT_ID or self.settings.get('google_client_id')
            client_secret = settings.GOOGLE_CLIENT_SECRET or self.settings.get('google_client_secret')
            
            client = await self._get_http_client()
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            data = response.json()
            
            if 'error' in data:
                raise Exception(f"OAuth exchange failed: {data.get('error')}")
            
            credentials = {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'token_type': data.get('token_type'),
                'expires_in': data.get('expires_in'),
                'scope': data.get('scope')
            }
            
            logger.info("Successfully exchanged OAuth code for Gmail")
            return credentials
            
        except Exception as e:
            logger.error(f"Gmail OAuth exchange failed: {e}")
            raise
    
    async def refresh_credentials(self) -> bool:
        """Refresh Gmail access token using refresh token"""
        try:
            from app.core.config import settings
            credentials = await self.get_credentials()
            refresh_token = credentials.get('refresh_token')
            
            if not refresh_token:
                logger.warning("No refresh token available")
                return False
            
            client_id = settings.GOOGLE_CLIENT_ID or self.settings.get('google_client_id')
            client_secret = settings.GOOGLE_CLIENT_SECRET or self.settings.get('google_client_secret')
            
            client = await self._get_http_client()
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Token refresh failed: {data.get('error')}")
                return False
            
            # Update credentials with new access token
            credentials['access_token'] = data.get('access_token')
            credentials['expires_in'] = data.get('expires_in')
            
            # Re-encrypt and store updated credentials
            self._credentials = credentials
            # Note: In production, you'd update the database here
            
            logger.info("Successfully refreshed Gmail credentials")
            return True
            
        except Exception as e:
            logger.error(f"Gmail credential refresh failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
