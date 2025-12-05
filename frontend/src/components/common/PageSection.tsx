import { ReactNode } from 'react';
import { Card, CardContent, CardHeader, Divider } from '@mui/material';

interface PageSectionProps {
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}

export default function PageSection({ title, children, action }: PageSectionProps) {
  return (
    <Card sx={{ mb: 3 }}>
      {title && (
        <>
          <CardHeader 
            title={title} 
            action={action}
            sx={{ pb: 0 }}
          />
          <Divider />
        </>
      )}
      <CardContent>
        {children}
      </CardContent>
    </Card>
  );
}
