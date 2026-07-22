# LoopOS - Planning Document

## Executive Summary

LoopOS is a connective intelligence layer designed for 10-100 person companies that turns organizational artifacts into a self-improving closed loop system. The platform connects fragmented SaaS tools into a unified queryable, learning, and autonomous system that continuously improves organizational effectiveness through specialized AI agents and a data flywheel mechanism.

## Vision Statement

Transform the open-loop nature of SMB operations—where decisions, actions, and outcomes exist in disconnected tools—into a closed-loop intelligence system that learns from every artifact and continuously improves organizational effectiveness.

## Core Value Proposition

1. **Unified Query Interface**: Ask "What did we decide about pricing last week?" and get sourced answers across Slack, Linear, HubSpot, Notion, GitHub
2. **Real-time Deviation Monitoring**: Compare actual performance against goals (response times, sprint alignment, churn targets) and flag drift immediately
3. **Self-Improving Loop**: Every action produces tracked outcomes that feed back into the intelligence layer, making recommendations better over time
4. **Specialized AI Agents**: Seven domain-specific agents (Operations, Customer Intelligence, Revenue, Knowledge, Finance, Alignment, Spec) operate autonomously within their scopes

## SECTION 1: SYSTEM OVERVIEW

### Architectural Philosophy & Five-Layer Stack

LoopOS is built around one principle: every artifact a company produces should be legible to intelligence by default. Every Slack message, every email, every CRM update, every ticket, every commit—all of it feeds into one connected layer that reasons across all of it simultaneously.

This requires an architecture that is:
- **Event-driven** — the system reacts to what happens in the company in real time, not on a human schedule
- **Context-aware** — every agent decision is made with full awareness of everything relevant across all connected tools
- **Outcome-oriented** — every action is measured against a goal and the result feeds back to improve the next decision
- **Tenant-isolated** — every company's data is completely separated at the infrastructure level
- **Production-hardened** — proven patterns from vellum-assistant including context overflow recovery, permission controls v2, and credential execution service isolation
- **Extensible** — skill-based architecture for rapid feature addition without core changes

### The Five-Layer Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        LAYER 5                               │
│                    FLYWHEEL ENGINE                           │
│         Learns from outcomes · Improves agents               │
│         Builds company-specific intelligence                 │
├──────────────────────────────────────────────────────────────┤
│                        LAYER 4                               │
│                      AGENT LAYER                             │
│    7 specialized agents that monitor, reason, and act        │
│    continuously across all connected company tools           │
├──────────────────────────────────────────────────────────────┤
│                        LAYER 3                               │
│                  INTELLIGENCE LAYER                          │
│    Cross-tool reasoning · Goal-state comparison              │
│    Semantic search · Decision extraction                     │
├──────────────────────────────────────────────────────────────┤
│                        LAYER 2                               │
│                    ARTIFACT STORE                            │
│    Every company artifact stored, indexed, and embedded      │
│    for semantic retrieval across all sources                 │
├──────────────────────────────────────────────────────────────┤
│                        LAYER 1                               │
│                  INTEGRATION LAYER                           │
│    Webhook receivers · API connectors · OAuth vault          │
│    Event normalizer · Credential management                  │
└──────────────────────────────────────────────────────────────┘
         ▲                                              ▼       
   COMPANY TOOLS                             COMPANY TOOLS     
   (data flows in)                          (agents act on)    
   Slack · Gmail · HubSpot                  Slack · Linear    
   Linear · Notion · GitHub                 HubSpot · Gmail   
   Stripe · Zoom · G-Drive                  Notion · GitHub   
   Jira · Teams · Salesforce                Stripe · Calendar 
```

### Complete Data Flow — 10 Steps

**STEP 1: EVENT OCCURS IN THE REAL WORLD**
A Slack message is sent. A HubSpot deal changes stage. A Linear ticket is created. A GitHub PR is merged. A Stripe payment is received. A Zoom call ends.

**STEP 2: INTEGRATION LAYER CAPTURES IT**
Webhook receiver catches the real-time event. Scheduled poller catches anything missed. Raw tool-specific data arrives at the system.

**STEP 3: NORMALIZATION**
Raw event transformed into a standardized Artifact object. All artifacts have the same structure regardless of source: content, author, timestamp, source, metadata.

**STEP 4: STORAGE AND EMBEDDING**
Artifact stored in PostgreSQL. Text content converted to vector embedding (text-embedding-3-small). Embedding stored in pgvector. Now semantically searchable.

**STEP 5: AGENT DISPATCH**
Dispatcher reads artifact type and source. Routes to relevant agents as background tasks. Example: new Slack message → Knowledge, Operations, Alignment Agents.

**STEP 6: AGENT CONTEXT RETRIEVAL**
Agent runs semantic search for most relevant artifacts. Retrieves current goal state and recent action history. Builds full context package for reasoning.

**STEP 7: AGENT REASONING**
Agent sends context to LLM (Claude 3.5 Sonnet / Groq). Returns structured decision: should_act, action_type, reasoning, output, confidence, requires_human_approval. Reasoning trace always recorded — no black boxes.

**STEP 8: ACTION EXECUTION**
If human approval required → queue in approval inbox. If auto-execute → post Slack, update HubSpot, create ticket. Action logged with full context and reasoning.

**STEP 9: OUTCOME MEASUREMENT**
System compares goal metric before and after action. Records outcome — success or failure, delta value.

**STEP 10: FLYWHEEL LEARNING**
Nightly batch analyzes all action-outcome pairs. Extracts patterns: what worked, what failed. Updates company-specific agent intelligence. Loop continues. System gets smarter every day.

## SECTION 2: TECHNOLOGY STACK

### Technology Selection Criteria

Every technology choice is evaluated against three criteria:
1. Speed of execution for a small team
2. Native AI/LLM ecosystem compatibility
3. Operational simplicity to minimize infrastructure burden

### Technology Stack

| Technology | Domain | Purpose |
|------------|--------|---------|
| Next.js 14 + TypeScript | Frontend | App Router, SSR, type-safe React |
| Tailwind CSS + shadcn/ui | Frontend | Component library, design system |
| Supabase Realtime | Frontend | Live agent activity feed via WebSockets |
| Recharts | Frontend | Goal-state visualization charts |
| Python 3.11 + FastAPI | Backend API | Async-first, auto-documented, Pydantic validated |
| Celery + Redis | Backend API | Background task processing and scheduling |
| httpx | Backend API | Async HTTP for external API calls |
| CrewAI | Agent Framework | Multi-agent orchestration, role-based agents |
| LangChain | Agent Framework | Tool building and RAG pipelines |
| LangGraph | Agent Framework | Stateful, long-running agent workflows |
| LangSmith | Agent Framework | Agent observability, tracing, evaluation |
| Anthropic Claude 3.5 Sonnet | LLM Providers | Primary 200K context, complex reasoning |
| OpenAI GPT-4o | LLM Providers | Fallback for primary agent reasoning |
| Groq Llama 3 | LLM Providers | High-speed, cost-sensitive classifications |
| PostgreSQL 16 + pgvector | Database | Primary data + vector embeddings unified |
| Redis | Database | Cache and Celery task queue |
| Supabase | Database | Hosted Postgres, auth, realtime subscriptions |
| Clerk | Authentication | User auth, multi-tenant, SSO (Scale plan) |
| Supabase RLS | Authentication | Row-level security, database-enforced isolation |
| Vercel | Infrastructure | Frontend hosting + edge CDN, global delivery |
| Railway | Infrastructure | Backend API hosting, auto-scaling containers |
| Modal | Infrastructure | Python AI workload execution, heavy batch jobs |
| Upstash | Infrastructure | Serverless Redis for queuing and caching |
| AWS KMS | Infrastructure | Encryption key management, 90-day rotation |
| LangSmith | Observability | LLM trace logging and performance tracking |
| OpenTelemetry | Observability | Distributed tracing across services |
| Grafana | Observability | Infrastructure metrics and dashboards |
| Sentry | Observability | Error tracking and alerting |
| MCP (Model Context Protocol) | Protocols | Universal AI agent tool connection standard |
| REST APIs | Protocols | External tool integrations |
| Webhooks | Protocols | Real-time event ingestion from tools |
| OAuth 2.0 | Protocols | External tool authentication |

### Key Technology Rationale

**Python + FastAPI for Backend**
The AI ecosystem is Python-first. Every major agent framework — CrewAI, LangChain, LangGraph, AutoGen — is Python-native. FastAPI provides async-first request handling (critical for I/O-heavy agent operations), automatic API documentation, and Pydantic for type-safe data validation.

**PostgreSQL + pgvector**
Using PostgreSQL with the pgvector extension rather than a separate vector database (Pinecone, Weaviate, Qdrant) is a deliberate architectural decision. pgvector handles vector similarity search natively inside PostgreSQL — one database stores both relational data and vector embeddings, eliminating an entire infrastructure dependency and enabling SQL joins between structured and semantic data.

**Claude 3.5 Sonnet as Primary LLM**
The Alignment Agent and Spec Agent require reasoning across large amounts of cross-tool context simultaneously. Claude 3.5 Sonnet's 200,000 token context window and superior reasoning quality for complex multi-step analysis make it the primary model. Groq with Llama 3 is used for high-frequency, lower-complexity decisions (e.g., classifying whether a Slack message contains a decision) where speed and cost matter more than depth.

**MCP (Model Context Protocol)**
MCP has reached 97 million monthly SDK downloads, backed by Anthropic, OpenAI, Google, and Microsoft. LoopOS adopts MCP as the standard for custom integration connections in Phase 4, enabling any tool with an MCP server to connect to the platform without custom connector code.

## SECTION 3: DATABASE ARCHITECTURE

### Database Design Principle

The database schema is built around one principle: every artifact, action, and outcome must be traceable end to end from the original event in an external tool, through the agent's reasoning, to the outcome that resulted.

### Core Data Relationships

```
COMPANY
  │
  ├── INTEGRATIONS (which tools are connected, credentials)
  │
  ├── ARTIFACTS (everything captured from all connected tools)
  │      └── EMBEDDINGS (1536-dim vector representations)
  │
  ├── GOALS (what should be happening — OKRs, targets)
  │      └── CURRENT VALUES (what is actually happening)
  │
  ├── DECISIONS (extracted from artifacts by Knowledge Agent)
  │      └── SPECS (generated from decisions by Spec Agent)
  │
  ├── AGENT ACTIONS (complete audit trail of all agent actions)
  │      └── OUTCOMES (measured results — before/after goal delta)
  │
  └── AGENT INTELLIGENCE (learned patterns per agent per company)
