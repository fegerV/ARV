// src/email/templates/types.ts
export type EmailTemplateId =
  | 'NEW_COMPANY_CREATED'
  | 'NEW_AR_CONTENT_CREATED'
  | 'AR_CONTENT_READY'
  | 'MARKER_GENERATION_COMPLETE'
  | 'VIDEO_ROTATION_REMINDER';

export interface EmailTemplateMeta {
  id: EmailTemplateId;
  name: string;
  description: string;
  subjectExample: string;
  variables: string[];
}

export const EMAIL_TEMPLATES: EmailTemplateMeta[] = [
  {
    id: 'NEW_COMPANY_CREATED',
    name: 'Новая компания создана',
    description: 'Отправляется при создании новой компании',
    subjectExample: 'Новая компания {{company_name}} создана',
    variables: ['company_name', 'admin_name', 'dashboard_url'],
  },
  {
    id: 'NEW_AR_CONTENT_CREATED',
    name: 'Новый AR-контент создан',
    description: 'Отправляется при создании нового AR-контента',
    subjectExample: 'Новый AR-контент: {{content_title}}',
    variables: ['company_name', 'project_name', 'content_title', 'content_url'],
  },
  {
    id: 'AR_CONTENT_READY',
    name: 'AR-контент готов',
    description: 'Отправляется когда AR-контент полностью готов к использованию',
    subjectExample: 'AR-контент {{content_title}} готов',
    variables: ['company_name', 'content_title', 'content_url', 'qr_code_url'],
  },
  {
    id: 'MARKER_GENERATION_COMPLETE',
    name: 'Генерация маркера завершена',
    description: 'Отправляется когда генерация NFT маркера завершена',
    subjectExample: 'Маркер для {{content_title}} готов',
    variables: ['company_name', 'content_title', 'marker_url', 'content_url'],
  },
  {
    id: 'VIDEO_ROTATION_REMINDER',
    name: 'Напоминание о ротации видео',
    description: 'Отправляется перед автоматической ротацией видео',
    subjectExample: 'Напоминание: ротация видео для {{content_title}}',
    variables: ['company_name', 'content_title', 'next_rotation_date', 'content_url'],
  },
];