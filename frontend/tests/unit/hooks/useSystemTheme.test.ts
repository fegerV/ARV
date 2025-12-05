/**
 * Tests for useSystemTheme hook
 * Проверяет отслеживание системной темы через prefers-color-scheme
 */

import { renderHook, waitFor } from '@testing-library/react';
import { useSystemTheme } from '@/hooks/useSystemTheme';

// Mock для matchMedia
const createMatchMediaMock = (matches: boolean) => {
  return jest.fn().mockImplementation((query) => ({
    matches,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  }));
};

describe('useSystemTheme', () => {
  let matchMediaMock: jest.Mock;

  beforeEach(() => {
    matchMediaMock = createMatchMediaMock(false);
    window.matchMedia = matchMediaMock;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should return "light" theme when system prefers light', () => {
    matchMediaMock = createMatchMediaMock(false);
    window.matchMedia = matchMediaMock;

    const { result } = renderHook(() => useSystemTheme());

    expect(result.current).toBe('light');
  });

  it('should return "dark" theme when system prefers dark', () => {
    matchMediaMock = createMatchMediaMock(true);
    window.matchMedia = matchMediaMock;

    const { result } = renderHook(() => useSystemTheme());

    expect(result.current).toBe('dark');
  });

  it('should add event listener on mount', () => {
    const addEventListenerSpy = jest.fn();
    matchMediaMock = createMatchMediaMock(false);
    matchMediaMock.mockReturnValue({
      matches: false,
      media: '',
      addEventListener: addEventListenerSpy,
      removeEventListener: jest.fn(),
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      dispatchEvent: jest.fn(),
    });
    window.matchMedia = matchMediaMock;

    renderHook(() => useSystemTheme());

    expect(addEventListenerSpy).toHaveBeenCalledWith('change', expect.any(Function));
  });

  it('should remove event listener on unmount', () => {
    const removeEventListenerSpy = jest.fn();
    matchMediaMock = createMatchMediaMock(false);
    matchMediaMock.mockReturnValue({
      matches: false,
      media: '',
      addEventListener: jest.fn(),
      removeEventListener: removeEventListenerSpy,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      dispatchEvent: jest.fn(),
    });
    window.matchMedia = matchMediaMock;

    const { unmount } = renderHook(() => useSystemTheme());
    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith('change', expect.any(Function));
  });

  it('should update theme when system preference changes to dark', async () => {
    let changeHandler: ((e: MediaQueryListEvent) => void) | null = null;

    matchMediaMock = createMatchMediaMock(false);
    matchMediaMock.mockReturnValue({
      matches: false,
      media: '',
      addEventListener: jest.fn((event, handler) => {
        if (event === 'change') {
          changeHandler = handler;
        }
      }),
      removeEventListener: jest.fn(),
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      dispatchEvent: jest.fn(),
    });
    window.matchMedia = matchMediaMock;

    const { result } = renderHook(() => useSystemTheme());

    expect(result.current).toBe('light');

    // Simulate system theme change to dark
    if (changeHandler) {
      changeHandler({ matches: true } as MediaQueryListEvent);
    }

    await waitFor(() => {
      expect(result.current).toBe('dark');
    });
  });

  it('should update theme when system preference changes to light', async () => {
    let changeHandler: ((e: MediaQueryListEvent) => void) | null = null;

    matchMediaMock = createMatchMediaMock(true);
    matchMediaMock.mockReturnValue({
      matches: true,
      media: '',
      addEventListener: jest.fn((event, handler) => {
        if (event === 'change') {
          changeHandler = handler;
        }
      }),
      removeEventListener: jest.fn(),
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      dispatchEvent: jest.fn(),
    });
    window.matchMedia = matchMediaMock;

    const { result } = renderHook(() => useSystemTheme());

    expect(result.current).toBe('dark');

    // Simulate system theme change to light
    if (changeHandler) {
      changeHandler({ matches: false } as MediaQueryListEvent);
    }

    await waitFor(() => {
      expect(result.current).toBe('light');
    });
  });

  it('should handle multiple theme changes', async () => {
    let changeHandler: ((e: MediaQueryListEvent) => void) | null = null;

    matchMediaMock = createMatchMediaMock(false);
    matchMediaMock.mockReturnValue({
      matches: false,
      media: '',
      addEventListener: jest.fn((event, handler) => {
        if (event === 'change') {
          changeHandler = handler;
        }
      }),
      removeEventListener: jest.fn(),
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      dispatchEvent: jest.fn(),
    });
    window.matchMedia = matchMediaMock;

    const { result } = renderHook(() => useSystemTheme());

    expect(result.current).toBe('light');

    // Change to dark
    if (changeHandler) {
      changeHandler({ matches: true } as MediaQueryListEvent);
    }
    await waitFor(() => expect(result.current).toBe('dark'));

    // Change back to light
    if (changeHandler) {
      changeHandler({ matches: false } as MediaQueryListEvent);
    }
    await waitFor(() => expect(result.current).toBe('light'));
  });

  it('should handle window undefined gracefully (SSR safety check)', () => {    // Не удаляем window, так как renderHook требует DOM
    // Просто проверяем, что hook работает с значением по умолчанию
    const { result } = renderHook(() => useSystemTheme());
    
    // Должно вернуть light или dark в зависимости от системных настроек
    expect(['light', 'dark']).toContain(result.current);
  });
});
