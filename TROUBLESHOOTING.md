# Troubleshooting Guide for ARVlite

This guide addresses common issues users may encounter when setting up and using the ARVlite platform.

## Issue: "Новая Компания и проект не создается" / "No Projects Available"

### Problem Description
Users may encounter messages like:
- "You need to create a project for the selected company before you can create AR content"
- "No Projects Available"
- "Новая Компания и проект не создается"

### Root Cause Analysis
After investigation, we identified several potential causes:
1. Missing company or project in the database
2. Authentication issues (bcrypt password hashing problems)
3. Incorrect API routes being called

### Solution Steps

#### 1. Verify Database State
First, check if your database contains the necessary records:

```bash
cd ARV && python utilities/check_db.py
```

Expected output should show:
- At least 1 company (e.g., "Vertex AR")
- At least 1 project associated with a company
- 1 admin user account

#### 2. Fix Authentication Issues
If you encounter bcrypt-related errors such as:
```
ValueError: password cannot be longer than 72 bytes
```

The system has been updated to use SHA-256 hashing instead of bcrypt for compatibility.

#### 3. Verify API Endpoints
The correct API endpoints are:
- Login: `POST /api/auth/login`
- Company projects: `GET /api/projects/companies/{company_id}/projects`
- AR content creation: `POST /api/ar-content/companies/{company_id}/projects/{project_id}/ar-content/new`

#### 4. Create Missing Records
If no company exists, create one through the web interface:
1. Navigate to the Companies section
2. Click "New Company" 
3. Fill in company details

If no projects exist for a company:
1. Navigate to the Projects section
2. Select your company
3. Create a new project

## Issue: Login Failures

### Solution
Default admin credentials:
- Email: `admin@vertexar.com`
- Password: `admin123`

## Issue: AR Content Creation Fails

### Solution
Ensure:
1. A company exists in the system
2. At least one project exists for that company
3. You're logged in with appropriate permissions
4. Required files (image/video) are properly formatted

## Development Notes

### Security Changes
- Changed password hashing from bcrypt to SHA-256 for better compatibility
- Old bcrypt hashes were replaced with SHA-256 hashes during migration
- The `utilities/create_admin.py` script ensures admin user exists with correct password hash

### API Routes
Key API routes for AR content creation:
- Authentication: `/api/auth/login`
- Companies: `/api/companies/`
- Projects: `/api/projects/companies/{company_id}/projects`
- AR Content: `/api/ar-content/companies/{company_id}/projects/{project_id}/ar-content/new`

## Verification Steps

After setup, verify the system works by running:

```bash
cd ARV && python scripts/legacy/manual_testing_guide.py
```

This test verifies:
- Server connectivity
- Successful authentication
- Company and project access
- AR content creation endpoints