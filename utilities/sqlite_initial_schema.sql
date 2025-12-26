-- SQLite-compatible initial schema
-- This creates the complete database schema for SQLite

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    last_login_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until DATETIME
);

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    contact_email TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- AR Content table
CREATE TABLE IF NOT EXISTS ar_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    unique_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    content_type TEXT NOT NULL DEFAULT 'image',
    image_path TEXT,
    image_url TEXT,
    thumbnail_url TEXT,
    video_path TEXT,
    video_url TEXT,
    qr_code_url TEXT,
    preview_url TEXT,
    marker_path TEXT,
    marker_url TEXT,
    marker_status TEXT DEFAULT 'pending',
    marker_metadata TEXT, -- JSON string
    content_metadata TEXT, -- JSON string
    duration_years INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Videos table
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ar_content_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    video_path TEXT,
    video_url TEXT,
    thumbnail_path TEXT,
    thumbnail_url TEXT,
    preview_url TEXT,
    duration INTEGER,
    width INTEGER,
    height INTEGER,
    size_bytes INTEGER,
    mime_type TEXT,
    status TEXT NOT NULL DEFAULT 'uploaded',
    is_active BOOLEAN NOT NULL DEFAULT 0,
    rotation_type TEXT NOT NULL DEFAULT 'none',
    rotation_order INTEGER NOT NULL DEFAULT 0,
    subscription_end DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ar_content_id) REFERENCES ar_content(id)
);

-- Video Schedules table
CREATE TABLE IF NOT EXISTS video_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    rotation_type TEXT NOT NULL DEFAULT 'none',
    rotation_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (video_id) REFERENCES videos(id)
);

-- Audit Logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);
CREATE INDEX IF NOT EXISTS ix_companies_slug ON companies(slug);
CREATE INDEX IF NOT EXISTS ix_companies_id ON companies(id);
CREATE INDEX IF NOT EXISTS ix_projects_company_id ON projects(company_id);
CREATE INDEX IF NOT EXISTS ix_projects_slug ON projects(slug);
CREATE INDEX IF NOT EXISTS ix_projects_id ON projects(id);
CREATE INDEX IF NOT EXISTS ix_ar_content_company_id ON ar_content(company_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_project_id ON ar_content(project_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_unique_id ON ar_content(unique_id);
CREATE INDEX IF NOT EXISTS ix_ar_content_status ON ar_content(status);
CREATE INDEX IF NOT EXISTS ix_ar_content_created_at ON ar_content(created_at);
CREATE INDEX IF NOT EXISTS ix_ar_content_id ON ar_content(id);
CREATE INDEX IF NOT EXISTS ix_videos_ar_content_id ON videos(ar_content_id);
CREATE INDEX IF NOT EXISTS ix_videos_id ON videos(id);
CREATE INDEX IF NOT EXISTS ix_video_schedules_video_id ON video_schedules(video_id);
CREATE INDEX IF NOT EXISTS ix_video_schedules_id ON video_schedules(id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_id ON audit_logs(id);