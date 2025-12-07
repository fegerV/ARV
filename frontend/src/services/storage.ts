// services/storage.ts
import api from './api';
import { StorageConnection } from '@/types/storage';

export interface StorageConnectionCreate {
  name: string;
  provider: 'yandex_disk' | 'minio';
  base_path: string;
  yandex_folder?: string;
  endpoint?: string;
  bucket?: string;
  region?: string;
  access_key?: string;
  secret_key?: string;
}

export interface StorageConnectionUpdate {
  name?: string;
  provider?: 'yandex_disk' | 'minio';
  base_path?: string;
  yandex_folder?: string;
  endpoint?: string;
  bucket?: string;
  region?: string;
  access_key?: string;
  secret_key?: string;
}

export const storageApi = {
  list: () => api.get<StorageConnection[]>('/api/storage/connections'),
  get: (id: number) => api.get<StorageConnection>(`/api/storage/connections/${id}`),
  create: (data: StorageConnectionCreate) =>
    api.post<StorageConnection>('/api/storage/connections', data),
  update: (id: number, data: StorageConnectionUpdate) =>
    api.put<StorageConnection>(`/api/storage/connections/${id}`, data),
  delete: (id: number) => api.delete(`/api/storage/connections/${id}`),
  test: (id: number) => api.post<{ success: boolean; message?: string }>(`/api/storage/connections/${id}/test`),
};