"""Add thumbnail fields to videos and ar_content

Revision ID: 20251205_thumbnails
Revises: 20251205_perf_idx
Create Date: 2025-12-05 16:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251205_thumbnails'
down_revision = '20251205_perf_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем поля для превью в таблицу videos
    op.add_column('videos', sa.Column('thumbnail_small_url', sa.String(500), nullable=True))
    op.add_column('videos', sa.Column('thumbnail_large_url', sa.String(500), nullable=True))
    
    # Поле thumbnail_url уже существует в модели, но добавим комментарий
    op.execute("COMMENT ON COLUMN videos.thumbnail_url IS 'Medium size thumbnail (400x225)'")
    op.execute("COMMENT ON COLUMN videos.thumbnail_small_url IS 'Small size thumbnail (200x112)'")
    op.execute("COMMENT ON COLUMN videos.thumbnail_large_url IS 'Large size thumbnail (800x450)'")
    
    # Поле thumbnail_url для ar_content уже существует
    op.execute("COMMENT ON COLUMN ar_content.thumbnail_url IS 'Medium size portrait thumbnail (400x225)'")


def downgrade() -> None:
    # Удаляем добавленные поля
    op.drop_column('videos', 'thumbnail_large_url')
    op.drop_column('videos', 'thumbnail_small_url')
