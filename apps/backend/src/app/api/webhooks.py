from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.integrations import (
    SlackIntegration,
    GmailIntegration,
    GitHubIntegration,
    LinearIntegration,
    HubSpotIntegration,
    NotionIntegration,
    ZapierBridgeIntegration
)
from app.models.integration import Integration, SourceTool
from app.models.artifact import Artifact, ArtifactType
from app.services.agent_runtime import agent_runtime
from app.services.artifact_store import artifact_store_service
from app.services.relationships import relationship_tracker
from sqlalchemy import select
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def dispatch_to_agents(
    db: AsyncSession,
    company_id: str,
    artifact_type: str,
    source_tool: str,
    content: str,
    artifact_id: str
):
    try:
        results = await agent_runtime.dispatch_artifact(
            artifact_type=artifact_type,
            source_tool=source_tool,
            content=content,
            company_id=company_id,
            db=db,
            artifact_id=artifact_id
        )
        logger.info(f"Dispatched artifact {artifact_id} to {len(results)} agents")
    except Exception as e:
        logger.error(f"Agent dispatch failed for artifact {artifact_id}: {e}")


async def track_artifact_relationships(
    db: AsyncSession,
    company_id: str,
    artifact_id: str,
    source_tool: str,
    artifact_type: str
):
    try:
        result = await db.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()
        if artifact:
            related = await relationship_tracker.track_relationships(db, artifact)
            if related:
                logger.info(f"Tracked {len(related)} relationships for artifact {artifact_id}")
    except Exception as e:
        logger.error(f"Relationship tracking failed for {artifact_id}: {e}")


async def process_webhook_and_dispatch(
    db: AsyncSession,
    company_id: str,
    integration_instance,
    event_data: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> bool:
    artifact = await integration_instance.process_webhook(event_data)
    if not artifact:
        logger.warning(f"Webhook processing returned no artifact for {integration_instance.source_tool.value}")
        return False

    stored = await integration_instance.store_artifact(db, artifact)
    if not stored:
        return False

    stored_artifact = await artifact_store_service.get_artifact_by_external_id(
        db, company_id, integration_instance.source_tool, artifact.external_id
    )
    if stored_artifact:
        background_tasks.add_task(
            dispatch_to_agents,
            db, company_id,
            artifact.artifact_type.value,
            artifact.source_tool.value,
            artifact.content,
            stored_artifact.id
        )
        background_tasks.add_task(
            track_artifact_relationships,
            db, company_id, stored_artifact.id,
            artifact.source_tool.value,
            artifact.artifact_type.value
        )

    return True


@router.post("/slack")
async def slack_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_slack_signature: str = Header(None),
    x_slack_timestamp: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.body()
        company_id = request.headers.get('x-company-id')
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")

        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.SLACK
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="Slack integration not found")

        slack_integration = SlackIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )

        if not slack_integration.validate_webhook_signature(x_slack_signature, body):
            raise HTTPException(status_code=401, detail="Invalid signature")

        event_data = await request.json()
        if event_data.get('type') == 'url_verification':
            return {"challenge": event_data.get('challenge')}

        success = await process_webhook_and_dispatch(
            db, company_id, slack_integration, event_data, background_tasks
        )
        if success:
            return {"status": "success"}
        raise HTTPException(status_code=500, detail="Failed to process webhook")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Slack webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        company_id = request.headers.get('x-company-id')
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")

        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.GMAIL
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="Gmail integration not found")

        gmail_integration = GmailIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )

        event_data = await request.json()
        success = await process_webhook_and_dispatch(
            db, company_id, gmail_integration, event_data, background_tasks
        )
        if success:
            return {"status": "success"}
        raise HTTPException(status_code=500, detail="Failed to process webhook")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gmail webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        body = await request.body()
        company_id = request.headers.get('x-company-id')
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")

        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.GITHUB
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="GitHub integration not found")

        github_integration = GitHubIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )

        if not github_integration.validate_webhook_signature(x_hub_signature_256, body):
            raise HTTPException(status_code=401, detail="Invalid signature")

        event_data = await request.json()
        event_data['x-github-event'] = x_github_event

        success = await process_webhook_and_dispatch(
            db, company_id, github_integration, event_data, background_tasks
        )
        if success:
            return {"status": "success"}
        raise HTTPException(status_code=500, detail="Failed to process webhook")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/linear")
async def linear_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_linear_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        company_id = request.headers.get('x-company-id')
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")

        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.LINEAR
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="Linear integration not found")

        linear_integration = LinearIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )

        event_data = await request.json()
        success = await process_webhook_and_dispatch(
            db, company_id, linear_integration, event_data, background_tasks
        )
        if success:
            return {"status": "success"}
        raise HTTPException(status_code=500, detail="Failed to process webhook")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Linear webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/hubspot")
