-- Recommended fixes before production.
-- Review before executing in the target database.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS "Control";
CREATE SCHEMA IF NOT EXISTS "Staging";
-- CREATE SCHEMA IF NOT EXISTS "Data_Warehouse";

-- If these tables already exist in public and you want schemas, move them intentionally:
-- ALTER TABLE public.data_imports SET SCHEMA "Control";
-- ALTER TABLE public.import_error_details SET SCHEMA "Control";
-- ALTER TABLE public.staging_branches SET SCHEMA "Staging";

ALTER TABLE IF EXISTS "Control".import_error_details
    ALTER COLUMN error_id SET DEFAULT gen_random_uuid();

ALTER TABLE IF EXISTS "Control".import_error_details
    ALTER COLUMN import_id SET NOT NULL;

ALTER TABLE IF EXISTS "Control".import_error_details
    DROP CONSTRAINT IF EXISTS import_error_details_import_id_fkey;

ALTER TABLE IF EXISTS "Control".import_error_details
    ADD CONSTRAINT import_error_details_import_id_fkey
    FOREIGN KEY (import_id)
    REFERENCES "Control".data_imports(import_id)
    ON DELETE CASCADE;

ALTER TABLE IF EXISTS "Control".data_imports
    ADD CONSTRAINT chk_data_imports_status
    CHECK (status IN ('PENDING', 'UPLOADED', 'PROCESSING', 'COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED'));

ALTER TABLE IF EXISTS "Control".data_imports
    ADD CONSTRAINT chk_data_imports_source_type
    CHECK (source_type IN ('excel', 'csv', 'api', 'manual'));

ALTER TABLE IF EXISTS "Control".import_error_details
    ADD CONSTRAINT chk_import_error_details_severity
    CHECK (severity IN ('ERROR', 'WARNING', 'INFO'));

ALTER TABLE IF EXISTS "Staging".staging_branches
    ADD CONSTRAINT uq_staging_branches_import_row UNIQUE (import_id, row_number);

-- Fixed version of the status procedure from the notes.
CREATE OR REPLACE FUNCTION "Control".sp_update_import_status (
    p_import_id UUID,
    p_status VARCHAR(30),
    p_total_records INT DEFAULT NULL,
    p_processed_records INT DEFAULT NULL,
    p_success_records INT DEFAULT NULL,
    p_failed_records INT DEFAULT NULL,
    p_skipped_records INT DEFAULT NULL,
    p_error_summary TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE "Control".data_imports
    SET
        status = p_status,
        total_records = COALESCE(p_total_records, total_records),
        processed_records = COALESCE(p_processed_records, processed_records),
        success_records = COALESCE(p_success_records, success_records),
        failed_records = COALESCE(p_failed_records, failed_records),
        skipped_records = COALESCE(p_skipped_records, skipped_records),
        error_summary = COALESCE(p_error_summary, error_summary),
        upload_completed_at = CASE
            WHEN p_status = 'UPLOADED' THEN CURRENT_TIMESTAMP
            ELSE upload_completed_at
        END,
        processing_started_at = CASE
            WHEN p_status = 'PROCESSING' THEN CURRENT_TIMESTAMP
            ELSE processing_started_at
        END,
        processing_completed_at = CASE
            WHEN p_status IN ('COMPLETED', 'PARTIAL', 'FAILED') THEN CURRENT_TIMESTAMP
            ELSE processing_completed_at
        END,
        total_duration_seconds = CASE
            WHEN p_status IN ('COMPLETED', 'PARTIAL', 'FAILED') AND upload_started_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - upload_started_at))::INT
            ELSE total_duration_seconds
        END
    WHERE import_id = p_import_id;
END;
$$ LANGUAGE plpgsql;

-- Optional missing staging tables for import types included in the service registry.
CREATE TABLE IF NOT EXISTS "Staging".staging_inventory (
    staging_inventory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_id UUID NOT NULL REFERENCES "Control".data_imports(import_id) ON DELETE CASCADE,
    row_number INT NOT NULL,
    raw_data JSONB NOT NULL,
    is_processed BOOLEAN DEFAULT FALSE,
    is_valid BOOLEAN DEFAULT FALSE,
    chunk_number INT,
    validation_errors JSONB,
    clean_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    CONSTRAINT uq_staging_inventory_import_row UNIQUE (import_id, row_number)
);

CREATE TABLE IF NOT EXISTS "Staging".staging_product_suppliers (
    staging_product_suppliers_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_id UUID NOT NULL REFERENCES "Control".data_imports(import_id) ON DELETE CASCADE,
    row_number INT NOT NULL,
    raw_data JSONB NOT NULL,
    is_processed BOOLEAN DEFAULT FALSE,
    is_valid BOOLEAN DEFAULT FALSE,
    chunk_number INT,
    validation_errors JSONB,
    clean_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    CONSTRAINT uq_staging_product_suppliers_import_row UNIQUE (import_id, row_number)
);

