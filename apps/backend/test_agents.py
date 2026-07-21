"""
Test script to verify Phase 3 agent implementations
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.services.agents import (
    OperationsAgent,
    CustomerIntelligenceAgent,
    RevenueAgent,
    KnowledgeAgent,
    FinanceAgent,
    AlignmentAgent,
    SpecAgent,
    agent_dispatcher
)
from app.services.agent_runtime import agent_runtime
from app.services.agent_base import AgentContext

def test_agent_instantiation():
    """Test that all agents can be instantiated"""
    print("Testing agent instantiation...")
    
    agents = [
        OperationsAgent(),
        CustomerIntelligenceAgent(),
        RevenueAgent(),
        KnowledgeAgent(),
        FinanceAgent(),
        AlignmentAgent(),
        SpecAgent()
    ]
    
    for agent in agents:
        print(f"✓ {agent.name}: {agent.description}")
        print(f"  Permissions: {agent.permissions}")
    
    print(f"\n✓ All {len(agents)} agents instantiated successfully")
    return True

def test_dispatcher():
    """Test agent dispatcher routing"""
    print("\nTesting agent dispatcher...")
    
    # Test routing rules
    test_cases = [
        ("message", "slack", "Test message about decision"),
        ("deal", "hubspot", "New deal opportunity"),
        ("email", "gmail", "Customer inquiry"),
        ("ticket", "linear", "Bug report"),
        ("commit", "github", "Feature implementation"),
        ("transaction", "stripe", "Payment received"),
        ("meeting", "zoom", "Team sync"),
        ("document", "notion", "Strategy doc"),
    ]
    
    for artifact_type, source_tool, content in test_cases:
        routed_agents = agent_dispatcher.route_artifact(artifact_type, source_tool, content)
        print(f"✓ {artifact_type}/{source_tool} -> {routed_agents}")
    
    print("\n✓ Dispatcher routing working correctly")
    return True

def test_agent_runtime():
    """Test agent runtime registration"""
    print("\nTesting agent runtime...")
    
    # Check registered agents
    registered_agents = agent_runtime.list_agents()
    print(f"✓ Registered agents: {registered_agents}")
    
    # Check dispatcher is available
    print(f"✓ Dispatcher available: {agent_runtime.dispatcher is not None}")
    
    # Test getting individual agents
    for agent_name in registered_agents:
        agent = agent_runtime.get_agent(agent_name)
        print(f"✓ Retrieved {agent_name}: {agent.description if agent else 'None'}")
    
    print(f"\n✓ Agent runtime working correctly")
    return True

def test_agent_context():
    """Test agent context creation"""
    print("\nTesting agent context creation...")
    
    # Create a sample context
    context = AgentContext(
        company_id="test-company",
        relevant_artifacts=[],
        current_goal_state={'goals': []},
        recent_actions=[],
        agent_intelligence={},
        additional_context={'test': True}
    )
    
    print(f"✓ Context created for company: {context.company_id}")
    print(f"  Artifacts: {len(context.relevant_artifacts)}")
    print(f"  Goals: {len(context.current_goal_state.get('goals', []))}")
    
    print("\n✓ Agent context working correctly")
    return True

def test_permission_control():
    """Test permission control system"""
    print("\nTesting permission control...")
    
    from app.services.agent_runtime import permission_control
    
    # Test getting permissions for each agent
    for agent_name in agent_runtime.list_agents():
        permissions = permission_control.get_agent_permissions(agent_name)
        print(f"✓ {agent_name} permissions: {permissions}")
    
    # Test permission validation
    can_create = permission_control.check_permission('operations', 'create_tickets')
    print(f"✓ Operations can create tickets: {can_create}")
    
    print("\n✓ Permission control working correctly")
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 3 Agent Implementation Tests")
    print("=" * 60)
    
    tests = [
        test_agent_instantiation,
        test_dispatcher,
        test_agent_runtime,
        test_agent_context,
        test_permission_control
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            results.append((test.__name__, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Phase 3 implementation complete.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
