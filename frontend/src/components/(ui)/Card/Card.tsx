/**
 * Card Component - Карточка с заголовком и действиями
 */

import {
  Card as MuiCard,
  CardHeader,
  CardContent as MuiCardContent,
  CardActions as MuiCardActions,
  Skeleton,
} from '@mui/material';
import type { CardProps } from '../../../types/components';

export const Card = ({
  title,
  subtitle,
  children,
  actions,
  loading = false,
  elevation = 1,
  className,
}: CardProps) => {
  return (
    <MuiCard elevation={elevation} className={className}>
      {(title || subtitle) && (
        <CardHeader
          title={loading ? <Skeleton width="60%" /> : title}
          subheader={loading ? <Skeleton width="40%" /> : subtitle}
        />
      )}
      <MuiCardContent>{loading ? <Skeleton variant="rectangular" height={100} /> : children}</MuiCardContent>
      {actions && <MuiCardActions>{actions}</MuiCardActions>}
    </MuiCard>
  );
};

export const CardContent = MuiCardContent;
export const CardActions = MuiCardActions;
