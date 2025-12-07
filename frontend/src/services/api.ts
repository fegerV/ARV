import axios from 'axios';
import { toast } from 'react-hot-toast';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      toast.error('Проблема с сетью. Проверьте подключение.');
      return Promise.reject(error);
    }

    const { status, data } = error.response;
    const detail: string =
      data?.detail ||
      data?.message ||
      'Произошла непредвиденная ошибка';

    // 4xx — показываем сообщение пользователю
    if (status >= 400 && status < 500) {
      toast.error(detail);
    } else if (status >= 500) {
      toast.error('Сервер временно недоступен. Попробуйте позже.');
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
  list: (params?: { include_default?: boolean }) => api.get('/companies', { params }),
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
