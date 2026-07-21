from .base import BaseIntegration, NormalizedArtifact
from .slack import SlackIntegration
from .gmail import GmailIntegration
from .github import GitHubIntegration
from .linear import LinearIntegration
from .hubspot import HubSpotIntegration
from .notion import NotionIntegration
from .mcp_bridge import MCPBridgeIntegration
from .rest_connector_service import RESTConnectorIntegration
from .zapier_bridge import ZapierBridgeIntegration

__all__ = [
    'BaseIntegration',
    'NormalizedArtifact',
    'SlackIntegration',
    'GmailIntegration',
    'GitHubIntegration',
    'LinearIntegration',
    'HubSpotIntegration',
    'NotionIntegration',
    'MCPBridgeIntegration',
    'RESTConnectorIntegration',
    'ZapierBridgeIntegration',
]
