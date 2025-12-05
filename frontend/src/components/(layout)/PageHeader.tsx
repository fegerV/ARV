/**
 * PageHeader - Заголовок страницы с breadcrumbs и действиями
 */

import { Box, Typography } from '@mui/material';
import { Breadcrumbs } from './Breadcrumbs';
import type { PageHeaderProps } from '../../types/components';

export const PageHeader = ({ title, subtitle, actions, breadcrumbs, icon }: PageHeaderProps) => {
  return (
    <Box sx={{ mb: 4 }}>
      {breadcrumbs && breadcrumbs.length > 0 && <Breadcrumbs items={breadcrumbs} />}

      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 2,
          flexWrap: 'wrap',
        }}
      >
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          {icon && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 56,
                height: 56,
                borderRadius: 2,
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
              }}
            >
              {icon}
            </Box>
          )}
          <Box>
            <Typography variant="h4" component="h1" fontWeight={700} gutterBottom={!!subtitle}>
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="body1" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
        </Box>

        {actions && (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {actions}
          </Box>
        )}
      </Box>
    </Box>
  );
};
