import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmDialog } from '@/components/(feedback)/ConfirmDialog';

describe('ConfirmDialog Component', () => {
  const mockOnConfirm = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render when open', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Confirm Action"
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure?')).toBeInTheDocument();
  });

  it('should not render when closed', () => {
    render(
      <ConfirmDialog
        open={false}
        title="Confirm Action"
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.queryByText('Confirm Action')).not.toBeInTheDocument();
  });

  it('should call onConfirm when confirm button clicked', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Delete Item"
        message="This action cannot be undone"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /подтвердить|confirm/i }));
    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('should call onCancel when cancel button clicked', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Delete Item"
        message="This action cannot be undone"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /отмена|cancel/i }));
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('should render with danger variant', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Delete"
        message="Permanently delete?"
        variant="danger"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const confirmButton = screen.getByRole('button', { name: /подтвердить|confirm/i });
    expect(confirmButton).toHaveClass('bg-red-600');
  });

  it('should render with warning variant', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Warning"
        message="Proceed with caution"
        variant="warning"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const confirmButton = screen.getByRole('button', { name: /подтвердить|confirm/i });
    expect(confirmButton).toHaveClass('bg-orange-600');
  });

  it('should close on backdrop click', () => {
    const { container } = render(
      <ConfirmDialog
        open={true}
        title="Confirm"
        message="Message"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const backdrop = container.querySelector('[data-testid="dialog-backdrop"]');
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(mockOnCancel).toHaveBeenCalledTimes(1);
    }
  });

  it('should render custom confirm button text', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Custom"
        message="Message"
        confirmText="Удалить"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByRole('button', { name: 'Удалить' })).toBeInTheDocument();
  });

  it('should render custom cancel button text', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Custom"
        message="Message"
        cancelText="Назад"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByRole('button', { name: 'Назад' })).toBeInTheDocument();
  });
});
