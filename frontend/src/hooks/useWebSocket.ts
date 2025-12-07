// src/hooks/useWebSocket.ts
import { useState, useEffect, useRef } from 'react';

interface WebSocketHook {
  lastMessage: string | null;
  sendMessage: (message: string) => void;
  readyState: number;
}

export const useWebSocket = (url: string): WebSocketHook => {
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CONNECTING);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Create WebSocket connection
    const wsUrl = `${process.env.REACT_APP_API_BASE_URL || ''}${url}`.replace('http', 'ws');
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log(`WebSocket connected to ${url}`);
      setReadyState(WebSocket.OPEN);
    };

    wsRef.current.onmessage = (event) => {
      setLastMessage(event.data);
    };

    wsRef.current.onclose = () => {
      console.log(`WebSocket disconnected from ${url}`);
      setReadyState(WebSocket.CLOSED);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setReadyState(WebSocket.CLOSED);
    };

    // Clean up function
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  const sendMessage = (message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn('WebSocket is not open. Cannot send message.');
    }
  };

  return {
    lastMessage,
    sendMessage,
    readyState,
  };
};