-- PostgreSQL Initial Migration for Vertex AR B2B Platform (Post Schema Overhaul)
-- This migration creates all required tables with proper constraints, indexes, and relationships
-- Compatible with PostgreSQL 12+
-- 
-- Usage: psql -d vertex_ar -f 001_initial_complete_migration.sql
-- 
-- IMPORTANT: This version reflects the schema overhaul that removes legacy tables
-- (portraits, orders) and finalizes the AR Content centric architecture.

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ENUM types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'manager', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE notification_type AS ENUM ('email', 'telegram', 'system', 'sms');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role DEFAULT 'viewer' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    -- Rate limiting fields
    login_attempts INTEGER DEFAULT 0 NOT NULL,
    locked_until TIMESTAMPTZ
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active);
CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at);

-- 2. COMPANIES TABLE
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    
    -- Contact information
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    telegram_chat_id VARCHAR(100),
    
    -- Storage configuration
    storage_type VARCHAR(50) DEFAULT 'local', -- 'local', 'minio', 'yandex_disk'
    yandex_disk_folder_id VARCHAR(255),
    content_types VARCHAR(255), -- Comma-separated: 'portrait,video,ar'
    backup_provider VARCHAR(50), -- 'none', 'local', 'minio', 'yandex_disk'
    backup_remote_path VARCHAR(500),
    storage_connection_id INTEGER REFERENCES storage_connections(id),
    storage_path VARCHAR(500),
    
    -- Quotas and billing
    subscription_tier VARCHAR(50) DEFAULT 'basic',
    storage_quota_gb INTEGER DEFAULT 10,
    storage_used_bytes BIGINT DEFAULT 0,
    projects_limit INTEGER DEFAULT 50,
    subscription_expires_at TIMESTAMP,
    
    -- Status and metadata
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps and auditing
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    created_by INTEGER REFERENCES users(id)
);

-- Indexes for companies
CREATE INDEX IF NOT EXISTS ix_companies_name ON companies (name);
CREATE INDEX IF NOT EXISTS ix_companies_slug ON companies (slug);
CREATE INDEX IF NOT EXISTS ix_companies_storage_type ON companies (storage_type);
CREATE INDEX IF NOT EXISTS ix_companies_is_active ON companies (is_active);
CREATE INDEX IF NOT EXISTS ix_companies_created_at ON companies (created_at);

-- 3. STORAGE_CONNECTIONS TABLE
CREATE TABLE IF NOT EXISTS storage_connections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    provider VARCHAR(50) NOT NULL, -- 'local_disk', 'minio', 'yandex_disk'
    credentials JSONB DEFAULT '{}',
    base_path VARCHAR(500),
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    last_tested_at TIMESTAMP,
    test_status VARCHAR(50),
    test_error TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    created_by INTEGER REFERENCES users(id)
);

-- Indexes for storage_connections
CREATE INDEX IF NOT EXISTS ix_storage_connections_provider ON storage_connections (provider);
CREATE INDEX IF NOT EXISTS ix_storage_connections_is_active ON storage_connections (is_active);
CREATE INDEX IF NOT EXISTS ix_storage_connections_created_at ON storage_connections (created_at);

-- 4. PROJECTS TABLE
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Status and lifecycle
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'archived', 'suspended'
    subscription_end TIMESTAMP,
    lifecycle_status VARCHAR(50) DEFAULT 'active', -- 'active', 'expiring', 'expired', 'suspended'
    
    -- Notification tracking
    notified_7d BOOLEAN DEFAULT false,
    notified_24h BOOLEAN DEFAULT false,
    notified_expired BOOLEAN DEFAULT false,
    
    -- Configuration
    settings JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    created_by INTEGER REFERENCES users(id),
    
    -- Constraints
    UNIQUE(company_id, slug)
);

-- Indexes for projects
CREATE INDEX IF NOT EXISTS ix_projects_company_id ON projects (company_id);
CREATE INDEX IF NOT EXISTS ix_projects_status ON projects (status);
CREATE INDEX IF NOT EXISTS ix_projects_subscription_end ON projects (subscription_end);
CREATE INDEX IF NOT EXISTS ix_projects_created_at ON projects (created_at);

-- 5. FOLDERS TABLE
CREATE TABLE IF NOT EXISTS folders (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES folders(id),
    folder_path VARCHAR(500),
    is_active VARCHAR(50) DEFAULT 'active',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    -- Constraints
    UNIQUE(project_id, name, parent_id)
);

