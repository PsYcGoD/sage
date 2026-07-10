import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import type { Message } from '../types';

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState('');
  const { connected, send, on } = useWebSocket();
  const cancelRef = useRef(false);

  useEffect(() => {
    if (!connected || !sessionId) return;

    send('session.messages', { id: sessionId });

    const unsubMessages = on('session.messages.response', (msg) => {
      setMessages(msg.payload.messages || []);
    });

    const unsubToken = on('chat.stream.token', (msg) => {
      setStreamBuffer((prev) => prev + (msg.payload.token || ''));
    });

    const unsubThinking = on('chat.stream.thinking', (msg) => {
      setStreamBuffer((prev) => prev + `\n<thinking>${msg.payload.text}</thinking>\n`);
    });

    const unsubDone = on('chat.stream.done', (msg) => {
      setStreaming(false);
      const assistantMsg: Message = {
        id: msg.payload.id || Date.now().toString(),
        role: 'assistant',
        content: streamBuffer + (msg.payload.final || ''),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setStreamBuffer('');
    });

    const unsubError = on('chat.stream.error', (msg) => {
      setStreaming(false);
      setStreamBuffer('');
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Error: ${msg.payload.message || 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    });

    return () => {
      unsubMessages();
      unsubToken();
      unsubThinking();
      unsubDone();
      unsubError();
    };
  }, [connected, sessionId, send, on, streamBuffer]);

  const sendMessage = useCallback((content: string) => {
    if (!sessionId || !content.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setStreamBuffer('');
    cancelRef.current = false;

    send('chat.send', { session_id: sessionId, content: content.trim() });
  }, [sessionId, send]);

  const cancelStream = useCallback(() => {
    cancelRef.current = true;
    setStreaming(false);
    send('chat.cancel', { session_id: sessionId });
  }, [sessionId, send]);

  return { messages, streaming, streamBuffer, sendMessage, cancelStream };
}