```

### Core Tables

**COMPANIES**
Stores each tenant company. Every other table references this. Tenant isolation is enforced at the PostgreSQL level through Row-Level Security — every query automatically filters to the requesting company's data only.

**INTEGRATIONS**
Records every tool connected to a company account. Stores encrypted credentials, connection status, last sync timestamp, and tool-specific configuration. Credentials are encrypted with AES-256-GCM before storage, managed by AWS KMS, decrypted only at request time in an isolated service, never returned in API responses, never written to logs.

**ARTIFACTS**
The most important table in the system. Every piece of company data from every connected tool is stored here as a normalized artifact. Fields include: source tool, artifact type (message, email, ticket, deal, commit, document, call, transaction, meeting), raw content as plain text, tool-specific metadata as JSON, and the 1536-dimensional vector embedding. The embedding field uses pgvector's ivfflat index for fast approximate nearest-neighbor search.

**GOALS**
Stores what the company says should be happening. Each goal has a metric name (a standardized identifier mapping to a calculation function), a target value, an operator (less than, greater than, equal to), the current calculated value, and a status (on track, at risk, off track). The Goal-State Comparator updates these every 15 minutes.

**DECISIONS**
Decisions extracted from artifacts by the Knowledge Agent. Each decision links back to the source artifact, includes the decision content, who made it, when, and optionally links to the outcome. This is the company's institutional memory.

**AGENT ACTIONS**
A complete audit trail of every action every agent has ever taken. Fields include: agent name, action type, full context the agent saw, the reasoning produced, the output, which artifacts informed the decision, which goal was served, and the measured outcome. No agent action is taken without being recorded.

**OUTCOMES**
Measures whether each agent action achieved its intended goal. Records the goal metric value before and after, the delta (automatically calculated), whether the action was successful, and optional human feedback. This table is the foundation of the flywheel.

**SPECS**
Structured specifications generated by the Spec Agent from decisions. Each spec contains: title, context, acceptance criteria (array), dependencies (array), estimated effort, suggested assignee, priority, and the external ticket ID once created in Linear or Jira.

**AGENT INTELLIGENCE**
Company-specific learned patterns per agent. Updated nightly by the Flywheel Engine. Contains patterns that led to successful versus failed outcomes for this specific company, overall success rate, and sample size. This is what makes each company's LoopOS deployment progressively unique.

### Multi-Tenant Isolation

**Row-Level Security**
RLS is enabled on every table. A database policy restricts every query to rows belonging to the company_id of the authenticated user. This isolation is enforced at the PostgreSQL level — even if application code has a bug that would otherwise return wrong data, the database will not serve it. Company A's data is physically inaccessible to Company B's requests regardless of application behavior.

## SECTION 4: INTEGRATION ARCHITECTURE

### The Three-Phase Integration Pattern

Every tool integration in LoopOS follows the same three-phase pattern without exception. This consistency means adding a new integration is a predictable, bounded engineering task rather than a custom project each time.

**PHASE 1: AUTHENTICATION**
Company connects via OAuth 2.0 flow. Access token and refresh token received. Credentials encrypted with AES-256-GCM. Encryption key managed by AWS KMS. Encrypted credentials stored in integrations table. Raw credentials never stored anywhere.

**PHASE 2: DATA INGESTION (two parallel mechanisms)**
- **PRIMARY — Webhook receiver**: Tool pushes events to LoopOS in real time. Endpoint receives, validates, processes. Response returned within 200ms. Actual processing happens in background task.
- **SECONDARY — Scheduled poller**: Runs on fixed intervals via Celery beat. Fetches any updates the webhook missed. Also runs on initial connection to backfill history.

**PHASE 3: NORMALIZATION**
Raw tool-specific event data arrives in the system. Normalizer transforms it into a standard Artifact. All artifacts have the same fields regardless of source. Source-specific details preserved in metadata field. Normalized artifact enters the embedding pipeline. Stored in artifact store. Dispatched to relevant agents.

### Normalized Artifact Standard

Regardless of which tool an event came from, it becomes the same structure before entering the artifact store. This is the key architectural decision that makes cross-tool reasoning possible — the intelligence layer never needs to know whether it is reading a Slack message or a HubSpot note.

```typescript
interface NormalizedArtifact {
  company_id: string;           // Which company this belongs to (always scoped)
  source_tool: 'slack' | 'hubspot' | 'linear' | 'gmail' | 
               'github' | 'notion' | 'stripe' | 'zoom' |
               'google_drive' | 'jira' | 'salesforce' |
               'teams' | 'asana' | 'quickbooks' | 'intercom';
  artifact_type: 'message' | 'email' | 'ticket' | 'deal' |
                 'document' | 'commit' | 'call' | 'transaction' |
                 'meeting' | 'review' | 'comment' | 'build';
  external_id: string;          // Original ID in the source tool (for deduplication and updates)
  content: string;             // Plain text representation. This is what gets embedded and what agents read. Must be rich, human-readable, and complete.
  author: string;              // Full name of the person
  author_email: string;        // Email address for identity resolution
  source_created_at: Date;     // When this was created in the source tool
  metadata: Record<string, any>; // Tool-specific fields as JSON. Preserved for context but not required for agent reasoning
}
```

### Integration Specifications

#### Integration 1: Slack
**Property**: Detail
- **Protocol**: OAuth 2.0
- **What is Captured**: Messages, thread replies, reactions, channel membership, DMs (opt-in), file uploads
- **Permissions**: channels:history, channels:read, users:read, reactions:read, chat:write, files:read
- **Primary Ingestion**: Slack Events API — events: message, reaction_added, member_joined_channel, app_mention
- **Secondary Ingestion**: Slack Web API polling every 15 minutes, also used for initial history backfill
- **Rate Limits**: Tier 3: 50 req/min, Tier 2: 20 req/min. Exponential backoff with jitter on all calls.
- **Agents Using Data**: Knowledge Agent (decisions), Operations Agent (blockers), Alignment Agent (priorities), Customer Intelligence (mentions), Spec Agent (decision language)

**Content normalization example**:
- **Raw**: user U01ABC123, text: 'we should prioritize the auth bug', channel: #engineering, thread reply
- **Normalized**: 'Sarah Chen said in #engineering: we should prioritize the auth bug over the new dashboard feature (reply in thread started 20 min ago)'

#### Integration 2: Gmail
- **Protocol**: Google OAuth 2.0
- **What is Captured**: Sent/received emails, thread conversations, email metadata, calendar events, Meet recordings
- **Permissions**: gmail.readonly, gmail.send (agent drafting), calendar.readonly
- **Primary Ingestion**: Gmail Push Notifications via Google Cloud Pub/Sub notifies on new email, we fetch full message
- **Secondary Ingestion**: Gmail History API using historyId runs every 30 minutes for missed notifications
- **Privacy Model**: Company admins choose which accounts LoopOS reads. Individual users can opt out. Raw email purged after 24 hours, only normalized artifact retained.
- **Agents Using Data**: Customer Intelligence (primary), Revenue Agent (deal threads), Knowledge Agent (decisions), Spec Agent (product decisions)

#### Integration 3: HubSpot
- **Protocol**: OAuth 2.0
- **What is Captured**: All deals with property history, contacts, companies, notes, call records, email activity, deal stage history
- **Permissions**: crm.objects.deals.read/write, crm.objects.contacts.read, crm.objects.companies.read, crm.objects.notes.read, crm.timeline.events.read
- **Primary Ingestion**: HubSpot Webhooks - deal.propertyChange, contact.propertyChange, contact.creation, note.creation
- **Secondary Ingestion**: CRM Search API hourly for deals modified in last 60 minutes. Daily full sync at 2am.
- **Data Freshness**: Real-time: <30 seconds. Hourly sync: catch-up. Daily full sync: reconciliation.
- **Agents Using Data**: Revenue Agent (primary), Customer Intelligence, Finance Agent (closed revenue), Knowledge Agent (deal notes)

#### Integration 4: Linear
- **Protocol**: OAuth 2.0 + GraphQL API
- **What is Captured**: All issues (title, description, status, assignee, priority, estimate, labels, due date), projects, cycles/sprints, comments, cycle metrics
- **Permissions**: read:issues, read:projects, read:cycles, write:issues (Spec Agent ticket creation)
- **Primary Ingestion**: Linear Webhooks - Issue.create, Issue.update, Comment.create, Cycle.create, Cycle.update
- **Secondary Ingestion**: GraphQL API polling every 30 minutes for aggregate sprint metrics not available via webhooks
- **Agents Using Data**: Operations Agent (primary - sprint progress, overdue tasks), Alignment Agent (sprint vs priorities), Spec Agent (creates tickets from specs)

#### Integration 5: GitHub
- **Protocol**: GitHub OAuth App
- **What is Captured**: Commits (message, author, files changed, branch), PRs (title, description, reviews, merge status), issues, code review comments, Actions workflow results
- **Permissions**: repo (read), workflow (read)
- **Primary Ingestion**: GitHub Webhooks - push, pull_request, pull_request_review, issues, workflow_run, create (branch/tag)
- **Secondary Ingestion**: GitHub REST API polling every 60 minutes for repository statistics and commit history
- **Agents Using Data**: Operations Agent (correlates PRs with ticket completions), Alignment Agent (primary - what is engineering actually building), Spec Agent (links specs to repos)

#### Integration 6: Notion
- **Protocol**: Notion OAuth integration
- **What is Captured**: All pages in connected workspaces, database entries, meeting notes, decision logs, product specs, OKR documentation, roadmap documents
- **Permissions**: Read access to selected pages and databases, write access for Knowledge Agent pages
- **Primary Ingestion**: Notion API polling every 30 minutes (Notion does not support webhooks). Fetches pages updated since last sync using last_edited_time.
- **Chunking Strategy**: Long pages chunked into 1000-token segments with 200-token overlap before embedding, enabling paragraph-level semantic search
- **Agents Using Data**: Knowledge Agent (primary - reads and writes company knowledge), Alignment Agent (OKRs, roadmap), Spec Agent (reads specs for context)

#### Integration 7: Stripe
- **Protocol**: Stripe Webhooks + read-only restricted API key
- **What is Captured**: Payment intents, charges, subscription events (created/updated/canceled/past_due), invoices, customer updates, refunds, disputes
- **Permissions**: Read access to charges, customers, subscriptions, invoices
- **Primary Ingestion**: Stripe Webhooks - payment_intent.succeeded/failed, customer.subscription.updated/deleted, invoice.paid/payment_failed, charge.dispute.created
- **Secondary Ingestion**: Stripe API daily sync for monthly revenue calculation and MRR reconciliation
- **Agents Using Data**: Finance Agent (primary and sole consumer - revenue, anomaly detection, churn signals), Revenue Agent (expansion/upsell from subscription data)

#### Integration 8: Zoom
- **Protocol**: Zoom OAuth App
- **What is Captured**: Meeting recordings (auto-transcribed via Whisper API / Deepgram), participants, duration, summaries, metadata
- **Permissions**: recording:read, meeting:read
- **Primary Ingestion**: Zoom Webhooks - recording.completed. LoopOS downloads audio, transcribes, stores transcript as normalized artifact.
- **Secondary Ingestion**: Zoom REST API polling for meeting metadata and participant lists
- **Agents Using Data**: Knowledge Agent (primary - decisions and action items from transcripts, meeting summaries to Slack), Spec Agent (product decisions from meetings)

#### Integration 9: Google Drive
- **Protocol**: Google OAuth 2.0
- **What is Captured**: Documents, spreadsheets, presentations, shared files in connected drives. Text extracted from all file types.
- **Permissions**: drive.readonly, drive.file (for agent-created documents)
- **Primary Ingestion**: Google Drive Push Notifications via Cloud Pub/Sub on file changes
- **Secondary Ingestion**: Drive API polling every 30 minutes using pageToken for incremental changes
- **Chunking Strategy**: Long documents chunked into 1000-token segments with 200-token overlap (same as Notion)
- **Agents Using Data**: Knowledge Agent (extracts decisions from docs), Alignment Agent (roadmap and strategy documents), Spec Agent (product specifications)

#### Integration 10: Jira (Enterprise Alternative to Linear)
- **Protocol**: Atlassian OAuth 2.0 + REST API
- **What is Captured**: Issues (all fields: summary, description, status, assignee, priority, story points, sprint, labels), projects, sprints, comments, workflow transitions
- **Permissions**: read:jira-work, write:jira-work (Spec Agent ticket creation)
- **Primary Ingestion**: Jira Webhooks - jira:issue_created, jira:issue_updated, comment_created, sprint_started, sprint_closed
- **Secondary Ingestion**: Jira REST API polling every 30 minutes for sprint velocity and burndown metrics
- **Agents Using Data**: Operations Agent (same role as Linear - sprint tracking, blockers), Alignment Agent, Spec Agent (creates Jira tickets from specs)

#### Integration 11: Salesforce (Enterprise CRM)
- **Protocol**: Salesforce OAuth 2.0 (Connected App)
- **What is Captured**: Opportunities (all stages, amounts, close dates, activities), accounts, contacts, leads, tasks, events, email activity, call logs
- **Permissions**: api (full API access, read), chatter_api (read activity feeds)
- **Primary Ingestion**: Salesforce Streaming API - PushTopics on Opportunity and Account objects for real-time changes
- **Secondary Ingestion**: SOQL polling hourly for opportunities modified in last 60 minutes. Daily full sync.
- **Agents Using Data**: Revenue Agent (same role as HubSpot — pipeline monitoring, stalled deals), Customer Intelligence, Finance Agent, Knowledge Agent

#### Integration 12: Microsoft Teams
- **Protocol**: Microsoft OAuth 2.0 (Azure AD)
- **What is Captured**: Channel messages, thread replies, mentions, file shares, meeting transcripts (via Teams Meetings API)
- **Permissions**: ChannelMessage.Read.All, Chat.Read, Files.Read.All, OnlineMeetings.Read.All
- **Primary Ingestion**: Microsoft Graph Change Notifications - subscriptions on channel messages and chats
- **Secondary Ingestion**: Graph API polling every 15 minutes for missed notifications (Graph subscriptions expire; poller ensures continuity)
- **Agents Using Data**: Knowledge Agent (decisions from Teams threads), Operations Agent (blocker detection), Alignment Agent (priority statements), Customer Intelligence

#### Integration 13: Asana / Trello
- **Protocol**: OAuth 2.0
- **What is Captured**: Tasks (name, description, assignee, due date, status, dependencies, tags), projects, sections, milestones, comments
- **Permissions**: tasks:read, projects:read, tasks:write (Spec Agent creation)
- **Primary Ingestion**: Asana Webhooks on task and project events. Trello Webhooks on card and board events.
- **Secondary Ingestion**: API polling every 30 minutes for task completion metrics
- **Agents Using Data**: Operations Agent (task tracking, overdue items), Alignment Agent (project work vs. priorities), Spec Agent

#### Integration 14: QuickBooks / Xero
- **Protocol**: OAuth 2.0
- **What is Captured**: Invoices (paid, unpaid, overdue), expenses, accounts payable/receivable, P&L data, bank transactions, payroll summaries
- **Permissions**: accounting.transactions.read, accounting.reports.read
- **Primary Ingestion**: QuickBooks Webhooks / Xero Webhooks for transaction and invoice events
- **Secondary Ingestion**: API polling daily for reconciled financial reports and P&L summaries
- **Agents Using Data**: Finance Agent (primary - budget vs actual, expense tracking, cash flow monitoring alongside Stripe)

#### Integration 15: Intercom / Zendesk
- **Protocol**: OAuth 2.0 / API token
- **What is Captured**: Support tickets (subject, status, priority, assignee, resolution time), customer conversations, CSAT scores, tags, contact history
- **Permissions**: tickets:read, conversations:read, contacts:read
- **Primary Ingestion**: Webhooks on ticket creation, status changes, conversation events
- **Secondary Ingestion**: API polling hourly for ticket volume metrics and first-response-time calculations
- **Agents Using Data**: Customer Intelligence (primary — support signal feeds into health scoring), Operations Agent (ticket SLA monitoring), Finance Agent (churn correlation)

#### Integration 16: Google Calendar / Outlook
- **Protocol**: Google OAuth 2.0 / Microsoft OAuth 2.0
- **What is Captured**: Meeting events (title, attendees, duration, description, meeting links), recurring meetings, out-of-office blocks
- **Permissions**: calendar.readonly
- **Primary Ingestion**: Google Calendar Push Notifications / Outlook Graph Change Notifications on calendar events
- **Secondary Ingestion**: API polling daily for upcoming week's meetings for proactive briefings
- **Agents Using Data**: Knowledge Agent (links meeting artifacts to transcripts and decisions), Operations Agent (team availability context for scheduling alerts)

### Integration Roadmap

| Integration | Phase | Status |
|-------------|-------|--------|
| Slack | Phase 1 — MVP | Implemented |
| Gmail | Phase 1 — MVP | Implemented |
| HubSpot | Phase 1 — MVP | Implemented |
| Linear | Phase 1 — MVP | Implemented |
| Notion | Phase 1 — MVP | Implemented |
| GitHub | Phase 2 | Implemented |
| Stripe | Phase 2 | Implemented |
| Google Drive | Phase 2 | Implemented |
| Zoom | Phase 2 | Implemented |
| Google Calendar | Phase 2 | Implemented |
| Jira | Phase 3 | Not started |
| Salesforce | Phase 3 | Not started |
| Microsoft Teams | Phase 3 | Not started |
| Asana / Trello | Phase 3 | Not started |
| QuickBooks / Xero | Phase 3 | Not started |
| Intercom / Zendesk | Phase 3 | Not started |
| Outlook / MS Calendar | Phase 3 | Not started |
| Pipedrive | Phase 3 | Not started |
| GitLab | Phase 3 | Not started |
| Rippling / Gusto / BambooHR | Phase 3 | Not started |
| MCP server bridge | Phase 4 | Implemented |
| Zapier / Make bridge | Phase 4 | Implemented |
| REST API (custom) | Phase 4 | Implemented |

## SECTION 5: AI AGENT DESIGN

### Five-Phase Agent Execution Pattern

Every agent in LoopOS follows the same five-phase execution pattern. This consistency means every agent is predictable, testable, observable, and replaceable without breaking the system.

**PHASE 1: TRIGGER**
- **EVENT-DRIVEN**: A new artifact arrived relevant to this agent.
- **SCHEDULE-DRIVEN**: This agent runs on a fixed interval.
- **GOAL-DRIVEN**: A goal status changed to 'at risk' or 'off track'.

**PHASE 2: CONTEXT RETRIEVAL**
- **SEMANTIC SEARCH**: Most relevant artifacts via vector similarity.
- **GOAL STATE**: Current goal metric value vs. target.
- **ACTION HISTORY**: Last 10 actions to avoid repetition.
- **COMPANY INTELLIGENCE**: Learned patterns from flywheel for this company.

**PHASE 3: REASONING**
Full context sent to LLM. Structured decision returned: should_act | action_type | reasoning | output | confidence (0.0–1.0) | requires_human_approval. Reasoning trace always recorded. No black-box decisions.

**PHASE 4: EXECUTION**
If human approval required → queue in approval inbox. If auto-execute → post Slack, update HubSpot, create ticket. Log everything to agent_actions table regardless of action taken. A 'no action needed' decision is still logged.

**PHASE 5: OUTCOME MONITORING**
Goal metric measured before and after action completes. Delta calculated automatically. Success/failure determined. Outcome feeds into nightly flywheel run.

### Agent Dispatcher — Routing Logic

When a new artifact arrives, the dispatcher determines which agents to trigger. Smart routing prevents unnecessary LLM calls and keeps compute costs low.

| Artifact Type | Source Tool | Agents Triggered |
|---------------|-------------|------------------|
| message | slack | Knowledge, Operations, Alignment, Customer Intelligence (if customer detected), Spec Agent (if decision language) |
| deal | hubspot | Revenue Agent, Customer Intelligence |
| contact | hubspot | Customer Intelligence |
| email | gmail | Customer Intelligence, Knowledge Agent |
| ticket | linear / jira | Operations Agent, Alignment Agent |
| commit | github | Operations Agent, Alignment Agent |
| pull_request | github | Operations Agent, Alignment Agent |
| transaction | stripe | Finance Agent, Revenue Agent |
| meeting | zoom | Knowledge Agent, Spec Agent |
| document | notion | Knowledge Agent, Alignment Agent |
| document | google_drive | Knowledge Agent, Alignment Agent |
| message | teams | Knowledge, Operations, Alignment, Customer Intelligence |
| ticket | asana | Operations Agent, Alignment Agent |
| invoice | quickbooks / xero | Finance Agent |
| ticket | intercom / zendesk | Customer Intelligence, Operations Agent |

### Agent Specifications

#### Agent 1: Operations Agent
- **Role**: Watches all active tasks and projects across Linear, Jira, Asana, Trello, Notion, and GitHub
- **Goal Monitored**: sprint_completion_rate — target set by company (e.g., 80%)
- **Trigger Conditions**: New ticket created, ticket status changed, sprint updated, scheduled every 4 hours
- **Context Retrieved**: Overdue tasks, Slack messages with blocker language (blocked/waiting/stuck/need approval), current sprint plan and completion rate, last 10 actions
- **Auto Actions**: Post Slack alert, update ticket status in Linear/Jira, generate weekly operations briefing
- **Approval Required**: Reassigning tasks to another person, closing tasks as won't-do, cross-system ticket moves
- **Output Example**: '3 tickets overdue in current sprint. 2 have blocker mentions in Slack. Sprint completion: 61% with 3 days remaining (target: 80%). Alert posted to #engineering.'

#### Agent 2: Customer Intelligence Agent
- **Role**: Monitors every customer touchpoint across email, CRM, support tools, and Slack
- **Goal Monitored**: monthly_churn_rate_pct (e.g., < 3%), customer_health_score per customer
- **Trigger Conditions**: New customer email, HubSpot/Salesforce contact updated, customer mentioned in Slack, daily at 7am
- **Context Retrieved**: Customer emails (30 days), CRM notes and activity (30 days), deal history, support ticket history (Intercom/Zendesk), Slack mentions
- **Health Score Signals**: 
  - **Positive**: email reply <24hr, expansion inquiry, positive sentiment, deal progressing
  - **Negative**: unanswered email >5 days, negative sentiment, support tickets increasing, contact going quiet, deal stalled >7 days
- **Auto Actions**: Post customer health summary to Slack, update health score in HubSpot, create at-risk task in Linear
- **Approval Required**: Sending emails on behalf of team member, flagging customer as churned
- **Output Example**: '4 customers showing churn signals. Acme Corp: no response 9 days, 2 support tickets opened. Draft follow-up ready for Sarah's review.'

#### Agent 3: Revenue Agent
- **Role**: Monitors the sales pipeline and revenue health continuously across HubSpot and Salesforce
- **Goal Monitored**: monthly_revenue_usd, pipeline_velocity_days — targets set by company
- **Trigger Conditions**: CRM deal updated, new deal created, scheduled daily at 8am
- **Context Retrieved**: All open deals and current stages, deals with no activity >5 days, email threads related to active deals, monthly revenue vs. target, historical win/loss patterns
- **Auto Actions**: Post daily pipeline briefing to Slack, flag stalled deals with context, draft follow-up for stalled deal, update deal forecast in CRM
- **Approval Required**: Sending outreach on behalf of salesperson, changing deal close date
- **Output Example**: 'Pipeline update: $87K closed vs. $150K target (58%). 2 deals stalled >7 days totaling $28K. Draft follow-ups ready. 3 deals need proposals this week.'

#### Agent 4: Knowledge Agent
- **Role**: Makes the company's institutional knowledge queryable and alive. Captures decisions before they are lost.
- **Goal Monitored**: decision_capture_rate — target: >90% of decisions documented within 24 hours
- **Trigger Conditions**: New Slack/Teams message with decision language, meeting recording transcribed, new document in Notion/Drive, every 2 hours
- **Decision Patterns**: 'we should', 'let's go with', 'decided', 'we'll', 'agreed', 'the plan is', 'going with', 'confirmed'
- **Context Retrieved**: Recent messages with decision patterns, meeting transcripts, existing decision log (deduplication), related documents
- **Auto Actions**: Create decision entry in decisions table, create Notion page, post decision summary to designated Slack channel, link related decisions and artifacts, flag outdated documentation
- **Approval Required**: Deleting or merging decision records, publishing to external-facing knowledge base
- **Output Example**: '7 decisions captured today. Notable: pricing decision from #leadership documented. Wednesday all-hands summary posted to Notion. 3 pages flagged outdated (>6 months).'

#### Agent 5: Finance Agent
- **Role**: Monitors financial health in real time across Stripe, QuickBooks, and Xero
- **Goal Monitored**: monthly_revenue_usd, monthly_churn_rate_pct, cash_flow, expense_vs_budget
- **Trigger Conditions**: Stripe payment received or failed, subscription created/canceled, daily at 7am
- **Context Retrieved**: All Stripe transactions (30 days), subscription status changes, monthly revenue vs. target, month-over-month comparison, learned anomaly baseline
- **Anomaly Detection**: Revenue below daily average, spike in failed payments, unusual refund volume, multiple cancellations in one day. Baseline is company-specific — learned via flywheel.
- **Auto Actions**: Generate daily revenue summary to Slack, generate weekly financial briefing, flag anomalies immediately, compare actual vs. budget
- **Approval Required**: All write operations (read-only by design)
- **Output Example**: 'Daily revenue: $3,240 (daily avg: $2,890). MRR: $67,400 vs. $75,000 target (89.9%). Anomaly: 3 subscription cancellations today vs. avg 0.4/day. All from same plan tier.'

#### Agent 6: Alignment Agent
- **Role**: Flags when engineering is building the wrong thing. Continuously compares stated priorities against actual work in progress.
- **Goal Monitored**: sprint_priority_alignment_pct — target set by company (e.g., >75%)
- **Trigger Conditions**: Linear/Jira sprint updated, new GitHub commits, new leadership decision captured, daily at 9am
- **What Should Be Built**: OKRs and roadmap from Notion/Drive, priority statements from leadership (Slack, Teams, meetings), strategic decisions in decision log
- **What Is Being Built**: Current sprint tickets in Linear/Jira, GitHub commits and PRs (last 7 days), engineering Slack/Teams discussions
- **Classification**: 
  - **ALIGNED**: directly addresses stated priority or OKR
  - **MISALIGNED**: no connection to stated priority
  - **UNCLEAR**: insufficient context to determine
- **Context Retrieved**: OKR documents, leadership priority statements (last 30 days), all current sprint tickets, GitHub commits (7 days), previous alignment scores for trend
- **Auto Actions**: Post alignment report to leadership channel, flag specific misaligned tickets with evidence, suggest sprint rebalancing, update alignment score in goal dashboard
- **Approval Required**: Moving or removing tickets from sprint, all Linear/Jira write operations in this agent
- **Output Example**: 'Sprint alignment: 64% (target: 75%). Q3 priority: churn reduction. Current: 8 tickets on new features, 3 on retention. Dashboard redesign ($2K) and API refactor ($3K) have no connection to stated priorities.'

#### Agent 7: Spec Agent
- **Role**: Closes the gap between 'we decided to do X' and 'here is exactly what X means, ready to build.'
- **Goal Monitored**: decision_to_spec_conversion_rate — target: >80% of engineering decisions have a spec within 24 hours
- **Trigger Conditions**: New decision created by Knowledge Agent, new meeting transcript processed, decision language detected in Slack/Teams, every 4 hours
- **Context Retrieved**: Unspecced decisions (last 24 hours), related code repositories from GitHub, existing specs (deduplication), codebase architecture from Notion, team member expertise signals
- **Spec Structure**: Title (imperative), Context (why it matters, links to source decision), Acceptance Criteria (3–5 testable conditions), Dependencies (files, APIs, services), Estimated Effort (S/M/L/XL), Suggested Assignee (based on GitHub/Slack signals), Priority (based on alignment with company goals)
- **Auto Actions**: Create spec in specs table, create Linear/Jira ticket with spec as description, link ticket to source decision, post spec summary to #engineering
- **Approval Required**: Specs estimated as XL (very large), specs touching security-sensitive systems
- **Output Example**: '3 specs generated. (1) Add webhook retry mechanism — ENG-247 created, Effort: M. (2) Improve onboarding email sequence — GROWTH-89 created, Effort: S. (3) Redesign pricing page — Queued for human approval (large scope).'

### Agent Coordination Patterns

**SEQUENTIAL PATTERN**:
Knowledge Agent extracts decision → Spec Agent receives decision trigger → Spec Agent generates spec → Operations Agent monitors spec's ticket

**PARALLEL PATTERN (same artifact, simultaneous)**:
New Slack message arrives → (simultaneously) Knowledge Agent (extracts any decision), Operations Agent (checks for blocker language), Alignment Agent (checks for priority signal)

**FEEDBACK PATTERN**:
Alignment Agent flags misalignment → Creates task in Linear → Operations Agent picks up new task → Operations Agent monitors its progress

### Human-in-the-Loop Design

**Non-Negotiable Principle**: High-stakes actions always require human approval before execution. Agents that take consequential actions without human oversight are not acceptable in production.

| Action | Approval Required | Agent |
|--------|------------------|-------|
| Sending emails on behalf of team members | Always required | All agents |
| Reassigning tasks to another person | Always required | Operations Agent |
| Closing or deleting any company record | Always required | All agents |
| Any action on security-sensitive systems | Always required | All agents |
| Specs estimated as XL (extra-large) | Always required | Spec Agent |
| Moving tickets in/out of active sprints | Always required | Alignment Agent |
| Posting in Slack channels | Configurable | All agents |
| Creating Linear/Jira tickets | Configurable | Spec Agent |
| Updating HubSpot/Salesforce deal stages | Configurable | Revenue Agent |
| Logging and recording actions | Never required | All agents |
| Generating internal summaries | Never required | All agents |
| Updating goal metric values | Never required | All agents |

## SECTION 6: INTELLIGENCE LAYER

### The Query Engine: Making the Company Queryable

The Query Engine answers questions like 'What did we decide about pricing last week?' by searching across all company tools simultaneously and synthesizing a sourced answer.

**HOW A QUERY IS PROCESSED**:

**STEP 1: QUERY RECEIVED**
User or agent submits natural language question. Example: 'Which customers are at risk this month?'

**STEP 2: QUERY EMBEDDING**
Question converted to vector embedding (text-embedding-3-small). Same model as artifact embeddings — semantic similarity search.

**STEP 3: SEMANTIC SEARCH**
pgvector searches all artifacts for this company. Filtered by: company_id (always). Optional filters: source_tool, artifact_type, date range. Returns top-K most semantically similar artifacts (default: 15).

**STEP 4: CONTEXT ASSEMBLY**
Artifacts assembled into context. Each labeled with source, tool, author, date, content.

**STEP 5: LLM SYNTHESIS**
Context sent to Claude 3.5 Sonnet with original question. LLM synthesizes answer using ONLY provided context. LLM cites specific sources in the answer. No hallucination.

**STEP 6: RESPONSE RETURNED**
- **answer**: The direct answer
- **sources**: List of artifacts used (tool, date, preview)
- **confidence**: How confident the system is
- **caveats**: Important limitations (e.g., 'HubSpot not connected')

### The Goal-State Comparator

The Goal-State Comparator runs every 15 minutes and continuously compares what is actually happening against what should be happening. This is the mechanism that closes the loop.

**GOAL-STATE COMPARATOR — EVERY 15 MINUTES**:

**FOR EACH ACTIVE GOAL**:

**1. IDENTIFY THE METRIC CALCULATOR**
| Metric | Calculator |
|--------|------------|
| support_first_response_time | Gmail + Intercom/Zendesk avg reply time |
| sprint_priority_alignment_pct | Linear/Jira + Notion ticket classification |
| pipeline_velocity_days | HubSpot/Salesforce avg days to close |
| monthly_churn_rate_pct | Stripe cancellations / total subscriptions |
| monthly_revenue_usd | Stripe paid invoices sum |
| sprint_completion_rate | Linear/Jira completed / total story points |
| decision_capture_rate | decisions table vs. estimated from artifacts |
| customer_health_score | Cross-tool signal aggregation per customer |
| expense_vs_budget | QuickBooks/Xero actual vs. budget |

**2. EVALUATE STATUS**
- **less_than operator** (e.g., churn < 3%):
  - current ≤ target: ON TRACK
  - target < current ≤ target×1.2: AT RISK
  - current > target×1.2: OFF TRACK

- **greater_than operator** (e.g., revenue > $50K):
  - current ≥ target: ON TRACK
  - target×0.8 ≤ current < target: AT RISK
  - current < target×0.8: OFF TRACK

**3. UPDATE AND TRIGGER**
Store new current_value and status. Goal dashboard updates via Supabase Realtime. If OFF TRACK → trigger responsible agent immediately. If AT RISK → trigger agent on next scheduled cycle. If ON TRACK → log for flywheel data. No action.

## SECTION 7: DATA FLYWHEEL MECHANISM

### Why the Flywheel Is the Moat

Without the flywheel, LoopOS is a capable AI tool. With the flywheel, LoopOS becomes institutional intelligence that belongs to the company. At month 12, LoopOS for Company A is a completely different product than LoopOS for Company B even if they are the same size and industry. The patterns are company-specific, non-transferable, and invisible to any competitor.

### The Complete Flywheel Cycle

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   ARTIFACT CAPTURED                                         │
│   New company data from any tool                            │
│         │                                                   │
│         ▼                                                   │
│   AGENT ACTS                                                │
│   Agent reasons and takes action.                           │
│   Full reasoning trace recorded.                            │
│         │                                                   │
│         ▼                                                   │
│   OUTCOME MEASURED                                          │
│   Goal metric before and after. Success/failure determined. │
│         │                                                   │
│         ▼                                                   │
│   PATTERN DETECTED           (NIGHTLY BATCH — 2AM)          │
│   Flywheel Engine analyzes all action-outcome pairs.        │
│   Compares successful vs. failed. Identifies company-       │
│   specific patterns invisible to generic tools.             │
│         │                                                   │
│         ▼                                                   │
│   INTELLIGENCE UPDATED                                      │
│   Company-specific agent intelligence updated.              │
│   Applied to all future reasoning prompts.                  │
│         │                                                   │
│         ▼                                                   │
│   BETTER NEXT DECISION                                      │
│   Next similar situation → better decision using            │
│   learned patterns specific to this company.                │
│         │                                                   │
│         └──────────────────► BACK TO TOP                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Flywheel Engine — Nightly Batch Operation

**INPUT**: All agent_actions with linked outcomes from last 30 days for this company.

**STEP 1: GROUP BY AGENT**
Separate action-outcome pairs per agent.

**STEP 2: SEPARATE SUCCESSFUL FROM FAILED**
- Successful: outcome.success = true
- Failed: outcome.success = false
- Calculate success rate per agent.

**STEP 3: PATTERN EXTRACTION (per agent)**
Send successful and failed pairs to LLM. Ask: 'What patterns led to success? What patterns led to failure? What is unique about how this company responds?'

**Examples of patterns the flywheel learns**:

**OPERATIONS AGENT**:
'This team responds better to Slack alerts that tag the specific person. Alerts sent Monday mornings are ignored. Tue-Thu 9am-11am = highest response.'

**REVENUE AGENT**:
'Deals that go quiet for 5+ days almost never close. Early follow-up on day 3 is significantly more effective than waiting. Deals with 3+ contacts have 2x close rate vs. single contact deals.'

**ALIGNMENT AGENT**:
'This company redefines priorities every 2-3 weeks. Weight Slack leadership statements from last 14 days more heavily than older OKR docs.'

**STEP 4: UPDATE AGENT INTELLIGENCE**
Stored in agent_intelligence table: company_id, agent_name, patterns, success_rate, sample_size, updated_at

**STEP 5: APPLY AT RUNTIME**
- **BASE PROMPT** (same for all companies): 'You are the Revenue Agent. Keep deals moving.'
- **COMPANY-SPECIFIC ADDITION** (unique per company): 'PATTERNS LEARNED FOR THIS COMPANY (47 actions, 74% success): — Deals in Proposal Sent with no email reply in 4 days have 89% churn probability. Act on day 3, not day 7. — Decision maker is almost always the CTO, not the CEO. Apply these patterns in your reasoning.'

### Embedding Drift Detector

As companies change — new priorities, pivots, new products, team growth — the flywheel detects when old learned patterns are no longer valid.

**WHAT IT DETECTS**: A significant shift in the company's language, priorities, or focus that means old patterns may no longer apply.

**HOW IT WORKS (runs weekly, Sunday)**:
1. Calculate 'centroid' (average embedding) of all artifacts from the last 7 days.
2. Compare to centroid from 30 days ago using cosine distance.
3. If cosine distance > 0.3 → significant drift detected. Flag company intelligence for recalibration.
4. Flywheel re-runs with higher weight on recent outcomes (last 14 days). Old contradicting patterns discounted.

**EXAMPLES OF DRIFT THAT TRIGGERS RECALIBRATION**:
- Company pivots B2C → B2B: customer patterns invalid.
- Company doubles team size: operations patterns may not scale.
- Company launches new product: alignment patterns shift.

### Compounding Intelligence Over Time

| Milestone | Success Rate | Intelligence Accumulated |
|-----------|--------------|--------------------------|
| Month 1 | ~60–65% success rate | No company-specific intelligence. General patterns only. |
| Month 3 | ~72–75% success rate | ~270 action-outcome pairs analyzed. Learns communication preferences, team response patterns, tool usage habits. Customer notices: 'It seems to know how we work.' |
| Month 6 | ~80–85% success rate | ~540 pairs analyzed. Knows which decisions this company struggles to execute, which customers always churn at the same signals, which sprint patterns lead to successful delivery. |
| Month 12 | ~88–92% success rate | ~1,080 pairs analyzed. Living model of how this specific company operates — seasonal patterns, team dynamics, customer behavior, product rhythms. Switching cost: enormous. Losing 12 months of compounded institutional intelligence. |

## SECTION 8: SECURITY ARCHITECTURE

### Five Security Layers

| Layer | Domain | Implementation |
|-------|--------|----------------|
| Layer 1 | Network Security | Cloudflare WAF, DDoS protection, rate limiting, IP allowlisting for known webhook sources (Slack, GitHub, HubSpot IPs only) |
| Layer 2 | Authentication | Clerk OAuth 2.0 + magic link + SSO (Scale). JWT tokens expire in 1 hour. Refresh tokens in httpOnly cookies only — never localStorage (prevents XSS theft). |
| Layer 3 | Authorization | Every API endpoint verifies company_id from JWT matches requested resource. RLS as final backstop — database-level enforcement surviving application code bugs. |
| Layer 4 | Credential Management | AES-256-GCM encryption of all external tool credentials before storage. Keys in AWS KMS, never in code or .env. Auto-rotation every 90 days. Decrypted in memory only for duration of API call. |
| Layer 5 | Agent Permission Scopes | Each agent has a defined permission scope enforced at the action execution layer, not just the prompt level. Agents cannot access tools outside their scope regardless of LLM instruction. |

### Agent Permission Scopes

| Agent | Read Permissions | Write Permissions |
|-------|------------------|-------------------|
| Operations Agent | READ: Linear, Jira, Asana, Trello, Slack, Teams, GitHub | WRITE: Linear/Jira (status only), Slack/Teams (posting) |
| Customer Intelligence | READ: Gmail, HubSpot, Salesforce, Slack, Teams, Intercom, Zendesk | WRITE: HubSpot/Salesforce (notes only), Slack/Teams (posting) |
| Revenue Agent | READ: HubSpot, Salesforce, Gmail, Stripe (read-only) | WRITE: CRM (deal notes only), Slack/Teams (posting) |
| Knowledge Agent | READ: Slack, Teams, Zoom transcripts, Notion, Google Drive, Gmail | WRITE: Notion (new pages), Slack/Teams (posting) |
| Finance Agent | READ: Stripe, QuickBooks, Xero | WRITE: None (read-only by design) |
| Alignment Agent | READ: Linear, Jira, GitHub, Notion, Drive, Slack, Teams | WRITE: Slack/Teams (posting alerts only) |
| Spec Agent | READ: All connected tools | WRITE: Linear/Jira (create issues), Notion (create spec pages), Slack/Teams (posting) |

## SECTION 9: INFRASTRUCTURE & DEPLOYMENT

### Production Deployment Architecture

```
                    ┌─────────────────────┐
                    │     CLOUDFLARE       │
                    │  WAF + CDN + DDoS    │
                    └──────────┬──────────┘
             ┌─────────────────┴──────────────┐
             ▼                                ▼
  ┌──────────────────┐            ┌──────────────────────┐
  │     VERCEL        │            │      RAILWAY          │
  │  Next.js Frontend │            │   FastAPI Backend     │
  │  SSR + Edge CDN   │            │   Auto-scaling        │
  │  Global delivery  │            │   containers          │
  └──────────────────┘            └──────────┬───────────┘
                                             │
                       ┌─────────────────────┼───────────┐
                       ▼                     ▼           ▼
             ┌──────────────────┐  ┌──────────────┐  ┌────────┐
             │    SUPABASE       │  │   UPSTASH     │  │ MODAL  │
             │  PostgreSQL 16    │  │    Redis      │  │  AI    │
             │  + pgvector       │  │  Task queue   │  │ Jobs   │
             │  + Auth           │  │  + Cache      │  │ Heavy  │
             │  + Realtime       │  │               │  │ batch  │
             └──────────────────┘  └──────────────┘  └────────┘
