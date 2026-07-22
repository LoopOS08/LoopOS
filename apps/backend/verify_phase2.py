"""
Phase 2 Verification Script
Tests all 6 integrations + Unified Query Interface end-to-end.

Run: python verify_phase2.py
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

PASS = 0
FAIL = 0


def check(description: str, condition: bool):
    global PASS, FAIL
    if condition:
        print(f"  ✓ {description}")
        PASS += 1
    else:
        print(f"  ✗ {description}")
        FAIL += 1


async def test_slack_integration():
    print("\n1. Slack Integration")
    from app.services.integrations.slack import SlackIntegration
    from app.models.integration import SourceTool
    from app.models.artifact import ArtifactType

    integration = SlackIntegration(
        company_id="test-company",
        credentials_encrypted="test-key:test-encrypted",
        settings={'slack_signing_secret': 'test-secret'}
    )

    check("source_tool returns SLACK", integration.source_tool == SourceTool.SLACK)
    check("webhook_events includes message", 'message' in integration.webhook_events)
    check("webhook_events includes reaction_added", 'reaction_added' in integration.webhook_events)
    check("webhook_events includes app_mention", 'app_mention' in integration.webhook_events)

    oauth_url = integration.get_oauth_url("http://localhost:3000/callback")
    check("get_oauth_url returns valid URL", oauth_url.startswith("https://slack.com/oauth/v2/authorize"))
    check("OAuth URL includes client_id param", "client_id=" in oauth_url)
    check("OAuth URL includes scope param", "scope=" in oauth_url)

    sig = integration.validate_webhook_signature("v0=test", b"payload")
    check("validate_webhook_signature handles invalid sig gracefully", not sig)

    check("rate limiter initialized", integration._rate_limiter is not None)
    check("rate limiter max calls = 50", integration._rate_limiter.max_calls == 50)

    print(f"  Slack integration: {integration.__class__.__name__} - {integration.source_tool.value}")


async def test_gmail_integration():
    print("\n2. Gmail Integration")
    from app.services.integrations.gmail import GmailIntegration, GmailPrivacyController
    from app.models.integration import SourceTool
    from app.models.artifact import ArtifactType

    privacy = GmailPrivacyController({
        'authorized_accounts': ['admin@company.com'],
        'opted_out_users': [],
        'privacy_enabled': True,
        'purge_raw_after_hours': 24
    })

    check("privacy controller authorizes admin", privacy.is_account_authorized('admin@company.com'))
    check("privacy controller rejects unknown", not privacy.is_account_authorized('unknown@other.com'))
    check("privacy controller should_process accepts authorized", privacy.should_process_email('admin@company.com'))
    check("privacy controller should_process rejects unknown", not privacy.should_process_email('unknown@other.com'))

    redacted = privacy.redact_pii("Contact me at john@test.com or 555-123-4567")
    check("PII redaction removes emails", '[email redacted]' in redacted)
    check("PII redaction removes phones", '[phone redacted]' in redacted)

    privacy_with_optout = GmailPrivacyController({
        'authorized_accounts': ['admin@company.com', 'user@company.com'],
        'opted_out_users': ['user@company.com'],
        'privacy_enabled': True
    })
    check("opted-out user is rejected", not privacy_with_optout.should_process_email('user@company.com'))

    integration = GmailIntegration(
        company_id="test-company",
        credentials_encrypted="test-key:test-encrypted",
        settings={'privacy_enabled': True}
    )

    check("source_tool returns GMAIL", integration.source_tool == SourceTool.GMAIL)
    check("privacy controller initialized", integration.privacy is not None)
    check("privacy mode enabled", integration.privacy.privacy_enabled is True)

    oauth_url = integration.get_oauth_url("http://localhost:3000/callback")
    check("OAuth URL includes gmail.readonly scope", "gmail.readonly" in oauth_url)
    check("OAuth URL includes access_type=offline", "access_type=offline" in oauth_url)

    _from = integration._parse_email_address('"John Doe" <john@test.com>')
    check("parse email with name returns name", _from[0] == "John Doe")
    check("parse email with name returns email", _from[1] == "john@test.com")

    _from2 = integration._parse_email_address('john@test.com')
    check("parse email without name returns empty name", _from2[0] == "")
    check("parse email without name returns email", _from2[1] == "john@test.com")

    addresses = integration._parse_email_addresses('"A" <a@x.com>, "B" <b@y.com>')
    check("parse multiple addresses", len(addresses) == 2)
    check("first address parsed correctly", 'a@x.com' in addresses)


async def test_github_integration():
    print("\n3. GitHub Integration")
    from app.services.integrations.github import GitHubIntegration
    from app.models.integration import SourceTool
    from app.models.artifact import ArtifactType

    integration = GitHubIntegration(
        company_id="test-company",
        credentials_encrypted="test-key:test-encrypted"
    )

    check("source_tool returns GITHUB", integration.source_tool == SourceTool.GITHUB)
    check("webhook_events includes push", 'push' in integration.webhook_events)
    check("webhook_events includes pull_request", 'pull_request' in integration.webhook_events)
    check("webhook_events includes issues", 'issues' in integration.webhook_events)
    check("webhook_events includes workflow_run", 'workflow_run' in integration.webhook_events)

    oauth_url = integration.get_oauth_url("http://localhost:3000/callback")
    check("OAuth URL starts with github.com", oauth_url.startswith("https://github.com/login/oauth/authorize"))
    check("OAuth URL includes repo scope", "repo" in oauth_url)

    sig = integration.validate_webhook_signature("sha256=test", b"payload")
    check("validate_webhook_signature handles invalid sig", not sig)

    is_valid_format = integration.validate_webhook_signature("sha256=abc123", b"test")
    check("validate_webhook_signature with no secret returns False", not is_valid_format)


async def test_linear_integration():
    print("\n4. Linear Integration")
    from app.services.integrations.linear import LinearIntegration
    from app.models.integration import SourceTool

    integration = LinearIntegration(
        company_id="test-company",
        credentials_encrypted="test-key:test-encrypted"
    )

    check("source_tool returns LINEAR", integration.source_tool == SourceTool.LINEAR)
    check("webhook_events includes Issue", 'Issue' in integration.webhook_events)
    check("webhook_events includes Comment", 'Comment' in integration.webhook_events)
    check("webhook_events includes Cycle", 'Cycle' in integration.webhook_events)

    oauth_url = integration.get_oauth_url("http://localhost:3000/callback")
    check("OAuth URL starts with linear.app", oauth_url.startswith("https://linear.app/oauth/authorize"))
    check("OAuth URL includes scope=read,write", "scope=read,write" in oauth_url)

    test_issue = {
        'Issue': {
            'id': 'linear-issue-1',
            'title': 'Test Issue',
            'description': 'Testing linear integration',
            'state': {'name': 'In Progress'},
            'priority': 2,
            'assignee': {'name': 'Alice', 'email': 'alice@test.com'},
            'creator': {'name': 'Bob', 'email': 'bob@test.com'},
            'team': {'name': 'Engineering'},
            'labels': [{'name': 'bug'}],
            'estimate': 3,
            'url': 'https://linear.app/issue/TEST-1',
            'createdAt': '2024-01-15T10:00:00Z',
            'updatedAt': '2024-01-15T12:00:00Z'
        }
    }
    artifact = await integration._process_issue_event(test_issue)
    check("process issue returns artifact", artifact is not None)
    if artifact:
        check("issue artifact type is TICKET", artifact.artifact_type.value == 'ticket')
        check("issue content mentions title", 'Test Issue' in artifact.content)
        check("issue external_id matches", artifact.external_id == 'linear-issue-1')


async def test_hubspot_integration():
    print("\n5. HubSpot Integration")
    from app.services.integrations.hubspot import HubSpotIntegration
    from app.models.integration import SourceTool

    integration = HubSpotIntegration(
        company_id="test-company",
        credentials_encrypted="test-key:test-encrypted"
    )

    check("source_tool returns HUBSPOT", integration.source_tool == SourceTool.HUBSPOT)
    check("webhook_events includes deal.propertyChange", 'deal.propertyChange' in integration.webhook_events)
    check("webhook_events includes contact.creation", 'contact.creation' in integration.webhook_events)

    oauth_url = integration.get_oauth_url("http://localhost:3000/callback")
    check("OAuth URL starts with app.hubspot.com", oauth_url.startswith("https://app.hubspot.com/oauth/authorize"))
    check("OAuth URL includes crm.objects.deals.read scope", "crm.objects.deals.read" in oauth_url)


async def test_notion_integration():
    print("\n6. Notion Integration")
    from app.services.integrations.notion import NotionIntegration
    from app.models.integration import SourceTool

    integration = NotionIntegration(
        company_id="test-company",
        credentials_encrypted="test-key:test-encrypted"
    )

    check("source_tool returns NOTION", integration.source_tool == SourceTool.NOTION)
    check("webhook_events is empty (no webhooks)", integration.webhook_events == [])

    oauth_url = integration.get_oauth_url("http://localhost:3000/callback")
    check("OAuth URL starts with notion.com", oauth_url.startswith("https://api.notion.com/v1/oauth/authorize"))

    chunks = integration._chunk_document("word " * 3000)
    check("document chunking produces multiple chunks", len(chunks) > 1)
    if chunks:
        check("first chunk is not empty", len(chunks[0]) > 0)

    chunks_small = integration._chunk_document("small document")
    check("small document is not chunked", len(chunks_small) == 1)

    title = integration._extract_page_title({
        'title': {'type': 'title', 'title': [{'text': {'content': 'My Page'}}]}
    })
    check("extract title from properties", title == 'My Page')

    title_fallback = integration._extract_page_title({})
    check("extract title returns Untitled for empty props", title_fallback == 'Untitled')

    text = integration._extract_rich_text([
        {'text': {'content': 'Hello '}, 'annotations': {'bold': True, 'italic': False, 'code': False, 'strikethrough': False}},
        {'text': {'content': 'World'}, 'annotations': {'bold': False, 'italic': False, 'code': False, 'strikethrough': False}}
    ])
    check("extract rich text preserves bold", '**Hello **' in text)
    check("extract rich text returns full content", 'World' in text)


async def test_query_interface():
    print("\n7. Unified Query Interface")
    from app.services.query import QueryService, QueryResult
    from app.models.artifact import SourceTool, ArtifactType

    qs = QueryService()

    check("QueryService initialized", qs is not None)
    check("artifact_store service available", qs.artifact_store is not None)
    check("embedding_service available", qs.embedding_service is not None)

    context = qs._assemble_context([])
    check("assemble_context with empty returns empty string", context == "")

    result = QueryResult(
        answer="Test answer",
        sources=[{"tool": "slack", "type": "message", "author": "Alice", "date": "2024-01-15",
                  "preview": "test", "similarity": 0.95, "metadata": {}}],
        confidence=0.95,
        caveats=["Limited results"]
    )
    check("QueryResult stores answer", result.answer == "Test answer")
    check("QueryResult stores confidence", result.confidence == 0.95)
    check("QueryResult stores caveats", len(result.caveats) == 1)
    check("QueryResult to_dict returns dict", isinstance(result.to_dict(), dict))
    check("QueryResult to_dict has answer key", 'answer' in result.to_dict())

    confidence = qs._calculate_confidence([])
    check("empty confidence is 0.0", confidence == 0.0)

    suggestions = await qs.get_answer_suggestions(None, "test-company", "pricing")
    check("suggestions contain matching queries", len(suggestions) > 0)
    check("suggestions are filtered by partial query", all('pricing' in s.lower() for s in suggestions))


async def test_agent_dispatcher():
    print("\n8. Agent Dispatcher Routing")
    from app.services.agents.dispatcher import AgentDispatcher

    dispatcher = AgentDispatcher()

    slack_msg = dispatcher.route_artifact("message", "slack", "we should fix the auth bug")
    check("slack message routes to knowledge", 'knowledge' in slack_msg)
    check("slack message with decision routes to spec", 'spec' in slack_msg)
    check("slack message routes to operations", 'operations' in slack_msg)
    check("slack message routes to alignment", 'alignment' in slack_msg)

    slack_no_decision = dispatcher.route_artifact("message", "slack", "lunch menu today")
    check("slack without decision does not route to spec", 'spec' not in slack_no_decision)

    blocker_msg = dispatcher.route_artifact("message", "teams", "we are blocked by the API")
    check("blocker language adds operations agent", 'operations' in blocker_msg)

    customer_msg = dispatcher.route_artifact("message", "slack", "the customer is unhappy with churn")
    check("customer mention adds customer_intelligence", 'customer_intelligence' in customer_msg)

    deal = dispatcher.route_artifact("deal", "hubspot", "new deal")
    check("hubspot deal routes to revenue", 'revenue' in deal)
    check("hubspot deal routes to customer_intelligence", 'customer_intelligence' in deal)

    email = dispatcher.route_artifact("email", "gmail", "meeting reminder")
    check("gmail email routes to customer_intelligence", 'customer_intelligence' in email)
    check("gmail email routes to knowledge", 'knowledge' in email)

    commit = dispatcher.route_artifact("commit", "github", "fix: auth bug")
    check("github commit routes to operations", 'operations' in commit)
    check("github commit routes to alignment", 'alignment' in commit)

    ticket = dispatcher.route_artifact("ticket", "linear", "new ticket")
    check("linear ticket routes to operations", 'operations' in ticket)
    check("linear ticket routes to alignment", 'alignment' in ticket)

    doc = dispatcher.route_artifact("document", "notion", "roadmap doc")
    check("notion document routes to knowledge", 'knowledge' in doc)
    check("notion document routes to alignment", 'alignment' in doc)

    transaction = dispatcher.route_artifact("transaction", "stripe", "payment")
    check("stripe transaction routes to finance", 'finance' in transaction)
    check("stripe transaction routes to revenue", 'revenue' in transaction)

    unknown = dispatcher.route_artifact("unknown_type", "unknown_tool")
    check("unknown artifact uses default agents", 'knowledge' in unknown)

    dispatcher.add_routing_rule("custom", "custom_tool", ["knowledge", "operations"])
    custom = dispatcher.route_artifact("custom", "custom_tool")
    check("custom routing rule works", 'knowledge' in custom and 'operations' in custom)

    dispatcher.remove_routing_rule("custom", "custom_tool")
    after_remove = dispatcher.route_artifact("custom", "custom_tool")
    check("removed routing falls back to default", 'knowledge' in after_remove)


async def test_encryption_service():
    print("\n9. Encryption Service (mock KMS)")
    from app.services.encryption import EncryptionService
    with patch('app.services.encryption.boto3.client') as mock_boto:
        mock_kms = MagicMock()
        mock_kms.generate_data_key.return_value = {
            'Plaintext': b'x' * 32,
            'CiphertextBlob': b'y' * 40
        }
        mock_kms.decrypt.return_value = {'Plaintext': b'x' * 32}
        mock_boto.return_value = mock_kms

        es = EncryptionService()
        encrypted = es.encrypt_credentials({'access_token': 'test-token'})
        check("encrypt_credentials returns combined format", ':' in encrypted)

        decrypted = es.decrypt_credentials(encrypted)
        check("decrypt_credentials returns dict", isinstance(decrypted, dict))
        check("decrypt_credentials returns original data", decrypted.get('access_token') == 'test-token')


async def test_rate_limiter():
    print("\n10. Rate Limiter")
    from app.services.rate_limiter import RateLimiter, exponential_backoff_delay

    rl = RateLimiter(max_calls=5, period_seconds=60.0)
    check("rate limiter initialized with max_calls=5", rl.max_calls == 5)

    delay = exponential_backoff_delay(0, base=1.0)
    check("backoff attempt 0 gives ~1s", 0.5 <= delay <= 1.5)

    delay2 = exponential_backoff_delay(1, base=1.0)
    check("backoff attempt 1 gives ~2s", 1.0 <= delay2 <= 3.0)

    delay3 = exponential_backoff_delay(2, base=1.0)
    check("backoff attempt 2 gives ~4s", 2.0 <= delay3 <= 6.0)

    delay_capped = exponential_backoff_delay(10, base=1.0, max_delay=60.0)
    check("backoff capped at max_delay", delay_capped <= 60.0)


async def test_artifact_relationships():
    print("\n11. Artifact Relationship Tracker")
    from app.services.relationships import ArtifactRelationshipTracker
    from app.models.artifact import Artifact

    tracker = ArtifactRelationshipTracker()
    check("relationship tracker initialized", tracker is not None)

    mock_artifact = MagicMock(spec=Artifact)
    mock_artifact.artifact_type = MagicMock()
    mock_artifact.artifact_type.value = 'email'
    mock_artifact.source_tool = MagicMock()
    mock_artifact.source_tool.value = 'gmail'
    mock_artifact.metadata = {'thread_id': 'thread-1'}
    mock_artifact.company_id = 'test-company'
    mock_artifact.id = 'artifact-1'

    check("relationship tracker has email rules", ('email', 'gmail') in tracker._relationship_rules)
    check("relationship tracker has slack rules", ('message', 'slack') in tracker._relationship_rules)
    check("relationship tracker has github commit rules", ('commit', 'github') in tracker._relationship_rules)


async def test_normalized_artifact_model():
    print("\n12. Normalized Artifact Model")
    from app.services.integrations.base import NormalizedArtifact
    from app.models.integration import SourceTool
    from app.models.artifact import ArtifactType

    na = NormalizedArtifact(
        company_id="test-company",
        source_tool=SourceTool.SLACK,
        artifact_type=ArtifactType.MESSAGE,
        external_id="ext-1",
        content="Hello world",
        author="Alice",
        author_email="alice@test.com",
        source_created_at=datetime.utcnow(),
        metadata={"channel": "#general"}
    )

    check("NormalizedArtifact stores company_id", na.company_id == "test-company")
    check("NormalizedArtifact stores content", na.content == "Hello world")
    check("NormalizedArtifact stores author", na.author == "Alice")
    check("NormalizedArtifact to_dict returns dict", isinstance(na.to_dict(), dict))
    check("to_dict has source_tool key", 'source_tool' in na.to_dict())
    check("to_dict has content key", 'content' in na.to_dict())


async def main():
    global PASS, FAIL
    print("=" * 60)
    print("Phase 2 - Integration Layer Verification")
    print("=" * 60)

    await test_slack_integration()
    await test_gmail_integration()
    await test_github_integration()
    await test_linear_integration()
    await test_hubspot_integration()
    await test_notion_integration()
    await test_query_interface()
    await test_agent_dispatcher()
    await test_encryption_service()
    await test_rate_limiter()
    await test_artifact_relationships()
    await test_normalized_artifact_model()

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} total checks")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)
    else:
        print("All Phase 2 checks passed!")


if __name__ == "__main__":
    asyncio.run(main())
