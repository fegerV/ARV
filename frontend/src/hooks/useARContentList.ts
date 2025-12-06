// hooks/useARContentList.ts
import { useState, useCallback } from 'react';

interface FilterState {
  search: string;
  company_id?: number;
  project_id?: number;
  marker_status?: string;
  is_active?: boolean;
  date_from?: string;
  date_to?: string;
}

interface ARContent {
  id: number;
  title: string;
  unique_id: string;
  image_url?: string;
  thumbnail_url?: string;
  company_name?: string;
  videos_count: number;
  marker_status: 'pending' | 'processing' | 'ready' | 'failed';
  views: number;
  created_at: string;
  expires_at?: string;
}

export const useARContentList = (projectId?: number) => {
  const [filters, setFilters] = useState<FilterState>({ search: '' });
  const [pagination, setPagination] = useState({
    page: 0,
    limit: 25,
    total: 0
  });
  
  // Mock data for demonstration
  const mockContents: ARContent[] = [
    {
      id: 1,
      title: 'Постер #1 - Санта с подарками',
      unique_id: 'abc123xyz',
      image_url: '/placeholder-image.jpg',
      company_name: 'Креативное агентство',
      videos_count: 5,
      marker_status: 'ready',
      views: 3245,
      created_at: '2023-12-01T10:30:00Z',
      expires_at: '2024-12-01T10:30:00Z'
    },
    {
      id: 2,
      title: 'Выставка - Современное искусство',
      unique_id: 'def456uvw',
      thumbnail_url: '/thumbnail-image.jpg',
      company_name: 'Арт-студия',
      videos_count: 3,
      marker_status: 'processing',
      views: 1204,
      created_at: '2023-12-02T09:15:00Z'
    },
    {
      id: 3,
      title: 'Промо - Новый продукт',
      unique_id: 'ghi789rst',
      image_url: '/promo-image.jpg',
      company_name: 'БрендПро',
      videos_count: 1,
      marker_status: 'pending',
      views: 876,
      created_at: '2023-12-03T16:45:00Z'
    }
  ];

  const updateFilters = useCallback((newFilters: Partial<FilterState>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    setPagination(prev => ({ ...prev, page: 0 }));
  }, []);

  const updatePagination = useCallback((newPagination: Partial<typeof pagination>) => {
    setPagination(prev => ({ ...prev, ...newPagination }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ search: '' });
    setPagination({ page: 0, limit: 25, total: 0 });
  }, []);

  const refetch = useCallback(() => {
    // In a real implementation, this would refetch data from the API
    console.log('Refetching data...');
  }, []);

  return {
    contents: mockContents,
    total: mockContents.length,
    filters,
    pagination,
    isLoading: false,
    updateFilters,
    updatePagination,
    resetFilters,
    refetch
  };
};