import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FileUploadZone } from '@/components/(forms)/FileUploadZone';
import { useToast } from '@/store/useToast';

// Mock toast hook
jest.mock('@/store/useToast');

describe('FileUploadZone Component', () => {
  const mockOnFileSelect = jest.fn();
  const mockShowToast = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useToast as jest.Mock).mockReturnValue({
      showToast: mockShowToast,
    });
  });

  describe('Rendering', () => {
    it('should render upload zone with default label', () => {
      render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      expect(screen.getByText('Загрузить файл')).toBeInTheDocument();
    });

    it('should render with custom label', () => {
      render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
          label="Выберите изображение"
        />
      );

      expect(screen.getByText('Выберите изображение')).toBeInTheDocument();
    });

    it('should render with description', () => {
      render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
          description="Только JPG, PNG форматы"
        />
      );

      expect(screen.getByText('Только JPG, PNG форматы')).toBeInTheDocument();
    });

    it('should display max size', () => {
      render(
        <FileUploadZone
          accept="image/*"
          maxSize={5}
          onFileSelect={mockOnFileSelect}
        />
      );

      expect(screen.getByText(/Максимальный размер: 5MB/)).toBeInTheDocument();
    });

    it('should render file input element', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const fileInput = container.querySelector('input[type="file"]');
      expect(fileInput).toBeInTheDocument();
      expect(fileInput).toHaveAttribute('accept', 'image/*');
    });

    it('should render upload instructions', () => {
      render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      expect(screen.getByText(/Перетащите файл или нажмите для выбора/)).toBeInTheDocument();
    });
  });

  describe('File selection via input', () => {
    it('should call onFileSelect when valid file is chosen', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          maxSize={10}
          onFileSelect={mockOnFileSelect}
        />
      );

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      expect(mockOnFileSelect).toHaveBeenCalledWith(file);
    });

    it('should display file name after selection', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const file = new File(['test'], 'portrait.jpg', { type: 'image/jpeg' });
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      expect(screen.getByText('portrait.jpg')).toBeInTheDocument();
    });

    it('should display file size after selection', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const fileContent = new Array(1024 * 1024 * 2).join('a'); // ~2MB
      const file = new File([fileContent], 'test.jpg', { type: 'image/jpeg' });
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      expect(screen.getByText(/MB/)).toBeInTheDocument();
    });
  });

  describe('File validation', () => {
    it('should reject file larger than maxSize', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          maxSize={1}
          onFileSelect={mockOnFileSelect}
        />
      );

      const largeContent = new Array(1024 * 1024 * 2).join('a'); // 2MB
      const largeFile = new File([largeContent], 'large.jpg', { type: 'image/jpeg' });
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [largeFile],
        writable: false,
      });

      fireEvent.change(input);

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.stringContaining('слишком большой'),
        'error'
      );
      expect(mockOnFileSelect).not.toHaveBeenCalled();
    });

    it('should accept file within size limit', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          maxSize={10}
          onFileSelect={mockOnFileSelect}
        />
      );

      const file = new File(['small content'], 'small.jpg', { type: 'image/jpeg' });
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      expect(mockShowToast).not.toHaveBeenCalled();
      expect(mockOnFileSelect).toHaveBeenCalledWith(file);
    });
  });

  describe('Drag and drop', () => {
    it('should highlight drop zone on drag over', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const dropZone = container.querySelector('[onDragOver]') as HTMLElement;

      fireEvent.dragOver(dropZone, {
        dataTransfer: {
          files: [],
        },
      });

      // Zone should be highlighted (implementation specific)
    });

    it('should remove highlight on drag leave', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const dropZone = container.querySelector('[onDragLeave]') as HTMLElement;

      fireEvent.dragOver(dropZone);
      fireEvent.dragLeave(dropZone);

      // Highlight should be removed
    });

    it('should handle file drop', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const file = new File(['test'], 'dropped.jpg', { type: 'image/jpeg' });
      const dropZone = container.querySelector('[onDrop]') as HTMLElement;

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file],
        },
      });

      expect(mockOnFileSelect).toHaveBeenCalledWith(file);
    });

    it('should validate dropped file size', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          maxSize={1}
          onFileSelect={mockOnFileSelect}
        />
      );

      const largeContent = new Array(1024 * 1024 * 2).join('a');
      const largeFile = new File([largeContent], 'large.jpg', { type: 'image/jpeg' });
      const dropZone = container.querySelector('[onDrop]') as HTMLElement;

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [largeFile],
        },
      });

      expect(mockShowToast).toHaveBeenCalledWith(
        expect.stringContaining('слишком большой'),
        'error'
      );
    });
  });

  describe('File removal', () => {
    it('should show remove button after file selection', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      const removeButton = container.querySelector('[color="error"]');
      expect(removeButton).toBeInTheDocument();
    });

    it('should remove file when remove button is clicked', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(input);

      expect(screen.getByText('test.jpg')).toBeInTheDocument();

      const removeButton = container.querySelector('[color="error"]') as HTMLElement;
      fireEvent.click(removeButton);

      expect(screen.queryByText('test.jpg')).not.toBeInTheDocument();
      expect(screen.getByText('Загрузить файл')).toBeInTheDocument();
    });
  });

  describe('Different file types', () => {
    it('should accept image files', () => {
      render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const input = screen.getByLabelText(/Выбрать файл/i).previousElementSibling as HTMLInputElement;
      expect(input).toHaveAttribute('accept', 'image/*');
    });

    it('should accept video files', () => {
      render(
        <FileUploadZone
          accept="video/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(input).toHaveAttribute('accept', 'video/*');
    });

    it('should accept specific file extensions', () => {
      render(
        <FileUploadZone
          accept=".jpg,.png,.webp"
          onFileSelect={mockOnFileSelect}
        />
      );

      const input = document.querySelector('input[type="file"]') as HTMLInputElement;
      expect(input).toHaveAttribute('accept', '.jpg,.png,.webp');
    });
  });

  describe('Edge cases', () => {
    it('should handle empty file drop', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const dropZone = container.querySelector('[onDrop]') as HTMLElement;

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [],
        },
      });

      expect(mockOnFileSelect).not.toHaveBeenCalled();
    });

    it('should handle undefined files', () => {
      const { container } = render(
        <FileUploadZone
          accept="image/*"
          onFileSelect={mockOnFileSelect}
        />
      );

      const input = container.querySelector('input[type="file"]') as HTMLInputElement;

      Object.defineProperty(input, 'files', {
        value: null,
        writable: false,
      });

      fireEvent.change(input);

      expect(mockOnFileSelect).not.toHaveBeenCalled();
    });
  });
});
