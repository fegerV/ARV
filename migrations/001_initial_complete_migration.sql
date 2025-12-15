-- Initial Database Schema for Vertex AR Platform
-- This file creates the complete database schema from scratch
-- Generated from Alembic migration: 44af7900a836

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables in correct order to avoid circular dependencies

-- 1. Companies (no dependencies)
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    contact_email VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_companies_id ON companies (id);

-- 2. Users (no dependencies)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    role VARCHAR NOT NULL DEFAULT 'admin',
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ
);
CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_id ON users (id);

-- 3. Projects (depends on companies)
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_projects_id ON projects (id);
CREATE INDEX ix_projects_company_id ON projects (company_id);
CREATE INDEX ix_project_company_name ON projects (company_id, name);

-- 4. Storage connections (no dependencies)
CREATE TABLE storage_connections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(50) NOT NULL,
    base_path VARCHAR(500) NOT NULL,
    is_default BOOLEAN,
    is_active BOOLEAN,
    last_tested_at TIMESTAMP,
    test_status VARCHAR(50),
    test_error TEXT,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by INTEGER
);

-- 5. Videos (created before ar_content to break circular dependency)
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    ar_content_id INTEGER NOT NULL, -- FK will be added after ar_content table
    filename VARCHAR(255) NOT NULL,
    video_path VARCHAR(500),
    video_url VARCHAR(500),
    thumbnail_path VARCHAR(500),
    thumbnail_url VARCHAR(500),
    preview_url VARCHAR(500),
    duration INTEGER,
    width INTEGER,
    height INTEGER,
    size_bytes INTEGER,
    mime_type VARCHAR(100),
    status VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL,
    rotation_type VARCHAR(20) NOT NULL,
    rotation_order INTEGER NOT NULL,
    subscription_end TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_videos_id ON videos (id);

-- 6. AR Content (depends on projects, companies, videos)
CREATE TABLE ar_content (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    active_video_id INTEGER REFERENCES videos(id),
    unique_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    order_number VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    customer_email VARCHAR(255),
    duration_years INTEGER NOT NULL CHECK (duration_years IN (1, 3, 5)),
    views_count INTEGER NOT NULL DEFAULT 0 CHECK (views_count >= 0),
    status VARCHAR(50) NOT NULL,
    content_metadata JSONB,
    photo_path VARCHAR(500),
    photo_url VARCHAR(500),
    video_path VARCHAR(500),
    video_url VARCHAR(500),
    qr_code_path VARCHAR(500),
    qr_code_url VARCHAR(500),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_ar_content_id ON ar_content (id);
CREATE INDEX ix_ar_content_project_id ON ar_content (project_id);
CREATE UNIQUE INDEX ix_ar_content_project_order ON ar_content (project_id, order_number);

-- Now add the FK from videos to ar_content
ALTER TABLE videos ADD CONSTRAINT fk_videos_ar_content_id 
    FOREIGN KEY (ar_content_id) REFERENCES ar_content(id);

-- 7. Email queue (no dependencies)
CREATE TABLE email_queue (
    id SERIAL PRIMARY KEY,
    recipient_to VARCHAR(255) NOT NULL,
    recipient_cc VARCHAR(255),
    recipient_bcc VARCHAR(255),
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    html TEXT,
    template_id VARCHAR(100),
    variables JSONB,
    status VARCHAR(50),
    attempts INTEGER,
    max_attempts INTEGER,
    last_error TEXT,
    priority INTEGER,
    scheduled_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    sent_at TIMESTAMP
);

-- 8. Notifications (depends on companies, projects, ar_content)
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    project_id INTEGER REFERENCES projects(id),
    ar_content_id INTEGER REFERENCES ar_content(id),
    notification_type VARCHAR(50) NOT NULL,
    email_sent BOOLEAN,
    email_sent_at TIMESTAMP,
    email_error TEXT,
    telegram_sent BOOLEAN,
    telegram_sent_at TIMESTAMP,
    telegram_error TEXT,
    subject VARCHAR(500),
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMP
);

-- 9. Audit log (depends on companies, users)
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    entity_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL,
    changes JSONB,
    field_name VARCHAR(100),
    actor_id INTEGER REFERENCES users(id),
    actor_email VARCHAR(255),
    actor_ip VARCHAR(64),
    user_agent TEXT,
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL
);

-- 10. Clients (depends on companies)
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    address VARCHAR(500),
    notes VARCHAR(1000),
    is_active VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 11. Storage folders (depends on companies)
CREATE TABLE storage_folders (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    name VARCHAR(255) NOT NULL,
    path VARCHAR(500) NOT NULL,
    folder_type VARCHAR(50),
    files_count INTEGER,
    total_size_bytes BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 12. Video schedules (depends on videos)
CREATE TABLE video_schedules (
    id SERIAL PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status VARCHAR(20),
    description VARCHAR(500),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT check_schedule_time_range CHECK (start_time <= end_time)
);
CREATE INDEX ix_video_schedules_id ON video_schedules (id);

-- 13. Video rotation schedules (depends on ar_content)
CREATE TABLE video_rotation_schedules (
    id SERIAL PRIMARY KEY,
    ar_content_id INTEGER NOT NULL REFERENCES ar_content(id),
    rotation_type VARCHAR(50) NOT NULL,
    time_of_day TIME,
    day_of_week INTEGER,
    day_of_month INTEGER,
    cron_expression VARCHAR(100),
    video_sequence INTEGER[],
    current_index INTEGER,
    is_active INTEGER,
    last_rotation_at TIMESTAMP,
    next_rotation_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_video_rotation_schedules_id ON video_rotation_schedules (id);

-- 14. AR view sessions (depends on ar_content, projects, companies)
CREATE TABLE ar_view_sessions (
    id SERIAL PRIMARY KEY,
    ar_content_id INTEGER NOT NULL REFERENCES ar_content(id),
    project_id INTEGER NOT NULL REFERENCES projects(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    session_id UUID,
    user_agent VARCHAR,
    device_type VARCHAR(50),
    browser VARCHAR(100),
    os VARCHAR(100),
    ip_address VARCHAR(64),
    country VARCHAR(100),
    city VARCHAR(100),
    duration_seconds INTEGER,
    tracking_quality VARCHAR(50),
    video_played BOOLEAN,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_ar_view_sessions_id ON ar_view_sessions (id);

-- 15. Folders (depends on projects)
CREATE TABLE folders (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES folders(id),
    folder_path VARCHAR(500),
    is_active VARCHAR(50),
    sort_order INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Create Alembic version table
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

-- Set current Alembic version
INSERT INTO alembic_version (version_num) VALUES ('44af7900a836');