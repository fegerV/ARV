import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // Увеличиваем таймаут до 30 секунд
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
  listAll: () => api.get('/ar-content'),
  list: (companyId: number, projectId: number) => api.get(`/companies/${companyId}/projects/${projectId}/ar-content`),
  getDetail: (id: number) => api.get(`/ar-content/${id}`),
  get: (companyId: number, projectId: number, contentId: number) => api.get(`/companies/${companyId}/projects/${projectId}/ar-content/${contentId}`),
  create: (companyId: number, projectId: number, formData: FormData) => api.post(`/companies/${companyId}/projects/${projectId}/ar-content/new`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
  update: (companyId: number, projectId: number, contentId: number, data: any) => api.put(`/companies/${companyId}/projects/${projectId}/ar-content/${contentId}`, data),
  patchVideo: (companyId: number, projectId: number, contentId: number, videoFile: File) => {
    const formData = new FormData();
    formData.append('video', videoFile);
    return api.patch(`/companies/${companyId}/projects/${projectId}/ar-content/${contentId}/video`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  delete: (companyId: number, projectId: number, contentId: number) => api.delete(`/companies/${companyId}/projects/${projectId}/ar-content/${contentId}`),
  generateMarker: (id: number) => api.post(`/ar-content/${id}/generate-marker`),
};

export const companiesAPI = {
  list: (includeDefault: boolean = false) => api.get(`/companies?include_default=${includeDefault}`),
  get: (id: number) => api.get(`/companies/${id}`),
  create: (data: any) => api.post('/companies', data),
  update: (id: number, data: any) => api.put(`/companies/${id}`, data),
  delete: (id: number) => api.delete(`/companies/${id}`),
};

export const projectsAPI = {
  list: (companyId: number) => api.get(`/companies/${companyId}/projects`),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (companyId: number, data: any) => api.post(`/companies/${companyId}/projects`, data),
  delete: (id: number) => api.delete(`/projects/${id}`),
};

export const analyticsAPI = {
  overview: () => api.get('/analytics/overview'),
  arContent: (id: number, days: number = 30) => api.get(`/analytics/ar-content/${id}?days=${days}`),
};