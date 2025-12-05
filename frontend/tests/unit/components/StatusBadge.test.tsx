/**
 * Tests for StatusBadge component
 * Проверяет отображение статус-бейджей для AR контента
 */

import { render, screen } from '@testing-library/react';
import { StatusBadge } from '@/components/(ui)/Badge/StatusBadge';

describe('StatusBadge', () => {
  describe('Status variants', () => {
    it('should render pending status with correct label', () => {
      render(<StatusBadge status="pending" />);
      
      expect(screen.getByText('В очереди')).toBeInTheDocument();
    });

    it('should render processing status with correct label', () => {
      render(<StatusBadge status="processing" />);
      
      expect(screen.getByText('Обработка')).toBeInTheDocument();
    });

    it('should render ready status with correct label', () => {
      render(<StatusBadge status="ready" />);
      
      expect(screen.getByText('Готово')).toBeInTheDocument();
    });

    it('should render failed status with correct label', () => {
      render(<StatusBadge status="failed" />);
      
      expect(screen.getByText('Ошибка')).toBeInTheDocument();
    });

    it('should render active status with correct label', () => {
      render(<StatusBadge status="active" />);
      
      expect(screen.getByText('Активно')).toBeInTheDocument();
    });

    it('should render expired status with correct label', () => {
      render(<StatusBadge status="expired" />);
      
      expect(screen.getByText('Истекло')).toBeInTheDocument();
    });
  });

  describe('Size variants', () => {
    it('should render medium size by default', () => {
      const { container } = render(<StatusBadge status="ready" />);
      const chip = container.querySelector('.MuiChip-sizeMedium');
      
      expect(chip).toBeInTheDocument();
    });

    it('should render small size when specified', () => {
      const { container } = render(<StatusBadge status="ready" size="small" />);
      const chip = container.querySelector('.MuiChip-sizeSmall');
      
      expect(chip).toBeInTheDocument();
    });
  });

  describe('Icons', () => {
    it('should render icon for pending status', () => {
      const { container } = render(<StatusBadge status="pending" />);
      const icon = container.querySelector('.MuiChip-icon');
      
      expect(icon).toBeInTheDocument();
    });

    it('should render icon for processing status', () => {
      const { container } = render(<StatusBadge status="processing" />);
      const icon = container.querySelector('.MuiChip-icon');
      
      expect(icon).toBeInTheDocument();
    });

    it('should render icon for ready status', () => {
      const { container } = render(<StatusBadge status="ready" />);
      const icon = container.querySelector('.MuiChip-icon');
      
      expect(icon).toBeInTheDocument();
    });

    it('should render icon for failed status', () => {
      const { container } = render(<StatusBadge status="failed" />);
      const icon = container.querySelector('.MuiChip-icon');
      
      expect(icon).toBeInTheDocument();
    });

    it('should render icon for active status', () => {
      const { container } = render(<StatusBadge status="active" />);
      const icon = container.querySelector('.MuiChip-icon');
      
      expect(icon).toBeInTheDocument();
    });

    it('should render icon for expired status', () => {
      const { container } = render(<StatusBadge status="expired" />);
      const icon = container.querySelector('.MuiChip-icon');
      
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Color mapping', () => {
    it('should have default color for pending status', () => {
      const { container } = render(<StatusBadge status="pending" />);
      const chip = container.querySelector('.MuiChip-colorDefault');
      
      expect(chip).toBeInTheDocument();
    });

    it('should have info color for processing status', () => {
      const { container } = render(<StatusBadge status="processing" />);
      const chip = container.querySelector('.MuiChip-colorInfo');
      
      expect(chip).toBeInTheDocument();
    });

    it('should have success color for ready status', () => {
      const { container } = render(<StatusBadge status="ready" />);
      const chip = container.querySelector('.MuiChip-colorSuccess');
      
      expect(chip).toBeInTheDocument();
    });

    it('should have error color for failed status', () => {
      const { container } = render(<StatusBadge status="failed" />);
      const chip = container.querySelector('.MuiChip-colorError');
      
      expect(chip).toBeInTheDocument();
    });

    it('should have success color for active status', () => {
      const { container } = render(<StatusBadge status="active" />);
      const chip = container.querySelector('.MuiChip-colorSuccess');
      
      expect(chip).toBeInTheDocument();
    });

    it('should have warning color for expired status', () => {
      const { container } = render(<StatusBadge status="expired" />);
      const chip = container.querySelector('.MuiChip-colorWarning');
      
      expect(chip).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should render as accessible element', () => {
      const { container } = render(<StatusBadge status="ready" />);
      const chip = container.querySelector('.MuiChip-root');
      
      expect(chip).toBeInTheDocument();
      expect(chip).toHaveClass('MuiChip-root');
    });

    it('should have proper font weight', () => {
      const { container } = render(<StatusBadge status="ready" />);
      const chip = container.querySelector('.MuiChip-root');
      
      expect(chip).toHaveStyle({ fontWeight: 500 });
    });
  });

  describe('Snapshots', () => {
    it('should match snapshot for all statuses', () => {
      const statuses = ['pending', 'processing', 'ready', 'failed', 'active', 'expired'] as const;
      
      statuses.forEach(status => {
        const { container } = render(<StatusBadge status={status} />);
        expect(container.firstChild).toMatchSnapshot(`status-${status}`);
      });
    });
  });
});
