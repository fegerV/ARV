-- Initialize database with ar_content table including missing timestamp columns

-- Create ar_content table with all required columns including timestamps
CREATE TABLE IF NOT EXISTS ar_content (
    id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    active_video_id INTEGER,
    unique_id UUID NOT NULL,
    order_number VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    duration_years INTEGER NOT NULL,
    views_count INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    content_metadata JSON,
    photo_path VARCHAR(500),
    photo_url VARCHAR(500),
    video_path VARCHAR(500),
    video_url VARCHAR(500),
    qr_code_path VARCHAR(500),
    qr_code_url VARCHAR(500),
    -- Missing timestamp columns
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    UNIQUE (unique_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_ar_content_company_id ON ar_content (company_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_id ON ar_content (id);
CREATE INDEX IF NOT EXISTS ix_ar_content_project_id ON ar_content (project_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_project_order ON ar_content (project_id, order_number);

-- Add check constraints
ALTER TABLE ar_content ADD CONSTRAINT IF NOT EXISTS check_duration_years CHECK (duration_years IN (1, 3, 5));
ALTER TABLE ar_content ADD CONSTRAINT IF NOT EXISTS check_views_count_non_negative CHECK (views_count >= 0);