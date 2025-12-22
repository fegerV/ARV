-- Create basic tables for the application

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL,
    email VARCHAR NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    UNIQUE (email)
);

-- Create companies table
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id)
);

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    company_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Create videos table
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER NOT NULL,
    ar_content_id INTEGER NOT NULL,
    filename VARCHAR(255) NOT NULL,
    video_path VARCHAR(500),
    video_url VARCHAR(500),
    thumbnail_path VARCHAR(500),
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
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (ar_content_id) REFERENCES ar_content(id)
);

-- Add foreign key constraints to ar_content table
ALTER TABLE ar_content ADD CONSTRAINT IF NOT EXISTS fk_ar_content_company FOREIGN KEY (company_id) REFERENCES companies(id);
ALTER TABLE ar_content ADD CONSTRAINT IF NOT EXISTS fk_ar_content_project FOREIGN KEY (project_id) REFERENCES projects(id);
ALTER TABLE ar_content ADD CONSTRAINT IF NOT EXISTS fk_ar_content_active_video FOREIGN KEY (active_video_id) REFERENCES videos(id);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);
CREATE INDEX IF NOT EXISTS ix_companies_id ON companies (id);
CREATE INDEX IF NOT EXISTS ix_projects_id ON projects (id);
CREATE INDEX IF NOT EXISTS ix_projects_company_id ON projects (company_id);
CREATE INDEX IF NOT EXISTS ix_project_company_name ON projects (company_id, name);
CREATE INDEX IF NOT EXISTS ix_videos_id ON videos (id);
CREATE INDEX IF NOT EXISTS ix_videos_ar_content_id ON videos (ar_content_id);