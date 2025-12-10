-- PostgreSQL Initial Migration for Vertex AR B2B Platform
-- This migration creates all required tables with proper constraints, indexes, and relationships
-- Compatible with PostgreSQL 12+
-- 
-- Usage: psql -d vertex_ar -f 001_initial_complete_migration.sql

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

-- 4. STORAGE_FOLDERS TABLE
CREATE TABLE IF NOT EXISTS storage_folders (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    path VARCHAR(500) NOT NULL,
    folder_type VARCHAR(50), -- 'portraits', 'videos', 'markers', 'custom'
    files_count INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Indexes for storage_folders
CREATE INDEX IF NOT EXISTS ix_storage_folders_company_id ON storage_folders (company_id);
CREATE INDEX IF NOT EXISTS ix_storage_folders_folder_type ON storage_folders (folder_type);

-- 5. PROJECTS TABLE
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    folder_path VARCHAR(500),
    description TEXT,
    project_type VARCHAR(100),
    
    -- Subscription information
    subscription_type VARCHAR(50) DEFAULT 'monthly',
    subscription_end TIMESTAMP,
    starts_at TIMESTAMP,
    auto_renew INTEGER DEFAULT 0,
    
    -- Status and lifecycle
    status VARCHAR(50) DEFAULT 'active',
    lifecycle_status VARCHAR(50) DEFAULT 'active', -- 'active', 'expiring', 'expired', 'suspended'
    
    -- Notification tracking
    notified_7d BOOLEAN DEFAULT false,
    notified_24h BOOLEAN DEFAULT false,
    notified_expired BOOLEAN DEFAULT false,
    
    -- Additional fields
    notify_before_expiry_days INTEGER DEFAULT 7,
    last_notification_sent_at TIMESTAMP,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Unique constraint for project slug within company
CREATE UNIQUE INDEX IF NOT EXISTS ux_projects_company_slug ON projects (company_id, slug);

-- Indexes for projects
CREATE INDEX IF NOT EXISTS ix_projects_company_id ON projects (company_id);
CREATE INDEX IF NOT EXISTS ix_projects_status ON projects (status);
CREATE INDEX IF NOT EXISTS ix_projects_subscription_end ON projects (subscription_end);
CREATE INDEX IF NOT EXISTS ix_projects_created_at ON projects (created_at);

-- 6. FOLDERS TABLE (Project organization)
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
    updated_at TIMESTAMP DEFAULT now()
);

-- Indexes for folders
CREATE INDEX IF NOT EXISTS ix_folders_project_id ON folders (project_id);
CREATE INDEX IF NOT EXISTS ix_folders_parent_id ON folders (parent_id);
CREATE INDEX IF NOT EXISTS ix_folders_is_active ON folders (is_active);

-- 7. CLIENTS TABLE
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

-- 8. ORDERS TABLE
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    client_id INTEGER REFERENCES clients(id),
    order_number VARCHAR(100) UNIQUE NOT NULL,
    content_type VARCHAR(100) NOT NULL, -- 'portrait', 'video', 'ar_content'
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'cancelled'
    payment_status VARCHAR(50) DEFAULT 'unpaid', -- 'unpaid', 'paid', 'refunded'
    
    -- Financial information
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Subscription information
    subscription_end TIMESTAMP,
    
    -- Additional information
    description TEXT,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    completed_at TIMESTAMP
);

-- Indexes for orders
CREATE INDEX IF NOT EXISTS ix_orders_company_id ON orders (company_id);
CREATE INDEX IF NOT EXISTS ix_orders_client_id ON orders (client_id);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status);
CREATE INDEX IF NOT EXISTS ix_orders_payment_status ON orders (payment_status);
CREATE INDEX IF NOT EXISTS ix_orders_subscription_end ON orders (subscription_end);
CREATE INDEX IF NOT EXISTS ix_orders_created_at ON orders (created_at);

