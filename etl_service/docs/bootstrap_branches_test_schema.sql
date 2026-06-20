-- Minimal schema needed to test POST /imports/file with import_type = branches
-- and process_now = false.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS "Control";
CREATE SCHEMA IF NOT EXISTS "Staging";

CREATE TABLE IF NOT EXISTS "Control".data_imports (
    import_id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    import_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    original_filename TEXT,
    file_path TEXT,
    file_size_bytes BIGINT,
    status TEXT NOT NULL,
    total_records INTEGER NOT NULL DEFAULT 0,
    processed_records INTEGER NOT NULL DEFAULT 0,
    success_records INTEGER NOT NULL DEFAULT 0,
    failed_records INTEGER NOT NULL DEFAULT 0,
    skipped_records INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT,
    upload_started_at TIMESTAMP,
    upload_completed_at TIMESTAMP,
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    total_duration_seconds INTEGER,
    created_by TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "Control".import_error_details (
    error_id UUID PRIMARY KEY,
    import_id UUID NOT NULL REFERENCES "Control".data_imports(import_id) ON DELETE CASCADE,
    row_number INTEGER,
    error_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    field_name TEXT,
    field_value TEXT,
    expected_format TEXT,
    error_message TEXT NOT NULL,
    suggested_fix TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "Staging".staging_branches (
    staging_branches_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_id UUID NOT NULL REFERENCES "Control".data_imports(import_id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    raw_data JSONB NOT NULL,
    clean_data JSONB,
    validation_errors JSONB,
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,
    is_valid BOOLEAN NOT NULL DEFAULT FALSE,
    chunk_number INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    CONSTRAINT uq_staging_branches_import_row UNIQUE (import_id, row_number)
);
