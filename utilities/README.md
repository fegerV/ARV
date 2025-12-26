# Utilities Directory

This directory contains temporary utility scripts for debugging, testing, and maintenance tasks.

## Script Categories

### Database & Migration Scripts
- `check_migration.py` - Check migration status
- `check_and_create_tables.py` - Verify and create database tables
- `clear_migrations.py` - Clear migration history
- `fix_migration.py` - Fix migration issues
- `init_db.py` - Initialize database

### Authentication & User Management Scripts
- `check_users_and_auth.py` - Verify authentication system
- `check_and_fix_passwords.py` - Check and fix password hashes
- `reset_password.py` - Reset user passwords
- `reset_login_attempts.py` - Clear login attempts
- `update_admin_password_sha256.py` - Update admin password to SHA256
- `update_password_directly.py` - Direct password update

### Admin Management Scripts
- `check_admin.py` - Check admin user status
- `check_admin_user.py` - Verify admin user configuration
- `create_admin.py` - Create admin user
- `create_admin_test.py` - Create test admin user
- `fix_admin_password.py` - Fix admin password issues

### Database Verification Scripts
- `check_db.py` - Basic database connectivity check
- `check_hash_type.py` - Check password hash types
- `check_seed_data.py` - Verify seed data

### Testing Scripts
- `create_test_project.py` - Create test project
- `debug_server.py` - Debug server issues
- `test_ar_content_creation.py` - Test AR content creation

### Container Scripts
- `check_containers.py` - Check Docker containers

## Usage

These scripts are primarily for development and debugging purposes. They should not be used in production without proper understanding of their functionality.

## Security Notice

Some scripts contain sensitive operations like password management. Use with caution and ensure proper authorization before running.