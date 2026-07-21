from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.agent_action import AgentAction, ApprovalStatus
from app.services.agent_runtime import agent_runtime
from app.services.agent_base import AgentContext

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


class AgentExecuteRequest(BaseModel):
    company_id: str
    agent_name: str
    additional_context: Optional[dict] = {}


class AgentExecuteResponse(BaseModel):
    success: bool
    agent_name: str
    action_type: str
    reasoning: str
    requires_approval: bool
    confidence: float
    output: dict


@router.post("/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    request: AgentExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Execute a specific agent with given context"""
    try:
        # Build agent context
        context = await agent_runtime.build_agent_context(
            db=db,
            company_id=request.company_id,
            agent_name=request.agent_name,
            additional_context=request.additional_context
        )
        
        # Dispatch agent
        action, outcome = await agent_runtime.dispatch_agent(
            agent_name=request.agent_name,
            context=context,
            db=db
        )
        
        return AgentExecuteResponse(
            success=True,
            agent_name=action.agent_name,
            action_type=action.action_type,
            reasoning=action.reasoning,
            requires_approval=action.requires_human_approval,
            confidence=action.confidence,
            output=action.output
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


class ArtifactDispatchRequest(BaseModel):
    company_id: str
    artifact_type: str
    source_tool: str
    content: str
    artifact_id: Optional[str] = None


class ArtifactDispatchResponse(BaseModel):
    success: bool
    dispatched_agents: List[str]
    results: List[dict]


@router.post("/dispatch-artifact", response_model=ArtifactDispatchResponse)
async def dispatch_artifact(
    request: ArtifactDispatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Dispatch an artifact to all relevant agents based on routing rules"""
    try:
        # Dispatch artifact to agents
        results = await agent_runtime.dispatch_artifact(
            artifact_type=request.artifact_type,
            source_tool=request.source_tool,
            content=request.content,
            company_id=request.company_id,
            db=db,
            artifact_id=request.artifact_id
        )
        
        # Extract results
        dispatched_agents = []
        result_summaries = []
        
        for action, outcome in results:
            dispatched_agents.append(action.agent_name)
            result_summaries.append({
                'agent_name': action.agent_name,
                'action_type': action.action_type,
                'reasoning': action.reasoning,
                'requires_approval': action.requires_human_approval,
                'confidence': action.confidence,
                'output': action.output
            })
        
        return ArtifactDispatchResponse(
            success=True,
            dispatched_agents=dispatched_agents,
            results=result_summaries
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Artifact dispatch failed: {str(e)}")


@router.get("/list")
async def list_agents():
    """List all registered agents"""
    agents = agent_runtime.list_agents()
    
    return {
        "success": True,
        "agents": agents,
        "count": len(agents)
    }


class AgentInfoResponse(BaseModel):
    name: str
    description: str
    permissions: List[str]


@router.get("/info/{agent_name}", response_model=AgentInfoResponse)
async def get_agent_info(agent_name: str):
    """Get information about a specific agent"""
    agent = agent_runtime.get_agent(agent_name)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentInfoResponse(
        name=agent.name,
        description=agent.description,
        permissions=agent.permissions
    )


class AgentStatusResponse(BaseModel):
    agent_name: str
    is_registered: bool
    intelligence: dict
    recent_actions: List[dict]


@router.get("/status/{agent_name}", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_name: str,
    company_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get status and intelligence for a specific agent"""
    agent = agent_runtime.get_agent(agent_name)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Load agent intelligence
    intelligence = await agent_runtime.load_agent_intelligence(
        db=db,
        company_id=company_id,
        agent_name=agent_name
    )
    
    # Get recent actions for this agent
    result = await db.execute(
        select(AgentAction)
        .where(AgentAction.company_id == company_id)
        .where(AgentAction.agent_name == agent_name)
        .order_by(AgentAction.created_at.desc())
        .limit(10)
    )
    recent_actions = result.scalars().all()
    
    return AgentStatusResponse(
        agent_name=agent_name,
        is_registered=True,
        intelligence=intelligence,
        recent_actions=[
            {
                'id': action.id,
                'action_type': action.action_type,
                'reasoning': action.reasoning,
                'created_at': action.created_at.isoformat(),
                'approval_status': action.approval_status.value if action.approval_status else None
            }
            for action in recent_actions
        ]
    )


class AgentIntelligenceUpdateRequest(BaseModel):
    company_id: str
    agent_name: str
    intelligence: dict


@router.post("/intelligence/update")
async def update_agent_intelligence(
    request: AgentIntelligenceUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update agent intelligence manually"""
    try:
        await agent_runtime.update_agent_intelligence(
            db=db,
            company_id=request.company_id,
            agent_name=request.agent_name,
            intelligence=request.intelligence
        )
        
        return {"success": True, "message": "Agent intelligence updated"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update intelligence: {str(e)}")


class RoutingRulesResponse(BaseModel):
    rules: dict


@router.get("/routing/rules", response_model=RoutingRulesResponse)
async def get_routing_rules():
    """Get all routing rules"""
    rules = agent_runtime.dispatcher.get_all_routing_rules()
    return RoutingRulesResponse(rules=rules)