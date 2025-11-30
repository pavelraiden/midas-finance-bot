-- ============================================================================
-- Migration: Add Balance Snapshots Table
-- Version: 002
-- Date: 2025-11-30
-- Description: Добавляет таблицу balance_snapshots для balance-based detection
-- ============================================================================

-- ============================================================================
-- BALANCE SNAPSHOTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS balance_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Wallet info
    wallet_id UUID REFERENCES wallets(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Balance info
    currency VARCHAR(10) NOT NULL,
    balance DECIMAL(30, 8) NOT NULL,  -- Support crypto precision
    
    -- Timestamp
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Source
    source VARCHAR(50) NOT NULL,  -- 'blockchain', 'api', 'manual'
    
    -- Blockchain metadata
    block_number BIGINT,
    chain_id VARCHAR(50),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_balance_snapshots_wallet ON balance_snapshots(wallet_id);
CREATE INDEX idx_balance_snapshots_user ON balance_snapshots(user_id);
CREATE INDEX idx_balance_snapshots_timestamp ON balance_snapshots(timestamp DESC);
CREATE INDEX idx_balance_snapshots_wallet_currency ON balance_snapshots(wallet_id, currency, timestamp DESC);

-- Unique constraint: one snapshot per wallet per currency per timestamp
CREATE UNIQUE INDEX idx_balance_snapshots_unique ON balance_snapshots(wallet_id, currency, timestamp);

-- ============================================================================
-- DETECTED TRANSACTIONS TABLE (from balance changes)
-- ============================================================================

CREATE TABLE IF NOT EXISTS detected_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User & Wallet
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    wallet_id UUID REFERENCES wallets(id) ON DELETE CASCADE,
    
    -- Balance snapshots
    from_snapshot_id UUID REFERENCES balance_snapshots(id) ON DELETE CASCADE,
    to_snapshot_id UUID REFERENCES balance_snapshots(id) ON DELETE CASCADE,
    
    -- Transaction details
    amount DECIMAL(30, 8) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('income', 'expense', 'unknown')),
    
    -- Detection metadata
    confidence FLOAT NOT NULL,  -- 0.0 - 1.0
    detection_method VARCHAR(50) NOT NULL,  -- 'balance_delta', 'pattern_match', etc.
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'rejected', 'merged')),
    
    -- Linked transaction (if confirmed)
    transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
    
    -- Timestamps
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_detected_transactions_user ON detected_transactions(user_id);
CREATE INDEX idx_detected_transactions_wallet ON detected_transactions(wallet_id);
CREATE INDEX idx_detected_transactions_status ON detected_transactions(status);
CREATE INDEX idx_detected_transactions_snapshots ON detected_transactions(from_snapshot_id, to_snapshot_id);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Latest balance for each wallet/currency
CREATE OR REPLACE VIEW v_latest_balances AS
SELECT DISTINCT ON (wallet_id, currency)
    wallet_id,
    user_id,
    currency,
    balance,
    timestamp,
    source
FROM balance_snapshots
ORDER BY wallet_id, currency, timestamp DESC;

-- View: Balance history with deltas
CREATE OR REPLACE VIEW v_balance_history AS
SELECT 
    bs.id,
    bs.wallet_id,
    bs.user_id,
    bs.currency,
    bs.balance,
    bs.timestamp,
    bs.source,
    LAG(bs.balance) OVER (PARTITION BY bs.wallet_id, bs.currency ORDER BY bs.timestamp) AS previous_balance,
    bs.balance - LAG(bs.balance) OVER (PARTITION BY bs.wallet_id, bs.currency ORDER BY bs.timestamp) AS delta,
    EXTRACT(EPOCH FROM (bs.timestamp - LAG(bs.timestamp) OVER (PARTITION BY bs.wallet_id, bs.currency ORDER BY bs.timestamp))) AS time_diff_seconds
FROM balance_snapshots bs
ORDER BY bs.wallet_id, bs.currency, bs.timestamp DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Get balance delta between two timestamps
CREATE OR REPLACE FUNCTION get_balance_delta(
    p_wallet_id UUID,
    p_currency VARCHAR,
    p_from_timestamp TIMESTAMPTZ,
    p_to_timestamp TIMESTAMPTZ
) RETURNS TABLE (
    from_balance DECIMAL,
    to_balance DECIMAL,
    delta DECIMAL,
    time_diff_seconds BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT balance FROM balance_snapshots 
         WHERE wallet_id = p_wallet_id AND currency = p_currency AND timestamp <= p_from_timestamp
         ORDER BY timestamp DESC LIMIT 1) AS from_balance,
        (SELECT balance FROM balance_snapshots 
         WHERE wallet_id = p_wallet_id AND currency = p_currency AND timestamp <= p_to_timestamp
         ORDER BY timestamp DESC LIMIT 1) AS to_balance,
        (SELECT balance FROM balance_snapshots 
         WHERE wallet_id = p_wallet_id AND currency = p_currency AND timestamp <= p_to_timestamp
         ORDER BY timestamp DESC LIMIT 1) - 
        (SELECT balance FROM balance_snapshots 
         WHERE wallet_id = p_wallet_id AND currency = p_currency AND timestamp <= p_from_timestamp
         ORDER BY timestamp DESC LIMIT 1) AS delta,
        EXTRACT(EPOCH FROM (p_to_timestamp - p_from_timestamp))::BIGINT AS time_diff_seconds;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE balance_snapshots IS 'Snapshots балансов кошельков для balance-based detection';
COMMENT ON TABLE detected_transactions IS 'Транзакции, детектированные по изменению баланса';
COMMENT ON COLUMN detected_transactions.confidence IS 'Confidence score (0.0-1.0) для детекции';
COMMENT ON COLUMN detected_transactions.status IS 'pending = ждет подтверждения, confirmed = создана транзакция, rejected = отклонено пользователем';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
