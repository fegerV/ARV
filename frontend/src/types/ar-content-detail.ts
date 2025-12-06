// types/ar-content-detail.ts
export interface CompanyInfo {
  id: number;
  name: string;
}

export interface ProjectInfo {
  id: number;
  name: string;
}

export interface VideoInfo {
  id: number;
  title: string;
  video_url: string;
  thumbnail_url: string;
  thumbnail_small_url?: string;
  thumbnail_large_url?: string;
  duration: number;
  width: number;
  height: number;
  mime_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VideoRotationRule {
  id: number;
  ar_content_id: number;
  type: 'fixed' | 'daily' | 'date_specific' | 'random';
  default_video_id?: number;
  default_video_title?: string;
  next_change_at?: string;
  next_change_at_readable?: string;
  type_human: string;
  created_at: string;
  updated_at: string;
}

export interface StatsInfo {
  views: number;
  unique_sessions: number;
  avg_duration: number;
  avg_fps: number;
}

export interface ARContentDetail {
  id: number;
  unique_id: string;
  title: string;
  description: string;
  company_id: number;
  company_name: string;
  project_id: number;
  project_name: string;
  image_url: string;
  thumbnail_url: string;
  image_width: number;
  image_height: number;
  image_size_readable: string;
  image_path: string;
  marker_status: 'pending' | 'processing' | 'ready' | 'failed';
  marker_url?: string;
  marker_path?: string;
  marker_feature_points?: number;
  videos: VideoInfo[];
  rotation_rule?: VideoRotationRule;
  stats: StatsInfo;
  created_at: string;
  updated_at: string;
}