from typing import Dict, Any, List, Optional
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
import logging
import json

logger = logging.getLogger(__name__)


class RevenueAgent(BaseAgent):
    """
    Revenue Agent - Sales pipeline monitoring and revenue tracking
    
    Role: Monitors the sales pipeline and revenue health continuously across HubSpot and Salesforce
    Goal Monitored: monthly_revenue_usd, pipeline_velocity_days — targets set by company
    """
    
    def __init__(self):
        super().__init__(
            name="revenue",
            description="Sales pipeline monitoring and revenue tracking agent",
            permissions=[
                "read_artifacts",
                "read_crm",
                "analyze_deals",
                "update_deal_notes",
                "post_slack"
            ]
        )
    
    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        """
        Phase 1: Context Retrieval
        - Retrieve all open deals and current stages
        - Get deals with no activity >5 days
        - Get email threads related to active deals
        - Get monthly revenue vs target
        - Get historical win/loss patterns
        """
        try:
            company_id = context.company_id
            
            # For now, use placeholder data since semantic_search needs db session
            deal_artifacts = []
            stalled_artifacts = []
            email_artifacts = []
            revenue_artifacts = []
            
            # In production, these would call artifact_store_service.semantic_search with actual db
            # deal_artifacts = await artifact_store_service.semantic_search(...)
            # stalled_artifacts = await artifact_store_service.semantic_search(...)
            # email_artifacts = await artifact_store_service.semantic_search(...)
            # revenue_artifacts = await artifact_store_service.semantic_search(...)
            
            # Combine all relevant artifacts
            all_relevant = deal_artifacts + stalled_artifacts + email_artifacts + revenue_artifacts
            
            # Update context with retrieved artifacts
            context.relevant_artifacts = [
                {
                    'id': artifact.get('id'),
                    'content': artifact.get('content'),
                    'source_tool': artifact.get('source_tool'),
                    'artifact_type': artifact.get('artifact_type'),
                    'author': artifact.get('author'),
                    'created_at': artifact.get('created_at'),
                    'metadata': artifact.get('metadata', {})
                }
                for artifact in all_relevant
            ]
            
            # Add revenue-specific context
            context.additional_context.update({
                'open_deal_count': len(deal_artifacts),
                'stalled_deal_count': len(stalled_artifacts),
                'deal_email_count': len(email_artifacts),
                'revenue_artifact_count': len(revenue_artifacts),
                'analysis_type': 'revenue_pipeline_monitoring'
            })
            
            logger.info(f"Revenue Agent retrieved {len(context.relevant_artifacts)} relevant artifacts")
            return context
            
        except Exception as e:
            logger.error(f"Revenue Agent context retrieval failed: {e}")
            return context
    
    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        """
        Phase 2: Reasoning
        - Analyze pipeline health
        - Identify stalled deals
        - Determine if action is needed
        """
        try:
            # Extract key information
            open_deal_count = context.additional_context.get('open_deal_count', 0)
            stalled_deal_count = context.additional_context.get('stalled_deal_count', 0)
            
            # Get current revenue goal
            revenue_goal = None
            for goal in context.current_goal_state.get('goals', []):
                if goal.get('metric_name') in ['monthly_revenue_usd', 'pipeline_velocity_days']:
                    revenue_goal = goal
                    break
            
            # Analyze pipeline health
            pipeline_health = self._analyze_pipeline_health(context.relevant_artifacts)
            
            should_act = False
            action_type = "no_action"
            reasoning = "No immediate action required"
            output = {}
            confidence = 0.8
            requires_approval = False
            
            if stalled_deal_count > 3:
                should_act = True
                action_type = "alert_slack"
                reasoning = f"Detected {stalled_deal_count} stalled deals requiring attention"
                output = {
                    "message": f"Revenue Alert: {stalled_deal_count} deals stalled with no recent activity.",
                    "channel": "#sales",
                    "stalled_deals": pipeline_health.get('stalled_deals', [])[:5],
                    "total_pipeline_value": pipeline_health.get('total_value', 0)
                }
                confidence = 0.9
            elif revenue_goal and revenue_goal.get('metric_name') == 'monthly_revenue_usd':
                current = revenue_goal.get('current_value', 0)
                target = revenue_goal.get('target_value', 0)
                if current < target * 0.7:  # Less than 70% of target
                    should_act = True
                    action_type = "generate_briefing"
                    reasoning = f"Monthly revenue (${current:,.0f}) significantly below target (${target:,.0f})"
                    output = {
                        "briefing_type": "revenue_status",
                        "current_revenue": current,
                        "target_revenue": target,
                        "gap_percentage": ((target - current) / target * 100) if target > 0 else 0,
                        "recommendations": [
                            "Review stalled deals",
                            "Accelerate proposal process",
                            "Focus on high-value opportunities"
                        ]
                    }
                    confidence = 0.85
            elif open_deal_count > 0:
                should_act = True
                action_type = "daily_briefing"
                reasoning = f"Generating daily pipeline briefing with {open_deal_count} open deals"
                output = {
                    "briefing_type": "daily_pipeline",
                    "open_deals": open_deal_count,
                    "pipeline_health": pipeline_health,
                    "key_insights": pipeline_health.get('insights', [])
                }
                confidence = 0.8
            
            return AgentReasoning(
                should_act=should_act,
                action_type=action_type,
                reasoning=reasoning,
                output=output,
                confidence=confidence,
                requires_human_approval=requires_approval
            )
            
        except Exception as e:
            logger.error(f"Revenue Agent reasoning failed: {e}")
            return AgentReasoning(
                should_act=False,
                action_type="no_action",
                reasoning=f"Reasoning failed due to error: {str(e)}",
                output={},
                confidence=0.0,
                requires_human_approval=False
            )
    
    def _analyze_pipeline_health(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze pipeline health from artifacts
        """
        stalled_deals = []
        active_deals = []
        total_value = 0
        
        for artifact in artifacts:
            if artifact.get('artifact_type') != 'deal':
                continue
                
            metadata = artifact.get('metadata', {})
            content = artifact.get('content', '').lower()
            
            # Check if deal is stalled
            stalled_indicators = ['no activity', 'stalled', 'quiet', 'waiting', 'follow up needed']
            is_stalled = any(indicator in content for indicator in stalled_indicators)
            
            deal_info = {
                'deal_name': metadata.get('deal_name') or 'Unknown Deal',
                'value': metadata.get('amount', 0),
                'stage': metadata.get('stage', 'Unknown'),
                'last_activity': artifact.get('created_at'),
                'source': artifact.get('source_tool')
            }
            
            total_value += deal_info['value']
            
            if is_stalled:
                stalled_deals.append(deal_info)
            else:
                active_deals.append(deal_info)
        
        return {
            'stalled_deals': stalled_deals,
            'active_deals': active_deals,
            'total_value': total_value,
            'stalled_value': sum(d['value'] for d in stalled_deals),
            'insights': [
                f"{len(stalled_deals)} deals stalled representing ${sum(d['value'] for d in stalled_deals):,.0f}",
                f"{len(active_deals)} active deals in pipeline",
                f"Total pipeline value: ${total_value:,.0f}"
            ]
        }
    
    async def phase3_action_execution(self, reasoning: AgentReasoning, context: AgentContext) -> AgentAction:
        """
        Phase 3: Action Execution
        """
        try:
            action = AgentAction(
                agent_name=self.name,
                action_type=reasoning.action_type,
                context={
                    'company_id': context.company_id,
                    'relevant_artifacts': context.relevant_artifacts,
                    'current_goal_state': context.current_goal_state,
                    'additional_context': context.additional_context
                },
                reasoning=reasoning.reasoning,
                output=reasoning.output,
                artifact_ids=[a.get('id') for a in context.relevant_artifacts if a.get('id')],
                goal_id=context.additional_context.get('goal_id'),
                requires_human_approval=reasoning.requires_human_approval,
                confidence=reasoning.confidence
            )
            
            if reasoning.should_act and not reasoning.requires_human_approval:
                await self._execute_action(action, reasoning)
            
            logger.info(f"Revenue Agent executed action: {reasoning.action_type}")
            return action
            
        except Exception as e:
            logger.error(f"Revenue Agent action execution failed: {e}")
            raise
    
    async def _execute_action(self, action: AgentAction, reasoning: AgentReasoning) -> None:
        """
        Execute the actual action
        """
        try:
            if reasoning.action_type == "alert_slack":
                logger.info(f"Would post revenue alert to Slack: {reasoning.output.get('message')}")
                
            elif reasoning.action_type == "generate_briefing":
                logger.info(f"Would generate revenue briefing")
                
            elif reasoning.action_type == "daily_briefing":
                logger.info(f"Would generate daily pipeline briefing")
                
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            raise
    
    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        """
        Phase 4: Outcome Measurement
        """
        try:
            return AgentOutcome(
                success=True,
                goal_metric_before=0.0,
                goal_metric_after=0.0,
                delta=0.0,
                human_feedback=None
            )
            
        except Exception as e:
            logger.error(f"Revenue Agent outcome measurement failed: {e}")
            return AgentOutcome(
                success=False,
                goal_metric_before=0.0,
                goal_metric_after=0.0,
                delta=0.0,
                human_feedback=f"Measurement failed: {str(e)}"
            )
    
    async def phase5_learning(self, action: AgentAction, outcome: AgentOutcome) -> None:
        """
        Phase 5: Learning
        """
        try:
            if outcome.success:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': True
                }
                self.update_intelligence({
                    'successful_patterns': [pattern],
                    'success_rate': 0.78
                })
            else:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': False
                }
                self.update_intelligence({
                    'failed_patterns': [pattern],
                    'success_rate': 0.68
                })
            
            logger.info("Revenue Agent learning completed")
            
        except Exception as e:
            logger.error(f"Revenue Agent learning failed: {e}")
