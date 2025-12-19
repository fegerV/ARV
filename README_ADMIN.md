# Vertex AR Admin Interface (HTML + Jinja2 + htmx/Alpine.js)

## Overview
This is the new admin interface for Vertex AR B2B Platform, built with a simple, maintainable stack:
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Templates**: Jinja2 for server-side rendering
- **Styling**: Tailwind CSS (utility-first CSS framework)
- **Dynamic Updates**: htmx for AJAX without JavaScript complexity
- **Local State**: Alpine.js for client-side interactions
- **Icons**: Font Awesome
- **Charts**: Chart.js for analytics

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Clone and Setup
```bash
git clone <repository-url>
cd vertex-ar
```

### 2. Start Services
```bash
# Use the admin-specific docker-compose file
docker-compose -f docker-compose.admin.yml up -d
```

### 3. Run Migrations
```bash
docker-compose -f docker-compose.admin.yml exec app alembic upgrade head
```

### 4. Access the Admin Interface
- **Admin URL**: http://localhost:8000/admin
- **Login**: admin@vertex.local / admin123
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin123)

## Architecture

### Directory Structure
```
templates/
├── base.html              # Main layout with sidebar, header
├── components/             # Reusable components
│   ├── sidebar.html       # Navigation sidebar
│   ├── header.html        # Top header with user menu
│   ├── toast.html         # Toast notifications
│   ├── modals.html        # Modal dialogs
│   └── pagination.html    # Pagination component
├── auth/
│   └── login.html         # Login page
├── dashboard/
│   └── index.html         # Dashboard with stats
├── companies/
│   ├── list.html          # Companies list
│   ├── form.html          # Create/edit company
│   └── detail.html        # Company details
├── projects/
│   ├── list.html          # Projects list
│   ├── form.html          # Create/edit project
│   └── detail.html        # Project details
├── ar-content/
│   ├── list.html          # AR content list
│   ├── form.html          # Create/edit AR content
│   └── detail.html        # AR content details
├── analytics/
│   └── index.html         # Analytics dashboard
├── storage/
│   └── index.html         # Storage management
├── notifications/
│   └── index.html         # Notifications
└── settings/
    └── index.html         # Settings page
```

### Technology Stack

#### Frontend (No Build Process)
- **Jinja2**: Server-side templating with FastAPI
- **Tailwind CSS**: Utility-first CSS framework (CDN)
- **htmx**: AJAX via HTML attributes (CDN)
- **Alpine.js**: Lightweight reactivity (CDN)
- **Font Awesome**: Icon library (CDN)
- **Chart.js**: Charts for analytics (CDN)

#### Backend
- **FastAPI**: Python web framework
- **SQLAlchemy**: ORM and database toolkit
- **PostgreSQL**: Primary database
- **Redis**: Caching and session storage
- **MinIO**: Object storage (S3-compatible)
- **Celery**: Background task processing

## Features

### Authentication
- Session-based authentication with JWT tokens
- Protected routes with middleware
- User profile and settings
- Login/logout functionality

### Dashboard
- Real-time statistics cards
- Recent activity feed
- Quick action buttons
- Responsive layout

### Companies Management
- Full CRUD operations
- List with search and filtering
- Status management (active/inactive)
- Projects count and drill-down

### Projects Management
- Create projects under companies
- AR content management
- Status tracking
- Multi-tenant support

### AR Content Management
- File upload with progress
- Video attachment support
- QR code generation
- Status tracking (pending/processing/ready/failed)

### Analytics
- Charts and metrics
- Date range filtering
- Export functionality
- Real-time data updates

### Storage Management
- Multiple storage providers (Local, MinIO, Yandex Disk)
- File browser interface
- Usage statistics
- Configuration management

### Notifications
- Alert management
- Email/Telegram notifications
- Preferences management
- Real-time updates

## Development

### Adding New Pages

1. **Create Template**:
   ```html
   {% extends "base.html" %}
   
   {% block title %}Page Title{% endblock %}
   {% block page_title %}Page Title{% endblock %}
   
   {% block content %}
   <div x-data="pageData()">
       <!-- Page content -->
   </div>
   {% endblock %}
   
   {% block extra_scripts %}
   <script>
   function pageData() {
       return {
           // Alpine.js data and methods
       };
   }
   </script>
   {% endblock %}
   ```

2. **Add Route**:
   ```python
   @router.get("/new-page", response_class=HTMLResponse)
   async def new_page(
       request: Request,
       current_user: User = Depends(get_current_active_user)
   ):
       context = get_templates_context(request, current_user)
       return templates.TemplateResponse("new_page/index.html", context)
   ```

### Adding Components

1. **Create Component Template**:
   ```html
   <!-- templates/components/my_component.html -->
   <div x-data="myComponent()">
       <!-- Component content -->
   </div>
   
   <script>
   function myComponent() {
       return {
           // Component logic
       };
   }
   </script>
   ```

