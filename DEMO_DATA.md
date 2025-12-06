# 🎬 Vertex AR Demo Data

Production-ready demo data for showcasing the Vertex AR platform with sample companies, projects, and AR content.

## 📋 Contents

- **1 Default Company**: Vertex AR (internal)
- **5 Client Companies**: Advertising agencies, marketing studios, event companies
- **6 Projects**: Various use cases (demo, posters, souvenirs, POS materials, exhibitions, cafe branding)
- **6 AR Portraits**: One per project with ready markers
- **8 Videos**: 2-3 videos per portrait with different themes

## 🏢 Companies Structure

```
🏢 Vertex AR (Default, 100GB)
├── 📁 Демо контент Vertex AR
│   └── 🎬 Демо портрет Vertex AR (✅ Ready)

🏢 Рекламное агентство "Креатив" (10GB)
├── 📁 Новогодние постеры 2025
│   └── 🎬 Санта с подарками (✅ Ready, 3,245 views)

🏢 Маркетинговая студия "BrandPro" (25GB)
├── 📁 Корпоративные сувениры
│   └── 🎬 Бизнес портрет CEO (✅ Ready)

🏢 POS Материалы "PrintMaster" (5GB)
├── 📁 POS материалы для магазинов
│   └── 🎬 POS стенд с продуктом (✅ Ready)

🏢 Event агентство "ShowTime" (15GB)
├── 📁 Выставка EventShow 2026
│   └── 🎬 Выставочный стенд (✅ Ready)

🏢 Дизайн студия "ArtFusion" (20GB)
└── 📁 Брендинг для кафе
    └── 🎬 Бариста с кофе (✅ Ready)
```

## 🚀 Quick Start

### Method 1: One-Command Setup (Recommended)

```bash
# Run the complete demo setup script
./scripts/setup_demo.sh
```

Or on Windows:
```cmd
scripts\setup_demo.bat
```

### Method 2: Step-by-Step Setup

1. **Apply the demo data migration**
   ```bash
   docker-compose exec app alembic upgrade head
   ```

2. **Create the demo data**
   ```bash
   docker-compose exec app python scripts/create_demo_data.py
   ```

3. **Generate markers for AR content**
   ```bash
   docker-compose exec app python scripts/generate_demo_markers.py
   ```

4. **Generate demo statistics**
   ```bash
   docker-compose exec app python scripts/generate_demo_statistics.py
   ```
## 📁 Demo Files Structure

```
static/demo/
├── portraits/
│   ├── vertex-demo.jpg          # 1920x1080 (Vertex AR)
│   ├── santa-gifts.jpg          # 1200x1600 (Новогодние)
│   ├── ceo-portrait.jpg         # 1080x1920 (Бизнес)
│   ├── pos-stand.jpg            # 2000x1000 (POS)
│   ├── exhibition-stand.jpg     # 1500x1200 (Выставка)
│   └── barista-coffee.jpg       # 1080x1350 (Кафе)
├── markers/
│   ├── vertex-demo.mind
│   ├── santa-gifts.mind
│   └── ... (6 files)
└── videos/
    ├── demo-animation.mp4       # 15s
    ├── new-year-santa.mp4       # 20s
    └── ... (8 files)
```

## 🔧 Implementation Details

The demo data includes:

1. **Storage Connection**: Uses the default local storage connection
2. **Vertex AR Company**: The default system company with 100GB quota
3. **Client Companies**: 5 sample client companies with varying quotas (5-25GB)
4. **Projects**: Each company has one project with appropriate metadata
5. **AR Content**: Each project has one portrait with ready markers
6. **Videos**: Multiple videos per AR content with thumbnails
7. **View Statistics**: Realistic demo analytics data for all AR content
8. **Markers**: Generated markers for all AR content

All demo content is marked as active and ready for immediate use in the AR viewer.
## 🗑️ Cleanup

To remove demo data:

```bash
# Downgrade the migration
docker-compose exec app alembic downgrade -1
```

Or manually delete the demo entries through the admin panel.

## ⚠️ Notes

- Demo data is intended for development and demonstration purposes only
- Do not use in production environments
- All timestamps are set to current time with appropriate expiration dates
- Video durations and dimensions are realistic but fictional
- Contact information is fake and should not be used for actual communications