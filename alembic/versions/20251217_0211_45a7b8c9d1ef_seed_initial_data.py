"""seed initial data

Revision ID: 45a7b8c9d1ef
Revises: 28cd993514df
Create Date: 2025-12-17 02:11:0.0000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func
import hashlib
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '45a7b8c9d1ef'
down_revision: Union[str, None] = '28cd993514df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if admin user already exists
    connection = op.get_bind()
    
    # Check if admin user exists
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE email = :email"),
        {"email": "admin@vertex.local"}
    )
    admin_exists = result.fetchone()[0] > 0
    
    if not admin_exists:
        # Hash password using SHA-256 (consistent with existing security implementation)
        admin_password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        
        # Insert admin user
        connection.execute(
            sa.text("""
                INSERT INTO users (email, hashed_password, full_name, role, is_active, created_at, updated_at, login_attempts)
                VALUES (:email, :hashed_password, :full_name, :role, :is_active, :created_at, :updated_at, :login_attempts)
            """),
            {
                "email": "admin@vertex.local",
                "hashed_password": admin_password_hash,
                "full_name": "Admin User",
                "role": "admin",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "login_attempts": 0
            }
        )
    
    # Check if default company exists
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM companies WHERE name = :name"),
        {"name": "Vertex AR"}
    )
    company_exists = result.fetchone()[0] > 0
    
    if not company_exists:
        # Insert default company
        connection.execute(
            sa.text("""
                INSERT INTO companies (name, slug, contact_email, status, created_at, updated_at)
                VALUES (:name, :slug, :contact_email, :status, :created_at, :updated_at)
            """),
            {
                "name": "Vertex AR",
                "slug": "vertex-ar",
                "contact_email": "admin@vertex.local",
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        )


def downgrade() -> None:
    # Remove admin user
    connection = op.get_bind()
    
    # First, find the company ID to properly clean up related data
    result = connection.execute(
        sa.text("SELECT id FROM companies WHERE name = :name"),
        {"name": "Vertex AR"}
    )
    company_row = result.fetchone()
    
    if company_row:
        company_id = company_row[0]
        # Delete related projects first to avoid foreign key constraint violations
        connection.execute(
            sa.text("DELETE FROM projects WHERE company_id = :company_id"),
            {"company_id": company_id}
        )
        
        # Now delete the company
        connection.execute(
            sa.text("DELETE FROM companies WHERE id = :company_id"),
            {"company_id": company_id}
        )
    
    # Delete the admin user
    connection.execute(
        sa.text("DELETE FROM users WHERE email = :email"),
        {"email": "admin@vertex.local"}
    )