import React, { useEffect, useRef, useState } from 'react';
import { Button, Dialog, DialogContent, CircularProgress } from '@mui/material';

interface YandexDiskAuthProps {
  onSuccess: (connectionId: number) => void;
  connectionName: string;
}

export const YandexDiskAuth: React.FC<YandexDiskAuthProps> = ({ onSuccess, connectionName }) => {
  const [authLoading, setAuthLoading] = useState(false);
  const popupRef = useRef<Window | null>(null);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const data = event.data as any;
      if (data && data.type === 'YANDEX_OAUTH_SUCCESS' && data.connectionId) {
        setAuthLoading(false);
        popupRef.current?.close();
        popupRef.current = null;
        onSuccess(Number(data.connectionId));
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onSuccess]);

  const handleAuthorize = () => {
    setAuthLoading(true);

    const width = 600;
    const height = 700;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;

    const authUrl = `/api/oauth/yandex/authorize?connection_name=${encodeURIComponent(
      connectionName || 'Yandex Disk Connection'
    )}`;

    popupRef.current = window.open(
      authUrl,
      'YandexDiskAuth',
      `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no`
    );

    const checkInterval = setInterval(() => {
      const popup = popupRef.current;
      if (popup && popup.closed) {
        clearInterval(checkInterval);
        setAuthLoading(false);
        popupRef.current = null;
      }
    }, 500);
  };

  return (
    <>
      <Button
        variant="contained"
        color="primary"
        onClick={handleAuthorize}
        disabled={authLoading}
        startIcon={authLoading ? <CircularProgress size={20} /> : null}
      >
        {authLoading ? 'Авторизация...' : 'Подключить Яндекс Диск'}
      </Button>

      {authLoading && (
        <Dialog open={authLoading}>
          <DialogContent>
            <p>Пожалуйста, разрешите доступ к Яндекс Диску в открывшемся окне</p>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};
