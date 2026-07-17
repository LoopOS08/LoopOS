from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.agent_action import AgentAction, ApprovalStatus

router = APIRouter()


class AgentActionCreate(BaseModel):
    company_id: str
    agent_name: str
    action_type: str
    context: dict
    reasoning: str
    output: dict
    artifact_ids: List[str] = []
    goal_id: Optional[str] = None
    requires_human_approval: bool = False


class AgentActionResponse(BaseModel):
    id: str
    company_id: str
    agent_name: str
    action_type: str
    context: dict
    reasoning: str
    output: dict
    artifact_ids: List[str]
    goal_id: Optional[str]
    requires_human_approval: bool
    approval_status: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.post("/actions", response_model=AgentActionResponse)
async def create_agent_action(
    action: AgentActionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent action"""
    db_action = AgentAction(
        company_id=action.company_id,
        agent_name=action.agent_name,
        action_type=action.action_type,
        context=action.context,
        reasoning=action.reasoning,
        output=action.output,
        artifact_ids=action.artifact_ids,
        goal_id=action.goal_id,
        requires_human_approval=action.requires_human_approval,
        approval_status=ApprovalStatus.PENDING if action.requires_human_approval else None
    )
    db.add(db_action)
    await db.commit()
    await db.refresh(db_action)
    return db_action


@router.get("/actions/{action_id}", response_model=AgentActionResponse)
async def get_agent_action(
    action_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get agent action by ID"""
    result = await db.execute(
        select(AgentAction).where(AgentAction.id == action_id)
    )
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(status_code=404, detail="Agent action not found")
    
    return action


@router.get("/actions/company/{company_id}", response_model=List[AgentActionResponse])
async def get_company_agent_actions(
    company_id: str,
    agent_name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get agent actions for a company"""
    query = select(AgentAction).where(AgentAction.company_id == company_id)
    
    if agent_name:
        query = query.where(AgentAction.agent_name == agent_name)
    
    query = query.order_by(AgentAction.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    actions = result.scalars().all()
    return actions


@router.post("/actions/{action_id}/approve")
async def approve_agent_action(
    action_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Approve an agent action requiring human approval"""
    result = await db.execute(
        select(AgentAction).where(AgentAction.id == action_id)
    )
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(status_code=404, detail="Agent action not found")
    
    action.approval_status = ApprovalStatus.APPROVED
    await db.commit()
    await db.refresh(action)
    
    return {"success": True, "message": "Action approved"}


@router.post("/actions/{action_id}/reject")
async def reject_agent_action(
    action_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Reject an agent action requiring human approval"""
    result = await db.execute(
        select(AgentAction).where(AgentAction.id == action_id)
    )
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(status_code=404, detail="Agent action not found")
    
    action.approval_status = ApprovalStatus.REJECTED
    await db.commit()
    await db.refresh(action)
    
    return {"success": True, "message": "Action rejected"}