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
    console.log('API error interceptor triggered:', error);
    if (error.response?.status === 401) {
      console.log('401 error, redirecting to /login');
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Authentication API methods
export const authAPI = {
  login: (credentials: { username: string; password: string }) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  register: (userData: any) => api.post('/auth/register', userData),
};

// API methods
export const arContentAPI = {
  listAll: (params?: { page?: number; page_size?: number; company_id?: number; project_id?: string; status?: string; search?: string }) =>
    api.get('/ar-content', { params }),
  getDetail: (id: string) => api.get(`/ar-content/${id}`),
  getDetailByHierarchy: (companyId: string, projectId: string, id: string) => api.get(`/companies/${companyId}/projects/${projectId}/ar-content/${id}`),
  getDetailWithIds: (id: string) => api.get(`/ar-content/${id}`),
  create: (companyId: string, projectId: string, formData: FormData) => api.post(`/companies/${companyId}/projects/${projectId}/ar-content`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
  listByProject: (companyId: string, projectId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/companies/${companyId}/projects/${projectId}/ar-content`, { params }),
  updateVideo: (companyId: string, projectId: string, contentId: string, formData: FormData) =>
    api.patch(`/companies/${companyId}/projects/${projectId}/ar-content/${contentId}/video`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  delete: (id: string) => api.delete(`/ar-content/${id}`),
  deleteByHierarchy: (companyId: string, projectId: string, contentId: string) =>
    api.delete(`/companies/${companyId}/projects/${projectId}/ar-content/${contentId}`),
};

export const companiesAPI = {
  list: (params?: { page?: number; page_size?: number; search?: string; status?: string }) => api.get('/companies', { params }),
  get: (id: string) => api.get(`/companies/${id}`),
  create: (data: any) => api.post('/companies', data),
  update: (id: string, data: any) => api.put(`/companies/${id}`, data),
  delete: (id: string) => api.delete(`/companies/${id}`),
};

export const projectsAPI = {
  listByCompany: (companyId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/companies/${companyId}/projects`, { params }),
  get: (companyId: string, id: string) => api.get(`/companies/${companyId}/projects/${id}`),
  create: (companyId: string, data: any) => api.post(`/companies/${companyId}/projects`, data),
  update: (companyId: string, id: string, data: any) => api.put(`/companies/${companyId}/projects/${id}`, data),
  delete: (companyId: string, id: string) => api.delete(`/companies/${companyId}/projects/${id}`),
};

export const analyticsAPI = {
  summary: () => api.get('/analytics/summary'),
  overview: () => api.get('/analytics/overview'),
  company: (companyId: string) => api.get(`/analytics/companies/${companyId}`),
};

export const notificationsAPI = {
  list: (limit: number = 50) => api.get('/notifications', { params: { limit } }),
  markRead: (ids: number[]) => api.post('/notifications/mark-read', ids),
  delete: (id: number) => api.delete(`/notifications/${id}`),
};

export const settingsAPI = {
 get: () => api.get('/settings'),
};

// Storage Connections API
export interface StorageConnection {
  id: number;
  name: string;
  provider: 'local_disk' | 'minio' | 'yandex_disk';
  is_active: boolean;
  base_path?: string;
  is_default?: boolean;
  last_tested_at?: string;
  test_status?: string;
  test_error?: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface StorageConnectionCreate {
  name: string;
  provider: 'local_disk' | 'minio' | 'yandex_disk';
  base_path?: string;
  is_default?: boolean;
  credentials?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface StorageConnectionUpdate {
  name?: string;
  is_active?: boolean;
  credentials?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface YandexDiskFolder {
  name: string;
  path: string;
  type: string;
  created: string;
  modified: string;
  last_modified: string;
}

export interface YandexDiskFoldersResponse {
  current_path: string;
  folders: YandexDiskFolder[];
  parent_path: string;
  has_parent: boolean;
}

export const storageAPI = {
  // Storage Connections
  list: () => api.get<StorageConnection[]>('/storage/connections'),
  get: (id: number) => api.get<StorageConnection>(`/storage/connections/${id}`),
  create: (data: StorageConnectionCreate) => api.post<StorageConnection>('/storage/connections', data),
  update: (id: number, data: StorageConnectionUpdate) => api.put<StorageConnection>(`/storage/connections/${id}`, data),
  delete: (id: number) => api.delete(`/storage/connections/${id}`),
  test: (id: number) => api.post<{ status: string; message: string }>(`/storage/connections/${id}/test`),

  // Yandex Disk specific
  yandex: {
    listFolders: (connectionId: number, path: string = '/') =>
      api.get<YandexDiskFoldersResponse>(`/oauth/${connectionId}/folders?path=${encodeURIComponent(path)}`),
    createFolder: (connectionId: number, folderPath: string) =>
      api.post<{ status: string; message: string; path: string }>(
        `/oauth/${connectionId}/create-folder?folder_path=${encodeURIComponent(folderPath)}`
      ),
  },
};