// src/email/templates/VideoRotationReminder.tsx
import React from 'react';

interface VideoRotationReminderProps {
  company_name: string;
  content_title: string;
  next_rotation_date: string;
  content_url: string;
}

export const VideoRotationReminderEmail: React.FC<VideoRotationReminderProps> = (props) => (
  <div style={{ fontFamily: 'Arial, sans-serif', fontSize: '14px', color: '#333' }}>
    <h2>Напоминание о ротации видео</h2>
    <p>Контент: <strong>{props.content_title}</strong></p>
    <p>Компания: {props.company_name}</p>
    <p>Следующая ротация запланирована на: {props.next_rotation_date}</p>
    <p><a href={props.content_url}>Просмотреть контент</a></p>
    <br />
    <p>С уважением,<br />Команда Vertex AR</p>
  </div>
);