from typing import Dict, Any, List, Optional
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
import logging
import json

logger = logging.getLogger(__name__)


class CustomerIntelligenceAgent(BaseAgent):
    """
    Customer Intelligence Agent - Customer behavior analysis and health scoring
    
    Role: Monitors every customer touchpoint across email, CRM, support tools, and Slack
    Goal Monitored: monthly_churn_rate_pct (e.g., < 3%), customer_health_score per customer
    """
    
    def __init__(self):
        super().__init__(
            name="customer_intelligence",
            description="Customer behavior analysis and health scoring agent",
            permissions=[
                "read_artifacts",
                "read_crm",
                "read_email",
                "analyze_customers",
                "update_health_score",
                "post_slack"
            ]
        )
    
    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        """
        Phase 1: Context Retrieval
        - Retrieve customer emails (30 days)
        - Get CRM notes and activity (30 days)
        - Get deal history
        - Get support ticket history
        - Get Slack mentions
        """
        try:
            company_id = context.company_id
            
            # For now, use placeholder data since semantic_search needs db session
            email_artifacts = []
            crm_artifacts = []
            support_artifacts = []
            slack_artifacts = []
            
            # In production, these would call artifact_store_service.semantic_search with actual db
            # email_artifacts = await artifact_store_service.semantic_search(...)
            # crm_artifacts = await artifact_store_service.semantic_search(...)
            # support_artifacts = await artifact_store_service.semantic_search(...)
            # slack_artifacts = await artifact_store_service.semantic_search(...)
            
            # Combine all relevant artifacts
            all_relevant = email_artifacts + crm_artifacts + support_artifacts + slack_artifacts
            
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
            
            # Add customer intelligence specific context
            context.additional_context.update({
                'email_count': len(email_artifacts),
                'crm_activity_count': len(crm_artifacts),
                'support_ticket_count': len(support_artifacts),
                'slack_mention_count': len(slack_artifacts),
                'analysis_type': 'customer_health_monitoring'
            })
            
            logger.info(f"Customer Intelligence Agent retrieved {len(context.relevant_artifacts)} relevant artifacts")
            return context
            
        except Exception as e:
            logger.error(f"Customer Intelligence Agent context retrieval failed: {e}")
            return context
    
    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        """
        Phase 2: Reasoning
        - Analyze customer health signals
        - Determine if action is needed
        - Decide on action type
        """
        try:
            # Extract key information
            email_count = context.additional_context.get('email_count', 0)
            crm_activity_count = context.additional_context.get('crm_activity_count', 0)
            support_ticket_count = context.additional_context.get('support_ticket_count', 0)
            
            # Get current churn goal
            churn_goal = None
            for goal in context.current_goal_state.get('goals', []):
                if goal.get('metric_name') == 'monthly_churn_rate_pct':
                    churn_goal = goal
                    break
            
            # Analyze customer health signals from artifacts
            health_signals = self._analyze_health_signals(context.relevant_artifacts)
            
            # Build reasoning
            at_risk_customers = health_signals.get('at_risk', [])
            healthy_customers = health_signals.get('healthy', [])
            
            should_act = False
            action_type = "no_action"
            reasoning = "No immediate action required"
            output = {}
            confidence = 0.8
            requires_approval = False
            
            if len(at_risk_customers) > 0:
                should_act = True
                action_type = "alert_slack"
                reasoning = f"Detected {len(at_risk_customers)} customers showing churn risk signals"
                output = {
                    "message": f"Customer Intelligence Alert: {len(at_risk_customers)} customers at risk of churn.",
                    "channel": "#customer-success",
                    "at_risk_customers": at_risk_customers[:5],
                    "health_summary": health_signals
                }
                confidence = 0.85
            elif support_ticket_count > 10:
                should_act = True
                action_type = "generate_summary"
                reasoning = f"High support ticket volume ({support_ticket_count}) may indicate customer issues"
                output = {
                    "summary_type": "support_volume",
                    "ticket_count": support_ticket_count,
                    "recommendation": "Review support ticket trends and common issues"
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
            logger.error(f"Customer Intelligence Agent reasoning failed: {e}")
            return AgentReasoning(
                should_act=False,
                action_type="no_action",
                reasoning=f"Reasoning failed due to error: {str(e)}",
                output={},
                confidence=0.0,
                requires_human_approval=False
            )
    
    def _analyze_health_signals(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze artifacts for customer health signals
        """
        at_risk = []
        healthy = []
        
        for artifact in artifacts:
            content = artifact.get('content', '').lower()
            metadata = artifact.get('metadata', {})
            
            # Negative signals
            negative_indicators = ['cancel', 'churn', 'unhappy', 'issue', 'problem', 'complaint', 'frustrated']
            positive_indicators = ['happy', 'great', 'love', 'excellent', 'satisfied', 'upgrade', 'expand']
            
            has_negative = any(indicator in content for indicator in negative_indicators)
            has_positive = any(indicator in content for indicator in positive_indicators)
            
            customer_info = {
                'customer_name': metadata.get('customer_name') or artifact.get('author'),
                'source': artifact.get('source_tool'),
                'signal': 'negative' if has_negative else 'positive' if has_positive else 'neutral',
                'content_preview': artifact.get('content', '')[:200]
            }
            
            if has_negative:
                at_risk.append(customer_info)
            elif has_positive:
                healthy.append(customer_info)
        
        return {
            'at_risk': at_risk,
            'healthy': healthy,
            'total_analyzed': len(artifacts)
        }
    
    async def phase3_action_execution(self, reasoning: AgentReasoning, context: AgentContext) -> AgentAction:
        """
        Phase 3: Action Execution
        - Execute the determined action
        - Queue for approval if required
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
            
            logger.info(f"Customer Intelligence Agent executed action: {reasoning.action_type}")
            return action
            
        except Exception as e:
            logger.error(f"Customer Intelligence Agent action execution failed: {e}")
            raise
    
    async def _execute_action(self, action: AgentAction, reasoning: AgentReasoning) -> None:
        """
        Execute the actual action
        """
        try:
            if reasoning.action_type == "alert_slack":
                logger.info(f"Would post customer health alert to Slack: {reasoning.output.get('message')}")
                
            elif reasoning.action_type == "generate_summary":
                logger.info(f"Would generate customer intelligence summary")
                
            elif reasoning.action_type == "update_health_score":
                # TODO: Update health scores in CRM
                logger.info(f"Would update customer health scores in CRM")
                
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
            logger.error(f"Customer Intelligence Agent outcome measurement failed: {e}")
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
                    'success_rate': 0.75
                })
            else:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': False
                }
                self.update_intelligence({
                    'failed_patterns': [pattern],
                    'success_rate': 0.65
                })
            
            logger.info("Customer Intelligence Agent learning completed")
            
        except Exception as e:
            logger.error(f"Customer Intelligence Agent learning failed: {e}")
