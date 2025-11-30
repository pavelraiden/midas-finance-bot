-- ============================================================================
-- Migration: Add Audit Log Table
-- Version: 001
-- Date: 2025-11-30
-- Description: Добавляет таблицу audit_log для comprehensive audit logging
-- ============================================================================

-- ============================================================================
-- AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Who & When
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- What
    action VARCHAR(100) NOT NULL,  -- e.g., 'transaction.create', 'wallet.delete'
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Details (JSON)
    details JSONB,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_success ON audit_log(success) WHERE success = FALSE;

-- Index для поиска по details (JSONB)
CREATE INDEX idx_audit_log_details ON audit_log USING GIN (details);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE audit_log IS 'Comprehensive audit log для всех критических операций';
COMMENT ON COLUMN audit_log.action IS 'Тип действия (transaction.create, wallet.delete, etc.)';
COMMENT ON COLUMN audit_log.details IS 'JSON с деталями операции (transaction_id, amount, etc.)';
COMMENT ON COLUMN audit_log.ip_address IS 'IP адрес пользователя (для security tracking)';
COMMENT ON COLUMN audit_log.user_agent IS 'User agent (для device tracking)';

-- ============================================================================
-- RETENTION POLICY (Optional)
-- ============================================================================

-- Для 50 users можно хранить audit logs бесконечно долго
-- Но если нужно - можно добавить retention policy:

-- CREATE OR REPLACE FUNCTION delete_old_audit_logs() RETURNS void AS $$
-- BEGIN
--     DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '2 years';
-- END;
-- $$ LANGUAGE plpgsql;

-- -- Schedule cleanup (requires pg_cron extension)
-- -- SELECT cron.schedule('cleanup-audit-logs', '0 0 1 * *', 'SELECT delete_old_audit_logs()');

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
