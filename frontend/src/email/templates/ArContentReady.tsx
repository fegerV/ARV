// src/email/templates/ArContentReady.tsx
import React from 'react';

interface ArContentReadyProps {
  company_name: string;
  content_title: string;
  content_url: string;
  qr_code_url: string;
}

export const ArContentReadyEmail: React.FC<ArContentReadyProps> = (props) => (
  <div style={{ fontFamily: 'Arial, sans-serif', fontSize: '14px', color: '#333' }}>
    <h2>AR-контент готов к использованию</h2>
    <p>Контент <strong>{props.content_title}</strong> полностью готов.</p>
    <p>Компания: {props.company_name}</p>
    <p><a href={props.content_url}>Просмотреть контент</a></p>
    <p>QR-код: <a href={props.qr_code_url}>Скачать QR-код</a></p>
    <br />
    <p>С уважением,<br />Команда Vertex AR</p>
  </div>
);