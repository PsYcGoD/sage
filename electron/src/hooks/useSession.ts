import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import type { Session } from '../types';

export function useSession() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const { connected, send, on } = useWebSocket();

  useEffect(() => {
    if (!connected) return;

    const unsub = on('session.list.response', (msg) => {
      setSessions(msg.payload.sessions || []);
      setLoading(false);
    });

    send('session.list', {});

    const interval = setInterval(() => send('session.list', {}), 5000);

    return () => {
      unsub();
      clearInterval(interval);
    };
  }, [connected, send, on]);

  const createSession = useCallback((project: string) => {
    send('session.create', { project });
  }, [send]);

  const deleteSession = useCallback((id: string) => {
    send('session.delete', { id });
  }, [send]);

  return { sessions, loading, connected, createSession, deleteSession };
}
