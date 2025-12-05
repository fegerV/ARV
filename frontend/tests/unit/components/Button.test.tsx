/**
 * Tests for Button component
 * Проверяет базовую кнопку с различными вариантами
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/(ui)/Button/Button';
import { Search } from 'lucide-react';

describe('Button', () => {
  describe('Rendering', () => {
    it('should render button with text', () => {
      render(<Button>Click me</Button>);
      
      expect(screen.getByText('Click me')).toBeInTheDocument();
    });

    it('should render as button element by default', () => {
      render(<Button>Click me</Button>);
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'button');
    });
  });

  describe('Variants', () => {
    it('should render primary variant by default', () => {
      const { container } = render(<Button>Primary</Button>);
      const button = container.querySelector('.MuiButton-contained');
      
      expect(button).toBeInTheDocument();
    });

    it('should render secondary variant', () => {
      const { container } = render(<Button variant="secondary">Secondary</Button>);
      const button = container.querySelector('.MuiButton-outlined');
      
      expect(button).toBeInTheDocument();
    });

    it('should render danger variant', () => {
      const { container } = render(<Button variant="danger">Danger</Button>);
      const button = container.querySelector('.MuiButton-contained');
      const errorButton = container.querySelector('.MuiButton-colorError');
      
      expect(button).toBeInTheDocument();
      expect(errorButton).toBeInTheDocument();
    });

    it('should render ghost variant', () => {
      const { container } = render(<Button variant="ghost">Ghost</Button>);
      const button = container.querySelector('.MuiButton-text');
      
      expect(button).toBeInTheDocument();
    });
  });

  describe('Sizes', () => {
    it('should render medium size by default', () => {
      const { container } = render(<Button>Medium</Button>);
      const button = container.querySelector('.MuiButton-sizeMedium');
      
      expect(button).toBeInTheDocument();
    });

    it('should render small size', () => {
      const { container } = render(<Button size="small">Small</Button>);
      const button = container.querySelector('.MuiButton-sizeSmall');
      
      expect(button).toBeInTheDocument();
    });

    it('should render large size', () => {
      const { container } = render(<Button size="large">Large</Button>);
      const button = container.querySelector('.MuiButton-sizeLarge');
      
      expect(button).toBeInTheDocument();
    });
  });

  describe('States', () => {
    it('should be disabled when disabled prop is true', () => {
      render(<Button disabled>Disabled</Button>);
      
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should be disabled when loading prop is true', () => {
      render(<Button loading>Loading</Button>);
      
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });

    it('should show loading spinner when loading', () => {
      const { container } = render(<Button loading>Loading</Button>);
      const spinner = container.querySelector('.MuiCircularProgress-root');
      
      expect(spinner).toBeInTheDocument();
    });

    it('should not be disabled by default', () => {
      render(<Button>Enabled</Button>);
      
      const button = screen.getByRole('button');
      expect(button).not.toBeDisabled();
    });
  });

  describe('Click handling', () => {
    it('should call onClick when clicked', () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>Click me</Button>);
      
      fireEvent.click(screen.getByText('Click me'));
      
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should not call onClick when disabled', () => {
      const handleClick = jest.fn();
      render(<Button disabled onClick={handleClick}>Disabled</Button>);
      
      fireEvent.click(screen.getByText('Disabled'));
      
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('should not call onClick when loading', () => {
      const handleClick = jest.fn();
      render(<Button loading onClick={handleClick}>Loading</Button>);
      
      fireEvent.click(screen.getByText('Loading'));
      
      expect(handleClick).not.toHaveBeenCalled();
    });
  });

  describe('Icons', () => {
    it('should render startIcon', () => {
      const { container } = render(
        <Button startIcon={<Search data-testid="start-icon" />}>
          Search
        </Button>
      );
      
      expect(screen.getByTestId('start-icon')).toBeInTheDocument();
    });

    it('should render endIcon', () => {
      const { container } = render(
        <Button endIcon={<Search data-testid="end-icon" />}>
          Search
        </Button>
      );
      
      expect(screen.getByTestId('end-icon')).toBeInTheDocument();
    });

    it('should replace startIcon with spinner when loading', () => {
      const { container } = render(
        <Button loading startIcon={<Search data-testid="start-icon" />}>
          Loading
        </Button>
      );
      
      const spinner = container.querySelector('.MuiCircularProgress-root');
      expect(spinner).toBeInTheDocument();
      expect(screen.queryByTestId('start-icon')).not.toBeInTheDocument();
    });

    it('should keep endIcon when loading', () => {
      const { container } = render(
        <Button loading endIcon={<Search data-testid="end-icon" />}>
          Loading
        </Button>
      );
      
      expect(screen.getByTestId('end-icon')).toBeInTheDocument();
    });
  });

  describe('Layout', () => {
    it('should render full width when fullWidth is true', () => {
      const { container } = render(<Button fullWidth>Full Width</Button>);
      const button = container.querySelector('.MuiButton-fullWidth');
      
      expect(button).toBeInTheDocument();
    });

    it('should not render full width by default', () => {
      const { container } = render(<Button>Normal</Button>);
      const button = container.querySelector('.MuiButton-fullWidth');
      
      expect(button).not.toBeInTheDocument();
    });
  });

  describe('Type attribute', () => {
    it('should have type="button" by default', () => {
      render(<Button>Default</Button>);
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'button');
    });

    it('should have type="submit" when specified', () => {
      render(<Button type="submit">Submit</Button>);
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'submit');
    });

    it('should have type="reset" when specified', () => {
      render(<Button type="reset">Reset</Button>);
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('type', 'reset');
    });
  });

  describe('Ref forwarding', () => {
    it('should forward ref to button element', () => {
      const ref = React.createRef<HTMLButtonElement>();
      render(<Button ref={ref}>With Ref</Button>);
      
      expect(ref.current).toBeInstanceOf(HTMLButtonElement);
      expect(ref.current?.tagName).toBe('BUTTON');
    });
  });

  describe('Styling', () => {
    it('should have textTransform: none', () => {
      const { container } = render(<Button>No Transform</Button>);
      const button = container.querySelector('.MuiButton-root');
      
      expect(button).toHaveStyle({ textTransform: 'none' });
    });

    it('should have fontWeight: 500', () => {
      const { container } = render(<Button>Medium Weight</Button>);
      const button = container.querySelector('.MuiButton-root');
      
      expect(button).toHaveStyle({ fontWeight: 500 });
    });
  });

  describe('Accessibility', () => {
    it('should be accessible by role', () => {
      render(<Button>Accessible</Button>);
      
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('should be accessible by text', () => {
      render(<Button>Click Here</Button>);
      
      expect(screen.getByText('Click Here')).toBeInTheDocument();
    });
  });

  describe('Snapshots', () => {
    it('should match snapshot for primary variant', () => {
      const { container } = render(<Button variant="primary">Primary</Button>);
      expect(container.firstChild).toMatchSnapshot();
    });

    it('should match snapshot for loading state', () => {
      const { container } = render(<Button loading>Loading</Button>);
      expect(container.firstChild).toMatchSnapshot();
    });

    it('should match snapshot for disabled state', () => {
      const { container } = render(<Button disabled>Disabled</Button>);
      expect(container.firstChild).toMatchSnapshot();
    });
  });
});

// Import React for ref test
import React from 'react';
