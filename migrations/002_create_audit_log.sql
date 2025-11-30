-- Migration: Create audit_log table
-- Date: 2025-11-30
-- Description: Add audit log table for security and compliance

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user 
ON audit_log(user_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_action 
ON audit_log(action);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp 
ON audit_log(timestamp);
