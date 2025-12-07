"""Add thumbnail fields to videos and ar_content

Revision ID: 20251205_thumbnails
Revises: 20251205_add_missing_fields
Create Date: 2025-12-05 16:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251205_thumbnails'
down_revision = '20251205_add_missing_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if columns exist before adding them
    conn = op.get_bind()
    
    # Check for thumbnail_small_url in videos table
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'videos' AND column_name = 'thumbnail_small_url'
    """))
    
    if not result.fetchone():
        op.add_column('videos', sa.Column('thumbnail_small_url', sa.String(500), nullable=True))
    
    # Check for thumbnail_large_url in videos table
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'videos' AND column_name = 'thumbnail_large_url'
    """))
    
    if not result.fetchone():
        op.add_column('videos', sa.Column('thumbnail_large_url', sa.String(500), nullable=True))
    
    # Add comments if columns exist or were just created
    try:
        op.execute("COMMENT ON COLUMN videos.thumbnail_url IS 'Medium size thumbnail (400x225)'")
        op.execute("COMMENT ON COLUMN videos.thumbnail_small_url IS 'Small size thumbnail (200x112)'")
        op.execute("COMMENT ON COLUMN videos.thumbnail_large_url IS 'Large size thumbnail (800x450)'")
        op.execute("COMMENT ON COLUMN ar_content.thumbnail_url IS 'Medium size portrait thumbnail (400x225)'")
    except Exception:
        # Ignore if comments fail
        pass


def downgrade() -> None:
    # Check if columns exist before dropping them
    conn = op.get_bind()
    
    # Check for thumbnail_large_url in videos table
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'videos' AND column_name = 'thumbnail_large_url'
    """))
    
    if result.fetchone():
        op.drop_column('videos', 'thumbnail_large_url')
    
    # Check for thumbnail_small_url in videos table
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'videos' AND column_name = 'thumbnail_small_url'
    """))
    
    if result.fetchone():
        op.drop_column('videos', 'thumbnail_small_url')