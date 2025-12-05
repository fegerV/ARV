/**
 * FormCard - Карточка с формой и кнопками действий
 */

import { ReactNode } from 'react';
import { Card, CardContent, CardHeader, Box } from '@mui/material';
import { Save, X } from 'lucide-react';
import { Button } from '../(ui)';

interface FormCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onSubmit: (e: React.FormEvent) => void;
  onCancel?: () => void;
  loading?: boolean;
  submitLabel?: string;
  cancelLabel?: string;
}

export const FormCard = ({
  title,
  subtitle,
  children,
  onSubmit,
  onCancel,
  loading = false,
  submitLabel = 'Сохранить',
  cancelLabel = 'Отмена',
}: FormCardProps) => {
  return (
    <Card>
      <CardHeader title={title} subheader={subtitle} />
      <form onSubmit={onSubmit}>
        <CardContent>{children}</CardContent>
        <Box sx={{ p: 2, pt: 0, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
          {onCancel && (
            <Button
              variant="secondary"
              startIcon={<X size={20} />}
              onClick={onCancel}
              disabled={loading}
            >
              {cancelLabel}
            </Button>
          )}
          <Button
            type="submit"
            variant="primary"
            startIcon={<Save size={20} />}
            loading={loading}
            disabled={loading}
          >
            {submitLabel}
          </Button>
        </Box>
      </form>
    </Card>
  );
};
