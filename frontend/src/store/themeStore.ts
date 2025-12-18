import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeState {
  mode: ThemeMode;
  toggleTheme: () => void;
  setTheme: (mode: ThemeMode) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: 'system',
      toggleTheme: () => {
        const current = get().mode;
        let next: ThemeMode;
        
        if (current === 'light') next = 'dark';
        else if (current === 'dark') next = 'system';
        else next = 'light';
        
        set({ mode: next });
      },
      setTheme: (mode) => set({ mode }),
    }),
    {
      name: 'vertex-ar-theme',
      partialize: (state) => ({ mode: state.mode }),
    }
  )
);
