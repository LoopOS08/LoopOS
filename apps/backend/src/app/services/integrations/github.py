import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.integrations.base import BaseIntegration, NormalizedArtifact
from app.models.integration import SourceTool
from app.models.artifact import ArtifactType
import logging

logger = logging.getLogger(__name__)


class GitHubIntegration(BaseIntegration):
    """
    GitHub Integration following three-phase pattern:
    1. GitHub OAuth App Authentication
    2. Webhooks (primary) + REST API (polling)
    3. Normalization to standard artifact format
    """
    
    @property
    def source_tool(self) -> SourceTool:
        return SourceTool.GITHUB
    
    @property
    def webhook_events(self) -> List[str]:
        return [
            'push',
            'pull_request',
            'pull_request_review',
            'issues',
            'workflow_run',
            'create',
            'delete',
            'release'
        ]
    
    def __init__(self, company_id: str, credentials_encrypted: str, settings: Dict[str, Any] = None):
        super().__init__(company_id, credentials_encrypted, settings)
        self.base_url = "https://api.github.com"
        self._http_client = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def authenticate(self) -> bool:
        """Validate GitHub credentials using a test API call"""
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            if not access_token:
                logger.error("No access token in credentials")
                return False
            
            client = await self._get_http_client()
            response = await client.get(
                f"{self.base_url}/user",
                headers={"Authorization": f"token {access_token}"}
            )
            
            if response.status_code == 200:
                user = response.json()
                logger.info(f"GitHub authentication successful for: {user.get('login')}")
                return True
            else:
                logger.error(f"GitHub authentication failed: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"GitHub authentication failed: {e}")
            return False
    
    async def process_webhook(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """
        Process GitHub webhook
        Handles: push, pull_request, pull_request_review, issues, workflow_run, create, delete, release
        """
        try:
            event_type = event_data.get('x-github-event', '')
            
            if event_type == 'push':
                return await self._process_push_event(event_data)
            elif event_type == 'pull_request':
                return await self._process_pull_request_event(event_data)
            elif event_type == 'pull_request_review':
                return await self._process_pull_request_review_event(event_data)
            elif event_type == 'issues':
                return await self._process_issues_event(event_data)
            elif event_type == 'workflow_run':
                return await self._process_workflow_run_event(event_data)
            elif event_type == 'create':
                return await self._process_create_event(event_data)
            elif event_type == 'delete':
                return await self._process_delete_event(event_data)
            elif event_type == 'release':
                return await self._process_release_event(event_data)
            else:
                logger.debug(f"Unhandled GitHub event type: {event_type}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to process GitHub webhook: {e}")
            return None
    
    async def _process_push_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process GitHub push event (commits)"""
        try:
            repository = event_data.get('repository', {})
            pusher = event_data.get('pusher', {})
            commits = event_data.get('commits', [])
            
            if not commits:
                return None
            
            # Process each commit
            artifacts = []
            for commit in commits:
                # Build normalized content
                commit_message = commit.get('message', '')
                commit_id = commit.get('id', '')[:7]  # Short SHA
                author_name = commit.get('author', {}).get('name', pusher.get('name', 'Unknown'))
                author_email = commit.get('author', {}).get('email', '')
                
                # Get changed files
                added = commit.get('added', [])
                modified = commit.get('modified', [])
                removed = commit.get('removed', [])
                
                files_summary = []
                if added:
                    files_summary.append(f"Added: {', '.join(added[:5])}")
                if modified:
                    files_summary.append(f"Modified: {', '.join(modified[:5])}")
                if removed:
                    files_summary.append(f"Removed: {', '.join(removed[:5])}")
                
                repo_name = repository.get('full_name', 'unknown')
                branch = event_data.get('ref', '').replace('refs/heads/', '')
                
                normalized_content = (
                    f"Commit by {author_name} ({author_email}) to {repo_name}/{branch}: "
                    f"{commit_message}\n"
                    f"Commit: {commit_id}\n"
                    f"{', '.join(files_summary)}"
                )
                
                # Build metadata
                metadata = {
                    'commit_id': commit.get('id'),
                    'commit_short_id': commit_id,
                    'repository': repository.get('full_name'),
                    'branch': branch,
                    'commit_message': commit_message,
                    'timestamp': commit.get('timestamp'),
                    'added_files': added,
                    'modified_files': modified,
                    'removed_files': removed,
                    'pusher_name': pusher.get('name'),
                    'pusher_email': pusher.get('email')
                }
                
                artifact = NormalizedArtifact(
                    company_id=self.company_id,
                    source_tool=self.source_tool,
                    artifact_type=ArtifactType.COMMIT,
                    external_id=commit.get('id'),
                    content=normalized_content,
                    author=author_name,
                    author_email=author_email,
                    source_created_at=datetime.fromisoformat(commit.get('timestamp', '').replace('Z', '+00:00')),
                    metadata=metadata
                )
                
                artifacts.append(artifact)
            
            # Return the first artifact (main commit)
            return artifacts[0] if artifacts else None
            
        except Exception as e:
            logger.error(f"Failed to process GitHub push event: {e}")
            return None
    
    async def _process_pull_request_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process GitHub pull request event"""
        try:
            pull_request = event_data.get('pull_request', {})
            repository = event_data.get('repository', {})
            sender = event_data.get('sender', {})
            
            # Extract PR information
            pr_number = pull_request.get('number')
            pr_title = pull_request.get('title', '')
            pr_body = pull_request.get('body', '')
            action = event_data.get('action', 'opened')
            state = pull_request.get('state', 'open')
            
            author_name = sender.get('login', 'Unknown')
            author_email = sender.get('email', '')
            
            repo_name = repository.get('full_name', 'unknown')
            
            # Build normalized content
            normalized_content = (
                f"Pull Request #{pr_number} {action} by {author_name} in {repo_name}\n"
                f"Title: {pr_title}\n"
                f"State: {state}\n"
                f"Body: {pr_body or '(no description)'}"
            )
            
            # Build metadata
            metadata = {
                'pr_number': pr_number,
                'pr_title': pr_title,
                'action': action,
                'state': state,
                'repository': repo_name,
                'head_branch': pull_request.get('head', {}).get('ref'),
                'base_branch': pull_request.get('base', {}).get('ref'),
                'additions': pull_request.get('additions', 0),
                'deletions': pull_request.get('deletions', 0),
                'changed_files': pull_request.get('changed_files', 0),
                'merged': pull_request.get('merged', False),
                'mergeable': pull_request.get('mergeable'),
                'url': pull_request.get('html_url'),
                'user_login': sender.get('login')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.REVIEW,
                external_id=f"pr_{pr_number}_{pull_request.get('id')}",
                content=normalized_content,
                author=author_name,
                author_email=author_email,
                source_created_at=datetime.fromisoformat(pull_request.get('created_at', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process GitHub pull request event: {e}")
            return None
    
    async def _process_pull_request_review_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process GitHub pull request review event"""
        try:
            review = event_data.get('review', {})
            pull_request = event_data.get('pull_request', {})
            repository = event_data.get('repository', {})
            sender = event_data.get('sender', {})
            
            # Extract review information
            review_state = review.get('state', 'pending')  # approved, changes_requested, commented, pending
            review_body = review.get('body', '')
            
            author_name = sender.get('login', 'Unknown')
            author_email = sender.get('email', '')
            
            pr_number = pull_request.get('number')
            repo_name = repository.get('full_name', 'unknown')
            
            # Build normalized content
            normalized_content = (
                f"Pull Request Review {review_state} by {author_name} on PR #{pr_number} in {repo_name}\n"
                f"Review: {review_body or '(no comments)'}"
            )
            
            # Build metadata
            metadata = {
                'review_id': review.get('id'),
                'review_state': review_state,
                'pr_number': pr_number,
                'repository': repo_name,
                'commit_id': review.get('commit_id'),
                'submitted_at': review.get('submitted_at'),
                'user_login': sender.get('login')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.REVIEW,
                external_id=f"review_{review.get('id')}",
                content=normalized_content,
                author=author_name,
                author_email=author_email,
                source_created_at=datetime.fromisoformat(review.get('submitted_at', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process GitHub pull request review event: {e}")
            return None
    
    async def _process_issues_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process GitHub issues event"""
        try:
            issue = event_data.get('issue', {})
            repository = event_data.get('repository', {})
            sender = event_data.get('sender', {})
            
            # Extract issue information
            issue_number = issue.get('number')
            issue_title = issue.get('title', '')
            issue_body = issue.get('body', '')
            action = event_data.get('action', 'opened')
            state = issue.get('state', 'open')
            
            author_name = sender.get('login', 'Unknown')
            author_email = sender.get('email', '')
            
            repo_name = repository.get('full_name', 'unknown')
            
            # Build normalized content
            normalized_content = (
                f"Issue #{issue_number} {action} by {author_name} in {repo_name}\n"
                f"Title: {issue_title}\n"
                f"State: {state}\n"
                f"Body: {issue_body or '(no description)'}"
            )
            
            # Build metadata
            metadata = {
                'issue_number': issue_number,
                'issue_title': issue_title,
                'action': action,
                'state': state,
                'repository': repo_name,
                'labels': [label.get('name') for label in issue.get('labels', [])],
                'assignees': [assignee.get('login') for assignee in issue.get('assignees', [])],
                'milestone': issue.get('milestone', {}).get('title') if issue.get('milestone') else None,
                'url': issue.get('html_url'),
                'user_login': sender.get('login')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.TICKET,
                external_id=f"issue_{issue_number}_{issue.get('id')}",
                content=normalized_content,
                author=author_name,
                author_email=author_email,
                source_created_at=datetime.fromisoformat(issue.get('created_at', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process GitHub issues event: {e}")
            return None
    
    async def _process_workflow_run_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process GitHub workflow run event"""
        try:
            workflow_run = event_data.get('workflow_run', {})
            repository = event_data.get('repository', {})
            sender = event_data.get('sender', {})
            
            # Extract workflow information
            workflow_name = workflow_run.get('name', 'unknown')
            workflow_status = workflow_run.get('status', 'queued')
            workflow_conclusion = workflow_run.get('conclusion')  # success, failure, cancelled
            action = event_data.get('action', 'queued')
            
            author_name = sender.get('login', 'Unknown')
            author_email = sender.get('email', '')
            
            repo_name = repository.get('full_name', 'unknown')
            
            # Build normalized content
            normalized_content = (
                f"Workflow '{workflow_name}' {action} by {author_name} in {repo_name}\n"
                f"Status: {workflow_status}, Conclusion: {workflow_conclusion or 'pending'}"
            )
            
            # Build metadata
            metadata = {
                'workflow_id': workflow_run.get('id'),
                'workflow_name': workflow_name,
                'action': action,
                'status': workflow_status,
                'conclusion': workflow_conclusion,
                'repository': repo_name,
                'head_branch': workflow_run.get('head_branch'),
                'head_sha': workflow_run.get('head_sha'),
                'event': workflow_run.get('event'),
                'url': workflow_run.get('html_url'),
                'user_login': sender.get('login')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.BUILD,
                external_id=f"workflow_{workflow_run.get('id')}",
                content=normalized_content,
                author=author_name,
                author_email=author_email,
                source_created_at=datetime.fromisoformat(workflow_run.get('created_at', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process GitHub workflow run event: {e}")
            return None
    
    async def _process_create_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process GitHub create event (branch, tag)"""
        try:
            ref_type = event_data.get('ref_type', 'unknown')  # branch, tag
            ref = event_data.get('ref', 'unknown')
            repository = event_data.get('repository', {})
            sender = event_data.get('sender', {})
            
            author_name = sender.get('login', 'Unknown')
            author_email = sender.get('email', '')
            
            repo_name = repository.get('full_name', 'unknown')
            
            # Build normalized content
            normalized_content = f"{author_name} created {ref_type} '{ref}' in {repo_name}"
            
            # Build metadata
            metadata = {
                'ref_type': ref_type,
                'ref': ref,
                'repository': repo_name,
                'master_branch': repository.get('master_branch'),
                'description': repository.get('description'),
                'user_login': sender.get('login')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.COMMENT,
                external_id=f"create_{event_data.get('ref')}_{event_data.get('repository', {}).get('id')}",
                content=normalized_content,
                author=author_name,
                author_email=author_email,
                source_created_at=datetime.utcnow(),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process GitHub create event: {e}")
            return None
    
    async def _process_delete_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process GitHub delete event (branch, tag)"""
        try:
            ref_type = event_data.get('ref_type', 'unknown')  # branch, tag
            ref = event_data.get('ref', 'unknown')
            repository = event_data.get('repository', {})
            sender = event_data.get('sender', {})
            
            author_name = sender.get('login', 'Unknown')
            author_email = sender.get('email', '')
            
            repo_name = repository.get('full_name', 'unknown')
            
            # Build normalized content
            normalized_content = f"{author_name} deleted {ref_type} '{ref}' in {repo_name}"
            
            # Build metadata
            metadata = {
                'ref_type': ref_type,
                'ref': ref,
                'repository': repo_name,
                'user_login': sender.get('login')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.COMMENT,
                external_id=f"delete_{event_data.get('ref')}_{event_data.get('repository', {}).get('id')}",
                content=normalized_content,
                author=author_name,
                author_email=author_email,
                source_created_at=datetime.utcnow(),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process GitHub delete event: {e}")
            return None
    
    async def _process_release_event(self, event_data: Dict[str, Any]) -> Optional[NormalizedArtifact]:
        """Process GitHub release event"""
        try:
            release = event_data.get('release', {})
            repository = event_data.get('repository', {})
            sender = event_data.get('sender', {})
            
            # Extract release information
            release_name = release.get('name', 'unknown')
            release_tag = release.get('tag_name', 'unknown')
            release_body = release.get('body', '')
            action = event_data.get('action', 'published')
            
            author_name = sender.get('login', 'Unknown')
            author_email = sender.get('email', '')
            
            repo_name = repository.get('full_name', 'unknown')
            
            # Build normalized content
            normalized_content = (
                f"Release '{release_name}' ({release_tag}) {action} by {author_name} in {repo_name}\n"
                f"Notes: {release_body or '(no release notes)'}"
            )
            
            # Build metadata
            metadata = {
                'release_id': release.get('id'),
                'release_name': release_name,
                'release_tag': release_tag,
                'action': action,
                'repository': repo_name,
                'prerelease': release.get('prerelease', False),
                'draft': release.get('draft', False),
                'url': release.get('html_url'),
                'user_login': sender.get('login')
            }
            
            return NormalizedArtifact(
                company_id=self.company_id,
                source_tool=self.source_tool,
                artifact_type=ArtifactType.COMMENT,
                external_id=f"release_{release.get('id')}",
                content=normalized_content,
                author=author_name,
                author_email=author_email,
                source_created_at=datetime.fromisoformat(release.get('created_at', '').replace('Z', '+00:00')),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to process GitHub release event: {e}")
            return None
    
    async def poll_data(self, since: Optional[datetime] = None) -> List[NormalizedArtifact]:
        """
        Poll for missed data using GitHub REST API
        Also used for repository statistics and commit history
        """
        try:
            credentials = await self.get_credentials()
            access_token = credentials.get('access_token')
            
            client = await self._get_http_client()
            
            # Get repositories for the authenticated user
            repos_response = await client.get(
                f"{self.base_url}/user/repos",
                headers={"Authorization": f"token {access_token}"},
                params={"per_page": 30, "sort": "updated"}
            )
            
            repos_data = repos_response.json()
            
            if not isinstance(repos_data, list):
                logger.error(f"Failed to get repositories: {repos_data}")
                return []
            
            artifacts = []
            
            # Poll each repository for recent activity
            for repo in repos_data[:10]:  # Limit to 10 repos for performance
                repo_name = repo.get('full_name')
                
                # Get recent commits
                commits_response = await client.get(
                    f"{self.base_url}/repos/{repo_name}/commits",
                    headers={"Authorization": f"token {access_token}"},
                    params={"per_page": 10}
                )
                
                if commits_response.status_code == 200:
                    commits = commits_response.json()
                    
                    for commit in commits:
                        # Convert to push event format
                        commit_data = commit.get('commit', {})
                        author = commit_data.get('author', {})
                        committer = commit_data.get('committer', {})
                        
                        event = {
                            'pusher': {
                                'name': author.get('name', committer.get('name', 'Unknown')),
                                'email': author.get('email', committer.get('email', ''))
                            },
                            'repository': repo,
                            'commits': [{
                                'id': commit.get('sha'),
                                'message': commit_data.get('message', ''),
                                'author': {
                                    'name': author.get('name', 'Unknown'),
                                    'email': author.get('email', '')
                                },
                                'timestamp': author.get('date', committer.get('date', ''))
                            }],
                            'ref': repo.get('default_branch', 'main')
                        }
                        
                        artifact = await self._process_push_event(event)
                        if artifact:
                            artifacts.append(artifact)
            
            logger.info(f"Polled {len(artifacts)} artifacts from GitHub")
            return artifacts
            
        except Exception as e:
            logger.error(f"GitHub data polling failed: {e}")
            return []
    
    def normalize_event(self, raw_event: Dict[str, Any]) -> NormalizedArtifact:
        """
        Normalize raw GitHub event to standard artifact format
        This is a synchronous version used for testing
        """
        # For async operations, use process_webhook instead
        raise NotImplementedError("Use process_webhook for async normalization")
    
    def get_oauth_url(self, redirect_uri: str) -> str:
        """Generate GitHub OAuth URL"""
        from app.core.config import settings
        client_id = settings.GITHUB_CLIENT_ID or self.settings.get('github_client_id')
        scopes = "repo,read:org,read:user"
        
        return (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
        )
    
    async def exchange_code_for_credentials(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens"""
        try:
            from app.core.config import settings
            client_id = settings.GITHUB_CLIENT_ID or self.settings.get('github_client_id')
            client_secret = settings.GITHUB_CLIENT_SECRET or self.settings.get('github_client_secret')
            
            client = await self._get_http_client()
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                },
                headers={"Accept": "application/json"}
            )
            
            data = response.json()
            
            if 'error' in data:
                raise Exception(f"OAuth exchange failed: {data.get('error')}")
            
            credentials = {
                'access_token': data.get('access_token'),
                'token_type': data.get('token_type'),
                'scope': data.get('scope')
            }
            
            logger.info("Successfully exchanged OAuth code for GitHub")
            return credentials
            
        except Exception as e:
            logger.error(f"GitHub OAuth exchange failed: {e}")
            raise
    
    def validate_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """
        Validate GitHub webhook signature
        """
        try:
            from app.core.config import settings
            webhook_secret = settings.GITHUB_WEBHOOK_SECRET or self.settings.get('github_webhook_secret')
            
            if not webhook_secret:
                logger.warning("No GitHub webhook secret configured")
                return False
            
            # GitHub signature format: sha256=<hash>
            if not signature.startswith('sha256='):
                logger.warning("Invalid GitHub signature format")
                return False
            
            hash_value = signature[7:]  # Remove 'sha256=' prefix
            
            # Create expected hash
            import hmac
            import hashlib
            expected_hash = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare hashes
            is_valid = hmac.compare_digest(expected_hash, hash_value)
            
            if not is_valid:
                logger.warning("Invalid GitHub webhook signature")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"GitHub signature validation failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
