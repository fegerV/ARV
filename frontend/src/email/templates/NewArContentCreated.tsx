// src/email/templates/NewArContentCreated.tsx
import React from 'react';

interface NewArContentCreatedProps {
  company_name: string;
  project_name: string;
  content_title: string;
  content_url: string;
}

export const NewArContentCreatedEmail: React.FC<NewArContentCreatedProps> = (props) => (
  <div style={{ fontFamily: 'Arial, sans-serif', fontSize: '14px', color: '#333' }}>
    <h2>Новый AR-контент создан</h2>
    <p>Компания: <strong>{props.company_name}</strong></p>
    <p>Проект: <strong>{props.project_name}</strong></p>
    <p>Контент: <strong>{props.content_title}</strong></p>
    <p><a href={props.content_url}>Просмотреть контент</a></p>
    <br />
    <p>С уважением,<br />Команда Vertex AR</p>
  </div>
);