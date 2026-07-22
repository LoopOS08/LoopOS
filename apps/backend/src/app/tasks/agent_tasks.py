from typing import Dict, Any
from app.tasks.sync import celery_app
from app.db.database import get_async_session_local
from app.services.agent_runtime import agent_runtime
from app.services.intelligence.goal_comparator import goal_comparator
from app.services.intelligence.flywheel import flywheel_engine
from app.models.company import Company
from sqlalchemy import select
import asyncio
import logging

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_agent_for_company(self, agent_name: str, company_id: str, artifact_type: str = None, source_tool: str = None, content: str = None):
    async def _run():
        db_session_factory = get_async_session_local()
        async with db_session_factory() as db:
            try:
                extra = {}
                if artifact_type:
                    extra['artifact_type'] = artifact_type
                if source_tool:
                    extra['source_tool'] = source_tool
                if content:
                    extra['artifact_content'] = content
                context = await agent_runtime.build_agent_context(
                    db, company_id, agent_name, extra
                )
                action, outcome = await agent_runtime.dispatch_agent(agent_name, context, db)
                logger.info(f"Agent {agent_name} executed for company {company_id}: {action.action_type}")
                return {'agent': agent_name, 'company_id': company_id, 'action_type': action.action_type}
            except Exception as e:
                logger.error(f"Agent task failed: {e}")
                raise
    return _run_async(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_all_agents_for_artifact(self, artifact_type: str, source_tool: str, content: str, company_id: str, artifact_id: str = None):
    async def _run():
        db_session_factory = get_async_session_local()
        async with db_session_factory() as db:
            try:
                results = await agent_runtime.dispatch_artifact(
                    artifact_type, source_tool, content, company_id, db, artifact_id
                )
                logger.info(f"Dispatched artifact {artifact_type}/{source_tool} to {len(results)} agents")
                return {'company_id': company_id, 'agent_count': len(results)}
            except Exception as e:
                logger.error(f"Artifact dispatch task failed: {e}")
                raise
    return _run_async(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def goal_state_comparator_task(self):
    async def _run():
        db_session_factory = get_async_session_local()
        async with db_session_factory() as db:
            try:
                results = await goal_comparator.run_all_companies(db)
                logger.info(f"Goal comparison completed for {len(results)} companies")
                return {'companies_processed': len(results)}
            except Exception as e:
                logger.error(f"Goal comparator task failed: {e}")
                raise
    return _run_async(_run())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def flywheel_engine_task(self):
    async def _run():
        db_session_factory = get_async_session_local()
        async with db_session_factory() as db:
            try:
                companies = await db.execute(select(Company))
                results = {}
                for company in companies.scalars().all():
                    flywheel_results = await flywheel_engine.run_for_company(db, company.id)
                    results[company.id] = flywheel_results
                logger.info(f"Flywheel completed for {len(results)} companies")
                return {'companies_processed': len(results)}
            except Exception as e:
                logger.error(f"Flywheel task failed: {e}")
                raise
    return _run_async(_run())
