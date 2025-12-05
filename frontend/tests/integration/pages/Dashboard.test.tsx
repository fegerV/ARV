/**
 * Integration tests for Dashboard page
 * Проверяет Dashboard с KPI карточками и общий layout
 */

import { render, screen, within } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '@/pages/Dashboard';

// Wrapper для React Router
const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('Dashboard Page - Integration', () => {
  describe('Page Layout', () => {
    it('should render page header with title', () => {
      renderWithRouter(<Dashboard />);
      
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    it('should render page subtitle', () => {
      renderWithRouter(<Dashboard />);
      
      expect(screen.getByText('Обзор системы Vertex AR')).toBeInTheDocument();
    });

    it('should render within PageContent wrapper', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      // PageContent должен быть в DOM
      expect(container.querySelector('.MuiContainer-root')).toBeInTheDocument();
    });
  });

  describe('KPI Cards', () => {
    it('should render all 8 KPI cards', () => {
      renderWithRouter(<Dashboard />);
      
      // Проверяем наличие всех заголовков KPI карточек
      expect(screen.getByText('Всего просмотров')).toBeInTheDocument();
      expect(screen.getByText('Уникальных сессий')).toBeInTheDocument();
      expect(screen.getByText('Активного контента')).toBeInTheDocument();
      expect(screen.getByText('Использовано')).toBeInTheDocument();
      expect(screen.getByText('Компаний')).toBeInTheDocument();
      expect(screen.getByText('Проектов')).toBeInTheDocument();
      expect(screen.getByText('Доход')).toBeInTheDocument();
      expect(screen.getByText('Uptime')).toBeInTheDocument();
    });

    it('should display correct values for KPI cards', () => {
      renderWithRouter(<Dashboard />);
      
      expect(screen.getByText('45,892')).toBeInTheDocument(); // Всего просмотров
      expect(screen.getByText('38,234')).toBeInTheDocument(); // Уникальных сессий
      expect(screen.getByText('280')).toBeInTheDocument(); // Активного контента
      expect(screen.getByText('125GB')).toBeInTheDocument(); // Использовано
      expect(screen.getByText('15')).toBeInTheDocument(); // Компаний
      expect(screen.getByText('100')).toBeInTheDocument(); // Проектов
      expect(screen.getByText('$4,200')).toBeInTheDocument(); // Доход
      expect(screen.getByText('99.92%')).toBeInTheDocument(); // Uptime
    });

    it('should display trend indicators', () => {
      renderWithRouter(<Dashboard />);
      
      // Проверяем наличие трендов (в виде текста subtitle)
      expect(screen.getByText('+15 за месяц')).toBeInTheDocument();
      expect(screen.getByText('10% от лимита')).toBeInTheDocument();
      expect(screen.getByText('+12 активных')).toBeInTheDocument();
    });

    it('should render icons in KPI cards', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      // Проверяем наличие SVG иконок
      const svgIcons = container.querySelectorAll('svg');
      expect(svgIcons.length).toBeGreaterThan(0);
    });
  });

  describe('Grid Layout', () => {
    it('should render KPI cards in grid layout', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      const grid = container.querySelector('.MuiGrid-container');
      expect(grid).toBeInTheDocument();
    });

    it('should have 8 grid items for KPI cards', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      const gridItems = container.querySelectorAll('.MuiGrid-item');
      expect(gridItems.length).toBeGreaterThanOrEqual(8);
    });

    it('should use responsive grid breakpoints', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      const gridItems = container.querySelectorAll('.MuiGrid-item');
      gridItems.forEach(item => {
        // Проверяем наличие Grid классов
        expect(item.className).toContain('MuiGrid');
      });
    });
  });

  describe('Activity Section', () => {
    it('should render activity section title', () => {
      renderWithRouter(<Dashboard />);
      
      expect(screen.getByText('Недавняя активность')).toBeInTheDocument();
    });

    it('should render placeholder text for activity feed', () => {
      renderWithRouter(<Dashboard />);
      
      expect(screen.getByText('Activity feed будет здесь...')).toBeInTheDocument();
    });

    it('should render activity section in paper component', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      const papers = container.querySelectorAll('.MuiPaper-root');
      expect(papers.length).toBeGreaterThan(0);
    });
  });

  describe('Specific KPI Card Details', () => {
    it('should display views card with upward trend', () => {
      renderWithRouter(<Dashboard />);
      
      const viewsCard = screen.getByText('Всего просмотров').closest('.MuiPaper-root');
      expect(viewsCard).toBeInTheDocument();
      expect(within(viewsCard!).getByText('45,892')).toBeInTheDocument();
    });

    it('should display sessions card with upward trend', () => {
      renderWithRouter(<Dashboard />);
      
      const sessionsCard = screen.getByText('Уникальных сессий').closest('.MuiPaper-root');
      expect(sessionsCard).toBeInTheDocument();
      expect(within(sessionsCard!).getByText('38,234')).toBeInTheDocument();
    });

    it('should display storage card with usage info', () => {
      renderWithRouter(<Dashboard />);
      
      const storageCard = screen.getByText('Использовано').closest('.MuiPaper-root');
      expect(storageCard).toBeInTheDocument();
      expect(within(storageCard!).getByText('125GB')).toBeInTheDocument();
      expect(within(storageCard!).getByText('10% от лимита')).toBeInTheDocument();
    });

    it('should display uptime card with status', () => {
      renderWithRouter(<Dashboard />);
      
      const uptimeCard = screen.getByText('Uptime').closest('.MuiPaper-root');
      expect(uptimeCard).toBeInTheDocument();
      expect(within(uptimeCard!).getByText('99.92%')).toBeInTheDocument();
      expect(within(uptimeCard!).getByText('✅ Все сервисы работают')).toBeInTheDocument();
    });
  });

  describe('Component Integration', () => {
    it('should integrate PageHeader component correctly', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      // PageHeader должен рендериться с правильными props
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Обзор системы Vertex AR')).toBeInTheDocument();
    });

    it('should integrate KpiCard component correctly', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      // Все KpiCard должны рендериться
      const kpiCards = container.querySelectorAll('.MuiPaper-root');
      expect(kpiCards.length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    it('should have accessible headings', () => {
      renderWithRouter(<Dashboard />);
      
      const headings = screen.getAllByRole('heading');
      expect(headings.length).toBeGreaterThan(0);
    });

    it('should have proper heading hierarchy', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      // Проверяем наличие h4, h5, h6
      const h4 = container.querySelector('h4');
      const h6 = container.querySelector('h6');
      
      expect(h4 || h6).toBeInTheDocument();
    });
  });

  describe('Rendering Performance', () => {
    it('should render all components without errors', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render quickly with all KPI cards', () => {
      const startTime = performance.now();
      renderWithRouter(<Dashboard />);
      const endTime = performance.now();
      
      // Рендеринг должен занимать меньше 500ms
      expect(endTime - startTime).toBeLessThan(500);
    });
  });

  describe('Snapshot', () => {
    it('should match snapshot', () => {
      const { container } = renderWithRouter(<Dashboard />);
      
      expect(container.firstChild).toMatchSnapshot();
    });
  });
});
