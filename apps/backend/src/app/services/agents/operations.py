from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
from app.services.agent_reasoning import build_reasoning_prompt, call_llm_for_reasoning, fallback_reasoning
from app.services.agent_actions import action_executor
from app.models.goal import Goal
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class OperationsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="operations",
            description="Task coordination and workflow automation agent",
            permissions=[
                "read_artifacts", "read_tasks", "update_status",
                "create_tickets", "post_slack",
            ],
        )

    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        try:
            db: AsyncSession = context.additional_context.get('db_session')
            company_id = context.company_id
            overdue_artifacts = []
            blocker_artifacts = []
            sprint_artifacts = []
            if db:
                from app.services.artifact_store import artifact_store_service
                overdue = await artifact_store_service.semantic_search(
                    db, company_id, "overdue task ticket", limit=10
                )
                overdue_artifacts = overdue if not isinstance(overdue, list) else overdue
                blocker = await artifact_store_service.semantic_search(
                    db, company_id, "blocked stuck waiting need approval", limit=10
                )
                blocker_artifacts = blocker if not isinstance(blocker, list) else blocker
                sprint = await artifact_store_service.semantic_search(
                    db, company_id, "sprint completion rate", limit=10
                )
                sprint_artifacts = sprint if not isinstance(sprint, list) else sprint
            all_relevant = list(overdue_artifacts) + list(blocker_artifacts) + list(sprint_artifacts)
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
                'overdue_task_count': len(overdue_artifacts),
                'blocker_message_count': len(blocker_artifacts),
                'sprint_artifact_count': len(sprint_artifacts),
                'analysis_type': 'operations_monitoring',
            })
            logger.info(f"Operations Agent retrieved {len(context.relevant_artifacts)} relevant artifacts")
            return context
        except Exception as e:
            logger.error(f"Operations Agent context retrieval failed: {e}")
            return context

    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        try:
            summary = context.additional_context
            prompt = build_reasoning_prompt(
                agent_name="Operations Agent",
                context_summary=summary,
                relevant_artifacts=context.relevant_artifacts,
                current_goal_state=context.current_goal_state,
                agent_intelligence=context.agent_intelligence,
                instructions="""Monitor tasks across Linear/Jira/Asana/GitHub.
Action types: alert_slack, generate_briefing, update_status, reassign_task, no_action.
- If overdue tasks > 3: alert_slack with summary
- If blockers > 5: alert_slack with blocker summary
- If sprint completion below target: generate_briefing
- Simple alerts do NOT require human approval
- Task reassignment always requires human approval""",
            )
            result = await call_llm_for_reasoning(prompt)
            if result:
                return AgentReasoning(**result)
            return fallback_reasoning(
                {
                    "default_should_act": False,
                    "default_action_type": "no_action",
                    "default_reasoning": "No immediate action required",
                    "default_output": {},
                    "default_confidence": 0.8,
                    "default_requires_approval": False,
                    "conditions": [
                        {
                            "field": "overdue_task_count", "op": "gt", "threshold": 3,
                            "should_act": True, "action_type": "alert_slack",
                            "reasoning": "Found {value} overdue tasks requiring attention",
                            "output": {"message": "Operations Alert: {value} tasks overdue", "channel": "#engineering"},
                            "confidence": 0.9,
                        },
                        {
                            "field": "blocker_message_count", "op": "gt", "threshold": 5,
                            "should_act": True, "action_type": "alert_slack",
                            "reasoning": "Detected {value} blocker messages",
                            "output": {"message": "Operations Alert: {value} blockers detected", "channel": "#engineering"},
                            "confidence": 0.85,
                        },
                    ],
                },
                summary,
            )
        except Exception as e:
            logger.error(f"Operations Agent reasoning failed: {e}")
            return AgentReasoning(
                should_act=False, action_type="no_action",
                reasoning=f"Reasoning failed: {str(e)}", output={},
                confidence=0.0, requires_human_approval=False,
            )

    async def phase3_action_execution(self, reasoning: AgentReasoning, context: AgentContext) -> AgentAction:
        try:
            action = AgentAction(
                agent_name=self.name,
                action_type=reasoning.action_type,
                context={
                    'company_id': context.company_id,
                    'relevant_artifacts': context.relevant_artifacts,
                    'current_goal_state': context.current_goal_state,
                    'additional_context': context.additional_context,
                },
                reasoning=reasoning.reasoning,
                output=reasoning.output,
                artifact_ids=[a.get('id') for a in context.relevant_artifacts if a.get('id')],
                goal_id=context.additional_context.get('goal_id'),
                requires_human_approval=reasoning.requires_human_approval,
                confidence=reasoning.confidence,
            )
            if reasoning.should_act and not reasoning.requires_human_approval:
                db = context.additional_context.get('db_session')
                await action_executor.execute_action(
                    reasoning.action_type, reasoning.output,
                    db, context.company_id, self.name,
                )
            logger.info(f"Operations Agent executed action: {reasoning.action_type}")
            return action
        except Exception as e:
            logger.error(f"Operations Agent action execution failed: {e}")
            raise

    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        try:
            db = action.context.get('additional_context', {}).get('db_session')
            company_id = action.context.get('company_id')
            goal_before = 0.0
            goal_after = 0.0
            if db and company_id:
                result = await db.execute(
                    select(Goal).where(
                        Goal.company_id == company_id,
                        Goal.metric_name == 'sprint_completion_rate',
                    )
                )
                goal = result.scalar_one_or_none()
                if goal:
                    goal_before = float(goal.current_value or 0)
            return AgentOutcome(
                success=True,
                goal_metric_before=goal_before,
                goal_metric_after=goal_before,
                delta=0.0,
            )
        except Exception as e:
            logger.error(f"Operations Agent outcome measurement failed: {e}")
            return AgentOutcome(
                success=False, goal_metric_before=0.0, goal_metric_after=0.0,
                delta=0.0, human_feedback=f"Measurement failed: {str(e)}",
            )

    async def phase5_learning(self, action: AgentAction, outcome: AgentOutcome) -> None:
        try:
            if outcome.success:
                self.update_intelligence({
                    'successful_patterns': [{
                        'action_type': action.action_type,
                        'context_clues': action.context.get('additional_context', {}),
                        'successful': True,
                    }],
                    'success_rate': 0.8,
                })
            else:
                self.update_intelligence({
                    'failed_patterns': [{
                        'action_type': action.action_type,
                        'context_clues': action.context.get('additional_context', {}),
                        'successful': False,
                    }],
                    'success_rate': 0.6,
                })
            logger.info("Operations Agent learning completed")
        except Exception as e:
            logger.error(f"Operations Agent learning failed: {e}")
