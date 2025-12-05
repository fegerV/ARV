import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// API methods
export const arContentAPI = {
  getDetail: (id: number) => api.get(`/ar-content/${id}`),
  update: (id: number, data: any) => api.put(`/ar-content/${id}`, data),
  delete: (id: number) => api.delete(`/ar-content/${id}`),
};

export const companiesAPI = {
  list: () => api.get('/companies'),
  get: (id: number) => api.get(`/companies/${id}`),
  create: (data: any) => api.post('/companies', data),
  update: (id: number, data: any) => api.put(`/companies/${id}`, data),
  delete: (id: number) => api.delete(`/companies/${id}`),
};

export const projectsAPI = {
  list: (companyId: number) => api.get(`/companies/${companyId}/projects`),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (companyId: number, data: any) => api.post(`/companies/${companyId}/projects`, data),
};

export const analyticsAPI = {
  overview: () => api.get('/analytics/overview'),
  arContent: (id: number, days: number = 30) => api.get(`/analytics/ar-content/${id}?days=${days}`),
};
