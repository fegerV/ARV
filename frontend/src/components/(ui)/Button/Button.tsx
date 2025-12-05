/**
 * Button Component - Базовая кнопка с вариантами стилей
 */

import { forwardRef } from 'react';
import { Button as MuiButton, CircularProgress } from '@mui/material';
import type { ButtonProps } from '../../../types/components';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      onClick,
      disabled = false,
      loading = false,
      variant = 'primary',
      size = 'medium',
      fullWidth = false,
      type = 'button',
      startIcon,
      endIcon,
    },
    ref
  ) => {
    const variantMap = {
      primary: 'contained',
      secondary: 'outlined',
      danger: 'contained',
      ghost: 'text',
    } as const;

    const colorMap = {
      primary: 'primary',
      secondary: 'primary',
      danger: 'error',
      ghost: 'inherit',
    } as const;

    return (
      <MuiButton
        ref={ref}
        variant={variantMap[variant]}
        color={colorMap[variant]}
        size={size}
        fullWidth={fullWidth}
        type={type}
        disabled={disabled || loading}
        onClick={onClick}
        startIcon={loading ? <CircularProgress size={16} /> : startIcon}
        endIcon={endIcon}
        sx={{
          textTransform: 'none',
          fontWeight: 500,
        }}
      >
        {children}
      </MuiButton>
    );
  }
);

Button.displayName = 'Button';
