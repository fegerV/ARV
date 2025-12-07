// src/services/analyticsService.ts
import api from './api';

export interface DateRange {
  start_date?: string;
  end_date?: string;
}

export interface AnalyticsFilters extends DateRange {
  company_id?: number;
  project_id?: number;
  content_id?: number;
}

export interface AnalyticsOverview {
  total_views: number;
  unique_sessions: number;
  avg_session_duration: number;
  avg_fps: number;
  tracking_success_rate: number;
  active_content: number;
  date_range: {
    start: string;
    end: string;
  };
}

export interface TrendDataPoint {
  date: string;
  views?: number;
  avg_duration?: number;
}

export interface TrendsData {
  views_trend: TrendDataPoint[];
  duration_trend: TrendDataPoint[];
  interval: string;
}

export interface TopContentItem {
  id: number;
  title: string;
  views: number;
  avg_duration: number;
}

export interface DeviceStat {
  device_type: string;
  count: number;
}

export interface BrowserStat {
  browser: string;
  count: number;
}

export interface FPSByDevice {
  device_type: string;
  avg_fps: number;
}

export interface DeviceStats {
  device_distribution: DeviceStat[];
  browser_distribution: BrowserStat[];
  fps_by_device: FPSByDevice[];
}

export interface EngagementMetrics {
  avg_first_session_duration: number;
  avg_sessions_per_user: number;
  hourly_distribution: { hour: number; count: number }[];
}

class AnalyticsService {
  /**
   * Get analytics overview with filters
   */
  async getOverview(filters: AnalyticsFilters = {}): Promise<AnalyticsOverview> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) {
        params.append(key, value.toString());
      }
    });
    
    const response = await api.get<AnalyticsOverview>(`/analytics/overview?${params.toString()}`);
    return response.data;
  }

  /**
   * Get trend data
   */
  async getTrends(filters: AnalyticsFilters & { interval?: string } = {}): Promise<TrendsData> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) {
        params.append(key, value.toString());
      }
    });
    
    const response = await api.get<TrendsData>(`/analytics/trends?${params.toString()}`);
    return response.data;
  }

  /**
   * Get top content by views
   */
  async getTopContent(filters: AnalyticsFilters & { limit?: number } = {}): Promise<TopContentItem[]> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) {
        params.append(key, value.toString());
      }
    });
    
    const response = await api.get<TopContentItem[]>(`/analytics/top-content?${params.toString()}`);
    return response.data;
  }

  /**
   * Get device and browser statistics
   */
  async getDeviceStats(filters: AnalyticsFilters = {}): Promise<DeviceStats> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) {
        params.append(key, value.toString());
      }
    });
    
    const response = await api.get<DeviceStats>(`/analytics/device-stats?${params.toString()}`);
    return response.data;
  }

  /**
   * Get engagement metrics
   */
  async getEngagementMetrics(filters: AnalyticsFilters = {}): Promise<EngagementMetrics> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) {
        params.append(key, value.toString());
      }
    });
    
    const response = await api.get<EngagementMetrics>(`/analytics/engagement?${params.toString()}`);
    return response.data;
  }
}

export const analyticsService = new AnalyticsService();