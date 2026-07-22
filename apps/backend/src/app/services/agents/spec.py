from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
from app.services.agent_reasoning import build_reasoning_prompt, call_llm_for_reasoning, fallback_reasoning
from app.services.agent_actions import action_executor
from app.models.goal import Goal
from app.models.spec import Spec
from app.models.decision import Decision
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class SpecAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="spec",
            description="Decision-to-specification generation agent",
            permissions=["read_artifacts", "create_tickets", "update_requirements", "create_notion", "post_slack"],
        )

    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        try:
            db: AsyncSession = context.additional_context.get('db_session')
            company_id = context.company_id
            decision_artifacts = []
            spec_artifacts = []
            github_artifacts = []
            if db:
                from app.services.artifact_store import artifact_store_service
                decisions = await artifact_store_service.semantic_search(db, company_id, "decision decided agreed spec", limit=15)
                decision_artifacts = decisions if isinstance(decisions, list) else []
                specs = await artifact_store_service.semantic_search(db, company_id, "spec requirement acceptance criteria", limit=10)
                spec_artifacts = specs if isinstance(specs, list) else []
                gh = await artifact_store_service.semantic_search(db, company_id, "github repository code", limit=10)
                github_artifacts = gh if isinstance(gh, list) else []
            all_relevant = list(decision_artifacts) + list(spec_artifacts) + list(github_artifacts)
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
            unspecced = self._filter_unspecced_decisions(context.relevant_artifacts, spec_artifacts)
            context.additional_context.update({
                'decision_count': len(decision_artifacts),
                'existing_spec_count': len(spec_artifacts),
                'unspecced_decision_count': len(unspecced),
                'analysis_type': 'spec_generation',
            })
            context.relevant_artifacts = unspecced
            logger.info(f"Spec Agent found {len(unspecced)} unspecced decisions")
            return context
        except Exception as e:
            logger.error(f"Spec context retrieval failed: {e}")
            return context

    def _filter_unspecced_decisions(self, artifacts: List[Dict[str, Any]], existing_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        spec_titles = set()
        for s in existing_specs:
            content = s.get('content', '').lower() if isinstance(s, dict) else getattr(s, 'content', '').lower()
            spec_titles.add(content[:50])
        unspecced = []
        for a in artifacts:
            content = a.get('content', '').lower() if isinstance(a, dict) else getattr(a, 'content', '').lower()
            decision_keywords = ['decided', 'should', "let's", 'agreed', 'plan', 'going to']
            is_decision = any(kw in content for kw in decision_keywords)
            if is_decision and content[:50] not in spec_titles:
                unspecced.append(a)
        return unspecced

    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        try:
            summary = context.additional_context
            unspecced_count = summary.get('unspecced_decision_count', 0)
            prompt = build_reasoning_prompt(
                agent_name="Spec Agent",
                context_summary=summary, relevant_artifacts=context.relevant_artifacts,
                current_goal_state=context.current_goal_state, agent_intelligence=context.agent_intelligence,
                instructions="""Generate specs from unspecced decisions.
Action types: create_spec, no_action.
- If unspecced decisions exist: create_spec
- XL effort specs require human approval
- S/M/L specs are auto-approved
- Specs include: title, context, acceptance criteria, dependencies, effort, assignee, priority""",
            )
            result = await call_llm_for_reasoning(prompt)
            if result:
                return AgentReasoning(**result)
            specs = self._generate_specs(context.relevant_artifacts)
            if specs:
                xl_specs = [s for s in specs if s.get('estimated_effort') == 'XL']
                requires_approval = len(xl_specs) > 0
                return AgentReasoning(
                    should_act=True, action_type="create_spec",
                    reasoning=f"Generated {len(specs)} specs, {len(xl_specs)} XL",
                    output={"specs": specs, "action": "create_tickets_and_specs", "total_specs": len(specs)},
                    confidence=0.85, requires_human_approval=requires_approval,
                )
            return AgentReasoning(
                should_act=False, action_type="no_action",
                reasoning="No decisions requiring specs",
                output={}, confidence=0.8, requires_human_approval=False,
            )
        except Exception as e:
            logger.error(f"Spec reasoning failed: {e}")
            return AgentReasoning(
                should_act=False, action_type="no_action",
                reasoning=f"Reasoning failed: {str(e)}", output={},
                confidence=0.0, requires_human_approval=False,
            )

    def _generate_specs(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        specs = []
        for d in decisions:
            spec = self._create_spec(d)
            if spec:
                specs.append(spec)
        return specs

    def _create_spec(self, decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            content = decision.get('content', '')
            author = decision.get('author', 'Unknown')
            source = decision.get('source_tool', 'unknown')
            words = content.split()
            title = ' '.join(words[:10]).capitalize() if len(words) > 10 else content[:50].capitalize()
            effort = self._estimate_effort(content)
            criteria = [
                "Implementation meets the requirements specified in the decision",
                "Code is reviewed and approved by at least one team member",
                "Tests are written and passing for the new functionality",
            ]
            cl = content.lower()
            if 'api' in cl:
                criteria.append("API endpoints are documented and tested")
            if 'database' in cl or 'data' in cl:
                criteria.append("Data migration is considered and executed if needed")
            assignee = self._suggest_assignee(content, author)
            priority = self._determine_priority(content)
            return {
                'title': title,
                'context': f"Decision by {author} in {source}: {content[:200]}",
                'acceptance_criteria': criteria[:5],
                'dependencies': [],
                'estimated_effort': effort,
                'suggested_assignee': assignee,
                'priority': priority,
                'source_decision': content[:500],
                'author': author,
                'decision_id': decision.get('id'),
            }
        except Exception as e:
            logger.error(f"Failed to create spec: {e}")
            return None

    def _estimate_effort(self, content: str) -> str:
        cl = content.lower()
        if any(w in cl for w in ['rewrite', 'architecture', 'migration', 'infrastructure', 'platform']):
            return 'XL'
        if any(w in cl for w in ['feature', 'integration', 'system', 'module']):
            return 'L'
        if any(w in cl for w in ['update', 'improve', 'enhance', 'fix']):
            return 'M'
        if any(w in cl for w in ['small', 'minor', 'simple', 'quick']):
            return 'S'
        return 'M'

    def _suggest_assignee(self, content: str, author: str) -> str:
        cl = content.lower()
        if 'backend' in cl or 'api' in cl:
            return 'Backend Team'
        elif 'frontend' in cl or 'ui' in cl:
            return 'Frontend Team'
        elif 'design' in cl:
            return 'Design Team'
        return author

    def _determine_priority(self, content: str) -> str:
        cl = content.lower()
        if any(w in cl for w in ['urgent', 'critical', 'important', 'priority', 'asap']):
            return 'high'
        if any(w in cl for w in ['later', 'eventually', 'nice to have', 'maybe']):
            return 'low'
        return 'medium'

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
            logger.info(f"Spec executed action: {reasoning.action_type}")
            return action
        except Exception as e:
            logger.error(f"Spec action execution failed: {e}")
            raise

    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        try:
            db = action.context.get('additional_context', {}).get('db_session')
            company_id = action.context.get('company_id')
            goal_before = 0.0
            if db and company_id:
                result = await db.execute(
                    select(Goal).where(Goal.company_id == company_id, Goal.metric_name == 'decision_to_spec_conversion_rate')
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
                self.update_intelligence({'successful_patterns': [{'action_type': action.action_type, 'successful': True}], 'success_rate': 0.83})
            else:
                self.update_intelligence({'failed_patterns': [{'action_type': action.action_type, 'successful': False}], 'success_rate': 0.73})
            logger.info("Spec learning completed")
        except Exception as e:
            logger.error(f"Spec learning failed: {e}")