```

### Background Job Architecture

Agent operations are never executed synchronously in a request-response cycle. Every agent run is a background task — webhook endpoints return within 200ms while agents reason and execute asynchronously.

| Job Type | Trigger / Schedule | Purpose |
|----------|-------------------|---------|
| run_agent | Event-driven or scheduled | Core agent execution — triggered by artifact arrival or schedule |
| sync_hubspot | Every 60 minutes | CRM data sync, deals modified in last 60 minutes |
| sync_salesforce | Every 60 minutes | Enterprise CRM sync via SOQL |
| sync_linear | Every 30 minutes | Sprint metrics and issue updates |
| sync_jira | Every 30 minutes | Enterprise PM sync, sprint velocity |
| sync_notion | Every 30 minutes | Document and page updates (no webhooks) |
| sync_github | Every 60 minutes | Repository statistics, commit history |
| sync_google_drive | Every 30 minutes | Document changes via pageToken |
| sync_asana | Every 30 minutes | Task and project updates |
| sync_quickbooks | Daily 3am | Financial reconciliation, P&L reports |
| goal_state_comparator | Every 15 minutes | All goal metrics recalculated and statuses updated |
| flywheel_engine | Nightly 2am | Pattern extraction, agent intelligence updates |
| embedding_drift_check | Weekly Sunday | Cosine distance drift detection, recalibration flag |
| process_zoom_recording | Event-driven | On recording.completed webhook — transcription and embedding |
| generate_daily_briefings | Daily 7am | Finance, operations, revenue, customer briefings to Slack |

**Worker configuration**: Celery workers on Railway, 4 workers per instance, auto-scaling based on queue depth. Failed jobs retry 3 times with exponential backoff (1min, 5min, 25min). Dead-letter queue for jobs failing all retries.

## SECTION 10: PERFORMANCE & COST MODEL

### Compute Cost Per Customer

| Cost Component | Type | Calculation |
|---------------|------|-------------|
| Claude 3.5 Sonnet (primary) | LLM | ~2,000 tokens × 10,000 actions = 20M tokens/mo × $3/1M = $60 |
| Groq Llama 3 (classifications) | LLM | ~5M tokens/mo × $0.05/1M = $0.25 |
| text-embedding-3-small | Embeddings | ~5,000 artifacts × 500 tokens × $0.02/1M = $0.05 |
| Supabase PostgreSQL | Database | ~$5/customer/month allocated |
| Railway backend | Infrastructure | ~$5/customer/month allocated |
| Modal AI batch jobs | Infrastructure | ~$3/customer/month |
| Upstash Redis | Infrastructure | ~$2/customer/month |
| **Total (Growth Plan)** | **COGS** | **~$75/customer/month** |

### Unit Economics by Plan

| Plan | Price | Details & Margin |
|------|-------|-----------------|
| Starter Plan | $299/month | 3 agents, 5 integrations, 1,000 actions/mo, basic goal tracking. Est. COGS: $40. Gross Margin: 86.6% |
| Growth Plan | $799/month | All 7 agents, unlimited integrations, 10,000 actions/mo, full goal-state monitoring, decision trail. Est. COGS: $75. Gross Margin: 90.6% |
| Scale Plan | $1,999/month | Everything in Growth + custom agents, API access, SSO, audit logs, dedicated support. Est. COGS: $180. Gross Margin: 91.0% |

## SECTION 11: DIRECTORY STRUCTURE

```
loopos/
├── apps/
│   ├── web/                       Next.js 14 frontend
│   │   ├── app/                   App Router pages
│   │   │   ├── dashboard/         Main command center — query bar + live feed
│   │   │   ├── agents/            Agent roster, status, control panel
│   │   │   ├── goals/             Goal-state monitor — live vs. target
│   │   │   ├── decisions/         Decision trail — linked to specs and outcomes
│   │   │   ├── integrations/      Tool connection hub — all 16+ connectors
│   │   │   ├── query/             Company query interface — cross-tool Q&A
│   │   │   └── approvals/         Human-in-the-loop inbox for agent actions
│   │   ├── components/            Shared UI components (shadcn/ui based)
│   │   └── lib/                   Utility functions, API client, auth helpers
│   │
│   └── api/                       FastAPI backend
│       ├── main.py                App entry point
│       ├── routers/               API route handlers
│       │   ├── webhooks.py        Incoming tool webhooks (all integrations)
│       │   ├── integrations.py    Connect / disconnect / health tools
│       │   ├── agents.py          Agent control + status + pause/resume
│       │   ├── query.py           Company query endpoint (cross-tool Q&A)
│       │   ├── goals.py           Goal CRUD + real-time monitoring
│       │   ├── artifacts.py       Artifact search and retrieval
│       │   ├── outcomes.py        Outcome recording and reporting
│       │   └── approvals.py       Approval inbox management
│       ├── agents/                All agent implementations
│       │   ├── base.py            BaseAgent class — five-phase pattern
│       │   ├── operations.py      Operations Agent
│       │   ├── customer.py        Customer Intelligence Agent
│       │   ├── revenue.py         Revenue Agent
│       │   ├── knowledge.py       Knowledge Agent
│       │   ├── finance.py         Finance Agent
│       │   ├── alignment.py       Alignment Agent
│       │   ├── spec.py            Spec Agent
│       │   └── dispatcher.py      Routing logic — artifact to agent mapping
│       ├── integrations/          Tool connectors
│       │   ├── slack.py           Slack Events API + Web API
│       │   ├── gmail.py           Gmail Push Notifications + History API
│       │   ├── hubspot.py         HubSpot Webhooks + CRM Search API
│       │   ├── salesforce.py      Salesforce Streaming API + SOQL
│       │   ├── linear.py          Linear Webhooks + GraphQL API
│       │   ├── jira.py            Jira Webhooks + REST API
│       │   ├── github.py          GitHub Webhooks + REST API
│       │   ├── notion.py          Notion API polling + chunking
│       │   ├── stripe.py          Stripe Webhooks + API
│       │   ├── zoom.py            Zoom Webhooks + transcription pipeline
│       │   ├── google_drive.py    Drive Push Notifications + API
│       │   ├── teams.py           MS Graph Change Notifications
│       │   ├── asana.py           Asana Webhooks + REST API
│       │   ├── quickbooks.py      QBO Webhooks + Accounting API
│       │   ├── xero.py            Xero Webhooks + Accounting API
│       │   ├── intercom.py        Intercom Webhooks + REST API
│       │   ├── zendesk.py         Zendesk Webhooks + REST API
│       │   ├── google_calendar.py Google Calendar Push Notifications
│       │   └── normalizer.py      Event normalization → Artifact standard
│       ├── intelligence/          Core reasoning layer
│       │   ├── query_engine.py    Cross-tool reasoning + sourced answers
│       │   ├── goal_comparator.py 15-minute goal-state comparison engine
│       │   └── flywheel.py        Nightly pattern extraction + intelligence
│       ├── artifacts/             Storage layer
│       │   ├── store.py           Artifact CRUD + semantic search (pgvector)
│       │   └── embedder.py        text-embedding-3-small pipeline
│       ├── security/              Security layer
│       │   ├── vault.py           Credential vault (AES-256-GCM + AWS KMS)
│       │   └── permissions.py     Agent permission scope enforcement
│       └── workers/               Background jobs (Celery)
│           ├── celery_app.py      Celery configuration + Upstash Redis
│           ├── scheduled.py       Periodic sync + comparison jobs
│           ├── agent_tasks.py     Agent background runs
│           └── flywheel_tasks.py  Nightly batch + drift detection
│
├── database/
│   ├── migrations/                Schema version history (Alembic)
│   ├── schema.sql                 Complete schema definition
│   └── rls_policies.sql           Row-level security policies (all tables)
│
└── docs/
    ├── architecture.md            This document
    ├── integration_guide.md       Adding new integrations
    ├── agent_guide.md             Adding new agents
    └── api_reference.md           API endpoint reference
