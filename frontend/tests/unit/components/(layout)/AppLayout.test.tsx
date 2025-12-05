import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AppLayout } from '@/components/(layout)/AppLayout';
import { useMediaQuery } from '@mui/material';

// Mock MUI hooks
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  useMediaQuery: jest.fn(),
}));

// Mock child components
jest.mock('@/components/(layout)/TopBar', () => ({
  TopBar: ({ onMenuClick }: any) => (
    <div data-testid="top-bar" onClick={onMenuClick}>
      TopBar Mock
    </div>
  ),
}));

jest.mock('@/components/(layout)/SidebarNav', () => ({
  SidebarNav: ({ open, onClose, variant }: any) => (
    <div data-testid="sidebar-nav" data-open={open} data-variant={variant}>
      SidebarNav Mock
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('AppLayout Component', () => {
  beforeEach(() => {
    (useMediaQuery as jest.Mock).mockReturnValue(false);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should render layout with TopBar and SidebarNav', () => {
    renderWithRouter(
      <AppLayout>
        <div>Test Content</div>
      </AppLayout>
    );

    expect(screen.getByTestId('top-bar')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar-nav')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('should render children content in main area', () => {
    renderWithRouter(
      <AppLayout>
        <div data-testid="child-content">
          <h1>Dashboard</h1>
          <p>Content area</p>
        </div>
      </AppLayout>
    );

    const childContent = screen.getByTestId('child-content');
    expect(childContent).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Content area')).toBeInTheDocument();
  });

  it('should use permanent sidebar variant on desktop', () => {
    (useMediaQuery as jest.Mock).mockReturnValue(false); // desktop

    renderWithRouter(
      <AppLayout>
        <div>Desktop Content</div>
      </AppLayout>
    );

    const sidebar = screen.getByTestId('sidebar-nav');
    expect(sidebar).toHaveAttribute('data-variant', 'permanent');
    expect(sidebar).toHaveAttribute('data-open', 'true');
  });

  it('should use temporary sidebar variant on mobile', () => {
    (useMediaQuery as jest.Mock).mockReturnValue(true); // mobile

    renderWithRouter(
      <AppLayout>
        <div>Mobile Content</div>
      </AppLayout>
    );

    const sidebar = screen.getByTestId('sidebar-nav');
    expect(sidebar).toHaveAttribute('data-variant', 'temporary');
    expect(sidebar).toHaveAttribute('data-open', 'false'); // closed by default
  });

  it('should apply correct styles to main container', () => {
    const { container } = renderWithRouter(
      <AppLayout>
        <div>Test</div>
      </AppLayout>
    );

    const mainBox = container.querySelector('[component="main"]');
    expect(mainBox).toBeInTheDocument();
  });

  it('should render with multiple children', () => {
    renderWithRouter(
      <AppLayout>
        <div data-testid="child-1">First Child</div>
        <div data-testid="child-2">Second Child</div>
        <div data-testid="child-3">Third Child</div>
      </AppLayout>
    );

    expect(screen.getByTestId('child-1')).toBeInTheDocument();
    expect(screen.getByTestId('child-2')).toBeInTheDocument();
    expect(screen.getByTestId('child-3')).toBeInTheDocument();
  });

  it('should have proper layout structure', () => {
    const { container } = renderWithRouter(
      <AppLayout>
        <div>Content</div>
      </AppLayout>
    );

    // Check flex container
    const flexBox = container.querySelector('[sx]');
    expect(flexBox).toBeInTheDocument();
  });

  it('should maintain state between renders', () => {
    const { rerender } = renderWithRouter(
      <AppLayout>
        <div>Initial Content</div>
      </AppLayout>
    );

    expect(screen.getByText('Initial Content')).toBeInTheDocument();

    rerender(
      <BrowserRouter>
        <AppLayout>
          <div>Updated Content</div>
        </AppLayout>
      </BrowserRouter>
    );

    expect(screen.getByText('Updated Content')).toBeInTheDocument();
    expect(screen.queryByText('Initial Content')).not.toBeInTheDocument();
  });
});
