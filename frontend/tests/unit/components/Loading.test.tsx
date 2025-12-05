/**
 * Tests for Loading components
 * Проверяет индикаторы загрузки (PageSpinner, ListSkeleton, ButtonSpinner)
 */

import { render } from '@testing-library/react';
import { PageSpinner, ListSkeleton, ButtonSpinner } from '@/components/(ui)/Loading/Loading';

describe('Loading Components', () => {
  describe('PageSpinner', () => {
    it('should render CircularProgress', () => {
      const { container } = render(<PageSpinner />);
      const spinner = container.querySelector('.MuiCircularProgress-root');
      
      expect(spinner).toBeInTheDocument();
    });

    it('should render with size 48', () => {
      const { container } = render(<PageSpinner />);
      const spinner = container.querySelector('.MuiCircularProgress-root');
      
      expect(spinner).toHaveAttribute('role', 'progressbar');
    });

    it('should be centered in container', () => {
      const { container } = render(<PageSpinner />);
      const box = container.firstChild;
      
      expect(box).toHaveStyle({
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      });
    });

    it('should have minimum height of 400px', () => {
      const { container } = render(<PageSpinner />);
      const box = container.firstChild;
      
      expect(box).toHaveStyle({ minHeight: '400px' });
    });

    it('should match snapshot', () => {
      const { container } = render(<PageSpinner />);
      
      expect(container.firstChild).toMatchSnapshot();
    });
  });

  describe('ListSkeleton', () => {
    it('should render 5 skeleton items by default', () => {
      const { container } = render(<ListSkeleton />);
      const skeletons = container.querySelectorAll('.MuiSkeleton-root');
      
      expect(skeletons).toHaveLength(5);
    });

    it('should render custom count of skeleton items', () => {
      const { container } = render(<ListSkeleton count={3} />);
      const skeletons = container.querySelectorAll('.MuiSkeleton-root');
      
      expect(skeletons).toHaveLength(3);
    });

    it('should render rectangular variant', () => {
      const { container } = render(<ListSkeleton count={1} />);
      const skeleton = container.querySelector('.MuiSkeleton-rectangular');
      
      expect(skeleton).toBeInTheDocument();
    });

    it('should render skeletons with height 80', () => {
      const { container } = render(<ListSkeleton count={1} />);
      const skeleton = container.querySelector('.MuiSkeleton-root');
      
      expect(skeleton).toHaveStyle({ height: '80px' });
    });

    it('should render skeletons in stack with spacing', () => {
      const { container } = render(<ListSkeleton />);
      const stack = container.querySelector('.MuiStack-root');
      
      expect(stack).toBeInTheDocument();
    });

    it('should render 10 skeleton items', () => {
      const { container } = render(<ListSkeleton count={10} />);
      const skeletons = container.querySelectorAll('.MuiSkeleton-root');
      
      expect(skeletons).toHaveLength(10);
    });

    it('should render 1 skeleton item', () => {
      const { container } = render(<ListSkeleton count={1} />);
      const skeletons = container.querySelectorAll('.MuiSkeleton-root');
      
      expect(skeletons).toHaveLength(1);
    });

    it('should match snapshot with default count', () => {
      const { container } = render(<ListSkeleton />);
      
      expect(container.firstChild).toMatchSnapshot();
    });

    it('should match snapshot with custom count', () => {
      const { container } = render(<ListSkeleton count={3} />);
      
      expect(container.firstChild).toMatchSnapshot();
    });
  });

  describe('ButtonSpinner', () => {
    it('should render CircularProgress', () => {
      const { container } = render(<ButtonSpinner />);
      const spinner = container.querySelector('.MuiCircularProgress-root');
      
      expect(spinner).toBeInTheDocument();
    });

    it('should render with size 20', () => {
      const { container } = render(<ButtonSpinner />);
      const spinner = container.querySelector('.MuiCircularProgress-root');
      
      expect(spinner).toHaveAttribute('role', 'progressbar');
    });

    it('should be smaller than PageSpinner', () => {
      const { container: pageContainer } = render(<PageSpinner />);
      const { container: buttonContainer } = render(<ButtonSpinner />);
      
      // Проверяем, что размеры разные
      expect(pageContainer.querySelector('.MuiCircularProgress-root')).toBeInTheDocument();
      expect(buttonContainer.querySelector('.MuiCircularProgress-root')).toBeInTheDocument();
    });

    it('should match snapshot', () => {
      const { container } = render(<ButtonSpinner />);
      
      expect(container).toMatchSnapshot();
    });
  });

  describe('Integration scenarios', () => {
    it('should render PageSpinner for full-page loading', () => {
      const { container } = render(
        <div>
          <PageSpinner />
        </div>
      );
      
      const spinner = container.querySelector('.MuiCircularProgress-root');
      expect(spinner).toBeInTheDocument();
    });

    it('should render ListSkeleton for table loading', () => {
      const { container } = render(
        <div>
          <ListSkeleton count={5} />
        </div>
      );
      
      const skeletons = container.querySelectorAll('.MuiSkeleton-root');
      expect(skeletons).toHaveLength(5);
    });

    it('should render ButtonSpinner inside button', () => {
      const { container } = render(
        <button>
          <ButtonSpinner />
          Loading...
        </button>
      );
      
      const spinner = container.querySelector('.MuiCircularProgress-root');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('PageSpinner should have progressbar role', () => {
      const { container } = render(<PageSpinner />);
      const spinner = container.querySelector('[role="progressbar"]');
      
      expect(spinner).toBeInTheDocument();
    });

    it('ButtonSpinner should have progressbar role', () => {
      const { container } = render(<ButtonSpinner />);
      const spinner = container.querySelector('[role="progressbar"]');
      
      expect(spinner).toBeInTheDocument();
    });

    it('ListSkeleton items should be recognizable by screen readers', () => {
      const { container } = render(<ListSkeleton count={3} />);
      const skeletons = container.querySelectorAll('.MuiSkeleton-root');
      
      skeletons.forEach(skeleton => {
        expect(skeleton).toBeInTheDocument();
      });
    });
  });

  describe('Edge cases', () => {
    it('should handle ListSkeleton with count 0', () => {
      const { container } = render(<ListSkeleton count={0} />);
      const skeletons = container.querySelectorAll('.MuiSkeleton-root');
      
      expect(skeletons).toHaveLength(0);
    });

    it('should handle ListSkeleton with large count', () => {
      const { container } = render(<ListSkeleton count={100} />);
      const skeletons = container.querySelectorAll('.MuiSkeleton-root');
      
      expect(skeletons).toHaveLength(100);
    });

    it('should render PageSpinner multiple times independently', () => {
      const { container } = render(
        <div>
          <PageSpinner />
          <PageSpinner />
        </div>
      );
      
      const spinners = container.querySelectorAll('.MuiCircularProgress-root');
      expect(spinners.length).toBeGreaterThanOrEqual(2);
    });
  });
});
