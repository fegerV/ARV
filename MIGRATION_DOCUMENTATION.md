# PostgreSQL Initial Migration Documentation

## Overview

This document describes the complete PostgreSQL migration for the Vertex AR B2B Platform. The migration creates all necessary tables, relationships, indexes, and default data to support a fully functional AR content management system.

## Migration Files

### 1. Alembic Migration
- **File**: `alembic/versions/20251218_initial_complete_migration.py`
- **Type**: Alembic Python migration
- **Usage**: `alembic upgrade head`

### 2. Raw SQL Migration
- **File**: `migrations/001_initial_complete_migration.sql`
- **Type**: PostgreSQL SQL script
- **Usage**: `psql -d vertex_ar -f migrations/001_initial_complete_migration.sql`

## Database Schema

### Core Tables

#### 1. Users (`users`)
Authentication and user management table.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `email` (VARCHAR(255) UNIQUE NOT NULL)
- `hashed_password` (VARCHAR(255) NOT NULL)
- `full_name` (VARCHAR(255) NOT NULL)
- `role` (ENUM: admin, manager, viewer)
- `is_active` (BOOLEAN DEFAULT true)
- `login_attempts` (INTEGER DEFAULT 0)
- `locked_until` (TIMESTAMPTZ)

**Indexes:**
- `ix_users_email` (UNIQUE)
- `ix_users_role`
- `ix_users_is_active`
- `ix_users_created_at`

#### 2. Companies (`companies`)
Company/organization management with storage configuration.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `name` (VARCHAR(255) UNIQUE NOT NULL)
- `slug` (VARCHAR(255) UNIQUE NOT NULL)
- `storage_type` (VARCHAR(50) DEFAULT 'local')
- `yandex_disk_folder_id` (VARCHAR(255))
- `content_types` (VARCHAR(255)) - Comma-separated
- `backup_provider` (VARCHAR(50))
- `backup_remote_path` (VARCHAR(500))
- `storage_quota_gb` (INTEGER DEFAULT 10)
- `is_active` (BOOLEAN DEFAULT true)

**Relationships:**
- `storage_connection_id` → `storage_connections.id`

**Indexes:**
- `ix_companies_name` (UNIQUE)
- `ix_companies_slug` (UNIQUE)
- `ix_companies_storage_type`
- `ix_companies_is_active`

#### 3. Projects (`projects`)
Project management within companies.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `company_id` (INTEGER NOT NULL)
- `name` (VARCHAR(255) NOT NULL)
- `slug` (VARCHAR(255) NOT NULL)
- `subscription_end` (TIMESTAMP)
- `lifecycle_status` (VARCHAR(50) DEFAULT 'active')
- `status` (VARCHAR(50) DEFAULT 'active')

**Notification Tracking:**
- `notified_7d` (BOOLEAN DEFAULT false)
- `notified_24h` (BOOLEAN DEFAULT false)
- `notified_expired` (BOOLEAN DEFAULT false)

**Relationships:**
- `company_id` → `companies.id`

**Indexes:**
- `ux_projects_company_slug` (UNIQUE on company_id, slug)
- `ix_projects_company_id`
- `ix_projects_status`
- `ix_projects_subscription_end`

### Content Hierarchy

#### 4. Folders (`folders`)
Hierarchical folder organization within projects.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `project_id` (INTEGER NOT NULL)
- `name` (VARCHAR(255) NOT NULL)
- `parent_id` (INTEGER) - Self-referencing
- `folder_path` (VARCHAR(500))
- `is_active` (VARCHAR(50) DEFAULT 'active')

**Relationships:**
- `project_id` → `projects.id`
- `parent_id` → `folders.id` (self-referencing)

#### 5. Clients (`clients`)
Client management for companies.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `company_id` (INTEGER NOT NULL)
- `name` (VARCHAR(255) NOT NULL)
- `phone` (VARCHAR(50))
- `email` (VARCHAR(255))
- `address` (VARCHAR(500))

**Relationships:**
- `company_id` → `companies.id`

#### 6. Orders (`orders`)
Order management with subscription tracking.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `company_id` (INTEGER NOT NULL)
- `client_id` (INTEGER)
- `order_number` (VARCHAR(100) UNIQUE NOT NULL)
- `content_type` (VARCHAR(100) NOT NULL)
- `status` (VARCHAR(50) DEFAULT 'pending')
- `payment_status` (VARCHAR(50) DEFAULT 'unpaid')
- `amount` (DECIMAL(10,2) NOT NULL)
- `subscription_end` (TIMESTAMP)

