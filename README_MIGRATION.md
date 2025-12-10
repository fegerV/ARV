# PostgreSQL Migration for Vertex AR B2B Platform

## Quick Start

This migration creates a complete PostgreSQL database schema for the Vertex AR B2B Platform.

### Option 1: Using Alembic (Recommended)

```bash
# Upgrade to the latest migration
alembic upgrade head

# Check current migration status
alembic current

# View migration history
alembic history
```

### Option 2: Using Raw SQL

```bash
# Execute the SQL migration directly
psql -h localhost -U vertex_ar -d vertex_ar -f migrations/001_initial_complete_migration.sql
```

## What's Included

### Tables Created (16 total)

**Core Tables:**
- `users` - User authentication and management
- `companies` - Company/organization management
- `storage_connections` - Storage provider configurations

**Content Hierarchy:**
- `projects` - Project management within companies
- `folders` - Hierarchical folder organization
- `clients` - Client management
- `orders` - Order and subscription tracking
- `portraits` - AR portrait content
- `videos` - Video content attached to portraits

**Advanced Features:**
- `ar_content` - Extended AR content with analytics
- `video_rotation_schedules` - Automated video rotation
- `ar_view_sessions` - Session tracking and analytics
- `notifications` - Multi-channel notification system
- `email_queue` - Email processing with retry logic
- `audit_log` - Comprehensive audit trail

### Default Data Created

- **Admin User**: `admin@vertexar.com` / `admin123` (⚠️ CHANGE IN PRODUCTION!)
- **Default Storage**: Local disk storage at `/app/storage/content`
- **Demo Company**: Vertex AR Demo company

## Key Features

### 1. Multi-Storage Support
- Local disk storage
- MinIO S3-compatible storage
- Yandex Disk integration
- Backup providers

### 2. Subscription Management
- Project lifecycle tracking
- Automated expiry notifications
- 7-day, 24-hour, and expiry notifications
- Graceful subscription handling

### 3. Content Organization
- Hierarchical folder structure
- Company-based isolation
- Project-based grouping
- Client associations

### 4. Audit and Analytics
- Complete audit trail
- AR view session tracking
- Content analytics
- Device and location tracking

### 5. Notification System
- Multi-channel support (email, telegram, system)
- Queue-based email processing
- Retry logic with exponential backoff
- Template-based notifications

## Security Features

- Row-level security ready
- Company-based data isolation
- User role management
- Audit logging for all operations
- Secure password hashing

## Performance Optimizations

- Strategic indexing on foreign keys
- Composite indexes for common queries
- JSONB for flexible metadata storage
- Optimized for high-volume content

## Validation

All models have been tested and validated:

```bash
# Test model imports and relationships
python test_models_import.py
```

## Documentation

- **Complete Documentation**: `MIGRATION_DOCUMENTATION.md`
- **Schema Details**: Full table definitions and relationships
- **Troubleshooting Guide**: Common issues and solutions
- **Performance Guide**: Optimization recommendations

## Production Deployment

### 1. Security Checklist
- [ ] Change default admin password
- [ ] Set up proper database users
- [ ] Configure row-level security
- [ ] Enable SSL connections
- [ ] Set up backup procedures

### 2. Performance Checklist
- [ ] Configure connection pooling
- [ ] Set up monitoring
- [ ] Configure table partitioning for high-volume tables
- [ ] Optimize PostgreSQL settings
- [ ] Set up regular VACUUM/ANALYZE

### 3. Backup Strategy
- [ ] Regular database backups
- [ ] Point-in-time recovery
- [ ] Backup validation procedures
- [ ] Disaster recovery plan

## Support

For issues with the migration:

1. Check the troubleshooting section in `MIGRATION_DOCUMENTATION.md`
2. Verify PostgreSQL version (12+ required)
3. Ensure proper database permissions
4. Run the model validation script

## Migration Files

- `alembic/versions/20251218_initial_complete_migration.py` - Alembic migration
- `migrations/001_initial_complete_migration.sql` - Raw SQL migration
- `MIGRATION_DOCUMENTATION.md` - Complete documentation
- `test_models_import.py` - Model validation script

---

**Version**: 20251218_initial_complete_migration  
**Compatible**: PostgreSQL 12+  
**Status**: ✅ Tested and validated