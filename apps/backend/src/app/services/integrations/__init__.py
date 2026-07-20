from .base import BaseIntegration, NormalizedArtifact
from .slack import SlackIntegration
from .gmail import GmailIntegration
from .github import GitHubIntegration
from .linear import LinearIntegration
from .hubspot import HubSpotIntegration
from .notion import NotionIntegration

__all__ = [
    'BaseIntegration',
    'NormalizedArtifact',
    'SlackIntegration',
    'GmailIntegration',
    'GitHubIntegration',
    'LinearIntegration',
    'HubSpotIntegration',
    'NotionIntegration',
]
