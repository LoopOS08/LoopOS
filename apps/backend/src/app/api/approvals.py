from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.agent_action import AgentAction, ApprovalStatus

router = APIRouter()


class ApprovalInboxResponse(BaseModel):
    pending_actions: List[dict]
    total_count: int


@router.get("/inbox", response_model=ApprovalInboxResponse)
async def get_approval_inbox(
    company_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get all pending actions requiring human approval"""
    result = await db.execute(
        select(AgentAction)
        .where(AgentAction.company_id == company_id)
        .where(AgentAction.requires_human_approval == True)
        .where(AgentAction.approval_status == ApprovalStatus.PENDING)
        .order_by(AgentAction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    pending_actions = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(
        select(AgentAction)
        .where(AgentAction.company_id == company_id)
        .where(AgentAction.requires_human_approval == True)
        .where(AgentAction.approval_status == ApprovalStatus.PENDING)
    )
    total_count = len(count_result.scalars().all())
    
    return ApprovalInboxResponse(
        pending_actions=[
            {
                'id': action.id,
                'agent_name': action.agent_name,
                'action_type': action.action_type,
                'reasoning': action.reasoning,
                'output': action.output,
                'confidence': action.confidence,
                'created_at': action.created_at.isoformat(),
                'artifact_ids': action.artifact_ids,
                'goal_id': action.goal_id
            }
            for action in pending_actions
        ],
        total_count=total_count
    )


class ApprovalActionRequest(BaseModel):
    action_id: str
    approved: bool
    feedback: Optional[str] = None


@router.post("/process")
async def process_approval(
    request: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process an approval (approve or reject)"""
    result = await db.execute(
        select(AgentAction).where(AgentAction.id == request.action_id)
    )
    action = result.scalar_one_or_none()
    
    if not action:
        raise HTTPException(status_code=404, detail="Agent action not found")
    
    if action.approval_status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Action has already been processed")
    
    # Update approval status
    if request.approved:
        action.approval_status = ApprovalStatus.APPROVED
    else:
        action.approval_status = ApprovalStatus.REJECTED
    
    # Add feedback if provided
    if request.feedback:
        # Store feedback in context or create a separate feedback mechanism
        action.context['human_feedback'] = request.feedback
    
    await db.commit()
    await db.refresh(action)
    
    # If approved, trigger the action execution
    if request.approved:
        # TODO: Execute the approved action
        # This would call the agent's action execution method
        pass
    
    return {
        "success": True,
        "message": f"Action {'approved' if request.approved else 'rejected'}",
        "action_id": action.id,
        "approval_status": action.approval_status.value
    }


class ApprovalHistoryResponse(BaseModel):
    processed_actions: List[dict]
    total_count: int


@router.get("/history", response_model=ApprovalHistoryResponse)
async def get_approval_history(
    company_id: str,
    agent_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get history of processed approvals"""
    query = select(AgentAction).where(
        AgentAction.company_id == company_id,
        AgentAction.requires_human_approval == True,
        AgentAction.approval_status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])
    )
    
    if agent_name:
        query = query.where(AgentAction.agent_name == agent_name)
    
    query = query.order_by(AgentAction.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    processed_actions = result.scalars().all()
    
    # Get total count
    count_query = select(AgentAction).where(
        AgentAction.company_id == company_id,
        AgentAction.requires_human_approval == True,
        AgentAction.approval_status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])
    )
    
    if agent_name:
        count_query = count_query.where(AgentAction.agent_name == agent_name)
    
    count_result = await db.execute(count_query)
    total_count = len(count_result.scalars().all())
    
    return ApprovalHistoryResponse(
        processed_actions=[
            {
                'id': action.id,
                'agent_name': action.agent_name,
                'action_type': action.action_type,
                'reasoning': action.reasoning,
                'approval_status': action.approval_status.value,
                'created_at': action.created_at.isoformat(),
                'updated_at': action.updated_at.isoformat(),
                'human_feedback': action.context.get('human_feedback')
            }
            for action in processed_actions
        ],
        total_count=total_count
    )


class ApprovalStatsResponse(BaseModel):
    total_pending: int
    total_approved: int
    total_rejected: int
    approval_rate: float
    by_agent: dict


@router.get("/stats", response_model=ApprovalStatsResponse)
async def get_approval_stats(
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get approval statistics"""
    # Get all approval-required actions
    result = await db.execute(
        select(AgentAction).where(
            AgentAction.company_id == company_id,
            AgentAction.requires_human_approval == True
        )
    )
    all_actions = result.scalars().all()
    
    total_pending = sum(1 for a in all_actions if a.approval_status == ApprovalStatus.PENDING)
    total_approved = sum(1 for a in all_actions if a.approval_status == ApprovalStatus.APPROVED)
    total_rejected = sum(1 for a in all_actions if a.approval_status == ApprovalStatus.REJECTED)
    
    total_processed = total_approved + total_rejected
    approval_rate = (total_approved / total_processed * 100) if total_processed > 0 else 0
    
    # Break down by agent
    by_agent = {}
    for action in all_actions:
        agent_name = action.agent_name
        if agent_name not in by_agent:
            by_agent[agent_name] = {
                'pending': 0,
                'approved': 0,
                'rejected': 0
            }
        
        if action.approval_status == ApprovalStatus.PENDING:
            by_agent[agent_name]['pending'] += 1
        elif action.approval_status == ApprovalStatus.APPROVED:
            by_agent[agent_name]['approved'] += 1
        elif action.approval_status == ApprovalStatus.REJECTED:
            by_agent[agent_name]['rejected'] += 1
    
    return ApprovalStatsResponse(
        total_pending=total_pending,
        total_approved=total_approved,
        total_rejected=total_rejected,
        approval_rate=round(approval_rate, 2),
        by_agent=by_agent
    )
