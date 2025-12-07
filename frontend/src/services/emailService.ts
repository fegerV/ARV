// src/services/emailService.ts
import { api } from './api';
import { EMAIL_TEMPLATES, EmailTemplateMeta } from '@/email/templates/types';

// Define types based on backend models
export interface EmailNotificationRequest {
  template_id: string;
  recipients: string[];
  data: Record<string, any>;
}

export interface EmailNotificationResponse {
  status: string;
  message: string;
}

export interface EmailTemplateInfo {
  id: string;
  name: string;
  description: string;
  subjectExample: string;
  variables: string[];
}

class EmailService {
  /**
   * Send email notification using a template
   */
  async sendEmail(request: EmailNotificationRequest): Promise<EmailNotificationResponse> {
    const response = await api.post<EmailNotificationResponse>('/notifications/email', request);
    return response.data;
  }

  /**
   * Get list of available email templates
   */
  async getEmailTemplates(): Promise<Record<string, EmailTemplateInfo>> {
    const response = await api.get<Record<string, EmailTemplateInfo>>('/notifications/email/templates');
    return response.data;
  }

  /**
   * Get template metadata by ID
   */
  getTemplateMeta(templateId: string): EmailTemplateInfo | undefined {
    // In a real implementation, this would fetch from backend
    // For now, we use the frontend constants
    const template = EMAIL_TEMPLATES.find(t => t.id === templateId);
    if (!template) return undefined;
    
    return {
      id: template.id,
      name: template.name,
      description: template.description,
      subjectExample: template.subjectExample,
      variables: template.variables,
    };
  }
}

export const emailService = new EmailService();