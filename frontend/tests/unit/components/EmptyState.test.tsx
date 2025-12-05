/**
 * Tests for EmptyState component
 * Проверяет компонент для отображения пустых состояний
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { EmptyState } from '@/components/(ui)/EmptyState/EmptyState';
import { Package } from 'lucide-react';

describe('EmptyState', () => {
  describe('Rendering', () => {
    it('should render title', () => {
      render(<EmptyState title="No data" />);
      
      expect(screen.getByText('No data')).toBeInTheDocument();
    });

    it('should render description when provided', () => {
      render(
        <EmptyState 
          title="No data" 
          description="There are no items to display"
        />
      );
      
      expect(screen.getByText('There are no items to display')).toBeInTheDocument();
    });

    it('should not render description when not provided', () => {
      const { container } = render(<EmptyState title="No data" />);
      
      const descriptions = container.querySelectorAll('.MuiTypography-body1');
      expect(descriptions.length).toBe(0);
    });

    it('should render icon when provided', () => {
      render(
        <EmptyState 
          title="No packages" 
          icon={<Package data-testid="package-icon" />}
        />
      );
      
      expect(screen.getByTestId('package-icon')).toBeInTheDocument();
    });

    it('should not render icon when not provided', () => {
      const { container } = render(<EmptyState title="No data" />);
      
      // Icon wrapper не должен существовать
      const iconWrapper = container.querySelector('[style*="fontSize: 80"]');
      expect(iconWrapper).not.toBeInTheDocument();
    });
  });

  describe('Action button', () => {
    it('should render action button when both actionLabel and onAction are provided', () => {
      const handleAction = jest.fn();
      render(
        <EmptyState 
          title="No items" 
          actionLabel="Add Item"
          onAction={handleAction}
        />
      );
      
      expect(screen.getByText('Add Item')).toBeInTheDocument();
    });

    it('should not render action button when actionLabel is missing', () => {
      const handleAction = jest.fn();
      render(
        <EmptyState 
          title="No items" 
          onAction={handleAction}
        />
      );
      
      const button = screen.queryByRole('button');
      expect(button).not.toBeInTheDocument();
    });

    it('should not render action button when onAction is missing', () => {
      render(
        <EmptyState 
          title="No items" 
          actionLabel="Add Item"
        />
      );
      
      const button = screen.queryByRole('button');
      expect(button).not.toBeInTheDocument();
    });

    it('should call onAction when action button is clicked', () => {
      const handleAction = jest.fn();
      render(
        <EmptyState 
          title="No items" 
          actionLabel="Add Item"
          onAction={handleAction}
        />
      );
      
      fireEvent.click(screen.getByText('Add Item'));
      
      expect(handleAction).toHaveBeenCalledTimes(1);
    });

    it('should render Plus icon in action button', () => {
      const handleAction = jest.fn();
      const { container } = render(
        <EmptyState 
          title="No items" 
          actionLabel="Add Item"
          onAction={handleAction}
        />
      );
      
      // MUI Button с startIcon
      const button = container.querySelector('.MuiButton-startIcon');
      expect(button).toBeInTheDocument();
    });
  });

  describe('Layout and styling', () => {
    it('should render with centered layout', () => {
      const { container } = render(<EmptyState title="No data" />);
      const box = container.firstChild;
      
      expect(box).toHaveStyle({
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      });
    });

    it('should render title as h5 variant', () => {
      render(<EmptyState title="No data" />);
      
      const title = screen.getByText('No data');
      expect(title.tagName).toBe('H5');
    });

    it('should apply text-center to container', () => {
      const { container } = render(<EmptyState title="No data" />);
      const box = container.firstChild;
      
      expect(box).toHaveStyle({ textAlign: 'center' });
    });
  });

  describe('Complete examples', () => {
    it('should render full example with all props', () => {
      const handleAction = jest.fn();
      render(
        <EmptyState 
          icon={<Package data-testid="icon" />}
          title="No packages found"
          description="You haven't created any packages yet. Get started by creating your first package."
          actionLabel="Create Package"
          onAction={handleAction}
        />
      );
      
      expect(screen.getByTestId('icon')).toBeInTheDocument();
      expect(screen.getByText('No packages found')).toBeInTheDocument();
      expect(screen.getByText(/You haven't created any packages yet/)).toBeInTheDocument();
      expect(screen.getByText('Create Package')).toBeInTheDocument();
    });

    it('should render minimal example with only title', () => {
      render(<EmptyState title="No data" />);
      
      expect(screen.getByText('No data')).toBeInTheDocument();
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('should render with title and description only', () => {
      render(
        <EmptyState 
          title="No items"
          description="Add your first item to get started"
        />
      );
      
      expect(screen.getByText('No items')).toBeInTheDocument();
      expect(screen.getByText('Add your first item to get started')).toBeInTheDocument();
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible heading', () => {
      render(<EmptyState title="No data" />);
      
      const heading = screen.getByRole('heading', { level: 5 });
      expect(heading).toBeInTheDocument();
      expect(heading).toHaveTextContent('No data');
    });

    it('should have accessible button when action is provided', () => {
      const handleAction = jest.fn();
      render(
        <EmptyState 
          title="No items" 
          actionLabel="Add Item"
          onAction={handleAction}
        />
      );
      
      const button = screen.getByRole('button', { name: 'Add Item' });
      expect(button).toBeInTheDocument();
    });
  });

  describe('Icon styling', () => {
    it('should apply correct styles to icon container', () => {
      const { container } = render(
        <EmptyState 
          title="No data"
          icon={<Package />}
        />
      );
      
      // Проверяем стили контейнера иконки
      const iconBox = container.querySelector('[style*="fontSize: 80"]');
      expect(iconBox).toBeInTheDocument();
    });
  });

  describe('Snapshots', () => {
    it('should match snapshot for full example', () => {
      const handleAction = jest.fn();
      const { container } = render(
        <EmptyState 
          icon={<Package />}
          title="No packages found"
          description="Create your first package to get started"
          actionLabel="Create Package"
          onAction={handleAction}
        />
      );
      
      expect(container.firstChild).toMatchSnapshot();
    });

    it('should match snapshot for minimal example', () => {
      const { container } = render(<EmptyState title="No data" />);
      
      expect(container.firstChild).toMatchSnapshot();
    });
  });
});