**Relationships:**
- `company_id` → `companies.id`
- `client_id` → `clients.id`

#### 7. Portraits (`portraits`)
AR portrait content with lifecycle management.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `unique_id` (UUID UNIQUE NOT NULL)
- `company_id` (INTEGER NOT NULL)
- `client_id` (INTEGER)
- `folder_id` (INTEGER)
- `file_path` (VARCHAR(500) NOT NULL)
- `public_url` (VARCHAR(500))
- `status` (VARCHAR(50) DEFAULT 'active')
- `subscription_end` (TIMESTAMP)
- `lifecycle_status` (VARCHAR(50) DEFAULT 'active')

**Notification Tracking:**
- `notified_7d` (BOOLEAN DEFAULT false)
- `notified_24h` (BOOLEAN DEFAULT false)
- `notified_expired` (BOOLEAN DEFAULT false)

**MindAR Integration:**
- `marker_path` (VARCHAR(500))
- `marker_url` (VARCHAR(500))
- `marker_status` (VARCHAR(50) DEFAULT 'pending')

**Relationships:**
- `company_id` → `companies.id`
- `client_id` → `clients.id`
- `folder_id` → `folders.id`

#### 8. Videos (`videos`)
Video content attached to portraits.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `portrait_id` (INTEGER NOT NULL)
- `file_path` (VARCHAR(500) NOT NULL)
- `public_url` (VARCHAR(500))
- `status` (VARCHAR(50) DEFAULT 'active')
- `is_active` (BOOLEAN DEFAULT true)
- `rotation_type` (VARCHAR(50))

**Scheduling:**
- `schedule_start` (TIMESTAMP)
- `schedule_end` (TIMESTAMP)
- `rotation_order` (INTEGER DEFAULT 0)

**Video Metadata:**
- `title` (VARCHAR(255))
- `duration` (DECIMAL(10,3))
- `width` (INTEGER)
- `height` (INTEGER)
- `size_bytes` (INTEGER)

**Relationships:**
- `portrait_id` → `portraits.id`

### Storage and Configuration

#### 9. Storage Connections (`storage_connections`)
Storage provider configurations.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `name` (VARCHAR(255) UNIQUE NOT NULL)
- `provider` (VARCHAR(50) NOT NULL) - 'local_disk', 'minio', 'yandex_disk'
- `credentials` (JSONB DEFAULT '{}')
- `base_path` (VARCHAR(500))
- `is_default` (BOOLEAN DEFAULT false)
- `is_active` (BOOLEAN DEFAULT true)

#### 10. Storage Folders (`storage_folders`)
Physical storage folder tracking.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `company_id` (INTEGER NOT NULL)
- `name` (VARCHAR(255) NOT NULL)
- `path` (VARCHAR(500) NOT NULL)
- `folder_type` (VARCHAR(50)) - 'portraits', 'videos', 'markers', 'custom'
- `files_count` (INTEGER DEFAULT 0)
- `total_size_bytes` (BIGINT DEFAULT 0)

**Relationships:**
- `company_id` → `companies.id`

### Email and Notifications

#### 11. Email Queue (`email_queue`)
Email processing queue with retry logic.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `recipient_to` (VARCHAR(255) NOT NULL)
- `subject` (VARCHAR(500) NOT NULL)
- `body` (TEXT NOT NULL)
- `html` (TEXT)
- `template_id` (VARCHAR(100))
- `variables` (JSONB DEFAULT '{}')
- `status` (VARCHAR(50) DEFAULT 'pending')
- `attempts` (INTEGER DEFAULT 0)
- `max_attempts` (INTEGER DEFAULT 3)
- `priority` (INTEGER DEFAULT 5) - 1-10, lower = higher priority
- `scheduled_at` (TIMESTAMP)

**Error Handling:**
- `last_error` (TEXT)

#### 12. Notifications (`notifications`)
Multi-channel notification system.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `company_id` (INTEGER)
- `type` (VARCHAR(50) NOT NULL) - 'email', 'telegram', 'system', 'sms'
- `priority` (VARCHAR(50) DEFAULT 'normal')
- `subject` (VARCHAR(500))
- `message` (TEXT)

