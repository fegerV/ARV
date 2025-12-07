# System Architecture

## Overview

Vertex AR is a B2B SaaS platform for creating augmented reality content based on image recognition (NFT markers). The system follows a microservices-inspired architecture with clear separation of concerns, enabling scalability and maintainability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Client Applications                              │
├─────────────────────────────┬───────────────────────────────────────────────┤
│        Web Browser          │           AR Mobile App                       │
│  (Admin Panel / Viewer)     │    (Unity/Android/iOS)                        │
└────────────┬────────────────┴───────────────┬───────────────────────────────┘
             │                                │
             │         HTTPS/TLS              │
             ▼                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Load Balancer / CDN                                │
│                              (Nginx)                                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
     ┌──────────▼──┐  ┌────────▼──┐  ┌────────▼──┐
     │    API      │  │  Static   │  │   AR      │
     │  Gateway    │  │  Assets   │  │  Content  │
     │ (FastAPI)   │  │ (Nginx)   │  │  Cache    │
     └──────┬──────┘  └───────────┘  └───────────┘
            │
     ┌──────▼───────────────────────────────────────────────────────────────┐
     │                         Application Services                         │
     ├──────────────────────────────────────────────────────────────────────┤
     │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
     │  │   Auth      │  │  Storage    │  │  Marker     │  │  Analytics  │ │
     │  │  Service    │  │  Service    │  │  Service    │  │  Service    │ │
     │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
     │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
     │  │   Video     │  │  Rotation   │  │Notification │  │    User     │ │
     │  │Processing   │  │  Service    │  │   Service   │  │Management   │ │
     │  │  Service    │  │             │  │             │  │   Service   │ │
     │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
     └─────────────────────────────┬────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
         ┌──────────▼──┐  ┌────────▼──┐  ┌────────▼──┐
         │  Database   │  │  Message  │  │  Storage  │
         │ (PostgreSQL)│  │  Queue    │  │ (MinIO/   │
         └─────────────┘  │ (Redis)   │  │YandexDisk)│
                          └───────────┘  └───────────┘
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.109 (Python 3.11)
- **Database**: PostgreSQL 15 with SQLAlchemy 2.0 async ORM
- **Message Queue**: Redis 7 with Celery 5.3
- **Authentication**: JWT with OAuth 2.0
- **API Documentation**: OpenAPI/Swagger

### Frontend
- **Admin Panel**: React 18 with TypeScript, Material-UI 5, TailwindCSS
- **AR Viewer**: Mind AR 1.2.5 with Three.js 0.158

### Infrastructure
- **Containerization**: Docker with Docker Compose
- **Reverse Proxy**: Nginx
- **Monitoring**: Prometheus, Grafana, Alertmanager
- **Logging**: Structured JSON logs with ELK stack integration
- **Backup**: WAL archiving, pg_dump, rsync

## Service Components

### API Gateway (FastAPI)
- RESTful API endpoints
- Request/response validation
- Authentication and authorization
- Rate limiting
- Request logging and tracing

### Authentication Service
- User registration and management
- JWT token generation and validation
- Password hashing and verification
- Session management
- Role-based access control

### Storage Service
- Multi-tenant storage abstraction
- Support for local filesystem, MinIO, and Yandex Disk
- File upload and download operations
- Storage quota management
- Path isolation and security
- Configurable storage providers via environment variables
- Graceful fallback to local storage on provider failure
- Provider-specific configuration validation
- Presigned URL generation for direct uploads (MinIO)

### Marker Service
- NFT marker generation using MindAR
- Marker quality assessment
- Feature point detection
- Marker caching and optimization

### Video Processing Service
- Video upload handling
- Thumbnail generation
- Format conversion
- Metadata extraction
- Streaming optimization

### Rotation Service
- Video rotation scheduling
- Rule-based content switching
- Date-specific scheduling
- Random rotation algorithms

### Analytics Service
- Usage statistics collection
- Performance metrics tracking
- User behavior analysis
- Reporting and dashboards

