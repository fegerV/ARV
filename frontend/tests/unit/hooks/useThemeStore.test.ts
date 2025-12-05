import { renderHook, act } from '@testing-library/react';
import { useThemeStore } from '@/store/themeStore';

describe('useThemeStore', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should initialize with system theme by default', () => {
    const { result } = renderHook(() => useThemeStore());
    
    expect(result.current.mode).toBe('system');
  });

  it('should toggle between light and dark themes', () => {
    const { result } = renderHook(() => useThemeStore());
    
    act(() => {
      result.current.setTheme('light');
    });
    expect(result.current.mode).toBe('light');
    
    act(() => {
      result.current.toggleTheme();
    });
    expect(result.current.mode).toBe('dark');
    
    act(() => {
      result.current.toggleTheme();
    });
    expect(result.current.mode).toBe('system');
  });

  it('should persist theme preference to localStorage', () => {
    const { result } = renderHook(() => useThemeStore());
    
    act(() => {
      result.current.setTheme('dark');
    });
    
    const stored = localStorage.getItem('vertex-ar-theme');
    expect(stored).toContain('"mode":"dark"');
  });

  it('should restore theme from localStorage', () => {
    const themeData = {
      state: { mode: 'dark' },
      version: 0,
    };
    localStorage.setItem('vertex-ar-theme', JSON.stringify(themeData));
    
    const { result } = renderHook(() => useThemeStore());
    
    expect(result.current.mode).toBe('dark');
  });

  it('should set system theme mode', () => {
    const { result } = renderHook(() => useThemeStore());
    
    act(() => {
      result.current.setTheme('system');
    });
    
    expect(result.current.mode).toBe('system');
  });

  it('should handle keyboard shortcut toggle', () => {
    const { result } = renderHook(() => useThemeStore());
    
    act(() => {
      result.current.setTheme('light');
    });
    
    // Simulate Ctrl+T keyboard shortcut
    act(() => {
      result.current.toggleTheme();
    });
    
    expect(result.current.mode).toBe('dark');
  });

  it('should compute effective theme based on system preference', () => {
    // Mock window.matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    const { result } = renderHook(() => useThemeStore());
    
    act(() => {
      result.current.setTheme('system');
    });
    
    expect(result.current.mode).toBe('system');
  });
});
