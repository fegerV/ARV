"""Mock data for HTML routes fallback."""

# Dashboard mock data
DASHBOARD_MOCK_DATA = {
    "total_views": 12543,
    "unique_sessions": 3241,
    "active_content": 156,
    "storage_used_gb": 2.4,
    "active_companies": 24,
    "active_projects": 89,
    "revenue": "$12,450",
    "uptime": "99.9%"
}

# Companies mock data
COMPANIES_MOCK_DATA = [
    {
        "id": "1",
        "name": "Vertex AR Solutions",
        "contact_email": "contact@vertexar.com",
        "storage_provider": "Local",
        "status": "active",
        "projects_count": 12,
        "created_at": "2023-01-15T10:30:00"
    },
    {
        "id": "2",
        "name": "AR Tech Innovations",
        "contact_email": "info@artech.com",
        "storage_provider": "AWS S3",
        "status": "active",
        "projects_count": 8,
        "created_at": "2023-02-20T14:22:0"
    }
]

# AR Content mock data
AR_CONTENT_MOCK_DATA = [
    {
        "id": "1",
        "order_number": "AR-001",
        "company_name": "Vertex AR Solutions",
        "created_at": "2023-01-15T10:30:00",
        "status": "ready",
        "thumbnail_url": "/storage/thumbnails/sample.jpg",
        "active_video_title": "Product Demo",
        "customer_name": "John Doe",
        "customer_phone": "+1234567890",
        "customer_email": "john@example.com",
        "views_count": 125,
        "views_30_days": 42,
        "public_url": "https://example.com/ar/1"
    },
    {
        "id": "2",
        "order_number": "AR-002",
        "company_name": "AR Tech Innovations",
        "created_at": "2023-01-20T14:45:00",
        "status": "processing",
        "thumbnail_url": "/storage/thumbnails/sample2.jpg",
        "active_video_title": "Marketing Video",
        "customer_name": "Jane Smith",
        "customer_phone": "+0987654321",
        "customer_email": "jane@example.com",
        "views_count": 89,
        "views_30_days": 23,
        "public_url": "https://example.com/ar/2"
    }
]

# AR Content detail mock data
AR_CONTENT_DETAIL_MOCK_DATA = {
    "id": "1",
    "order_number": "AR-001",
    "company_name": "Vertex AR Solutions",
    "project_name": "Q4 Marketing Campaign",
    "created_at": "2023-01-15T10:30:00",
    "status": "ready",
    "customer_name": "John Doe",
    "customer_phone": "+1234567890",
    "customer_email": "john@example.com",
    "duration_years": 1,
    "photo_url": "/storage/photos/sample.jpg",
    "video_url": "/storage/videos/sample.mp4",
    "thumbnail_url": "/storage/thumbnails/sample.jpg",
    "active_video_title": "Product Demo",
    "views_count": 125,
    "views_30_days": 42,
    "public_url": "/api/ar-content/view/1",
    "unique_link": "/view/1",
    "qr_code_url": "/storage/qr/1.png",
    "marker_status": "generated",
    "videos": []
}

# Projects mock data
PROJECTS_MOCK_DATA = [
    {
        "id": "1",
        "name": "Q4 Marketing Campaign",
        "status": "active",
        "company_name": "Vertex AR Solutions",
        "created_at": "2023-01-15T10:30:00",
        "ar_content_count": 5
    },
    {
        "id": "2",
        "name": "Product Demo Series",
        "status": "active",
        "company_name": "AR Tech Innovations",
        "created_at": "2023-02-20T14:22:00",
        "ar_content_count": 3
    }
]

# Project creation mock data
PROJECT_CREATE_MOCK_DATA = {
    "companies": [
        {"id": "1", "name": "Vertex AR Solutions", "status": "active"},
        {"id": "2", "name": "AR Tech Innovations", "status": "active"}
    ],
    "projects": [
        {"id": "1", "name": "Q4 Marketing Campaign", "company_id": "1", "status": "active"},
        {"id": "2", "name": "Product Demo Series", "company_id": "1", "status": "active"}
    ]
}

# Storage mock data
STORAGE_MOCK_DATA = {
    "storage_info": {
        "total_storage": "100 GB",
        "used_storage": "24.5 GB",
        "available_storage": "75.5 GB",
        "providers": [
            {
                "name": "Local Storage",
                "status": "active",
                "description": "Default local storage provider",
                "used_space": "24.5 GB",
                "capacity": "100 GB"
            }
        ],
        "companies": [
            {
                "id": "1",
                "name": "Vertex AR Solutions",
                "storage_used": "15.2 GB",
                "files_count": 142
            },
            {
                "id": "2",
                "name": "AR Tech Innovations",
                "storage_used": "9.3 GB",
                "files_count": 87
            }
        ]
    }
}

# Analytics mock data
ANALYTICS_MOCK_DATA = {
    "analytics_data": {
        "total_views": 12543,
        "unique_sessions": 3241,
        "active_content": 156,
        "avg_session_duration": "2m 34s",
        "views_30_days": 3241,
        "unique_visitors_30_days": 1245,
        "avg_engagement_time": "1m 45s",
        "bounce_rate": "24.3%",
        "top_content": [
            {
                "id": "1",
                "title": "Product Demo AR",
                "company_name": "Vertex AR Solutions",
                "views_count": 1240
            },
            {
                "id": "2",
                "title": "Marketing Campaign",
                "company_name": "AR Tech Innovations",
                "views_count": 987
            }
        ]
    }
}

# Notifications mock data
NOTIFICATIONS_MOCK_DATA = [
    {
        "id": "1",
        "title": "New AR Content Created",
        "message": "A new AR content item 'Product Demo' was created for Vertex AR Solutions",
        "created_at": "2023-01-15T10:30:00",
        "is_read": False,
        "company_name": "Vertex AR Solutions",
        "project_name": "Q4 Campaign",
        "ar_content_name": "Product Demo"
    },
    {
        "id": "2",
        "title": "Storage Alert",
        "message": "Storage usage for AR Tech Innovations has reached 80% of allocated space",
        "created_at": "2023-01-14T16:45:00",
        "is_read": True,
        "company_name": "AR Tech Innovations",
        "project_name": "Summer Sale",
        "ar_content_name": "—"
    }
]

# Settings mock data
SETTINGS_MOCK_DATA = {
    "settings": {
        "site_title": "Vertex AR B2B Platform",
        "admin_email": "admin@vertexar.com",
        "site_description": "B2B SaaS platform for creating AR content based on image recognition (NFT markers)",
        "password_min_length": 8,
        "session_timeout": 60,
        "default_storage": "local",
        "max_file_size": 10
    }
}

# Unique values for filters mock data
UNIQUE_VALUES_MOCK_DATA = {
    "unique_companies": ["Vertex AR Solutions", "AR Tech Innovations"],
    "unique_statuses": ["ready", "processing", "pending", "failed"]
}