/**
 * Breadcrumbs - Хлебные крошки для навигации
 */

import { Breadcrumbs as MuiBreadcrumbs, Link, Typography } from '@mui/material';
import { NavigateNext, Home } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import type { BreadcrumbItem } from '../../types/components';

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export const Breadcrumbs = ({ items }: BreadcrumbsProps) => {
  return (
    <MuiBreadcrumbs
      separator={<NavigateNext fontSize="small" />}
      aria-label="breadcrumb"
      sx={{ mb: 2 }}
    >
      <Link
        component={RouterLink}
        to="/"
        underline="hover"
        color="inherit"
        sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
      >
        <Home fontSize="small" />
        Dashboard
      </Link>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return isLast ? (
          <Typography key={index} color="text.primary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {item.icon}
            {item.label}
          </Typography>
        ) : (
          <Link
            key={index}
            component={RouterLink}
            to={item.href || '#'}
            underline="hover"
            color="inherit"
            sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
          >
            {item.icon}
            {item.label}
          </Link>
        );
      })}
    </MuiBreadcrumbs>
  );
};
