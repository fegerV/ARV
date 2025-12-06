// components/(forms)/YandexOAuthButton.tsx
import React from 'react';
import { Button, Typography } from '@mui/material';
import { Login as LoginIcon } from '@mui/icons-material';

interface YandexOAuthButtonProps {
  connectionName: string;
  onSuccess: (connectionId: number, folderPath: string) => void;
  disabled?: boolean;
}

export const YandexOAuthButton: React.FC<YandexOAuthButtonProps> = ({
  connectionName,
  onSuccess,
  disabled
}) => {
  const handleOAuth = () => {
    // Открываем popup с OAuth
    const width = 600;
    const height = 700;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;
    
    const oauthWindow = window.open(
      `/api/oauth/yandex/authorize?connection_name=${encodeURIComponent(connectionName)}`,
      'yandex-oauth',
      `width=${width},height=${height},left=${left},top=${top},resizable=no,scrollbars=no`
    );
    
    // Обработка callback через postMessage
    const checkClosed = setInterval(() => {
      if (oauthWindow?.closed) {
        clearInterval(checkClosed);
        // Получаем результат из localStorage или URL
        const result = localStorage.getItem('yandex-oauth-result');
        if (result) {
          const data = JSON.parse(result);
          localStorage.removeItem('yandex-oauth-result');
          onSuccess(data.connection_id, data.selected_folder);
        }
      }
    }, 1000);
  };

  return (
    <Button
      fullWidth
      variant="outlined"
      startIcon={<LoginIcon />}
      onClick={handleOAuth}
      disabled={disabled}
      sx={{ py: 2 }}
    >
      Подключить Яндекс.Диск
    </Button>
  );
};