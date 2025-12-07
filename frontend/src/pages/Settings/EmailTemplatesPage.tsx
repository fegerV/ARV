// src/pages/Settings/EmailTemplatesPage.tsx
import React, { useState } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Divider,
  Box,
  Chip,
} from '@mui/material';
import { EMAIL_TEMPLATES, EmailTemplateId, EmailTemplateMeta } from '@/email/templates/types';
import { NewCompanyCreatedEmail } from '@/email/templates/NewCompanyCreated';
import { NewArContentCreatedEmail } from '@/email/templates/NewArContentCreated';
import { ArContentReadyEmail } from '@/email/templates/ArContentReady';
import { MarkerGenerationCompleteEmail } from '@/email/templates/MarkerGenerationComplete';
import { VideoRotationReminderEmail } from '@/email/templates/VideoRotationReminder';

const EmailTemplatesPage: React.FC = () => {
  const [selected, setSelected] = useState<EmailTemplateId>('NEW_COMPANY_CREATED');

  const selectedTemplate = EMAIL_TEMPLATES.find(t => t.id === selected);

  const renderPreview = () => {
    switch (selected) {
      case 'NEW_COMPANY_CREATED':
        return (
          <NewCompanyCreatedEmail
            company_name="Vertex AR"
            admin_name="Администратор"
            dashboard_url="https://admin.vertexar.com/dashboard"
          />
        );
      case 'NEW_AR_CONTENT_CREATED':
        return (
          <NewArContentCreatedEmail
            company_name="Креативное агентство"
            project_name="Демо проект"
            content_title="Бариста с кофе"
            content_url="https://admin.vertexar.com/content/123"
          />
        );
      case 'AR_CONTENT_READY':
        return (
          <ArContentReadyEmail
            company_name="Креативное агентство"
            content_title="Бариста с кофе"
            content_url="https://admin.vertexar.com/content/123"
            qr_code_url="https://admin.vertexar.com/content/123/qr"
          />
        );
      case 'MARKER_GENERATION_COMPLETE':
        return (
          <MarkerGenerationCompleteEmail
            company_name="Креативное агентство"
            content_title="Бариста с кофе"
            marker_url="https://storage.vertexar.com/markers/123.mind"
            content_url="https://admin.vertexar.com/content/123"
          />
        );
      case 'VIDEO_ROTATION_REMINDER':
        return (
          <VideoRotationReminderEmail
            company_name="Креативное агентство"
            content_title="Бариста с кофе"
            next_rotation_date="2023-12-01 00:00"
            content_url="https://admin.vertexar.com/content/123"
          />
        );
      default:
        return <Typography>Шаблон не найден</Typography>;
    }
  };

  return (
    <Container maxWidth={false}>
      <Typography variant="h4" gutterBottom>
        Шаблоны Email-уведомлений
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Доступные шаблоны
            </Typography>
            <List>
              {EMAIL_TEMPLATES.map((template) => (
                <React.Fragment key={template.id}>
                  <ListItem disablePadding>
                    <ListItemButton 
                      selected={selected === template.id}
                      onClick={() => setSelected(template.id)}
                    >
                      <ListItemText 
                        primary={template.name}
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="body2" color="text.secondary">
                              {template.description}
                            </Typography>
                            <Chip 
                              label={template.id} 
                              size="small" 
                              sx={{ mt: 1, fontSize: '0.7rem' }} 
                            />
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                  <Divider />
                </React.Fragment>
              ))}
            </List>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            {selectedTemplate && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="h5" gutterBottom>
                  {selectedTemplate.name}
                </Typography>
                <Typography variant="body1" color="text.secondary" paragraph>
                  {selectedTemplate.description}
                </Typography>
                <Typography variant="subtitle2" sx={{ mt: 2 }}>
                  Пример темы:
                </Typography>
                <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                  {selectedTemplate.subjectExample}
                </Typography>
                <Typography variant="subtitle2" sx={{ mt: 2 }}>
                  Переменные:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                  {selectedTemplate.variables.map((variable) => (
                    <Chip 
                      key={variable} 
                      label={`{{${variable}}}`} 
                      size="small" 
                      variant="outlined" 
                    />
                  ))}
                </Box>
              </Box>
            )}
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              Предварительный просмотр
            </Typography>
            <Box 
              sx={{ 
                border: '1px solid #eee', 
                borderRadius: 1, 
                p: 2, 
                bgcolor: '#fafafa',
                minHeight: 300
              }}
            >
              {renderPreview()}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default EmailTemplatesPage;