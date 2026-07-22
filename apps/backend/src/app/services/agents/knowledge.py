from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
from app.services.agent_reasoning import build_reasoning_prompt, call_llm_for_reasoning, fallback_reasoning
from app.services.agent_actions import action_executor
from app.models.goal import Goal
from app.models.decision import Decision
from sqlalchemy import select
import re
import logging

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="knowledge",
            description="Decision extraction and knowledge management agent",
            permissions=["read_artifacts", "extract_decisions", "create_knowledge", "update_notion", "post_slack"],
        )
        self.decision_patterns = [
            r'we should', r'let\'s go with', r'decided to', r'we\'ll',
            r'agreed to', r'the plan is', r'going with', r'confirmed',
            r'final decision', r'we have decided',
        ]

    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        try:
            db: AsyncSession = context.additional_context.get('db_session')
            company_id = context.company_id
            decision_messages = []
            meeting_artifacts = []
            document_artifacts = []
            if db:
                from app.services.artifact_store import artifact_store_service
                decisions = await artifact_store_service.semantic_search(db, company_id, "decision decided agreed plan", limit=20)
                decision_messages = decisions if isinstance(decisions, list) else []
                meetings = await artifact_store_service.semantic_search(db, company_id, "meeting transcript recording", limit=10)
                meeting_artifacts = meetings if isinstance(meetings, list) else []
                docs = await artifact_store_service.semantic_search(db, company_id, "document spec roadmap", limit=10)
                document_artifacts = docs if isinstance(docs, list) else []
            all_relevant = list(decision_messages) + list(meeting_artifacts) + list(document_artifacts)
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
            decision_artifacts = self._filter_decision_artifacts(context.relevant_artifacts)
            context.additional_context.update({
                'decision_message_count': len(decision_messages),
                'meeting_count': len(meeting_artifacts),
                'document_count': len(document_artifacts),
                'total_decisions_detected': len(decision_artifacts),
                'analysis_type': 'decision_extraction',
            })
            context.relevant_artifacts = decision_artifacts
            logger.info(f"Knowledge Agent retrieved {len(context.relevant_artifacts)} decision artifacts")
            return context
        except Exception as e:
            logger.error(f"Knowledge context retrieval failed: {e}")
            return context

    def _filter_decision_artifacts(self, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for a in artifacts:
            content = a.get('content', '').lower()
            for pattern in self.decision_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    result.append(a)
                    break
        return result

    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        try:
            summary = context.additional_context
            prompt = build_reasoning_prompt(
                agent_name="Knowledge Agent",
                context_summary=summary,
                relevant_artifacts=context.relevant_artifacts,
                current_goal_state=context.current_goal_state,
                agent_intelligence=context.agent_intelligence,
                instructions="""Extract and document decisions from artifacts.
Action types: document_decision, document_and_publish, no_action.
- If decisions detected: document_decision
- If significant decisions found: document_and_publish
- Check existing decisions for deduplication
- Decisions do NOT require human approval
- Publishing to Notion requires approval""",
            )
            result = await call_llm_for_reasoning(prompt)
            if result:
                return AgentReasoning(**result)
            decisions = self._extract_decisions(context.relevant_artifacts)
            should_act = len(decisions) > 0
            action_type = "no_action"
            reasoning = "No decisions requiring documentation"
            output = {}
            confidence = 0.8
            if should_act:
                action_type = "document_decision"
                reasoning = f"Extracted {len(decisions)} decisions"
                output = {"decisions": decisions, "action": "create_decision_entries", "total_decisions": len(decisions)}
                confidence = 0.85
            return AgentReasoning(
                should_act=should_act, action_type=action_type, reasoning=reasoning,
                output=output, confidence=confidence, requires_human_approval=False,
            )
        except Exception as e:
            logger.error(f"Knowledge reasoning failed: {e}")
            return AgentReasoning(
                should_act=False, action_type="no_action",
                reasoning=f"Reasoning failed: {str(e)}", output={},
                confidence=0.0, requires_human_approval=False,
            )

    def _extract_decisions(self, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        decisions = []
        for artifact in artifacts:
            content = artifact.get('content', '')
            author = artifact.get('author', 'Unknown')
            source = artifact.get('source_tool', 'unknown')
            for pattern in self.decision_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    decision_context = content[start:end].strip()
                    significance = self._determine_significance(decision_context)
                    decisions.append({
                        'content': decision_context, 'author': author, 'source': source,
                        'detected_at': artifact.get('created_at', ''),
                        'artifact_id': artifact.get('id'), 'significance': significance,
                        'pattern_matched': pattern,
                    })
        return decisions

    def _determine_significance(self, decision_context: str) -> str:
        high_keywords = ['strategy', 'roadmap', 'pricing', 'funding', 'hiring', 'launch',
                         'partnership', 'acquisition', 'pivot', 'architecture', 'policy']
        for kw in high_keywords:
            if kw in decision_context.lower():
                return 'high'
        return 'medium' if len(decision_context) > 100 else 'low'

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
                await action_executor.execute_action(reasoning.action_type, reasoning.output, db, context.company_id, self.name)
            logger.info(f"Knowledge executed action: {reasoning.action_type}")
            return action
        except Exception as e:
            logger.error(f"Knowledge action execution failed: {e}")
            raise

    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        try:
            db = action.context.get('additional_context', {}).get('db_session')
            company_id = action.context.get('company_id')
            goal_before = 0.0
            if db and company_id:
                result = await db.execute(
                    select(Goal).where(Goal.company_id == company_id, Goal.metric_name == 'decision_capture_rate')
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
                self.update_intelligence({'successful_patterns': [{'action_type': action.action_type, 'successful': True}], 'success_rate': 0.82})
            else:
                self.update_intelligence({'failed_patterns': [{'action_type': action.action_type, 'successful': False}], 'success_rate': 0.72})
            logger.info("Knowledge learning completed")
        except Exception as e:
            logger.error(f"Knowledge learning failed: {e}")
