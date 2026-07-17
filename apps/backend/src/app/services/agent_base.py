from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum
import json


class AgentPhase(Enum):
    """The five phases of agent execution"""
    CONTEXT_RETRIEVAL = "context_retrieval"
    REASONING = "reasoning"
    ACTION_EXECUTION = "action_execution"
    OUTCOME_MEASUREMENT = "outcome_measurement"
    LEARNING = "learning"


class AgentContext(BaseModel):
    """Context package for agent reasoning"""
    company_id: str
    relevant_artifacts: List[Dict[str, Any]]
    current_goal_state: Dict[str, Any]
    recent_actions: List[Dict[str, Any]]
    agent_intelligence: Dict[str, Any]
    additional_context: Dict[str, Any] = {}


class AgentReasoning(BaseModel):
    """Agent reasoning output"""
    should_act: bool
    action_type: str
    reasoning: str
    output: Dict[str, Any]
    confidence: float
    requires_human_approval: bool
    suggested_goal_id: Optional[str] = None


class AgentAction(BaseModel):
    """Structured agent action"""
    agent_name: str
    action_type: str
    context: Dict[str, Any]
    reasoning: str
    output: Dict[str, Any]
    artifact_ids: List[str]
    goal_id: Optional[str]
    requires_human_approval: bool
    confidence: float


class AgentOutcome(BaseModel):
    """Measured outcome of agent action"""
    success: bool
    goal_metric_before: float
    goal_metric_after: float
    delta: float
    human_feedback: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all LoopOS agents with five-phase pattern"""
    
    def __init__(self, name: str, description: str, permissions: List[str]):
        self.name = name
        self.description = description
        self.permissions = permissions
        self.intelligence: Dict[str, Any] = {}
    
    @abstractmethod
    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        """
        Phase 1: Context Retrieval
        - Retrieve relevant artifacts via semantic search
        - Get current goal state
        - Load recent action history
        - Load company-specific agent intelligence
        """
        pass
    
    @abstractmethod
    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        """
        Phase 2: Reasoning
        - Send context to LLM
        - Return structured decision about whether to act
        - Always include reasoning trace (no black boxes)
        """
        pass
    
    @abstractmethod
    async def phase3_action_execution(self, reasoning: AgentReasoning, context: AgentContext) -> AgentAction:
        """
        Phase 3: Action Execution
        - If approval required, queue in approval inbox
        - If auto-execute, perform the action
        - Log action with full context and reasoning
        """
        pass
    
    @abstractmethod
    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        """
        Phase 4: Outcome Measurement
        - Compare goal metric before and after action
        - Record outcome (success/failure, delta value)
        - Capture human feedback if available
        """
        pass
    
    @abstractmethod
    async def phase5_learning(self, action: AgentAction, outcome: AgentOutcome) -> None:
        """
        Phase 5: Learning
        - Update company-specific agent intelligence
        - Extract patterns from success/failure
        - Improve future decision-making
        """
        pass
    
    async def execute(self, initial_context: AgentContext) -> tuple[AgentAction, Optional[AgentOutcome]]:
        """
        Execute the complete five-phase agent workflow
        """
        # Phase 1: Context Retrieval
        enriched_context = await self.phase1_context_retrieval(initial_context)
        
        # Phase 2: Reasoning
        reasoning = await self.phase2_reasoning(enriched_context)
        
        # Phase 3: Action Execution
        action = await self.phase3_action_execution(reasoning, enriched_context)
        
        # Phase 4: Outcome Measurement (only if action was executed)
        outcome = None
        if reasoning.should_act:
            outcome = await self.phase4_outcome_measurement(action)
        
        # Phase 5: Learning (only if action was executed and outcome measured)
        if outcome:
            await self.phase5_learning(action, outcome)
        
        return action, outcome
    
    def has_permission(self, permission: str) -> bool:
        """Check if agent has specific permission"""
        return permission in self.permissions
    
    def update_intelligence(self, new_intelligence: Dict[str, Any]) -> None:
        """Update agent's learned intelligence"""
        self.intelligence.update(new_intelligence)
    
    def get_intelligence(self) -> Dict[str, Any]:
        """Get current agent intelligence"""
        return self.intelligence.copy()