// src/services/minioService.ts
import api from './api';

export interface PresignedURLRequest {
  bucket: string;
  object_name: string;
  expires_in?: number;
  method?: string;
}

export interface PresignedURLResponse {
  url: string;
  method: string;
  expires_at: string;
  fields: Record<string, string>;
}

class MinIOService {
  /**
   * Generate a presigned URL for direct MinIO upload
   * 
   * @param connectionId - ID of the storage connection
   * @param request - Presigned URL request parameters
   * @returns Presigned URL and related information
   */
  async generatePresignedURL(connectionId: number, request: PresignedURLRequest): Promise<PresignedURLResponse> {
    const response = await api.post<PresignedURLResponse>(
      `/storage/minio/presign-upload?connection_id=${connectionId}`,
      request
    );
    return response.data;
  }

  /**
   * Upload a file directly to MinIO using a presigned URL
   * 
   * @param presignedUrl - The presigned URL for upload
   * @param file - The file to upload
   * @param onProgress - Optional progress callback
   * @returns Promise that resolves when upload is complete
   */
  async uploadFileWithPresignedURL(
    presignedUrl: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      // Track upload progress if callback provided
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            onProgress(progress);
          }
        });
      }
      
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve();
        } else {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      });
      
      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });
      
      xhr.open('PUT', presignedUrl);
      xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
      xhr.send(file);
    });
  }
}

export const minioService = new MinIOService();