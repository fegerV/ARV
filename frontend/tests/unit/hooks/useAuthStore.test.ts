import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '@/store/authStore';

describe('useAuthStore', () => {
  beforeEach(() => {
    // Clear store state before each test
    localStorage.clear();
    useAuthStore.getState().logout();
  });

  describe('login', () => {
    it('should set token and user on successful login', () => {
      const { result } = renderHook(() => useAuthStore());
      
      const loginData = {
        access_token: 'test-jwt-token',
        user: {
          id: 1,
          email: 'admin@test.com',
          full_name: 'Admin User',
          role: 'admin',
          last_login_at: '2025-12-05T10:00:00Z',
        },
      };

      act(() => {
        result.current.login(loginData);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.token).toBe('test-jwt-token');
      expect(result.current.user?.email).toBe('admin@test.com');
      expect(result.current.user?.role).toBe('admin');
    });

    it('should persist token to localStorage', () => {
      const { result } = renderHook(() => useAuthStore());
      
      act(() => {
        result.current.login({
          access_token: 'persistent-token',
          user: {
            id: 1,
            email: 'test@example.com',
            full_name: 'Test User',
            role: 'user',
          },
        });
      });

      expect(localStorage.getItem('auth_token')).toBe('persistent-token');
    });
  });

  describe('logout', () => {
    it('should clear state and remove token from localStorage', () => {
      const { result } = renderHook(() => useAuthStore());
      
      // First login
      act(() => {
        result.current.login({
          access_token: 'token',
          user: {
            id: 1,
            email: 'test@example.com',
            full_name: 'Test User',
            role: 'user',
          },
        });
      });

      expect(result.current.isAuthenticated).toBe(true);

      // Then logout
      act(() => {
        result.current.logout();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.token).toBeNull();
      expect(result.current.user).toBeNull();
      expect(localStorage.getItem('auth_token')).toBeNull();
    });
  });

  describe('updateUser', () => {
    it('should update user information', () => {
      const { result } = renderHook(() => useAuthStore());
      
      // First login
      act(() => {
        result.current.login({
          access_token: 'token',
          user: {
            id: 1,
            email: 'old@example.com',
            full_name: 'Old Name',
            role: 'user',
          },
        });
      });

      // Update user
      act(() => {
        result.current.updateUser({
          id: 1,
          email: 'new@example.com',
          full_name: 'New Name',
          role: 'admin',
        });
      });

      expect(result.current.user?.email).toBe('new@example.com');
      expect(result.current.user?.full_name).toBe('New Name');
      expect(result.current.user?.role).toBe('admin');
      expect(result.current.isAuthenticated).toBe(true);
    });
  });

  describe('persistence', () => {
    it('should restore state from localStorage on initialization', () => {
      // Simulate existing auth data in localStorage
      const authData = {
        state: {
          token: 'existing-token',
          user: {
            id: 1,
            email: 'existing@example.com',
            full_name: 'Existing User',
            role: 'admin',
          },
          isAuthenticated: true,
        },
        version: 0,
      };
      localStorage.setItem('vertex-ar-auth', JSON.stringify(authData));

      const { result } = renderHook(() => useAuthStore());

      // Zustand persist загружает асинхронно, проверяем значения
      expect(result.current.token).toBe('existing-token');
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user?.email).toBe('existing@example.com');
    });
  });
});
