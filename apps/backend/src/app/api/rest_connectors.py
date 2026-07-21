from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.rest_connector import RESTConnector, RESTAuthType, RESTConnectorStatus
from app.services.integrations.rest_connector_service import RESTConnectorIntegration
from app.services.artifact_store import artifact_store_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class RESTConnectorCreate(BaseModel):
    company_id: str
    name: str
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = {}
    auth_type: str = "none"
    auth_config: Optional[Dict[str, Any]] = {}
    field_mappings: Dict[str, str]
    pagination: Optional[Dict[str, Any]] = {}
    polling_interval_minutes: int = 60
    settings: Optional[Dict[str, Any]] = {}


class RESTConnectorUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    field_mappings: Optional[Dict[str, str]] = None
    pagination: Optional[Dict[str, Any]] = None
    polling_interval_minutes: Optional[int] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class RESTConnectorResponse(BaseModel):
    id: str
    company_id: str
    name: str
    url: str
    method: str
    headers: dict
    auth_type: str
    auth_config: dict
    field_mappings: dict
    pagination: dict
    polling_interval_minutes: int
    status: str
    last_sync_at: Optional[str]
    settings: dict
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("/connectors", response_model=RESTConnectorResponse)
async def create_rest_connector(
    connector: RESTConnectorCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new REST API connector"""
    try:
        auth_type = RESTAuthType(connector.auth_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid auth type: {connector.auth_type}")

    db_connector = RESTConnector(
        company_id=connector.company_id,
        name=connector.name,
        url=connector.url,
        method=connector.method.upper(),
        headers=connector.headers or {},
        auth_type=auth_type,
        auth_config=connector.auth_config or {},
        field_mappings=connector.field_mappings,
        pagination=connector.pagination or {},
        polling_interval_minutes=connector.polling_interval_minutes,
        status=RESTConnectorStatus.PAUSED,
        settings=connector.settings or {}
    )
    db.add(db_connector)
    await db.commit()
    await db.refresh(db_connector)
    return db_connector


@router.get("/connectors", response_model=List[RESTConnectorResponse])
async def list_rest_connectors(
    company_id: str = Query(..., description="Company ID"),
    db: AsyncSession = Depends(get_db)
):
    """List all REST connectors for a company"""
    result = await db.execute(
        select(RESTConnector).where(RESTConnector.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/connectors/{connector_id}", response_model=RESTConnectorResponse)
async def get_rest_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get REST connector details"""
    result = await db.execute(
        select(RESTConnector).where(RESTConnector.id == connector_id)
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="REST connector not found")
    return connector


@router.put("/connectors/{connector_id}", response_model=RESTConnectorResponse)
async def update_rest_connector(
    connector_id: str,
    update: RESTConnectorUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update REST connector configuration"""
    result = await db.execute(
        select(RESTConnector).where(RESTConnector.id == connector_id)
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="REST connector not found")

    update_data = update.model_dump(exclude_unset=True)
    if 'auth_type' in update_data:
        try:
            update_data['auth_type'] = RESTAuthType(update_data['auth_type'])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid auth type")
    if 'status' in update_data:
        try:
            update_data['status'] = RESTConnectorStatus(update_data['status'])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status")

    for field, value in update_data.items():
        if value is not None:
            setattr(connector, field, value)

    await db.commit()
    await db.refresh(connector)
    return connector


@router.delete("/connectors/{connector_id}")
async def delete_rest_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a REST connector"""
    result = await db.execute(
        select(RESTConnector).where(RESTConnector.id == connector_id)
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="REST connector not found")

    await db.delete(connector)
    await db.commit()
    return {"status": "success"}


@router.post("/connectors/{connector_id}/test")
async def test_rest_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Test a REST connector connection and return sample data"""
    result = await db.execute(
        select(RESTConnector).where(RESTConnector.id == connector_id)
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="REST connector not found")

    try:
        integration = RESTConnectorIntegration(
            company_id=connector.company_id,
            credentials_encrypted="",
            settings={}
        )
        integration.configure(connector)
        test_result = await integration.test_connection()
        return test_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")


@router.post("/connectors/{connector_id}/sync")
async def sync_rest_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger sync for a REST connector"""
    result = await db.execute(
        select(RESTConnector).where(RESTConnector.id == connector_id)
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="REST connector not found")

    try:
        integration = RESTConnectorIntegration(
            company_id=connector.company_id,
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

        return {
            "status": "success",
            "connector_id": connector.id,
            "synced_artifacts": synced_count
        }
    except Exception as e:
        connector.status = RESTConnectorStatus.ERROR
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/connectors/{connector_id}/activate")
async def activate_rest_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Activate a REST connector for scheduled polling"""
    result = await db.execute(
        select(RESTConnector).where(RESTConnector.id == connector_id)
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="REST connector not found")

    connector.status = RESTConnectorStatus.ACTIVE
    await db.commit()
    return {"status": "active", "connector_id": connector.id}


@router.post("/connectors/{connector_id}/pause")
async def pause_rest_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Pause a REST connector's scheduled polling"""
    result = await db.execute(
        select(RESTConnector).where(RESTConnector.id == connector_id)
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(status_code=404, detail="REST connector not found")

    connector.status = RESTConnectorStatus.PAUSED
    await db.commit()
    return {"status": "paused", "connector_id": connector.id}
