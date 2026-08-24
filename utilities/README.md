# Utilities Directory

This directory contains temporary utility scripts for debugging, testing, and maintenance tasks.

## Script Categories

### Database & Migration Scripts
- `check_and_create_tables.py` - Verify and create database tables
- `clear_migrations.py` - Clear migration history
- `init_db.py` - Initialize database

### Admin Management Scripts
- `scripts/manage_admin.py` - **Canonical** admin user management (create, reset, unlock, fix passwords)

### Database Verification Scripts
- `check_db.py` - Basic database connectivity check
- `check_hash_type.py` - Check password hash types
- `check_seed_data.py` - Verify seed data

### Testing Scripts
- `create_test_project.py` - Create test project
- `debug_server.py` - Debug server issues

### Container Scripts
- `check_containers.py` - Check Docker containers

## Canonical Admin CLI

All admin and password management operations are now handled by a single script:

```bash
python scripts/manage_admin.py create                # create or update admin password
python scripts/manage_admin.py reset                  # reset existing admin password
python scripts/manage_admin.py reset-login-attempts   # unlock all locked accounts
python scripts/manage_admin.py fix-passwords          # re-hash admin password with current scheme
```

The legacy scripts in `utilities/` and `scripts/legacy/` have been removed to avoid confusion.

## Usage

These scripts are primarily for development and debugging purposes. They should not be used in production without proper understanding of their functionality.

## Security Notice

Some scripts contain sensitive operations like password management. Use with caution and ensure proper authorization before running.