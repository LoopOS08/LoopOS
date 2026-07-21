from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
from uuid import uuid4
import httpx
from jsonpath_ng import parse as jsonpath_parse
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType
from app.models.rest_connector import RESTConnector, RESTAuthType

logger = logging.getLogger(__name__)


class RESTConnectorIntegration(BaseIntegration):
    """
    Generic REST API Connector - Polls any REST API and normalizes responses into artifacts.
    
    Users configure:
    - URL, HTTP method, headers
    - Auth type (None, API Key, Basic, Bearer, OAuth2)
    - JSONPath expressions to extract fields from the response
    - Pagination configuration
    - Polling interval
    """

    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.connector_config: Optional[RESTConnector] = None
        self._client = None

    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.REST_API

    @property
    def webhook_events(self) -> List[str]:
        return []

    def configure(self, connector: RESTConnector):
        """Set the REST connector configuration"""
        self.connector_config = connector

    async def _get_client(self) -> httpx.AsyncClient:
        """Create authenticated HTTP client based on connector config"""
        if self._client:
            return self._client

        if not self.connector_config:
            raise ValueError("REST connector not configured")

        headers = dict(self.connector_config.headers or {})

        auth_type = self.connector_config.auth_type
        auth_config = self.connector_config.auth_config or {}

        if auth_type == RESTAuthType.API_KEY:
            key_header = auth_config.get('header_name', 'X-API-Key')
            key_value = auth_config.get('api_key', '')
            headers[key_header] = key_value

        elif auth_type == RESTAuthType.BASIC:
            username = auth_config.get('username', '')
            password = auth_config.get('password', '')
            auth = httpx.BasicAuth(username, password)

        elif auth_type == RESTAuthType.BEARER:
            token = auth_config.get('token', '')
            headers['Authorization'] = f'Bearer {token}'

        elif auth_type == RESTAuthType.OAUTH2_CLIENT_CREDENTIALS:
            token_url = auth_config.get('token_url', '')
            client_id = auth_config.get('client_id', '')
            client_secret = auth_config.get('client_secret', '')
            scope = auth_config.get('scope', '')

            async with httpx.AsyncClient() as token_client:
                token_data = {
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret,
                }
                if scope:
                    token_data['scope'] = scope

                token_resp = await token_client.post(token_url, data=token_data)
                if token_resp.status_code == 200:
                    token_json = token_resp.json()
                    access_token = token_json.get('access_token', '')
                    headers['Authorization'] = f'Bearer {access_token}'

        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            follow_redirects=True
        )
        return self._client

    async def _extract_field(self, data: Any, jsonpath_expr: str, default: Any = '') -> Any:
        """Extract a field from data using JSONPath expression"""
        if not jsonpath_expr:
            return default
        try:
            expr = jsonpath_parse(jsonpath_expr)
            matches = expr.find(data)
            if matches:
                return matches[0].value
            return default
        except Exception as e:
            logger.warning(f"JSONPath extraction failed for '{jsonpath_expr}': {e}")
            return default

    async def _extract_items(self, data: Any, jsonpath_expr: str) -> List[Any]:
        """Extract a list of items from data using JSONPath"""
        if not jsonpath_expr:
            return [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
        try:
            expr = jsonpath_parse(jsonpath_expr)
            matches = expr.find(data)
            if matches:
                return matches[0].value if isinstance(matches[0].value, list) else [matches[0].value]
            return []
        except Exception as e:
            logger.warning(f"JSONPath items extraction failed for '{jsonpath_expr}': {e}")
            return [data] if isinstance(data, dict) else []

    async def _get_next_page_url(self, response: httpx.Response, data: Any) -> Optional[str]:
        """Extract next page URL from response"""
        pagination = self.connector_config.pagination or {}
        strategy = pagination.get('strategy', 'none')

        if strategy == 'link_header':
            link_header = response.headers.get('link', '')
            if 'rel="next"' in link_header:
                for part in link_header.split(','):
                    if 'rel="next"' in part:
                        url_part = part.split(';')[0].strip().strip('<>')
                        return url_part

        elif strategy == 'jsonpath':
            next_url_expr = pagination.get('next_url_path', '')
            if next_url_expr:
                return await self._extract_field(data, next_url_expr)

        elif strategy == 'cursor':
            cursor_param = pagination.get('cursor_param', 'cursor')
            cursor_expr = pagination.get('cursor_path', '')
            cursor = await self._extract_field(data, cursor_expr)
            if cursor:
                from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
                parsed = list(urlparse(str(response.url)))
                params = parse_qs(parsed[4])
                params[cursor_param] = [str(cursor)]
                parsed[4] = urlencode(params, doseq=True)
                return urlunparse(parsed)

        return None

    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """Poll the REST API and normalize responses"""
        artifacts = []
        if not self.connector_config:
            logger.warning("REST connector not configured")
            return artifacts

        try:
            client = await self._get_client()
            url = self.connector_config.url
            method = self.connector_config.method.upper()
            field_mappings = self.connector_config.field_mappings or {}

            while url:
                if method == 'GET':
                    response = await client.get(url)
                elif method == 'POST':
                    response = await client.post(url, json=self.connector_config.settings.get('body', {}))
                elif method == 'PUT':
                    response = await client.put(url, json=self.connector_config.settings.get('body', {}))
                else:
                    response = await client.get(url)

                if response.status_code != 200:
                    logger.error(f"REST API returned {response.status_code} for {url}")
                    break

                data = response.json()

                items_path = field_mappings.get('items_path', '')
                items = await self._extract_items(data, items_path) if items_path else [data]

                for i, item in enumerate(items):
                    if not isinstance(item, dict):
                        continue

                    content = await self._extract_field(
                        item, field_mappings.get('content_path', ''), json.dumps(item, indent=2)
                    )
                    external_id = await self._extract_field(
                        item, field_mappings.get('id_path', ''), str(uuid4())
                    )
                    author = await self._extract_field(
                        item, field_mappings.get('author_path', ''), 'rest-api'
                    )
                    author_email = await self._extract_field(
                        item, field_mappings.get('email_path', ''), 'rest-api@loopos.internal'
                    )
                    timestamp_str = await self._extract_field(
                        item, field_mappings.get('timestamp_path', ''), ''
                    )

                    try:
                        source_created_at = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.utcnow()
                    except (ValueError, TypeError):
                        source_created_at = datetime.utcnow()

                    artifact_type_str = field_mappings.get('artifact_type', 'message')

                    try:
                        artifact_type = ArtifactType(artifact_type_str)
                    except ValueError:
                        artifact_type = ArtifactType.MESSAGE

                    artifact = NormalizedArtifact(
                        company_id=self.company_id,
                        source_tool=SourceTool.REST_API,
                        artifact_type=artifact_type,
                        external_id=str(external_id),
                        content=str(content),
                        author=str(author),
                        author_email=str(author_email),
                        source_created_at=source_created_at,
                        metadata={
                            'connector_name': self.connector_config.name,
                            'url': url,
                            'method': method,
                            'raw_item': item
                        }
                    )
                    artifacts.append(artifact)

                url = await self._get_next_page_url(response, data)

            logger.info(f"Polled {len(artifacts)} artifacts from REST API {self.connector_config.name}")
            return artifacts

        except Exception as e:
            logger.error(f"REST API poll failed for {self.connector_config.name if self.connector_config else 'unknown'}: {e}")
            return artifacts

    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """Normalize a raw REST event"""
        return NormalizedArtifact(
            company_id=self.company_id,
            source_tool=SourceTool.REST_API,
            artifact_type=ArtifactType.MESSAGE,
            external_id=raw_event.get('id', str(uuid4())),
            content=json.dumps(raw_event.get('data', raw_event), indent=2),
            author=raw_event.get('author', 'rest-api'),
            author_email=raw_event.get('author_email', 'rest-api@loopos.internal'),
            source_created_at=datetime.utcnow(),
            metadata=raw_event
        )

    async def authenticate(self) -> bool:
        """Verify REST API connection is valid"""
        try:
            if not self.connector_config:
                return False
            client = await self._get_client()
            response = await client.head(self.connector_config.url)
            return response.status_code < 500
        except Exception as e:
            logger.error(f"REST API authentication failed: {e}")
            return False

    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        return self.normalize_event(event_data)

    def get_oauth_url(self, redirect_uri: str) -> str:
        raise NotImplementedError("REST connector uses direct configuration, not OAuth")

    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        raise NotImplementedError("REST connector uses direct configuration, not OAuth")

    async def test_connection(self) -> Dict[str, Any]:
        """Test the REST API connection and return sample data"""
        try:
            client = await self._get_client()
            url = self.connector_config.url
            method = self.connector_config.method.upper()

            if method == 'GET':
                response = await client.get(url)
            elif method == 'POST':
                response = await client.post(url, json=self.connector_config.settings.get('body', {}))
            else:
                response = await client.get(url)

            return {
                'success': response.status_code < 500,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'sample_data': response.json() if response.status_code < 500 else response.text[:1000]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