async def hubspot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        company_id = request.headers.get('x-company-id')
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")

        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.HUBSPOT
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(status_code=404, detail="HubSpot integration not found")

        hubspot_integration = HubSpotIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )

        event_data = await request.json()
        success = await process_webhook_and_dispatch(
            db, company_id, hubspot_integration, event_data, background_tasks
        )
        if success:
            return {"status": "success"}
        raise HTTPException(status_code=500, detail="Failed to process webhook")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HubSpot webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notion")
async def notion_webhook():
    return {
        "status": "not_implemented",
        "message": "Notion integration uses polling only (no webhooks)"
    }


@router.post("/zapier")
async def zapier_webhook(
    request: Request,
    x_hook_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Zapier webhook events
    Zapier sends webhook events from 5,000+ connected apps
    """
    try:
        body = await request.body()
        company_id = request.headers.get('x-company-id')

        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")

        from app.models.webhook_config import WebhookConfig
        from sqlalchemy import select

        result = await db.execute(
            select(WebhookConfig).where(
                WebhookConfig.company_id == company_id,
                WebhookConfig.source_tool == 'zapier',
                WebhookConfig.enabled == True
            )
        )
        webhook_config = result.scalar_one_or_none()

        if not webhook_config:
            raise HTTPException(status_code=404, detail="Zapier webhook configuration not found")

        zapier_integration = ZapierBridgeIntegration(
            company_id=company_id,
            credentials_encrypted="",
            settings={
                'webhook_secret': webhook_config.webhook_secret,
                'artifact_type': webhook_config.artifact_type,
                'platform': 'zapier'
            }
        )

        if not zapier_integration.validate_webhook_signature(x_hook_signature, body):
            raise HTTPException(status_code=401, detail="Invalid signature")

        event_data = await request.json()
        success = await zapier_integration.handle_webhook(db, event_data)

        webhook_config.last_event_at = datetime.utcnow()
        await db.commit()

        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Zapier webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/make")
async def make_webhook(
    request: Request,
    x_hook_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Make (formerly Integromat) webhook events
    """
    try:
        body = await request.body()
        company_id = request.headers.get('x-company-id')

        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")

        from app.models.webhook_config import WebhookConfig
        from sqlalchemy import select

        result = await db.execute(
            select(WebhookConfig).where(
                WebhookConfig.company_id == company_id,
                WebhookConfig.source_tool == 'make',
                WebhookConfig.enabled == True
            )
        )
        webhook_config = result.scalar_one_or_none()

        if not webhook_config:
            raise HTTPException(status_code=404, detail="Make webhook configuration not found")

        make_integration = ZapierBridgeIntegration(
            company_id=company_id,
            credentials_encrypted="",
            settings={
                'webhook_secret': webhook_config.webhook_secret,
                'artifact_type': webhook_config.artifact_type,
                'platform': 'make'
            }
        )

        if not make_integration.validate_webhook_signature(x_hook_signature, body):
            raise HTTPException(status_code=401, detail="Invalid signature")

        event_data = await request.json()
        success = await make_integration.handle_webhook(db, event_data)

        webhook_config.last_event_at = datetime.utcnow()
        await db.commit()

        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Make webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook-config")
async def create_webhook_config(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Create a webhook configuration for Zapier or Make
    Generates a unique webhook URL path and secret
    """
    try:
        data = await request.json()
        company_id = data.get('company_id')
        source_tool = data.get('source_tool', 'zapier')
        artifact_type = data.get('artifact_type', 'message')

        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id")

        from app.models.webhook_config import WebhookConfig
        import secrets

        webhook_secret = secrets.token_hex(32)
        webhook_url_path = f"{company_id}/{source_tool}/{secrets.token_hex(8)}"

        webhook_config = WebhookConfig(
            company_id=company_id,
            source_tool=source_tool,
            webhook_secret=webhook_secret,
            webhook_url_path=webhook_url_path,
            artifact_type=artifact_type,
            enabled=True
        )

        db.add(webhook_config)
        await db.commit()
        await db.refresh(webhook_config)

        return {
            "status": "success",
            "config_id": webhook_config.id,
            "webhook_url": f"/api/webhooks/{source_tool}",
            "webhook_secret": webhook_secret,
            "instructions": {
                "zapier": "Create a Webhook trigger in Zapier and POST JSON to the webhook URL. Include x-hook-signature header with HMAC-SHA256 of the body using the webhook_secret.",
                "make": "Create a Webhook module in Make and POST JSON to the webhook URL. Include x-hook-signature header with HMAC-SHA256 of the body using the webhook_secret."
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create webhook config: {str(e)}")
