import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  last_login_at?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (data: { access_token: string; user: User }) => void;
  logout: () => void;
  updateUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      
      login: (data) => {
        localStorage.setItem('auth_token', data.access_token);
        set({
          token: data.access_token,
          user: data.user,
          isAuthenticated: true,
        });
      },
      
      logout: () => {
        localStorage.removeItem('auth_token');
        set({ 
          token: null, 
          user: null, 
          isAuthenticated: false 
        });
      },
      
      updateUser: (user) => {
        set({ user });
      },
    }),
    {
      name: 'vertex-ar-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
