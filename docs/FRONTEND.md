# Frontend Architecture Documentation

## Overview
The frontend of the Vertex AR application is a React 18 application built with TypeScript, Material-UI, and Zustand for state management. It serves as an admin panel for managing AR content, companies, projects, and storage connections.

## Table of Contents
1. [Project Structure](#project-structure)
2. [React 18 Setup and Configuration](#react-18-setup-and-configuration)
3. [Main Pages and Their Purpose](#main-pages-and-their-purpose)
4. [Components: Classification and Usage](#components-classification-and-usage)
5. [State Management](#state-management)
6. [API Integration](#api-integration)
7. [Routing](#routing)
8. [Styling](#styling)
9. [Authentication Flow](#authentication-flow)
10. [Forms and Validation](#forms-and-validation)
11. [Environment Configuration](#environment-configuration)
12. [Build and Deployment](#build-and-deployment)
13. [Testing](#testing)
14. [Performance Optimization and Best Practices](#performance-optimization-and-best-practices)

## Project Structure

```
frontend/
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   ├── theme.ts
│   ├── components/
│   │   ├── auth/
│   │   │   └── ProtectedRoute.tsx
│   │   ├── common/
│   │   │   ├── ThemeToggle.tsx
│   │   │   └── ToastNotification.tsx
│   │   └── layout/
│   │       └── Sidebar.tsx
│   ├── hooks/
│   │   ├── useKeyboardShortcuts.ts
│   │   └── useSystemTheme.ts
│   ├── pages/
│   │   ├── Analytics.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Login.tsx
│   │   ├── Notifications.tsx
│   │   ├── Settings.tsx
│   │   ├── Storage.tsx
│   │   ├── ar-content/
│   │   │   ├── ARContentDetail.tsx
│   │   │   ├── ARContentForm.tsx
│   │   │   └── ARContentList.tsx
│   │   ├── companies/
│   │   │   ├── CompaniesList.tsx
│   │   │   ├── CompanyDetails.tsx
│   │   │   └── CompanyForm.tsx
│   │   ├── oauth/
│   │   │   └── YandexDiskCallback.tsx
│   │   └── projects/
│   │       ├── ProjectForm.tsx
│   │       └── ProjectsList.tsx
│   ├── providers/
│   │   └── ThemeProvider.tsx
│   ├── services/
│   │   └── api.ts
│   ├── store/
│   │   ├── authStore.ts
│   │   ├── themeStore.ts
│   │   └── useToast.ts
│   ├── test/
│   │   └── setup.ts
│   ├── utils/
│   │   └── qrCodeExport.ts
│   └── types/
```

### Directory Descriptions:

- **src/**: Main source code directory
- **components/**: Reusable UI components organized by category (auth, common, layout)
- **hooks/**: Custom React hooks for shared logic
- **pages/**: Route-level components, organized by feature
- **providers/**: React context providers
- **services/**: API clients and business logic services
- **store/**: Zustand stores for global state management
- **test/**: Test utilities and configuration
- **utils/**: Utility functions
- **types/**: TypeScript type definitions

## React 18 Setup and Configuration

The application is built with React 18 and uses the following key technologies:

- **React 18**: With concurrent features and StrictMode
- **TypeScript**: For type safety
- **Vite**: As the build tool and development server
- **React Router DOM**: For client-side routing
- **Material-UI (MUI)**: Component library for UI elements
- **Zustand**: State management solution
- **Axios**: HTTP client for API requests

### Main Entry Point (src/main.tsx)

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { VertexThemeProvider } from './providers/ThemeProvider'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter future={{
      v7_startTransition: true,
      v7_relativeSplatPath: true
    }}>
      <VertexThemeProvider>
        <App />
      </VertexThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
```

The application uses React's StrictMode for development, BrowserRouter for routing, and a custom theme provider.

## Main Pages and Their Purpose

### Login Page (src/pages/Login.tsx)
- Handles user authentication
- Provides form for email/password login
- Includes security features like rate limiting and account lockout
- Supports password visibility toggle
- Redirects to dashboard after successful login

### Dashboard Page (src/pages/Dashboard.tsx)
- Overview of key metrics and analytics
- Shows total AR views, unique sessions, active content, and storage usage
- Displays recent activity feed
- Serves as the main landing page after login

### AR Content Pages
- **ARContentList**: Displays all AR content with filtering and search capabilities
- **ARContentForm**: Form for creating/editing AR content with media upload
- **ARContentDetail**: Shows detailed information about specific AR content

### Company Management Pages
- **CompaniesList**: Lists all companies
- **CompanyForm**: Form for creating/editing companies
- **CompanyDetails**: Shows detailed information about a specific company

### Project Management Pages
- **ProjectsList**: Lists projects within a company
- **ProjectForm**: Form for creating/editing projects

### Other Pages
- **Analytics**: Detailed analytics and reporting
- **Storage**: Management of storage connections (local, MinIO, Yandex Disk)
- **Notifications**: Notification management
- **Settings**: User settings and preferences

## Components: Classification and Usage

### Layout Components
- **Sidebar**: Navigation sidebar with collapsible menu
- **ProtectedRoute**: Wrapper component that ensures authentication before rendering children

### Common Components
- **ThemeToggle**: Component for switching between light/dark/system themes
- **ToastNotification**: Global notification system using Material-UI alerts

### Auth Components
- **ProtectedRoute**: Ensures only authenticated users can access protected routes

### Component Classification

1. **Layout Components**: Handle page structure and navigation
2. **UI Components**: Presentational components with minimal logic
3. **Form Components**: Handle user input and form submission
4. **Data Components**: Fetch and display data from APIs
5. **Utility Components**: Provide shared functionality across the app

### Example Component Structure
```tsx
// Example of a typical component structure
import { useState, useEffect } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { useToast } from '../store/useToast';

interface MyComponentProps {
  id: string;
}

export default function MyComponent({ id }: MyComponentProps) {
  const [data, setData] = useState<any>(null);
  const { addToast } = useToast();
  
  useEffect(() => {
    // Data fetching logic
  }, [id]);
  
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6">Component Title</Typography>
      {/* Component content */}
    </Paper>
  );
}
```

## State Management

The application uses Zustand for state management, providing a lightweight and intuitive solution for global state. The following stores are implemented:

### Authentication Store (src/store/authStore.ts)
- Manages user authentication state
- Handles token storage in localStorage
- Provides login, logout, and user update functions
- Persists state across browser sessions

```ts
interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  last_login_at?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (data: { access_token: string; user: User }) => void;
  logout: () => void;
  updateUser: (user: User) => void;
}
```

### Theme Store (src/store/themeStore.ts)
- Manages application theme (light/dark/system)
- Persists theme preference in localStorage
- Provides theme switching functionality

### Toast Store (src/store/useToast.ts)
- Manages global toast notifications
- Handles success, error, warning, and info messages
- Automatically dismisses toasts after a specified duration

## API Integration

### API Service (src/services/api.ts)
The application uses Axios for HTTP requests with the following configuration:

- Base URL: `/api` (relative to the frontend)
- 30-second timeout
- Authorization header with Bearer token from localStorage
- Response interceptor for handling 401 unauthorized errors
- Dedicated API methods for different entities

### API Method Categories
- **authAPI**: Login, logout, user profile
- **arContentAPI**: AR content management (list, create, detail)
- **companiesAPI**: Company management
- **projectsAPI**: Project management within companies
- **analyticsAPI**: Analytics and reporting
- **notificationsAPI**: Notification management
- **settingsAPI**: User settings
- **storageAPI**: Storage connection management

### Example API Usage
```tsx
// In a component
import { arContentAPI } from '../services/api';

const [contentList, setContentList] = useState([]);

useEffect(() => {
  const fetchContent = async () => {
    try {
      const response = await arContentAPI.listAll();
      setContentList(response.data.items);
    } catch (error) {
      console.error('Error fetching content:', error);
    }
  };
  
  fetchContent();
}, []);
```

## Routing

The application uses React Router DOM for client-side routing with the following structure:

### Main Routes
- `/login` - Public login page
- `/oauth/yandex/callback` - OAuth callback for Yandex integration
- `/` - Dashboard (protected)
- `/companies` - Companies list (protected)
- `/companies/new` - Create new company (protected)
- `/companies/:id` - Company details (protected)
- `/projects` - Projects list (protected)
- `/companies/:companyId/projects` - Projects list for a company (protected)
- `/companies/:companyId/projects/new` - Create new project (protected)
- `/ar-content` - AR content list (protected)
- `/ar-content/new` - Create new AR content (protected)
- `/ar-content/:arContentId` - AR content detail (protected)
- `/analytics` - Analytics dashboard (protected)
- `/storage` - Storage management (protected)
- `/notifications` - Notifications (protected)
- `/settings` - Settings (protected)

### Protected Route Implementation
The application uses a `ProtectedRoute` component that checks authentication status and redirects unauthenticated users to the login page.

## Styling

### Theme System
The application uses Material-UI's theme system with a custom theme provider:

- **ThemeProvider**: Custom provider that manages light/dark/system themes
- **Theme Toggle**: Supports keyboard shortcuts (Ctrl+T or Ctrl+B) for theme switching
- **CSS Baseline**: Enables proper color scheme support

### Custom Theme (src/providers/ThemeProvider.tsx)
- Light and dark theme variants with custom color palettes
- Consistent typography with Inter/Roboto fonts
- Custom component styling for MUI components
- Responsive design with mobile-first approach

### Styling Approach
- Material-UI components for consistent UI
- MUI's sx prop for custom styling
- CSS variables for theme consistency
- Responsive design with breakpoints

## Authentication Flow

### Login Process
1. User enters email and password
2. Form data is sent to `/api/auth/login` endpoint
3. Server returns access token and user information
4. Token is stored in localStorage and Zustand store
5. User is redirected to dashboard

### Token Management
- Access token stored in localStorage
- Token automatically added to Authorization header for API requests
- 401 responses trigger automatic logout and redirect to login

### Protected Routes
- All routes except `/login` and OAuth callbacks are protected
- `ProtectedRoute` component checks authentication status
- Unauthenticated users are redirected to login page

### Logout Process
- Token is removed from localStorage and store
- User is redirected to login page
- All session-related data is cleared

## Forms and Validation

### Form Handling
- React Hook Form is not used; forms use controlled components with React state
- Validation is performed before form submission
- Error messages are displayed to users

### Example Form Validation
```tsx
const validateForm = (): string | null => {
  if (!formData.name.trim()) {
    return 'Content name is required';
  }
  
  if (!formData.customerName.trim()) {
    return 'Customer name is required';
  }
  
  if (!formData.customerEmail.trim()) {
    return 'Customer email is required';
  }
  
  if (!formData.companyId) {
    return 'Please select a company';
  }
  
  if (!formData.image) {
    return 'Please upload an image';
  }
  
  return null;
};
```

### Form Components
- **TextField**: For text input with validation
- **Select**: For dropdown selections
- **File Input**: For media uploads
- **Checkbox/Radio**: For boolean and choice inputs
- **Date/Time Pickers**: For scheduling

## Environment Configuration

### Environment Variables
The application uses Vite's environment variable system:

- `.env` - General environment variables
- `.env.local` - Local environment variables (not committed)
- `.env.example` - Example environment variables

### Configuration Files
- **vite.config.ts**: Vite build configuration
- **tsconfig.json**: TypeScript configuration
- **tailwind.config.js**: Tailwind CSS configuration (if used)

## Build and Deployment

### Build Process
The application uses Vite for building:

```bash
# Development
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Build Configuration (vite.config.ts)
- TypeScript and JSX compilation
- Asset optimization
- Code splitting
- Production-ready output

### Deployment
The frontend is designed to work with the backend API server, expecting the API to be available at `/api` relative to the frontend.

## Testing

### Testing Framework
- **Jest**: JavaScript testing framework
- **React Testing Library**: For component testing
- **@testing-library/jest-dom**: Custom Jest matchers

### Test Configuration
- **jest.config.js**: Jest configuration file
- **src/test/setup.ts**: Test setup and configuration
- **__tests__** directories: Component and utility tests

### Example Test
```tsx
// Example test file
import { render, screen, fireEvent } from '@testing-library/react';
import Login from '../pages/Login';

test('renders login form', () => {
  render(<Login />);
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
});
```

## Performance Optimization and Best Practices

### Code Splitting
- React.lazy and Suspense for route-level code splitting
- Component-level splitting where appropriate

### State Management
- Zustand for efficient global state management
- Local state for component-specific data
- Memoization with useMemo and useCallback where needed

### Data Fetching
- API caching considerations
- Loading states and error handling
- Pagination for large datasets

### Component Optimization
- Proper use of React.memo for components with expensive renders
- useCallback for functions passed to child components
- useMemo for expensive calculations

### Performance Monitoring
- Console logging during development (removed in production)
- Loading indicators for async operations
- Error boundaries for graceful error handling

### Security Considerations
- CSRF protection through proper authentication
- Input sanitization and validation
- Secure token storage and transmission
- Rate limiting handled on the backend

### Best Practices Implemented
- TypeScript for type safety
- Consistent component structure
- Separation of concerns
- Reusable components
- Proper error handling
- Accessibility considerations
- Responsive design
- Clean, maintainable code structure