```

## SECTION 12: KEY ARCHITECTURAL DECISIONS

| Decision | Rationale |
|----------|-----------|
| Python + FastAPI | AI ecosystem is Python-first. FastAPI is async, auto-documented, Pydantic type-safe. Every major agent framework (CrewAI, LangChain, LangGraph) is Python-native. |
| PostgreSQL + pgvector | One database for relational + vector data. No separate vector DB dependency. SQL joins between structured and semantic data — capability no separate vector DB provides. |
| CrewAI for Multi-Agent Orchestration | Purpose-built for role-based agent teams. Maps directly to LoopOS's architecture. Handles inter-agent communication, sequential and hierarchical execution, shared memory. |
| Claude 3.5 Sonnet as Primary LLM | Superior reasoning for cross-tool analysis. 200K context window handles large artifact sets. Groq Llama 3 for high-frequency low-complexity decisions where speed/cost > depth. |
| Celery + Redis for Background Jobs | Agents run asynchronously. Webhooks return in 200ms. Agents reason in the background. Dead-letter queue for failed jobs. |
| Webhook-First Ingestion | Real-time events preferred over polling. Normalized artifact model makes adding new integrations fast and predictable. All 16+ integrations follow the same three-phase pattern. |
| Flywheel as Nightly Batch Job | Pattern learning on the full day's data is more reliable than real-time updates. Intelligence applied every morning. 90-day rolling window with recent weighting. |
| AWS KMS for Credentials | External tool credentials encrypted before database storage. Never in code, never in logs. Decrypted in memory only at request time. 90-day key rotation. |
| Row-Level Security (RLS) | Multi-tenant isolation enforced at the database level. Company A's data physically inaccessible to Company B regardless of application code bugs. |
| Human-in-the-Loop by Default | High-stakes agent actions require human approval. Approval inbox is a core product feature, not an afterthought. Rejected actions feed to flywheel as negative outcomes. |
| MCP Protocol Adoption | Model Context Protocol adopted for Phase 4 custom integrations. Universal standard backed by Anthropic, OpenAI, Google, Microsoft enables any tool to connect without custom connector code. |
| Embedding Drift Detection | Cosine distance weekly check detects company pivots and priority shifts. Ensures flywheel recalibrates when old patterns become invalid. |

## SECTION 13: ADVANCED ARCHITECTURAL PATTERNS FROM VELLUM-ASSISTANT

### Context Overflow Recovery System

LoopOS incorporates vellum-assistant's proven context overflow recovery pipeline to handle edge cases where agent context exceeds token limits without surfacing errors to users.

**Overflow Recovery Pipeline**:
1. **Preflight Budget Check**: Estimates token usage before provider calls. If estimate > maxInputTokens × (1 - safetyMarginRatio), triggers recovery.
2. **Tiered Reducer**: Iteratively shrinks payload through multiple tiers:
   - **Tier 1**: Forced compaction with minKeepRecentUserTurns=0
   - **Tier 2**: Tool-result truncation (4,000 chars per result)
   - **Tier 3**: Media/file stubbing
   - **Tier 4**: Injection downgrade to minimal mode
3. **Latest Turn Compression**: When all tiers exhausted, auto-compresses the latest turn with no user prompt
4. **Graceful Degradation**: Each tier has escape hatches for interactive vs non-interactive sessions

**Configuration**:
```python
contextWindow:
  overflowRecovery:
    enabled: true
    interactiveLatestTurnCompression: "compress"  # or "drop" to opt out
    nonInteractiveLatestTurnCompression: "compress"  # or "drop" to opt out
    safetyMarginRatio: 0.1  # 10% safety margin
