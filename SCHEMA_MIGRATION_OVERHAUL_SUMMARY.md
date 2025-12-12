# Schema Migration Overhaul Summary

## Overview
This document summarizes the major schema migration overhaul implemented on December 23, 2025, which transforms the Vertex AR B2B Platform from a portrait-centric architecture to an AR Content-centric architecture.

## Migration Files Created
- **Alembic Migration**: `alembic/versions/20251223_schema_migration_overhaul.py`
- **Updated SQL**: `migrations/001_initial_complete_migration.sql`
- **Documentation**: Updated `MIGRATION_DOCUMENTATION.md`

## Key Changes

### 1. Legacy Table Removal
- **`portraits`** table completely removed
- **`orders`** table completely removed
- All dependent foreign keys, indexes, and constraints dropped

### 2. Videos Table Transformation
- **Foreign Key Change**: `portrait_id` → `ar_content_id`
- **Cascade Delete**: Videos auto-delete when AR content deleted
- **Data Migration**: Best-effort mapping from portraits to AR content
- **Index Updates**: New indexes on `ar_content_id`

### 3. AR Content Table Finalization
- **Column Renaming**: `title` → `name` for consistency
- **New Columns Added**:
  - `video_path` (VARCHAR(500))
  - `video_url` (VARCHAR(500))
  - `qr_code_url` (VARCHAR(500))
  - `preview_url` (VARCHAR(500))
  - `content_metadata` (JSONB)
- **Constraints**: Unique constraint on `unique_id`
- **Performance Indexes**:
  - `ix_ar_content_company_project` on `(company_id, project_id)`
  - `ix_ar_content_created_at` on `created_at`

### 4. Schema Simplification
- **Central Entity**: `ar_content` is now the primary content entity
- **Clean Hierarchy**: Company → Project → AR Content → Videos
- **Reduced Complexity**: Eliminated portrait/order dependencies

## Data Migration Strategy

### Migration Logic
1. **Videos Table**: 
   - Add `ar_content_id` column
   - Attempt to map existing portrait data to AR content
   - Set `ar_content_id = NULL` where mapping fails
   - Drop `portrait_id` column
   - Create new foreign key constraint

2. **AR Content Table**:
   - Rename `title` → `name` if needed
   - Add new columns with appropriate defaults
   - Migrate data from existing URLs to new standardized columns
   - Create performance indexes

3. **Table Removal**:
   - Drop indexes first
   - Drop foreign key constraints
   - Drop tables (portraits, orders)

### Rollback Considerations
- **Schema Reversion**: Possible but with data loss
- **Legacy Recreation**: Basic table structures recreated
- **Data Recovery**: Manual intervention required

## Fresh Install Changes

### SQL Migration Updates
- **Removed**: All references to `portraits` and `orders` tables
- **Updated**: `videos` table references `ar_content.id`
- **Finalized**: `ar_content` table with complete schema
- **Optimized**: Indexes for AR Content-centric queries

### Default Data
- Admin user creation preserved
- Default storage connection preserved
- Default company and project creation preserved

## Model Updates

### Video Model
- **Fixed**: ForeignKey reference from `ar_contents.id` to `ar_content.id`
- **Maintained**: Backward compatibility with legacy columns
- **Relationship**: Proper relationship to ARContent model

### AR Content Model
- **Already Updated**: Model already reflects final schema
- **Consistent**: Column names match database schema

## Testing Recommendations

### Pre-Migration
1. **Backup Database**: Full database backup required
2. **Test Environment**: Run in staging first
3. **Data Assessment**: Review existing portrait/order data
4. **Application Check**: Verify no code dependencies on removed tables

### Post-Migration
1. **Schema Validation**: Verify all tables created correctly
2. **Data Integrity**: Check AR content and video relationships
3. **Application Testing**: Test all AR content functionality
4. **Performance Verify**: Confirm new indexes improve queries

## Acceptance Criteria Met

✅ **Alembic Migration**: `alembic upgrade head` removes legacy tables and creates new schema  
✅ **Fresh Install**: SQL snapshot creates new schema without legacy tables  
✅ **Documentation**: Migration documentation updated with overhaul details  
✅ **Rollback Logic**: `alembic downgrade -1` reverts structural changes  
✅ **Data Migration**: Best-effort migration of existing data  
✅ **Index Optimization**: Performance indexes for AR Content queries  
✅ **Model Consistency**: Python models updated to match schema  

## Operational Notes

### Deployment
1. **Schedule Maintenance**: Database will be unavailable during migration
2. **Backup Required**: Mandatory backup before migration
3. **Monitor Progress**: Watch migration logs for errors
4. **Validate Post-Migration**: Verify application functionality

### Performance Impact
- **Improved Queries**: AR Content queries optimized with new indexes
- **Reduced Complexity**: Simpler schema improves join performance
- **Cascade Deletes**: Automatic cleanup of related videos

### Future Considerations
- **Data Recovery**: Some legacy data relationships not recoverable
- **Application Updates**: Code may need updates for AR Content model
- **API Changes**: Endpoints referencing portraits/orders need updates

## Files Modified

### Database
- `alembic/versions/20251223_schema_migration_overhaul.py` (new)
- `migrations/001_initial_complete_migration.sql` (updated)
- `app/models/video.py` (fixed ForeignKey reference)

### Documentation
- `MIGRATION_DOCUMENTATION.md` (updated with overhaul details)
- `SCHEMA_MIGRATION_OVERHAUL_SUMMARY.md` (this file)

## Migration Commands

### Upgrade
```bash
# Alembic upgrade
alembic upgrade head

# Fresh install
psql -d vertex_ar -f migrations/001_initial_complete_migration.sql
```

### Downgrade
```bash
# Single step rollback
alembic downgrade -1

# Full rollback to pre-overhaul
alembic downgrade 20251220_rebuild_ar_content_api
```

---
**Migration Date**: 2025-12-23  
**Status**: Ready for Deployment  
**Risk Level**: Medium (data loss potential for legacy data)  
**Testing Required**: Mandatory staging environment validation