from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.integration import Integration, SourceTool, IntegrationStatus

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