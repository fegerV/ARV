/**
 * Общие типы для компонентов Vertex AR Admin Panel
 */

import { ReactNode } from 'react';

// ============= UI Primitives =============
export interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'small' | 'medium' | 'large';
  fullWidth?: boolean;
  type?: 'button' | 'submit' | 'reset';
  startIcon?: ReactNode;
  endIcon?: ReactNode;
}

export interface CardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
  loading?: boolean;
  elevation?: number;
  className?: string;
}

export interface BadgeProps {
  status: 'success' | 'warning' | 'error' | 'info' | 'default';
  label: string;
  size?: 'small' | 'medium';
  icon?: ReactNode;
}

export interface StatusBadgeProps {
  status: 'pending' | 'processing' | 'ready' | 'failed' | 'active' | 'expired';
  size?: 'small' | 'medium';
}

// ============= Layout =============
export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  icon?: ReactNode;
}

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: ReactNode;
}

export interface SidebarNavItem {
  label: string;
  href: string;
  icon: ReactNode;
  badge?: number;
  children?: SidebarNavItem[];
}

// ============= Tables =============
export interface ColumnDef<T> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (row: T) => ReactNode;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export interface FilterDef {
  key: string;
  label: string;
  type: 'text' | 'select' | 'date' | 'dateRange';
  options?: { value: string; label: string }[];
}

export interface TableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  filters?: FilterDef[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
}

// ============= Forms =============
export interface FormCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onSubmit: () => void;
  onCancel?: () => void;
  loading?: boolean;
  submitLabel?: string;
  cancelLabel?: string;
}

export interface FileUploadZoneProps {
  accept?: string;
  maxSize?: number; // MB
  onUpload: (file: File) => void;
  loading?: boolean;
  error?: string;
  preview?: string;
  label?: string;
  helperText?: string;
}

// ============= Analytics =============
export interface KpiCardProps {
  title: string;
  value: string | number;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  icon?: ReactNode;
  loading?: boolean;
}

export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

// ============= Media =============
export interface QRCodeCardProps {
  url: string;
  title?: string;
  size?: number;
  downloadFormats?: ('png' | 'svg' | 'pdf')[];
}

export interface ImagePreviewProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  onClick?: () => void;
  loading?: boolean;
}

export interface VideoPreviewProps {
  src: string;
  thumbnail?: string;
  duration?: number;
  onClick?: () => void;
}

// ============= Feedback =============
export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
  onConfirm: () => void;
  onCancel: () => void;
}

export interface AlertBannerProps {
  type: 'success' | 'warning' | 'error' | 'info';
  message: string;
  onClose?: () => void;
  autoHideDuration?: number;
}

// ============= System =============
export interface HealthStatusProps {
  service: string;
  status: 'healthy' | 'degraded' | 'down';
  lastCheck?: Date;
  message?: string;
}
