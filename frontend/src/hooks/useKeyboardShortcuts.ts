import { useEffect } from 'react';
import { useThemeStore } from '../store/themeStore';

export const useKeyboardShortcuts = () => {
  const { toggleTheme } = useThemeStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+T or Cmd+T: Toggle theme
      if ((e.ctrlKey || e.metaKey) && e.key === 't') {
        e.preventDefault();
        toggleTheme();
      }
      
      // Ctrl+B or Cmd+B: Toggle theme (alias)
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        toggleTheme();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleTheme]);
};
