import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import YandexDiskCallback from '../YandexDiskCallback';

// Mock window.opener
const mockOpener = {
  postMessage: jest.fn(),
  closed: false,
};
Object.defineProperty(window, 'opener', {
  writable: true,
  value: mockOpener,
});

// Mock window.close
const mockClose = jest.fn();
Object.defineProperty(window, 'close', {
  writable: true,
  value: mockClose,
});

// Mock useSearchParams to return custom params
const mockUseSearchParams = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useSearchParams: () => mockUseSearchParams(),
}));

describe('YandexDiskCallback', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const renderWithRouter = (initialEntries = ['/oauth/yandex/callback']) => {
    return render(
      <MemoryRouter initialEntries={initialEntries}>
        <YandexDiskCallback />
      </MemoryRouter>
    );
  };

  it('renders processing state initially', () => {
    mockUseSearchParams.mockReturnValue([new URLSearchParams(), jest.fn()]);
    renderWithRouter();
    
    expect(screen.getByText('Processing Authorization...')).toBeInTheDocument();
    expect(screen.getByText('Please wait while we process your authorization.')).toBeInTheDocument();
  });

  it('displays success state for successful OAuth', async () => {
    const params = new URLSearchParams('success=true&connectionId=123');
    mockUseSearchParams.mockReturnValue([params, jest.fn()]);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText('Authorization Successful!')).toBeInTheDocument();
      expect(screen.getByText('Your Yandex Disk has been successfully connected.')).toBeInTheDocument();
    });

    expect(mockOpener.postMessage).toHaveBeenCalledWith(
      {
        type: 'YANDEX_OAUTH_SUCCESS',
        data: {
          connectionId: 123,
        },
      },
      window.location.origin
    );

    // Fast-forward timers
    jest.advanceTimersByTime(2000);
    await waitFor(() => {
      expect(mockClose).toHaveBeenCalled();
    });
  });

  it('displays error state for failed OAuth', async () => {
    const params = new URLSearchParams('error=Access%20denied');
    mockUseSearchParams.mockReturnValue([params, jest.fn()]);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText('Authorization Failed')).toBeInTheDocument();
      expect(screen.getByText('Access denied')).toBeInTheDocument();
    });

    expect(mockOpener.postMessage).toHaveBeenCalledWith(
      {
        type: 'YANDEX_OAUTH_ERROR',
        data: {
          error: 'Access denied',
        },
      },
      window.location.origin
    );

    // Fast-forward timers
    jest.advanceTimersByTime(3000);
    await waitFor(() => {
      expect(mockClose).toHaveBeenCalled();
    });
  });

  it('handles invalid callback parameters', async () => {
    const params = new URLSearchParams('');
    mockUseSearchParams.mockReturnValue([params, jest.fn()]);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(mockOpener.postMessage).toHaveBeenCalledWith(
        {
          type: 'YANDEX_OAUTH_ERROR',
          data: {
            error: 'Invalid callback parameters received',
          },
        },
        window.location.origin
      );
    });

    // Fast-forward timers
    jest.advanceTimersByTime(3000);
    await waitFor(() => {
      expect(mockClose).toHaveBeenCalled();
    });
  });

  it('handles success without connection ID', async () => {
    const params = new URLSearchParams('success=true');
    mockUseSearchParams.mockReturnValue([params, jest.fn()]);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(mockOpener.postMessage).toHaveBeenCalledWith(
        {
          type: 'YANDEX_OAUTH_ERROR',
          data: {
            error: 'Invalid callback parameters received',
          },
        },
        window.location.origin
      );
    });
  });

  it('shows fallback messaging for manual closure', async () => {
    const params = new URLSearchParams('error=Some%20error');
    mockUseSearchParams.mockReturnValue([params, jest.fn()]);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText('If this window doesn\'t close automatically, you can close it manually.')).toBeInTheDocument();
    });
  });

  it('handles window.opener being closed', async () => {
    const params = new URLSearchParams('success=true&connectionId=123');
    mockUseSearchParams.mockReturnValue([params, jest.fn()]);
    mockOpener.closed = true;
    
    renderWithRouter();
    
    await waitFor(() => {
      // Should not throw error even if opener is closed
      expect(mockOpener.postMessage).not.toHaveBeenCalled();
    });
  });

  it('decodes error messages properly', async () => {
    const params = new URLSearchParams('error=Invalid%20credentials%20provided');
    mockUseSearchParams.mockReturnValue([params, jest.fn()]);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText('Invalid credentials provided')).toBeInTheDocument();
      expect(mockOpener.postMessage).toHaveBeenCalledWith(
        {
          type: 'YANDEX_OAUTH_ERROR',
          data: {
            error: 'Invalid credentials provided',
          },
        },
        window.location.origin
      );
    });
  });
});