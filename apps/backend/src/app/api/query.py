from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.query import query_service
from app.models.artifact import SourceTool, ArtifactType

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    limit: Optional[int] = 15
    threshold: Optional[float] = 0.7
    source_tool: Optional[SourceTool] = None
    artifact_type: Optional[ArtifactType] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: float
    caveats: List[str]


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    threshold: Optional[float] = 0.7
    source_tool: Optional[SourceTool] = None
    artifact_type: Optional[ArtifactType] = None


@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    company_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a unified query across all connected tools
    
    Example: "What did we decide about pricing last week?"
    """
    try:
        result = await query_service.query(
            db=db,
            company_id=company_id,
            question=request.question,
            limit=request.limit,
            threshold=request.threshold,
            source_tool=request.source_tool,
            artifact_type=request.artifact_type
        )
        
        return result.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.post("/search")
async def search_artifacts(
    request: SearchRequest,
    company_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Simple semantic search returning artifacts directly
    Useful for UI components that need raw artifact data
    """
    try:
        results = await query_service.search_artifacts(
            db=db,
            company_id=company_id,
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
            source_tool=request.source_tool,
            artifact_type=request.artifact_type
        )
        
        return {"results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/suggestions")
async def get_query_suggestions(
    partial_query: str = Query(""),
    company_id: str = Query(...),
    limit: int = Query(5),
    db: AsyncSession = Depends(get_db)
):
    """
    Get query suggestions based on partial input
    """
    try:
        suggestions = await query_service.get_answer_suggestions(
            db=db,
            company_id=company_id,
            partial_query=partial_query,
            limit=limit
        )
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")
