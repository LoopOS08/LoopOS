from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.integration import Integration, SourceTool, IntegrationStatus
from app.services.integrations import (
    SlackIntegration,
    GmailIntegration,
    GitHubIntegration,
    LinearIntegration,
    HubSpotIntegration,
    NotionIntegration
)
from app.services.encryption import encryption_service

router = APIRouter()


class IntegrationCreate(BaseModel):
    company_id: str
    source_tool: SourceTool
    credentials_encrypted: str
    settings: Optional[dict] = {}


class IntegrationResponse(BaseModel):
    id: str
    company_id: str
    source_tool: str
    status: str
    last_sync_at: Optional[str]
    settings: dict
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class OAuthUrlRequest(BaseModel):
    company_id: str
    source_tool: SourceTool
    redirect_uri: str


class OAuthUrlResponse(BaseModel):
    oauth_url: str


class OAuthExchangeRequest(BaseModel):
    company_id: str
    source_tool: SourceTool
    code: str
    redirect_uri: str


class SyncRequest(BaseModel):
    company_id: str
    source_tool: SourceTool


@router.post("/", response_model=IntegrationResponse)
async def create_integration(
    integration: IntegrationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new integration"""
    db_integration = Integration(
        company_id=integration.company_id,
        source_tool=integration.source_tool,
        credentials_encrypted=integration.credentials_encrypted,
        settings=integration.settings,
        status=IntegrationStatus.CONNECTED
    )
    db.add(db_integration)
    await db.commit()
    await db.refresh(db_integration)
    return db_integration


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get integration by ID"""
    result = await db.execute(
        select(Integration).where(Integration.id == integration_id)
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    return integration


@router.get("/company/{company_id}", response_model=List[IntegrationResponse])
async def get_company_integrations(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all integrations for a company"""
    result = await db.execute(
        select(Integration).where(Integration.company_id == company_id)
    )
    integrations = result.scalars().all()
    return integrations


@router.post("/oauth/url", response_model=OAuthUrlResponse)
async def get_oauth_url(request: OAuthUrlRequest):
    """
    Generate OAuth URL for integration setup
    """
    try:
        # Get integration class based on source tool
        integration_classes = {
            SourceTool.SLACK: SlackIntegration,
            SourceTool.GMAIL: GmailIntegration,
            SourceTool.GITHUB: GitHubIntegration,
            SourceTool.LINEAR: LinearIntegration,
            SourceTool.HUBSPOT: HubSpotIntegration,
            SourceTool.NOTION: NotionIntegration
        }
        
        integration_class = integration_classes.get(request.source_tool)
        
        if not integration_class:
            raise HTTPException(status_code=400, detail="Unsupported integration")
        
        # Create temporary integration instance to get OAuth URL
        from app.core.config import settings
        integration_settings = {
            'slack_client_id': settings.SLACK_CLIENT_ID,
            'slack_client_secret': settings.SLACK_CLIENT_SECRET,
            'slack_signing_secret': settings.SLACK_SIGNING_SECRET,
            'google_client_id': settings.GOOGLE_CLIENT_ID,
            'google_client_secret': settings.GOOGLE_CLIENT_SECRET,
            'github_client_id': settings.GITHUB_CLIENT_ID,
            'github_client_secret': settings.GITHUB_CLIENT_SECRET,
            'github_webhook_secret': settings.GITHUB_WEBHOOK_SECRET,
            'linear_client_id': settings.LINEAR_CLIENT_ID,
            'linear_client_secret': settings.LINEAR_CLIENT_SECRET,
            'hubspot_client_id': settings.HUBSPOT_CLIENT_ID,
            'hubspot_client_secret': settings.HUBSPOT_CLIENT_SECRET,
            'notion_client_id': settings.NOTION_CLIENT_ID,
            'notion_client_secret': settings.NOTION_CLIENT_SECRET,
        }
        
        integration = integration_class(
            company_id=request.company_id,
            credentials_encrypted="",  # Not needed for OAuth URL
            settings=integration_settings
        )
        
        oauth_url = integration.get_oauth_url(request.redirect_uri)
        
        return {"oauth_url": oauth_url}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate OAuth URL: {str(e)}")


@router.post("/oauth/exchange")
async def exchange_oauth_code(request: OAuthExchangeRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchange OAuth code for access tokens and create integration
    """
    try:
        # Get integration class based on source tool
        integration_classes = {
            SourceTool.SLACK: SlackIntegration,
            SourceTool.GMAIL: GmailIntegration,
            SourceTool.GITHUB: GitHubIntegration,
            SourceTool.LINEAR: LinearIntegration,
            SourceTool.HUBSPOT: HubSpotIntegration,
            SourceTool.NOTION: NotionIntegration
        }
        
        integration_class = integration_classes.get(request.source_tool)
        
        if not integration_class:
            raise HTTPException(status_code=400, detail="Unsupported integration")
        
        # Create temporary integration instance
        from app.core.config import settings
        integration_settings = {
            'slack_client_id': settings.SLACK_CLIENT_ID,
            'slack_client_secret': settings.SLACK_CLIENT_SECRET,
            'slack_signing_secret': settings.SLACK_SIGNING_SECRET,
            'google_client_id': settings.GOOGLE_CLIENT_ID,
            'google_client_secret': settings.GOOGLE_CLIENT_SECRET,
            'github_client_id': settings.GITHUB_CLIENT_ID,
            'github_client_secret': settings.GITHUB_CLIENT_SECRET,
            'github_webhook_secret': settings.GITHUB_WEBHOOK_SECRET,
            'linear_client_id': settings.LINEAR_CLIENT_ID,
            'linear_client_secret': settings.LINEAR_CLIENT_SECRET,
            'hubspot_client_id': settings.HUBSPOT_CLIENT_ID,
            'hubspot_client_secret': settings.HUBSPOT_CLIENT_SECRET,
            'notion_client_id': settings.NOTION_CLIENT_ID,
            'notion_client_secret': settings.NOTION_CLIENT_SECRET,
        }
        
        integration = integration_class(
            company_id=request.company_id,
            credentials_encrypted="",
            settings=integration_settings
        )
        
        # Exchange code for credentials
        credentials = await integration.exchange_code_for_credentials(
            request.code,
            request.redirect_uri
        )
        
        # Encrypt credentials
        credentials_encrypted = encryption_service.encrypt_credentials(credentials)
        
        # Create integration in database
        db_integration = Integration(
            company_id=request.company_id,
            source_tool=request.source_tool,
            credentials_encrypted=credentials_encrypted,
            settings={},
            status=IntegrationStatus.CONNECTED
        )
        
        db.add(db_integration)
        await db.commit()
        await db.refresh(db_integration)
        
        return {
            "status": "success",
            "integration_id": db_integration.id,
            "source_tool": db_integration.source_tool.value
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {str(e)}")


@router.post("/sync")
async def sync_integration(request: SyncRequest, db: AsyncSession = Depends(get_db)):
    """
    Manually trigger sync for an integration
    """
    try:
        # Get integration
        result = await db.execute(
            select(Integration).where(
                Integration.company_id == request.company_id,
                Integration.source_tool == request.source_tool
            )
        )
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Get integration class
        integration_classes = {
            SourceTool.SLACK: SlackIntegration,
            SourceTool.GMAIL: GmailIntegration,
            SourceTool.GITHUB: GitHubIntegration,
            SourceTool.LINEAR: LinearIntegration,
            SourceTool.HUBSPOT: HubSpotIntegration,
            SourceTool.NOTION: NotionIntegration
        }
        
        integration_class = integration_classes.get(request.source_tool)
        
        if not integration_class:
            raise HTTPException(status_code=400, detail="Unsupported integration")
        
        # Create integration instance
        integration_instance = integration_class(
            company_id=request.company_id,
            credentials_encrypted=integration.credentials_encrypted,
            settings=integration.settings
        )
        
        # Perform sync
        sync_count = await integration_instance.sync_data(db)
        
        # Update last sync time
        from datetime import datetime
        integration.last_sync_at = datetime.utcnow()
        await db.commit()
        
        return {
            "status": "success",
            "synced_artifacts": sync_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete an integration"""
    try:
        result = await db.execute(
            select(Integration).where(Integration.id == integration_id)
        )
        integration = result.scalar_one_or_none()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        await db.delete(integration)
        await db.commit()
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete integration: {str(e)}")