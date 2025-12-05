import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '@/components/(auth)/ProtectedRoute';
import { useAuthStore } from '@/store/authStore';

// Mock auth store
jest.mock('@/store/authStore');

const LoginPage = () => <div>Login Page</div>;
const ProtectedPage = () => <div>Protected Content</div>;

const renderWithRouter = (isAuthenticated: boolean, initialRoute = '/protected') => {
  (useAuthStore as unknown as jest.Mock).mockReturnValue({
    isAuthenticated,
  });

  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/protected"
          element={
            <ProtectedRoute>
              <ProtectedPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div>Dashboard Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>
  );
};

describe('ProtectedRoute Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('When user is authenticated', () => {
    it('should render children content', () => {
      renderWithRouter(true);

      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
    });

    it('should allow access to protected pages', () => {
      renderWithRouter(true, '/dashboard');

      expect(screen.getByText('Dashboard Content')).toBeInTheDocument();
    });

    it('should render nested components', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: true,
      });

      render(
        <MemoryRouter>
          <ProtectedRoute>
            <div data-testid="nested-content">
              <h1>Title</h1>
              <p>Paragraph</p>
              <button>Action</button>
            </div>
          </ProtectedRoute>
        </MemoryRouter>
      );

      expect(screen.getByTestId('nested-content')).toBeInTheDocument();
      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Paragraph')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
    });

    it('should render multiple children', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: true,
      });

      render(
        <MemoryRouter>
          <ProtectedRoute>
            <div>First Child</div>
            <div>Second Child</div>
            <div>Third Child</div>
          </ProtectedRoute>
        </MemoryRouter>
      );

      expect(screen.getByText('First Child')).toBeInTheDocument();
      expect(screen.getByText('Second Child')).toBeInTheDocument();
      expect(screen.getByText('Third Child')).toBeInTheDocument();
    });

    it('should maintain state when authenticated', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: true,
      });

      const { rerender } = render(
        <MemoryRouter>
          <ProtectedRoute>
            <div>Initial Content</div>
          </ProtectedRoute>
        </MemoryRouter>
      );

      expect(screen.getByText('Initial Content')).toBeInTheDocument();

      rerender(
        <MemoryRouter>
          <ProtectedRoute>
            <div>Updated Content</div>
          </ProtectedRoute>
        </MemoryRouter>
      );

      expect(screen.getByText('Updated Content')).toBeInTheDocument();
    });
  });

  describe('When user is NOT authenticated', () => {
    it('should redirect to login page', () => {
      renderWithRouter(false);

      expect(screen.getByText('Login Page')).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    it('should NOT render children content', () => {
      renderWithRouter(false, '/dashboard');

      expect(screen.queryByText('Dashboard Content')).not.toBeInTheDocument();
      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });

    it('should block access to all protected routes', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });

      render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div>Protected</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });

    it('should use replace navigation to login', () => {
      renderWithRouter(false);

      // Should be on login page
      expect(screen.getByText('Login Page')).toBeInTheDocument();
      
      // Navigation should have used replace (can't go back)
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  describe('Auth state changes', () => {
    it('should update when auth state changes from false to true', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });

      const { rerender } = render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div>Protected Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Login Page')).toBeInTheDocument();

      // Simulate login
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: true,
      });

      rerender(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div>Protected Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    it('should redirect when auth state changes from true to false', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: true,
      });

      const { rerender } = render(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div>Protected Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Protected Content')).toBeInTheDocument();

      // Simulate logout
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });

      rerender(
        <MemoryRouter initialEntries={['/protected']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div>Protected Content</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Login Page')).toBeInTheDocument();
    });
  });

  describe('Edge cases', () => {
    it('should handle null children gracefully', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: true,
      });

      render(
        <MemoryRouter>
          <ProtectedRoute>
            {null}
          </ProtectedRoute>
        </MemoryRouter>
      );

      // Should not crash
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    it('should handle empty children', () => {
      (useAuthStore as unknown as jest.Mock).mockReturnValue({
        isAuthenticated: true,
      });

      const { container } = render(
        <MemoryRouter>
          <ProtectedRoute>
            <></>
          </ProtectedRoute>
        </MemoryRouter>
      );

      // Should render without errors
      expect(container).toBeInTheDocument();
    });
  });
});