2. **Include in Page**:
   ```html
   {% include "components/my_component.html" %}
   ```

### Using htmx

#### Partial Updates
```html
<div hx-get="/api/data" 
     hx-trigger="load, every 5s" 
     hx-target="#content">
    <!-- Content will be updated -->
</div>
```

#### Form Submission
```html
<form hx-post="/api/submit" 
      hx-target="#result" 
      hx-swap="innerHTML">
    <!-- Form fields -->
    <button type="submit">Submit</button>
</form>
```

#### Search with Debounce
```html
<input type="search" 
       hx-get="/api/search" 
       hx-trigger="keyup changed delay:500ms"
       hx-target="#results"
       placeholder="Search...">
```

### Using Alpine.js

#### Reactive Data
```html
<div x-data="{ count: 0 }">
    <button @click="count++">Increment</button>
    <span x-text="count"></span>
</div>
```

#### Conditional Display
```html
<div x-data="{ show: false }">
    <button @click="show = !show">Toggle</button>
    <div x-show="show" x-transition>
        Content appears with transition
    </div>
</div>
```

#### Form Validation
```html
<form x-data="formValidator()">
    <input type="email" 
           x-model="email" 
           :class="{ 'border-red-500': errors.email }">
    <span x-show="errors.email" x-text="errors.email"></span>
</form>
```

## Deployment

### Production Configuration

1. **Environment Variables**:
   ```bash
   ENVIRONMENT=production
   DEBUG=false
   SECRET_KEY=your-production-secret-key
   DATABASE_URL=postgresql+asyncpg://user:pass@host/db
   REDIS_URL=redis://host:port/0
   ```

2. **SSL Configuration**:
   ```bash
   # Enable HTTPS
   CORS_ORIGINS=https://yourdomain.com
   MINIO_USE_SSL=true
   ```

3. **Static Assets**:
   ```bash
   # Host static files locally instead of CDN
   STATIC_DIR=/app/static
   TEMPLATES_DIR=/app/templates
   ```

### Docker Production

```bash
# Build production image
docker build -t vertex-ar-admin .

# Run with production compose file
docker-compose -f docker-compose.prod.yml up -d
```

### Monitoring

- **Health Checks**: `/api/health/status`
- **Metrics**: `/metrics` (Prometheus)
- **Logs**: Structured JSON logging
- **Error Tracking**: Custom error handlers

## Migration from React

If you're migrating from the React version:

1. **Backup Data**: Export any important data
2. **Update DNS**: Point to new admin interface
3. **Train Users**: New interface is simpler but different
4. **Monitor Performance**: Compare with React version
5. **Gather Feedback**: User experience improvements

## Benefits vs React

### Advantages
- **No Build Process**: Direct HTML serving
- **Smaller Bundle**: ~50KB vs 2MB+ React bundle
- **Better SEO**: Server-rendered HTML
- **Simpler Debugging**: Server-side logs
- **Easier Testing**: Integration tests only
- **Lower Complexity**: No state management, routing libraries
- **Better Performance**: Faster initial page load
- **Easier Maintenance**: Single codebase (Python)

### Trade-offs
- **Less Interactive**: No SPA-like experience
- **Limited Offline**: Requires server connection
- **Simpler Animations**: Basic transitions only
- **Smaller Ecosystem**: Fewer third-party components

## Troubleshooting

### Common Issues

1. **Template Not Found**:
   - Check templates directory mounting
   - Verify Jinja2 configuration

2. **Static Files 404**:
   - Ensure static directory is mounted
   - Check file permissions

3. **Authentication Issues**:
   - Verify cookie settings
   - Check CORS configuration

4. **htmx Not Working**:
   - Ensure script is loaded
   - Check network requests in browser dev tools

5. **Alpine.js Errors**:
   - Check script loading order
   - Verify syntax in x-data functions

### Debugging

1. **Enable Debug Mode**:
   ```bash
   DEBUG=true LOG_LEVEL=DEBUG
   ```

2. **Check Browser Console**:
   - JavaScript errors
   - Network requests
   - Console logs

3. **Server Logs**:
   ```bash
   docker-compose logs -f app
   ```

4. **Database Issues**:
   ```bash
   docker-compose exec app alembic current
   docker-compose exec app alembic upgrade head
   ```

## Contributing

1. Follow existing code patterns
2. Use semantic HTML
3. Implement proper error handling
4. Add accessibility features
5. Test in multiple browsers
6. Document new features

## Support

- **Documentation**: Check `/docs` for API documentation
- **Issues**: Report bugs via GitHub issues
- **Community**: Join our Discord server
- **Email**: support@vertexar.com

---

This admin interface provides a modern, maintainable alternative to complex React applications while preserving all functionality and improving performance and developer experience.