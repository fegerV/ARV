// tests/unit/pages/ARContentDetailPage.test.tsx
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ARContentDetailPage from '../../../src/pages/ar-content/ARContentDetailPage';

// Мокаем react-router-dom
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({
    id: '1',
  }),
  useNavigate: () => jest.fn(),
}));

// Мокаем arContentApi
jest.mock('../../../src/services/ar-content', () => ({
  arContentApi: {
    get: jest.fn(),
    generateMarker: jest.fn(),
  },
}));

describe('ARContentDetailPage', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', async () => {
    const { arContentApi } = require('../../../src/services/ar-content');
    arContentApi.get.mockResolvedValue({ data: null });

    render(<ARContentDetailPage />, { wrapper });

    expect(screen.getByText('Загрузка заказа...')).toBeInTheDocument();
  });

  it('renders content details when data is loaded', async () => {
    const mockContent = {
      id: 1,
      unique_id: 'abc123',
      title: 'Тестовый контент',
      description: 'Описание тестового контента',
      company_id: 1,
      company_name: 'Тестовая компания',
      project_id: 1,
      project_name: 'Тестовый проект',
      image_url: '/test-image.jpg',
      thumbnail_url: '/test-thumbnail.jpg',
      image_width: 1920,
      image_height: 1080,
      image_size_readable: '2MB',
      image_path: '/path/to/image.jpg',
      marker_status: 'ready',
      marker_url: '/test-marker.mind',
      marker_path: '/path/to/marker.mind',
      marker_feature_points: 1247,
      videos: [],
      stats: {
        views: 100,
        unique_sessions: 80,
        avg_duration: 30,
        avg_fps: 59.5,
      },
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    };

    const { arContentApi } = require('../../../src/services/ar-content');
    arContentApi.get.mockResolvedValue({ data: mockContent });

    render(<ARContentDetailPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Тестовый контент')).toBeInTheDocument();
    });

    expect(screen.getByText('Компания: Тестовая компания • Проект: Тестовый проект')).toBeInTheDocument();
    expect(screen.getByText('Портрет')).toBeInTheDocument();
    expect(screen.getByText('NFT‑маркер')).toBeInTheDocument();
    expect(screen.getByText('Ссылка и QR‑код')).toBeInTheDocument();
    expect(screen.getByText('Видеоанимации')).toBeInTheDocument();
    expect(screen.getByText('Расписание')).toBeInTheDocument();
    expect(screen.getByText('Статистика (30 дней)')).toBeInTheDocument();
  });
});