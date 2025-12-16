# Backend Architecture Guide

This document provides a comprehensive overview of the backend architecture for the ARVlite project, detailing the folder structure, modules, components, and best practices for backend development.

## Table of Contents
- [Folder Structure](#folder-structure)
- [Main Components](#main-components)
- [Modules Overview](#modules-overview)
- [Database Layer](#database-layer)
- [Services Layer](#services-layer)
- [API Layer](#api-layer)
- [Configuration](#configuration)
- [Migrations](#migrations)
- [Background Tasks](#background-tasks)
- [Logging and Monitoring](#logging-and-monitoring)
- [Testing](#testing)

## Folder Structure

The backend follows a modular architecture with the following folder structure:

```
ARV/
├── alembic/              # Migration files
├── app/                  # Main application code
│   ├── api/              # API routes and endpoints
│   ├── core/             # Core functionality (config, database, security)
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas for validation
│   ├── services/         # Business logic services
│   ├── utils/            # Utility functions
│   ├── background_tasks/ # Background task handlers
│   ├── middleware/       # Middleware components
│   └── main.py           # Application entry point
├── docs/                 # Documentation
├── tests/                # Test files
└── requirements.txt      # Dependencies
```

### Key Directories Explained

- `app/`: Contains all the main application code organized by layers
- `app/api/`: API routes and endpoint definitions
- `app/core/`: Core functionality like configuration, database connection, security utilities
- `app/models/`: SQLAlchemy ORM models representing database tables
- `app/schemas/`: Pydantic schemas for request/response validation
- `app/services/`: Business logic separated from API layer
- `app/utils/`: Reusable utility functions
- `alembic/`: Database migration management
- `tests/`: Unit and integration tests

## Main Components

### FastAPI Application

The application is built on FastAPI, providing:
- Automatic API documentation (Swagger UI and ReDoc)
- Asynchronous request handling
- Built-in request validation
- Dependency injection system

Key initialization in [`ARV/app/main.py`](ARV/app/main.py):
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine
from app.api.routes import router

app = FastAPI(
    title="ARVlite API",
    description="Backend API for ARVlite application",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")
```

### Database

The application uses PostgreSQL with SQLAlchemy ORM:
- Connection pooling
- Transaction management
- Query optimization
- Support for complex relationships

### Authentication

Authentication system includes:
- JWT token-based authentication
- OAuth support (Yandex integration)
- Role-based access control
- Password hashing with bcrypt

## Modules Overview

### Auth Module

Handles user authentication and authorization:

Location: `app/api/routes/auth.py`

Key features:
- User registration and login
- JWT token generation and validation
- Password reset functionality
- Session management

Example code:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginRequest, TokenResponse
from app.models.user import User
from app.core.database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_request.email).first()
    if not user or not verify_password(login_request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

### Companies Module

Manages company entities and their relationships:

Location: `app/api/routes/companies.py`

Features:
- Company creation and management
- User-company associations
- Permission controls
- Company-specific settings

### Projects Module

Handles project management within companies:

Location: `app/api/routes/projects.py`

Functionality:
- Project lifecycle management
- Project permissions
- Project templates
- Project analytics

### AR Content Module

Core module for managing AR content:

Location: `app/api/routes/ar_content.py`

Capabilities:
- AR content creation and editing
- Media file handling
- AR scene management
- Content publishing workflow

### Videos Module

Video processing and management:

Location: `app/api/routes/videos.py`

Features:
- Video upload and processing
- Thumbnail generation
- Video scheduling
- Video analytics

### Orders Module

E-commerce functionality for orders:

Location: Various files under `app/api/routes/`

Functionality:
- Order creation and tracking
- Payment processing integration
- Order history
- Invoice generation

### Storage Module

File storage management:

Location: `app/api/routes/storage.py`

Features:
- Multiple storage providers (local, cloud)
- File upload/download
- Storage quotas
- File metadata management

### Notifications Module

Real-time notification system:

Location: `app/api/routes/notifications.py`

Components:
- Push notifications
- Email notifications
- WebSocket connections
- Notification preferences

## Database Layer

### SQLAlchemy Models

Models are defined in `app/models/` using SQLAlchemy ORM:

Example model:
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="users")
```

### Database Queries

Query operations are typically handled in the service layer:

```python
from sqlalchemy.orm import Session
from app.models.user import User

def get_user_by_email(db: Session, email: str) -> User:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: dict) -> User:
    db_user = User(**user_data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
```

## Services Layer

Business logic is separated from API endpoints in the services layer:

Location: `app/services/`

### Service Example

```python
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.company import Company

class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_project(self, company_id: int, project_data: dict) -> Project:
        # Validate company exists
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError("Company not found")
        
        # Create project
        project = Project(company_id=company_id, **project_data)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_company_projects(self, company_id: int) -> list[Project]:
        return self.db.query(Project).filter(Project.company_id == company_id).all()
```

## API Layer

### Endpoints

API endpoints follow RESTful conventions:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.project_service import ProjectService
from app.core.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    service = ProjectService(db)
    try:
        created_project = service.create_project(current_user.company_id, project.dict())
        return created_project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Validation

Pydantic schemas provide request/response validation:

```python
from pydantic import BaseModel, EmailStr, validator
from typing import Optional

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
```

### Error Handling

Custom exception handlers ensure consistent error responses:

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

## Configuration

### Config Module

Configuration is managed in `app/core/config.py`:

```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Storage settings
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Environment Variables

Important environment variables:
- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: JWT secret key
- `STORAGE_PROVIDER`: Storage provider (local, s3, gcs)
- `REDIS_URL`: Redis connection for caching/background tasks
- `SMTP_SERVER`: Email server configuration

## Migrations

### Alembic Setup

Database migrations are handled by Alembic:

`alembic.ini`:
```ini
[alembic]
script_location = alembic
sqlalchemy.url = ${DATABASE_URL}

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME
```

### Migration Commands

To create a new migration:
```bash
cd ARV
alembic revision --autogenerate -m "Add new table"
```

To run migrations:
```bash
alembic upgrade head
```

To run migrations on startup:
```python
from alembic.config import Config
from alembic import command

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

## Background Tasks

### Background Task Handlers

Background tasks are managed in `app/background_tasks/`:

Example email task:
```python
import asyncio
from app.core.database import get_db
from app.models.email_queue import EmailQueue

async def process_email_queue():
    async with get_db() as db:
        pending_emails = db.query(EmailQueue).filter(EmailQueue.sent == False).all()
        
        for email in pending_emails:
            try:
                # Send email
                await send_email(email.recipient, email.subject, email.body)
                
                # Mark as sent
                email.sent = True
                db.commit()
            except Exception as e:
                # Log error and retry logic
                print(f"Failed to send email {email.id}: {str(e)}")
```

### Task Scheduling

Tasks can be scheduled using the service layer:
```python
from celery import Celery

celery_app = Celery('arvlite')

@celery_app.task
def process_video_upload(video_id: int):
    # Process video in background
    pass
```

## Logging and Monitoring

### Logging Configuration

Structured logging is implemented throughout the application:

```python
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Log important events
logger.info(f"Processing request for user {user_id}")
logger.error(f"Database connection failed: {error_message}")
```

### Monitoring Integration

For production environments, integrate with monitoring tools:
- Application performance monitoring (APM)
- Error tracking (Sentry)
- Infrastructure monitoring (Prometheus/Grafana)

## Testing

### Pytest Setup

Tests are located in the `tests/` directory:

`pytest.ini`:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
```

### Test Examples

Unit test example:
```python
import pytest
from app.services.project_service import ProjectService
from app.models.company import Company

def test_create_project_success(db_session):
    # Arrange
    company = Company(name="Test Company")
    db_session.add(company)
    db_session.commit()
    
    service = ProjectService(db_session)
    project_data = {"name": "Test Project", "description": "A test project"}
    
    # Act
    project = service.create_project(company.id, project_data)
    
    # Assert
    assert project.name == "Test Project"
    assert project.company_id == company.id

def test_create_project_invalid_company(db_session):
    # Arrange
    service = ProjectService(db_session)
    project_data = {"name": "Test Project", "description": "A test project"}
    
    # Act & Assert
    with pytest.raises(ValueError, match="Company not found"):
        service.create_project(999, project_data)
```

### Test Fixtures

Common fixtures are defined in `conftest.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.main import app

@pytest.fixture(scope="session")
def engine():
    return create_engine("sqlite:///./test.db")

@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine, tables):
    """Creates a new database session for a test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
```

Integration test example:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_project_endpoint(client, authenticated_headers):
    # Arrange
    payload = {
        "name": "Integration Test Project",
        "description": "Project created via API"
    }
    
    # Act
    response = client.post(
        "/api/v1/projects/",
        json=payload,
        headers=authenticated_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Integration Test Project"
```

## Best Practices

### Code Organization
- Separate concerns: API, business logic, data access
- Use dependency injection for testability
- Follow SOLID principles
- Keep functions small and focused

### Security
- Always validate and sanitize inputs
- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization
- Hash passwords using bcrypt or similar
- Use HTTPS in production

### Performance
- Use database indexes appropriately
- Implement caching for frequently accessed data
- Optimize database queries (avoid N+1 problems)
- Use async functions for I/O-bound operations

### Error Handling
- Provide meaningful error messages
- Log errors appropriately
- Implement retry mechanisms for transient failures
- Use custom exceptions for domain-specific errors

### Testing
- Aim for high test coverage (>80%)
- Write both unit and integration tests
- Use property-based testing for complex logic
- Mock external dependencies in unit tests