**Delivery Tracking:**
- `email_sent` (BOOLEAN DEFAULT false)
- `telegram_sent` (BOOLEAN DEFAULT false)
- `email_error` (TEXT)
- `telegram_error` (TEXT)

**Metadata:**
- `event_data` (JSONB DEFAULT '{}')
- `group_id` (VARCHAR(100))

**Status Tracking:**
- `status` (VARCHAR(50) DEFAULT 'pending')
- `processed_at` (TIMESTAMP)
- `read_at` (TIMESTAMP)

### Audit and Analytics

#### 13. Audit Log (`audit_log`)
Comprehensive audit trail for all operations.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `entity_type` (VARCHAR(100) NOT NULL) - 'user', 'company', 'project', etc.
- `entity_id` (INTEGER NOT NULL)
- `action` (VARCHAR(100) NOT NULL) - 'create', 'update', 'delete', 'login'
- `changes` (JSONB DEFAULT '{}') - Before/after values
- `field_name` (VARCHAR(100)) - Specific field changed

**Actor Information:**
- `actor_id` (INTEGER) → `users.id`
- `actor_email` (VARCHAR(255))
- `actor_ip` (VARCHAR(64))
- `user_agent` (TEXT)

**Context:**
- `session_id` (VARCHAR(255))
- `request_id` (VARCHAR(255))
- `created_at` (TIMESTAMP DEFAULT now())

#### 14. AR Content (`ar_content`)
Extended AR content with analytics.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `unique_id` (UUID UNIQUE NOT NULL)
- `project_id` (INTEGER NOT NULL)
- `company_id` (INTEGER NOT NULL)
- `title` (VARCHAR(255) NOT NULL)
- `description` (TEXT)

**Client Information:**
- `client_name` (VARCHAR(255))
- `client_phone` (VARCHAR(50))
- `client_email` (VARCHAR(255))

**File Paths:**
- `image_path` (VARCHAR(500) NOT NULL)
- `image_url` (VARCHAR(500))
- `thumbnail_url` (VARCHAR(500))
- `marker_path` (VARCHAR(500))
- `marker_url` (VARCHAR(500))

**Analytics:**
- `views_count` (INTEGER DEFAULT 0)
- `last_viewed_at` (TIMESTAMP)

#### 15. Video Rotation Schedules (`video_rotation_schedules`)
Automated video rotation configuration.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `ar_content_id` (INTEGER NOT NULL)
- `rotation_type` (VARCHAR(50) NOT NULL)
- `time_of_day` (TIME)
- `day_of_week` (INTEGER)
- `day_of_month` (INTEGER)
- `cron_expression` (VARCHAR(100))
- `video_sequence` (INTEGER[])
- `current_index` (INTEGER DEFAULT 0)

#### 16. AR View Sessions (`ar_view_sessions`)
Session tracking for AR content views.

**Key Fields:**
- `id` (SERIAL PRIMARY KEY)
- `ar_content_id` (INTEGER NOT NULL)
- `project_id` (INTEGER NOT NULL)
- `company_id` (INTEGER NOT NULL)
- `session_id` (UUID)

**Device and Location:**
- `user_agent` (TEXT)
- `device_type` (VARCHAR(50))
- `browser` (VARCHAR(100))
- `os` (VARCHAR(100))
- `ip_address` (VARCHAR(64))
- `country` (VARCHAR(100))
- `city` (VARCHAR(100))

**Session Data:**
- `duration_seconds` (INTEGER)
- `tracking_quality` (VARCHAR(50))
- `video_played` (BOOLEAN DEFAULT false)

## Default Data

### Default Admin User
- **Email**: admin@vertexar.com
- **Password**: admin123
- **Role**: admin
- **⚠️ IMPORTANT**: Change password in production!

### Default Storage Connection
- **Name**: default_local
- **Provider**: local_disk
- **Base Path**: /app/storage/content
- **Is Default**: true

### Default Company
- **Name**: Vertex AR Demo
- **Slug**: vertex-ar-demo
- **Storage Type**: local

## Database Views

### Active Projects View
```sql
CREATE VIEW active_projects AS
SELECT p.*, c.name as company_name
FROM projects p
JOIN companies c ON p.company_id = c.id
WHERE p.status = 'active' AND c.is_active = true;
```

