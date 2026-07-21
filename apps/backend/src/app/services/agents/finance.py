from typing import Dict, Any, List, Optional
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
import logging
import json

logger = logging.getLogger(__name__)


class FinanceAgent(BaseAgent):
    """
    Finance Agent - Financial metrics and anomaly detection
    
    Role: Monitors financial health in real time across Stripe, QuickBooks, and Xero
    Goal Monitored: monthly_revenue_usd, monthly_churn_rate_pct, cash_flow, expense_vs_budget
    """
    
    def __init__(self):
        super().__init__(
            name="finance",
            description="Financial metrics and anomaly detection agent",
            permissions=[
                "read_artifacts",
                "read_financials",
                "analyze_metrics",
                "detect_anomalies"
            ]
        )
        # Finance Agent is read-only by design for security
    
    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        """
        Phase 1: Context Retrieval
        - Retrieve all Stripe transactions (30 days)
        - Get subscription status changes
        - Get monthly revenue vs target
        - Get month-over-month comparison
        - Get learned anomaly baseline
        """
        try:
            company_id = context.company_id
            
            # For now, use placeholder data since semantic_search needs db session
            transaction_artifacts = []
            subscription_artifacts = []
            accounting_artifacts = []
            
            # In production, these would call artifact_store_service.semantic_search with actual db
            # transaction_artifacts = await artifact_store_service.semantic_search(...)
            # subscription_artifacts = await artifact_store_service.semantic_search(...)
            # accounting_artifacts = await artifact_store_service.semantic_search(...)
            
            # Combine all relevant artifacts
            all_relevant = transaction_artifacts + subscription_artifacts + accounting_artifacts
            
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
            
            # Add finance-specific context
            context.additional_context.update({
                'transaction_count': len(transaction_artifacts),
                'subscription_event_count': len(subscription_artifacts),
                'accounting_artifact_count': len(accounting_artifacts),
                'analysis_type': 'financial_health_monitoring'
            })
            
            logger.info(f"Finance Agent retrieved {len(context.relevant_artifacts)} relevant artifacts")
            return context
            
        except Exception as e:
            logger.error(f"Finance Agent context retrieval failed: {e}")
            return context
    
    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        """
        Phase 2: Reasoning
        - Analyze financial metrics
        - Detect anomalies
        - Determine if action is needed
        """
        try:
            # Analyze financial data
            financial_analysis = self._analyze_financial_data(context.relevant_artifacts)
            
            # Get current financial goals
            revenue_goal = None
            churn_goal = None
            for goal in context.current_goal_state.get('goals', []):
                if goal.get('metric_name') == 'monthly_revenue_usd':
                    revenue_goal = goal
                elif goal.get('metric_name') == 'monthly_churn_rate_pct':
                    churn_goal = goal
            
            anomalies = financial_analysis.get('anomalies', [])
            daily_revenue = financial_analysis.get('daily_revenue', 0)
            subscription_cancellations = financial_analysis.get('cancellations', 0)
            
            should_act = False
            action_type = "no_action"
            reasoning = "No financial anomalies detected"
            output = {}
            confidence = 0.8
            requires_approval = False
            
            if len(anomalies) > 0:
                should_act = True
                action_type = "alert_anomaly"
                reasoning = f"Detected {len(anomalies)} financial anomalies requiring attention"
                output = {
                    "message": f"Finance Alert: {len(anomalies)} anomalies detected in financial data.",
                    "channel": "#finance",
                    "anomalies": anomalies,
                    "severity": "high" if len(anomalies) > 2 else "medium"
                }
                confidence = 0.9
            elif subscription_cancellations > 3:
                should_act = True
                action_type = "alert_churn"
                reasoning = f"High subscription cancellation rate: {subscription_cancellations} cancellations detected"
                output = {
                    "message": f"Finance Alert: {subscription_cancellations} subscription cancellations detected.",
                    "channel": "#finance",
                    "cancellation_count": subscription_cancellations,
                    "affected_plans": financial_analysis.get('affected_plans', [])
                }
                confidence = 0.85
            elif revenue_goal:
                current = revenue_goal.get('current_value', 0)
                target = revenue_goal.get('target_value', 0)
                if current < target * 0.8:  # Less than 80% of target
                    should_act = True
                    action_type = "generate_summary"
                    reasoning = f"Monthly revenue (${current:,.0f}) below target (${target:,.0f})"
                    output = {
                        "summary_type": "revenue_status",
                        "current_revenue": current,
                        "target_revenue": target,
                        "gap_percentage": ((target - current) / target * 100) if target > 0 else 0,
                        "daily_revenue": daily_revenue
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
            logger.error(f"Finance Agent reasoning failed: {e}")
            return AgentReasoning(
                should_act=False,
                action_type="no_action",
                reasoning=f"Reasoning failed due to error: {str(e)}",
                output={},
                confidence=0.0,
                requires_human_approval=False
            )
    
    def _analyze_financial_data(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze financial data for anomalies and patterns
        """
        anomalies = []
        cancellations = 0
        daily_revenue = 0
        affected_plans = []
        
        for artifact in artifacts:
            metadata = artifact.get('metadata', {})
            content = artifact.get('content', '').lower()
            
            # Check for payment failures
            if 'failed' in content or 'refund' in content:
                anomalies.append({
                    'type': 'payment_issue',
                    'description': content[:200],
                    'amount': metadata.get('amount', 0),
                    'timestamp': artifact.get('created_at')
                })
            
            # Check for subscription cancellations
            if 'cancel' in content or 'churn' in content:
                cancellations += 1
                plan = metadata.get('plan', 'unknown')
                if plan not in affected_plans:
                    affected_plans.append(plan)
            
            # Calculate daily revenue from successful transactions
            if artifact.get('artifact_type') == 'transaction':
                amount = metadata.get('amount', 0)
                if amount > 0 and 'failed' not in content:
                    daily_revenue += amount
        
        # Detect unusual patterns
        if daily_revenue > 0 and len(artifacts) > 0:
            avg_transaction = daily_revenue / len([a for a in artifacts if a.get('artifact_type') == 'transaction'])
            if avg_transaction > 10000:  # Unusually high average transaction
                anomalies.append({
                    'type': 'unusual_transaction_size',
                    'description': f'Average transaction amount ${avg_transaction:,.0f} is unusually high',
                    'severity': 'medium'
                })
        
        return {
            'anomalies': anomalies,
            'cancellations': cancellations,
            'daily_revenue': daily_revenue,
            'affected_plans': affected_plans
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
            
            logger.info(f"Finance Agent executed action: {reasoning.action_type}")
            return action
            
        except Exception as e:
            logger.error(f"Finance Agent action execution failed: {e}")
            raise
    
    async def _execute_action(self, action: AgentAction, reasoning: AgentReasoning) -> None:
        """
        Execute the actual action (Finance Agent is read-only, only generates alerts)
        """
        try:
            if reasoning.action_type == "alert_anomaly":
                logger.info(f"Would post financial anomaly alert: {reasoning.output.get('message')}")
                
            elif reasoning.action_type == "alert_churn":
                logger.info(f"Would post churn alert: {reasoning.output.get('message')}")
                
            elif reasoning.action_type == "generate_summary":
                logger.info(f"Would generate financial summary")
                
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
            logger.error(f"Finance Agent outcome measurement failed: {e}")
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
                    'success_rate': 0.80
                })
            else:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': False
                }
                self.update_intelligence({
                    'failed_patterns': [pattern],
                    'success_rate': 0.70
                })
            
            logger.info("Finance Agent learning completed")
            
        except Exception as e:
            logger.error(f"Finance Agent learning failed: {e}")
