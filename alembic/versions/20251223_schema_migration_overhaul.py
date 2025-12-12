"""Schema/Migration Overhaul - Remove legacy tables and finalize AR Content schema

This migration implements the final domain changes at the database level:
- Drops legacy `portraits` and `orders` tables plus dependent FK constraints/indexes
- Alters `videos` to replace `portrait_id` with `ar_content_id` (FK to `ar_content.id`, cascade delete, reindexed)
- Finalizes `ar_content` schema with proper column names and indexes
- Migrates existing data where possible
- Updates indexes for performance optimization

Revision ID: 20251223_schema_migration_overhaul
Revises: 20251220_rebuild_ar_content_api
Create Date: 2025-12-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251223_schema_migration_overhaul'
down_revision = '20251220_rebuild_ar_content_api'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check which tables exist
    existing_tables = inspector.get_table_names()
    
    # 1. MIGRATE VIDEOS TABLE - Replace portrait_id with ar_content_id
    if 'videos' in existing_tables:
        video_columns = [col['name'] for col in inspector.get_columns('videos')]
        
        # Add ar_content_id column if it doesn't exist
        if 'ar_content_id' not in video_columns:
            op.add_column('videos', sa.Column('ar_content_id', sa.Integer(), nullable=True))
        
        # Migrate data from portrait_id to ar_content_id if portrait_id exists
        if 'portrait_id' in video_columns:
            # Attempt to migrate data: find AR content records that might correspond to portraits
            # This is a best-effort migration - some data might not be migratable
            conn.execute(sa.text("""
                -- Try to map portrait_id to ar_content_id where possible
                -- This looks for AR content with similar characteristics
                UPDATE videos v
                SET ar_content_id = ac.id
                FROM ar_content ac
                WHERE v.portrait_id IS NOT NULL
                AND ac.company_id = (
                    SELECT p.company_id FROM portraits p WHERE p.id = v.portrait_id
                )
                AND ac.project_id = (
                    SELECT COALESCE(
                        (SELECT MIN(id) FROM projects WHERE company_id = p.company_id),
                        1
                    ) FROM portraits p WHERE p.id = v.portrait_id
                )
                AND ac.id IS NOT NULL
            """))
            
            # For remaining videos with portrait_id, set ar_content_id to NULL
            # This ensures the foreign key constraint can be created
            conn.execute(sa.text("""
                UPDATE videos 
                SET ar_content_id = NULL 
                WHERE portrait_id IS NOT NULL AND ar_content_id IS NULL
            """))
            
            # Make ar_content_id not nullable after data migration
            op.alter_column('videos', 'ar_content_id', nullable=False)
            
            # Create foreign key constraint to ar_content
            op.create_foreign_key(
                'fk_videos_ar_content', 'videos', 'ar_content', 
                ['ar_content_id'], ['id'], ondelete='CASCADE'
            )
            
            # Drop the old portrait_id foreign key if it exists
            if 'fk_videos_portrait' in [fk['name'] for fk in inspector.get_foreign_keys('videos')]:
                op.drop_constraint('fk_videos_portrait', 'videos', type_='foreignkey')
            
            # Drop the old portrait_id column
            op.drop_column('videos', 'portrait_id')
            
            # Update indexes
            old_indexes = [idx['name'] for idx in inspector.get_indexes('videos')]
            if 'ix_videos_portrait_id' in old_indexes:
                op.drop_index('ix_videos_portrait_id', table_name='videos')
            
            # Create new index on ar_content_id
            op.create_index('ix_videos_ar_content_id', 'videos', ['ar_content_id'])
    
    # 2. FINALIZE AR_CONTENT TABLE SCHEMA
    if 'ar_content' in existing_tables:
        ar_content_columns = [col['name'] for col in inspector.get_columns('ar_content')]
        
        # Rename title to name if needed
        if 'title' in ar_content_columns and 'name' not in ar_content_columns:
            op.alter_column('ar_content', 'title', new_column_name='name')
        elif 'title' in ar_content_columns and 'name' in ar_content_columns:
            # Copy data from title to name, then drop title
            conn.execute(sa.text("""
                UPDATE ar_content 
                SET name = COALESCE(name, title)
                WHERE name IS NULL AND title IS NOT NULL
            """))
            op.drop_column('ar_content', 'title')
        
        # Add missing columns
        if 'video_path' not in ar_content_columns:
            op.add_column('ar_content', sa.Column('video_path', sa.String(length=500), nullable=True))
        if 'video_url' not in ar_content_columns:
            op.add_column('ar_content', sa.Column('video_url', sa.String(length=500), nullable=True))
        if 'qr_code_url' not in ar_content_columns:
            op.add_column('ar_content', sa.Column('qr_code_url', sa.String(length=500), nullable=True))
        if 'preview_url' not in ar_content_columns:
            op.add_column('ar_content', sa.Column('preview_url', sa.String(length=500), nullable=True))
        if 'content_metadata' not in ar_content_columns:
            op.add_column('ar_content', sa.Column('content_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")))
        elif 'metadata' in ar_content_columns and 'content_metadata' not in ar_content_columns:
            # Rename metadata to content_metadata for consistency
            op.alter_column('ar_content', 'metadata', new_column_name='content_metadata')
        
        # Ensure unique constraint on unique_id
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('ar_content')]
        existing_constraints = [idx['name'] for idx in inspector.get_unique_constraints('ar_content')]
        
        if 'uq_ar_content_unique_id' not in existing_constraints and 'uq_ar_content_unique_id' not in existing_indexes:
            op.create_index('uq_ar_content_unique_id', 'ar_content', ['unique_id'], unique=True)
        
        # Create performance indexes
        if 'ix_ar_content_company_project' not in existing_indexes:
            op.create_index('ix_ar_content_company_project', 'ar_content', ['company_id', 'project_id'])
        if 'ix_ar_content_created_at' not in existing_indexes:
            op.create_index('ix_ar_content_created_at', 'ar_content', ['created_at'])
        
        # Migrate data to new columns if needed
        conn.execute(sa.text("""
            -- Copy existing URLs to new standardized columns if they're empty
            UPDATE ar_content 
            SET video_url = COALESCE(video_url, 
                (SELECT v.video_url FROM videos v WHERE v.ar_content_id = ar_content.id LIMIT 1)
            )
            WHERE video_url IS NULL
            
            UPDATE ar_content 
            SET preview_url = COALESCE(preview_url, thumbnail_url)
            WHERE preview_url IS NULL AND thumbnail_url IS NOT NULL
        """))
    
    # 3. DROP LEGACY TABLES
    # Drop orders table and its indexes
    if 'orders' in existing_tables:
        # Drop indexes first
        order_indexes = [idx['name'] for idx in inspector.get_indexes('orders')]
        for idx_name in order_indexes:
            op.drop_index(idx_name, table_name='orders')
        
        # Drop foreign key constraints
        order_fks = [fk['name'] for fk in inspector.get_foreign_keys('orders')]
        for fk_name in order_fks:
            op.drop_constraint(fk_name, 'orders', type_='foreignkey')
        
        # Drop the table
        op.drop_table('orders')
    
    # Drop portraits table and its indexes
    if 'portraits' in existing_tables:
        # Drop indexes first
        portrait_indexes = [idx['name'] for idx in inspector.get_indexes('portraits')]
        for idx_name in portrait_indexes:
            op.drop_index(idx_name, table_name='portraits')
        
        # Drop foreign key constraints
        portrait_fks = [fk['name'] for fk in inspector.get_foreign_keys('portraits')]
        for fk_name in portrait_fks:
            op.drop_constraint(fk_name, 'portraits', type_='foreignkey')
        
        # Drop the table
        op.drop_table('portraits')
    
    # 4. CLEAN UP ANY ORPHANED REFERENCES
    # Remove any references to dropped tables from other tables
    if 'clients' in existing_tables:
        client_columns = [col['name'] for col in inspector.get_columns('clients')]
        # No specific cleanup needed for clients table as it's referenced elsewhere
    
    # 5. UPDATE SEQUENCES AND STATISTICS
    conn.execute(sa.text("SELECT setval(pg_get_serial_sequence('ar_content', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM ar_content"))
    conn.execute(sa.text("SELECT setval(pg_get_serial_sequence('videos', 'id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM videos"))
    conn.execute(sa.text("ANALYZE"))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    existing_tables = inspector.get_table_names()
    
    # 1. RECREATE LEGACY TABLES (Basic structure - data loss is unavoidable)
    
    # Recreate portraits table
    if 'portraits' not in existing_tables:
        op.create_table(
            'portraits',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('unique_id', postgresql.UUID(as_uuid=True), nullable=True, default=sa.text('uuid_generate_v4()')),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=True),
            sa.Column('folder_id', sa.Integer(), nullable=True),
            sa.Column('file_path', sa.String(length=500), nullable=False),
            sa.Column('public_url', sa.String(length=500), nullable=True),
            sa.Column('image_path', sa.String(length=500), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('thumbnail_path', sa.String(length=500), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=True, default='active'),
            sa.Column('subscription_end', sa.DateTime(), nullable=True),
            sa.Column('lifecycle_status', sa.String(length=50), nullable=True, default='active'),
            sa.Column('notified_7d', sa.Boolean(), nullable=True, default=False),
            sa.Column('notified_24h', sa.Boolean(), nullable=True, default=False),
            sa.Column('notified_expired', sa.Boolean(), nullable=True, default=False),
            sa.Column('marker_path', sa.String(length=500), nullable=True),
            sa.Column('marker_url', sa.String(length=500), nullable=True),
            sa.Column('marker_status', sa.String(length=50), nullable=True, default='pending'),
            sa.Column('storage_connection_id', sa.Integer(), nullable=True),
            sa.Column('storage_folder_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('unique_id', name='uq_portraits_unique_id')
        )
        
        # Add foreign key constraints
        if 'companies' in existing_tables:
            op.create_foreign_key('fk_portraits_company', 'portraits', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
        if 'clients' in existing_tables:
            op.create_foreign_key('fk_portraits_client', 'portraits', 'clients', ['client_id'], ['id'])
        if 'folders' in existing_tables:
            op.create_foreign_key('fk_portraits_folder', 'portraits', 'folders', ['folder_id'], ['id'])
        
        # Add indexes
        op.create_index('ix_portraits_unique_id', 'portraits', ['unique_id'])
        op.create_index('ix_portraits_company_id', 'portraits', ['company_id'])
        op.create_index('ix_portraits_client_id', 'portraits', ['client_id'])
        op.create_index('ix_portraits_folder_id', 'portraits', ['folder_id'])
        op.create_index('ix_portraits_status', 'portraits', ['status'])
        op.create_index('ix_portraits_created_at', 'portraits', ['created_at'])
    
    # Recreate orders table
    if 'orders' not in existing_tables:
        op.create_table(
            'orders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('client_id', sa.Integer(), nullable=True),
            sa.Column('order_number', sa.String(length=100), nullable=False),
            sa.Column('content_type', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=True, default='pending'),
            sa.Column('payment_status', sa.String(length=50), nullable=True, default='unpaid'),
            sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('currency', sa.String(length=10), nullable=True, default='USD'),
            sa.Column('subscription_end', sa.DateTime(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.text('now()')),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('order_number')
        )
        
        # Add foreign key constraints
        if 'companies' in existing_tables:
            op.create_foreign_key('fk_orders_company', 'orders', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
        if 'clients' in existing_tables:
            op.create_foreign_key('fk_orders_client', 'orders', 'clients', ['client_id'], ['id'])
        
        # Add indexes
        op.create_index('ix_orders_company_id', 'orders', ['company_id'])
        op.create_index('ix_orders_client_id', 'orders', ['client_id'])
        op.create_index('ix_orders_status', 'orders', ['status'])
        op.create_index('ix_orders_created_at', 'orders', ['created_at'])
    
    # 2. REVERT VIDEOS TABLE CHANGES
    if 'videos' in existing_tables:
        video_columns = [col['name'] for col in inspector.get_columns('videos')]
        
        # Add back portrait_id column
        if 'portrait_id' not in video_columns:
            op.add_column('videos', sa.Column('portrait_id', sa.Integer(), nullable=True))
        
        # Try to migrate data back from ar_content_id to portrait_id (best effort)
        conn.execute(sa.text("""
            -- This is a best-effort reverse migration
            -- Some data may not be recoverable
            UPDATE videos 
            SET portrait_id = NULL
            WHERE ar_content_id IS NOT NULL
        """))
        
        # Make portrait_id not nullable (this may fail if there's no data)
        try:
            op.alter_column('videos', 'portrait_id', nullable=False)
        except Exception:
            # If it fails, leave it nullable
            pass
        
        # Create foreign key to portraits if portraits table exists
        if 'portraits' in existing_tables:
            try:
                op.create_foreign_key(
                    'fk_videos_portrait', 'videos', 'portraits', 
                    ['portrait_id'], ['id'], ondelete='CASCADE'
                )
            except Exception:
                pass
        
        # Drop ar_content_id foreign key and column
        if 'ar_content_id' in video_columns:
            if 'fk_videos_ar_content' in [fk['name'] for fk in inspector.get_foreign_keys('videos')]:
                op.drop_constraint('fk_videos_ar_content', 'videos', type_='foreignkey')
            op.drop_column('videos', 'ar_content_id')
        
        # Update indexes
        op.drop_index('ix_videos_ar_content_id', table_name='videos')
        op.create_index('ix_videos_portrait_id', 'videos', ['portrait_id'])
    
    # 3. REVERT AR_CONTENT CHANGES
    if 'ar_content' in existing_tables:
        ar_content_columns = [col['name'] for col in inspector.get_columns('ar_content')]
        
        # Drop new indexes
        ar_content_indexes = [idx['name'] for idx in inspector.get_indexes('ar_content')]
        if 'ix_ar_content_company_project' in ar_content_indexes:
            op.drop_index('ix_ar_content_company_project', table_name='ar_content')
        if 'ix_ar_content_created_at' in ar_content_indexes:
            op.drop_index('ix_ar_content_created_at', table_name='ar_content')
        if 'uq_ar_content_unique_id' in ar_content_indexes:
            op.drop_index('uq_ar_content_unique_id', table_name='ar_content')
        
        # Drop new columns
        new_columns = ['video_path', 'video_url', 'qr_code_url', 'preview_url', 'content_metadata']
        for col in new_columns:
            if col in ar_content_columns:
                op.drop_column('ar_content', col)
        
        # Rename name back to title
        if 'name' in ar_content_columns and 'title' not in ar_content_columns:
            op.alter_column('ar_content', 'name', new_column_name='title')