-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_artifacts_company_id ON artifacts(company_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_source_tool ON artifacts(source_tool);
CREATE INDEX IF NOT EXISTS idx_artifacts_artifact_type ON artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_external_id ON artifacts(external_id);

-- Create vector similarity index (IVFFlat for approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_artifacts_embedding_ivfflat 
ON artifacts USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Row-Level Security Policies

-- Enable RLS on all tables
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE specs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_intelligence ENABLE ROW LEVEL SECURITY;

-- Companies RLS policies
CREATE POLICY "Users can view own company" ON companies
    FOR SELECT
    USING (
        id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "Admins can update company" ON companies
    FOR UPDATE
    USING (
        id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
            AND role = 'admin'
        )
    );

-- Users RLS policies
CREATE POLICY "Users can view users in same company" ON users
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "Admins can insert users" ON users
    FOR INSERT
    WITH CHECK (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
            AND role = 'admin'
        )
    );

CREATE POLICY "Admins can update users" ON users
    FOR UPDATE
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
            AND role = 'admin'
        )
    );

-- Integrations RLS policies
CREATE POLICY "Users can view company integrations" ON integrations
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "Admins can manage integrations" ON integrations
    FOR ALL
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
            AND role = 'admin'
        )
    );

-- Artifacts RLS policies
CREATE POLICY "Users can view company artifacts" ON artifacts
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "System can insert artifacts" ON artifacts
    FOR INSERT
    WITH CHECK (true);  -- System user bypasses RLS for ingestion

-- Goals RLS policies
CREATE POLICY "Users can view company goals" ON goals
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "Admins can manage goals" ON goals
    FOR ALL
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
            AND role = 'admin'
        )
    );

-- Decisions RLS policies
CREATE POLICY "Users can view company decisions" ON decisions
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

-- Agent Actions RLS policies
CREATE POLICY "Users can view company agent actions" ON agent_actions
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "System can insert agent actions" ON agent_actions
    FOR INSERT
    WITH CHECK (true);  -- System user bypasses RLS for agent execution

-- Outcomes RLS policies
CREATE POLICY "Users can view company outcomes" ON outcomes
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

-- Specs RLS policies
CREATE POLICY "Users can view company specs" ON specs
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

-- Agent Intelligence RLS policies
CREATE POLICY "Users can view company agent intelligence" ON agent_intelligence
    FOR SELECT
    USING (
        company_id IN (
            SELECT company_id FROM users 
            WHERE clerk_user_id = current_setting('app.current_user_id', true)
        )
    );

CREATE POLICY "System can update agent intelligence" ON agent_intelligence
    FOR UPDATE
    WITH CHECK (true);  -- System user bypasses RLS for flywheel updates

-- Function to set current user context
CREATE OR REPLACE FUNCTION set_current_user_id(user_id TEXT)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_user_id', user_id, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION set_current_user_id(TEXT) TO public;