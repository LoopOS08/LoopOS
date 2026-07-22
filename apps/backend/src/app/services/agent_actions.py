from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AgentActionExecutor:
    def __init__(self):
        self._slack_webhook_url: Optional[str] = None

    def configure_slack(self, webhook_url: str):
        self._slack_webhook_url = webhook_url

    async def post_to_slack(self, channel: str, message: str) -> bool:
        logger.info(f"[Slack] Would post to #{channel}: {message[:100]}...")
        if self._slack_webhook_url:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        self._slack_webhook_url,
                        json={"channel": channel, "text": message},
                    )
                    return resp.is_success
            except Exception as e:
                logger.error(f"Failed to post to Slack: {e}")
                return False
        return True

    async def create_decision_entry(
        self, db_session, company_id: str, content: str, author: str,
        source: str, artifact_id: Optional[str] = None,
        significance: str = "medium",
    ) -> Optional[str]:
        if db_session is None:
            logger.info(f"[test] Would create decision entry: {content[:50]}")
            return "test-decision-id"
        try:
            from app.models.decision import Decision
            from sqlalchemy import select
            import uuid
            result = await db_session.execute(
                select(Decision).where(
                    Decision.company_id == company_id,
                    Decision.content == content[:200],
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing.id
            decision = Decision(
                id=str(uuid.uuid4()),
                company_id=company_id,
                artifact_id=artifact_id,
                content=content,
                decision_maker=author,
                outcome={},
            )
            db_session.add(decision)
            await db_session.commit()
            logger.info(f"Created decision entry: {decision.id}")
            return decision.id
        except Exception as e:
            logger.error(f"Failed to create decision entry: {e}")
            try:
                await db_session.rollback()
            except Exception:
                pass
            return None

    async def create_spec_entry(
        self, db_session, company_id: str, title: str, context: str,
        acceptance_criteria: List[str], dependencies: List[str],
        estimated_effort: str, suggested_assignee: str, priority: str,
        decision_id: Optional[str] = None,
    ) -> Optional[str]:
        if db_session is None:
            logger.info(f"[test] Would create spec entry: {title}")
            return "test-spec-id"
        try:
            from app.models.spec import Spec
            import uuid
            spec = Spec(
                id=str(uuid.uuid4()),
                company_id=company_id,
                decision_id=decision_id,
                title=title,
                context=context,
                acceptance_criteria=acceptance_criteria,
                dependencies=dependencies,
                estimated_effort=estimated_effort,
                suggested_assignee=suggested_assignee,
                priority=priority,
            )
            db_session.add(spec)
            await db_session.commit()
            logger.info(f"Created spec entry: {spec.id}")
            return spec.id
        except Exception as e:
            logger.error(f"Failed to create spec entry: {e}")
            try:
                await db_session.rollback()
            except Exception:
                pass
            return None

    async def store_agent_briefing(
        self, db_session, company_id: str, agent_name: str,
        briefing_type: str, content: Dict[str, Any],
    ) -> bool:
        if db_session is None:
            logger.info(f"[test] Would store briefing: {agent_name}/{briefing_type}")
            return True
        try:
            from app.models.artifact import Artifact, ArtifactType
            from app.models.integration import SourceTool
            import uuid
            from datetime import datetime, timezone
            content_str = json.dumps(content) if isinstance(content, dict) else str(content)
            artifact = Artifact(
                id=str(uuid.uuid4()),
                company_id=company_id,
                source_tool=SourceTool.INTERNAL,
                artifact_type=ArtifactType.BRIEFING,
                external_id=f"{agent_name}_{briefing_type}_{datetime.now(timezone.utc).isoformat()}",
                content=f"[{agent_name}] {briefing_type}: {content_str[:500]}",
                author="LoopOS Agent",
                author_email="agent@loopos.dev",
                source_created_at=datetime.now(timezone.utc),
                artifact_metadata={"agent": agent_name, "briefing_type": briefing_type},
            )
            db_session.add(artifact)
            await db_session.commit()
            logger.info(f"Stored briefing artifact: {artifact.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store briefing: {e}")
            try:
                await db_session.rollback()
            except Exception:
                pass
            return False

    async def execute_action(
        self,
        action_type: str,
        output: Dict[str, Any],
        db_session,
        company_id: str,
        agent_name: str,
    ) -> bool:
        if action_type in ("alert_slack", "daily_briefing", "status_report"):
            message = output.get("message", output.get("briefing_type", "No message"))
            channel = output.get("channel", "#general")
            await self.post_to_slack(channel, message)
            return True
        elif action_type == "alert_misalignment":
            message = output.get("message", "Alignment issue detected")
            channel = output.get("channel", "#engineering-leadership")
            await self.post_to_slack(channel, message)
            return True
        elif action_type == "flag_drift":
            message = output.get("message", "Drift detected")
            channel = output.get("channel", "#engineering")
            await self.post_to_slack(channel, message)
            return True
        elif action_type == "alert_anomaly":
            message = output.get("message", "Anomaly detected")
            channel = output.get("channel", "#finance")
            await self.post_to_slack(channel, message)
            return True
        elif action_type == "alert_churn":
            message = output.get("message", "Churn detected")
            channel = output.get("channel", "#finance")
            await self.post_to_slack(channel, message)
            return True
        elif action_type == "generate_briefing":
            briefing_type = output.get("briefing_type", "generic")
            await self.store_agent_briefing(
                db_session, company_id, agent_name, briefing_type, output
            )
            return True
        elif action_type == "generate_summary":
            await self.store_agent_briefing(
                db_session, company_id, agent_name,
                output.get("summary_type", "summary"), output,
            )
            return True
        elif action_type == "document_decision":
            decisions = output.get("decisions", [])
            for dec in decisions[:5]:
                await self.create_decision_entry(
                    db_session, company_id,
                    dec.get("content", ""),
                    dec.get("author", "Unknown"),
                    dec.get("source", "unknown"),
                    artifact_id=dec.get("artifact_id"),
                    significance=dec.get("significance", "medium"),
                )
            return True
        elif action_type == "create_spec":
            specs = output.get("specs", [])
            for spec in specs[:3]:
                await self.create_spec_entry(
                    db_session, company_id,
                    spec.get("title", "Untitled"),
                    spec.get("context", ""),
                    spec.get("acceptance_criteria", []),
                    spec.get("dependencies", []),
                    spec.get("estimated_effort", "M"),
                    spec.get("suggested_assignee", "TBD"),
                    spec.get("priority", "medium"),
                    decision_id=spec.get("decision_id"),
                )
            return True
        elif action_type == "no_action":
            return True
        else:
            logger.warning(f"Unknown action type: {action_type}, logging only")
            return True


import json


action_executor = AgentActionExecutor()
