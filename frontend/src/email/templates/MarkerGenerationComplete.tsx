// src/email/templates/MarkerGenerationComplete.tsx
import React from 'react';

interface MarkerGenerationCompleteProps {
  company_name: string;
  content_title: string;
  marker_url: string;
  content_url: string;
}

export const MarkerGenerationCompleteEmail: React.FC<MarkerGenerationCompleteProps> = (props) => (
  <div style={{ fontFamily: 'Arial, sans-serif', fontSize: '14px', color: '#333' }}>
    <h2>Генерация NFT маркера завершена</h2>
    <p>NFT маркер для контента <strong>{props.content_title}</strong> успешно сгенерирован.</p>
    <p>Компания: {props.company_name}</p>
    <p><a href={props.marker_url}>Скачать маркер</a></p>
    <p><a href={props.content_url}>Просмотреть контент</a></p>
    <br />
    <p>С уважением,<br />Команда Vertex AR</p>
  </div>
);