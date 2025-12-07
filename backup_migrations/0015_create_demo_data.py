"""Create demo data for Vertex AR platform

Revision ID: 0015_create_demo_data
Revises: 003_create_users
Create Date: 2025-12-06 14:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
import uuid

# revision identifiers, used by Alembic.
revision = '0015_create_demo_data'
down_revision = '003_create_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # 1. Ensure default storage connection exists (should already exist from seed_defaults)
    result = conn.execute(sa.text("""
        SELECT id FROM storage_connections WHERE name = 'Vertex AR Local Storage' AND is_default = true
    """))
    default_storage_row = result.fetchone()
    
    if default_storage_row:
        default_storage_id = default_storage_row[0]
    else:
        # Create default storage connection if it doesn't exist
        conn.execute(sa.text("""
            INSERT INTO storage_connections 
            (name, provider, base_path, is_default, is_active, test_status, created_at) 
            VALUES 
            ('Vertex AR Local Storage', 'local_disk', '/app/storage/content', true, true, 'success', NOW())
            ON CONFLICT (name) DO NOTHING
            RETURNING id
        """))
        
        result = conn.execute(sa.text("""
            SELECT id FROM storage_connections WHERE name = 'Vertex AR Local Storage' AND is_default = true
        """))
        default_storage_id = result.fetchone()[0]
    
    # 2. Ensure Vertex AR Company exists (should already exist from seed_defaults)
    result = conn.execute(sa.text("""
        SELECT id FROM companies WHERE slug = 'vertex-ar' AND is_default = true
    """))
    vertex_ar_company_row = result.fetchone()
    
    if vertex_ar_company_row:
        vertex_ar_company_id = vertex_ar_company_row[0]
    else:
        # Create Vertex AR company if it doesn't exist
        conn.execute(sa.text("""
            INSERT INTO companies 
            (name, slug, contact_email, contact_phone, storage_connection_id, storage_path, 
             is_default, is_active, storage_quota_gb, storage_used_bytes, created_at)
            VALUES 
            ('Vertex AR', 'vertex-ar', 'admin@vertexar.com', '+7 (999) 123-45-67', :storage_id, '/', 
             true, true, 100, 0, NOW())
            ON CONFLICT (slug) DO NOTHING
            RETURNING id
        """), {"storage_id": default_storage_id})
        
        result = conn.execute(sa.text("""
            SELECT id FROM companies WHERE slug = 'vertex-ar' AND is_default = true
        """))
        vertex_ar_company_id = result.fetchone()[0]
    
    # 3. Create 5 client companies
    demo_clients = [
        ('Рекламное агентство "Креатив"', 'creative-agency', 'info@creative.ru', '+7 (495) 123-45-67', 10),
        ('Маркетинговая студия "BrandPro"', 'brandpro', 'hello@brandpro.ru', '+7 (812) 987-65-43', 25),
        ('POS Материалы "PrintMaster"', 'printmaster', 'order@printmaster.ru', '+7 (495) 777-88-99', 5),
        ('Event агентство "ShowTime"', 'showtime', 'events@showtime.ru', '+7 (903) 555-44-33', 15),
        ('Дизайн студия "ArtFusion"', 'artfusion', 'design@artfusion.ru', '+7 (495) 222-11-00', 20),
    ]
    
    client_company_ids = []
    for name, slug, email, phone, quota in demo_clients:
        conn.execute(sa.text("""
            INSERT INTO companies 
            (name, slug, contact_email, contact_phone, storage_connection_id, storage_path, 
             storage_quota_gb, is_active, created_at)
            VALUES (:name, :slug, :email, :phone, :storage_id, :storage_path, :quota, true, NOW())
            ON CONFLICT (slug) DO NOTHING
        """), {
            "name": name, 
            "slug": slug, 
            "email": email, 
            "phone": phone, 
            "storage_id": default_storage_id,
            "storage_path": f"/{slug}",
            "quota": quota
        })
        
        # Get the company ID
        result = conn.execute(sa.text("""
            SELECT id FROM companies WHERE slug = :slug
        """), {"slug": slug})
        company_id = result.fetchone()[0]
        client_company_ids.append(company_id)
    
    # 4. Create projects for each company
    demo_projects = [
        # Vertex AR projects
        (vertex_ar_company_id, 'Демо контент Vertex AR', 'demo-vertex', 'demo', datetime.now(), datetime.now() + timedelta(days=365)),
        
        # Client company projects (using the client company IDs we just created)
        (client_company_ids[0], 'Новогодние постеры 2025', 'new-year-posters', 'posters', datetime.now(), datetime.now() + timedelta(days=90)),
        (client_company_ids[1], 'Корпоративные сувениры', 'corporate-souvenirs', 'souvenirs', datetime.now(), datetime.now() + timedelta(days=180)),
        (client_company_ids[2], 'POS материалы для магазинов', 'pos-materials', 'pos', datetime.now(), datetime.now() + timedelta(days=60)),
        (client_company_ids[3], 'Выставка EventShow 2026', 'event-show-2026', 'exhibition', datetime.now(), datetime.now() + timedelta(days=120)),
        (client_company_ids[4], 'Брендинг для кафе', 'cafe-branding', 'cafe', datetime.now(), datetime.now() + timedelta(days=365)),
    ]
    
    project_ids = {}
    for i, (company_id, name, slug, project_type, start, end) in enumerate(demo_projects):
        conn.execute(sa.text("""
            INSERT INTO projects 
            (company_id, name, slug, folder_path, project_type, starts_at, expires_at, status, created_at)
            VALUES (:company_id, :name, :slug, :folder_path, :project_type, :starts_at, :expires_at, 'active', NOW())
            ON CONFLICT (company_id, slug) DO NOTHING
        """), {
            "company_id": company_id,
            "name": name,
            "slug": slug,
            "folder_path": f"/{slug}",
            "project_type": project_type,
            "starts_at": start,
            "expires_at": end
        })
        
        # Get the project ID
        result = conn.execute(sa.text("""
            SELECT id FROM projects WHERE company_id = :company_id AND slug = :slug
        """), {"company_id": company_id, "slug": slug})
        project_id = result.fetchone()[0]
        project_ids[i] = project_id
    
    # 5. Create AR content (1 portrait per project)
    demo_ar_content = [
        (project_ids[0], 'Демо портрет Vertex AR', 'vertex-demo', 1920, 1080),
        (project_ids[1], 'Санта с подарками', 'santa-gifts', 1200, 1600),
        (project_ids[2], 'Бизнес портрет CEO', 'ceo-portrait', 1080, 1920),
        (project_ids[3], 'POS стенд с продуктом', 'pos-stand', 2000, 1000),
        (project_ids[4], 'Выставочный стенд', 'exhibition-stand', 1500, 1200),
        (project_ids[5], 'Бариста с кофе', 'barista-coffee', 1080, 1350),
    ]
    
    ar_content_ids = {}
    for i, (project_id, title, unique_id_str, width, height) in enumerate(demo_ar_content):
        # Generate a UUID for the unique_id
        unique_id = str(uuid.uuid4())
        
        conn.execute(sa.text("""
            INSERT INTO ar_content 
            (project_id, company_id, unique_id, title, image_path, image_url, 
             marker_path, marker_url, marker_status, marker_generated_at, width, height, 
             is_active, created_at)
            VALUES (:project_id, 
                    (SELECT company_id FROM projects WHERE id = :project_id), 
                    :unique_id, :title, 
                    :image_path, 
                    :image_url,
                    :marker_path,
                    :marker_url,
                    'ready', NOW(), :width, :height, true, NOW())
            ON CONFLICT (unique_id) DO NOTHING
        """), {
            "project_id": project_id,
            "unique_id": unique_id,
            "title": title,
            "image_path": f'/demo/portraits/{unique_id_str}.jpg',
            "image_url": f'/storage/content/demo/portraits/{unique_id_str}.jpg',
            "marker_path": f'/demo/markers/{unique_id_str}.mind',
            "marker_url": f'/storage/content/demo/markers/{unique_id_str}.mind',
            "width": width,
            "height": height
        })
        # Get the AR content ID
        result = conn.execute(sa.text("""
            SELECT id FROM ar_content WHERE unique_id = :unique_id
        """), {"unique_id": unique_id})
        ar_content_id = result.fetchone()[0]
        ar_content_ids[i] = ar_content_id
    
    # 6. Create videos for demo content (2-3 videos per portrait)
    demo_videos = [
        # Vertex AR videos
        (ar_content_ids[0], 'Демо анимация', 15.0, 1920, 1080),
        (ar_content_ids[0], 'Демо ротация 2', 12.0, 1920, 1080),
        
        # Client videos
        (ar_content_ids[1], 'Новогодняя анимация Санта', 20.0, 1920, 1080),
        (ar_content_ids[1], 'Снегопад с подарками', 10.0, 1920, 1080),
        (ar_content_ids[2], 'Корпоративный привет', 18.0, 1080, 1920),
        (ar_content_ids[3], 'POS промо продукт', 25.0, 1920, 1080),
        (ar_content_ids[4], 'Выставочный тур', 30.0, 1920, 1080),
        (ar_content_ids[5], 'Кофе бариста', 22.0, 1080, 1920),
    ]
    
    for ar_content_id, title, duration, width, height in demo_videos:
        # Generate a unique filename for the video
        video_filename = f"{title.replace(' ', '_').lower()}.mp4"
        thumbnail_filename = f"{title.replace(' ', '_').lower()}_medium.webp"
        
        conn.execute(sa.text("""
            INSERT INTO videos 
            (ar_content_id, title, video_path, video_url, duration, width, height, 
             is_active, thumbnail_url, created_at)
            VALUES (:ar_content_id, :title, :video_path, 
                    :video_url, 
                    :duration, :width, :height, true, 
                    :thumbnail_url, NOW())
            ON CONFLICT DO NOTHING
        """), {
            "ar_content_id": ar_content_id,
            "title": title,
            "video_path": f'/demo/videos/{video_filename}',
            "video_url": f'/storage/content/demo/videos/{video_filename}',
            "duration": duration,
            "width": width,
            "height": height,
            "thumbnail_url": f'/storage/content/demo/thumbnails/{thumbnail_filename}'
        })


def downgrade() -> None:
    # Carefully delete demo data
    conn = op.get_bind()
    
    # Delete videos first (foreign key constraints)
    conn.execute(sa.text("""
        DELETE FROM videos WHERE 
        ar_content_id IN (
            SELECT id FROM ar_content WHERE 
            title IN (
                'Демо анимация', 'Демо ротация 2', 'Новогодняя анимация Санта', 
                'Снегопад с подарками', 'Корпоративный привет', 'POS промо продукт',
                'Выставочный тур', 'Кофе бариста'
            )
        )
    """))
    
    # Delete AR content
    conn.execute(sa.text("""
        DELETE FROM ar_content WHERE 
        title IN (
            'Демо портрет Vertex AR', 'Санта с подарками', 'Бизнес портрет CEO',
            'POS стенд с продуктом', 'Выставочный стенд', 'Бариста с кофе'
        )
    """))
    
    # Delete projects (except those that might be in use)
    conn.execute(sa.text("""
        DELETE FROM projects WHERE 
        name IN (
            'Демо контент Vertex AR', 'Новогодние постеры 2025', 'Корпоративные сувениры',
            'POS материалы для магазинов', 'Выставка EventShow 2026', 'Брендинг для кафе'
        )
    """))
    
    # Delete client companies (but NOT the default Vertex AR company)
    conn.execute(sa.text("""
        DELETE FROM companies WHERE 
        name IN (
            'Рекламное агентство "Креатив"', 'Маркетинговая студия "BrandPro"',
            'POS Материалы "PrintMaster"', 'Event агентство "ShowTime"',
            'Дизайн студия "ArtFusion"'
        )
    """))