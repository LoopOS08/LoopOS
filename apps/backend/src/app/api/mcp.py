from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.database import get_db
from app.models.mcp_server import MCPServer, MCPTransportType, MCPServerStatus
from app.services.integrations.mcp_bridge import MCPBridgeIntegration
from app.services.integrations.base import NormalizedArtifact
from app.services.artifact_store import artifact_store_service
from app.models.integration import SourceTool
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPServerCreate(BaseModel):
    company_id: str
    name: str
    transport_type: str = "sse"
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = []
    auth_token: Optional[str] = None
    polling_interval_minutes: int = 60


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    auth_token: Optional[str] = None
    enabled_tools: Optional[List[str]] = None
    polling_interval_minutes: Optional[int] = None


class MCPServerResponse(BaseModel):
    id: str
    company_id: str
    name: str
    transport_type: str
    url: Optional[str]
    command: Optional[str]
    args: list
    enabled_tools: list
    discovered_tools: list
    status: str
    polling_interval_minutes: int
    last_sync_at: Optional[str]
    settings: dict
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("/servers", response_model=MCPServerResponse)
async def create_mcp_server(
    server: MCPServerCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new MCP server"""
    try:
        transport = MCPTransportType(server.transport_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid transport type: {server.transport_type}")

    db_server = MCPServer(
        company_id=server.company_id,
        name=server.name,
        transport_type=transport,
        url=server.url,
        command=server.command,
        args=server.args or [],
        auth_token=server.auth_token,
        polling_interval_minutes=server.polling_interval_minutes,
        status=MCPServerStatus.DISCONNECTED
    )
    db.add(db_server)
    await db.commit()
    await db.refresh(db_server)
    return db_server


@router.get("/servers", response_model=List[MCPServerResponse])
async def list_mcp_servers(
    company_id: str = Query(..., description="Company ID"),
    db: AsyncSession = Depends(get_db)
):
    """List all MCP servers for a company"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.company_id == company_id)
    )
    return result.scalars().all()


@router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get MCP server details"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


@router.put("/servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: str,
    update: MCPServerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update MCP server configuration"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(server, field, value)

    await db.commit()
    await db.refresh(server)
    return server


@router.delete("/servers/{server_id}")
async def delete_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete an MCP server"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    await db.delete(server)
    await db.commit()
    return {"status": "success"}


@router.post("/servers/{server_id}/connect")
async def connect_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Connect to an MCP server"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    try:
        bridge = MCPBridgeIntegration(
            company_id=server.company_id,
            credentials_encrypted="",
            settings={'server_id': server.id}
        )
        connected = await bridge.connect(server)

        if connected:
            server.status = MCPServerStatus.CONNECTED
        else:
            server.status = MCPServerStatus.ERROR

        await db.commit()
        return {
            "status": "connected" if connected else "error",
            "server_id": server.id,
            "name": server.name
        }
    except Exception as e:
        server.status = MCPServerStatus.ERROR
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.post("/servers/{server_id}/disconnect")
async def disconnect_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Disconnect from an MCP server"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    server.status = MCPServerStatus.DISCONNECTED
    await db.commit()
    return {"status": "disconnected", "server_id": server.id}


@router.post("/servers/{server_id}/discover")
async def discover_mcp_tools(
    server_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Discover tools and resources from an MCP server"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    try:
        bridge = MCPBridgeIntegration(
            company_id=server.company_id,
            credentials_encrypted="",
            settings={'server_id': server.id}
        )
        await bridge.connect(server)
        discovered = await bridge.discover_tools()
        await bridge.disconnect()

        server.discovered_tools = discovered
        await db.commit()

        return {
            "status": "success",
            "server_id": server.id,
            "discovered_tools": discovered
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.post("/servers/{server_id}/sync")
async def sync_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Sync data from an MCP server"""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    try:
        bridge = MCPBridgeIntegration(
            company_id=server.company_id,
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

        return {
            "status": "success",
            "server_id": server.id,
            "synced_artifacts": synced_count
        }
    except Exception as e:
        server.status = MCPServerStatus.ERROR
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
