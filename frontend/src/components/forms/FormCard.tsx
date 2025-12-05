import { ReactNode } from 'react';
import { Card, CardContent, CardHeader, Box, Button, CircularProgress } from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';

interface FormCardProps {
  title: string;
  children: ReactNode;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  loading?: boolean;
  submitLabel?: string;
  cancelLabel?: string;
}

export default function FormCard({ 
  title, 
  children, 
  onSubmit, 
  onCancel, 
  loading = false,
  submitLabel = 'Сохранить',
  cancelLabel = 'Отмена'
}: FormCardProps) {
  return (
    <Card>
      <CardHeader title={title} />
      <form onSubmit={onSubmit}>
        <CardContent>
          {children}
        </CardContent>
        <Box sx={{ p: 2, pt: 0, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
          <Button
            variant="outlined"
            startIcon={<CancelIcon />}
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
          <Button
            type="submit"
            variant="contained"
            startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
            disabled={loading}
          >
            {submitLabel}
          </Button>
        </Box>
      </form>
    </Card>
  );
}
