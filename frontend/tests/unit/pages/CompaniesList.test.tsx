import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CompaniesList from '@/pages/companies/CompaniesList';
import { BrowserRouter } from 'react-router-dom';

// Mock the API services
jest.mock('@/services/api', () => ({
  companiesAPI: {
    list: jest.fn(),
  },
}));

jest.mock('@/services/companies', () => ({
  companiesApi: {
    storageConnections: jest.fn(),
  },
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('CompaniesList', () => {
  const mockCompanies = [
    {
      id: 1,
      name: 'Test Company',
      slug: 'test-company',
      is_default: false,
      is_active: true,
      storage_connection_id: 1,
      storage_path: '/test',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
      contact_email: 'test@example.com',
      storage_quota_gb: 10,
      storage_used_gb: 2.5,
    },
    {
      id: 2,
      name: 'Default Company',
      slug: 'default',
      is_default: true,
      is_active: true,
      storage_connection_id: 1,
      storage_path: '/',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z',
    },
  ];

  const mockStorageConnections = [
    {
      id: 1,
      name: 'Local Storage',
      provider: 'local_disk',
      is_active: true,
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    require('@/services/api').companiesAPI.list.mockResolvedValue({ data: mockCompanies });
    require('@/services/companies').companiesApi.storageConnections.mockResolvedValue({ data: mockStorageConnections });
  });

  it('renders companies list correctly', async () => {
    render(
      <BrowserRouter>
        <CompaniesList />
      </BrowserRouter>
    );

    // Check loading state
    expect(screen.getByText('Companies')).toBeInTheDocument();
    expect(screen.getByText('New Company')).toBeInTheDocument();

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('Test Company')).toBeInTheDocument();
    });

    // Check that companies are displayed
    expect(screen.getByText('Test Company')).toBeInTheDocument();
    expect(screen.getByText('Default Company')).toBeInTheDocument();
    expect(screen.getByText('test-company')).toBeInTheDocument();
    expect(screen.getByText('default')).toBeInTheDocument();
  });

  it('allows searching companies', async () => {
    render(
      <BrowserRouter>
        <CompaniesList />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Company')).toBeInTheDocument();
    });

    // Type in search box
    const searchInput = screen.getByPlaceholderText('Search companies...');
    fireEvent.change(searchInput, { target: { value: 'Test' } });

    // Should show only matching company
    expect(screen.getByText('Test Company')).toBeInTheDocument();
    expect(screen.queryByText('Default Company')).not.toBeInTheDocument();
  });

  it('filters companies by status', async () => {
    render(
      <BrowserRouter>
        <CompaniesList />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Company')).toBeInTheDocument();
    });

    // Select inactive status filter
    const statusFilter = screen.getByLabelText('Status');
    fireEvent.click(statusFilter);
    fireEvent.click(screen.getByText('Inactive'));

    // Should show all companies since both are active
    expect(screen.getByText('Test Company')).toBeInTheDocument();
  });

  it('navigates to company details when row is clicked', async () => {
    render(
      <BrowserRouter>
        <CompaniesList />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Company')).toBeInTheDocument();
    });

    // Click on a company row
    const companyRow = screen.getByText('Test Company').closest('tr');
    fireEvent.click(companyRow!);

    // Should navigate to company details
    expect(mockNavigate).toHaveBeenCalledWith('/companies/1');
  });

  it('navigates to new company form when button is clicked', async () => {
    render(
      <BrowserRouter>
        <CompaniesList />
      </BrowserRouter>
    );

    const newCompanyButton = screen.getByText('New Company');
    fireEvent.click(newCompanyButton);

    expect(mockNavigate).toHaveBeenCalledWith('/companies/new');
  });
});