-- 9. PORTRAITS TABLE
CREATE TABLE IF NOT EXISTS portraits (
    id SERIAL PRIMARY KEY,
    unique_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    
    -- Relationships
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    client_id INTEGER REFERENCES clients(id),
    folder_id INTEGER REFERENCES folders(id),
    
    -- File information
    file_path VARCHAR(500) NOT NULL,
    public_url VARCHAR(500),
    image_path VARCHAR(500), -- Legacy compatibility
    image_url VARCHAR(500),  -- Legacy compatibility
    thumbnail_path VARCHAR(500),
    
    -- Status and lifecycle
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'archived'
    subscription_end TIMESTAMP,
    lifecycle_status VARCHAR(50) DEFAULT 'active', -- 'active', 'expiring', 'expired', 'suspended'
    
    -- Notification tracking
    notified_7d BOOLEAN DEFAULT false,
    notified_24h BOOLEAN DEFAULT false,
    notified_expired BOOLEAN DEFAULT false,
    
    -- MindAR marker
    marker_path VARCHAR(500),
    marker_url VARCHAR(500),
    marker_status VARCHAR(50) DEFAULT 'pending',
    
    -- Storage metadata
    storage_connection_id INTEGER,
    storage_folder_id INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for portraits
CREATE INDEX IF NOT EXISTS ix_portraits_unique_id ON portraits (unique_id);
CREATE INDEX IF NOT EXISTS ix_portraits_company_id ON portraits (company_id);
CREATE INDEX IF NOT EXISTS ix_portraits_client_id ON portraits (client_id);
CREATE INDEX IF NOT EXISTS ix_portraits_folder_id ON portraits (folder_id);
CREATE INDEX IF NOT EXISTS ix_portraits_status ON portraits (status);
CREATE INDEX IF NOT EXISTS ix_portraits_subscription_end ON portraits (subscription_end);
CREATE INDEX IF NOT EXISTS ix_portraits_marker_status ON portraits (marker_status);
CREATE INDEX IF NOT EXISTS ix_portraits_created_at ON portraits (created_at);

-- 10. VIDEOS TABLE
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    portrait_id INTEGER NOT NULL REFERENCES portraits(id) ON DELETE CASCADE,
    
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
CREATE INDEX IF NOT EXISTS ix_videos_portrait_id ON videos (portrait_id);
CREATE INDEX IF NOT EXISTS ix_videos_status ON videos (status);
CREATE INDEX IF NOT EXISTS ix_videos_rotation_type ON videos (rotation_type);
CREATE INDEX IF NOT EXISTS ix_videos_schedule_start ON videos (schedule_start);
CREATE INDEX IF NOT EXISTS ix_videos_schedule_end ON videos (schedule_end);
CREATE INDEX IF NOT EXISTS ix_videos_created_at ON videos (created_at);

-- 11. AR_CONTENT TABLE
CREATE TABLE IF NOT EXISTS ar_content (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    unique_id UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Client information
    client_name VARCHAR(255),
    client_phone VARCHAR(50),
    client_email VARCHAR(255),
    
    -- File paths
    image_path VARCHAR(500) NOT NULL,
    image_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    marker_path VARCHAR(500),
    marker_url VARCHAR(500),
    marker_status VARCHAR(50) DEFAULT 'pending',
    marker_generated_at TIMESTAMP,
    
    -- Video configuration
    active_video_id INTEGER,
    video_rotation_enabled BOOLEAN DEFAULT false,
    video_rotation_type VARCHAR(50),
    
    -- Status and lifecycle
    is_active BOOLEAN DEFAULT true,
    published_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- QR code
    qr_code_path VARCHAR(500),
    qr_code_url VARCHAR(500),
    
    -- Analytics
    views_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Indexes for ar_content
CREATE INDEX IF NOT EXISTS ix_ar_content_unique_id ON ar_content (unique_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_project_id ON ar_content (project_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_company_id ON ar_content (company_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_is_active ON ar_content (is_active);
CREATE INDEX IF NOT EXISTS ix_ar_content_marker_status ON ar_content (marker_status);
CREATE INDEX IF NOT EXISTS ix_ar_content_created_at ON ar_content (created_at);

-- 12. VIDEO_ROTATION_SCHEDULES TABLE
CREATE TABLE IF NOT EXISTS video_rotation_schedules (
    id SERIAL PRIMARY KEY,
    ar_content_id INTEGER NOT NULL REFERENCES ar_content(id) ON DELETE CASCADE,
    
    rotation_type VARCHAR(50) NOT NULL,
    time_of_day TIME,
    day_of_week INTEGER,
    day_of_month INTEGER,
    cron_expression VARCHAR(100),
    
    video_sequence INTEGER[],
    current_index INTEGER DEFAULT 0,
    
    is_active INTEGER DEFAULT 1,
    last_rotation_at TIMESTAMP,
    next_rotation_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT now()
);

-- Indexes for video_rotation_schedules
CREATE INDEX IF NOT EXISTS ix_video_rotation_schedules_ar_content_id ON video_rotation_schedules (ar_content_id);
CREATE INDEX IF NOT EXISTS ix_video_rotation_schedules_rotation_type ON video_rotation_schedules (rotation_type);
CREATE INDEX IF NOT EXISTS ix_video_rotation_schedules_is_active ON video_rotation_schedules (is_active);

-- 13. AR_VIEW_SESSIONS TABLE
CREATE TABLE IF NOT EXISTS ar_view_sessions (
    id SERIAL PRIMARY KEY,
    ar_content_id INTEGER NOT NULL REFERENCES ar_content(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    session_id UUID DEFAULT uuid_generate_v4(),
    
    -- User agent and device information
    user_agent TEXT,
    device_type VARCHAR(50),
    browser VARCHAR(100),
    os VARCHAR(100),
    
    -- Location information
    ip_address VARCHAR(64),
    country VARCHAR(100),
    city VARCHAR(100),
    
    -- Session data
    duration_seconds INTEGER,
    tracking_quality VARCHAR(50),
    video_played BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT now()
);

-- Indexes for ar_view_sessions
CREATE INDEX IF NOT EXISTS ix_ar_view_sessions_ar_content_id ON ar_view_sessions (ar_content_id);
CREATE INDEX IF NOT EXISTS ix_ar_view_sessions_company_id ON ar_view_sessions (company_id);
CREATE INDEX IF NOT EXISTS ix_ar_view_sessions_session_id ON ar_view_sessions (session_id);
CREATE INDEX IF NOT EXISTS ix_ar_view_sessions_created_at ON ar_view_sessions (created_at);

-- 14. NOTIFICATIONS TABLE
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    
    -- Target references
    company_id INTEGER REFERENCES companies(id),
    project_id INTEGER,
    ar_content_id INTEGER,
    
    -- Notification details
    type VARCHAR(50) NOT NULL, -- 'email', 'telegram', 'system', 'sms'
    notification_type VARCHAR(50), -- Legacy compatibility
    priority VARCHAR(50) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    
    -- Message content
    subject VARCHAR(500),
    message TEXT,
    
    -- Delivery tracking
    email_sent BOOLEAN DEFAULT false,
    email_sent_at TIMESTAMP,
    email_error TEXT,
    
    telegram_sent BOOLEAN DEFAULT false,
    telegram_sent_at TIMESTAMP,
    telegram_error TEXT,
    
    -- Additional metadata
    source VARCHAR(100),
    service_name VARCHAR(100),
    event_data JSONB DEFAULT '{}',
    group_id VARCHAR(100),
    
    -- Status and timestamps
    status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    read_at TIMESTAMP
);

-- Indexes for notifications
CREATE INDEX IF NOT EXISTS ix_notifications_company_id ON notifications (company_id);
CREATE INDEX IF NOT EXISTS ix_notifications_type ON notifications (type);
CREATE INDEX IF NOT EXISTS ix_notifications_status ON notifications (status);
CREATE INDEX IF NOT EXISTS ix_notifications_priority ON notifications (priority);
CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications (created_at);

-- 15. EMAIL_QUEUE TABLE
CREATE TABLE IF NOT EXISTS email_queue (
    id SERIAL PRIMARY KEY,
    
    -- Recipients
    recipient_to VARCHAR(255) NOT NULL,
    recipient_cc VARCHAR(255),
    recipient_bcc VARCHAR(255),
    
    -- Message content
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    html TEXT,
    
    -- Template information
    template_id VARCHAR(100),
    variables JSONB DEFAULT '{}',
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'cancelled'
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    last_error TEXT,
    
    -- Priority and scheduling
    priority INTEGER DEFAULT 5, -- 1-10, lower number = higher priority
    scheduled_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    sent_at TIMESTAMP
);

-- Indexes for email_queue
CREATE INDEX IF NOT EXISTS ix_email_queue_status ON email_queue (status);
CREATE INDEX IF NOT EXISTS ix_email_queue_priority ON email_queue (priority);
CREATE INDEX IF NOT EXISTS ix_email_queue_scheduled_at ON email_queue (scheduled_at);
CREATE INDEX IF NOT EXISTS ix_email_queue_created_at ON email_queue (created_at);

-- 16. AUDIT_LOG TABLE
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    
    -- Entity information
    entity_type VARCHAR(100) NOT NULL, -- 'user', 'company', 'project', etc.
    entity_id INTEGER NOT NULL,
    
    -- Action information
    action VARCHAR(100) NOT NULL, -- 'create', 'update', 'delete', 'login', etc.
    
    -- Change details
    changes JSONB DEFAULT '{}', -- Before/after values
    field_name VARCHAR(100), -- Specific field that changed
    
    -- Actor information
    actor_id INTEGER REFERENCES users(id),
    actor_email VARCHAR(255),
    actor_ip VARCHAR(64),
    user_agent TEXT,
    
    -- Additional context
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

-- FOREIGN KEY CONSTRAINTS (add after all tables are created)
DO $$
BEGIN
    -- Add foreign keys if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_companies_storage_connection') THEN
        ALTER TABLE companies ADD CONSTRAINT fk_companies_storage_connection 
            FOREIGN KEY (storage_connection_id) REFERENCES storage_connections(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_projects_company') THEN
        ALTER TABLE projects ADD CONSTRAINT fk_projects_company 
            FOREIGN KEY (company_id) REFERENCES companies(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_folders_project') THEN
        ALTER TABLE folders ADD CONSTRAINT fk_folders_project 
            FOREIGN KEY (project_id) REFERENCES projects(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_folders_parent') THEN
        ALTER TABLE folders ADD CONSTRAINT fk_folders_parent 
            FOREIGN KEY (parent_id) REFERENCES folders(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_clients_company') THEN
        ALTER TABLE clients ADD CONSTRAINT fk_clients_company 
            FOREIGN KEY (company_id) REFERENCES companies(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_orders_company') THEN
        ALTER TABLE orders ADD CONSTRAINT fk_orders_company 
            FOREIGN KEY (company_id) REFERENCES companies(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_orders_client') THEN
        ALTER TABLE orders ADD CONSTRAINT fk_orders_client 
            FOREIGN KEY (client_id) REFERENCES clients(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_portraits_company') THEN
        ALTER TABLE portraits ADD CONSTRAINT fk_portraits_company 
            FOREIGN KEY (company_id) REFERENCES companies(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_portraits_client') THEN
        ALTER TABLE portraits ADD CONSTRAINT fk_portraits_client 
            FOREIGN KEY (client_id) REFERENCES clients(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_portraits_folder') THEN
        ALTER TABLE portraits ADD CONSTRAINT fk_portraits_folder 
            FOREIGN KEY (folder_id) REFERENCES folders(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_videos_portrait') THEN
        ALTER TABLE videos ADD CONSTRAINT fk_videos_portrait 
            FOREIGN KEY (portrait_id) REFERENCES portraits(id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints 
                   WHERE constraint_name = 'fk_audit_log_actor') THEN
        ALTER TABLE audit_log ADD CONSTRAINT fk_audit_log_actor 
            FOREIGN KEY (actor_id) REFERENCES users(id);
    END IF;
END $$;

-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for tables that have updated_at columns
DO $$
BEGIN
    -- Users table trigger
    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
    CREATE TRIGGER update_users_updated_at 
        BEFORE UPDATE ON users 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Companies table trigger
    DROP TRIGGER IF EXISTS update_companies_updated_at ON companies;
    CREATE TRIGGER update_companies_updated_at 
        BEFORE UPDATE ON companies 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Storage connections table trigger
    DROP TRIGGER IF EXISTS update_storage_connections_updated_at ON storage_connections;
    CREATE TRIGGER update_storage_connections_updated_at 
        BEFORE UPDATE ON storage_connections 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Storage folders table trigger
    DROP TRIGGER IF EXISTS update_storage_folders_updated_at ON storage_folders;
    CREATE TRIGGER update_storage_folders_updated_at 
        BEFORE UPDATE ON storage_folders 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Projects table trigger
    DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
    CREATE TRIGGER update_projects_updated_at 
        BEFORE UPDATE ON projects 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Folders table trigger
    DROP TRIGGER IF EXISTS update_folders_updated_at ON folders;
    CREATE TRIGGER update_folders_updated_at 
        BEFORE UPDATE ON folders 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Clients table trigger
    DROP TRIGGER IF EXISTS update_clients_updated_at ON clients;
    CREATE TRIGGER update_clients_updated_at 
        BEFORE UPDATE ON clients 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Orders table trigger
    DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;
    CREATE TRIGGER update_orders_updated_at 
        BEFORE UPDATE ON orders 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Portraits table trigger
    DROP TRIGGER IF EXISTS update_portraits_updated_at ON portraits;
    CREATE TRIGGER update_portraits_updated_at 
        BEFORE UPDATE ON portraits 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Videos table trigger
    DROP TRIGGER IF EXISTS update_videos_updated_at ON videos;
    CREATE TRIGGER update_videos_updated_at 
        BEFORE UPDATE ON videos 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- AR content table trigger
    DROP TRIGGER IF EXISTS update_ar_content_updated_at ON ar_content;
    CREATE TRIGGER update_ar_content_updated_at 
        BEFORE UPDATE ON ar_content 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    
    -- Email queue table trigger
    DROP TRIGGER IF EXISTS update_email_queue_updated_at ON email_queue;
    CREATE TRIGGER update_email_queue_updated_at 
        BEFORE UPDATE ON email_queue 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
END $$;

-- INSERT DEFAULT DATA

-- Default admin user (password: admin123)
-- IMPORTANT: Change this password in production!
INSERT INTO users (email, hashed_password, full_name, role, is_active)
VALUES (
    'admin@vertexar.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF2PQaDi', -- admin123
    'Vertex AR Admin',
    'admin',
    true
) ON CONFLICT (email) DO NOTHING;

-- Default storage connection
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

-- Default company (if none exists)
INSERT INTO companies (name, slug, storage_type, is_active, is_default, created_at, updated_at)
VALUES (
    'Vertex AR Demo',
    'vertex-ar-demo',
    'local',
    true,
    true,
    now(),
    now()
) ON CONFLICT (slug) DO NOTHING;

-- Create views for common queries
CREATE OR REPLACE VIEW active_projects AS
SELECT p.*, c.name as company_name
FROM projects p
JOIN companies c ON p.company_id = c.id
WHERE p.status = 'active' AND c.is_active = true;

CREATE OR REPLACE VIEW expiring_subscriptions AS
SELECT 
    'projects' as entity_type,
    p.id as entity_id,
    p.name as entity_name,
    p.subscription_end,
    c.name as company_name,
    CASE 
        WHEN p.subscription_end <= now() THEN 'expired'
        WHEN p.subscription_end <= now() + interval '24 hours' THEN 'expires_today'
        WHEN p.subscription_end <= now() + interval '7 days' THEN 'expires_soon'
        ELSE 'active'
    END as urgency
FROM projects p
JOIN companies c ON p.company_id = c.id
WHERE p.subscription_end IS NOT NULL 
  AND p.subscription_end <= now() + interval '7 days'
  AND p.status = 'active'
  AND c.is_active = true;

-- Grant permissions (adjust as needed for your environment)
-- These commands assume you have a dedicated application user
-- Uncomment and modify as needed:
-- GRANT CONNECT ON DATABASE vertex_ar TO vertex_ar_app;
-- GRANT USAGE ON SCHEMA public TO vertex_ar_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO vertex_ar_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vertex_ar_app;

COMMIT;

-- Migration completed successfully
-- Database is now ready for the Vertex AR B2B Platform
-- 
-- Next steps:
-- 1. Update application configuration with database connection details
-- 2. Run the application to verify all models work correctly
-- 3. Change the default admin password
-- 4. Configure storage providers as needed
-- 5. Set up proper database user permissions in production