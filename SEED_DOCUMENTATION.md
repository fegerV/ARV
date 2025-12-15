# Database Seed Documentation

This document describes the database seeding functionality that creates an initial admin user and default company.

## Overview

The Vertex AR platform includes automated database seeding to initialize the system with:

- **Admin User**: A default administrator account for initial system access
- **Default Company**: A default company "Vertex AR" for organizing projects and content

## Implementation

Two approaches are provided for database seeding:

### 1. Alembic Migration (Recommended)

**File**: `alembic/versions/20250623_1000_a1b2c3d4e5f6_seed_initial_data.py`

This migration runs automatically as part of the standard migration process:

```bash
# Run all migrations including seed
alembic upgrade head
```

**Features**:
- ✅ Integrated with standard migration workflow
- ✅ Can be rolled back with `alembic downgrade -1`
- ✅ Checks for existing data before creating
- ✅ Uses secure password hashing with bcrypt
- ✅ Atomic operations with proper error handling

### 2. Standalone Python Script

**File**: `scripts/seed_db.py`

This script can be run independently or integrated into Docker startup:

```bash
# Run seed script directly
python scripts/seed_db.py

# Or via Docker (automatically called by entrypoint.sh)
docker-compose up app
```

**Features**:
- ✅ Async/await implementation for performance
- ✅ Detailed logging and error reporting
- ✅ Safe - checks for existing data
- ✅ Can be called multiple times safely

## Seeded Data

### Admin User

| Field | Value |
|-------|-------|
| **Email** | `admin@vertex.local` |
| **Password** | `admin123` (hashed with bcrypt) |
| **Full Name** | `System Administrator` |
| **Role** | `admin` |
| **Active** | `true` |

### Default Company

| Field | Value |
|-------|-------|
| **Name** | `Vertex AR` |
| **Slug** | `vertex-ar` |
| **Contact Email** | `admin@vertex.local` |
| **Status** | `active` |

## Docker Integration

The seeding is automatically integrated into the Docker startup process:

1. **entrypoint.sh** runs `alembic upgrade head`
2. **entrypoint.sh** then runs `python scripts/seed_db.py`
3. Application starts after both complete

This ensures the database is always properly initialized when containers start.

## Testing

A test script is provided to validate the seeded data:

```bash
# Test that seed data was created correctly
python scripts/test_seed.py
```

The test script verifies:
- ✅ Admin user exists with correct credentials
- ✅ Password can be verified with bcrypt
- ✅ Default company exists with correct details
- ✅ All data relationships are intact

## Security Considerations

### Password Hashing

- Uses `passlib.context.CryptContext` with bcrypt scheme
- Password is properly salted and hashed
- Verification uses the same secure context

### Default Credentials

⚠️ **Important**: The default credentials (`admin@vertex.local` / `admin123`) should be changed in production environments.

### Idempotency

Both seeding approaches are idempotent:
- Check for existing data before creating
- No data is overwritten if it already exists
- Safe to run multiple times

## Manual Operations

### Check if Data Exists

```sql
-- Check admin user
SELECT * FROM users WHERE email = 'admin@vertex.local';

-- Check default company  
SELECT * FROM companies WHERE name = 'Vertex AR';
```

### Manual Seeding

If you need to manually create the data:

```sql
-- Create admin user (password already hashed)
INSERT INTO users (email, hashed_password, full_name, role, is_active, created_at, updated_at)
VALUES (
    'admin@vertex.local',
    '$2b$12$...', -- bcrypt hash of 'admin123'
    'System Administrator',
    'admin',
    true,
    NOW(),
    NOW()
);

-- Create default company
INSERT INTO companies (name, slug, contact_email, status, created_at, updated_at)
VALUES (
    'Vertex AR',
    'vertex-ar',
    'admin@vertex.local',
    'active',
    NOW(),
    NOW()
);
```

### Rollback Migration

```bash
# Remove seeded data
alembic downgrade -1
```

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and accessible
2. **Migration Conflicts**: Run `alembic current` to check migration status
3. **Permission Errors**: Ensure the database user has INSERT permissions
4. **Existing Data**: Scripts will skip creation if data already exists

### Debug Commands

```bash
# Check migration status
alembic current
alembic history

# Test database connection
python -c "from app.core.database import engine; print('DB OK')"

# Run seed with verbose output
python scripts/seed_db.py

# Test seeded data
python scripts/test_seed.py
```

## Integration Points

### New User Registration

When implementing user registration, ensure:
- Email uniqueness validation
- Password strength requirements
- Role assignment based on business logic

### Company Management

When implementing company management:
- Company slug uniqueness
- Proper status management
- User-company relationships

### Security Auditing

Consider adding:
- Audit logs for admin actions
- Password change requirements
- Session management for admin users