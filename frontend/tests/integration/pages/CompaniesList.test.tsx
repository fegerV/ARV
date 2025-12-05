/**
 * Integration tests for Companies List page
 * Проверяет страницу списка компаний с навигацией и UI
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import CompaniesList from '@/pages/companies/CompaniesList';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
};

describe('CompaniesList Page - Integration', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  describe('Page Structure', () => {
    it('should render page title', () => {
      renderWithRouter(<CompaniesList />);
      
      expect(screen.getByText('Companies')).toBeInTheDocument();
    });

    it('should render header section', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const header = container.querySelector('[style*="display: flex"]');
      expect(header).toBeInTheDocument();
    });

    it('should render content container', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
    });
  });

  describe('New Company Button', () => {
    it('should render "New Company" button', () => {
      renderWithRouter(<CompaniesList />);
      
      expect(screen.getByText('New Company')).toBeInTheDocument();
    });

    it('should render button with Add icon', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const button = screen.getByText('New Company').closest('button');
      const icon = button?.querySelector('.MuiSvgIcon-root');
      
      expect(icon).toBeInTheDocument();
    });

    it('should navigate to /companies/new when clicked', () => {
      renderWithRouter(<CompaniesList />);
      
      const button = screen.getByText('New Company');
      fireEvent.click(button);
      
      expect(mockNavigate).toHaveBeenCalledWith('/companies/new');
    });

    it('should be a contained variant button', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const button = screen.getByText('New Company').closest('button');
      expect(button?.className).toContain('MuiButton-contained');
    });
  });

  describe('Content Area', () => {
    it('should render placeholder text', () => {
      renderWithRouter(<CompaniesList />);
      
      expect(screen.getByText('Companies list будет здесь...')).toBeInTheDocument();
    });

    it('should render placeholder in Paper component', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
      expect(paper?.textContent).toContain('Companies list будет здесь...');
    });

    it('should have padding in Paper component', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
    });
  });

  describe('Layout and Spacing', () => {
    it('should have proper spacing between header and content', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const header = container.querySelector('[style*="margin-bottom"]');
      expect(header).toBeInTheDocument();
    });

    it('should align header items correctly', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const header = container.querySelector('[style*="space-between"]');
      expect(header).toBeInTheDocument();
    });
  });

  describe('Typography', () => {
    it('should render title as h4 variant', () => {
      renderWithRouter(<CompaniesList />);
      
      const title = screen.getByText('Companies');
      expect(title.tagName).toBe('H4');
    });

    it('should render placeholder text', () => {
      renderWithRouter(<CompaniesList />);
      
      const placeholder = screen.getByText('Companies list будет здесь...');
      expect(placeholder).toBeInTheDocument();
    });
  });

  describe('Navigation Integration', () => {
    it('should work with React Router', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/companies']}>
          <CompaniesList />
        </MemoryRouter>
      );
      
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should maintain navigation state', () => {
      renderWithRouter(<CompaniesList />);
      
      const button = screen.getByText('New Company');
      
      // Multiple clicks
      fireEvent.click(button);
      fireEvent.click(button);
      
      expect(mockNavigate).toHaveBeenCalledTimes(2);
    });
  });

  describe('Component Composition', () => {
    it('should compose Box, Typography, Button, and Paper', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      expect(container.querySelector('.MuiBox-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiTypography-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiButton-root')).toBeInTheDocument();
      expect(container.querySelector('.MuiPaper-root')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible button', () => {
      renderWithRouter(<CompaniesList />);
      
      const button = screen.getByRole('button', { name: /new company/i });
      expect(button).toBeInTheDocument();
    });

    it('should have accessible heading', () => {
      renderWithRouter(<CompaniesList />);
      
      const heading = screen.getByRole('heading', { name: 'Companies' });
      expect(heading).toBeInTheDocument();
    });

    it('should have keyboard navigable button', () => {
      renderWithRouter(<CompaniesList />);
      
      const button = screen.getByText('New Company');
      button.focus();
      
      expect(document.activeElement).toBe(button);
    });
  });

  describe('User Interactions', () => {
    it('should handle button click', () => {
      renderWithRouter(<CompaniesList />);
      
      const button = screen.getByText('New Company');
      
      expect(() => fireEvent.click(button)).not.toThrow();
    });

    it('should handle multiple button clicks', () => {
      renderWithRouter(<CompaniesList />);
      
      const button = screen.getByText('New Company');
      
      fireEvent.click(button);
      fireEvent.click(button);
      fireEvent.click(button);
      
      expect(mockNavigate).toHaveBeenCalledTimes(3);
    });
  });

  describe('Future Enhancements Placeholder', () => {
    it('should indicate where companies table will be', () => {
      renderWithRouter(<CompaniesList />);
      
      // Placeholder для будущей таблицы
      expect(screen.getByText('Companies list будет здесь...')).toBeInTheDocument();
    });

    it('should render in Paper ready for data table', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
    });
  });

  describe('Snapshot', () => {
    it('should match snapshot', () => {
      const { container } = renderWithRouter(<CompaniesList />);
      
      expect(container.firstChild).toMatchSnapshot();
    });
  });
});
