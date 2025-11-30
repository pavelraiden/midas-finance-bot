-- Migration: Create balance_snapshots table
-- Date: 2025-11-30
-- Description: Add balance snapshots table for balance-based transaction detection

CREATE TABLE IF NOT EXISTS balance_snapshots (
    id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    balance REAL NOT NULL,
    available_balance REAL,
    reserved_balance REAL,
    snapshot_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    provider TEXT,
    metadata TEXT,
    FOREIGN KEY (wallet_id) REFERENCES wallets(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_balance_snapshots_wallet_currency 
ON balance_snapshots(wallet_id, currency);

CREATE INDEX IF NOT EXISTS idx_balance_snapshots_timestamp 
ON balance_snapshots(snapshot_timestamp);
