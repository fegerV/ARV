# Migration Guide: React to HTML + Jinja2 + htmx/Alpine.js

## Overview
This guide provides step-by-step instructions for migrating from the React frontend to a simpler HTML + Jinja2 + htmx/Alpine.js stack.

## Prerequisites
- FastAPI backend is running and functional
- Database is properly configured
- Authentication system is working

## Step 1: Update Docker Configuration

### 1.1 Remove Frontend Build Service
Remove the frontend build service from `docker-compose.yml` and update the main app service:

```yaml
# Remove this entire service
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  # ... rest of frontend config
```

### 1.2 Update App Service
Update the app service to serve HTML templates:

```yaml
app:
  build:
    context: .
    dockerfile: Dockerfile.dev
  volumes:
    - .:/app
    - ./storage:/app/storage
    - ./templates:/app/templates  # Add templates volume
  ports:
    - "8000:8000"
  environment:
    - DATABASE_URL=postgresql+asyncpg://vertex_ar:password@postgres:5432/vertex_ar
    - PUBLIC_URL=http://localhost:8000
    - MEDIA_ROOT=/app/storage/content
    - LOG_LEVEL=INFO
    - TEMPLATES_DIR=/app/templates  # Add templates directory
  depends_on:
    postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/status"]
    interval: 30s
    timeout: 10s
    retries: 3
  networks:
    - vertex_net
```

### 1.3 Update Dockerfile.dev
Ensure the Dockerfile.dev includes Jinja2 templates:

```dockerfile
# Add to Dockerfile.dev
COPY ./templates /app/templates
```

## Step 2: Update FastAPI Configuration

### 2.1 Template Configuration
The main.py file already includes Jinja2 template configuration:

```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
```

### 2.2 Static Files
Ensure static files are properly served:

```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```

## Step 3: Authentication Integration

### 3.1 Update Login Flow
The new login page uses form-based authentication. Update the auth routes to support both API and form-based login:

```python
# In app/api/routes/auth.py
@router.post("/login", response_class=HTMLResponse)
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_async_session)
):
    # Handle form-based login
    # Set cookie and redirect to /admin
```

### 3.2 Cookie-based Authentication
Update authentication to use cookies for the HTML interface:

```python
# In auth.py
def create_access_token_cookie(response: Response, access_token: str):
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=3600,
        expires=3600,
        path="/",
        secure=False,  # Set to True in production with HTTPS
        httponly=True,
        samesite="lax",
    )
```

## Step 4: Route Updates

### 4.1 Main Route Redirect
Update the main route to redirect to the admin interface:

```python
@app.get("/", response_class=RedirectResponse)
async def root(current_user: User = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse("/admin")
    return RedirectResponse("/admin/login")
```

### 4.2 Protected Routes
All admin routes should require authentication:

```python
@router.get("/admin", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    # Serve dashboard
```

## Step 5: Template Development

### 5.1 Base Template
The base template (`templates/base.html`) includes:
- Tailwind CSS from CDN
- htmx and Alpine.js from CDN
- Responsive sidebar navigation
- Toast notification system
- Modal system
- Dark mode support

### 5.2 Component Templates
Create reusable components in `templates/components/`:
- `sidebar.html` - Navigation sidebar
- `header.html` - Top header with user menu
- `toast.html` - Toast notification system
- `modals.html` - Modal dialog system
- `pagination.html` - Pagination component

### 5.3 Page Templates
Create page-specific templates:
- `dashboard/index.html` - Main dashboard
- `companies/list.html` - Companies list with CRUD
- `companies/form.html` - Company create/edit form
- `companies/detail.html` - Company details
- Similar structure for projects and AR content

## Step 6: htmx Integration

### 6.1 Dynamic Table Updates
Use htmx for partial page updates:

```html
<div hx-get="/admin/companies/table" 
     hx-trigger="revealed" 
     hx-target="#companies-tbody">
    <!-- Table content -->
</div>
```

### 6.2 Form Submissions
Handle form submissions with htmx:

```html
<form hx-post="/admin/companies" 
      hx-target="#companies-container" 
      hx-swap="innerHTML">
    <!-- Form fields -->
</form>
```

### 6.3 Search and Filter
Implement real-time search:

```html
<input type="text" 
       hx-get="/admin/companies/search" 
       hx-trigger="keyup changed delay:500ms"
       hx-target="#results">
```

## Step 7: Alpine.js Integration

### 7.1 Local State Management
Use Alpine.js for client-side state:

```javascript
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>
    <div x-show="open" x-transition>
        <!-- Content -->
    </div>
</div>
```

### 7.2 Form Validation
Implement client-side validation:

