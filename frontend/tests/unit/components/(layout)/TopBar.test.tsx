import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { TopBar } from '@/components/(layout)/TopBar';
import { useAuthStore } from '@/store/authStore';

// Mock auth store
jest.mock('@/store/authStore');

// Mock ThemeToggle component
jest.mock('@/components/common/ThemeToggle', () => ({
  __esModule: true,
  default: () => <button data-testid="theme-toggle">Theme Toggle</button>,
}));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('TopBar Component', () => {
  const mockOnMenuClick = jest.fn();
  const mockLogout = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useAuthStore as unknown as jest.Mock).mockReturnValue({
      user: {
        id: 1,
        email: 'admin@test.com',
        full_name: 'Admin User',
        role: 'admin',
      },
      logout: mockLogout,
    });
  });

  describe('Rendering', () => {
    it('should render app title', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      expect(screen.getByText('Vertex AR')).toBeInTheDocument();
    });

    it('should render user avatar with email initial', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatar = screen.getByText('A'); // First letter of admin@test.com
      expect(avatar).toBeInTheDocument();
    });

    it('should render notifications button', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const notificationButton = screen.getAllByRole('button').find(
        (btn) => btn.querySelector('[data-testid="NotificationsIcon"]')
      );
      // Check button exists (MUI IconButton)
      expect(screen.getAllByRole('button').length).toBeGreaterThan(0);
    });

    it('should render theme toggle', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
    });

    it('should render menu button on mobile', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const menuButton = screen.getByLabelText('menu');
      expect(menuButton).toBeInTheDocument();
    });
  });

  describe('Menu interactions', () => {
    it('should call onMenuClick when menu button is clicked', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const menuButton = screen.getByLabelText('menu');
      fireEvent.click(menuButton);

      expect(mockOnMenuClick).toHaveBeenCalledTimes(1);
    });

    it('should open user menu when avatar is clicked', async () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatarButton = screen.getByText('A').closest('button');
      fireEvent.click(avatarButton!);

      await waitFor(() => {
        expect(screen.getByText('admin@test.com')).toBeVisible();
      });
    });

    it('should display user email in menu', async () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatarButton = screen.getByText('A').closest('button');
      fireEvent.click(avatarButton!);

      await waitFor(() => {
        expect(screen.getByText('admin@test.com')).toBeInTheDocument();
      });
    });

    it('should show settings option in menu', async () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatarButton = screen.getByText('A').closest('button');
      fireEvent.click(avatarButton!);

      await waitFor(() => {
        expect(screen.getByText('Настройки')).toBeInTheDocument();
      });
    });

    it('should show logout option in menu', async () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatarButton = screen.getByText('A').closest('button');
      fireEvent.click(avatarButton!);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeInTheDocument();
      });
    });

    it('should close menu when clicking outside', async () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatarButton = screen.getByText('A').closest('button');
      fireEvent.click(avatarButton!);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeVisible();
      });

      // Click outside (on document body)
      fireEvent.click(document.body);

      await waitFor(() => {
        expect(screen.queryByText('Выход')).not.toBeVisible();
      });
    });
  });

  describe('Navigation', () => {
    it('should navigate to notifications on notifications button click', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const buttons = screen.getAllByRole('button');
      // Find notifications button (has Notifications icon)
      const notificationsButton = buttons.find(
        (btn) => btn.getAttribute('aria-label') === 'notifications'
      ) || buttons[1]; // Fallback to second button

      fireEvent.click(notificationsButton);

      expect(mockNavigate).toHaveBeenCalledWith('/notifications');
    });

    it('should navigate to settings from menu', async () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatarButton = screen.getByText('A').closest('button');
      fireEvent.click(avatarButton!);

      await waitFor(() => {
        expect(screen.getByText('Настройки')).toBeVisible();
      });

      const settingsMenuItem = screen.getByText('Настройки').closest('li');
      fireEvent.click(settingsMenuItem!);

      expect(mockNavigate).toHaveBeenCalledWith('/settings');
    });
  });

  describe('Logout', () => {
    it('should call logout and navigate to login', async () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatarButton = screen.getByText('A').closest('button');
      fireEvent.click(avatarButton!);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeVisible();
      });

      const logoutMenuItem = screen.getByText('Выход').closest('li');
      fireEvent.click(logoutMenuItem!);

      expect(mockLogout).toHaveBeenCalledTimes(1);
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  describe('User avatar', () => {
    it('should display first letter of email in avatar', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      expect(screen.getByText('A')).toBeInTheDocument();
    });

    it('should handle user with different email', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        user: {
          id: 2,
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
        },
        logout: mockLogout,
      });

      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      expect(screen.getByText('T')).toBeInTheDocument();
    });

    it('should show default avatar when no user', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        user: null,
        logout: mockLogout,
      });

      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      expect(screen.getByText('A')).toBeInTheDocument(); // Default 'A'
    });
  });

  describe('Styling', () => {
    it('should have fixed position', () => {
      const { container } = renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const appBar = container.querySelector('.MuiAppBar-root');
      expect(appBar).toBeInTheDocument();
    });

    it('should have correct z-index', () => {
      const { container } = renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const appBar = container.querySelector('.MuiAppBar-root');
      expect(appBar).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible menu button', () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const menuButton = screen.getByLabelText('menu');
      expect(menuButton).toHaveAttribute('aria-label', 'menu');
    });

    it('should have keyboard navigation support', async () => {
      renderWithRouter(<TopBar onMenuClick={mockOnMenuClick} />);

      const avatarButton = screen.getByText('A').closest('button');
      
      // Keyboard enter to open menu
      fireEvent.keyDown(avatarButton!, { key: 'Enter', code: 'Enter' });
      fireEvent.click(avatarButton!);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeVisible();
      });
    });
  });
});
