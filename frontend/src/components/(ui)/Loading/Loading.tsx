/**
 * Loading Components - Индикаторы загрузки
 */

import { Box, CircularProgress, Skeleton, Stack } from '@mui/material';

export const PageSpinner = () => (
  <Box
    sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '400px',
    }}
  >
    <CircularProgress size={48} />
  </Box>
);

export const ListSkeleton = ({ count = 5 }: { count?: number }) => (
  <Stack spacing={2}>
    {Array.from({ length: count }).map((_, i) => (
      <Skeleton key={i} variant="rectangular" height={80} />
    ))}
  </Stack>
);

export const ButtonSpinner = () => <CircularProgress size={20} />;
