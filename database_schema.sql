-- ============================================================================
-- Spendee Clone Telegram Bot - Complete Database Schema
-- Database: PostgreSQL (Supabase)
-- Version: 1.0
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- for pgvector (embeddings)

-- ============================================================================
-- 1. USERS TABLE
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'en',
    default_currency VARCHAR(3) DEFAULT 'USD',
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);

-- ============================================================================
-- 2. WALLETS TABLE
-- ============================================================================

CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    currency VARCHAR(3) DEFAULT 'USD',
    initial_balance DECIMAL(15, 2) DEFAULT 0,
    current_balance DECIMAL(15, 2) DEFAULT 0,
    icon VARCHAR(50),  -- emoji or icon identifier
    color VARCHAR(7),  -- hex color (#RRGGBB)
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wallets_owner ON wallets(owner_id);

-- ============================================================================
-- 3. WALLET MEMBERS (for shared wallets)
-- ============================================================================

CREATE TABLE wallet_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES wallets(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'editor', 'viewer')),
    invited_at TIMESTAMPTZ DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    UNIQUE(wallet_id, user_id)
);

CREATE INDEX idx_wallet_members_wallet ON wallet_members(wallet_id);
CREATE INDEX idx_wallet_members_user ON wallet_members(user_id);

-- ============================================================================
-- 4. CATEGORIES TABLE
-- ============================================================================

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,  -- NULL for system categories
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    icon VARCHAR(50),  -- emoji
    color VARCHAR(7),  -- hex color
    parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,  -- for subcategories
    is_system BOOLEAN DEFAULT FALSE,  -- system vs user-created
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_categories_user ON categories(user_id);
CREATE INDEX idx_categories_type ON categories(type);
CREATE INDEX idx_categories_parent ON categories(parent_id);

-- ============================================================================
-- 5. LABELS TABLE (separate from categories!)
-- ============================================================================

CREATE TABLE labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    color VARCHAR(7),  -- hex color
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE INDEX idx_labels_user ON labels(user_id);

-- ============================================================================
-- 6. RECURRING RULES TABLE
-- ============================================================================

