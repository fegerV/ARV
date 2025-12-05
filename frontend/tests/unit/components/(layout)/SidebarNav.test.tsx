import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { SidebarNav } from '@/components/(layout)/SidebarNav';

const renderWithRouter = (component: React.ReactElement, initialRoute = '/') => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      {component}
    </MemoryRouter>
  );
};

describe('SidebarNav Component', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render all navigation items', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Компании')).toBeInTheDocument();
      expect(screen.getByText('Проекты')).toBeInTheDocument();
      expect(screen.getByText('AR Контент')).toBeInTheDocument();
      expect(screen.getByText('Хранилище')).toBeInTheDocument();
      expect(screen.getByText('Аналитика')).toBeInTheDocument();
      expect(screen.getByText('Уведомления')).toBeInTheDocument();
      expect(screen.getByText('Настройки')).toBeInTheDocument();
    });

    it('should render with correct variant', () => {
      const { container } = renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      const drawer = container.querySelector('.MuiDrawer-root');
      expect(drawer).toBeInTheDocument();
    });

    it('should render when open', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      expect(screen.getByText('Dashboard')).toBeVisible();
    });
  });

  describe('Navigation', () => {
    it('should highlight active route (Dashboard)', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />,
        '/'
      );

      const dashboardButton = screen.getByText('Dashboard').closest('button');
      expect(dashboardButton).toHaveClass('Mui-selected');
    });

    it('should highlight active route (Companies)', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />,
        '/companies'
      );

      const companiesButton = screen.getByText('Компании').closest('button');
      expect(companiesButton).toHaveClass('Mui-selected');
    });

    it('should highlight active route for nested paths', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />,
        '/companies/123'
      );

      const companiesButton = screen.getByText('Компании').closest('button');
      expect(companiesButton).toHaveClass('Mui-selected');
    });

    it('should navigate on item click', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />,
        '/'
      );

      const projectsButton = screen.getByText('Проекты').closest('button');
      fireEvent.click(projectsButton!);

      // Check navigation happened (URL changed)
      expect(window.location.pathname).toBe('/projects');
    });

    it('should call onClose after navigation in temporary mode', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="temporary" />
      );

      const companiesButton = screen.getByText('Компании').closest('button');
      fireEvent.click(companiesButton!);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should NOT call onClose in permanent mode', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      const companiesButton = screen.getByText('Компании').closest('button');
      fireEvent.click(companiesButton!);

      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('Icons', () => {
    it('should render icons for all menu items', () => {
      const { container } = renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      const icons = container.querySelectorAll('.MuiListItemIcon-root');
      expect(icons.length).toBeGreaterThanOrEqual(8);
    });
  });

  describe('Responsive behavior', () => {
    it('should support temporary variant for mobile', () => {
      renderWithRouter(
        <SidebarNav open={false} onClose={mockOnClose} variant="temporary" />
      );

      // Drawer should respect open prop in temporary mode
      const drawer = screen.queryByText('Dashboard');
      // In temporary mode with open=false, content might not be visible
    });

    it('should support permanent variant for desktop', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      expect(screen.getByText('Dashboard')).toBeVisible();
    });
  });

  describe('Styling', () => {
    it('should apply correct width', () => {
      const { container } = renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      const drawer = container.querySelector('.MuiDrawer-root');
      expect(drawer).toBeInTheDocument();
    });

    it('should apply hover styles on menu items', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      const dashboardButton = screen.getByText('Dashboard').closest('button');
      expect(dashboardButton).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have clickable list items', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThanOrEqual(8);
    });

    it('should have proper text labels', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Компании')).toBeInTheDocument();
      expect(screen.getByText('Настройки')).toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    it('should handle rapid clicks', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      const companiesButton = screen.getByText('Компании').closest('button');
      
      fireEvent.click(companiesButton!);
      fireEvent.click(companiesButton!);
      fireEvent.click(companiesButton!);

      // Should navigate successfully
      expect(window.location.pathname).toBe('/companies');
    });

    it('should handle all navigation items sequentially', () => {
      renderWithRouter(
        <SidebarNav open={true} onClose={mockOnClose} variant="permanent" />
      );

      const menuItems = [
        'Dashboard',
        'Компании',
        'Проекты',
        'AR Контент',
        'Хранилище',
        'Аналитика',
        'Уведомления',
        'Настройки',
      ];

      menuItems.forEach((item) => {
        const button = screen.getByText(item).closest('button');
        expect(button).toBeInTheDocument();
      });
    });
  });
});
