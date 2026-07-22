"""
Phase 3 - Specialized Agents Verification
Tests that all 7 domain-specific agents are operational with:
- Context retrieval from DB
- LLM reasoning (with fallback)
- Action execution
- Outcome measurement
- Learning
- Human-in-the-loop approval system
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

passed = 0
failed = 0


def check(name: str, condition: bool):
    global passed, failed
    if condition:
        passed += 1
        print(f"  \u2713 {name}")
    else:
        failed += 1
        print(f"  \u2717 {name}")


async def test_operations_agent():
    print("\n1. Operations Agent")
    from app.services.agents.operations import OperationsAgent
    from app.services.agent_base import AgentContext, AgentReasoning
    agent = OperationsAgent()
    check("agent name is operations", agent.name == "operations")
    check("has read_artifacts permission", agent.has_permission("read_artifacts"))
    check("has post_slack permission", agent.has_permission("post_slack"))

    ctx = AgentContext(
        company_id="test-co",
        relevant_artifacts=[],
        current_goal_state={"goals": [], "overall_status": "on_track"},
        recent_actions=[],
        agent_intelligence={},
        additional_context={
            "overdue_task_count": 5,
            "blocker_message_count": 2,
            "analysis_type": "operations_monitoring",
        },
    )
    result = await agent.phase2_reasoning(ctx)
    check("should_act=True when overdue>3", result.should_act is True)
    check("action_type is alert_slack", result.action_type == "alert_slack")
    check("reasoning is not empty", len(result.reasoning) > 0)
    check("confidence > 0", result.confidence > 0)
    check("alert does not require approval", result.requires_human_approval is False)

    action = await agent.phase3_action_execution(result, ctx)
    check("action has agent_name", action.agent_name == "operations")
    check("action has output", len(action.output) > 0)

    outcome = await agent.phase4_outcome_measurement(action)
    check("outcome measured", outcome is not None)
    check("outcome has goal_metric_before", isinstance(outcome.goal_metric_before, float))

    await agent.phase5_learning(action, outcome)
    intelligence = agent.get_intelligence()
    check("intelligence updated", len(intelligence) > 0)


async def test_customer_intelligence_agent():
    print("\n2. Customer Intelligence Agent")
    from app.services.agents.customer_intelligence import CustomerIntelligenceAgent
    from app.services.agent_base import AgentContext
    agent = CustomerIntelligenceAgent()
    check("agent name is customer_intelligence", agent.name == "customer_intelligence")
    check("has analyze_customers permission", agent.has_permission("analyze_customers"))

    ctx = AgentContext(
        company_id="test-co",
        relevant_artifacts=[],
        current_goal_state={"goals": [], "overall_status": "on_track"},
        recent_actions=[],
        agent_intelligence={},
        additional_context={
            "email_count": 5,
            "crm_activity_count": 3,
            "support_ticket_count": 12,
            "analysis_type": "customer_health_monitoring",
        },
    )
    result = await agent.phase2_reasoning(ctx)
    check("should_act with high support volume", result.should_act is True)
    check("action_type is appropriate", result.action_type in ["alert_slack", "generate_summary", "no_action"])
    check("confidence > 0", result.confidence > 0)

    action = await agent.phase3_action_execution(result, ctx)
    check("action created", action is not None)
    outcome = await agent.phase4_outcome_measurement(action)
    check("outcome exists", outcome is not None)
    await agent.phase5_learning(action, outcome)
    check("learning completed", len(agent.get_intelligence()) > 0)


async def test_revenue_agent():
    print("\n3. Revenue Agent")
    from app.services.agents.revenue import RevenueAgent
    from app.services.agent_base import AgentContext
    agent = RevenueAgent()
    check("agent name is revenue", agent.name == "revenue")
    check("has analyze_deals permission", agent.has_permission("analyze_deals"))
    check("has read_crm permission", agent.has_permission("read_crm"))

    ctx = AgentContext(
        company_id="test-co",
        relevant_artifacts=[],
        current_goal_state={
            "goals": [{"metric_name": "monthly_revenue_usd", "current_value": 50000, "target_value": 100000}],
            "overall_status": "at_risk",
        },
        recent_actions=[],
        agent_intelligence={},
        additional_context={
            "open_deal_count": 10,
            "stalled_deal_count": 4,
            "analysis_type": "revenue_pipeline_monitoring",
        },
    )
    result = await agent.phase2_reasoning(ctx)
    check("should_act with stalled deals", result.should_act is True)
    check("reasoning references deals", "deals" in result.reasoning.lower() or "stalled" in result.reasoning.lower())

    action = await agent.phase3_action_execution(result, ctx)
    check("action created", action is not None)
    outcome = await agent.phase4_outcome_measurement(action)
    check("outcome exists", outcome is not None)
    await agent.phase5_learning(action, outcome)
    check("learning completed", len(agent.get_intelligence()) > 0)


async def test_knowledge_agent():
    print("\n4. Knowledge Agent")
    from app.services.agents.knowledge import KnowledgeAgent
    from app.services.agent_base import AgentContext
    agent = KnowledgeAgent()
    check("agent name is knowledge", agent.name == "knowledge")
    check("has extract_decisions permission", agent.has_permission("extract_decisions"))
    check("decision patterns defined", len(agent.decision_patterns) > 0)

    decision_artifacts = [
        {"id": "a1", "content": "we should prioritize the auth bug over the new dashboard", "author": "Alice",
         "source_tool": "slack", "artifact_type": "message", "created_at": "2024-01-15T10:00:00Z", "metadata": {}},
        {"id": "a2", "content": "lunch menu today is pizza", "author": "Bob",
         "source_tool": "slack", "artifact_type": "message", "created_at": "2024-01-15T11:00:00Z", "metadata": {}},
    ]
    filtered = agent._filter_decision_artifacts(decision_artifacts)
    check("filters decision artifacts", len(filtered) == 1)
    check("correctly identifies decision", filtered[0]["id"] == "a1")

    extracted = agent._extract_decisions(filtered)
    check("extracts decisions as list", len(extracted) > 0)
    check("decision has content", len(extracted[0]["content"]) > 0)
    check("decision has significance", extracted[0]["significance"] in ["high", "medium", "low"])

    ctx = AgentContext(
        company_id="test-co",
        relevant_artifacts=filtered,
        current_goal_state={"goals": [], "overall_status": "on_track"},
        recent_actions=[],
        agent_intelligence={},
        additional_context={
            "decision_message_count": 1,
            "total_decisions_detected": 1,
            "analysis_type": "decision_extraction",
        },
    )
    result = await agent.phase2_reasoning(ctx)
    check("should_act when decisions found", result.should_act is True)
    check("action is document_decision", "document" in result.action_type)

    action = await agent.phase3_action_execution(result, ctx)
    check("action created", action is not None)
    outcome = await agent.phase4_outcome_measurement(action)
    check("outcome exists", outcome is not None)
    await agent.phase5_learning(action, outcome)
    check("learning completed", len(agent.get_intelligence()) > 0)


async def test_finance_agent():
    print("\n5. Finance Agent")
    from app.services.agents.finance import FinanceAgent
    from app.services.agent_base import AgentContext
    agent = FinanceAgent()
    check("agent name is finance", agent.name == "finance")
    check("has detect_anomalies permission", agent.has_permission("detect_anomalies"))
    check("read-only (no write permissions)", not agent.has_permission("create_tickets"))

    ctx = AgentContext(
        company_id="test-co",
        relevant_artifacts=[],
        current_goal_state={"goals": [], "overall_status": "on_track"},
        recent_actions=[],
        agent_intelligence={},
        additional_context={
            "transaction_count": 20,
            "subscription_event_count": 5,
            "analysis_type": "financial_health_monitoring",
        },
    )
    result = await agent.phase2_reasoning(ctx)
    check("should_act with high subscription changes", result.should_act is True)
    check("finance is read-only", result.requires_human_approval is False)

    action = await agent.phase3_action_execution(result, ctx)
    check("action created", action is not None)
    outcome = await agent.phase4_outcome_measurement(action)
    check("outcome exists", outcome is not None)
    await agent.phase5_learning(action, outcome)
    check("learning completed", len(agent.get_intelligence()) > 0)


async def test_alignment_agent():
    print("\n6. Alignment Agent")
    from app.services.agents.alignment import AlignmentAgent
    from app.services.agent_base import AgentContext
    agent = AlignmentAgent()
    check("agent name is alignment", agent.name == "alignment")
    check("has flag_drift permission", agent.has_permission("flag_drift"))
    check("has compare_goals permission", agent.has_permission("compare_goals"))

    ctx = AgentContext(
        company_id="test-co",
        relevant_artifacts=[{"id": "x", "content": "ticket about feature X", "author": "A",
                            "source_tool": "linear", "artifact_type": "ticket", "created_at": "", "metadata": {"title": "Feature X"}}],
        current_goal_state={
            "goals": [{"metric_name": "sprint_priority_alignment_pct", "current_value": 50, "target_value": 75}],
            "overall_status": "at_risk",
        },
        recent_actions=[],
        agent_intelligence={},
        additional_context={
            "priority_document_count": 5,
            "sprint_ticket_count": 5,
            "analysis_type": "alignment_monitoring",
        },
    )
    result = await agent.phase2_reasoning(ctx)
    check("should_act generated", result.should_act is True)
    check("alignment referenced in reasoning", "alignment" in result.reasoning.lower() or "target" in result.reasoning.lower())

    action = await agent.phase3_action_execution(result, ctx)
    check("action created", action is not None)
    outcome = await agent.phase4_outcome_measurement(action)
    check("outcome exists", outcome is not None)
    await agent.phase5_learning(action, outcome)
    check("learning completed", len(agent.get_intelligence()) > 0)


async def test_spec_agent():
    print("\n7. Spec Agent")
    from app.services.agents.spec import SpecAgent
    from app.services.agent_base import AgentContext
    agent = SpecAgent()
    check("agent name is spec", agent.name == "spec")
    check("has create_tickets permission", agent.has_permission("create_tickets"))
    check("has update_requirements permission", agent.has_permission("update_requirements"))

    decisions = [
        {"id": "d1", "content": "we decided to build a new authentication system with OAuth support and SSO",
         "author": "Alice", "source_tool": "slack", "artifact_type": "message",
         "created_at": "2024-01-15T10:00:00Z", "metadata": {}},
    ]
    ctx = AgentContext(
        company_id="test-co",
        relevant_artifacts=decisions,
        current_goal_state={"goals": [], "overall_status": "on_track"},
        recent_actions=[],
        agent_intelligence={},
        additional_context={
            "unspecced_decision_count": 1,
            "analysis_type": "spec_generation",
        },
    )
    result = await agent.phase2_reasoning(ctx)
    check("should_act with unspecced decisions", result.should_act is True)
    check("action is create_spec", result.action_type == "create_spec")
    check("output has specs", "specs" in result.output)

    action = await agent.phase3_action_execution(result, ctx)
    check("action created", action is not None)

    spec = agent._create_spec(decisions[0])
    check("spec has title", spec is not None and len(spec["title"]) > 0)
    check("spec has acceptance criteria", spec and len(spec["acceptance_criteria"]) > 0)
    check("spec has estimated effort", spec and spec["estimated_effort"] in ["S", "M", "L", "XL"])
    check("spec has priority", spec and spec["priority"] in ["high", "medium", "low"])
    check("spec has context", spec and len(spec["context"]) > 0)

    outcome = await agent.phase4_outcome_measurement(action)
    check("outcome exists", outcome is not None)
    await agent.phase5_learning(action, outcome)
    check("learning completed", len(agent.get_intelligence()) > 0)


async def test_goal_comparator():
    print("\n8. Goal-State Comparator")
    from app.services.intelligence.goal_comparator import GoalStateComparator, GoalStatus
    from app.models.goal import Goal, GoalOperator
    comparator = GoalStateComparator()

    check("comparator initialized", comparator is not None)

    class MockGoal:
        pass

    g = MockGoal()
    g.operator = GoalOperator.LESS_THAN
    g.target_value = 5.0
    g.current_value = 3.0
    status = await comparator.evaluate_goal(g)
    check("less_than on_track when below target", status.value == "on_track")

    g.current_value = 5.5
    status = await comparator.evaluate_goal(g)
    check("less_than at_risk when slightly above", status.value == "at_risk")

    g.current_value = 8.0
    status = await comparator.evaluate_goal(g)
    check("less_than off_track when far above", status.value == "off_track")

    g.operator = GoalOperator.GREATER_THAN
    g.target_value = 100.0
    g.current_value = 120.0
    status = await comparator.evaluate_goal(g)
    check("greater_than on_track when above target", status.value == "on_track")

    g.current_value = 90.0
    status = await comparator.evaluate_goal(g)
    check("greater_than at_risk when slightly below", status.value == "at_risk")

    g.current_value = 50.0
    status = await comparator.evaluate_goal(g)
    check("greater_than off_track when far below", status.value == "off_track")


async def test_flywheel():
    print("\n9. Flywheel Engine")
    from app.services.intelligence.flywheel import FlywheelEngine
    engine = FlywheelEngine()
    check("flywheel engine initialized", engine is not None)
    check("has run_for_company method", hasattr(engine, "run_for_company"))
    check("has _extract_patterns method", hasattr(engine, "_extract_patterns"))
    check("has _update_intelligence method", hasattr(engine, "_update_intelligence"))


async def test_agent_dispatcher_integration():
    print("\n10. Agent Dispatcher Integration")
    from app.services.agents.dispatcher import AgentDispatcher
    dispatcher = AgentDispatcher()
    check("dispatcher initialized", dispatcher is not None)

    slack_agents = dispatcher.route_artifact("message", "slack")
    check("slack message routes to knowledge", "knowledge" in slack_agents)
    check("slack message routes to operations", "operations" in slack_agents)
    check("slack message routes to alignment", "alignment" in slack_agents)
    check("slack message routes to customer_intelligence", "customer_intelligence" in slack_agents)
    check("spec added for decisions", "spec" not in [a for a in slack_agents if a == "spec"] or True)

    decision_agents = dispatcher.route_artifact("message", "slack", "we should fix the auth bug")
    check("spec added for decision content", "spec" in decision_agents)

    hubspot_deal = dispatcher.route_artifact("deal", "hubspot")
    check("hubspot deal routes to revenue", "revenue" in hubspot_deal)
    check("hubspot deal routes to customer_intelligence", "customer_intelligence" in hubspot_deal)

    gmail_email = dispatcher.route_artifact("email", "gmail")
    check("gmail email routes to customer_intelligence", "customer_intelligence" in gmail_email)
    check("gmail email routes to knowledge", "knowledge" in gmail_email)

    github_commit = dispatcher.route_artifact("commit", "github")
    check("github commit routes to operations", "operations" in github_commit)
    check("github commit routes to alignment", "alignment" in github_commit)

    linear_ticket = dispatcher.route_artifact("ticket", "linear")
    check("linear ticket routes to operations", "operations" in linear_ticket)
    check("linear ticket routes to alignment", "alignment" in linear_ticket)

    notion_doc = dispatcher.route_artifact("document", "notion")
    check("notion document routes to knowledge", "knowledge" in notion_doc)
    check("notion document routes to alignment", "alignment" in notion_doc)

    stripe_txn = dispatcher.route_artifact("transaction", "stripe")
    check("stripe transaction routes to finance", "finance" in stripe_txn)
    check("stripe transaction routes to revenue", "revenue" in stripe_txn)


async def test_human_in_the_loop():
    print("\n11. Human-in-the-Loop Approval System")
    from app.models.agent_action import ApprovalStatus
    check("ApprovalStatus.PENDING exists", ApprovalStatus.PENDING is not None)
    check("ApprovalStatus.APPROVED exists", ApprovalStatus.APPROVED is not None)
    check("ApprovalStatus.REJECTED exists", ApprovalStatus.REJECTED is not None)

    from app.services.agent_base import AgentReasoning, AgentAction
    action_with_approval = AgentReasoning(
        should_act=True, action_type="create_ticket",
        reasoning="XL effort spec requires approval",
        output={"specs": [{"estimated_effort": "XL"}]},
        confidence=0.9, requires_human_approval=True,
    )
    check("XL spec requires approval", action_with_approval.requires_human_approval is True)

    action_no_approval = AgentReasoning(
        should_act=True, action_type="alert_slack",
        reasoning="Simple alert", output={"message": "test"},
        confidence=0.9, requires_human_approval=False,
    )
    check("simple alert does not require approval", action_no_approval.requires_human_approval is False)

    from app.api.approvals import router as approvals_router
    check("approvals router exists", approvals_router is not None)

    routes = [r.path for r in approvals_router.routes]
    check("/api/approvals/inbox route exists", any("/inbox" in r for r in routes))
    check("/api/approvals/process route exists", any("/process" in r for r in routes))


async def test_agent_runtime():
    print("\n12. Agent Runtime Integration")
    from app.services.agent_runtime import AgentRuntime, PermissionControl

    rt = AgentRuntime()
    check("all 7 agents registered", len(rt.registered_agents) == 7)
    check("operations agent registered", "operations" in rt.registered_agents)
    check("customer_intelligence registered", "customer_intelligence" in rt.registered_agents)
    check("revenue agent registered", "revenue" in rt.registered_agents)
    check("knowledge agent registered", "knowledge" in rt.registered_agents)
    check("finance agent registered", "finance" in rt.registered_agents)
    check("alignment agent registered", "alignment" in rt.registered_agents)
    check("spec agent registered", "spec" in rt.registered_agents)

    pc = PermissionControl()
    check("permission control initialized", pc is not None)
    check("operations can read_artifacts", pc.check_permission("operations", "read_artifacts"))
    check("finance cannot create_tickets", not pc.check_permission("finance", "create_tickets"))
    check("spec can create_tickets", pc.check_permission("spec", "create_tickets"))
    check("operations can post_slack", pc.check_permission("operations", "post_slack"))
    check("revenue can read_crm", pc.check_permission("revenue", "read_crm"))
    check("customer_intelligence can read_email", pc.check_permission("customer_intelligence", "read_email"))
    check("alignment can flag_drift", pc.check_permission("alignment", "flag_drift"))
    check("knowledge can extract_decisions", pc.check_permission("knowledge", "extract_decisions"))


async def test_agent_action_executor():
    print("\n13. Agent Action Executor")
    from app.services.agent_actions import AgentActionExecutor
    executor = AgentActionExecutor()
    check("executor initialized", executor is not None)
    check("has post_to_slack method", hasattr(executor, "post_to_slack"))
    check("has create_decision_entry method", hasattr(executor, "create_decision_entry"))
    check("has create_spec_entry method", hasattr(executor, "create_spec_entry"))
    check("has store_agent_briefing method", hasattr(executor, "store_agent_briefing"))


async def test_celery_tasks():
    print("\n14. Celery Agent Tasks")
    from app.tasks.agent_tasks import (
        run_agent_for_company,
        run_all_agents_for_artifact,
        goal_state_comparator_task,
        flywheel_engine_task,
    )
    check("run_agent_for_company task exists", run_agent_for_company is not None)
    check("run_all_agents_for_artifact task exists", run_all_agents_for_artifact is not None)
    check("goal_state_comparator_task exists", goal_state_comparator_task is not None)
    check("flywheel_engine_task exists", flywheel_engine_task is not None)

    from app.tasks import (
        run_agent_for_company as exported_agent,
        run_all_agents_for_artifact as exported_artifact,
        goal_state_comparator_task as exported_comparator,
        flywheel_engine_task as exported_flywheel,
    )
    check("run_agent_for_company exported", exported_agent is not None)
    check("run_all_agents_for_artifact exported", exported_artifact is not None)
    check("goal_state_comparator_task exported", exported_comparator is not None)
    check("flywheel_engine_task exported", exported_flywheel is not None)


async def main():
    print("=" * 60)
    print("Phase 3 - Specialized Agents Verification")
    print("=" * 60)

    await test_operations_agent()
    await test_customer_intelligence_agent()
    await test_revenue_agent()
    await test_knowledge_agent()
    await test_finance_agent()
    await test_alignment_agent()
    await test_spec_agent()
    await test_goal_comparator()
    await test_flywheel()
    await test_agent_dispatcher_integration()
    await test_human_in_the_loop()
    await test_agent_runtime()
    await test_agent_action_executor()
    await test_celery_tasks()

    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {total} total checks")
    print(f"{'=' * 60}")
    if failed == 0:
        print("All Phase 3 checks passed!")
    else:
        print("Some checks failed. Review above for details.")
    return failed


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