### Expiring Subscriptions View
```sql
CREATE VIEW expiring_subscriptions AS
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
```

## Triggers

### Updated At Trigger
Automatically updates `updated_at` timestamps on row modifications:

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';
```

Applied to all tables with `updated_at` columns.

## Indexes

### Performance Indexes
- All foreign keys have corresponding indexes
- Frequently queried fields (status, created_at, company_id) are indexed
- Unique constraints on email, slugs, and order numbers
- Composite indexes for common query patterns

### Full-Text Search
Ready for PostgreSQL full-text search implementation on:
- `companies.name`
- `projects.name` and `projects.description`
- `clients.name`
- `portraits` metadata fields

## Security Considerations

### Row-Level Security
Ready for RLS implementation on:
- `companies` - Users can only see their company
- `projects` - Company-based access control
- `portraits` - Company and project-based access

### Default Permissions
The migration includes commented GRANT statements for setting up proper database user permissions in production.

## Migration Process

### Using Alembic (Recommended)
```bash
# Upgrade to latest migration
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history

# Downgrade if needed
alembic downgrade -1
```

### Using Raw SQL
```bash
# Execute migration
psql -h localhost -U vertex_ar -d vertex_ar -f migrations/001_initial_complete_migration.sql

# Verify tables were created
psql -h localhost -U vertex_ar -d vertex_ar -c "\dt"
```

## Validation

### Post-Migration Checks
```sql
-- Check table counts
SELECT 
    schemaname,
    tablename,
    n_tup_ins as "rows inserted"
FROM pg_stat_user_tables 
ORDER BY tablename;

-- Verify foreign key constraints
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';

-- Verify indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Ensure database user has CREATE, ALTER, and INDEX permissions
   - Run migrations as superuser or with appropriate privileges

2. **Foreign Key Conflicts**
   - Ensure tables are created in correct order
   - Check for existing data that violates constraints

3. **UUID Extension**
   - Migration enables `uuid-ossp` extension automatically
   - Requires superuser privileges in some PostgreSQL installations

4. **Enum Type Conflicts**
   - Migration uses `DO $$ BEGIN ... EXCEPTION ... END $$` blocks
   - Handles existing enum types gracefully

### Rollback Procedure

#### Alembic Rollback
```bash
alembic downgrade -1
```

#### SQL Rollback
```sql
-- Drop all tables in reverse order
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS email_queue CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS ar_view_sessions CASCADE;
DROP TABLE IF EXISTS video_rotation_schedules CASCADE;
DROP TABLE IF EXISTS ar_content CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS portraits CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS folders CASCADE;
DROP TABLE IF EXISTS storage_folders CASCADE;
DROP TABLE IF EXISTS storage_connections CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop custom types
DROP TYPE IF EXISTS user_role;
DROP TYPE IF EXISTS notification_type;
```

## Performance Considerations

### Expected Table Sizes
- **users**: < 1,000 rows
- **companies**: < 10,000 rows
- **projects**: < 100,000 rows
- **portraits**: < 1,000,000 rows
- **videos**: < 5,000,000 rows
- **audit_log**: High write volume, consider partitioning

### Partitioning Recommendations
Consider table partitioning for:
- `audit_log` (by date)
- `ar_view_sessions` (by date)
- `email_queue` (by status/date)

### Vacuum and Analyze
Run after initial data load:
```sql
VACUUM ANALYZE;
```

## Next Steps

1. **Application Configuration**
   - Update database connection strings
   - Configure ORM models
   - Test all model relationships

2. **Security Hardening**
   - Set up proper database users
   - Configure row-level security
   - Enable audit logging

3. **Performance Tuning**
   - Monitor query performance
   - Add additional indexes as needed
   - Consider connection pooling

4. **Backup Strategy**
   - Set up regular database backups
   - Test restore procedures
   - Configure point-in-time recovery

5. **Monitoring**
   - Set up database monitoring
   - Configure alerting for critical metrics
   - Monitor table growth

## Support

For questions or issues with this migration:
1. Check the application logs for specific error messages
2. Verify PostgreSQL version compatibility (12+)
3. Ensure proper database permissions
4. Review the troubleshooting section above

---

**Migration Version**: 20251218_initial_complete_migration
**Compatible PostgreSQL Versions**: 12+
**Last Updated**: 2025-12-18