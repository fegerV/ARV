// src/email/templates/NewCompanyCreated.tsx
import React from 'react';

interface NewCompanyCreatedProps {
  company_name: string;
  admin_name: string;
  dashboard_url: string;
}

export const NewCompanyCreatedEmail: React.FC<NewCompanyCreatedProps> = (props) => (
  <div style={{ fontFamily: 'Arial, sans-serif', fontSize: '14px', color: '#333' }}>
    <h2>Новая компания создана</h2>
    <p>Здравствуйте, {props.admin_name}!</p>
    <p>Компания <strong>{props.company_name}</strong> была успешно создана.</p>
    <p>Вы можете управлять компанией в <a href={props.dashboard_url}>панели управления</a>.</p>
    <br />
    <p>С уважением,<br />Команда Vertex AR</p>
  </div>
);