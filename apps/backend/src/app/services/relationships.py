from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from app.models.artifact import Artifact, SourceTool, ArtifactType
from app.services.artifact_store import artifact_store_service
import logging

logger = logging.getLogger(__name__)


class ArtifactRelationshipTracker:
    def __init__(self):
        self._relationship_rules = {
            ('commit', 'github'): self._link_commit_to_pr,
            ('pull_request', 'github'): self._link_pr_to_issues,
            ('review', 'github'): self._link_review_to_pr,
            ('email', 'gmail'): self._link_email_to_thread,
            ('ticket', 'linear'): self._link_ticket_to_cycle,
            ('message', 'slack'): self._link_slack_to_thread,
        }

    async def track_relationships(
        self,
        db: AsyncSession,
        artifact: Artifact
    ) -> List[str]:
        key = (artifact.artifact_type.value, artifact.source_tool.value)
        handler = self._relationship_rules.get(key)
        if handler:
            try:
                return await handler(db, artifact)
            except Exception as e:
                logger.error(f"Relationship tracking failed for {artifact.id}: {e}")
        return []

    async def _link_commit_to_pr(
        self, db: AsyncSession, artifact: Artifact
    ) -> List[str]:
        related = []
        metadata = artifact.artifact_metadata or {}
        commit_message = metadata.get('commit_message', '')
        repo = metadata.get('repository', '')
        if repo and commit_message:
            pr_patterns = ['#', 'PR', 'pull request', 'merge']
            if any(p in commit_message.lower() for p in pr_patterns):
                result = await db.execute(
                    select(Artifact).where(
                        Artifact.company_id == artifact.company_id,
                        Artifact.source_tool == SourceTool.GITHUB,
                        Artifact.artifact_type == ArtifactType.REVIEW,
                        Artifact.artifact_metadata['repository'].as_string() == repo
                    ).limit(5)
                )
                for linked in result.scalars().all():
                    related.append(linked.id)
                    logger.debug(f"Linked commit {artifact.id} to PR/review {linked.id}")
        return related

    async def _link_pr_to_issues(
        self, db: AsyncSession, artifact: Artifact
    ) -> List[str]:
        related = []
        pr_body = (artifact.artifact_metadata or {}).get('pr_title', '')
        repo = (artifact.artifact_metadata or {}).get('repository', '')
        if pr_body:
            result = await db.execute(
                select(Artifact).where(
                    Artifact.company_id == artifact.company_id,
                    Artifact.source_tool == SourceTool.GITHUB,
                    Artifact.artifact_type == ArtifactType.TICKET,
                    Artifact.artifact_metadata['repository'].as_string() == repo
                ).limit(5)
            )
            for linked in result.scalars().all():
                related.append(linked.id)
                logger.debug(f"Linked PR {artifact.id} to issue {linked.id}")
        return related

    async def _link_review_to_pr(
        self, db: AsyncSession, artifact: Artifact
    ) -> List[str]:
        related = []
        metadata = artifact.artifact_metadata or {}
        pr_number = metadata.get('pr_number')
        repo = metadata.get('repository', '')
        if pr_number and repo:
            result = await db.execute(
                select(Artifact).where(
                    Artifact.company_id == artifact.company_id,
                    Artifact.source_tool == SourceTool.GITHUB,
                    Artifact.artifact_type == ArtifactType.REVIEW,
                    Artifact.artifact_metadata['pr_number'].as_string() == str(pr_number),
                    Artifact.artifact_metadata['repository'].as_string() == repo,
                    Artifact.id != artifact.id
                ).limit(10)
            )
            for linked in result.scalars().all():
                related.append(linked.id)
        return related

    async def _link_email_to_thread(
        self, db: AsyncSession, artifact: Artifact
    ) -> List[str]:
        related = []
        thread_id = (artifact.artifact_metadata or {}).get('thread_id')
        if thread_id:
            result = await db.execute(
                select(Artifact).where(
                    Artifact.company_id == artifact.company_id,
                    Artifact.source_tool == SourceTool.GMAIL,
                    Artifact.artifact_type == ArtifactType.EMAIL,
                    Artifact.artifact_metadata['thread_id'].as_string() == thread_id,
                    Artifact.id != artifact.id
                ).limit(20)
            )
            for linked in result.scalars().all():
                related.append(linked.id)
                logger.debug(f"Linked email {artifact.id} to thread {linked.id}")
        return related

    async def _link_ticket_to_cycle(
        self, db: AsyncSession, artifact: Artifact
    ) -> List[str]:
        related = []
        metadata = artifact.artifact_metadata or {}
        team = metadata.get('team_name', '')
        if team:
            result = await db.execute(
                select(Artifact).where(
                    Artifact.company_id == artifact.company_id,
                    Artifact.source_tool == SourceTool.LINEAR,
                    Artifact.artifact_type == ArtifactType.TICKET,
                    Artifact.artifact_metadata['team_name'].as_string() == team,
                    Artifact.id != artifact.id
                ).limit(10)
            )
            for linked in result.scalars().all():
                related.append(linked.id)
        return related

    async def _link_slack_to_thread(
        self, db: AsyncSession, artifact: Artifact
    ) -> List[str]:
        related = []
        metadata = artifact.artifact_metadata or {}
        thread_parent = metadata.get('thread_parent_ts')
        channel = metadata.get('channel_id', '')
        if thread_parent and channel:
            result = await db.execute(
                select(Artifact).where(
                    Artifact.company_id == artifact.company_id,
                    Artifact.source_tool == SourceTool.SLACK,
                    Artifact.artifact_type == ArtifactType.MESSAGE,
                    Artifact.artifact_metadata['channel_id'].as_string() == channel,
                    Artifact.id != artifact.id
                ).limit(20)
            )
            for linked in result.scalars().all():
                related.append(linked.id)
        return related


relationship_tracker = ArtifactRelationshipTracker()