CREATE TABLE recurring_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    wallet_id UUID REFERENCES wallets(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    
    -- Template
    type VARCHAR(20) NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    note TEXT,
    
    -- Recurrence pattern
    frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
    interval INTEGER DEFAULT 1,  -- every N days/weeks/months
    start_date DATE NOT NULL,
    end_date DATE,
    
    -- Next execution
    next_execution_date DATE NOT NULL,
    last_execution_date DATE,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recurring_user ON recurring_rules(user_id);
CREATE INDEX idx_recurring_next_exec ON recurring_rules(next_execution_date) WHERE is_active = TRUE;

-- ============================================================================
-- 7. TRANSACTIONS TABLE
-- ============================================================================

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES wallets(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    
    -- Transaction details
    type VARCHAR(20) NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    date DATE NOT NULL,
    time TIME,
    note TEXT,
    
    -- Transfer-specific
    to_wallet_id UUID REFERENCES wallets(id) ON DELETE SET NULL,
    
    -- Integration fields
    source_type VARCHAR(50),  -- 'manual', 'trustee', 'plaid_chase', etc.
    source_id VARCHAR(255),  -- unique ID from source
    source_email VARCHAR(255),  -- for Payoneer, etc.
    raw_data JSONB,  -- original transaction data
    
    -- Attachments
    attachment_urls TEXT[],  -- array of receipt/photo URLs
    
    -- Geolocation
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_name VARCHAR(255),
    
    -- Merchant info
    merchant_name VARCHAR(255),
    merchant_category VARCHAR(100),
    
    -- Vector embedding for similarity search
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    
    -- Metadata
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_rule_id UUID REFERENCES recurring_rules(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_transactions_user_date ON transactions(user_id, date DESC);
CREATE INDEX idx_transactions_wallet ON transactions(wallet_id);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_source ON transactions(source_type, source_id);
CREATE INDEX idx_transactions_filters ON transactions(user_id, wallet_id, category_id, date);

-- Vector similarity search index
CREATE INDEX idx_transactions_embedding ON transactions USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================================================
-- 8. TRANSACTION LABELS (many-to-many)
-- ============================================================================

CREATE TABLE transaction_labels (
    transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
    label_id UUID REFERENCES labels(id) ON DELETE CASCADE,
    PRIMARY KEY (transaction_id, label_id)
);

CREATE INDEX idx_transaction_labels_tx ON transaction_labels(transaction_id);
CREATE INDEX idx_transaction_labels_label ON transaction_labels(label_id);

-- ============================================================================
-- 9. BUDGETS TABLE
-- ============================================================================

CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    period VARCHAR(20) NOT NULL CHECK (period IN ('daily', 'weekly', 'monthly', 'yearly', 'custom')),
    start_date DATE NOT NULL,
    end_date DATE,
    
    -- Filters
    wallet_ids UUID[],  -- NULL = all wallets
    category_ids UUID[],  -- NULL = all categories
    
    -- Alerts
    alert_threshold INTEGER DEFAULT 80,  -- % threshold for alerts
    alert_sent BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_budgets_user ON budgets(user_id);
CREATE INDEX idx_budgets_period ON budgets(start_date, end_date);

-- ============================================================================
-- 10. TRANSACTION TEMPLATES TABLE
-- ============================================================================

CREATE TABLE transaction_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    amount DECIMAL(15, 2),
    currency VARCHAR(3),
    note TEXT,
    label_ids UUID[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_templates_user ON transaction_templates(user_id);

-- ============================================================================
-- 11. CONNECTED SOURCES TABLE (for integrations)
-- ============================================================================

CREATE TABLE connected_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    wallet_id UUID REFERENCES wallets(id) ON DELETE CASCADE,
    
    -- Source info
    source_type VARCHAR(50) NOT NULL,  -- 'trustee', 'plaid', 'manual_api', etc.
    source_name VARCHAR(255) NOT NULL,  -- user-friendly name
    
    -- Authentication
    auth_type VARCHAR(50),  -- 'api_key', 'oauth', 'credentials'
    auth_data JSONB,  -- encrypted credentials
    
    -- Sync settings
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_frequency VARCHAR(20) DEFAULT 'hourly' CHECK (sync_frequency IN ('realtime', '15min', 'hourly', '6hours', 'manual')),
    last_sync_at TIMESTAMPTZ,
    next_sync_at TIMESTAMPTZ,
    
    -- Adapter configuration
    adapter_config JSONB,  -- field mappings, filters, etc.
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'error', 'paused')),
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sources_user ON connected_sources(user_id);
CREATE INDEX idx_sources_next_sync ON connected_sources(next_sync_at) WHERE sync_enabled = TRUE;

-- ============================================================================
-- 12. AI ANALYSIS CACHE TABLE
-- ============================================================================

CREATE TABLE ai_analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL,  -- 'period_summary', 'category_insights', etc.
    period_days INTEGER NOT NULL,
    
    -- Cache key (hash of parameters)
    cache_key VARCHAR(64) UNIQUE NOT NULL,
    
    -- Analysis result
    result JSONB NOT NULL,
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    transaction_count INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analysis_cache_key ON ai_analysis_cache(cache_key);
CREATE INDEX idx_analysis_expires ON ai_analysis_cache(expires_at);

-- ============================================================================
-- 13. USER SETTINGS TABLE
-- ============================================================================

CREATE TABLE user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Preferences
    theme VARCHAR(20) DEFAULT 'light',
    date_format VARCHAR(20) DEFAULT 'DD/MM/YYYY',
    first_day_of_week INTEGER DEFAULT 1,  -- 1 = Monday
    
    -- Notifications
    budget_alerts_enabled BOOLEAN DEFAULT TRUE,
    weekly_summary_enabled BOOLEAN DEFAULT TRUE,
    unusual_spending_alerts BOOLEAN DEFAULT TRUE,
    
    -- AI settings
    auto_categorization_enabled BOOLEAN DEFAULT TRUE,
    ai_suggestions_enabled BOOLEAN DEFAULT TRUE,
    
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transaction_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE recurring_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE transaction_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE connected_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Users: can only see their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (id = auth.uid());

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (id = auth.uid());

-- Wallets: owners and members can see
CREATE POLICY "Users can view own wallets" ON wallets
    FOR SELECT USING (
        owner_id = auth.uid() OR
        id IN (SELECT wallet_id FROM wallet_members WHERE user_id = auth.uid())
    );

CREATE POLICY "Owners can update wallets" ON wallets
    FOR UPDATE USING (owner_id = auth.uid());

CREATE POLICY "Owners can delete wallets" ON wallets
    FOR DELETE USING (owner_id = auth.uid());

-- Transactions: wallet members can see
CREATE POLICY "Users can view wallet transactions" ON transactions
    FOR SELECT USING (
        user_id = auth.uid() OR
        wallet_id IN (SELECT wallet_id FROM wallet_members WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can insert own transactions" ON transactions
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own transactions" ON transactions
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Users can delete own transactions" ON transactions
    FOR DELETE USING (user_id = auth.uid());

-- Categories: users can see system categories and own categories
CREATE POLICY "Users can view categories" ON categories
    FOR SELECT USING (is_system = TRUE OR user_id = auth.uid());

CREATE POLICY "Users can manage own categories" ON categories
    FOR ALL USING (user_id = auth.uid());

-- Labels: users can only see own labels
CREATE POLICY "Users can view own labels" ON labels
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can manage own labels" ON labels
    FOR ALL USING (user_id = auth.uid());

-- Budgets: users can only see own budgets
CREATE POLICY "Users can view own budgets" ON budgets
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can manage own budgets" ON budgets
    FOR ALL USING (user_id = auth.uid());

-- Similar policies for other tables...
-- (abbreviated for brevity, but same pattern)

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_budgets_updated_at BEFORE UPDATE ON budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON connected_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update wallet balance on transaction insert/update/delete
CREATE OR REPLACE FUNCTION update_wallet_balance()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.type = 'income' THEN
            UPDATE wallets SET current_balance = current_balance + NEW.amount WHERE id = NEW.wallet_id;
        ELSIF NEW.type = 'expense' THEN
            UPDATE wallets SET current_balance = current_balance - NEW.amount WHERE id = NEW.wallet_id;
        ELSIF NEW.type = 'transfer' THEN
            UPDATE wallets SET current_balance = current_balance - NEW.amount WHERE id = NEW.wallet_id;
            UPDATE wallets SET current_balance = current_balance + NEW.amount WHERE id = NEW.to_wallet_id;
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Reverse old transaction
        IF OLD.type = 'income' THEN
            UPDATE wallets SET current_balance = current_balance - OLD.amount WHERE id = OLD.wallet_id;
        ELSIF OLD.type = 'expense' THEN
            UPDATE wallets SET current_balance = current_balance + OLD.amount WHERE id = OLD.wallet_id;
        ELSIF OLD.type = 'transfer' THEN
            UPDATE wallets SET current_balance = current_balance + OLD.amount WHERE id = OLD.wallet_id;
            UPDATE wallets SET current_balance = current_balance - OLD.amount WHERE id = OLD.to_wallet_id;
        END IF;
        -- Apply new transaction
        IF NEW.type = 'income' THEN
            UPDATE wallets SET current_balance = current_balance + NEW.amount WHERE id = NEW.wallet_id;
        ELSIF NEW.type = 'expense' THEN
            UPDATE wallets SET current_balance = current_balance - NEW.amount WHERE id = NEW.wallet_id;
        ELSIF NEW.type = 'transfer' THEN
            UPDATE wallets SET current_balance = current_balance - NEW.amount WHERE id = NEW.wallet_id;
            UPDATE wallets SET current_balance = current_balance + NEW.amount WHERE id = NEW.to_wallet_id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        -- Reverse transaction
        IF OLD.type = 'income' THEN
            UPDATE wallets SET current_balance = current_balance - OLD.amount WHERE id = OLD.wallet_id;
        ELSIF OLD.type = 'expense' THEN
            UPDATE wallets SET current_balance = current_balance + OLD.amount WHERE id = OLD.wallet_id;
        ELSIF OLD.type = 'transfer' THEN
            UPDATE wallets SET current_balance = current_balance + OLD.amount WHERE id = OLD.wallet_id;
            UPDATE wallets SET current_balance = current_balance - OLD.amount WHERE id = OLD.to_wallet_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_wallet_balance_trigger
    AFTER INSERT OR UPDATE OR DELETE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_wallet_balance();

-- ============================================================================
-- SEED DATA: System Categories
-- ============================================================================

-- Income categories
INSERT INTO categories (name, type, icon, color, is_system) VALUES
    ('Salary', 'income', '💼', '#4CAF50', TRUE),
    ('Freelance', 'income', '💻', '#8BC34A', TRUE),
    ('Investment', 'income', '📈', '#009688', TRUE),
    ('Gift', 'income', '🎁', '#00BCD4', TRUE),
    ('Other Income', 'income', '💰', '#03A9F4', TRUE);

-- Expense categories
INSERT INTO categories (name, type, icon, color, is_system) VALUES
    ('Food & Dining', 'expense', '🍔', '#F44336', TRUE),
    ('Groceries', 'expense', '🛒', '#E91E63', TRUE),
    ('Transportation', 'expense', '🚗', '#9C27B0', TRUE),
    ('Shopping', 'expense', '🛍️', '#673AB7', TRUE),
    ('Entertainment', 'expense', '🎬', '#3F51B5', TRUE),
    ('Bills & Utilities', 'expense', '📄', '#2196F3', TRUE),
    ('Health & Fitness', 'expense', '⚕️', '#00BCD4', TRUE),
    ('Travel', 'expense', '✈️', '#009688', TRUE),
    ('Education', 'expense', '📚', '#4CAF50', TRUE),
    ('Subscriptions', 'expense', '📱', '#8BC34A', TRUE),
    ('Other Expense', 'expense', '💸', '#CDDC39', TRUE);

-- Transfer category
INSERT INTO categories (name, type, icon, color, is_system) VALUES
    ('Transfer', 'transfer', '🔄', '#FF9800', TRUE);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View: Transaction summary by category
CREATE OR REPLACE VIEW v_transaction_summary_by_category AS
SELECT 
    t.user_id,
    t.wallet_id,
    c.id AS category_id,
    c.name AS category_name,
    c.icon AS category_icon,
    c.type AS transaction_type,
    DATE_TRUNC('month', t.date) AS month,
    COUNT(*) AS transaction_count,
    SUM(t.amount) AS total_amount,
    t.currency
FROM transactions t
JOIN categories c ON t.category_id = c.id
GROUP BY t.user_id, t.wallet_id, c.id, c.name, c.icon, c.type, DATE_TRUNC('month', t.date), t.currency;

-- View: Monthly spending summary
CREATE OR REPLACE VIEW v_monthly_summary AS
SELECT 
    user_id,
    wallet_id,
    DATE_TRUNC('month', date) AS month,
    SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expenses,
    SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) AS net_change,
    currency
FROM transactions
GROUP BY user_id, wallet_id, DATE_TRUNC('month', date), currency;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
