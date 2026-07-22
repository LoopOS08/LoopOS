from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_action import AgentAction
from app.models.outcome import Outcome
from app.models.agent_intelligence import AgentIntelligence
from app.services.agent_runtime import agent_runtime
from app.core.config import settings
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import logging
import json

logger = logging.getLogger(__name__)

_openai_client = None


def _get_client():
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


class FlywheelEngine:
    async def run_for_company(self, db: AsyncSession, company_id: str) -> Dict[str, Any]:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        actions_result = await db.execute(
            select(AgentAction).where(
                AgentAction.company_id == company_id,
                AgentAction.created_at >= thirty_days_ago,
            )
        )
        all_actions = actions_result.scalars().all()

        agent_groups: Dict[str, List[AgentAction]] = {}
        for action in all_actions:
            agent_groups.setdefault(action.agent_name, []).append(action)

        results = {}
        for agent_name, actions in agent_groups.items():
            try:
                patterns = await self._extract_patterns(db, company_id, agent_name, actions)
                await self._update_intelligence(db, company_id, agent_name, patterns)
                results[agent_name] = patterns
            except Exception as e:
                logger.error(f"Flywheel failed for {agent_name}: {e}")
                results[agent_name] = {'error': str(e)}

        logger.info(f"Flywheel completed for {company_id}: {len(agent_groups)} agents processed")
        return results

    async def _extract_patterns(
        self, db: AsyncSession, company_id: str, agent_name: str, actions: List[AgentAction],
    ) -> Dict[str, Any]:
        successful = []
        failed = []
        total = len(actions)
        for action in actions:
            if action.approval_status == 'rejected':
                failed.append({'action_type': action.action_type, 'reasoning': action.reasoning})
                continue
            outcome_result = await db.execute(
                select(Outcome).where(Outcome.agent_action_id == action.id)
            )
            outcome = outcome_result.scalar_one_or_none()
            if outcome and outcome.success:
                successful.append({'action_type': action.action_type, 'reasoning': action.reasoning})
            elif outcome and not outcome.success:
                failed.append({'action_type': action.action_type, 'reasoning': action.reasoning})
            else:
                successful.append({'action_type': action.action_type, 'reasoning': action.reasoning})

        success_rate = (len(successful) / total * 100) if total > 0 else 0

        client = _get_client()
        patterns_text = ""
        if client and len(successful) + len(failed) > 3:
            try:
                prompt = f"""Analyze these agent actions for {agent_name} at a company and extract patterns.

Successful actions ({len(successful)}):
{json.dumps(successful[:10], indent=2)}

Failed/rejected actions ({len(failed)}):
{json.dumps(failed[:10], indent=2)}

Identify 2-3 specific patterns that distinguish successful from failed actions.
Consider: timing, action types, context, content characteristics.
Return as JSON: {{"patterns": ["pattern1", "pattern2"], "recommendations": ["rec1"]}}"""
                response = await client.chat.completions.create(
                    model="gpt-4o", messages=[{"role": "user", "content": prompt}],
                    temperature=0.3, max_tokens=1000,
                )
                text = response.choices[0].message.content.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    text = text.rsplit("```", 1)[0] if "```" in text else text
                parsed = json.loads(text.strip())
                patterns_text = json.dumps(parsed)
            except Exception as e:
                logger.warning(f"Flywheel LLM pattern extraction failed: {e}")
                patterns_text = json.dumps({
                    "patterns": [f"{agent_name} actions: {success_rate:.0f}% success rate from {total} actions"],
                    "recommendations": ["Continue monitoring for more data"],
                })
        else:
            patterns_text = json.dumps({
                "patterns": [f"{agent_name}: {success_rate:.0f}% success rate ({total} actions)"],
                "recommendations": ["Insufficient data for pattern extraction"],
            })

        return {
            'agent_name': agent_name,
            'total_actions': total,
            'successful_count': len(successful),
            'failed_count': len(failed),
            'success_rate': round(success_rate, 1),
            'patterns': patterns_text,
        }

    async def _update_intelligence(
        self, db: AsyncSession, company_id: str, agent_name: str, patterns: Dict[str, Any],
    ) -> None:
        result = await db.execute(
            select(AgentIntelligence).where(
                AgentIntelligence.company_id == company_id,
                AgentIntelligence.agent_name == agent_name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.successful_patterns = {'patterns': patterns.get('patterns', '')}
            existing.failed_patterns = {'patterns': patterns.get('recommendations', [])}
            existing.success_rate = patterns.get('success_rate', 0) / 100.0
            existing.sample_size = patterns.get('total_actions', 0)
        else:
            db.add(AgentIntelligence(
                company_id=company_id,
                agent_name=agent_name,
                successful_patterns={'patterns': patterns.get('patterns', '')},
                failed_patterns={'patterns': patterns.get('recommendations', [])},
                success_rate=patterns.get('success_rate', 0) / 100.0,
                sample_size=patterns.get('total_actions', 0),
            ))
        await db.commit()


flywheel_engine = FlywheelEngine()