```

### Permission Controls v2

LoopOS implements vellum-assistant's permission controls v2, removing deterministic tool-by-tool approval friction for agent-owned actions while maintaining security for cross-principal identity checks.

**Permission Model**:
- **Deterministic Approval**: Only for conversation-scoped host computer access (host_* / host-target tools)
- **Model-Mediated Consent**: All other agent-owned tool usage relies on model-mediated consent
- **No Temporary Approvals**: Eliminates wildcard scopes, per-tool persistence, or network/side-effect approval cards
- **Cross-Principal Checks**: Unknown actors still fail closed deterministically

**Implementation**:
```python
class PermissionContext:
    actor_role: 'guardian' | 'trusted' | 'restricted'
    actor_principal_id: str
    conversation_scope: bool  # True for host computer access
    model_consent: bool  # Model-mediated consent for other tools
    
    def can_execute_tool(self, tool_name: str) -> bool:
        if tool_name.startswith('host_'):
            return self.conversation_scope and self.actor_role == 'guardian'
        return self.model_consent  # LLM decides based on context
```

### Credential Execution Service (CES) Isolation

LoopOS adopts vellum-assistant's CES architecture for hard process-boundary isolation of credential-bearing operations.

**CES Architecture**:
- **Separate Process**: Credential operations run in isolated container/process
- **RPC Communication**: Assistant communicates via stdio JSON-RPC (local) or Unix socket (managed)
- **Manifest-Driven Commands**: Each command declares auth adapter, egress mode, and allowed argv patterns
- **Grant-Based Access Control**: CES-owned durable state (grants and audit logs) never read/written by assistant
- **Secure Storage**: Credential key files stored on CES security volume, no other container access

**CES API**:
```python
interface CESRPC:
    run_authenticated_command(params: {
        command: string
        args: string[]
        env: Record<string, string>
        auth_adapter: 'env_var' | 'temp_file' | 'credential_process'
        egress_mode: 'proxy_required' | 'no_network'
    }): Promise<CESResult>
    
    make_authenticated_request(params: {
        url: string
        method: string
        headers: Record<string, string>
        body?: string
        credential_id: string
    }): Promise<CESResult>
    
    manage_secure_command_tool(params: {
        tool_id: string
        action: 'install' | 'uninstall' | 'update'
    }): Promise<CESResult>
```

### Simplified Memory System

LoopOS uses vellum-assistant's simplified memory system with two-layer architecture (brief + archive) instead of the complex item/tier/staleness model.

**Memory Architecture**:
```
Write Path:
- Incoming Message → Memory Reducer (LLM-backed, delayed)
- Reducer → time_contexts + open_loops (brief state)
- Reducer → memory_observations + memory_episodes (archive candidates)
- Message → Dual-Write Indexer → memory_chunks (content-hash deduped)

Read Path:
- User Turn → Memory Brief Compiler → <memory_brief> (time contexts + open loops)
- User Turn → Archive Recall Gate (keyword + pattern match)
- Recall Gate → Prefetch (episodes + observations) or Deeper Recall
- Deeper Recall → <supporting_recall> (source-linked bullets)
```

**Memory Tables**:
```sql
-- Brief state (time-relevant)
CREATE TABLE time_contexts (
    id TEXT PRIMARY KEY,
    time_window TEXT NOT NULL,
    content TEXT NOT NULL,
    relevance_score REAL,
    updated_at DATETIME
);

CREATE TABLE open_loops (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    assignee TEXT,
    due_date DATETIME,
    created_at DATETIME
);

