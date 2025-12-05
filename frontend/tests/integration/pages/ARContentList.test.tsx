/**
 * Integration tests for AR Content List page
 * Проверяет страницу списка AR контента с таблицей и навигацией
 */

import { render, screen, fireEvent, within } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import ARContentList from '@/pages/ar-content/ARContentList';

const mockNavigate = jest.fn();
const mockProjectId = '123';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => ({ projectId: mockProjectId }),
}));

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('ARContentList Page - Integration', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  describe('Page Structure', () => {
    it('should render page title', () => {
      renderWithRouter(<ARContentList />);
      
      expect(screen.getByText('AR Content')).toBeInTheDocument();
    });

    it('should render header with title and button', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const header = container.querySelector('[style*="display: flex"]');
      expect(header).toBeInTheDocument();
    });

    it('should render content in Paper component', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
    });
  });

  describe('New AR Content Button', () => {
    it('should render "New AR Content" button', () => {
      renderWithRouter(<ARContentList />);
      
      expect(screen.getByText('New AR Content')).toBeInTheDocument();
    });

    it('should render button with Add icon', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const button = screen.getByText('New AR Content').closest('button');
      const icon = button?.querySelector('.MuiSvgIcon-root');
      
      expect(icon).toBeInTheDocument();
    });

    it('should navigate to content creation page with project ID', () => {
      renderWithRouter(<ARContentList />);
      
      const button = screen.getByText('New AR Content');
      fireEvent.click(button);
      
      expect(mockNavigate).toHaveBeenCalledWith(`/projects/${mockProjectId}/content/new`);
    });

    it('should be a contained variant button', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const button = screen.getByText('New AR Content').closest('button');
      expect(button?.className).toContain('MuiButton-contained');
    });
  });

  describe('Content Table', () => {
    it('should render table with headers', () => {
      renderWithRouter(<ARContentList />);
      
      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Marker Status')).toBeInTheDocument();
      expect(screen.getByText('Videos')).toBeInTheDocument();
      expect(screen.getByText('Views')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });

    it('should render table structure', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const table = container.querySelector('.MuiTable-root');
      expect(table).toBeInTheDocument();
    });

    it('should render table head', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const tableHead = container.querySelector('.MuiTableHead-root');
      expect(tableHead).toBeInTheDocument();
    });

    it('should render table body', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const tableBody = container.querySelector('.MuiTableBody-root');
      expect(tableBody).toBeInTheDocument();
    });
  });

  describe('Mock Data Display', () => {
    it('should display mock content title', () => {
      renderWithRouter(<ARContentList />);
      
      expect(screen.getByText('Постер #1 - Санта с подарками')).toBeInTheDocument();
    });

    it('should display marker status badge', () => {
      renderWithRouter(<ARContentList />);
      
      expect(screen.getByText('✅ Ready')).toBeInTheDocument();
    });

    it('should display videos count', () => {
      renderWithRouter(<ARContentList />);
      
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('should display views count with formatting', () => {
      renderWithRouter(<ARContentList />);
      
      expect(screen.getByText('3,245')).toBeInTheDocument();
    });

    it('should render status badge with correct color', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const successChip = container.querySelector('.MuiChip-colorSuccess');
      expect(successChip).toBeInTheDocument();
    });
  });

  describe('Action Buttons', () => {
    it('should render view details button', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const viewButton = container.querySelector('button[title="View Details"]');
      expect(viewButton).toBeInTheDocument();
    });

    it('should render icon button with ViewIcon', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const iconButton = container.querySelector('.MuiIconButton-root');
      expect(iconButton).toBeInTheDocument();
    });

    it('should navigate to content detail page on view click', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const viewButton = container.querySelector('button[title="View Details"]') as HTMLElement;
      fireEvent.click(viewButton);
      
      expect(mockNavigate).toHaveBeenCalledWith('/ar-content/456');
    });
  });

  describe('Table Structure Details', () => {
    it('should have 5 column headers', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const headerCells = container.querySelectorAll('.MuiTableHead-root .MuiTableCell-root');
      expect(headerCells).toHaveLength(5);
    });

    it('should render data row', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const bodyRows = container.querySelectorAll('.MuiTableBody-root .MuiTableRow-root');
      expect(bodyRows.length).toBeGreaterThan(0);
    });

    it('should display all columns in data row', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const bodyRow = container.querySelector('.MuiTableBody-root .MuiTableRow-root');
      const cells = bodyRow?.querySelectorAll('.MuiTableCell-root');
      
      expect(cells).toHaveLength(5);
    });
  });

  describe('Layout and Spacing', () => {
    it('should have proper spacing between header and table', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const header = container.querySelector('[style*="margin-bottom"]');
      expect(header).toBeInTheDocument();
    });

    it('should render table in padded Paper', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
    });
  });

  describe('Typography', () => {
    it('should render title as h4 variant', () => {
      renderWithRouter(<ARContentList />);
      
      const title = screen.getByText('AR Content');
      expect(title.tagName).toBe('H4');
    });
  });

  describe('Status Badge Integration', () => {
    it('should show ready status badge for ready marker', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const readyBadge = screen.getByText('✅ Ready');
      expect(readyBadge).toBeInTheDocument();
    });

    it('should render badge as Chip component', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const chip = container.querySelector('.MuiChip-root');
      expect(chip).toBeInTheDocument();
    });

    it('should render small size badge', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const smallChip = container.querySelector('.MuiChip-sizeSmall');
      expect(smallChip).toBeInTheDocument();
    });
  });

  describe('Navigation Integration', () => {
    it('should work with React Router params', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/projects/123/content']}>
          <ARContentList />
        </MemoryRouter>
      );
      
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should use projectId from params in navigation', () => {
      renderWithRouter(<ARContentList />);
      
      const button = screen.getByText('New AR Content');
      fireEvent.click(button);
      
      expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining(mockProjectId));
    });
  });

  describe('Data Formatting', () => {
    it('should format views with thousands separator', () => {
      renderWithRouter(<ARContentList />);
      
      // 3245 должно отображаться как "3,245"
      expect(screen.getByText('3,245')).toBeInTheDocument();
    });

    it('should display videos count as number', () => {
      renderWithRouter(<ARContentList />);
      
      expect(screen.getByText('5')).toBeInTheDocument();
    });
  });

  describe('Component Composition', () => {
    it('should compose Table components correctly', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      expect(container.querySelector('.MuiTable-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiTableHead-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiTableBody-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiTableRow-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiTableCell-root')).toBeInTheDocument();
    });

    it('should compose UI elements correctly', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      expect(container.querySelector('.MuiBox-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiPaper-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiButton-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiIconButton-root')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible buttons', () => {
      renderWithRouter(<ARContentList />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('should have accessible heading', () => {
      renderWithRouter(<ARContentList />);
      
      const heading = screen.getByRole('heading', { name: 'AR Content' });
      expect(heading).toBeInTheDocument();
    });

    it('should have accessible table', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const table = container.querySelector('table');
      expect(table).toBeInTheDocument();
    });

    it('should have title attribute on icon button', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const button = container.querySelector('button[title="View Details"]');
      expect(button).toBeInTheDocument();
      expect(button).toHaveAttribute('title', 'View Details');
    });
  });

  describe('User Interactions', () => {
    it('should handle new content button click', () => {
      renderWithRouter(<ARContentList />);
      
      const button = screen.getByText('New AR Content');
      
      expect(() => fireEvent.click(button)).not.toThrow();
    });

    it('should handle view button click', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      const viewButton = container.querySelector('button[title="View Details"]') as HTMLElement;
      
      expect(() => fireEvent.click(viewButton)).not.toThrow();
    });
  });

  describe('Snapshot', () => {
    it('should match snapshot', () => {
      const { container } = renderWithRouter(<ARContentList />);
      
      expect(container.firstChild).toMatchSnapshot();
    });
  });
});
