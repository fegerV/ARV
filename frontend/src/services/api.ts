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
      api.get<YandexDiskFoldersResponse>(`/api/oauth/yandex/${connectionId}/folders?path=${encodeURIComponent(path)}`),
    createFolder: (connectionId: number, folderPath: string) =>
      api.post<{ status: string; message: string; path: string }>(
        `/api/oauth/yandex/${connectionId}/create-folder?folder_path=${encodeURIComponent(folderPath)}`
      ),
  },
};