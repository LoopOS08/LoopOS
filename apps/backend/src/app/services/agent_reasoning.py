from typing import Dict, Any, List, Optional
from app.services.agent_base import AgentReasoning
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

_llm_client = None


def _get_llm_client():
    global _llm_client
    if _llm_client is None and settings.OPENAI_API_KEY:
        from openai import AsyncOpenAI
        _llm_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _llm_client


def build_reasoning_prompt(
    agent_name: str,
    context_summary: Dict[str, Any],
    relevant_artifacts: List[Dict[str, Any]],
    current_goal_state: Dict[str, Any],
    agent_intelligence: Dict[str, Any],
    instructions: str,
) -> str:
    artifacts_text = ""
    for a in relevant_artifacts[:10]:
        artifacts_text += f"- [{a.get('source_tool', '?')}/{a.get('artifact_type', '?')}] {a.get('author', '?')}: {a.get('content', '')[:300]}\n"

    goals_text = ""
    for g in current_goal_state.get('goals', []):
        goals_text += f"- {g.get('metric_name')}: current={g.get('current_value')} target={g.get('target_value')} status={g.get('status')}\n"

    intelligence_text = ""
    if agent_intelligence:
        intelligence_text = json.dumps(agent_intelligence, indent=2)

    return f"""You are the {agent_name} agent for LoopOS.

{instructions}

Current goal state:
{goals_text or 'No goals configured.'}

Company-specific intelligence learned for this agent:
{intelligence_text or 'No patterns learned yet.'}

Relevant artifacts from company tools:
{artifacts_text or 'No relevant artifacts found.'}

Context summary:
{json.dumps(context_summary, indent=2)}

Respond with a JSON object ONLY (no other text):
{{
    "should_act": true/false,
    "action_type": "one_of: ...",
    "reasoning": "detailed reasoning text",
    "output": {{ ... action-specific output fields }},
    "confidence": 0.0-1.0,
    "requires_human_approval": true/false
}}"""


async def call_llm_for_reasoning(prompt: str) -> Optional[Dict[str, Any]]:
    client = _get_llm_client()
    if client:
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000,
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0] if "```" in text else text
            return json.loads(text.strip())
        except Exception as e:
            logger.warning(f"LLM reasoning call failed: {e}")
    return None


def fallback_reasoning(
    rules: Dict[str, Any],
    context_summary: Dict[str, Any],
) -> AgentReasoning:
    should_act = rules.get("default_should_act", False)
    action_type = rules.get("default_action_type", "no_action")
    reasoning = rules.get("default_reasoning", "No action needed")
    output = rules.get("default_output", {})
    confidence = rules.get("default_confidence", 0.5)
    requires_approval = rules.get("default_requires_approval", False)

    conditions = rules.get("conditions", [])
    for condition in conditions:
        field_value = context_summary.get(condition.get("field"))
        if field_value is not None and condition.get("op", "gt") == "gt":
            if field_value > condition.get("threshold", 0):
                should_act = condition.get("should_act", True)
                action_type = condition.get("action_type", action_type)
                reasoning = condition.get("reasoning", reasoning).format(
                    value=field_value,
                    threshold=condition.get("threshold", 0),
                )
                output = condition.get("output", output)
                confidence = condition.get("confidence", confidence)
                requires_approval = condition.get("requires_approval", requires_approval)
                break
        elif field_value is not None and condition.get("op", "gt") == "lt":
            if field_value < condition.get("threshold", 0):
                should_act = condition.get("should_act", True)
                action_type = condition.get("action_type", action_type)
                reasoning = condition.get("reasoning", reasoning).format(
                    value=field_value,
                    threshold=condition.get("threshold", 0),
                )
                output = condition.get("output", output)
                confidence = condition.get("confidence", confidence)
                requires_approval = condition.get("requires_approval", requires_approval)
                break

    return AgentReasoning(
        should_act=should_act,
        action_type=action_type,
        reasoning=reasoning,
        output=output,
        confidence=confidence,
        requires_human_approval=requires_approval,
    )