### Notification Service
- Email notifications (SMTP)
- Telegram notifications
- Webhook integrations
- Alert management

## Data Model

### Core Entities

#### Company
- Multi-tenant isolation
- Storage connection configuration
- Subscription management
- Contact information

#### Project
- Content organization
- Storage path management
- Metadata and settings

#### AR Content
- Image and marker data
- Associated videos
- Rotation rules
- Analytics data

#### Video
- Video files and metadata
- Thumbnails and previews
- Format information
- Association with AR content

#### User
- Authentication credentials
- Role and permissions
- Account status
- Activity tracking

### Relationships

```
Company 1:N Project
Project 1:N ARContent
ARContent 1:N Video
ARContent 1:1 VideoRotationRule
Company 1:1 StorageConnection
User N:1 Company
```

## Data Flow

### Content Creation Process

1. **Company Registration**
   - Admin creates company account
   - Configures storage connection
   - Sets up quotas and permissions

2. **Project Creation**
   - Company creates project folder
   - Defines project settings
   - Assigns team members

3. **AR Content Upload**
   - Upload portrait image
   - System generates unique ID
   - Creates database record

4. **Marker Generation**
   - Background task processes image
   - Generates NFT marker (.mind file)
   - Updates content status

5. **Video Upload**
   - Upload video files
   - Generate thumbnails
   - Associate with AR content

6. **Rotation Configuration**
   - Define rotation rules
   - Set scheduling parameters
   - Configure default content

7. **Content Activation**
   - Review and approve content
   - Generate QR codes
   - Publish to production

### AR Viewing Process

1. **QR Code Scanning**
   - User scans printed QR code
   - Mobile app resolves unique ID
   - Fetches AR content metadata

2. **Content Retrieval**
   - Load marker file
   - Fetch active video
   - Download required assets

3. **AR Rendering**
   - Initialize MindAR engine
   - Track image features
   - Render video overlay

4. **Analytics Collection**
   - Record session start
   - Track performance metrics
   - Log user interactions

## Scalability Patterns

### Horizontal Scaling
- Stateless API services
- Shared database with connection pooling
- Distributed message queue
- CDN for static assets

### Caching Strategy
- Redis for session data
- In-memory caching for frequent queries
- CDN caching for static content
- Database query result caching

### Load Distribution
- Round-robin load balancing
- Sticky sessions for WebSocket connections
- Geographic distribution for global users
- Auto-scaling based on metrics

## Security Architecture

### Data Protection
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Secure key management
- Regular security audits

### Access Control
- JWT-based authentication
- Role-based authorization
- API rate limiting
- Input validation and sanitization

### Network Security
- Firewall rules
- Private network segmentation
- DDoS protection
- Intrusion detection systems

## Monitoring and Observability

### Metrics Collection
- API response times
- Database query performance
- Background task processing
- System resource utilization

### Logging Strategy
- Structured JSON logs
- Request tracing with correlation IDs
- Error and exception tracking
- Audit trails for security events

### Alerting System
- Threshold-based alerts
- Anomaly detection
- Escalation policies
- Integration with communication channels

## Deployment Architecture

### Container Orchestration
- Docker Compose for multi-container applications
- Environment-specific configurations
- Health checks and auto-restart
- Resource limits and constraints

### Database Architecture
- Primary database for writes
- Read replicas for scaling
- Connection pooling
- Backup and recovery procedures

### Storage Architecture
- Multi-tier storage (hot/warm/cold)
- Content delivery network integration
- Redundancy and replication
- Lifecycle management

## Disaster Recovery

### Backup Strategy
- Continuous WAL archiving
- Daily logical backups
- Weekly physical backups
- Cross-region replication

### Recovery Procedures
- Point-in-time recovery
- Failover to standby systems
- Data consistency verification
- Business continuity planning

### High Availability
- Multi-zone deployment
- Automatic failover
- Load balancer health checks
- Graceful degradation