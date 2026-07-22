from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
from app.services.agent_reasoning import build_reasoning_prompt, call_llm_for_reasoning, fallback_reasoning
from app.services.agent_actions import action_executor
from app.models.goal import Goal
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class CustomerIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="customer_intelligence",
            description="Customer behavior analysis and health scoring agent",
            permissions=["read_artifacts", "read_crm", "read_email", "analyze_customers", "update_health_score", "post_slack"],
        )

    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        try:
            db: AsyncSession = context.additional_context.get('db_session')
            company_id = context.company_id
            email_artifacts = []
            crm_artifacts = []
            support_artifacts = []
            slack_artifacts = []
            if db:
                from app.services.artifact_store import artifact_store_service
                email = await artifact_store_service.semantic_search(db, company_id, "customer email support", limit=10)
                email_artifacts = email if isinstance(email, list) else []
                crm = await artifact_store_service.semantic_search(db, company_id, "customer deal contact crm", limit=10)
                crm_artifacts = crm if isinstance(crm, list) else []
                support = await artifact_store_service.semantic_search(db, company_id, "support ticket issue problem", limit=10)
                support_artifacts = support if isinstance(support, list) else []
                slack = await artifact_store_service.semantic_search(db, company_id, "customer client mention", limit=10)
                slack_artifacts = slack if isinstance(slack, list) else []
            all_relevant = list(email_artifacts) + list(crm_artifacts) + list(support_artifacts) + list(slack_artifacts)
            context.relevant_artifacts = [
                {
                    'id': a.get('id') if isinstance(a, dict) else getattr(a, 'id', None),
                    'content': a.get('content') if isinstance(a, dict) else getattr(a, 'content', ''),
                    'source_tool': a.get('source_tool') if isinstance(a, dict) else str(getattr(a, 'source_tool', '')),
                    'artifact_type': a.get('artifact_type') if isinstance(a, dict) else str(getattr(a, 'artifact_type', '')),
                    'author': a.get('author') if isinstance(a, dict) else getattr(a, 'author', ''),
                    'created_at': a.get('created_at') if isinstance(a, dict) else str(getattr(a, 'created_at', '')),
                    'metadata': a.get('metadata') if isinstance(a, dict) else getattr(a, 'artifact_metadata', {}),
                }
                for a in all_relevant
            ]
            context.additional_context.update({
                'email_count': len(email_artifacts),
                'crm_activity_count': len(crm_artifacts),
                'support_ticket_count': len(support_artifacts),
                'slack_mention_count': len(slack_artifacts),
                'analysis_type': 'customer_health_monitoring',
            })
            logger.info(f"CustomerIntelligence Agent retrieved {len(context.relevant_artifacts)} artifacts")
            return context
        except Exception as e:
            logger.error(f"CustomerIntelligence context retrieval failed: {e}")
            return context

    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        try:
            summary = context.additional_context
            prompt = build_reasoning_prompt(
                agent_name="Customer Intelligence Agent",
                context_summary=summary,
                relevant_artifacts=context.relevant_artifacts,
                current_goal_state=context.current_goal_state,
                agent_intelligence=context.agent_intelligence,
                instructions="""Monitor customer health across email, CRM, and support.
Action types: alert_slack, generate_summary, update_health_score, no_action.
- If at-risk customers found: alert_slack with details
- If support volume high: generate_summary
- Health score updates require human approval
- Alerts do NOT require approval""",
            )
            result = await call_llm_for_reasoning(prompt)
            if result:
                return AgentReasoning(**result)
            return fallback_reasoning(
                {
                    "default_should_act": False, "default_action_type": "no_action",
                    "default_reasoning": "No customer health issues detected",
                    "default_output": {}, "default_confidence": 0.8,
                    "default_requires_approval": False,
                    "conditions": [
                        {
                            "field": "support_ticket_count", "op": "gt", "threshold": 10,
                            "should_act": True, "action_type": "generate_summary",
                            "reasoning": "High support volume ({value} tickets)",
                            "output": {"summary_type": "support_volume", "ticket_count": 0, "recommendation": "Review ticket trends"},
                            "confidence": 0.8,
                        },
                    ],
                },
                summary,
            )
        except Exception as e:
            logger.error(f"CustomerIntelligence reasoning failed: {e}")
            return AgentReasoning(
                should_act=False, action_type="no_action",
                reasoning=f"Reasoning failed: {str(e)}", output={},
                confidence=0.0, requires_human_approval=False,
            )

    async def phase3_action_execution(self, reasoning: AgentReasoning, context: AgentContext) -> AgentAction:
        try:
            action = AgentAction(
                agent_name=self.name, action_type=reasoning.action_type,
                context={'company_id': context.company_id, 'relevant_artifacts': context.relevant_artifacts,
                         'current_goal_state': context.current_goal_state, 'additional_context': context.additional_context},
                reasoning=reasoning.reasoning, output=reasoning.output,
                artifact_ids=[a.get('id') for a in context.relevant_artifacts if a.get('id')],
                goal_id=context.additional_context.get('goal_id'),
                requires_human_approval=reasoning.requires_human_approval, confidence=reasoning.confidence,
            )
            if reasoning.should_act and not reasoning.requires_human_approval:
                db = context.additional_context.get('db_session')
                await action_executor.execute_action(
                    reasoning.action_type, reasoning.output, db, context.company_id, self.name,
                )
            logger.info(f"CustomerIntelligence executed action: {reasoning.action_type}")
            return action
        except Exception as e:
            logger.error(f"CustomerIntelligence action execution failed: {e}")
            raise

    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        try:
            db = action.context.get('additional_context', {}).get('db_session')
            company_id = action.context.get('company_id')
            goal_before = 0.0
            if db and company_id:
                result = await db.execute(
                    select(Goal).where(Goal.company_id == company_id, Goal.metric_name == 'monthly_churn_rate_pct')
                )
                goal = result.scalar_one_or_none()
                if goal:
                    goal_before = float(goal.current_value or 0)
            return AgentOutcome(success=True, goal_metric_before=goal_before, goal_metric_after=goal_before, delta=0.0)
        except Exception as e:
            logger.error(f"CustomerIntelligence outcome measurement failed: {e}")
            return AgentOutcome(success=False, goal_metric_before=0.0, goal_metric_after=0.0, delta=0.0, human_feedback=f"Failed: {str(e)}")

    async def phase5_learning(self, action: AgentAction, outcome: AgentOutcome) -> None:
        try:
            if outcome.success:
                self.update_intelligence({'successful_patterns': [{'action_type': action.action_type, 'successful': True}], 'success_rate': 0.75})
            else:
                self.update_intelligence({'failed_patterns': [{'action_type': action.action_type, 'successful': False}], 'success_rate': 0.65})
            logger.info("CustomerIntelligence learning completed")
        except Exception as e:
            logger.error(f"CustomerIntelligence learning failed: {e}")
