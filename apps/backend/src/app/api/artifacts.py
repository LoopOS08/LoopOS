from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.artifact import Artifact, SourceTool, ArtifactType
from app.services.artifact_store import artifact_store_service
from datetime import datetime

router = APIRouter()


class ArtifactCreate(BaseModel):
    company_id: str
    source_tool: SourceTool
    artifact_type: ArtifactType
    external_id: str
    content: str
    author: str
    author_email: str
    source_created_at: str
    metadata: Optional[dict] = {}


class ArtifactResponse(BaseModel):
    id: str
    company_id: str
    source_tool: str
    artifact_type: str
    external_id: str
    content: str
    author: str
    author_email: str
    source_created_at: str
    metadata: dict
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    artifact: ArtifactResponse
    similarity: float


class SearchQuery(BaseModel):
    query: str
    company_id: str
    source_tool: Optional[SourceTool] = None
    artifact_type: Optional[ArtifactType] = None
    limit: int = 10
    threshold: float = 0.7


@router.post("/", response_model=ArtifactResponse)
async def create_artifact(
    artifact: ArtifactCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new artifact with automatic embedding generation"""
    # Parse source_created_at
    source_created_at = datetime.fromisoformat(artifact.source_created_at.replace('Z', '+00:00'))
    
    # Create artifact using artifact store service
    db_artifact = await artifact_store_service.create_artifact(
        db=db,
        company_id=artifact.company_id,
        source_tool=artifact.source_tool,
        artifact_type=artifact.artifact_type,
        external_id=artifact.external_id,
        content=artifact.content,
        author=artifact.author,
        author_email=artifact.author_email,
        source_created_at=source_created_at,
        metadata=artifact.metadata
    )
    return db_artifact


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get artifact by ID"""
    result = await db.execute(
        select(Artifact).where(Artifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return artifact


@router.get("/company/{company_id}", response_model=List[ArtifactResponse])
async def get_company_artifacts(
    company_id: str,
    source_tool: Optional[SourceTool] = None,
    artifact_type: Optional[ArtifactType] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get artifacts for a company with optional filters"""
    artifacts = await artifact_store_service.get_company_artifacts(
        db, company_id, source_tool, artifact_type, limit, offset
    )
    return artifacts


@router.post("/search", response_model=List[SearchResult])
async def search_artifacts(
    search_query: SearchQuery,
    db: AsyncSession = Depends(get_db)
):
    """Search artifacts using semantic similarity"""
    try:
        artifacts_with_similarity = await artifact_store_service.semantic_search(
            db=db,
            company_id=search_query.company_id,
            query_text=search_query.query,
            limit=search_query.limit,
            threshold=search_query.threshold,
            source_tool=search_query.source_tool,
            artifact_type=search_query.artifact_type
        )
        
        # Convert to response format
        return [
            SearchResult(
                artifact=ArtifactResponse.model_validate(artifact),
                similarity=similarity
            )
            for artifact, similarity in artifacts_with_similarity
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")