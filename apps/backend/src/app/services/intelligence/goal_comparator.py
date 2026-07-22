from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.goal import Goal, GoalStatus, GoalOperator
from app.services.agent_runtime import agent_runtime
from sqlalchemy import select
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class GoalStateComparator:
    def __init__(self):
        self._running = False

    async def evaluate_goal(self, goal: Goal) -> GoalStatus:
        if goal.operator == GoalOperator.LESS_THAN:
            if goal.current_value <= goal.target_value:
                return GoalStatus.ON_TRACK
            elif goal.current_value <= goal.target_value * 1.2:
                return GoalStatus.AT_RISK
            else:
                return GoalStatus.OFF_TRACK
        elif goal.operator == GoalOperator.GREATER_THAN:
            if goal.current_value >= goal.target_value:
                return GoalStatus.ON_TRACK
            elif goal.current_value >= goal.target_value * 0.8:
                return GoalStatus.AT_RISK
            else:
                return GoalStatus.OFF_TRACK
        else:
            if goal.current_value == goal.target_value:
                return GoalStatus.ON_TRACK
            return GoalStatus.OFF_TRACK

    async def run_comparison(self, db: AsyncSession, company_id: str) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(Goal).where(Goal.company_id == company_id)
        )
        goals = result.scalars().all()
        updates = []
        for goal in goals:
            old_status = goal.status
            new_status = await self.evaluate_goal(goal)
            goal.status = new_status
            updates.append({
                'goal_id': goal.id,
                'metric_name': goal.metric_name,
                'current_value': goal.current_value,
                'target_value': goal.target_value,
                'old_status': old_status.value if old_status else None,
                'new_status': new_status.value,
                'trigger_agent': new_status == GoalStatus.OFF_TRACK,
            })
        await db.commit()

        for update in updates:
            if update['trigger_agent']:
                agent_map = {
                    'sprint_completion_rate': 'operations',
                    'monthly_churn_rate_pct': 'customer_intelligence',
                    'monthly_revenue_usd': 'revenue',
                    'pipeline_velocity_days': 'revenue',
                    'decision_capture_rate': 'knowledge',
                    'decision_to_spec_conversion_rate': 'spec',
                    'sprint_priority_alignment_pct': 'alignment',
                    'customer_health_score': 'customer_intelligence',
                    'expense_vs_budget': 'finance',
                    'cash_flow': 'finance',
                }
                agent_name = agent_map.get(update['metric_name'])
                if agent_name and agent_name in agent_runtime.registered_agents:
                    logger.info(f"Goal {update['metric_name']} OFF_TRACK, triggering {agent_name}")
                    context = await agent_runtime.build_agent_context(
                        db, company_id, agent_name,
                        {'trigger': 'goal_off_track', 'goal_id': update['goal_id']},
                    )
                    await agent_runtime.dispatch_agent(agent_name, context, db)

        logger.info(f"Goal comparison completed for {company_id}: {len(updates)} goals evaluated, "
                     f"{sum(1 for u in updates if u['trigger_agent'])} agents triggered")
        return updates

    async def run_all_companies(self, db: AsyncSession) -> Dict[str, Any]:
        from app.models.company import Company
        companies = await db.execute(select(Company))
        results = {}
        for company in companies.scalars().all():
            try:
                updates = await self.run_comparison(db, company.id)
                results[company.id] = updates
            except Exception as e:
                logger.error(f"Goal comparison failed for company {company.id}: {e}")
                results[company.id] = {'error': str(e)}
        return results


goal_comparator = GoalStateComparator()
