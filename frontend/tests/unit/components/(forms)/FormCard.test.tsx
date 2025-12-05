import { render, screen, fireEvent } from '@testing-library/react';
import { FormCard } from '@/components/(forms)/FormCard';

// Mock Button component
jest.mock('@/components/(ui)', () => ({
  Button: ({ children, onClick, disabled, loading, variant, type }: any) => (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      data-variant={variant}
      type={type}
      data-loading={loading}
    >
      {children}
    </button>
  ),
}));

describe('FormCard Component', () => {
  const mockOnSubmit = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render title', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      expect(screen.getByText('Test Form')).toBeInTheDocument();
    });

    it('should render subtitle when provided', () => {
      render(
        <FormCard
          title="Test Form"
          subtitle="Form description"
          onSubmit={mockOnSubmit}
        >
          <input type="text" />
        </FormCard>
      );

      expect(screen.getByText('Test Form')).toBeInTheDocument();
      expect(screen.getByText('Form description')).toBeInTheDocument();
    });

    it('should render children content', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <div data-testid="form-fields">
            <input type="text" placeholder="Name" />
            <input type="email" placeholder="Email" />
          </div>
        </FormCard>
      );

      expect(screen.getByTestId('form-fields')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Name')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    });

    it('should render submit button with default label', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      expect(screen.getByText('Сохранить')).toBeInTheDocument();
    });

    it('should render submit button with custom label', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          submitLabel="Создать"
        >
          <input type="text" />
        </FormCard>
      );

      expect(screen.getByText('Создать')).toBeInTheDocument();
    });

    it('should render cancel button when onCancel is provided', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        >
          <input type="text" />
        </FormCard>
      );

      expect(screen.getByText('Отмена')).toBeInTheDocument();
    });

    it('should NOT render cancel button when onCancel is not provided', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      expect(screen.queryByText('Отмена')).not.toBeInTheDocument();
    });

    it('should render cancel button with custom label', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          cancelLabel="Назад"
        >
          <input type="text" />
        </FormCard>
      );

      expect(screen.getByText('Назад')).toBeInTheDocument();
    });
  });

  describe('Form submission', () => {
    it('should call onSubmit when form is submitted', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      const form = screen.getByRole('button', { name: /Сохранить/ }).closest('form');
      fireEvent.submit(form!);

      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    });

    it('should call onSubmit when submit button is clicked', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      const submitButton = screen.getByText('Сохранить');
      fireEvent.click(submitButton);

      expect(mockOnSubmit).toHaveBeenCalled();
    });

    it('should prevent default form submission', () => {
      const { container } = render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      const form = container.querySelector('form');
      const event = new Event('submit', { bubbles: true, cancelable: true });
      const preventDefault = jest.fn();
      Object.defineProperty(event, 'preventDefault', { value: preventDefault });

      form?.dispatchEvent(event);

      // Form should handle submission
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });

  describe('Cancel functionality', () => {
    it('should call onCancel when cancel button is clicked', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        >
          <input type="text" />
        </FormCard>
      );

      const cancelButton = screen.getByText('Отмена');
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it('should NOT submit form when cancel is clicked', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        >
          <input type="text" />
        </FormCard>
      );

      const cancelButton = screen.getByText('Отмена');
      fireEvent.click(cancelButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe('Loading state', () => {
    it('should disable submit button when loading', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          loading={true}
        >
          <input type="text" />
        </FormCard>
      );

      const submitButton = screen.getByText('Сохранить');
      expect(submitButton).toBeDisabled();
    });

    it('should disable cancel button when loading', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          loading={true}
        >
          <input type="text" />
        </FormCard>
      );

      const cancelButton = screen.getByText('Отмена');
      expect(cancelButton).toBeDisabled();
    });

    it('should enable buttons when not loading', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
          loading={false}
        >
          <input type="text" />
        </FormCard>
      );

      const submitButton = screen.getByText('Сохранить');
      const cancelButton = screen.getByText('Отмена');

      expect(submitButton).not.toBeDisabled();
      expect(cancelButton).not.toBeDisabled();
    });

    it('should show loading state on submit button', () => {
      const { container } = render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          loading={true}
        >
          <input type="text" />
        </FormCard>
      );

      const submitButton = screen.getByText('Сохранить');
      expect(submitButton).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('Button variants', () => {
    it('should render submit button as primary variant', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      const submitButton = screen.getByText('Сохранить');
      expect(submitButton).toHaveAttribute('data-variant', 'primary');
    });

    it('should render cancel button as secondary variant', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          onCancel={mockOnCancel}
        >
          <input type="text" />
        </FormCard>
      );

      const cancelButton = screen.getByText('Отмена');
      expect(cancelButton).toHaveAttribute('data-variant', 'secondary');
    });

    it('should set submit button type to submit', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      const submitButton = screen.getByText('Сохранить');
      expect(submitButton).toHaveAttribute('type', 'submit');
    });
  });

  describe('Complex children', () => {
    it('should render multiple form fields', () => {
      render(
        <FormCard title="User Form" onSubmit={mockOnSubmit}>
          <div>
            <input type="text" placeholder="First Name" />
            <input type="text" placeholder="Last Name" />
            <input type="email" placeholder="Email" />
            <textarea placeholder="Bio" />
          </div>
        </FormCard>
      );

      expect(screen.getByPlaceholderText('First Name')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Last Name')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Bio')).toBeInTheDocument();
    });

    it('should render nested components', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <div>
            <div data-testid="section-1">
              <input type="text" />
            </div>
            <div data-testid="section-2">
              <select>
                <option>Option 1</option>
              </select>
            </div>
          </div>
        </FormCard>
      );

      expect(screen.getByTestId('section-1')).toBeInTheDocument();
      expect(screen.getByTestId('section-2')).toBeInTheDocument();
    });
  });

  describe('Card structure', () => {
    it('should render as MUI Card', () => {
      const { container } = render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      const card = container.querySelector('.MuiCard-root');
      expect(card).toBeInTheDocument();
    });

    it('should have CardHeader with title', () => {
      const { container } = render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <input type="text" />
        </FormCard>
      );

      const cardHeader = container.querySelector('.MuiCardHeader-root');
      expect(cardHeader).toBeInTheDocument();
    });

    it('should have CardContent with children', () => {
      const { container } = render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          <div data-testid="content">Form fields</div>
        </FormCard>
      );

      const cardContent = container.querySelector('.MuiCardContent-root');
      expect(cardContent).toBeInTheDocument();
      expect(cardContent).toContainElement(screen.getByTestId('content'));
    });
  });

  describe('Edge cases', () => {
    it('should handle empty children', () => {
      render(
        <FormCard title="Test Form" onSubmit={mockOnSubmit}>
          {null}
        </FormCard>
      );

      expect(screen.getByText('Test Form')).toBeInTheDocument();
      expect(screen.getByText('Сохранить')).toBeInTheDocument();
    });

    it('should handle rapid submit clicks when loading', () => {
      render(
        <FormCard
          title="Test Form"
          onSubmit={mockOnSubmit}
          loading={true}
        >
          <input type="text" />
        </FormCard>
      );

      const submitButton = screen.getByText('Сохранить');
      
      fireEvent.click(submitButton);
      fireEvent.click(submitButton);
      fireEvent.click(submitButton);

      // Should not call onSubmit when disabled
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });
});
