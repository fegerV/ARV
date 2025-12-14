"""Simplify database schema - Remove storage complexity and enhance AR content

This migration implements a major schema simplification:
- Drops storage_connections and storage_folders tables (moving to local-only storage)
- Removes storage-related columns from companies table
- Adds customer and order management fields to ar_content table
- Adds is_active flag to videos table for better content management
- Creates ENUM types for status fields (content_status, company_status)

Revision ID: 20251226_simplify_db_schema
Revises: 20251224_video_scheduling_features
Create Date: 2025-12-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251226_simplify_db_schema'
down_revision = '20251224_video_scheduling_features'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check which tables exist
    existing_tables = inspector.get_table_names()
    
    # 1. CREATE ENUM TYPES FIRST
    # Create content_status enum
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE content_status AS ENUM ('pending', 'active', 'archived');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create company_status enum
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE company_status AS ENUM ('active', 'inactive');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # 2. MODIFY COMPANIES TABLE - Remove storage-related columns
    if 'companies' in existing_tables:
        company_columns = [col['name'] for col in inspector.get_columns('companies')]
        
        # Drop foreign key constraint to storage_connections first
        if 'storage_connection_id' in company_columns:
            storage_fks = [fk for fk in inspector.get_foreign_keys('companies') 
                          if fk['constrained_columns'] == ['storage_connection_id']]
            for fk in storage_fks:
                op.drop_constraint(fk['name'], 'companies', type_='foreignkey')
        
        # Drop storage-related columns
        storage_columns_to_remove = [
            'storage_connection_id',
            'storage_path',
            'storage_provider', 
            'yandex_disk_folder_id',
            'backup_provider',
            'backup_remote_path'
        ]
        
        for col in storage_columns_to_remove:
            if col in company_columns:
                op.drop_column('companies', col)
        
        # Add status column if it doesn't exist (using the new enum)
        if 'status' not in company_columns:
            op.add_column('companies', sa.Column('status', postgresql.ENUM('active', 'inactive', name='company_status', create_type=False), nullable=True, server_default='active'))
        
        # Update existing companies to have active status
        conn.execute(sa.text("""
            UPDATE companies 
            SET status = 'active' 
            WHERE status IS NULL
        """))
        
        # Make status column not nullable
        op.alter_column('companies', 'status', nullable=False)
    
    # 3. ENHANCE AR_CONTENT TABLE - Add customer and order management fields
    if 'ar_content' in existing_tables:
        ar_content_columns = [col['name'] for col in inspector.get_columns('ar_content')]
        
        # Add new columns for customer and order management
        new_columns = [
            ('order_number', sa.String(length=100), True),
            ('customer_name', sa.String(length=255), True),
            ('customer_phone', sa.String(length=50), True),
            ('customer_email', sa.String(length=255), True),
            ('duration_years', sa.Integer(), False, 1),
            ('views_count', sa.Integer(), False, 0),
            ('status', postgresql.ENUM('pending', 'active', 'archived', name='content_status', create_type=False), True, 'pending'),
            ('metadata', postgresql.JSONB(astext_type=sa.Text()), True, "'{}'::jsonb")
        ]
        
        for col_name, col_type, nullable, *default in new_columns:
            if col_name not in ar_content_columns:
                if default:
                    op.add_column('ar_content', sa.Column(col_name, col_type, nullable=nullable, server_default=default[0]))
                else:
                    op.add_column('ar_content', sa.Column(col_name, col_type, nullable=nullable))
        
        # Create unique constraint on order_number within company scope
        existing_constraints = [c['name'] for c in inspector.get_unique_constraints('ar_content')]
        if 'uq_ar_content_company_order_number' not in existing_constraints:
            op.create_unique_constraint(
                'uq_ar_content_company_order_number',
                'ar_content',
                ['company_id', 'order_number']
            )
        
        # Create index for order_number lookups
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('ar_content')]
        if 'ix_ar_content_order_number' not in existing_indexes:
            op.create_index('ix_ar_content_order_number', 'ar_content', ['order_number'])
        
        # Update existing records to have default values
        conn.execute(sa.text("""
            UPDATE ar_content 
            SET 
                order_number = COALESCE(order_number, 'ORD-' || LPAD(id::text, 6, '0')),
                views_count = COALESCE(views_count, 0),
                duration_years = COALESCE(duration_years, 1),
                status = COALESCE(status, 'pending'),
                metadata = COALESCE(metadata, '{}'::jsonb)
            WHERE order_number IS NULL OR views_count IS NULL OR duration_years IS NULL OR status IS NULL OR metadata IS NULL
        """))
    
    # 4. UPDATE VIDEOS TABLE - Add proper is_active flag
    if 'videos' in existing_tables:
        video_columns = [col['name'] for col in inspector.get_columns('videos')]
        
        # Ensure is_active column exists and is properly configured
        if 'is_active' not in video_columns:
            op.add_column('videos', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'))
        else:
            # Update existing is_active to default to false for better control
            conn.execute(sa.text("""
                UPDATE videos 
                SET is_active = false 
                WHERE is_active IS NULL
            """))
            op.alter_column('videos', 'is_active', nullable=False, server_default='false')
    
    # 5. DROP STORAGE TABLES
    # Drop storage_folders table first (depends on companies)
    if 'storage_folders' in existing_tables:
        # Drop foreign key constraints first
        folder_fks = [fk['name'] for fk in inspector.get_foreign_keys('storage_folders')]
        for fk_name in folder_fks:
            op.drop_constraint(fk_name, 'storage_folders', type_='foreignkey')
        
        # Drop indexes
        folder_indexes = [idx['name'] for idx in inspector.get_indexes('storage_folders')]
        for idx_name in folder_indexes:
            op.drop_index(idx_name, table_name='storage_folders')
        
        # Drop the table
        op.drop_table('storage_folders')
    
    # Drop storage_connections table
    if 'storage_connections' in existing_tables:
        # Drop foreign key constraints first
        connection_fks = [fk['name'] for fk in inspector.get_foreign_keys('storage_connections')]
        for fk_name in connection_fks:
            op.drop_constraint(fk_name, 'storage_connections', type_='foreignkey')
        
        # Drop indexes
        connection_indexes = [idx['name'] for idx in inspector.get_indexes('storage_connections')]
        for idx_name in connection_indexes:
            op.drop_index(idx_name, table_name='storage_connections')
        
        # Drop the table
        op.drop_table('storage_connections')
    
    # 6. UPDATE SEQUENCES AND STATISTICS
    conn.execute(sa.text("ANALYZE"))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    existing_tables = inspector.get_table_names()
    
    # 1. RECREATE STORAGE TABLES
    # Recreate storage_connections table
    if 'storage_connections' not in existing_tables:
        op.create_table('storage_connections',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('provider', sa.String(length=50), nullable=False, default='local_disk'),
            sa.Column('base_path', sa.String(length=500), nullable=False),
            sa.Column('is_default', sa.Boolean(), nullable=True, default=False),
            sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
            sa.Column('last_tested_at', sa.DateTime(), nullable=True),
            sa.Column('test_status', sa.String(length=50), nullable=True),
            sa.Column('test_error', sa.Text(), nullable=True),
            sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default='{}'),
            sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.text('now()')),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        
        # Add indexes
        op.create_index('ix_storage_connections_name', 'storage_connections', ['name'])
        op.create_index('ix_storage_connections_provider', 'storage_connections', ['provider'])
        op.create_index('ix_storage_connections_is_active', 'storage_connections', ['is_active'])
    
    # Recreate storage_folders table
    if 'storage_folders' not in existing_tables:
        op.create_table('storage_folders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('path', sa.String(length=500), nullable=False),
            sa.Column('folder_type', sa.String(length=50), nullable=True),
            sa.Column('files_count', sa.Integer(), nullable=True, default=0),
            sa.Column('total_size_bytes', sa.BigInteger(), nullable=True, default=0),
            sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.text('now()')),
            sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Add indexes
        op.create_index('ix_storage_folders_company_id', 'storage_folders', ['company_id'])
        op.create_index('ix_storage_folders_folder_type', 'storage_folders', ['folder_type'])
    
    # 2. RESTORE COMPANY STORAGE COLUMNS
    if 'companies' in existing_tables:
        company_columns = [col['name'] for col in inspector.get_columns('companies')]
        
        # Add back storage-related columns
        storage_columns_to_add = [
            ('storage_connection_id', sa.Integer(), True),
            ('storage_path', sa.String(length=500), True),
        ]
        
        for col_name, col_type, nullable in storage_columns_to_add:
            if col_name not in company_columns:
                op.add_column('companies', sa.Column(col_name, col_type, nullable=nullable))
        
        # Recreate foreign key to storage_connections
        if 'storage_connections' in existing_tables:
            op.create_foreign_key(
                'fk_companies_storage_connection_id',
                'companies',
                'storage_connections',
                ['storage_connection_id'],
                ['id']
            )
        
        # Drop status column if it exists
        if 'status' in company_columns:
            op.drop_column('companies', 'status')
    
    # 3. REMOVE AR_CONTENT ENHANCEMENTS
    if 'ar_content' in existing_tables:
        ar_content_columns = [col['name'] for col in inspector.get_columns('ar_content')]
        
        # Drop new columns
        new_columns = [
            'order_number', 'customer_name', 'customer_phone', 
            'customer_email', 'duration_years', 'views_count', 
            'status', 'metadata'
        ]
        
        for col in new_columns:
            if col in ar_content_columns:
                op.drop_column('ar_content', col)
        
        # Drop unique constraint and index if they exist
        existing_constraints = [c['name'] for c in inspector.get_unique_constraints('ar_content')]
        if 'uq_ar_content_company_order_number' in existing_constraints:
            op.drop_constraint('uq_ar_content_company_order_number', 'ar_content', type_='unique')
        
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('ar_content')]
        if 'ix_ar_content_order_number' in existing_indexes:
            op.drop_index('ix_ar_content_order_number', table_name='ar_content')
    
    # 4. REVERT VIDEOS IS_ACTIVE CHANGES
    if 'videos' in existing_tables:
        video_columns = [col['name'] for col in inspector.get_columns('videos')]
        if 'is_active' in video_columns:
            op.drop_column('videos', 'is_active')
    
    # 5. DROP ENUM TYPES
    conn.execute(sa.text("DROP TYPE IF EXISTS content_status"))
    conn.execute(sa.text("DROP TYPE IF EXISTS company_status"))
    
    # 6. UPDATE SEQUENCES AND STATISTICS
    conn.execute(sa.text("ANALYZE"))