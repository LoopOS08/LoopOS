"""
Phase 4 Verification Script
Tests the three Universal Connectivity Layer bridges:
1. MCP Server Bridge
2. REST API Connector
3. Zapier/Make Bridge

Run: python verify_phase4.py
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_result(name: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status} | {name}")
    if detail:
        print(f"         {detail}")
    return passed


async def test_mcp_bridge():
    """Test MCP Bridge Integration"""
    print_header("MCP Server Bridge Tests")
    passed = 0
    total = 0

    from app.services.integrations.mcp_bridge import MCPBridgeIntegration
    from app.models.integration import SourceTool
    from app.models.artifact import ArtifactType

    # Test 1: Instance creation
    total += 1
    try:
        bridge = MCPBridgeIntegration(
            company_id="test-company",
            credentials_encrypted="",
            settings={'server_id': 'test-server'}
        )
        result = print_result("Instance creation", True)
        passed += 1 if result else 0
    except Exception as e:
        print_result("Instance creation", False, str(e))

    # Test 2: Source tool property
    total += 1
    try:
        assert bridge.source_tool == SourceTool.MCP
        result = print_result("Source tool is MCP", True)
        passed += 1 if result else 0
    except AssertionError:
        result = print_result("Source tool is MCP", False, f"Got {bridge.source_tool}")
        passed += 1 if result else 0

    # Test 3: Normalize event
    total += 1
    try:
        artifact = bridge.normalize_event({
            'resource_uri': 'test://resource/1',
            'data': {'key': 'value'},
            'timestamp': '2024-01-01T00:00:00'
        })
        assert artifact.source_tool == SourceTool.MCP
        assert 'key' in artifact.content
        result = print_result("Normalize event", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Normalize event", False, str(e))
        passed += 1 if result else 0

    # Test 4: Webhook events list
    total += 1
    try:
        events = bridge.webhook_events
        assert 'resource_updated' in events
        assert 'tool_executed' in events
        result = print_result("Webhook events defined", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Webhook events defined", False, str(e))
        passed += 1 if result else 0

    print(f"\n  Results: {passed}/{total} passed\n")
    return passed == total


async def test_rest_connector():
    """Test REST API Connector"""
    print_header("REST API Connector Tests")
    passed = 0
    total = 0

    from app.services.integrations.rest_connector_service import RESTConnectorIntegration
    from app.models.integration import SourceTool
    from app.models.rest_connector import RESTConnector, RESTAuthType, RESTConnectorStatus

    # Test 1: Instance creation
    total += 1
    try:
        connector = RESTConnectorIntegration(
            company_id="test-company",
            credentials_encrypted="",
            settings={}
        )
        result = print_result("Instance creation", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Instance creation", False, str(e))

    # Test 2: Configure with mock connector
    total += 1
    try:
        mock_connector = RESTConnector(
            company_id="test-company",
            name="Test API",
            url="https://api.example.com/items",
            method="GET",
            headers={"Accept": "application/json"},
            auth_type=RESTAuthType.NONE,
            auth_config={},
            field_mappings={
                "items_path": "$.data",
                "id_path": "$.id",
                "content_path": "$.title",
                "author_path": "$.author",
                "timestamp_path": "$.created_at"
            },
            pagination={"strategy": "none"},
            polling_interval_minutes=60,
            status=RESTConnectorStatus.PAUSED
        )
        connector.configure(mock_connector)
        result = print_result("Configure connector", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Configure connector", False, str(e))

    # Test 3: Normalize event
    total += 1
    try:
        artifact = connector.normalize_event({
            'id': '123',
            'data': {'message': 'hello'}
        })
        assert artifact.source_tool == SourceTool.REST_API
        result = print_result("Normalize event", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Normalize event", False, str(e))

    print(f"\n  Results: {passed}/{total} passed\n")
    return passed == total


async def test_zapier_bridge():
    """Test Zapier/Make Bridge"""
    print_header("Zapier / Make Bridge Tests")
    passed = 0
    total = 0

    from app.services.integrations.zapier_bridge import ZapierBridgeIntegration
    from app.models.integration import SourceTool
    from app.models.artifact import ArtifactType

    # Test 1: Instance creation (Zapier mode)
    total += 1
    try:
        zapier = ZapierBridgeIntegration(
            company_id="test-company",
            credentials_encrypted="",
            settings={
                'webhook_secret': 'test-secret',
                'artifact_type': 'message',
                'platform': 'zapier'
            }
        )
        result = print_result("Zapier instance creation", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Zapier instance creation", False, str(e))

    # Test 2: Instance creation (Make mode)
    total += 1
    try:
        make = ZapierBridgeIntegration(
            company_id="test-company",
            credentials_encrypted="",
            settings={
                'webhook_secret': 'test-secret',
                'artifact_type': 'message',
                'platform': 'make'
            }
        )
        assert make.is_make == True
        result = print_result("Make instance creation", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Make instance creation", False, str(e))

    # Test 3: Normalize Zapier event with fields
    total += 1
    try:
        artifact = zapier.normalize_event({
            'type': 'message',
            'data': {
                'fields': {
                    'content': 'Hello from Zapier',
                    'author': 'Alice',
                    'email': 'alice@example.com',
                    'id': 'evt-001',
                    'timestamp': '2024-01-01T00:00:00'
                }
            }
        })
        assert artifact.content == 'Hello from Zapier'
        assert artifact.author == 'Alice'
        assert artifact.author_email == 'alice@example.com'
        assert artifact.external_id == 'evt-001'
        result = print_result("Normalize Zapier event with fields", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Normalize Zapier event with fields", False, str(e))

    # Test 4: Normalize Make event
    total += 1
    try:
        artifact = make.normalize_event({
            'type': 'ticket',
            'data': {
                'content': 'New support ticket',
                'author': 'Bob',
            },
            'source_tool': 'intercom'
        })
        assert artifact.source_tool == SourceTool.INTERCOM  # Detected from source_tool field
        assert artifact.artifact_type == ArtifactType.TICKET  # Detected from type field
        result = print_result("Normalize Make event with source detection", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Normalize Make event with source detection", False, str(e))

    # Test 5: Webhook signature validation
    total += 1
    try:
        import hmac, hashlib
        payload = b'{"test": "data"}'
        expected_sig = hmac.new(
            b'test-secret',
            payload,
            hashlib.sha256
        ).hexdigest()
        result = zapier.validate_webhook_signature(f'sha256={expected_sig}', payload)
        assert result == True
        result = print_result("Webhook signature validation", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Webhook signature validation", False, str(e))

    # Test 6: Invalid signature rejection
    total += 1
    try:
        result = zapier.validate_webhook_signature('sha256=invalid', b'test')
        assert result == False
        result = print_result("Invalid signature rejection", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Invalid signature rejection", False, str(e))

    # Test 7: Detect artifact type from event
    total += 1
    try:
        email_artifact = zapier.normalize_event({
            'type': 'email_received',
            'data': {'fields': {'content': 'Hello', 'author': 'Alice'}}
        })
        assert email_artifact.artifact_type == ArtifactType.EMAIL
        result = print_result("Artifact type detection from event", True)
        passed += 1 if result else 0
    except Exception as e:
        result = print_result("Artifact type detection from event", False, str(e))

    print(f"\n  Results: {passed}/{total} passed\n")
    return passed == total


async def test_dispatcher_routing():
    """Test dispatcher has Phase 4 routing rules"""
    print_header("Dispatcher Routing Tests")
    passed = 0
    total = 0

    from app.services.agents.dispatcher import agent_dispatcher

    # Test MCP routing
    total += 1
    agents = agent_dispatcher.route_artifact('message', 'mcp')
    if 'knowledge' in agents:
        result = print_result("MCP message routes to knowledge", True)
        passed += 1 if result else 0
    else:
        result = print_result("MCP message routes to knowledge", False, f"Got {agents}")

    # Test Zapier routing
    total += 1
    agents = agent_dispatcher.route_artifact('email', 'zapier')
    if 'customer_intelligence' in agents and 'knowledge' in agents:
        result = print_result("Zapier email routes to CI + knowledge", True)
        passed += 1 if result else 0
    else:
        result = print_result("Zapier email routes to CI + knowledge", False, f"Got {agents}")

    # Test Make routing
    total += 1
    agents = agent_dispatcher.route_artifact('ticket', 'make')
    if 'operations' in agents and 'alignment' in agents:
        result = print_result("Make ticket routes to operations + alignment", True)
        passed += 1 if result else 0
    else:
        result = print_result("Make ticket routes to operations + alignment", False, f"Got {agents}")

    # Test REST API routing
    total += 1
    agents = agent_dispatcher.route_artifact('message', 'rest_api')
    if 'knowledge' in agents:
        result = print_result("REST API message routes to knowledge", True)
        passed += 1 if result else 0
    else:
        result = print_result("REST API message routes to knowledge", False, f"Got {agents}")

    print(f"\n  Results: {passed}/{total} passed\n")
    return passed == total


async def main():
    """Run all Phase 4 verification tests"""
    print("=" * 60)
    print("  LoopOS Phase 4 - Universal Connectivity Layer")
    print("  Verification Script")
    print("=" * 60)

    results = await asyncio.gather(
        test_mcp_bridge(),
        test_rest_connector(),
        test_zapier_bridge(),
        test_dispatcher_routing(),
    )

    total = sum(1 for r in results if r)
    overall = len(results)

    print("\n" + "=" * 60)
    print(f"  OVERALL: {total}/{overall} test suites passed")
    print("=" * 60)

    if total == overall:
        print("\n  All Phase 4 components verified successfully!")
    else:
        print(f"\n  {overall - total} test suite(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
