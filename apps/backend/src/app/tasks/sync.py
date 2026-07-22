from celery import Celery
from app.core.config import settings
from app.models.integration import Integration, SourceTool, IntegrationStatus
from app.services.integrations.slack import SlackIntegration
from app.services.integrations.gmail import GmailIntegration
from app.services.integrations.github import GitHubIntegration
from app.services.integrations.linear import LinearIntegration
from app.services.integrations.hubspot import HubSpotIntegration
from app.services.integrations.notion import NotionIntegration
from sqlalchemy import select
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'loopos',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


def get_async_session():
    """Create async database session for Celery tasks"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session()


@celery_app.task(bind=True, max_retries=3)
def sync_slack_task(self, company_id: str):
    """
    Sync Slack data (every 15 minutes)
    """
    import asyncio
    
    async def _sync():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                # Get integration
                result = await db.execute(
                    select(Integration).where(
                        Integration.company_id == company_id,
                        Integration.source_tool == SourceTool.SLACK
                    )
                )
                integration = result.scalar_one_or_none()
                
                if not integration:
                    logger.warning(f"Slack integration not found for company {company_id}")
                    return {"status": "not_found"}
                
                # Create integration instance
                slack_integration = SlackIntegration(
                    company_id=company_id,
                    credentials_encrypted=integration.credentials_encrypted,
                    settings=integration.settings
                )
                
                # Perform sync (last 15 minutes)
                since = datetime.utcnow() - timedelta(minutes=15)
                sync_count = await slack_integration.sync_data(db, since)
                
                # Update last sync time
                integration.last_sync_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"Slack sync completed for company {company_id}: {sync_count} artifacts")
                return {"status": "success", "synced_artifacts": sync_count}
                
            except Exception as e:
                logger.error(f"Slack sync failed for company {company_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    return asyncio.run(_sync())


@celery_app.task(bind=True, max_retries=3)
def sync_gmail_task(self, company_id: str):
    """
    Sync Gmail data (every 30 minutes)
    """
    import asyncio
    
    async def _sync():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                # Get integration
                result = await db.execute(
                    select(Integration).where(
                        Integration.company_id == company_id,
                        Integration.source_tool == SourceTool.GMAIL
                    )
                )
                integration = result.scalar_one_or_none()
                
                if not integration:
                    logger.warning(f"Gmail integration not found for company {company_id}")
                    return {"status": "not_found"}
                
                # Create integration instance
                gmail_integration = GmailIntegration(
                    company_id=company_id,
                    credentials_encrypted=integration.credentials_encrypted,
                    settings=integration.settings
                )
                
                # Perform sync (last 30 minutes)
                since = datetime.utcnow() - timedelta(minutes=30)
                sync_count = await gmail_integration.sync_data(db, since)
                
                # Update last sync time
                integration.last_sync_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"Gmail sync completed for company {company_id}: {sync_count} artifacts")
                return {"status": "success", "synced_artifacts": sync_count}
                
            except Exception as e:
                logger.error(f"Gmail sync failed for company {company_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    return asyncio.run(_sync())


@celery_app.task(bind=True, max_retries=3)
def sync_github_task(self, company_id: str):
    """
    Sync GitHub data (every 60 minutes)
    """
    import asyncio
    
    async def _sync():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                # Get integration
                result = await db.execute(
                    select(Integration).where(
                        Integration.company_id == company_id,
                        Integration.source_tool == SourceTool.GITHUB
                    )
                )
                integration = result.scalar_one_or_none()
                
                if not integration:
                    logger.warning(f"GitHub integration not found for company {company_id}")
                    return {"status": "not_found"}
                
                # Create integration instance
                github_integration = GitHubIntegration(
                    company_id=company_id,
                    credentials_encrypted=integration.credentials_encrypted,
                    settings=integration.settings
                )
                
                # Perform sync (last 60 minutes)
                since = datetime.utcnow() - timedelta(minutes=60)
                sync_count = await github_integration.sync_data(db, since)
                
                # Update last sync time
                integration.last_sync_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"GitHub sync completed for company {company_id}: {sync_count} artifacts")
                return {"status": "success", "synced_artifacts": sync_count}
                
            except Exception as e:
                logger.error(f"GitHub sync failed for company {company_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    return asyncio.run(_sync())


@celery_app.task(bind=True, max_retries=3)
def sync_linear_task(self, company_id: str):
    """
    Sync Linear data (every 30 minutes)
    """
    import asyncio
    
    async def _sync():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                # Get integration
                result = await db.execute(
                    select(Integration).where(
                        Integration.company_id == company_id,
                        Integration.source_tool == SourceTool.LINEAR
                    )
                )
                integration = result.scalar_one_or_none()
                
                if not integration:
                    logger.warning(f"Linear integration not found for company {company_id}")
                    return {"status": "not_found"}
                
                # Create integration instance
                linear_integration = LinearIntegration(
                    company_id=company_id,
                    credentials_encrypted=integration.credentials_encrypted,
                    settings=integration.settings
                )
                
                # Perform sync (last 30 minutes)
                since = datetime.utcnow() - timedelta(minutes=30)
                sync_count = await linear_integration.sync_data(db, since)
                
                # Update last sync time
                integration.last_sync_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"Linear sync completed for company {company_id}: {sync_count} artifacts")
                return {"status": "success", "synced_artifacts": sync_count}
                
            except Exception as e:
                logger.error(f"Linear sync failed for company {company_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    return asyncio.run(_sync())


@celery_app.task(bind=True, max_retries=3)
def sync_hubspot_task(self, company_id: str):
    """
    Sync HubSpot data (every 60 minutes)
    """
    import asyncio
    
    async def _sync():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                # Get integration
                result = await db.execute(
                    select(Integration).where(
                        Integration.company_id == company_id,
                        Integration.source_tool == SourceTool.HUBSPOT
                    )
                )
                integration = result.scalar_one_or_none()
                
                if not integration:
                    logger.warning(f"HubSpot integration not found for company {company_id}")
                    return {"status": "not_found"}
                
                # Create integration instance
                hubspot_integration = HubSpotIntegration(
                    company_id=company_id,
                    credentials_encrypted=integration.credentials_encrypted,
                    settings=integration.settings
                )
                
                # Perform sync (last 60 minutes)
                since = datetime.utcnow() - timedelta(minutes=60)
                sync_count = await hubspot_integration.sync_data(db, since)
                
                # Update last sync time
                integration.last_sync_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"HubSpot sync completed for company {company_id}: {sync_count} artifacts")
                return {"status": "success", "synced_artifacts": sync_count}
                
            except Exception as e:
                logger.error(f"HubSpot sync failed for company {company_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    return asyncio.run(_sync())


@celery_app.task(bind=True, max_retries=3)
def sync_notion_task(self, company_id: str):
    """
    Sync Notion data (every 30 minutes)
    """
    import asyncio
    
    async def _sync():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                # Get integration
                result = await db.execute(
                    select(Integration).where(
                        Integration.company_id == company_id,
                        Integration.source_tool == SourceTool.NOTION
                    )
                )
                integration = result.scalar_one_or_none()
                
                if not integration:
                    logger.warning(f"Notion integration not found for company {company_id}")
                    return {"status": "not_found"}
                
                # Create integration instance
                notion_integration = NotionIntegration(
                    company_id=company_id,
                    credentials_encrypted=integration.credentials_encrypted,
                    settings=integration.settings
                )
                
                # Perform sync (last 30 minutes)
                since = datetime.utcnow() - timedelta(minutes=30)
                sync_count = await notion_integration.sync_data(db, since)
                
                # Update last sync time
                integration.last_sync_at = datetime.utcnow()
                await db.commit()
                
                logger.info(f"Notion sync completed for company {company_id}: {sync_count} artifacts")
                return {"status": "success", "synced_artifacts": sync_count}
                
            except Exception as e:
                logger.error(f"Notion sync failed for company {company_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    return asyncio.run(_sync())


@celery_app.task
def sync_all_integrations_for_company(company_id: str):
    """
    Sync all integrations for a company
    """
    results = {
        'slack': sync_slack_task.delay(company_id),
        'gmail': sync_gmail_task.delay(company_id),
        'github': sync_github_task.delay(company_id),
        'linear': sync_linear_task.delay(company_id),
        'hubspot': sync_hubspot_task.delay(company_id),
        'notion': sync_notion_task.delay(company_id)
    }
    
    return {"status": "scheduled", "tasks": {k: v.id for k, v in results.items()}}


# Schedule periodic tasks - these will be triggered for each company with active integrations
from celery.schedules import crontab

# Simple periodic schedules for background sync
# In production, these would be dynamically scheduled per company
celery_app.conf.beat_schedule = {
    'sync-all-integrations': {
        'task': 'app.tasks.sync.schedule_company_syncs',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}


@celery_app.task(bind=True, max_retries=3)
def sync_mcp_task(self, company_id: str, server_id: str):
    """
    Sync data from an MCP server
    """
    import asyncio

    async def _sync():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                from app.models.mcp_server import MCPServer, MCPServerStatus

                result = await db.execute(
                    select(MCPServer).where(
                        MCPServer.id == server_id,
                        MCPServer.company_id == company_id
                    )
                )
                server = result.scalar_one_or_none()

                if not server:
                    logger.warning(f"MCP server {server_id} not found for company {company_id}")
                    return {"status": "not_found"}

                from app.services.integrations.mcp_bridge import MCPBridgeIntegration

                bridge = MCPBridgeIntegration(
                    company_id=company_id,
                    credentials_encrypted="",
                    settings={'server_id': server.id}
                )
                await bridge.connect(server)
                artifacts = await bridge.poll_data()
                await bridge.disconnect()

                synced_count = 0
                for artifact in artifacts:
                    if await bridge.store_artifact(db, artifact):
                        synced_count += 1

                server.last_sync_at = datetime.utcnow()
                server.status = MCPServerStatus.CONNECTED
                await db.commit()

                logger.info(f"MCP sync completed for server {server.name}: {synced_count} artifacts")
                return {"status": "success", "synced_artifacts": synced_count}

            except Exception as e:
                logger.error(f"MCP sync failed for server {server_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    return asyncio.run(_sync())


@celery_app.task(bind=True, max_retries=3)
def sync_rest_connector_task(self, company_id: str, connector_id: str):
    """
    Sync data from a REST API connector
    """
    import asyncio

    async def _sync():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                from app.models.rest_connector import RESTConnector, RESTConnectorStatus

                result = await db.execute(
                    select(RESTConnector).where(
                        RESTConnector.id == connector_id,
                        RESTConnector.company_id == company_id
                    )
                )
                connector = result.scalar_one_or_none()

                if not connector:
                    logger.warning(f"REST connector {connector_id} not found for company {company_id}")
                    return {"status": "not_found"}

                from app.services.integrations.rest_connector_service import RESTConnectorIntegration

                integration = RESTConnectorIntegration(
                    company_id=company_id,
                    credentials_encrypted="",
                    settings={}
                )
                integration.configure(connector)
                artifacts = await integration.poll_data()

                synced_count = 0
                for artifact in artifacts:
                    if await integration.store_artifact(db, artifact):
                        synced_count += 1

                connector.last_sync_at = datetime.utcnow()
                connector.status = RESTConnectorStatus.ACTIVE
                await db.commit()

                logger.info(f"REST connector sync completed for {connector.name}: {synced_count} artifacts")
                return {"status": "success", "synced_artifacts": synced_count}

            except Exception as e:
                logger.error(f"REST connector sync failed for {connector_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    return asyncio.run(_sync())


@celery_app.task
def schedule_company_syncs():
    """
    Dynamically schedule sync tasks for all companies with active integrations
    This task runs every 5 minutes and checks for new/updated integrations
    """
    import asyncio

    async def _schedule():
        async_session = get_async_session()
        async with async_session() as db:
            try:
                # Get all active integrations
                result = await db.execute(
                    select(Integration).where(
                        Integration.status == IntegrationStatus.CONNECTED
                    )
                )
                integrations = result.scalars().all()

                # Group by company
                company_integrations = {}
                for integration in integrations:
                    if integration.company_id not in company_integrations:
                        company_integrations[integration.company_id] = []
                    company_integrations[integration.company_id].append(integration.source_tool)

                # Schedule tasks for each company's integrations
                scheduled_tasks = []
                for company_id, tools in company_integrations.items():
                    if SourceTool.SLACK in tools:
                        scheduled_tasks.append(sync_slack_task.delay(company_id))
                    if SourceTool.GMAIL in tools:
                        scheduled_tasks.append(sync_gmail_task.delay(company_id))
                    if SourceTool.GITHUB in tools:
                        scheduled_tasks.append(sync_github_task.delay(company_id))
                    if SourceTool.LINEAR in tools:
                        scheduled_tasks.append(sync_linear_task.delay(company_id))
                    if SourceTool.HUBSPOT in tools:
                        scheduled_tasks.append(sync_hubspot_task.delay(company_id))
                    if SourceTool.NOTION in tools:
                        scheduled_tasks.append(sync_notion_task.delay(company_id))

                # Schedule MCP server syncs for active servers
                from app.models.mcp_server import MCPServer, MCPServerStatus

                mcp_result = await db.execute(
                    select(MCPServer).where(MCPServer.status == MCPServerStatus.CONNECTED)
                )
                mcp_servers = mcp_result.scalars().all()
                for server in mcp_servers:
                    scheduled_tasks.append(sync_mcp_task.delay(server.company_id, server.id))

                # Schedule REST connector syncs for active connectors
                from app.models.rest_connector import RESTConnector, RESTConnectorStatus

                rest_result = await db.execute(
                    select(RESTConnector).where(RESTConnector.status == RESTConnectorStatus.ACTIVE)
                )
                rest_connectors = rest_result.scalars().all()
                for connector in rest_connectors:
                    scheduled_tasks.append(sync_rest_connector_task.delay(connector.company_id, connector.id))

                logger.info(f"Scheduled {len(scheduled_tasks)} sync tasks for {len(company_integrations)} companies + Phase 4 connectors")
                return {"status": "success", "scheduled_tasks": len(scheduled_tasks)}

            except Exception as e:
                logger.error(f"Failed to schedule company syncs: {e}")
                return {"status": "error", "error": str(e)}

    return asyncio.run(_schedule())
