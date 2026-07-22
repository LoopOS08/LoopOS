from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
from app.services.agent_reasoning import build_reasoning_prompt, call_llm_for_reasoning, fallback_reasoning
from app.services.agent_actions import action_executor
from app.models.goal import Goal
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class RevenueAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="revenue",
            description="Sales pipeline monitoring and revenue tracking agent",
            permissions=["read_artifacts", "read_crm", "analyze_deals", "update_deal_notes", "post_slack"],
        )

    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        try:
            db: AsyncSession = context.additional_context.get('db_session')
            company_id = context.company_id
            deal_artifacts = []
            stalled_artifacts = []
            email_artifacts = []
            revenue_artifacts = []
            if db:
                from app.services.artifact_store import artifact_store_service
                deals = await artifact_store_service.semantic_search(db, company_id, "deal opportunity pipeline", limit=15)
                deal_artifacts = deals if isinstance(deals, list) else []
                stalled = await artifact_store_service.semantic_search(db, company_id, "stalled no activity deal follow up", limit=10)
                stalled_artifacts = stalled if isinstance(stalled, list) else []
                emails = await artifact_store_service.semantic_search(db, company_id, "deal proposal email quote", limit=10)
                email_artifacts = emails if isinstance(emails, list) else []
                revenue = await artifact_store_service.semantic_search(db, company_id, "revenue payment subscription", limit=10)
                revenue_artifacts = revenue if isinstance(revenue, list) else []
            all_relevant = list(deal_artifacts) + list(stalled_artifacts) + list(email_artifacts) + list(revenue_artifacts)
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
                'open_deal_count': len(deal_artifacts),
                'stalled_deal_count': len(stalled_artifacts),
                'deal_email_count': len(email_artifacts),
                'analysis_type': 'revenue_pipeline_monitoring',
            })
            logger.info(f"Revenue Agent retrieved {len(context.relevant_artifacts)} artifacts")
            return context
        except Exception as e:
            logger.error(f"Revenue context retrieval failed: {e}")
            return context

    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        try:
            summary = context.additional_context
            prompt = build_reasoning_prompt(
                agent_name="Revenue Agent",
                context_summary=summary,
                relevant_artifacts=context.relevant_artifacts,
                current_goal_state=context.current_goal_state,
                agent_intelligence=context.agent_intelligence,
                instructions="""Monitor sales pipeline across HubSpot/Salesforce.
Action types: alert_slack, generate_briefing, daily_briefing, no_action.
- If stalled deals > 3: alert_slack
- If revenue < 70% of target: generate_briefing
- Daily pipeline briefing if open deals exist
- Alerts do NOT require approval
- Sending outreach requires approval""",
            )
            result = await call_llm_for_reasoning(prompt)
            if result:
                return AgentReasoning(**result)
            return fallback_reasoning(
                {
                    "default_should_act": False, "default_action_type": "no_action",
                    "default_reasoning": "Pipeline healthy", "default_output": {},
                    "default_confidence": 0.8, "default_requires_approval": False,
                    "conditions": [
                        {
                            "field": "stalled_deal_count", "op": "gt", "threshold": 3,
                            "should_act": True, "action_type": "alert_slack",
                            "reasoning": "{value} stalled deals detected",
                            "output": {"message": "Revenue Alert: {value} deals stalled", "channel": "#sales"},
                            "confidence": 0.9,
                        },
                    ],
                },
                summary,
            )
        except Exception as e:
            logger.error(f"Revenue reasoning failed: {e}")
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
            logger.info(f"Revenue executed action: {reasoning.action_type}")
            return action
        except Exception as e:
            logger.error(f"Revenue action execution failed: {e}")
            raise

    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        try:
            db = action.context.get('additional_context', {}).get('db_session')
            company_id = action.context.get('company_id')
            goal_before = 0.0
            if db and company_id:
                result = await db.execute(
                    select(Goal).where(Goal.company_id == company_id, Goal.metric_name == 'monthly_revenue_usd')
                )
                goal = result.scalar_one_or_none()
                if goal:
                    goal_before = float(goal.current_value or 0)
            return AgentOutcome(success=True, goal_metric_before=goal_before, goal_metric_after=goal_before, delta=0.0)
        except Exception as e:
            return AgentOutcome(success=False, goal_metric_before=0.0, goal_metric_after=0.0, delta=0.0, human_feedback=f"Failed: {str(e)}")

    async def phase5_learning(self, action: AgentAction, outcome: AgentOutcome) -> None:
        try:
            if outcome.success:
                self.update_intelligence({'successful_patterns': [{'action_type': action.action_type, 'successful': True}], 'success_rate': 0.78})
            else:
                self.update_intelligence({'failed_patterns': [{'action_type': action.action_type, 'successful': False}], 'success_rate': 0.68})
            logger.info("Revenue learning completed")
        except Exception as e:
            logger.error(f"Revenue learning failed: {e}")
