// types/storage.ts
export type StorageProvider = 'local_disk' | 'yandex_disk' | 'minio';

export interface StorageConnection {
  id: number;
  name: string;
  provider: StorageProvider;
  is_default: boolean;
  is_active: boolean;

  // общие поля
  base_path: string;

  // Yandex
  yandex_folder?: string;

  // MinIO/S3
  endpoint?: string;
  bucket?: string;
  region?: string;
  access_key?: string;
  secret_key_masked?: string;

  created_at: string;
}