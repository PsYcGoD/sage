import { useState, useRef, useCallback, useEffect } from 'react';
import TitleBar from './components/TitleBar';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import MetricCards from './components/MetricCards';
import Settings from './components/Settings';
import TeamView from './components/TeamView';
import type { Session, Message } from './types';

type AppSettings = {
  permission_mode: 'ask' | 'approve' | 'full';
  api_travel: boolean;
};

const DEFAULT_SETTINGS: AppSettings = {
  permission_mode: 'ask',
  api_travel: false,
};

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [showTeam, setShowTeam] = useState(false);
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [connected, setConnected] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const resizing = useRef(false);
  const streamBufferRef = useRef('');

  useEffect(() => {
    function connect() {
      const ws = new WebSocket('ws://localhost:19480');
      ws.onopen = () => {
        setConnected(true);
        ws.send(JSON.stringify({ type: 'session.list', payload: {} }));
        ws.send(JSON.stringify({ type: 'settings.get', payload: {} }));
      };
      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleWSMessage(msg);
        } catch {}
      };
      wsRef.current = ws;
    }
    connect();
    return () => { wsRef.current?.close(); };
  }, []);

  function send(type: string, payload: any = {}) {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }));
    }
  }

  function handleWSMessage(msg: any) {
    const { type, payload } = msg;
    switch (type) {
      case 'session.list.response':
        setSessions(payload.sessions || []);
        break;
      case 'settings.get.response':
      case 'settings.set.response':
        if (payload.settings) {
          setSettings({ ...DEFAULT_SETTINGS, ...payload.settings });
        }
        break;
      case 'session.create.response':
        if (payload.success) {
          send('session.list', {});
          const newSession: Session = {
            id: payload.id,
            title: 'New Chat',
            project: payload.project || '',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            preview: '',
            pinned: false,
            unread: false,
          };
          setActiveSession(newSession);
          setMessages([]);
        }
        break;
      case 'session.messages.response':
        setMessages(payload.messages || []);
        break;
      case 'chat.send.response':
        break;
      case 'chat.stream.thinking':
        streamBufferRef.current = '<thinking>' + (payload.text || '') + '</thinking>\n\n' + (streamBufferRef.current.replace(/^<thinking>.*?<\/thinking>\n\n/s, ''));
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant' && last.id === '__streaming__') {
            return [...prev.slice(0, -1), { ...last, content: streamBufferRef.current }];
          }
          return [...prev, { id: '__streaming__', role: 'assistant', content: streamBufferRef.current, timestamp: new Date().toISOString() }];
        });
        break;
      case 'chat.stream.token':
        // Append text after any existing thinking block
        const thinkMatch = streamBufferRef.current.match(/^(<thinking>.*?<\/thinking>\n\n)/s);
        const prefix = thinkMatch ? thinkMatch[1] : '';
        const existingText = streamBufferRef.current.slice(prefix.length);
        streamBufferRef.current = prefix + existingText + (payload.token || '');
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant' && last.id === '__streaming__') {
            return [...prev.slice(0, -1), { ...last, content: streamBufferRef.current }];
          }
          return [...prev, { id: '__streaming__', role: 'assistant', content: streamBufferRef.current, timestamp: new Date().toISOString() }];
        });
        break;
      case 'chat.stream.done':
        setStreaming(false);
        setMessages(prev => prev.map(m => m.id === '__streaming__' ? { ...m, id: payload.id || Date.now().toString(), provider: payload.provider || 'Claude' } : m));
        streamBufferRef.current = '';
        break;
      case 'chat.stream.error':
        setStreaming(false);
        streamBufferRef.current = '';
        setMessages(prev => [...prev, { id: Date.now().toString(), role: 'assistant', content: `Error: ${payload.message}`, timestamp: new Date().toISOString() }]);
        break;
    }
  }

  async function pickProjectFolder(): Promise<string | undefined> {
    try {
      const folder = await window.electronAPI?.dialog?.pickFolder?.();
      return folder || undefined;
    } catch {
      return undefined;
    }
  }

  async function handleNewChat(folder?: string) {
    const project = folder || await pickProjectFolder();
    if (!project) return;
    setShowTeam(false);
    send('session.create', { project });
  }

  function handleSelectSession(session: Session) {
    setActiveSession(session);
    send('session.messages', { id: session.id });
  }

  function handleSendMessage(content: string) {
    if (!content.trim() || streaming) return;
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: content.trim(), timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setStreaming(true);
    streamBufferRef.current = '';
    send('chat.send', { session_id: activeSession?.id || 'default', content: content.trim() });
  }

  function updateSettings(patch: Partial<AppSettings>) {
    const next = { ...settings, ...patch };
    setSettings(next);
    send('settings.set', patch);
  }

  function handleCancelStream() {
    send('chat.cancel', { session_id: activeSession?.id || '' });
    setStreaming(false);
  }

  const handleMouseDown = useCallback(() => {
    resizing.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizing.current) return;
      setSidebarWidth(Math.max(200, Math.min(500, e.clientX)));
    };
    const handleMouseUp = () => {
      resizing.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#1a1b26] overflow-hidden">
      <TitleBar />
      <div className="flex flex-1 overflow-hidden">
        {!sidebarCollapsed && (
          <div style={{ width: sidebarWidth }} className="flex-shrink-0">
            <Sidebar
              sessions={sessions}
              activeSession={activeSession}
              onSelectSession={handleSelectSession}
              onNewChat={handleNewChat}
              onOpenSettings={() => setShowSettings(true)}
              onOpenTeam={() => setShowTeam(true)}
              onCollapse={() => setSidebarCollapsed(true)}
            />
          </div>
        )}
        <div
          className="w-1.5 cursor-col-resize hover:bg-[#8b5cf6]/30 transition-colors flex-shrink-0"
          onMouseDown={handleMouseDown}
        />
        <div className="flex-1 overflow-hidden">
          {showTeam ? (
            <TeamView wsRef={wsRef} onBack={() => setShowTeam(false)} />
          ) : (
            <ChatPanel
              session={activeSession}
              messages={messages}
              streaming={streaming}
              connected={connected}
              settings={settings}
              onSettingsChange={updateSettings}
              sidebarCollapsed={sidebarCollapsed}
              onExpandSidebar={() => setSidebarCollapsed(false)}
              onSendMessage={handleSendMessage}
              onCancelStream={handleCancelStream}
              onNewChat={handleNewChat}
            />
          )}
        </div>
        <MetricCards connected={connected} wsRef={wsRef} />
      </div>
      {showSettings && (
        <div className="fixed inset-0 z-40 top-9">
          <Settings
            onClose={() => setShowSettings(false)}
            wsRef={wsRef}
            connected={connected}
            externalSettings={settings}
            onExternalChange={updateSettings}
          />
        </div>
      )}
    </div>
  );
}
