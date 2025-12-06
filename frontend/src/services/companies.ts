// services/companies.ts
import api from './api';

export interface Company {
  id: number;
  name: string;
  slug: string;
  contact_email?: string;
  contact_phone?: string;
  storage_connection_id: number;
  storage_path: string;
  storage_quota_gb: number;
  storage_used_bytes: number;
  storage_used_gb: number;
  is_active: boolean;
  subscription_tier?: string;
  subscription_expires_at?: string;
  created_at: string;
}

export interface CompanyCreate {
  name: string;
  slug: string;
  contact_email?: string;
  contact_phone?: string;
  storage_connection_id: number;
  storage_path: string;
  storage_quota_gb?: number;
}

export interface StorageConnection {
  id: number;
  name: string;
  provider: 'local_disk' | 'minio' | 'yandex_disk';
  is_active: boolean;
}

export const companiesApi = {
  create: (company: CompanyCreate) => 
    api.post<Company>('/api/companies', company),
  
  list: (params?: { page?: number; limit?: number }) => 
    api.get<{ companies: Company[]; total: number }>('/api/companies', { params }),
  
  get: (id: number) => 
    api.get<Company>(`/api/companies/${id}`),
  
  storageConnections: () => 
    api.get<StorageConnection[]>('/api/storage/connections'),
};

export const storageApi = {
  testConnection: (id: number) =>
    api.post(`/api/storage/connections/${id}/test`),
  
  yandexOAuth: (connectionName: string) =>
    api.get(`/api/oauth/yandex/authorize?connection_name=${connectionName}`),
};