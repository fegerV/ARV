// types/ar-content.ts
export interface ARContentCreate {
  project_id: number;
  title: string;
  description?: string;
  image_file: File;
}

export interface VideoUpload {
  id: string;
  file: File;
  title: string;
  duration?: number;
}

export interface VideoRotationRule {
  type: 'fixed' | 'daily' | 'date_specific' | 'random';
  default_video_id?: string;
  date_rules?: Array<{ date: string; video_id: string }>;
  video_sequence?: string[];
}

export interface ARContent {
  id: number;
  unique_id: string;
  title: string;
  image_url: string;
  marker_status: 'pending' | 'processing' | 'ready' | 'failed';
  marker_url?: string;
  qr_code_url?: string;
  videos: VideoUpload[];
  rotation_rule?: VideoRotationRule;
}