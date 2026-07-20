import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType
import logging

logger = logging.getLogger(__name__)


class LinearIntegration(BaseIntegration):
    """
    Linear Integration following three-phase pattern:
    1. OAuth 2.0 + GraphQL API Authentication
    2. Webhooks (primary) + GraphQL API (polling)
    3. Normalization to standard artifact format
    """
    
    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.LINEAR
    
    @property
    def webhook_events(self) -> List[str]:
        return [
            'Issue',
            'IssueUpdate',
            'Comment',
            'Cycle',
            'CycleUpdate',
            'Project',
            'ProjectUpdate'
        ]
    
    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.base_url = "https://api.linear.app/graphql"
        self._http_client = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def authenticate(self) -> bool:
        """Validate Linear credentials using a test GraphQL query"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            if not access_token:
                logger.error("No access token in credentials")
                return False
            
            client = await self._get_http_client()
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "query": """
                        query {
                            viewer {
                                id
                                name
                                email
                            }
                        }
                    """
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' not in data:
                    viewer = data.get('data', {}).get('viewer', {})
                    logger.info(f"Linear authentication successful for: {viewer.get('name')}")
                    return True
                else:
                    logger.error(f"Linear authentication failed: {data.get('errors')}")
                    return False
            else:
                logger.error(f"Linear authentication failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"Linear authentication failed: {e}")
            return False
    
    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """
        Process Linear webhook
        Handles: Issue, IssueUpdate, Comment, Cycle, CycleUpdate, Project, ProjectUpdate
        """
        try:
            action = event_data.get('action', '')
            data = event_data.get('data', {})
            
            if action == 'Issue':
                return await self._process_issue_event(data)
            elif action == 'IssueUpdate':
                return await self._process_issue_update_event(data)
            elif action == 'Comment':
                return await self._process_comment_event(data)
            elif action == 'Cycle':
                return await self._process_cycle_event(data)
            elif action == 'CycleUpdate':
                return await self._process_cycle_update_event(data)
            elif action == 'Project':
                return await self._process_project_event(data)
            elif action == 'ProjectUpdate':
                return await self._process_project_update_event(data)
            else:
                logger.debug(f"Unhandled Linear webhook action: {action}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to process Linear webhook: {e}")
            return None
    
    async def _process_issue_event(self, data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Linear issue event"""
        try:
            issue = data.get('Issue', {})
            
            # Extract issue information
            issue_id = issue.get('id')
            issue_title = issue.get('title', '')
            issue_description = issue.get('description', '')
            state_name = issue.get('state', {}).get('name', 'unknown')
            priority = issue.get('priority', 0)  # 0: no priority, 1: urgent, 2: high, 3: medium, 4: low
            
            # Assignee information
            assignee = issue.get('assignee', {})
            assignee_name = assignee.get('name', 'Unassigned')
            assignee_email = assignee.get('email', '')
            
            # Creator information
            creator = issue.get('creator', {})
            creator_name = creator.get('name', 'Unknown')
            creator_email = creator.get('email', '')
            
            # Team information
            team = issue.get('team', {})
            team_name = team.get('name', 'unknown')
            
            # Build normalized content
            normalized_content = (
                f"Issue created by {creator_name} in {team_name}: {issue_title}\n"
                f"State: {state_name}, Priority: {priority}\n"
                f"Assignee: {assignee_name}\n"
                f"Description: {issue_description or '(no description)'}"
            )
            
            # Build metadata
            metadata = {
                'issue_id': issue_id,
                'issue_title': issue_title,
                'state_name': state_name,
                'priority': priority,
                'team_name': team_name,
                'assignee_name': assignee_name,
                'creator_name': creator_name,
                'labels': [label.get('name') for label in issue.get('labels', [])],
                'estimate': issue.get('estimate'),
                'due_date': issue.get('dueDate'),
                'url': issue.get('url')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.TICKET,
                external_id=issue_id,
                content=normalized_content,
                author=creator_name,
                author_email=creator_email,
                source_created_at=datetime.fromisoformat(issue.get('createdAt', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Linear issue event: {e}")
            return None
    
    async def _process_issue_update_event(self, data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Linear issue update event"""
        try:
            issue = data.get('Issue', {})
            updated_from = data.get('updatedFrom', {})
            
            # Extract issue information
            issue_id = issue.get('id')
            issue_title = issue.get('title', '')
            state_name = issue.get('state', {}).get('name', 'unknown')
            
            # Creator information
            creator = issue.get('creator', {})
            creator_name = creator.get('name', 'Unknown')
            creator_email = creator.get('email', '')
            
            # Determine what changed
            changes = []
            if 'state' in updated_from:
                old_state = updated_from.get('state', {}).get('name', 'unknown')
                changes.append(f"State changed from {old_state} to {state_name}")
            if 'assignee' in updated_from:
                old_assignee = updated_from.get('assignee', {}).get('name', 'Unassigned')
                new_assignee = issue.get('assignee', {}).get('name', 'Unassigned')
                changes.append(f"Assignee changed from {old_assignee} to {new_assignee}")
            if 'priority' in updated_from:
                old_priority = updated_from.get('priority', 0)
                new_priority = issue.get('priority', 0)
                changes.append(f"Priority changed from {old_priority} to {new_priority}")
            
            if not changes:
                changes.append("Issue updated")
            
            # Build normalized content
            normalized_content = (
                f"Issue '{issue_title}' updated by {creator_name}\n"
                f"{', '.join(changes)}"
            )
            
            # Build metadata
            metadata = {
                'issue_id': issue_id,
                'issue_title': issue_title,
                'state_name': state_name,
                'changes': changes,
                'updated_from': updated_from
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.TICKET,
                external_id=f"{issue_id}_update",
                content=normalized_content,
                author=creator_name,
                author_email=creator_email,
                source_created_at=datetime.fromisoformat(issue.get('updatedAt', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Linear issue update event: {e}")
            return None
    
    async def _process_comment_event(self, data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Linear comment event"""
        try:
            comment = data.get('Comment', {})
            issue = data.get('Issue', {})
            
            # Extract comment information
            comment_id = comment.get('id')
            comment_body = comment.get('body', '')
            
            # Author information
            user = comment.get('user', {})
            user_name = user.get('name', 'Unknown')
            user_email = user.get('email', '')
            
            # Issue information
            issue_title = issue.get('title', 'unknown')
            issue_id = issue.get('id')
            
            # Build normalized content
            normalized_content = (
                f"Comment by {user_name} on issue '{issue_title}':\n"
                f"{comment_body}"
            )
            
            # Build metadata
            metadata = {
                'comment_id': comment_id,
                'issue_id': issue_id,
                'issue_title': issue_title,
                'parent_type': comment.get('parent', {}).get('type', 'Issue')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.COMMENT,
                external_id=comment_id,
                content=normalized_content,
                author=user_name,
                author_email=user_email,
                source_created_at=datetime.fromisoformat(comment.get('createdAt', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Linear comment event: {e}")
            return None
    
    async def _process_cycle_event(self, data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Linear cycle event"""
        try:
            cycle = data.get('Cycle', {})
            
            # Extract cycle information
            cycle_id = cycle.get('id')
            cycle_name = cycle.get('name', 'unknown')
            cycle_status = cycle.get('status', 'unknown')
            
            # Team information
            team = cycle.get('team', {})
            team_name = team.get('name', 'unknown')
            
            # Creator information
            creator = cycle.get('creator', {})
            creator_name = creator.get('name', 'Unknown')
            creator_email = creator.get('email', '')
            
            # Build normalized content
            normalized_content = (
                f"Cycle '{cycle_name}' {cycle_status} by {creator_name} in {team_name}\n"
                f"Start: {cycle.get('startDate', 'not set')}\n"
                f"End: {cycle.get('endDate', 'not set')}"
            )
            
            # Build metadata
            metadata = {
                'cycle_id': cycle_id,
                'cycle_name': cycle_name,
                'cycle_status': cycle_status,
                'team_name': team_name,
                'start_date': cycle.get('startDate'),
                'end_date': cycle.get('endDate'),
                'number': cycle.get('number')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.TICKET,
                external_id=cycle_id,
                content=normalized_content,
                author=creator_name,
                author_email=creator_email,
                source_created_at=datetime.fromisoformat(cycle.get('createdAt', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Linear cycle event: {e}")
            return None
    
    async def _process_cycle_update_event(self, data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Linear cycle update event"""
        try:
            cycle = data.get('Cycle', {})
            
            # Extract cycle information
            cycle_id = cycle.get('id')
            cycle_name = cycle.get('name', 'unknown')
            cycle_status = cycle.get('status', 'unknown')
            
            # Creator information
            creator = cycle.get('creator', {})
            creator_name = creator.get('name', 'Unknown')
            creator_email = creator.get('email', '')
            
            # Build normalized content
            normalized_content = (
                f"Cycle '{cycle_name}' updated to {cycle_status} by {creator_name}"
            )
            
            # Build metadata
            metadata = {
                'cycle_id': cycle_id,
                'cycle_name': cycle_name,
                'cycle_status': cycle_status
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.TICKET,
                external_id=f"{cycle_id}_update",
                content=normalized_content,
                author=creator_name,
                author_email=creator_email,
                source_created_at=datetime.fromisoformat(cycle.get('updatedAt', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Linear cycle update event: {e}")
            return None
    
    async def _process_project_event(self, data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Linear project event"""
        try:
            project = data.get('Project', {})
            
            # Extract project information
            project_id = project.get('id')
            project_name = project.get('name', 'unknown')
            project_status = project.get('status', 'unknown')
            
            # Team information
            team = project.get('team', {})
            team_name = team.get('name', 'unknown')
            
            # Creator information
            creator = project.get('creator', {})
            creator_name = creator.get('name', 'Unknown')
            creator_email = creator.get('email', '')
            
            # Build normalized content
            normalized_content = (
                f"Project '{project_name}' {project_status} by {creator_name} in {team_name}\n"
                f"Description: {project.get('description', '(no description)')}"
            )
            
            # Build metadata
            metadata = {
                'project_id': project_id,
                'project_name': project_name,
                'project_status': project_status,
                'team_name': team_name,
                'description': project.get('description')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.TICKET,
                external_id=project_id,
                content=normalized_content,
                author=creator_name,
                author_email=creator_email,
                source_created_at=datetime.fromisoformat(project.get('createdAt', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Linear project event: {e}")
            return None
    
    async def _process_project_update_event(self, data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process Linear project update event"""
        try:
            project = data.get('Project', {})
            
            # Extract project information
            project_id = project.get('id')
            project_name = project.get('name', 'unknown')
            project_status = project.get('status', 'unknown')
            
            # Creator information
            creator = project.get('creator', {})
            creator_name = creator.get('name', 'Unknown')
            creator_email = creator.get('email', '')
            
            # Build normalized content
            normalized_content = (
                f"Project '{project_name}' updated to {project_status} by {creator_name}"
            )
            
            # Build metadata
            metadata = {
                'project_id': project_id,
                'project_name': project_name,
                'project_status': project_status
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.TICKET,
                external_id=f"{project_id}_update",
                content=normalized_content,
                author=creator_name,
                author_email=creator_email,
                source_created_at=datetime.fromisoformat(project.get('updatedAt', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process Linear project update event: {e}")
            return None
    
    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """
        Poll for missed data using Linear GraphQL API
        Also used for sprint metrics not available via webhooks
        """
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            
            # Query for recent issues
            query = """
                query {
                    issues(filter: {isDeleted: {eq: false}}, first: 50) {
                        nodes {
                            id
                            title
                            description
                            state {
                                name
                            }
                            priority
                            assignee {
                                name
                                email
                            }
                            creator {
                                name
                                email
                            }
                            team {
                                name
                            }
                            labels {
                                nodes {
                                    name
                                }
                            }
                            estimate
                            dueDate
                            url
                            createdAt
                            updatedAt
                        }
                    }
                }
            """
            
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"query": query}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to query Linear: {response.status_code}")
                return []
            
            data = response.json()
            
            if 'errors' in data:
                logger.error(f"Linear GraphQL errors: {data.get('errors')}")
                return []
            
            issues = data.get('data', {}).get('issues', {}).get('nodes', [])
            
            artifacts = []
            
            # Process each issue
            for issue in issues:
                event_data = {
                    'action': 'Issue',
                    'data': {'Issue': issue}
                }
                
                artifact = await self.process_webhook(event_data)
                if artifact:
                    artifacts.append(artifact)
            
            logger.info(f"Polled {len(artifacts)} artifacts from Linear")
            return artifacts
            
        except Exception as e:
            logger.error(f"Linear data polling failed: {e}")
            return []
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """
        Normalize raw Linear event to standard artifact format
        This is a synchronous version used for testing
        """
        # For async operations, use process_webhook instead
        raise NotImplementedError("Use process_webhook for async normalization")
    
    def get_oauth_url(self, redirect_uri: str) -> str:
        """Generate Linear OAuth URL"""
        from app.core.config import settings
        client_id = settings.LINEAR_CLIENT_ID or self.settings.get('linear_client_id')
        scopes = "read,write"
        
        return (
            f"https://linear.app/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&response_type=code"
        )
    
    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens"""
        try:
            from app.core.config import settings
            client_id = settings.LINEAR_CLIENT_ID or self.settings.get('linear_client_id')
            client_secret = settings.LINEAR_CLIENT_SECRET or self.settings.get('linear_client_secret')
            
            client = await self._get_http_client()
            response = await client.post(
                "https://api.linear.app/oauth/token",
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
                'expires_in': data.get('expires_in')
            }
            
            logger.info("Successfully exchanged OAuth code for Linear")
            return credentials
            
        except Exception as e:
            logger.error(f"Linear OAuth exchange failed: {e}")
            raise
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