-- Archive (historical knowledge)
CREATE TABLE memory_observations (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source_artifact_id TEXT,
    confidence REAL,
    created_at DATETIME
);

CREATE TABLE memory_chunks (
    id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    content TEXT NOT NULL,
    observation_ids TEXT[],
    created_at DATETIME
);

CREATE TABLE memory_episodes (
    id TEXT PRIMARY KEY,
    narrative TEXT NOT NULL,
    time_range_start DATETIME,
    time_range_end DATETIME,
    artifact_ids TEXT[],
    created_at DATETIME
);
```

### Skill-Based Extensibility

LoopOS incorporates vellum-assistant's skill architecture for rapid feature addition without core codebase changes.

**Skill Structure**:
```
skill-name/
├── SKILL.md           # Markdown frontmatter + instructions
├── TOOLS.json         # Tool manifest (optional, for bundled skills)
├── scripts/           # Executable code with inline dependencies
│   ├── script.ts      # TypeScript with pinned imports
│   └── script.py      # Python with pinned imports
├── references/        # Supplementary documentation
└── assets/            # Static resources (icons, images)
```

**Skill Capabilities**:
- **Portability**: Self-contained skills work across different agent systems
- **Inline Dependencies**: Pin versions directly in imports (e.g., `import { Command } from "commander@13.1.0"`)
- **Runtime Injection**: Skills can add tools and prompt sections at runtime
- **Sandboxed Execution**: All skill code runs in sandboxed environment
- **Feature Flag Gating**: Skills can be gated by feature flags for controlled rollout

**Skill Categories**:
- Messaging (Slack, Gmail, Teams)
- Project Management (Linear, Jira, Asana)
- CRM (HubSpot, Salesforce)
- Development (GitHub, GitLab)
- Finance (Stripe, QuickBooks)
- Documentation (Notion, Confluence)
- Custom (MCP servers, REST APIs)

### Workflow Orchestration Engine

LoopOS implements vellum-assistant's workflow orchestration engine using QuickJS-WASM sandbox for secure multi-step automations.

**Workflow Architecture**:
- **QuickJS-WASM Sandbox**: Secure JavaScript execution environment
- **Deterministic Execution**: Scripts must be deterministic (no Date.now(), Math.random())
- **Hooks-Only Capability**: Scripts get hooks only — no filesystem, network, process, or ambient capabilities
- **Single Consent Point**: Per-run capability declaration is the single consent point
- **Agent Cap**: Per-run agent cap (default 500) prevents runaway execution
- **Replay Capability**: Journaled runs can resume after restart by replaying unchanged call prefix

**Workflow Definition**:
```typescript
interface Workflow {
    id: string
    name: string
    description: string
    trigger: WorkflowTrigger
    steps: WorkflowStep[]
    capabilities: CapabilityDeclaration
    error_handling: ErrorHandlingStrategy
}

interface WorkflowStep {
    id: string
    type: 'agent' | 'tool' | 'condition' | 'parallel'
    config: any
    depends_on?: string[]  // Step dependencies
}
```

### Safe Storage Limits

LoopOS incorporates vellum-assistant's safe storage limits to protect workspace volumes from running out of disk.

**Disk Pressure Guard**:
- **Continuous Sampling**: Samples workspace storage usage every 60 seconds
- **Critical Threshold**: At 95% usage, creates in-memory lock with blocked capabilities
- **Blocked Capabilities**: agent-turns, background-work, remote-ingress
- **Cleanup Mode**: Local guardian/owner turns allowed in cleanup mode
- **Override Mechanism**: Requires exact phrase "I understand the risks"

**Runtime Behavior**:
```python
class DiskPressureGuard:
    def check_disk_pressure(self) -> DiskPressureStatus:
        usage = self.get_disk_usage()
        if usage >= 0.95:  # 95% critical threshold
            return self.create_lock(usage)
        return self.clear_lock()
    
    def is_effectively_locked(self) -> bool:
        return self.lock.effectively_locked if self.lock else False
```

### DB Migration Readiness Gating

LoopOS implements vellum-assistant's DB migration readiness gating to prevent queries against partially-migrated schemas.

**Migration Readiness System**:
- **Async Migration**: DB migrations run asynchronously during startup
- **HTTP Server Binds First**: /healthz answers before initializeDb() finishes
- **Readiness Tracking**: setDbMigrating → setDbReady/setDbMigrationFailed
- **Query Gating**: No code may touch DB unless getDbMigrationReadiness().ready is true
- **Exempt Operations**: Health/liveness probes only exempt from readiness checks

**Enforcement Points**:
- HTTP requests gated per-route in runtime/http-server.ts
- IPC methods in ipc/assistant-server.ts
- Message sinks (processMessage, processMessageInBackground)
- Background sweeps started only after migrations settle

### Post-Execution Hooks

LoopOS uses vellum-assistant's post-execution hooks as an observation-and-notification layer only.

**Hook Philosophy**:
- **Observation Layer**: Refresh client-side state, broadcast events, kick off orthogonal background work
- **No Redo Work**: Hooks must not re-do work the executor already performed
- **No Recovery**: Hooks must not attempt recovery when executor failed
- **Independent Logic**: Hook logic independent of result payload, or passed through typed side channel
- **Serialized Resources**: Shared mutable resources serialized per-resource to prevent race conditions

**Hook Examples**:
```python
class ToolSideEffects:
    def after_tool_execution(self, tool_result: ToolResult, context: ToolContext):
        # Refresh client state
        self.emit_event('tool_completed', tool_result)
        
        # Kick off orthogonal work
        if tool_result.tool_name == 'create_ticket':
            self.schedule_icon_generation(tool_result.ticket_id)
        
        # Never retry or recover here - that's executor's job
```

### Shared ROUTES Architecture

LoopOS adopts vellum-assistant's shared ROUTES array pattern for transport-agnostic route definitions.

**Route Architecture**:
- **Single Source of Truth**: Shared ROUTES array serves both HTTP and IPC servers
- **Transport-Agnostic Handlers**: Handlers accept optional params and return plain data
- **No HTTP Types**: Handlers never import HTTP types, return Response objects, or reference Request
- **RouteError Subclasses**: Throw RouteError subclasses for error cases
- **Dual Exposure**: Every route served over both HTTP and IPC by design

**Route Definition**:
```typescript
interface RouteDefinition {
    operationId: string
    endpoint: string
    method: string
    handler: (params: any) => Promise<any>
    policyKey?: string
    summary?: string
    description?: string
    tags?: string[]
    responseBody?: any
}
```

**Adapters**:
- **HTTP Adapter**: Wraps handlers in Response.json(), maps RouteError to HTTP status codes
- **IPC Adapter**: Maps operationId → IPC method name, passes handler through directly

### Telemetry Wire Contract

LoopOS implements vellum-assistant's telemetry wire contract for structured event tracking.

**Wire Contract**:
- **Platform-Generated**: Event types defined by platform-generated wire contract
- **Type Safety**: Pre-flush validation against wire contract
- **Cross-Repo Ordering**: Platform-side defines event types first, then implemented in code
- **Drift Guards**: Guards against contract drift between platform and code

**Telemetry Events**:
```typescript
interface TelemetryEvent {
    event_type: string  // From wire contract
    timestamp: number
    company_id: string
    user_id?: string
    properties: Record<string, any>
}
```

### Generic Examples Policy

LoopOS enforces vellum-assistant's generic examples policy to prevent personal data propagation.

**Policy Rules**:
- **No Personal Data**: Never include real names, emails, phone numbers, account IDs in code/tests/docs
- **Generic Placeholders**: Use Alice, Bob, user1, Example User
- **Reserved Domains**: Use example.com/example.org for emails
- **Reserved Phone Range**: Use 555-0100–555-0199 for phone numbers
- **Generic IDs**: Use user-123, org-abc, conv-xyz
- **Precommit Enforcement**: Hook runs patterns check against staged changes
- **Commit Message Check**: Hook runs patterns against commit message

**Inline Suppression**:
```python
# generic-examples:ignore-next-line — reason: example for demonstration
email = "user@example.com"  # Would normally be flagged
```

### Backwards Compatibility Strategy

LoopOS maintains vellum-assistant's backwards compatibility principles for interface stability.

**Compatibility Principles**:
- **Real Users**: Maintain backwards compatibility for all interfaces, persisted state, and data
- **Never Break**: Never ship changes that silently break existing behavior
- **Migration Strategy**: Include migrations when changing file paths, directory structure, data shapes, namespaces, column schemas, or storage formats

**Migration Types**:
| What Changed | Migration Type | Location |
|--------------|----------------|----------|
| Workspace files (renames, moves, format changes) | Workspace migration | src/workspace/migrations/ |
| Database schema or data (columns, indexes, backfills) | DB migration | src/persistence/migrations/ |

**Migration Requirements**:
- **Idempotent**: Safe to re-run if interrupted
- **Append-Only**: Never reorder or remove existing entries
- **Fresh Prefix**: Each new DB migration gets fresh numeric prefix
- **Test Coverage**: Test migrations with test helpers

### Code Comments Philosophy

LoopOS follows vellum-assistant's code comments philosophy for maintainable documentation.

**Comment Philosophy**:
- **Present Tense**: Comments describe what code IS and DOES right now
- **No History**: Never how we got here, what replaced, what changed in PR
- **No Diff Language**: Avoid "no longer does X", "previously used Y", "was removed in PR Z"
- **PR for History**: History and reasoning belong in PR descriptions and commit messages
- **Generic to Specific**: Bias aggressively toward terseness and good naming
- **Follow Density**: Match commenting density of surrounding code

**Example**:
```python
# BAD (temporal language)
# This function no longer uses the old cache approach

# GOOD (present tense)
# This function uses Redis for caching with 5-minute TTL
```

### Dead Code Removal Policy

LoopOS implements vellum-assistant's proactive dead code removal policy.

**Removal Policy**:
- **Proactive Removal**: Remove unused code during every change
- **Clean Adjacent**: Clean up adjacent dead code when making changes
- **Delete vs Comment**: Delete rather than comment out
- **Check Orphans**: Ask "After my change, is there any code that nothing calls, imports, or references?"
- **Migration Exception**: Database and data migration files must never be deleted

**Exception - Migrations**:
- Migrations run sequentially on existing installs
- Skipping an entry breaks the chain
- When migration responsibility moves, keep file and add comment documenting new location

### Docker Volume Architecture

LoopOS implements vellum-assistant's Docker volume architecture for least-privilege container isolation.

**Volume Layout**:
```
<instance-name>-workspace       →  /workspace           (assistant: rw, gateway: rw, CES: ro)
<instance-name>-gateway-sec     →  /gateway-security    (gateway only)
<instance-name>-ces-sec         →  /ces-security        (CES only)
<instance-name>-socket          →  /run/ces-bootstrap   (assistant + CES)
<instance-name>-gateway-ipc     →  /run/gateway-ipc     (assistant + gateway)
<instance-name>-assistant-ipc   →  /run/assistant-ipc   (assistant + gateway)
<instance-name>-dockerd-data    →  /var/lib/docker      (assistant only — inner dockerd state)
```

**Volume Purposes**:
- **Workspace Volume**: Shared state — config, conversations, apps, skills, database, logs
- **Gateway Security Volume**: Files private to gateway container only
- **CES Security Volume**: Credential encryption keys (keys.enc, store.key) — CES only
- **Socket Volume**: CES bootstrap socket for initial service handshake
- **Gateway IPC Volume**: Unix domain socket for assistant→gateway IPC calls
- **Assistant IPC Volume**: Unix domain socket for gateway→assistant reverse IPC calls
- **Inner Dockerd Data**: Persistent storage for inner dockerd that runs meet-bot containers

### Multi-Local Instance Isolation

LoopOS supports multiple local instances running side-by-side with full isolation.

**Instance Layout**:
```
~/.loopos.lock.json                                       # Global lockfile
~/.local/share/loopos/assistants/
├── company-a/                                            # instanceDir for company-a
│   └── .loopos/                                          # Daemon root
│       ├── loopos.pid                                    # Daemon PID
│       ├── gateway.pid
│       ├── ngrok.pid
│       ├── runtime-port
│       ├── .env
│       ├── protected/                                    # keys.enc, trust.json, credentials/
│       └── workspace/
│           ├── config.json
│           ├── data/
│           │   ├── db/assistant.db
│           │   ├── qdrant/
│           │   └── logs/
│           └── skills/
└── company-b/
    └── .loopos/
        └── ...                                           # Same structure as company-a
