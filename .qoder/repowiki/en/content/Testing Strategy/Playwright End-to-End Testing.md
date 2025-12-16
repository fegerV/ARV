# Playwright End-to-End Testing

<cite>
**Referenced Files in This Document**   
- [playwright.config.ts](file://playwright.config.ts)
- [admin.spec.ts](file://tests/e2e/admin.spec.ts)
- [docker-compose.yml](file://docker-compose.yml)
- [Dockerfile](file://Dockerfile)
- [main.py](file://app/main.py)
- [vite.config.ts](file://frontend/vite.config.ts)
- [package.json](file://frontend/package.json)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document provides a comprehensive analysis of the Playwright end-to-end testing setup in the ARV project, a B2B SaaS platform for creating augmented reality (AR) content based on image recognition. The E2E tests validate the complete user journey from company creation to AR content generation and QR code deployment. The testing infrastructure is integrated with Docker Compose for environment consistency and uses structured logging, health checks, and CI/CD best practices.

## Project Structure

```mermaid
flowchart TD
E2ETests["tests/e2e/"]
E2ETests --> AdminSpec["admin.spec.ts"]
Config["playwright.config.ts"]
Frontend["frontend/"]
Backend["app/"]
Docker["docker-compose.yml"]
Dockerfile["Dockerfile"]
Config --> |Test Configuration| E2ETests
Frontend --> |UI Layer| E2ETests
Backend --> |API Layer| Frontend
Docker --> |Service Orchestration| Backend
Dockerfile --> |Application Image| Docker
```

**Diagram sources**
- [playwright.config.ts](file://playwright.config.ts#L1-L20)
- [tests/e2e/admin.spec.ts](file://tests/e2e/admin.spec.ts#L1-L24)
- [docker-compose.yml](file://docker-compose.yml#L1-L254)

**Section sources**
- [playwright.config.ts](file://playwright.config.ts#L1-L20)
- [docker-compose.yml](file://docker-compose.yml#L1-L254)

## Core Components

The Playwright E2E testing framework is configured to run against a full-stack application composed of a React frontend, FastAPI backend, PostgreSQL database, Redis cache, and MinIO storage. The test suite simulates real user interactions including authentication, company creation, project setup, AR content upload, and QR code generation. The configuration supports parallel execution, trace recording on failure, and HTML reporting for test results visualization.

**Section sources**
- [playwright.config.ts](file://playwright.config.ts#L1-L20)
- [admin.spec.ts](file://tests/e2e/admin.spec.ts#L1-L24)

## Architecture Overview

```mermaid
graph TD
Client[Playwright Test Runner]
Browser[Chromium Browser]
FE[Frontend: React App]
NGINX[Nginx Reverse Proxy]
API[FastAPI Backend]
DB[(PostgreSQL)]
Cache[(Redis)]
Storage[(MinIO)]
Client --> |Execute Tests| Browser
Browser --> |HTTP Requests| FE
FE --> |API Proxy| NGINX
NGINX --> |Forward /api| API
API --> |Database Operations| DB
API --> |Cache Operations| Cache
API --> |File Storage| Storage
API --> |Celery Tasks| Cache
style Client fill:#4B9CD3,stroke:#333
style Browser fill:#FFD700,stroke:#333
style FE fill:#61DAFB,stroke:#333
style NGINX fill:#009688,stroke:#333
style API fill:#563D7C,stroke:#333
style DB fill:#336791,stroke:#333
style Cache fill:#D32F2F,stroke:#333
style Storage fill:#2E7D32,stroke:#333
```

**Diagram sources**
- [docker-compose.yml](file://docker-compose.yml#L1-L254)
- [vite.config.ts](file://frontend/vite.config.ts#L1-L21)
- [main.py](file://app/main.py#L1-L268)

## Detailed Component Analysis

### Playwright Configuration Analysis

```mermaid
classDiagram
class PlaywrightConfig {
+testDir : string
+fullyParallel : boolean
+forbidOnly : boolean
+retries : number
+workers : number | undefined
+reporter : string
+use : object
+projects : array
}
class UseOptions {
+baseURL : string
+trace : string
}
class ProjectConfig {
+name : string
+use : object
}
PlaywrightConfig --> UseOptions : "has"
PlaywrightConfig --> ProjectConfig : "has multiple"
ProjectConfig --> UseOptions : "extends"
```

**Diagram sources**
- [playwright.config.ts](file://playwright.config.ts#L1-L20)

**Section sources**
- [playwright.config.ts](file://playwright.config.ts#L1-L20)

### E2E Test Flow Analysis

```mermaid
sequenceDiagram
participant Test as Playwright Test
participant Page as Browser Page
participant FE as Frontend App
participant API as FastAPI Backend
participant DB as PostgreSQL
Test->>Page : goto('/login')
Page->>FE : Render Login Page
Test->>Page : fill(email, password)
Test->>Page : click(Login)
Page->>API : POST /api/oauth/token
API->>DB : Validate Credentials
DB-->>API : User Data
API-->>Page : Set Session Cookie
Page->>FE : Redirect to /companies/new
Test->>Page : fill(company-name)
Test->>Page : click(Connect Yandex)
Test->>Page : click(Create Company)
Page->>API : POST /api/companies
API->>DB : Insert Company
DB-->>API : Success
API-->>Page : 201 Created
Test->>Page : expect(redirect to /companies/ : id)
```

**Diagram sources**
- [admin.spec.ts](file://tests/e2e/admin.spec.ts#L1-L24)
- [main.py](file://app/main.py#L1-L268)
- [docker-compose.yml](file://docker-compose.yml#L1-L254)

**Section sources**
- [admin.spec.ts](file://tests/e2e/admin.spec.ts#L1-L24)

### Docker Orchestration Analysis

```mermaid
flowchart TD
DockerCompose["docker-compose.yml"]
DockerCompose --> Postgres["postgres service"]
DockerCompose --> Redis["redis service"]
DockerCompose --> MinIO["minio service"]
DockerCompose --> App["app service"]
DockerCompose --> Nginx["nginx service"]
DockerCompose --> Playwright["Playwright Tests"]
Postgres --> |Health Check| PGIsReady["pg_isready"]
Redis --> |Health Check| RedisPing["redis-cli ping"]
App --> |Depends On| Postgres
App --> |Depends On| Redis
Nginx --> |Depends On| App
Playwright --> |Targets| Nginx
style DockerCompose fill:#2E7D32,stroke:#333
style Postgres fill:#336791,stroke:#333
style Redis fill:#D32F2F,stroke:#333
style MinIO fill:#2E7D32,stroke:#333
style App fill:#563D7C,stroke:#333
style Nginx fill:#009688,stroke:#333
```

**Diagram sources**
- [docker-compose.yml](file://docker-compose.yml#L1-L254)
- [Dockerfile](file://Dockerfile#L1-L53)

**Section sources**
- [docker-compose.yml](file://docker-compose.yml#L1-L254)
- [Dockerfile](file://Dockerfile#L1-L53)

## Dependency Analysis

```mermaid
dependency-graph
playwright.config.ts --> admin.spec.ts
playwright.config.ts --> frontend/package.json
admin.spec.ts --> docker-compose.yml
docker-compose.yml --> Dockerfile
Dockerfile --> app/main.py
frontend/vite.config.ts --> app/main.py
app/main.py --> docker-compose.yml
```

**Diagram sources**
- [playwright.config.ts](file://playwright.config.ts#L1-L20)
- [admin.spec.ts](file://tests/e2e/admin.spec.ts#L1-L24)
- [docker-compose.yml](file://docker-compose.yml#L1-L254)
- [Dockerfile](file://Dockerfile#L1-L53)
- [main.py](file://app/main.py#L1-L268)
- [vite.config.ts](file://frontend/vite.config.ts#L1-L21)

**Section sources**
- [playwright.config.ts](file://playwright.config.ts#L1-L20)
- [docker-compose.yml](file://docker-compose.yml#L1-L254)

## Performance Considerations
The Playwright configuration is optimized for CI environments with conditional retry logic and worker count adjustments. The `fullyParallel: true` setting enables maximum test concurrency, while trace recording is limited to first retry to balance debugging capability with storage efficiency. The Docker Compose setup includes health checks to prevent race conditions during service startup, ensuring reliable test execution. The frontend proxy configuration in Vite enables seamless API integration during development and testing.

## Troubleshooting Guide

When E2E tests fail, consider the following diagnostic steps:
1. Verify all Docker services are healthy using `docker-compose ps`
2. Check the Playwright HTML report for detailed trace information
3. Validate the frontend is served on port 3000 and backend on 8000
4. Confirm the proxy configuration in vite.config.ts is correctly forwarding API requests
5. Check application logs for authentication or database errors
6. Ensure test fixtures are properly loaded in the database

**Section sources**
- [playwright.config.ts](file://playwright.config.ts#L1-L20)
- [vite.config.ts](file://frontend/vite.config.ts#L1-L21)
- [docker-compose.yml](file://docker-compose.yml#L1-L254)

## Conclusion
The Playwright E2E testing setup in the ARV project provides a robust framework for validating the complete application workflow. The integration with Docker Compose ensures environment consistency across development and CI/CD pipelines. The test configuration follows best practices for parallel execution, failure recovery, and result reporting. The architecture enables reliable testing of complex user journeys involving authentication, data creation, and external service integration.