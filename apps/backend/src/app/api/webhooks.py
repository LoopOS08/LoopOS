from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.integrations import (
    SlackIntegration,
    GmailIntegration,
    GitHubIntegration,
    LinearIntegration,
    HubSpotIntegration,
    NotionIntegration
)
from app.models.integration import Integration, SourceTool
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/slack")
async def slack_webhook(
    request: Request,
    x_slack_signature: str = Header(None),
    x_slack_timestamp: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Slack webhooks
    """
    try:
        # Get raw body for signature validation
        body = await request.body()
        
        # Get company ID from request (in production, this would come from auth)
        company_id = request.headers.get('x-company-id')
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")
        
        # Get integration for this company
        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.SLACK
            )
        )
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Slack integration not found")
        
        # Create integration instance
        slack_integration = SlackIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )
        
        # Validate signature
        if not slack_integration.validate_webhook_signature(x_slack_signature, body):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON body
        event_data = await request.json()
        
        # Handle URL verification challenge
        if event_data.get('type') == 'url_verification':
            challenge = event_data.get('challenge')
            return {"challenge": challenge}
        
        # Process webhook
        success = await slack_integration.handle_webhook(db, event_data)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Slack webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Gmail Pub/Sub push notifications
    """
    try:
        # Get company ID from request
        company_id = request.headers.get('x-company-id')
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")
        
        # Get integration for this company
        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.GMAIL
            )
        )
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Gmail integration not found")
        
        # Create integration instance
        gmail_integration = GmailIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )
        
        # Parse JSON body
        event_data = await request.json()
        
        # Process webhook
        success = await gmail_integration.handle_webhook(db, event_data)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gmail webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle GitHub webhooks
    """
    try:
        # Get raw body for signature validation
        body = await request.body()
        
        # Get company ID from request
        company_id = request.headers.get('x-company-id')
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")
        
        # Get integration for this company
        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.GITHUB
            )
        )
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise HTTPException(status_code=404, detail="GitHub integration not found")
        
        # Create integration instance
        github_integration = GitHubIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )
        
        # Validate signature
        if not github_integration.validate_webhook_signature(x_hub_signature_256, body):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON body and add event type
        event_data = await request.json()
        event_data['x-github-event'] = x_github_event
        
        # Process webhook
        success = await github_integration.handle_webhook(db, event_data)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/linear")
async def linear_webhook(
    request: Request,
    x_linear_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Linear webhooks
    """
    try:
        # Get company ID from request
        company_id = request.headers.get('x-company-id')
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")
        
        # Get integration for this company
        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.LINEAR
            )
        )
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Linear integration not found")
        
        # Create integration instance
        linear_integration = LinearIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )
        
        # Parse JSON body
        event_data = await request.json()
        
        # Process webhook
        success = await linear_integration.handle_webhook(db, event_data)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Linear webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/hubspot")
async def hubspot_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle HubSpot webhooks
    """
    try:
        # Get company ID from request
        company_id = request.headers.get('x-company-id')
        
        if not company_id:
            raise HTTPException(status_code=400, detail="Missing company_id header")
        
        # Get integration for this company
        result = await db.execute(
            select(Integration).where(
                Integration.company_id == company_id,
                Integration.source_tool == SourceTool.HUBSPOT
            )
        )
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise HTTPException(status_code=404, detail="HubSpot integration not found")
        
        # Create integration instance
        hubspot_integration = HubSpotIntegration(
            company_id=company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )
        
        # Parse JSON body
        event_data = await request.json()
        
        # Process webhook
        success = await hubspot_integration.handle_webhook(db, event_data)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Failed to process webhook")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"HubSpot webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notion")
async def notion_webhook():
    """
    Notion doesn't support webhooks
    This endpoint is provided for consistency
    """
    return {
        "status": "not_implemented",
        "message": "Notion integration uses polling only (no webhooks)"
    }
