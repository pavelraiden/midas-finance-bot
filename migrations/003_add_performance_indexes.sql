-- Migration: Add Performance Indexes
-- Purpose: Optimize query performance for common access patterns
-- Date: 2025-11-30

-- Transactions table indexes
CREATE INDEX IF NOT EXISTS idx_transactions_user_id_timestamp 
ON transactions(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_wallet_id 
ON transactions(wallet_id);

CREATE INDEX IF NOT EXISTS idx_transactions_category_id 
ON transactions(category_id);

CREATE INDEX IF NOT EXISTS idx_transactions_merchant 
ON transactions(merchant);

CREATE INDEX IF NOT EXISTS idx_transactions_is_internal 
ON transactions(is_internal_transfer) 
WHERE is_internal_transfer = true;

CREATE INDEX IF NOT EXISTS idx_transactions_uncategorized 
ON transactions(user_id, timestamp DESC) 
WHERE category_id IS NULL;

-- Categories table indexes
CREATE INDEX IF NOT EXISTS idx_categories_user_id 
ON categories(user_id);

CREATE INDEX IF NOT EXISTS idx_categories_name 
ON categories(name);

-- Merchant mappings table indexes
CREATE INDEX IF NOT EXISTS idx_merchant_mappings_user_merchant 
ON merchant_mappings(user_id, merchant_name);

CREATE INDEX IF NOT EXISTS idx_merchant_mappings_category 
ON merchant_mappings(category_id);

-- Wallets table indexes
CREATE INDEX IF NOT EXISTS idx_wallets_user_id 
ON wallets(user_id);

CREATE INDEX IF NOT EXISTS idx_wallets_address 
ON wallets(address);

-- Balance snapshots table indexes
CREATE INDEX IF NOT EXISTS idx_balance_snapshots_wallet_timestamp 
ON balance_snapshots(wallet_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_balance_snapshots_user_id 
ON balance_snapshots(user_id, timestamp DESC);

-- Balance delta log table indexes
CREATE INDEX IF NOT EXISTS idx_balance_delta_log_wallet_timestamp 
ON balance_delta_log(wallet_id, timestamp DESC);

-- Uncategorized transactions table indexes
CREATE INDEX IF NOT EXISTS idx_uncategorized_user_detected 
ON uncategorized_transactions(user_id, detected_at DESC);

-- Labels table indexes
CREATE INDEX IF NOT EXISTS idx_labels_user_id 
ON labels(user_id);

-- Transaction labels table indexes
CREATE INDEX IF NOT EXISTS idx_transaction_labels_transaction 
ON transaction_labels(transaction_id);

CREATE INDEX IF NOT EXISTS idx_transaction_labels_label 
ON transaction_labels(label_id);

-- Audit log table indexes (if exists)
CREATE INDEX IF NOT EXISTS idx_audit_log_user_timestamp 
ON audit_log(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_action 
ON audit_log(action);

-- Comments
COMMENT ON INDEX idx_transactions_user_id_timestamp IS 'Optimize user transaction history queries';
COMMENT ON INDEX idx_transactions_uncategorized IS 'Fast lookup for uncategorized transactions';
COMMENT ON INDEX idx_merchant_mappings_user_merchant IS 'Fast merchant-to-category lookup';
COMMENT ON INDEX idx_balance_snapshots_wallet_timestamp IS 'Optimize balance history queries';