```javascript
<form x-data="formValidator()" @submit="validateAndSubmit">
    <!-- Form fields with validation -->
</form>
```

## Step 8: API Integration

### 8.1 Fetch API Usage
Use the Fetch API for data loading:

```javascript
async function loadCompanies() {
    const response = await fetch('/api/companies', {
        headers: {
            'Authorization': `Bearer ${getAuthToken()}`
        }
    });
    const data = await response.json();
    return data;
}
```

### 8.2 Error Handling
Implement proper error handling:

```javascript
try {
    const data = await loadCompanies();
    // Update UI
} catch (error) {
    showToast('Failed to load data', 'error');
}
```

## Step 9: Testing

### 9.1 Manual Testing
Test all major functionality:
- Login/logout flow
- Dashboard loading
- CRUD operations for companies
- CRUD operations for projects
- CRUD operations for AR content
- Navigation and routing

### 9.2 Automated Testing
Set up end-to-end tests using Playwright or Cypress:

```javascript
// Example Playwright test
test('can login and view dashboard', async ({ page }) => {
    await page.goto('/admin/login');
    await page.fill('[name="email"]', 'admin@vertex.local');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/admin');
});
```

## Step 10: Deployment

### 10.1 Production Configuration
Update production configuration:

```python
# In app/core/config.py
class Settings:
    # ... existing settings
    TEMPLATES_DIR: str = "/app/templates"
    STATIC_DIR: str = "/app/static"
    PRODUCTION: bool = os.getenv("ENVIRONMENT") == "production"
```

### 10.2 SSL Configuration
Configure SSL for production:

```python
# In main.py
if settings.PRODUCTION:
    app.add_middleware(
        HTTPSRedirectMiddleware,
    )
```

### 10.3 CDN Configuration
For production, consider self-hosting static assets:

```html
<!-- Instead of CDN -->
<link rel="stylesheet" href="/static/css/tailwind.css">
<script src="/static/js/htmx.min.js"></script>
<script src="/static/js/alpine.min.js"></script>
```

## Step 11: Cleanup

### 11.1 Remove React Dependencies
Remove the frontend directory and all React-related files:

```bash
rm -rf frontend/
rm package.json
rm package-lock.json
rm vite.config.ts
rm tsconfig.json
rm tailwind.config.js
```

### 11.2 Update Documentation
Update README.md and other documentation:

```markdown
# Frontend Technology Stack
- **Templates**: Jinja2
- **Styling**: Tailwind CSS
- **Dynamic Updates**: htmx
- **Local State**: Alpine.js
- **Icons**: Font Awesome
```

### 11.3 Update CI/CD
Update CI/CD pipelines to remove frontend build steps:

```yaml
# Remove frontend build steps
# - name: Build frontend
#   run: npm run build
```

## Step 12: Monitoring

### 12.1 Performance Monitoring
Monitor page load times and user experience:

```javascript
// Add performance monitoring
window.addEventListener('load', function() {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
    // Send to analytics
});
```

### 12.2 Error Tracking
Implement error tracking:

```javascript
window.addEventListener('error', function(event) {
    // Send error to monitoring service
    console.error('Page error:', event.error);
});
```

## Migration Checklist

- [ ] Update Docker configuration
- [ ] Create base template and components
- [ ] Implement authentication flow
- [ ] Create dashboard page
- [ ] Create companies CRUD pages
- [ ] Create projects CRUD pages
- [ ] Create AR content CRUD pages
- [ ] Implement htmx dynamic updates
- [ ] Add Alpine.js interactions
- [ ] Test all functionality
- [ ] Update production configuration
- [ ] Remove React dependencies
- [ ] Update documentation
- [ ] Deploy and monitor

## Troubleshooting

### Common Issues

1. **Template Not Found**
   - Ensure templates directory is properly mounted in Docker
   - Check template path in Jinja2Templates configuration

2. **Static Files Not Loading**
   - Verify static files directory is properly configured
   - Check file permissions

3. **Authentication Issues**
   - Ensure cookies are being set correctly
   - Check CORS configuration

4. **htmx Not Working**
   - Verify htmx script is loaded
   - Check hx-* attributes are correctly formatted

5. **Alpine.js Errors**
   - Ensure Alpine.js script is loaded after htmx
   - Check x-data syntax

## Performance Optimization

### 1. Asset Optimization
- Minimize external dependencies
- Use CDN for static assets
- Implement caching headers

### 2. Database Optimization
- Use efficient queries
- Implement pagination
- Add database indexes

### 3. Caching Strategy
- Cache frequently accessed data
- Use Redis for session storage
- Implement browser caching

This migration guide provides a comprehensive roadmap for transitioning from React to a simpler, more maintainable HTML-based frontend while preserving all existing functionality.