-- Indexes for folders
CREATE INDEX IF NOT EXISTS ix_folders_project_id ON folders (project_id);
CREATE INDEX IF NOT EXISTS ix_folders_parent_id ON folders (parent_id);
CREATE INDEX IF NOT EXISTS ix_folders_is_active ON folders (is_active);
CREATE INDEX IF NOT EXISTS ix_folders_created_at ON folders (created_at);

-- 6. CLIENTS TABLE
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    address VARCHAR(500),
    notes VARCHAR(1000),
    is_active VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Indexes for clients
CREATE INDEX IF NOT EXISTS ix_clients_company_id ON clients (company_id);
CREATE INDEX IF NOT EXISTS ix_clients_email ON clients (email);
CREATE INDEX IF NOT EXISTS ix_clients_name ON clients (name);

-- 7. VIDEOS TABLE (Updated to reference ar_content instead of portraits)
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    ar_content_id INTEGER NOT NULL REFERENCES ar_content(id) ON DELETE CASCADE,
    
    -- File information
    file_path VARCHAR(500) NOT NULL,
    public_url VARCHAR(500),
    video_path VARCHAR(500), -- Legacy compatibility
    video_url VARCHAR(500),  -- Legacy compatibility
    thumbnail_url VARCHAR(500),
    
    -- Video metadata
    title VARCHAR(255),
    duration DECIMAL(10,3),
    width INTEGER,
    height INTEGER,
    size_bytes INTEGER,
    mime_type VARCHAR(100),
    
    -- Status and scheduling
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'processing'
    is_active BOOLEAN DEFAULT true,
    
    -- Scheduling and rotation
    schedule_start TIMESTAMP,
    schedule_end TIMESTAMP,
    rotation_type VARCHAR(50), -- 'daily', 'weekly', 'monthly', 'custom'
    rotation_order INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Indexes for videos
CREATE INDEX IF NOT EXISTS ix_videos_ar_content_id ON videos (ar_content_id);
CREATE INDEX IF NOT EXISTS ix_videos_status ON videos (status);
CREATE INDEX IF NOT EXISTS ix_videos_rotation_type ON videos (rotation_type);
CREATE INDEX IF NOT EXISTS ix_videos_schedule_start ON videos (schedule_start);
CREATE INDEX IF NOT EXISTS ix_videos_schedule_end ON videos (schedule_end);
CREATE INDEX IF NOT EXISTS ix_videos_created_at ON videos (created_at);

-- 8. AR_CONTENT TABLE (Finalized schema after overhaul)
CREATE TABLE IF NOT EXISTS ar_content (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Immutable unique identifier
    unique_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    
    -- Basic information (finalized column names)
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- File paths and URLs
    image_path VARCHAR(500) NOT NULL,
    image_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    
    -- Video paths and URLs (new columns)
    video_path VARCHAR(500),
    video_url VARCHAR(500),
    
    -- QR code
    qr_code_path VARCHAR(500),
    qr_code_url VARCHAR(500),
    
    -- Preview URL (new column)
    preview_url VARCHAR(500),
    
    -- Status and lifecycle
    is_active BOOLEAN DEFAULT true,
    published_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Analytics
    views_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP,
    
    -- Content metadata (new standardized column)
    content_metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    -- Constraints
    UNIQUE(unique_id)
);