```

**Isolation Model**:
Each instance gets its own:
- **VELLUM_WORKSPACE_DIR**: Set to `<instanceDir>/.loopos/workspace`
- **GATEWAY_SECURITY_DIR** / **CREDENTIAL_SECURITY_DIR**: Set to `<instanceDir>/.loopos/protected`
- **Daemon Port**, **Gateway Port**, **Qdrant Port**: Allocated by scanning upward from base port
- **PID File**: `<instanceDir>/.loopos/loopos.pid`
- **SQLite Database, Logs, Memory Indices**: All under `<instanceDir>/.loopos/workspace/data/`

**Port Allocation**:
`allocateLocalResources()` takes each service's base port and scans upward for first port not bound by another local instance. Each environment has disjoint port window so running prod + non-prod instances side-by-side doesn't collide.

### Single-Header JWT Auth Model

LoopOS implements vellum-assistant's single-header JWT authentication model.

**Token Schema (JWT Claims)**:
| Claim | Type | Description |
|-------|------|-------------|
| `iss` | `'loopos-auth'` | Issuer — always `loopos-auth` |
| `aud` | `'loopos-daemon'` or `'loopos-gateway'` | Audience — which service the token targets |
| `sub` | string | Subject — encodes principal type and identity |
| `scope_profile` | string | Named permission bundle |
| `exp` | number | Expiry timestamp (seconds since epoch) |
| `policy_epoch` | number | Policy version — stale tokens are rejected with `refresh_required` |
| `iat` | number | Issued-at timestamp |
| `jti` | string | Unique token ID |

**Subject Patterns**:
| Pattern | Principal Type | Description |
|---------|---------------|-------------|
| `actor:<assistantId>:<actorPrincipalId>` | `actor` | Desktop or CLI client |
| `svc:gateway:<assistantId>` | `svc_gateway` | Gateway service (ingress, webhooks) |
| `svc:internal:<assistantId>:<sessionId>` | `svc_internal` | Internal service connections |
| `svc:daemon:<identifier>` | `svc_daemon` | Daemon service token (local) |

**Scope Profiles**:
| Profile | Scopes | Used by |
|---------|--------|---------|
| `actor_client_v1` | `artifacts.{read,write}`, `integrations.{read,write}`, `agents.{read,execute}`, `goals.{read,write}`, `workflows.{read,execute}`, `memory.{read,write}` | Desktop, CLI clients |
| `gateway_ingress_v1` | `ingress.write`, `internal.write` | Gateway channel inbound + webhook forwarding |
| `gateway_service_v1` | `settings.read`, `settings.write`, `internal.write` | Gateway service-to-daemon calls |
| `internal_v1` | `internal.all` | Internal service connections |

### Environment and Data Layout

LoopOS implements vellum-assistant's environment-aware data layout for multi-environment support.

**Environment Namespaces**:
- **production**: `loopos` path prefix
- **dev**, `staging`, `test**, `local**: `loopos-<env>` path prefix

**Per-Assistant Data Directories**:
Every local assistant's daemon root is `<resources.instanceDir>/.loopos/`

**Allocation Rules**:
| Environment | `instanceDir` path |
|-------------|-------------------|
| `production` | `$XDG_DATA_HOME/loopos/assistants/<name>/` |
| non-production (`loopos-<env>`) | `$XDG_DATA_HOME/loopos-<env>/assistants/<name>/` |

**Lockfile Locations**:
| Environment | Canonical Path | Read Fallback |
|-------------|----------------|---------------|
| `production` | `~/.loopos.lock.json` | `~/.loopos.lockfile.json` (legacy rename) |
| non-production | `$XDG_CONFIG_HOME/loopos-<env>/lockfile.json` | (none — new path) |

**Config Directory (XDG-shared auth state)**:
| Environment | Config Dir |
|-------------|------------|
| `production` | `$XDG_CONFIG_HOME/loopos/` |
| non-production | `$XDG_CONFIG_HOME/loopos-<env>/` |

### Inline Skill Commands

LoopOS supports vellum-assistant's inline skill command syntax for dynamic content resolution.

**Syntax**:
``!`command` ``

**Examples**:
``!`git branch --show-current` ``
!`cat package.json | jq '.version'` ``
```

**Execution Semantics**:
- **Sandboxed**: Commands run only in sandbox with network off, sanitized environment, 10-second timeout
- **Stdout-Only**: Captures stdout only
- **Strict Parsing**: Empty commands, whitespace-only commands, or unmatched backticks are rejected
- **Feature Flag**: `inline-skill-commands` feature flag must be enabled
- **Scope Support**: Only for `bundled`, `managed`, and `workspace` skill sources

**Fenced Code Protection**:
Place documentation examples inside fenced code blocks to prevent execution:
````
```bash
!`echo example`  # This won't execute, it's in a code block
```
````

### User-Gated Actions

LoopOS implements vellum-assistant's user-gated actions pattern for high-stakes operations.

**Interactive Confirmation**:
```bash
if assistant ui confirm \
    --title "Send email" \
    --message "Send draft to jane@example.com — Subject: Q2 Report" \
    --confirm-label "Send" \
    --deny-label "Cancel"; then
    # User confirmed — proceed with the action
    assistant oauth request POST "/v1.0/me/messages/${DRAFT_ID}/send" \
      --provider microsoft-graph
else
    echo "Send cancelled by user."
    exit 0
fi
```

**Structured Input Collection**:
```bash
RESULT=$(assistant ui request \
    --payload '{"message":"Select accounts to archive","fields":[{"name":"accounts","type":"multi-select"}]}' \
    --surface-type form \
    --title "Archive accounts" \
    --json)

STATUS=$(echo "$RESULT" | jq -r '.status')

if [ "$STATUS" = "submitted" ]; then
    ACCOUNTS=$(echo "$RESULT" | jq -r '.submittedData.accounts')
    archive_accounts "$ACCOUNTS"
elif [ "$STATUS" = "cancelled" ]; then
    echo "User cancelled."
else
    echo "Request failed or timed out: $STATUS"
    exit 1
fi
```

**Custom Action Buttons**:
```bash
RESULT=$(assistant ui request \
    --payload '{"message":"The staging deploy found 3 failing tests."}' \
    --title "Deploy decision" \
    --actions '[
        {"id":"deploy_anyway","label":"Deploy Anyway","variant":"danger"},
        {"id":"fix_first","label":"Fix Tests First","variant":"primary"},
        {"id":"skip","label":"Skip This Deploy","variant":"secondary"}
    ]' \
    --json)

ACTION=$(echo "$RESULT" | jq -r '.actionId')

case "$ACTION" in
    deploy_anyway)
        run_deploy --force
        ;;
    fix_first)
        echo "Aborting deploy. Fix the tests and re-run."
        exit 0
        ;;
    skip)
        echo "Deploy skipped."
        exit 0
        ;;
esac
```

### Test Machinery Isolation

LoopOS implements vellum-assistant's test machinery isolation to prevent test infrastructure from reaching production state.

**Isolation Principle**:
Test machinery — the test preload, the preload verifier, and shared test helpers — must not reach into production code.

**Inverted Invariants**:
- **Production**: Assumes workspace exists and is real
- **Tests**: Assume workspace is per-process temp dir safe to destroy

**Concrete Rules**:
- **Test Helpers**: Use only node stdlib, bun:test, and sibling helpers. If needed, declare typed slot under `globalThis.looposAssistant.*`
- **Test Preload**: Strictest — must not import from production code at all. Only stdlib, bun:test, and helpers in `__tests__/`
- **Preload Verifier**: Asserts workspace override took effect (`VELLUM_WORKSPACE_DIR` resolves under `os.tmpdir()`)
- **Destructive Ops**: Must call `assertNotLiveDb(path)` immediately before destructive calls

**Example**:
```python
# BAD - preload reaching into production
from src.memory import MemoryStore  # ❌

# GOOD - using shared typed slot
globalThis.looposAssistant.memoryStore = getTestMemoryStore()  # ✅
```

### Length-Prefixed Binary Framing

LoopOS implements vellum-assistant's length-prefixed binary framing for CLI-daemon communication.

**Framing Protocol**:
- Each frame: 4-byte big-endian length + payload
- Messages use JSON envelope: `{ id, method, params?, headers? }` for requests
- Responses: `{ id, result?, error?, headers? }`

**Response Shapes**:
1. **JSON-only**: Single JSON frame (no content-length or transfer-encoding header)
2. **Binary**: JSON envelope with `headers: { "content-length": "<n>" }` + binary frame
3. **Chunked Streaming**: JSON envelope with `headers: { "transfer-encoding": "chunked" }` + binary frames terminated by zero-length frame

**Auto-Detection**:
Server auto-detects legacy newline-delimited JSON from old CLI clients and handles transparently.

### Channel Onboarding Playbook

LoopOS implements vellum-assistant's channel onboarding playbook for multi-channel support.

**Onboarding Flow**:
1. **Transport Metadata**: Arrives via `conversation_create.transport` (HTTP) or `/channels/inbound`
2. **Playbook Resolution**: `OnboardingPlaybookManager` resolves `<channel>_onboarding.md`
3. **Playbook Check**: Checks `onboarding/playbooks/registry.json`
4. **Fast-Path Onboarding**: Applies per-channel first-time fast-path onboarding
5. **Orchestration**: `OnboardingOrchestrator` derives guidance from playbook + transport context
6. **Context Injection**: Assembly injects `<channel_onboarding_playbook>` and `<onboarding_mode>` before provider calls
7. **Context Stripping**: Strips both from persisted conversation history

**Guardian Actor Context**:
- **Centralized Resolution**: Guardian/non-guardian/unverified classification centralized in `runtime/trust-context-resolver.ts`
- **Shared Resolver**: Used by `/channels/inbound` (Telegram/WhatsApp) and inbound Twilio voice setup
- **Trust Context**: Runtime runs pass as `trustContext`, conversation includes actor context in `<turn_context>`
- **Voice Mirroring**: Voice calls mirror same prompt contract with guardian context

### Control-Flow Braces

LoopOS enforces vellum-assistant's control-flow braces policy for code safety.

**Policy**:
Wrap every `if` / `else` / `for` / `while` / `do…while` body in braces, even single-statement one-liners.

**Rationale**:
- Makes control flow easy to scan
- Block boundary is explicit
- Prevents common footgun where second line added under braceless condition runs unconditionally

**Example**:
```python
# BAD
if condition:
    do_something()
    do_another_thing()  # This runs unconditionally!

# GOOD
if condition:
    do_something()
    do_another_thing()  # Clearly inside the block
```

### Daemon Startup Philosophy

LoopOS implements vellum-assistant's daemon startup philosophy for robust service management.

**Startup Philosophy**:
The daemon must **never** block startup due to **subsystem** failures (DB, Qdrant, plugins, feature flags, etc.). If an individual subsystem fails, log the error and continue in degraded mode.

**Exception - Duplicate Daemon Detection**:
If the daemon cannot establish **any** client-facing transport because another daemon already holds both the IPC socket and HTTP port, it must exit immediately.

**Rationale**:
A daemon with no transport is unmanageable (invisible to health checks, unreachable by stop commands) yet still runs background jobs against the shared database, causing duplicate side effects.

### Single Source of Truth

LoopOS follows vellum-assistant's single source of truth principle to prevent code duplication.

**Principle**:
Don't copy-paste logic. Duplicated logic drifts — a bug gets fixed in one copy and left in others, and copies diverge silently over time.

**Extraction Rule**:
Extract on the **second** occurrence, not the fifth. Two copies is the signal, not a milestone to pass.

**Behavior Sharing**:
Share **behavior**, not just shapes. Reusing a type while re-implementing the logic around it still drifts.

**Layer Placement**:
Put extracted code at the right layer:
- Used by one area → inside it
- Used by two or more → a shared module

**Complete Migration**:
After extraction, delete the originals in the same change.

## SECTION 14: VELLUM-ASSISTANT INTEGRATION SUMMARY

### Key Architectural Patterns Adopted

LoopOS incorporates the most robust and production-tested patterns from vellum-assistant, creating a battle-hardened foundation for SMB business intelligence:

1. **Context Overflow Recovery**: Graceful handling of token limit exceeded scenarios
2. **Permission Controls v2**: Model-mediated consent reducing approval friction
3. **Credential Execution Service**: Hard process-boundary isolation for security
4. **Simplified Memory System**: Two-layer architecture (brief + archive) for efficiency
5. **Skill-Based Extensibility**: Rapid feature addition without core changes
6. **Workflow Orchestration**: QuickJS-WASM sandbox for secure automations
7. **Safe Storage Limits**: Protection against disk exhaustion
8. **DB Migration Readiness**: Prevents queries against partially-migrated schemas
9. **Post-Execution Hooks**: Observation-and-notification layer only
10. **Shared ROUTES Architecture**: Transport-agnostic route definitions
11. **Telemetry Wire Contract**: Structured event tracking
12. **Generic Examples Policy**: Personal data protection
13. **Backwards Compatibility**: Interface stability guarantees
14. **Code Comments Philosophy**: Maintainable documentation
15. **Dead Code Removal**: Proactive code hygiene
16. **Docker Volume Architecture**: Least-privilege container isolation
17. **Multi-Local Instance Isolation**: Side-by-side instance support
18. **Single-Header JWT Auth**: Unified authentication model
19. **Environment-Aware Data Layout**: Multi-environment support
20. **Inline Skill Commands**: Dynamic content resolution
21. **User-Gated Actions**: High-stakes operation protection
22. **Test Machinery Isolation**: Test infrastructure safety
23. **Length-Prefixed Binary Framing**: CLI-daemon communication
24. **Channel Onboarding Playbook**: Multi-channel support
25. **Control-Flow Braces**: Code safety enforcement
26. **Daemon Startup Philosophy**: Robust service management
27. **Single Source of Truth**: Code duplication prevention

### Competitive Advantages from Vellum Patterns

**Production Hardening**:
- Proven patterns from battle-tested personal AI system
- Graceful degradation under failure conditions
- Comprehensive security isolation at process and data levels

**Developer Experience**:
- Skill-based architecture for rapid feature development
- Transport-agnostic route definitions reduce duplication
- Deterministic workflow execution with replay capability

**Operational Excellence**:
- Multi-environment support with data isolation
- Safe storage limits prevent resource exhaustion
- Comprehensive telemetry and observability

**Security Posture**:
- Credential isolation via CES
- Permission controls v2 reduce friction while maintaining security
- Row-level security for multi-tenant isolation

