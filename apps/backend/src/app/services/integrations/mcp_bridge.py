from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
import asyncio
import subprocess
from uuid import uuid4
import httpx
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType
from app.models.mcp_server import MCPServer, MCPTransportType, MCPServerStatus

logger = logging.getLogger(__name__)


class MCPBridgeIntegration(BaseIntegration):
    """
    MCP Server Bridge - Connects to any MCP server and ingests data via Model Context Protocol.
    
    Supports both stdio (subprocess) and SSE (server-sent-events) transports.
    Discovers available tools/resources and normalizes data into LoopOS artifacts.
    """

    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.server_id = settings.get('server_id') if settings else None
        self.server_config: Optional[MCPServer] = None
        self._client = None
        self._session = None

    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.MCP

    @property
    def webhook_events(self) -> List[str]:
        return ['resource_updated', 'tool_executed']

    async def connect(self, server: MCPServer) -> bool:
        """Connect to an MCP server"""
        self.server_config = server
        try:
            if server.transport_type == MCPTransportType.STDIO:
                return await self._connect_stdio(server)
            else:
                return await self._connect_sse(server)
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {server.name}: {e}")
            return False

    async def _connect_stdio(self, server: MCPServer) -> bool:
        """Connect via stdio transport (subprocess)"""
        try:
            cmd = [server.command]
            if server.args:
                cmd.extend(server.args)
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Connected to MCP server {server.name} via stdio")
            return True
        except Exception as e:
            logger.error(f"Stdio connection failed for {server.name}: {e}")
            return False

    async def _connect_sse(self, server: MCPServer) -> bool:
        """Connect via SSE transport (HTTP)"""
        try:
            headers = {}
            if server.auth_token:
                headers['Authorization'] = f'Bearer {server.auth_token}'
            
            self._client = httpx.AsyncClient(
                base_url=server.url,
                headers=headers,
                timeout=30.0
            )
            
            health = await self._client.get('/health')
            if health.status_code != 200:
                logger.warning(f"MCP server {server.name} health check returned {health.status_code}")
            
            logger.info(f"Connected to MCP server {server.name} via SSE at {server.url}")
            return True
        except Exception as e:
            logger.error(f"SSE connection failed for {server.name}: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MCP server"""
        if hasattr(self, '_process') and self._process:
            self._process.terminate()
            await self._process.wait()
        if self._client:
            await self._client.aclose()
        logger.info(f"Disconnected from MCP server {self.server_config.name if self.server_config else 'unknown'}")

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools and resources from MCP server"""
        tools = []
        try:
            if self._client:
                response = await self._client.get('/tools')
                if response.status_code == 200:
                    tools = response.json().get('tools', [])
            
            resources = await self._discover_resources()
            
            return {
                'tools': tools,
                'resources': resources
            }
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            return {'tools': [], 'resources': []}

    async def _discover_resources(self) -> List[Dict[str, Any]]:
        """Discover available resources"""
        try:
            if self._client:
                response = await self._client.get('/resources')
                if response.status_code == 200:
                    return response.json().get('resources', [])
            return []
        except Exception as e:
            logger.error(f"Failed to discover resources: {e}")
            return []

    async def fetch_resource(self, resource_uri: str) -> Optional[NormalizedArtifact]:
        """Fetch a specific resource and normalize it"""
        try:
            if not self._client:
                logger.warning("Not connected to MCP server")
                return None
            
            response = await self._client.get(
                '/resources/fetch',
                params={'uri': resource_uri}
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch resource {resource_uri}: {response.status_code}")
                return None
            
            data = response.json()
            return self.normalize_event({
                'resource_uri': resource_uri,
                'data': data.get('data', data),
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to fetch resource {resource_uri}: {e}")
            return None

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Execute a tool and normalize the result"""
        try:
            if not self._client:
                logger.warning("Not connected to MCP server")
                return None
            
            response = await self._client.post(
                '/tools/execute',
                json={
                    'name': tool_name,
                    'arguments': arguments
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to execute tool {tool_name}: {response.status_code}")
                return None
            
            result = response.json()
            return self.normalize_event({
                'tool_name': tool_name,
                'arguments': arguments,
                'result': result.get('result', result),
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {e}")
            return None

    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """Poll MCP server for available resources and fetch them"""
        artifacts = []
        try:
            discover_result = await self.discover_tools()
            resources = discover_result.get('resources', [])
            
            for resource in resources:
                resource_uri = resource.get('uri') or resource.get('id')
                if not resource_uri:
                    continue
                
                artifact = await self.fetch_resource(resource_uri)
                if artifact:
                    artifacts.append(artifact)
            
            logger.info(f"Polled {len(artifacts)} artifacts from MCP server {self.server_config.name if self.server_config else 'unknown'}")
            return artifacts
            
        except Exception as e:
            logger.error(f"MCP poll failed: {e}")
            return artifacts

    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """Convert MCP event to NormalizedArtifact"""
        resource_uri = raw_event.get('resource_uri', '')
        tool_name = raw_event.get('tool_name', 'unknown')
        data = raw_event.get('data') or raw_event.get('result', raw_event)
        timestamp = raw_event.get('timestamp', datetime.utcnow().isoformat())
        
        content = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
        
        external_id = raw_event.get('id') or resource_uri or f"mcp-{tool_name}-{uuid4()}"
        
        try:
            source_created_at = datetime.fromisoformat(timestamp)
        except (ValueError, TypeError):
            source_created_at = datetime.utcnow()
        
        return NormalizedArtifact(
            company_id=self.company_id,
            source_tool=SourceTool.MCP,
            artifact_type=ArtifactType.MESSAGE,
            external_id=str(external_id),
            content=content,
            author='mcp-bridge',
            author_email='mcp@loopos.internal',
            source_created_at=source_created_at,
            metadata={
                'server_name': self.server_config.name if self.server_config else 'unknown',
                'resource_uri': resource_uri,
                'tool_name': tool_name,
                'raw_event': raw_event
            }
        )

    async def authenticate(self) -> bool:
        """Verify connection to MCP server is valid"""
        try:
            if self._client:
                health = await self._client.get('/health')
                return health.status_code == 200
            return hasattr(self, '_process') and self._process and self._process.returncode is None
        except Exception as e:
            logger.error(f"MCP authentication failed: {e}")
            return False

    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process an incoming MCP webhook event"""
        action = event_data.get('action', '')
        if action == 'resource_updated':
            resource_uri = event_data.get('resource_uri', '')
            if resource_uri:
                return await self.fetch_resource(resource_uri)
        return self.normalize_event(event_data)

    def get_oauth_url(self, redirect_uri: str) -> str:
        raise NotImplementedError("MCP bridge uses direct connection, not OAuth")

    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        raise NotImplementedError("MCP bridge uses direct connection, not OAuth")