-- Indexes for ar_content (optimized for performance)
CREATE INDEX IF NOT EXISTS ix_ar_content_unique_id ON ar_content (unique_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_project_id ON ar_content (project_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_company_id ON ar_content (company_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_company_project ON ar_content (company_id, project_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_is_active ON ar_content (is_active);
CREATE INDEX IF NOT EXISTS ix_ar_content_created_at ON ar_content (created_at);

-- 9. EMAIL_QUEUE TABLE
CREATE TABLE IF NOT EXISTS email_queue (
    id SERIAL PRIMARY KEY,
    recipient_to VARCHAR(255) NOT NULL,
    recipient_cc VARCHAR(255),
    recipient_bcc VARCHAR(255),
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    html TEXT,
    template_id VARCHAR(100),
    variables JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'cancelled'
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_error TEXT,
    priority INTEGER DEFAULT 5, -- 1=highest, 10=lowest
    scheduled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    sent_at TIMESTAMP
);

-- Indexes for email_queue
CREATE INDEX IF NOT EXISTS ix_email_queue_status ON email_queue (status);
CREATE INDEX IF NOT EXISTS ix_email_queue_priority ON email_queue (priority);
CREATE INDEX IF NOT EXISTS ix_email_queue_scheduled_at ON email_queue (scheduled_at);
CREATE INDEX IF NOT EXISTS ix_email_queue_created_at ON email_queue (created_at);

-- 10. NOTIFICATIONS TABLE
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification details
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type notification_type DEFAULT 'system', -- 'email', 'telegram', 'system', 'sms'
    priority VARCHAR(50) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    
    -- Status and delivery
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP,
    delivered_at TIMESTAMP,
    
    -- Metadata and tracking
    source VARCHAR(100), -- Source system/service
    service_name VARCHAR(100), -- Service that generated the notification
    event_data JSONB DEFAULT '{}',
    group_id VARCHAR(100), -- For grouping related notifications
    
    -- Processing tracking
    processed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Indexes for notifications
CREATE INDEX IF NOT EXISTS ix_notifications_company_id ON notifications (company_id);
CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);
CREATE INDEX IF NOT EXISTS ix_notifications_type ON notifications (type);
CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications (is_read);
CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications (created_at);
CREATE INDEX IF NOT EXISTS ix_notifications_group_id ON notifications (group_id);

-- 11. AUDIT_LOG TABLE
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    entity_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL, -- 'create', 'update', 'delete', 'view', 'login', 'logout'
    changes JSONB DEFAULT '{}',
    field_name VARCHAR(100), -- For field-level changes
    
    -- Actor information
    actor_id INTEGER REFERENCES users(id),
    actor_email VARCHAR(255),
    actor_ip VARCHAR(64),
    user_agent TEXT,
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT now() NOT NULL
);

-- Indexes for audit_log
CREATE INDEX IF NOT EXISTS ix_audit_log_entity ON audit_log (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action);
CREATE INDEX IF NOT EXISTS ix_audit_log_actor_id ON audit_log (actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log (created_at);
CREATE INDEX IF NOT EXISTS ix_audit_log_session_id ON audit_log (session_id);

-- 12. Insert default admin user if not exists
INSERT INTO users (email, hashed_password, full_name, role, is_active)
VALUES (
    'admin@vertexar.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF2PQaDi',  -- admin123
    'Vertex AR Admin',
    'admin',
    true
) ON CONFLICT (email) DO NOTHING;

-- 13. Insert default storage connection if not exists
INSERT INTO storage_connections (name, provider, base_path, is_default, is_active, created_at, updated_at)
VALUES (
    'default_local',
    'local_disk',
    '/app/storage/content',
    true,
    true,
    now(),
    now()
) ON CONFLICT (name) DO NOTHING;

-- 14. Create default company if not exists
INSERT INTO companies (name, slug, contact_email, is_default, is_active, created_at, updated_at)
VALUES (
    'Vertex AR Demo',
    'vertex-ar-demo',
    'demo@vertexar.com',
    true,
    true,
    now(),
    now()
) ON CONFLICT (name) DO NOTHING;

-- 15. Create default project for demo company if not exists
INSERT INTO projects (company_id, name, slug, description, status, created_at, updated_at)
SELECT 
    c.id,
    'Demo Project',
    'demo-project',
    'Default demo project for getting started',
    'active',
    now(),
    now()
FROM companies c
WHERE c.slug = 'vertex-ar-demo'
AND NOT EXISTS (
    SELECT 1 FROM projects p 
    WHERE p.company_id = c.id AND p.slug = 'demo-project'
);

-- Final database setup
-- Update sequence values
SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM users;
SELECT setval(pg_get_serial_sequence('companies', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM companies;
SELECT setval(pg_get_serial_sequence('storage_connections', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM storage_connections;
SELECT setval(pg_get_serial_sequence('projects', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM projects;
SELECT setval(pg_get_serial_sequence('folders', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM folders;
SELECT setval(pg_get_serial_sequence('clients', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM clients;
SELECT setval(pg_get_serial_sequence('ar_content', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM ar_content;
SELECT setval(pg_get_serial_sequence('videos', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM videos;
SELECT setval(pg_get_serial_sequence('email_queue', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM email_queue;
SELECT setval(pg_get_serial_sequence('notifications', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM notifications;
SELECT setval(pg_get_serial_sequence('audit_log', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM audit_log;

-- Update table statistics for query optimizer
ANALYZE;

-- Migration completed successfully
-- Legacy tables (portraits, orders) have been removed
-- AR Content is now the central entity with proper relationships
-- All indexes and constraints are optimized for the new schema