**Extensibility**:
- Skill marketplace for community contributions
- MCP protocol for universal tool integration
- Workflow engine for custom automations

### Integration Strategy

**Phase 1**: Core patterns (CES, Memory System, Permission Controls)
**Phase 2**: Extensibility (Skills, Workflows, Routes)
**Phase 3**: Production hardening (Overflow Recovery, Storage Limits, Migration Gating)
**Phase 4**: Advanced features (Inline Commands, User-Gated Actions, Telemetry)

This comprehensive integration of vellum-assistant's proven patterns gives LoopOS a significant architectural advantage, combining the battle-tested reliability of personal AI systems with the business intelligence capabilities required for SMB operations.

## Implementation Phases

### Phase 1: Core Infrastructure (Months 1-3)

**Objective**: Build foundational platform components

**Deliverables**:
- [x] **Monorepo Setup**: Next.js + FastAPI workspace structure
- [x] **Database Schema**: PostgreSQL + pgvector initialization with RLS
- [x] **Basic API Layer**: FastAPI with authentication (Clerk)
- [x] **OAuth Framework**: Provider registry and connect orchestrator
- [x] **Credential Service**: AWS KMS integration with AES-256-GCM encryption
- [x] **Artifact Store**: Normalized artifact model with embedding pipeline
- [x] **Agent Runtime**: Base agent class with five-phase pattern

**Success Criteria**:
- [x] Can create organizations and users with proper RLS
- [x] Can connect to at least 2 OAuth providers (Slack, Gmail)
- [x] Can ingest and index basic artifacts with embeddings
- [x] Can perform simple queries over ingested data
- [x] Basic agent can execute with permission controls

### Phase 2: Integration Layer (Months 3-5)

**Objective**: Connect to major SMB SaaS tools

**Deliverables**:
- [x] **Slack Integration**: Full Events API + Web API with webhook processing (rate limited, exponential backoff)
- [x] **Gmail Integration**: Push Notifications + History API with privacy controls (PII redaction, opt-out)
- [x] **GitHub Integration**: Webhooks + REST API for commit/PR tracking
- [x] **Linear Integration**: Webhooks + GraphQL API for project management
- [x] **HubSpot Integration**: Webhooks + CRM Search API for pipeline tracking
- [x] **Notion Integration**: API polling with document chunking strategy (1000/200 token chunks)
- [x] **Unified Query Interface**: Cross-platform semantic search with pgvector + LLM answer synthesis

**Success Criteria**:
- [x] All 6 integrations fully functional with proper normalization
- [x] Real-time webhook processing with agent dispatch (BackgroundTasks)
- [x] Cross-platform query returns relevant, sourced results via LLM synthesis
- [x] Artifact relationships established (commit↔PR, email↔thread, Slack↔thread, ticket↔cycle)
- [x] Background sync jobs operational (Celery beat, per-company scheduling)

### Phase 3: Specialized Agents (Months 5-7)

**Objective**: Implement domain-specific AI agents

**Deliverables**:
- [ ] **Operations Agent**: Task coordination and workflow automation
- [ ] **Customer Intelligence Agent**: Customer behavior analysis and health scoring
- [ ] **Revenue Agent**: Sales pipeline monitoring and revenue tracking
- [ ] **Knowledge Agent**: Decision extraction and knowledge management
- [ ] **Finance Agent**: Financial metrics and anomaly detection
- [ ] **Alignment Agent**: Engineering-business alignment monitoring
- [ ] **Spec Agent**: Decision-to-specification generation

**Success Criteria**:
- [ ] All 7 agents operational within their permission scopes
- [ ] Agents can access relevant data and tools properly
- [ ] Agents produce actionable outputs with reasoning traces
- [ ] Agent activities logged and auditable
- [ ] Human-in-the-loop approval system functional

### Phase 4: Goal Monitoring (Months 7-9)

**Objective**: Implement real-time goal monitoring and deviation detection

**Deliverables**:
- [ ] **Goal Definition UI**: Interface for creating and managing goals
- [ ] **Monitoring Engine**: 15-minute goal-state comparison engine
- [ ] **Deviation Detection**: Statistical analysis for drift identification
- [ ] **Alerting System**: Multi-channel alert delivery via Slack/Teams
- [ ] **Trend Analysis**: Historical performance tracking
- [ ] **Dashboard**: Real-time goal status and performance visualization

**Success Criteria**:
- [ ] Can define and monitor complex goals with metric calculators
- [ ] Detects deviations with low false-positive rate
- [ ] Alerts delivered promptly to correct channels
- [ ] Trends accurately reflect historical performance
- [ ] Supabase Realtime updates working correctly

### Phase 5: Workflow Engine (Months 9-11)

**Objective**: Enable complex multi-step automations

**Deliverables**:
- [ ] **Background Job System**: Celery + Redis with proper error handling
- [ ] **Workflow Authoring**: LangGraph-based workflow definitions
- [ ] **Parallel Execution**: Fan-out to parallel ephemeral agents
- [ ] **Workflow Library**: Pre-built workflow templates
- [ ] **Workflow UI**: Visual workflow builder and editor

**Success Criteria**:
- [ ] Can execute complex multi-step workflows reliably
- [ ] Parallel execution works correctly with proper coordination
- [ ] Workflows are secure and isolated
- [ ] Users can create custom workflows
- [ ] Dead-letter queue and retry mechanisms operational

### Phase 6: Self-Improving Loop (Months 11-13)

**Objective**: Implement learning from outcomes

**Deliverables**:
- [ ] **Outcome Tracking**: Capture and track action outcomes with goal deltas
- [ ] **Learning Engine**: Pattern extraction with LLM analysis
- [ ] **Recommendation Improvement**: Update agent behavior based on learning
- [ ] **Feedback Loop**: User feedback incorporation
- [ ] **Model Versioning**: Track and rollback model changes
- [ ] **Embedding Drift Detection**: Weekly cosine distance checks

**Success Criteria**:
- [ ] System learns from outcomes and improves over time
- [ ] Recommendations get better as flywheel accumulates data
- [ ] Users can provide feedback on recommendations
- [ ] Model changes are tracked and reversible
- [ ] Drift detection triggers recalibration appropriately

### Phase 7: Production Readiness (Months 13-15)

**Objective**: Prepare for production deployment

**Deliverables**:
- [ ] **Security Hardening**: Comprehensive security audit and fixes
- [ ] **Performance Optimization**: Database queries, API response times
- [ ] **Monitoring & Observability**: LangSmith, OpenTelemetry, Grafana, Sentry
- [ ] **Scaling Architecture**: Horizontal scaling capabilities
- [ ] **Disaster Recovery**: Backup and restore procedures
- [ ] **Documentation**: Comprehensive technical and user documentation

**Success Criteria**:
- [ ] Security audit passed with no critical vulnerabilities
- [ ] Performance meets SLA requirements
- [ ] Monitoring provides complete observability
- [ ] System can scale to handle customer growth
- [ ] Disaster recovery tested and verified

## Pricing & Packaging

### Starter Plan ($299/month)

**Target**: 1-10 person companies

**Includes**:
- 3 specialized agents (Operations, Knowledge, Alignment)
- 5 integrations (Slack, Gmail, GitHub, Linear, Notion)
- 1,000 actions/month
- Full goal tracking (10 goals)
- Basic reporting
- Email support
- 7-day data retention

**Limits**:
- 10 users
- 10,000 artifacts
- 1 GB storage
- Community support

### Growth Plan ($799/month)

**Target**: 10-50 person companies

**Includes**:
- All 7 specialized agents
- Unlimited integrations
- 10,000 actions/month
- Full goal monitoring (unlimited goals)
- Decision trail
- Advanced reporting
- Priority support
- 30-day data retention
- API access (basic)

**Limits**:
- 50 users
- 100,000 artifacts
- 10 GB storage
- Slack support

### Scale Plan ($1,999/month)

**Target**: 50-100 person companies

**Includes**:
- Everything in Growth
- Custom agents
- Full API access
- SSO
- Audit logs
- Custom integrations
- Dedicated support
- 90-day data retention
- SLA (99.5% uptime)
- Custom training

**Limits**:
- 100 users
- Unlimited artifacts
- 100 GB storage
- Phone support

## Go-to-Market Strategy

### Target Customer Segments

1. **Founder-led B2B SaaS Startups**
   - Pain: Fragmented tools, lack of alignment
   - Solution: Unified intelligence layer
   - Acquisition: Founder communities, startup accelerators

2. **Digital Agencies**
   - Pain: Client project coordination
   - Solution: Project intelligence and automation
   - Acquisition: Agency associations, conferences

3. **E-commerce Brands**
   - Pain: Customer data fragmentation
   - Solution: Customer intelligence and revenue tracking
   - Acquisition: E-commerce platforms, Shopify apps

4. **Professional Services Firms**
   - Pain: Knowledge management and billing
   - Solution: Knowledge extraction and finance automation
   - Acquisition: Professional associations, consulting networks

### Marketing Channels

**Content Marketing**:
- Blog posts on operational intelligence
- Case studies from beta customers
- White papers on closed-loop operations
- YouTube tutorials and demos

**Community Building**:
- Discord community for users
- GitHub repository for integrations
- Slack community for operators
- Regular webinars and workshops

**Partnerships**:
- Integration with existing SaaS tools
- Referral partnerships with consultants
- Co-marketing with complementary tools
- Marketplace listings

### Sales Motion

**Self-Serve (Starter/Growth)**:
- Free trial with limited features
- Onboarding flow with guided setup
- In-app upgrade prompts
- Email nurture sequences

**Sales-Assisted (Scale)**:
- Demo requests from website
- Discovery calls to understand needs
- Custom proposal and pricing
- Implementation support

## Competitive Analysis

### Direct Competitors

**None identified** in the SMB segment for this specific category

### Indirect Competitors

**Point Solutions**:
- Slack plugins (limited scope)
- Notion AI (document-focused)
- GitHub Copilot (code-focused)
- HubSpot AI (CRM-focused)

**Enterprise Solutions**:
- Palantir Foundry ($1M+ entry)
- SAP BW (requires consultants)
- Microsoft Power Platform (complex setup)

### Competitive Advantages

1. **Unified Intelligence**: Cross-tool reasoning vs. point solutions
2. **Self-Improving**: Gets better over time vs. static systems
3. **SMB-Focused**: Pricing and complexity vs. enterprise solutions
4. **Quick Implementation**: Self-serve onboarding vs. consulting required
5. **Closed Loop**: Connects decisions to outcomes vs. open-loop systems

## Risk Analysis

### Technical Risks

**Integration Complexity**:
- Risk: API changes from connected platforms
- Mitigation: Version-tolerant integration patterns, extensive testing

**Scale Performance**:
- Risk: Performance degradation at scale
- Mitigation: Horizontal scaling architecture, performance monitoring

**Data Privacy**:
- Risk: Security breaches or data leaks
- Mitigation: Encryption at rest and in transit, security audits

### Business Risks

**Market Adoption**:
- Risk: Slow market adoption of new category
- Mitigation: Strong content marketing, case studies, free trial

**Competitive Entry**:
- Risk: Large players entering the market
- Mitigation: Fast iteration, strong moat (data flywheel)

**Customer Churn**:
- Risk: High churn if value not realized
- Mitigation: Strong onboarding, success metrics, customer success

### Mitigation Strategies

**Technical**:
- Comprehensive testing strategy
- Performance monitoring and alerting
- Security best practices and audits
- Redundancy and backup systems

**Business**:
- Customer advisory board
- Strong customer success function
- Continuous value demonstration
- Flexible pricing and contracts

## Success Metrics

### Product Metrics

**Adoption**:
- Weekly active users
- Feature adoption rate
- Integration connection rate
- Agent execution frequency

**Engagement**:
- Queries per user per week
- Goal monitoring coverage
- Workflow automation rate
- Session duration

**Retention**:
- Monthly churn rate
- Feature usage depth
- Expansion revenue rate
- NPS score

### Business Metrics

**Growth**:
- Monthly new customers
- MRR growth rate
- Viral coefficient
- Conversion rate from trial

**Financial**:
- MRR
- ARR
- Gross margin
- CAC payback period
- LTV/CAC ratio

### Technical Metrics

**Performance**:
- API response time (p95)
- Agent execution success rate
- System uptime
- Error rate

**Quality**:
- Bug fix time
- Feature delivery time
- Test coverage
- Code review completion rate

## Timeline Summary

**Months 1-3**: Core Infrastructure
**Months 3-5**: Integration Layer
**Months 5-7**: Specialized Agents
**Months 7-9**: Goal Monitoring
**Months 9-11**: Workflow Engine
**Months 11-13**: Self-Improving Loop
**Months 13-15**: Production Readiness

**Total Timeline**: 15 months to production launch

## Conclusion

LoopOS represents a unique opportunity to define and own the AI Operating System category for SMBs. The five-layer architecture—Integration Layer, Artifact Store, Intelligence Layer, Agent Layer, and Flywheel Engine—creates a comprehensive system that transforms how small companies operate.

The key to success is execution on the integration layer (connecting the tools SMBs already use) and delivering immediate value through the query interface and goal monitoring, while building toward the long-term vision of a self-improving closed-loop system.

The data flywheel effect creates a strong defensive moat—every week of usage makes the product more valuable and harder to replace. This switching cost is not contractual but cognitive, providing sustainable competitive advantage.

With the right execution on this plan, LoopOS can become the connective intelligence layer that powers the next generation of SMB operations.