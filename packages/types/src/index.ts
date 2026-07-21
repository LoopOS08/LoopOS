// Shared TypeScript types for LoopOS

// Core entity types
export interface Company {
  id: string;
  name: string;
  created_at: Date;
  updated_at: Date;
  settings: Record<string, any>;
}

export interface User {
  id: string;
  company_id: string;
  email: string;
  full_name: string;
  clerk_user_id: string;
  role: 'admin' | 'member' | 'viewer';
  created_at: Date;
  updated_at: Date;
}

// Integration types
export interface Integration {
  id: string;
  company_id: string;
  source_tool: SourceTool;
  status: 'connected' | 'disconnected' | 'error';
  credentials_encrypted: string;
  last_sync_at: Date | null;
  settings: Record<string, any>;
  created_at: Date;
  updated_at: Date;
}

export type SourceTool = 
  | 'slack' 
  | 'gmail' 
  | 'hubspot' 
  | 'linear' 
  | 'notion' 
  | 'github' 
  | 'stripe' 
  | 'zoom'
  | 'google_drive'
  | 'jira'
  | 'salesforce'
  | 'teams'
  | 'asana'
  | 'quickbooks'
  | 'intercom'
  | 'mcp'
  | 'zapier'
  | 'make'
  | 'rest_api';

// Artifact types
export interface Artifact {
  id: string;
  company_id: string;
  source_tool: SourceTool;
  artifact_type: ArtifactType;
  external_id: string;
  content: string;
  author: string;
  author_email: string;
  source_created_at: Date;
  metadata: Record<string, any>;
  embedding?: number[];
  created_at: Date;
  updated_at: Date;
}

export type ArtifactType = 
  | 'message' 
  | 'email' 
  | 'ticket' 
  | 'deal' 
  | 'document' 
  | 'commit' 
  | 'call' 
  | 'transaction' 
  | 'meeting' 
  | 'review' 
  | 'comment' 
  | 'build';

// Goal types
export interface Goal {
  id: string;
  company_id: string;
  metric_name: string;
  target_value: number;
  operator: 'less_than' | 'greater_than' | 'equal_to';
  current_value: number;
  status: 'on_track' | 'at_risk' | 'off_track';
  created_at: Date;
  updated_at: Date;
}

// Decision types
export interface Decision {
  id: string;
  company_id: string;
  artifact_id: string;
  content: string;
  decision_maker: string;
  decision_date: Date;
  outcome?: string;
  created_at: Date;
  updated_at: Date;
}

// Agent action types
export interface AgentAction {
  id: string;
  company_id: string;
  agent_name: string;
  action_type: string;
  context: Record<string, any>;
  reasoning: string;
  output: Record<string, any>;
  artifact_ids: string[];
  goal_id?: string;
  requires_human_approval: boolean;
  approval_status?: 'pending' | 'approved' | 'rejected';
  created_at: Date;
  updated_at: Date;
}

// Outcome types
export interface Outcome {
  id: string;
  company_id: string;
  agent_action_id: string;
  goal_metric_before: number;
  goal_metric_after: number;
  delta: number;
  success: boolean;
  human_feedback?: string;
  created_at: Date;
  updated_at: Date;
}

// Spec types
export interface Spec {
  id: string;
  company_id: string;
  decision_id: string;
  title: string;
  context: string;
  acceptance_criteria: string[];
  dependencies: string[];
  estimated_effort: number;
  suggested_assignee: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  external_ticket_id?: string;
  created_at: Date;
  updated_at: Date;
}

// Agent intelligence types
export interface AgentIntelligence {
  id: string;
  company_id: string;
  agent_name: string;
  successful_patterns: Record<string, any>;
  failed_patterns: Record<string, any>;
  success_rate: number;
  sample_size: number;
  created_at: Date;
  updated_at: Date;
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// OAuth types
export interface OAuthProvider {
  name: string;
  display_name: string;
  auth_url: string;
  token_url: string;
  scopes: string[];
  client_id: string;
  redirect_uri: string;
}

export interface OAuthConnection {
  provider: string;
  access_token: string;
  refresh_token?: string;
  expires_at?: Date;
  scopes: string[];
}

// Search types
export interface SearchResult {
  artifact: Artifact;
  similarity: number;
  highlights: string[];
}

export interface SearchQuery {
  query: string;
  company_id: string;
  source_tool?: SourceTool;
  artifact_type?: ArtifactType;
  limit?: number;
  threshold?: number;
}

// Agent types
export interface AgentConfig {
  name: string;
  description: string;
  permissions: string[];
  tools: string[];
  max_context_tokens: number;
  temperature: number;
}

export interface AgentExecution {
  agent_name: string;
  context: Record<string, any>;
  reasoning: string;
  action: Record<string, any>;
  confidence: number;
  requires_approval: boolean;
}