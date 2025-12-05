import { http, HttpResponse } from 'msw';

const API_BASE = 'http://localhost:8000/api';

export const handlers = [
  // Auth endpoints
  http.post(`${API_BASE}/auth/login`, async ({ request }) => {
    const body = await request.json() as { username: string; password: string };
    
    if (body.username === 'admin@test.com' && body.password === 'password123') {
      return HttpResponse.json({
        access_token: 'mock-jwt-token',
        token_type: 'bearer',
        user: {
          id: 1,
          email: 'admin@test.com',
          role: 'admin',
          last_login: '2025-12-05T10:00:00Z',
        },
      });
    }
    
    return HttpResponse.json(
      { detail: 'Неверный email или пароль' },
      { status: 401 }
    );
  }),

  // Companies endpoints
  http.get(`${API_BASE}/companies`, () => {
    return HttpResponse.json({
      companies: [
        {
          id: 1,
          name: 'Test Agency',
          storage_used_gb: 5.2,
          storage_provider: 'local',
          active_projects: 3,
          created_at: '2025-01-01T00:00:00Z',
        },
      ],
      total: 1,
    });
  }),

  http.post(`${API_BASE}/companies`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      id: 999,
      name: body.name,
      storage_used_gb: 0,
      storage_provider: body.storage_provider || 'local',
      active_projects: 0,
      created_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  http.get(`${API_BASE}/companies/:id`, ({ params }) => {
    return HttpResponse.json({
      id: parseInt(params.id as string),
      name: 'Test Agency',
      storage_used_gb: 5.2,
      storage_provider: 'local',
      active_projects: 3,
      created_at: '2025-01-01T00:00:00Z',
    });
  }),

  // Projects endpoints
  http.get(`${API_BASE}/companies/:companyId/projects`, () => {
    return HttpResponse.json({
      projects: [
        {
          id: 1,
          name: 'Test Project',
          company_id: 1,
          subscription_end: '2025-12-31T23:59:59Z',
          is_active: true,
          ar_content_count: 5,
        },
      ],
      total: 1,
    });
  }),

  http.post(`${API_BASE}/companies/:companyId/projects`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      id: 888,
      name: body.name,
      company_id: parseInt(body.company_id),
      subscription_end: body.subscription_end,
      is_active: true,
      ar_content_count: 0,
    }, { status: 201 });
  }),

  // AR Content endpoints
  http.get(`${API_BASE}/projects/:projectId/ar-content`, () => {
    return HttpResponse.json({
      ar_contents: [
        {
          id: 1,
          project_id: 1,
          unique_id: 'abc123',
          is_active: true,
          marker_status: 'ready',
          video_count: 3,
          qr_code_url: 'http://localhost:8000/qr/abc123.png',
        },
      ],
      total: 1,
    });
  }),

  // Analytics endpoints
  http.get(`${API_BASE}/analytics/overview`, () => {
    return HttpResponse.json({
      total_companies: 12,
      total_projects: 45,
      total_ar_content: 234,
      total_views_today: 1567,
      avg_fps: 58.3,
      storage_used_gb: 125.4,
    });
  }),

  // Health check
  http.get(`${API_BASE}/health/status`, () => {
    return HttpResponse.json({
      status: 'healthy',
      version: '1.0.0',
      database: 'connected',
      redis: 'connected',
    });
  }),
];
