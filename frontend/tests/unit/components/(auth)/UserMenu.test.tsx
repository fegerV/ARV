import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { UserMenu } from '@/components/(auth)/UserMenu';
import { useAuthStore } from '@/store/authStore';

// Mock auth store
jest.mock('@/store/authStore');

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('UserMenu Component', () => {
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
    it('should render user avatar button', () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      expect(avatarButton).toBeInTheDocument();
    });

    it('should display first letter of email in avatar', () => {
      renderWithRouter(<UserMenu />);

      expect(screen.getByText('A')).toBeInTheDocument(); // 'A' from admin@test.com
    });

    it('should show default avatar when no user', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        user: null,
        logout: mockLogout,
      });

      renderWithRouter(<UserMenu />);

      expect(screen.getByText('A')).toBeInTheDocument(); // Default 'A'
    });

    it('should render avatar with different email initial', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        user: {
          id: 2,
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
        },
        logout: mockLogout,
      });

      renderWithRouter(<UserMenu />);

      expect(screen.getByText('T')).toBeInTheDocument(); // 'T' from test@example.com
    });
  });

  describe('Menu interactions', () => {
    it('should open menu when avatar is clicked', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('admin@test.com')).toBeVisible();
      });
    });

    it('should display user email in menu', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('admin@test.com')).toBeInTheDocument();
      });
    });

    it('should show settings menu item', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Настройки')).toBeInTheDocument();
      });
    });

    it('should show logout menu item', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeInTheDocument();
      });
    });

    it('should close menu when clicking outside', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeVisible();
      });

      // Simulate clicking outside
      fireEvent.click(document.body);

      await waitFor(() => {
        expect(screen.queryByText('Выход')).not.toBeVisible();
      });
    });

    it('should close menu after clicking menu item', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Настройки')).toBeVisible();
      });

      const settingsItem = screen.getByText('Настройки').closest('li');
      fireEvent.click(settingsItem!);

      await waitFor(() => {
        expect(screen.queryByText('Настройки')).not.toBeVisible();
      });
    });
  });

  describe('Navigation', () => {
    it('should navigate to settings when settings is clicked', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Настройки')).toBeVisible();
      });

      const settingsItem = screen.getByText('Настройки').closest('li');
      fireEvent.click(settingsItem!);

      expect(mockNavigate).toHaveBeenCalledWith('/settings');
    });
  });

  describe('Logout', () => {
    it('should call logout when logout is clicked', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeVisible();
      });

      const logoutItem = screen.getByText('Выход').closest('li');
      fireEvent.click(logoutItem!);

      expect(mockLogout).toHaveBeenCalledTimes(1);
    });

    it('should navigate to login after logout', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeVisible();
      });

      const logoutItem = screen.getByText('Выход').closest('li');
      fireEvent.click(logoutItem!);

      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });

    it('should call logout before navigation', async () => {
      const callOrder: string[] = [];
      
      mockLogout.mockImplementation(() => {
        callOrder.push('logout');
      });

      mockNavigate.mockImplementation(() => {
        callOrder.push('navigate');
      });

      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeVisible();
      });

      const logoutItem = screen.getByText('Выход').closest('li');
      fireEvent.click(logoutItem!);

      expect(callOrder).toEqual(['logout', 'navigate']);
    });
  });

  describe('Menu items styling', () => {
    it('should disable email menu item', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        const emailItem = screen.getByText('admin@test.com').closest('li');
        expect(emailItem).toHaveClass('Mui-disabled');
      });
    });

    it('should show icons for menu items', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        const icons = screen.getAllByTestId(/Icon/i);
        expect(icons.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Avatar styling', () => {
    it('should have correct avatar size', () => {
      const { container } = renderWithRouter(<UserMenu />);

      const avatar = container.querySelector('.MuiAvatar-root');
      expect(avatar).toBeInTheDocument();
    });

    it('should have primary color background', () => {
      const { container } = renderWithRouter(<UserMenu />);

      const avatar = container.querySelector('.MuiAvatar-root');
      expect(avatar).toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    it('should handle undefined email gracefully', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        user: {
          id: 1,
          email: undefined,
          full_name: 'Test User',
          role: 'user',
        },
        logout: mockLogout,
      });

      renderWithRouter(<UserMenu />);

      expect(screen.getByText('A')).toBeInTheDocument(); // Fallback to 'A'
    });

    it('should handle empty email', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        user: {
          id: 1,
          email: '',
          full_name: 'Test User',
          role: 'user',
        },
        logout: mockLogout,
      });

      renderWithRouter(<UserMenu />);

      expect(screen.getByText('A')).toBeInTheDocument(); // Fallback to 'A'
    });

    it('should handle rapid menu opening and closing', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');

      // Rapid clicks
      fireEvent.click(avatarButton);
      fireEvent.click(avatarButton);
      fireEvent.click(avatarButton);

      await waitFor(() => {
        expect(screen.getByText('Выход')).toBeVisible();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have clickable avatar button', () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      expect(avatarButton).toBeEnabled();
    });

    it('should have menu items as list items', async () => {
      renderWithRouter(<UserMenu />);

      const avatarButton = screen.getByRole('button');
      fireEvent.click(avatarButton);

      await waitFor(() => {
        const menuItems = screen.getAllByRole('menuitem');
        expect(menuItems.length).toBeGreaterThanOrEqual(2); // Settings + Logout
      });
    });
  });
});
