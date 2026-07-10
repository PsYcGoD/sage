import { useState, useEffect, useRef, useCallback } from 'react';
import type { WSMessage } from '../types';

const WS_URL = 'ws://localhost:19480';

type MessageHandler = (msg: WSMessage) => void;

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, MessageHandler[]>>(new Map());
  const reconnectTimer = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setConnected(true);
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      reconnectTimer.current = window.setTimeout(connect, 2000);
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        const handlers = handlersRef.current.get(msg.type) || [];
        handlers.forEach((h) => h(msg));
        const wildcardHandlers = handlersRef.current.get('*') || [];
        wildcardHandlers.forEach((h) => h(msg));
      } catch {}
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((type: string, payload: any = {}, id?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload, id }));
    }
  }, []);

  const on = useCallback((type: string, handler: MessageHandler) => {
    const existing = handlersRef.current.get(type) || [];
    handlersRef.current.set(type, [...existing, handler]);
    return () => {
      const handlers = handlersRef.current.get(type) || [];
      handlersRef.current.set(type, handlers.filter((h) => h !== handler));
    };
  }, []);

  return { connected, send, on };
}
