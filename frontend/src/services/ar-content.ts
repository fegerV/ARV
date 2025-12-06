// services/ar-content.ts
import api from './api';
import { ARContent } from '../types/ar-content';
import { ARContentDetail } from '../types/ar-content-detail';

export const arContentApi = {
  create: (data: FormData) =>
    api.post<{ id: number }>('/api/projects/:projectId/ar-content', data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  
  generateMarker: (id: number) =>
    api.post(`/api/ar-content/${id}/generate-marker`),
  
  uploadVideos: (arContentId: number, videos: FormData[]) =>
    Promise.all(
      videos.map(video => 
        api.post(`/api/ar-content/${arContentId}/videos`, video, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      )
    ),
  
  get: (id: number) => api.get<ARContentDetail>(`/api/ar-content/${id}`),
  
  pollStatus: (id: number) =>
    api.get(`/api/ar-content/${id}`),
  
  list: (params: {
    search?: string;
    company_id?: number;
    project_id?: number;
    marker_status?: string;
    is_active?: boolean;
    date_from?: string;
    date_to?: string;
    page?: number;
    limit?: number;
  } = {}) =>
    api.get<{
      contents: ARContent[];
      total: number;
      page: number;
      limit: number;
    }>('/api/ar-content', { params }),
};