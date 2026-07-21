-- Phase 4: Universal Connectivity Layer
-- MCP Servers table
CREATE TABLE IF NOT EXISTS mcp_servers (
    id VARCHAR PRIMARY KEY,
    company_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    transport_type VARCHAR NOT NULL DEFAULT 'sse',
    url VARCHAR,
    command VARCHAR,
    args JSON DEFAULT '[]',
    auth_token VARCHAR,
    enabled_tools JSON DEFAULT '[]',
    discovered_tools JSON DEFAULT '[]',
    status VARCHAR DEFAULT 'disconnected',
    polling_interval_minutes INTEGER DEFAULT 60,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    settings JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- REST Connectors table
CREATE TABLE IF NOT EXISTS rest_connectors (
    id VARCHAR PRIMARY KEY,
    company_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    url VARCHAR NOT NULL,
    method VARCHAR DEFAULT 'GET',
    headers JSON DEFAULT '{}',
    auth_type VARCHAR DEFAULT 'none',
    auth_config JSON DEFAULT '{}',
    field_mappings JSON NOT NULL,
    pagination JSON DEFAULT '{}',
    polling_interval_minutes INTEGER DEFAULT 60,
    status VARCHAR DEFAULT 'paused',
    last_sync_at TIMESTAMP WITH TIME ZONE,
    settings JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Zapier/Make webhook configs table
CREATE TABLE IF NOT EXISTS webhook_configs (
    id VARCHAR PRIMARY KEY,
    company_id VARCHAR NOT NULL,
    source_tool VARCHAR NOT NULL,
    webhook_secret VARCHAR NOT NULL,
    webhook_url_path VARCHAR NOT NULL UNIQUE,
    artifact_type VARCHAR DEFAULT 'message',
    enabled BOOLEAN DEFAULT TRUE,
    last_event_at TIMESTAMP WITH TIME ZONE,
    settings JSON DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mcp_servers_company_id ON mcp_servers(company_id);
CREATE INDEX IF NOT EXISTS idx_rest_connectors_company_id ON rest_connectors(company_id);
CREATE INDEX IF NOT EXISTS idx_webhook_configs_company_id ON webhook_configs(company_id);
CREATE INDEX IF NOT EXISTS idx_webhook_configs_url_path ON webhook_configs(webhook_url_path);

-- RLS policies for mcp_servers
ALTER TABLE mcp_servers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view company mcp servers" ON mcp_servers
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "Admins can manage mcp servers" ON mcp_servers
    FOR ALL
    USING (
        company_id IN (
            SELECT company_id FROM users
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
            AND role = 'admin'
        )
    );

-- RLS policies for rest_connectors
ALTER TABLE rest_connectors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view company rest connectors" ON rest_connectors
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "Admins can manage rest connectors" ON rest_connectors
    FOR ALL
    USING (
        company_id IN (
            SELECT company_id FROM users
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
            AND role = 'admin'
        )
    );

-- RLS policies for webhook_configs
ALTER TABLE webhook_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view company webhook configs" ON webhook_configs
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "Admins can manage webhook configs" ON webhook_configs
    FOR ALL
    USING (
        company_id IN (
            SELECT company_id FROM users
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
            AND role = 'admin'
        )
    );
