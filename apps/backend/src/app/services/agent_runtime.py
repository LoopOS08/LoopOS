from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_base import BaseAgent, AgentContext, AgentAction, AgentOutcome
from app.models.agent_action import AgentAction as AgentActionModel, ApprovalStatus
from app.models.agent_intelligence import AgentIntelligence
from app.models.artifact import Artifact
from app.models.goal import Goal, GoalStatus
from app.services.artifact_store import artifact_store_service
from app.services.agent_actions import action_executor
from app.services.agents import (
    OperationsAgent,
    CustomerIntelligenceAgent,
    RevenueAgent,
    KnowledgeAgent,
    FinanceAgent,
    AlignmentAgent,
    SpecAgent,
    agent_dispatcher
)
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Runtime environment for agent execution and dispatch"""
    
    def __init__(self):
        self.registered_agents: Dict[str, BaseAgent] = {}
        self.active_executions: Dict[str, Any] = {}
        self.dispatcher = agent_dispatcher
        
        # Auto-register all agents on initialization
        self._register_all_agents()
    
    def _register_all_agents(self) -> None:
        """Register all 7 specialized agents"""
        agents = [
            OperationsAgent(),
            CustomerIntelligenceAgent(),
            RevenueAgent(),
            KnowledgeAgent(),
            FinanceAgent(),
            AlignmentAgent(),
            SpecAgent()
        ]
        
        for agent in agents:
            self.register_agent(agent)
        
        logger.info(f"Registered {len(self.registered_agents)} agents: {list(self.registered_agents.keys())}")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the runtime"""
        self.registered_agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get a registered agent by name"""
        return self.registered_agents.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """List all registered agent names"""
        return list(self.registered_agents.keys())
    
    async def dispatch_agent(
        self,
        agent_name: str,
        context: AgentContext,
        db: AsyncSession
    ) -> tuple[AgentAction, Optional[AgentOutcome]]:
        """Dispatch an agent to execute with given context"""
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent not found: {agent_name}")

        logger.info(f"Dispatching agent: {agent_name}")

        context.additional_context['db_session'] = db

        action, outcome = await agent.execute(context, db=db)

        await self._store_agent_action(db, action)

        if outcome:
            await self._store_agent_outcome(db, action, outcome)

        return action, outcome
    
    async def dispatch_artifact(
        self,
        artifact_type: str,
        source_tool: str,
        content: str,
        company_id: str,
        db: AsyncSession,
        artifact_id: Optional[str] = None
    ) -> List[tuple[AgentAction, Optional[AgentOutcome]]]:
        """
        Dispatch an artifact to all relevant agents based on routing rules
        
        Args:
            artifact_type: Type of artifact (message, email, ticket, etc.)
            source_tool: Source tool (slack, gmail, hubspot, etc.)
            content: Content of the artifact
            company_id: Company ID
            db: Database session
            artifact_id: Optional artifact ID for reference
        
        Returns:
            List of (action, outcome) tuples from all dispatched agents
        """
        # Get agents that should process this artifact
        agent_names = self.dispatcher.route_artifact(artifact_type, source_tool, content)
        
        logger.info(f"Dispatching artifact {artifact_type}/{source_tool} to agents: {agent_names}")
        
        results = []
        
        for agent_name in agent_names:
            try:
                # Build context for this agent
                context = await self.build_agent_context(
                    db=db,
                    company_id=company_id,
                    agent_name=agent_name,
                    additional_context={
                        'artifact_type': artifact_type,
                        'source_tool': source_tool,
                        'artifact_content': content,
                        'artifact_id': artifact_id
                    }
                )
                
                # Dispatch agent
                action, outcome = await self.dispatch_agent(agent_name, context, db)
                results.append((action, outcome))
                
            except Exception as e:
                logger.error(f"Failed to dispatch artifact to agent {agent_name}: {e}")
                # Continue with other agents even if one fails
                continue
        
        return results
    
    async def _store_agent_action(self, db: AsyncSession, action: AgentAction) -> AgentActionModel:
        """Store agent action in database"""
        try:
            db_action = AgentActionModel(
                company_id=action.context.get('company_id'),
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
            
            logger.info(f"Stored agent action: {db_action.id}")
            return db_action
            
        except Exception as e:
            logger.error(f"Failed to store agent action: {e}")
            await db.rollback()
            raise
    
    async def _store_agent_outcome(
        self,
        db: AsyncSession,
        action: AgentAction,
        outcome: AgentOutcome
    ) -> None:
        """Store agent outcome in database"""
        try:
            # Get the stored action
            result = await db.execute(
                select(AgentActionModel).where(
                    AgentActionModel.company_id == action.context.get('company_id'),
                    AgentActionModel.agent_name == action.agent_name,
                    AgentActionModel.action_type == action.action_type
                ).order_by(AgentActionModel.created_at.desc())
            )
            db_action = result.scalar_one_or_none()
            
            if not db_action:
                logger.error("Could not find agent action to link outcome")
                return
            
            # Create outcome record
            from app.models.outcome import Outcome
            db_outcome = Outcome(
                company_id=action.context.get('company_id'),
                agent_action_id=db_action.id,
                goal_metric_before=outcome.goal_metric_before,
                goal_metric_after=outcome.goal_metric_after,
                delta=outcome.delta,
                success=outcome.success,
                human_feedback=outcome.human_feedback
            )
            
            db.add(db_outcome)
            await db.commit()
            
            logger.info(f"Stored agent outcome for action: {db_action.id}")
            
        except Exception as e:
            logger.error(f"Failed to store agent outcome: {e}")
            await db.rollback()
    
    async def load_agent_intelligence(
        self,
        db: AsyncSession,
        company_id: str,
        agent_name: str
    ) -> Dict[str, Any]:
        """Load company-specific agent intelligence"""
        try:
            result = await db.execute(
                select(AgentIntelligence).where(
                    AgentIntelligence.company_id == company_id,
                    AgentIntelligence.agent_name == agent_name
                )
            )
            intelligence = result.scalar_one_or_none()
            
            if intelligence:
                return {
                    'successful_patterns': intelligence.successful_patterns,
                    'failed_patterns': intelligence.failed_patterns,
                    'success_rate': intelligence.success_rate,
                    'sample_size': intelligence.sample_size
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to load agent intelligence: {e}")
            return {}
    
    async def update_agent_intelligence(
        self,
        db: AsyncSession,
        company_id: str,
        agent_name: str,
        intelligence: Dict[str, Any]
    ) -> None:
        """Update company-specific agent intelligence"""
        try:
            result = await db.execute(
                select(AgentIntelligence).where(
                    AgentIntelligence.company_id == company_id,
                    AgentIntelligence.agent_name == agent_name
                )
            )
            db_intelligence = result.scalar_one_or_none()
            
            if db_intelligence:
                # Update existing
                db_intelligence.successful_patterns = intelligence.get('successful_patterns', {})
                db_intelligence.failed_patterns = intelligence.get('failed_patterns', {})
                db_intelligence.success_rate = intelligence.get('success_rate', 0.0)
                db_intelligence.sample_size = intelligence.get('sample_size', 0)
            else:
                # Create new
                db_intelligence = AgentIntelligence(
                    company_id=company_id,
                    agent_name=agent_name,
                    successful_patterns=intelligence.get('successful_patterns', {}),
                    failed_patterns=intelligence.get('failed_patterns', {}),
                    success_rate=intelligence.get('success_rate', 0.0),
                    sample_size=intelligence.get('sample_size', 0)
                )
                db.add(db_intelligence)
            
            await db.commit()
            logger.info(f"Updated agent intelligence for {agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to update agent intelligence: {e}")
            await db.rollback()
    
    async def build_agent_context(
        self,
        db: AsyncSession,
        company_id: str,
        agent_name: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AgentContext:
        """Build context package for agent execution"""
        try:
            intelligence = await self.load_agent_intelligence(db, company_id, agent_name)

            now = datetime.now(timezone.utc)
            seven_days_ago = now - timedelta(days=7)

            artifacts = await artifact_store_service.get_company_artifacts(
                db, company_id, limit=50
            )

            relevant_artifacts = [
                {
                    'id': artifact.id,
                    'content': artifact.content,
                    'source_tool': artifact.source_tool.value if hasattr(artifact.source_tool, 'value') else str(artifact.source_tool),
                    'artifact_type': artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else str(artifact.artifact_type),
                    'author': artifact.author,
                    'created_at': artifact.created_at.isoformat() if artifact.created_at else '',
                    'metadata': artifact.artifact_metadata or {},
                }
                for artifact in artifacts
            ]

            goal_result = await db.execute(
                select(Goal).where(
                    Goal.company_id == company_id
                )
            )
            goals = goal_result.scalars().all()
            goal_list = []
            overall_statuses = set()
            for g in goals:
                status_val = g.status.value if hasattr(g.status, 'value') else str(g.status)
                goal_list.append({
                    'id': g.id,
                    'metric_name': g.metric_name,
                    'target_value': g.target_value,
                    'current_value': g.current_value,
                    'operator': g.operator.value if hasattr(g.operator, 'value') else str(g.operator),
                    'status': status_val,
                })
                overall_statuses.add(status_val)

            if GoalStatus.OFF_TRACK in overall_statuses:
                overall = 'off_track'
            elif GoalStatus.AT_RISK in overall_statuses:
                overall = 'at_risk'
            else:
                overall = 'on_track'

            current_goal_state = {
                'goals': goal_list,
                'overall_status': overall,
            }

            thirty_days_ago = now - timedelta(days=30)
            actions_result = await db.execute(
                select(AgentActionModel).where(
                    AgentActionModel.company_id == company_id,
                    AgentActionModel.agent_name == agent_name,
                    AgentActionModel.created_at >= thirty_days_ago,
                ).order_by(AgentActionModel.created_at.desc()).limit(10)
            )
            recent_actions = []
            for a in actions_result.scalars().all():
                recent_actions.append({
                    'id': a.id,
                    'action_type': a.action_type,
                    'reasoning': a.reasoning,
                    'output': a.output,
                    'approval_status': a.approval_status.value if a.approval_status else None,
                    'created_at': a.created_at.isoformat() if a.created_at else '',
                })

            return AgentContext(
                company_id=company_id,
                relevant_artifacts=relevant_artifacts,
                current_goal_state=current_goal_state,
                recent_actions=recent_actions,
                agent_intelligence=intelligence,
                additional_context=additional_context or {},
            )

        except Exception as e:
            logger.error(f"Failed to build agent context: {e}")
            raise


class PermissionControl:
    """Permission control system for agent actions"""
    
    def __init__(self):
        self.permission_rules: Dict[str, List[str]] = {
            'operations': ['read_artifacts', 'create_tickets', 'update_status', 'post_slack'],
            'customer_intelligence': ['read_artifacts', 'read_crm', 'analyze_customers', 'read_email'],
            'revenue': ['read_artifacts', 'read_crm', 'analyze_deals'],
            'knowledge': ['read_artifacts', 'extract_decisions', 'create_specs'],
            'finance': ['read_artifacts', 'read_financials', 'analyze_metrics'],
            'alignment': ['read_artifacts', 'compare_goals', 'flag_drift'],
            'spec': ['read_artifacts', 'create_tickets', 'update_requirements']
        }
    
    def check_permission(self, agent_name: str, permission: str) -> bool:
        """Check if agent has specific permission"""
        agent_permissions = self.permission_rules.get(agent_name, [])
        return permission in agent_permissions
    
    def get_agent_permissions(self, agent_name: str) -> List[str]:
        """Get all permissions for an agent"""
        return self.permission_rules.get(agent_name, [])
    
    def add_permission(self, agent_name: str, permission: str) -> None:
        """Add permission to agent"""
        if agent_name not in self.permission_rules:
            self.permission_rules[agent_name] = []
        
        if permission not in self.permission_rules[agent_name]:
            self.permission_rules[agent_name].append(permission)
            logger.info(f"Added permission {permission} to agent {agent_name}")
    
    def remove_permission(self, agent_name: str, permission: str) -> None:
        """Remove permission from agent"""
        if agent_name in self.permission_rules:
            if permission in self.permission_rules[agent_name]:
                self.permission_rules[agent_name].remove(permission)
                logger.info(f"Removed permission {permission} from agent {agent_name}")
    
    def validate_action(self, agent_name: str, action_type: str) -> bool:
        """Validate if agent can perform specific action type"""
        # Map action types to permissions
        action_permissions = {
            'create_ticket': 'create_tickets',
            'update_status': 'update_status',
            'analyze_data': 'read_artifacts',
            'extract_decision': 'extract_decisions',
            'create_spec': 'create_specs',
            'flag_drift': 'flag_drift'
        }
        
        required_permission = action_permissions.get(action_type)
        if not required_permission:
            # Unknown action - allow by default but log warning
            logger.warning(f"Unknown action type: {action_type}")
            return True
        
        return self.check_permission(agent_name, required_permission)


# Global instances
agent_runtime = AgentRuntime()
permission_control = PermissionControl()