import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType
import logging

logger = logging.getLogger(__name__)


class NotionIntegration(BaseIntegration):
    """
    Notion Integration following three-phase pattern:
    1. OAuth 2.0 Authentication
    2. API polling (primary - Notion doesn't support webhooks)
    3. Normalization to standard artifact format with document chunking
    """
    
    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.NOTION
    
    @property
    def webhook_events(self) -> List[str]:
        # Notion doesn't support webhooks, this is for consistency
        return []
    
    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.base_url = "https://api.notion.com/v1"
        self._http_client = None
        self.chunk_size = 1000  # tokens
        self.chunk_overlap = 200  # tokens
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self._get_access_token()}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
            )
        return self._http_client
    
    def _get_access_token(self) -> str:
        """Get access token from credentials (synchronous for headers)"""
        # This is a simplified version - in production, cache this
        if self._credentials:
            return self._credentials.get('access_token', '')
        return ''
    
    async def authenticate(self) -> bool:
        """Validate Notion credentials using a test API call"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            if not access_token:
                logger.error("No access token in credentials")
                return False
            
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/users/me"
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Notion authentication successful for: {data.get('name', 'user')}")
                return True
            else:
                logger.error(f"Notion authentication failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Notion authentication failed: {e}")
            return False
    
    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """
        Notion doesn't support webhooks, this is a placeholder for consistency
        All data comes through polling
        """
        logger.warning("Notion integration uses polling only, not webhooks")
        return None
    
    async def _process_page(self, page_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process a single Notion page"""
        try:
            page_id = page_data.get('id')
            page_properties = page_data.get('properties', {})
            
            # Extract page title
            title = self._extract_page_title(page_properties)
            
            # Get page content
            page_content = await self._get_page_content(page_id)
            
            # Extract author (Notion doesn't track authors well, use owner)
            owner = page_data.get('created_by', {})
            author_name = owner.get('name', 'Unknown')
            author_email = owner.get('person', {}).get('email', '')
            
            # Extract last edited time
            last_edited = page_data.get('last_edited_time', '')
            
            # Build normalized content
            normalized_content = f"Page: {title}\n\n{page_content}"
            
            # Build metadata
            metadata = {
                'page_id': page_id,
                'page_title': title,
                'url': page_data.get('url'),
                'icon': page_data.get('icon'),
                'cover': page_data.get('cover'),
                'archived': page_data.get('archived', False),
                'parent_type': page_data.get('parent', {}).get('type'),
                'created_time': page_data.get('created_time'),
                'last_edited_time': last_edited
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.DOCUMENT,
                external_id=page_id,
                content=normalized_content,
                author=author_name,
                author_email=author_email,
                source_created_at=datetime.fromisoformat(last_edited.replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Notion page: {e}")
            return None
    
    def _extract_page_title(self, properties: Dict[str, Any]) -> str:
        """Extract title from page properties"""
        # Try to find title property
        for prop_name, prop_data in properties.items():
            if prop_data.get('type') == 'title':
                title_array = prop_data.get('title', [])
                if title_array:
                    return title_array[0].get('text', {}).get('content', 'Untitled')
        
        return 'Untitled'
    
    async def _get_page_content(self, page_id: str) -> str:
        """Get page content with text blocks"""
        try:
            client = await self._get_http_client()
            
            # Get page blocks
            blocks_response = await client.get(
                f"{self.base_url}/blocks/{page_id}/children"
            )
            
            if blocks_response.status_code != 200:
                logger.warning(f"Failed to get page blocks for {page_id}")
                return ''
            
            blocks_data = blocks_response.json()
            blocks = blocks_data.get('results', [])
            
            return self._extract_text_from_blocks(blocks)
            
        except Exception as e:
            logger.error(f"Error getting page content: {e}")
            return ''
    
    def _extract_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Extract text content from Notion blocks"""
        text_parts = []
        
        for block in blocks:
            block_type = block.get('type')
            block_content = block.get(block_type, {})
            
            # Extract text based on block type
            if block_type == 'paragraph':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                if text:
                    text_parts.append(text)
            
            elif block_type == 'heading_1':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                if text:
                    text_parts.append(f"# {text}")
            
            elif block_type == 'heading_2':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                if text:
                    text_parts.append(f"## {text}")
            
            elif block_type == 'heading_3':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                if text:
                    text_parts.append(f"### {text}")
            
            elif block_type == 'bulleted_list_item':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                if text:
                    text_parts.append(f"- {text}")
            
            elif block_type == 'numbered_list_item':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                if text:
                    text_parts.append(f"1. {text}")
            
            elif block_type == 'to_do':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                checked = block_content.get('checked', False)
                if text:
                    text_parts.append(f"- [{'x' if checked else ' '}] {text}")
            
            elif block_type == 'code':
                code = block_content.get('code', {}).get('rich_text', [])
                text = self._extract_rich_text(code)
                if text:
                    text_parts.append(f"```\n{text}\n```")
            
            elif block_type == 'quote':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                if text:
                    text_parts.append(f"> {text}")
            
            elif block_type == 'divider':
                text_parts.append("---")
            
            elif block_type == 'callout':
                text_array = block_content.get('text', [])
                text = self._extract_rich_text(text_array)
                if text:
                    text_parts.append(f"> {text}")
            
            # Handle child blocks recursively
            has_children = block.get('has_children', False)
            if has_children:
                # In a full implementation, you'd recursively fetch child blocks
                # For now, we'll note that children exist
                text_parts.append("[Child blocks not expanded]")
        
        return '\n\n'.join(text_parts)
    
    def _extract_rich_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
        """Extract plain text from Notion rich text array"""
        text_parts = []
        
        for text_item in rich_text_array:
            text_content = text_item.get('text', {}).get('content', '')
            annotations = text_item.get('annotations', {})
            
            # Apply basic formatting
            if annotations.get('code'):
                text_content = f"`{text_content}`"
            if annotations.get('bold'):
                text_content = f"**{text_content}**"
            if annotations.get('italic'):
                text_content = f"*{text_content}*"
            if annotations.get('strikethrough'):
                text_content = f"~~{text_content}~~"
            
            text_parts.append(text_content)
        
        return ''.join(text_parts)
    
    def _chunk_document(self, content: str) -> List[str]:
        """
        Chunk long documents into smaller segments for better embedding
        Uses overlap to maintain context between chunks
        """
        if not content:
            return []
        
        # Simple word-based chunking (in production, use proper tokenization)
        words = content.split()
        
        if len(words) <= self.chunk_size:
            return [content]
        
        chunks = []
        chunk_words = []
        overlap_words = []
        
        for word in words:
            chunk_words.append(word)
            
            if len(chunk_words) >= self.chunk_size:
                chunks.append(' '.join(chunk_words))
                
                # Keep overlap words for next chunk
                overlap_words = chunk_words[-self.chunk_overlap:]
                chunk_words = overlap_words.copy()
        
        # Add remaining words
        if chunk_words:
            chunks.append(' '.join(chunk_words))
        
        return chunks
    
    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """
        Poll for data using Notion API
        Fetches pages updated since the specified time
        Also used for initial backfill
        """
        try:
            client = await self._get_http_client()
            
            # Search for pages
            search_query = {
                "filter": {
                    "value": "page",
                    "property": "object"
                }
            }
            
            if since:
                search_query["filter"] = {
                    "value": since.isoformat(),
                    "property": "last_edited_time"
                }
            
            search_response = await client.post(
                f"{self.base_url}/search",
                json=search_query
            )
            
            if search_response.status_code != 200:
                logger.error(f"Failed to search Notion pages: {search_response.status_code}")
                return []
            
            search_data = search_response.json()
            pages = search_data.get('results', [])
            
            artifacts = []
            
            # Process each page
            for page in pages[:50]:  # Limit to 50 pages for performance
                artifact = await self._process_page(page)
                
                if artifact:
                    # Check if document needs chunking
                    content_length = len(artifact.content.split())
                    
                    if content_length > self.chunk_size:
                        # Chunk the document and create multiple artifacts
                        chunks = self._chunk_document(artifact.content)
                        
                        for i, chunk in enumerate(chunks):
                            chunk_metadata = artifact.metadata.copy()
                            chunk_metadata['chunk_index'] = i
                            chunk_metadata['total_chunks'] = len(chunks)
                            chunk_metadata['is_chunk'] = True
                            
                            chunked_artifact = NormalizedArtifact(
                                company_id=artifact.company_id,
                                source_tool=artifact.source_tool,
                                artifact_type=artifact.artifact_type,
                                external_id=f"{artifact.external_id}_chunk_{i}",
                                content=chunk,
                                author=artifact.author,
                                author_email=artifact.author_email,
                                source_created_at=artifact.source_created_at,
                                metadata=chunk_metadata
                            )
                            
                            artifacts.append(chunked_artifact)
                    else:
                        # No chunking needed
                        artifacts.append(artifact)
            
            logger.info(f"Polled {len(artifacts)} artifacts from Notion (including chunks)")
            return artifacts
            
        except Exception as e:
            logger.error(f"Notion data polling failed: {e}")
            return []
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """
        Normalize raw Notion event to standard artifact format
        This is a synchronous version used for testing
        """
        # For async operations, use process_webhook instead
        raise NotImplementedError("Use poll_data for Notion (no webhooks)")
    
    def get_oauth_url(self, redirect_uri: str) -> str:
        """Generate Notion OAuth URL"""
        from app.core.config import settings
        client_id = settings.NOTION_CLIENT_ID or self.settings.get('notion_client_id')
        
        return (
            f"https://api.notion.com/v1/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&owner=user"
        )
    
    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens"""
        try:
            from app.core.config import settings
            client_id = settings.NOTION_CLIENT_ID or self.settings.get('notion_client_id')
            client_secret = settings.NOTION_CLIENT_SECRET or self.settings.get('notion_client_secret')
            
            client = await self._get_http_client()
            response = await client.post(
                "https://api.notion.com/v1/oauth/token",
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
                'token_type': data.get('token_type'),
                'workspace_id': data.get('workspace_id'),
                'workspace_name': data.get('workspace_name'),
                'workspace_icon': data.get('workspace_icon'),
                'bot_id': data.get('bot_id'),
                'owner': data.get('owner')
            }
            
            logger.info(f"Successfully exchanged OAuth code for Notion workspace: {credentials.get('workspace_name')}")
            return credentials
            
        except Exception as e:
            logger.error(f"Notion OAuth exchange failed: {e}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
