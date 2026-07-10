import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import AgentStrip from './AgentStrip';
import type { Session, Message } from '../types';

interface ChatPanelProps {
  session: Session | null;
  messages: Message[];
  streaming: boolean;
  connected: boolean;
  sidebarCollapsed: boolean;
  onExpandSidebar: () => void;
  onSendMessage: (content: string) => void;
  onCancelStream: () => void;
  onNewChat: () => void;
}

export default function ChatPanel({ session, messages, streaming, connected, sidebarCollapsed, onExpandSidebar, onSendMessage, onCancelStream, onNewChat }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [streamStartTime, setStreamStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  // Timer for streaming
  useEffect(() => {
    if (streaming && !streamStartTime) setStreamStartTime(Date.now());
    if (!streaming) { setStreamStartTime(null); setElapsed(0); }
  }, [streaming]);

  useEffect(() => {
    if (!streamStartTime) return;
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - streamStartTime) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [streamStartTime]);

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !streaming) {
        setHistory(prev => [input, ...prev]);
        setHistoryIdx(-1);
        onSendMessage(input);
        setInput('');
      } else if (input.trim() && streaming) {
        // Steer: send while running
        onSendMessage(input);
        setInput('');
      }
    }
    if (e.key === 'ArrowUp' && !input) {
      e.preventDefault();
      const nextIdx = Math.min(historyIdx + 1, history.length - 1);
      if (history[nextIdx]) { setHistoryIdx(nextIdx); setInput(history[nextIdx]); }
    }
    if (e.key === 'ArrowDown' && historyIdx >= 0) {
      e.preventDefault();
      const nextIdx = historyIdx - 1;
      if (nextIdx < 0) { setHistoryIdx(-1); setInput(''); }
      else { setHistoryIdx(nextIdx); setInput(history[nextIdx]); }
    }
  }

  const fmtTime = (s: number) => s >= 60 ? `${Math.floor(s/60)}m ${s%60}s` : `${s}s`;

  const expandBtn = sidebarCollapsed && (
    <button onClick={onExpandSidebar} className="absolute top-2 left-2 p-2 rounded hover:bg-[#24283b] text-[#9ca3af] hover:text-white transition-colors z-10">
      <svg width="14" height="14" viewBox="0 0 14 14"><path d="M5 3l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
    </button>
  );

  if (!session) {
    return (
      <div className="h-full flex flex-col bg-[#1a1b26]">
        <AgentStrip connected={connected} streaming={false} />
        {expandBtn}
        <div className="flex-1 flex flex-col items-center justify-center">
          <pre className="text-[#8b5cf6]/60 text-xs leading-tight font-mono mb-4">{`
  ____    _    ____ _____
 / ___|  / \\  / ___| ____|
 \\___ \\ / _ \\| |  _|  _|
  ___) / ___ \\ |_| | |___
 |____/_/   \\_\\____|_____|`}</pre>
          <h1 className="text-xl font-semibold text-white mb-2">SAGE Desktop</h1>
          <p className="text-[#9ca3af] text-sm mb-6">Smart Agent Guidance Engine</p>
          <button onClick={() => onNewChat()} className="bg-[#8b5cf6]/20 hover:bg-[#8b5cf6]/30 text-[#a78bfa] px-4 py-2 rounded-lg text-sm font-medium transition-colors">+ Start New Chat</button>
        </div>
      </div>
    );
  }

  // Find last user message for steer display
  const lastUserMsg = [...messages].reverse().find(m => m.role === 'user');

  return (
    <div className="h-full flex flex-col bg-[#1a1b26]">
      <AgentStrip connected={connected} streaming={streaming} />
      {expandBtn}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && (
            <div className="text-center text-[#6b7280] text-sm mt-16">Start typing to chat with your AI agent.</div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className="mb-6">
              <MessageBubble message={msg} streaming={streaming && msg.id === '__streaming__'} elapsed={elapsed} fmtTime={fmtTime} />
            </div>
          ))}
          {streaming && messages[messages.length - 1]?.id !== '__streaming__' && (
            <div className="flex items-center gap-2 text-[#9ca3af] text-sm">
              <div className="w-2 h-2 bg-[#8b5cf6] rounded-full animate-pulse" />
              Working for {fmtTime(elapsed)}...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Steer bar (shows last sent message while streaming) */}
      {streaming && lastUserMsg && (
        <div className="border-t border-[#333648] px-4 py-2">
          <div className="max-w-3xl mx-auto flex items-center justify-between bg-[#24283b] rounded-lg px-3 py-2 border border-[#333648]">
            <div className="flex items-center gap-2 text-[#9ca3af] text-sm truncate flex-1">
              <span className="text-[#6b7280]">⊙</span>
              <span className="truncate">{lastUserMsg.content}</span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 ml-3">
              <button className="text-[#a78bfa] text-xs hover:text-white transition-colors">↩ Steer</button>
              <button className="text-[#9ca3af] text-xs hover:text-white transition-colors">🗑</button>
              <button className="text-[#9ca3af] text-xs hover:text-white transition-colors">⋯</button>
            </div>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-[#333648] px-4 pt-3 pb-2">
        <div className="max-w-3xl mx-auto">
          <div className="relative bg-[#24283b] rounded-xl border border-[#333648] focus-within:border-[#8b5cf6] transition-colors">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={streaming ? "Ask for follow-up changes" : "Message SAGE..."}
              rows={5}
              className="w-full bg-transparent text-[#ededec] text-[15px] leading-relaxed px-4 pt-3 pb-12 rounded-xl resize-none placeholder:text-[#6b7280] focus:outline-none min-h-[140px]"
            />
            {/* Bottom row inside input */}
            <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button className="text-[#9ca3af] hover:text-white text-lg transition-colors" title="Attach file">+</button>
                <span className="text-[#fb923c] text-xs font-medium flex items-center gap-1">
                  <span>⚠</span> Full access
                </span>
              </div>
              <div className="flex items-center gap-3">
                <select className="bg-transparent text-[#9ca3af] text-xs border-none outline-none cursor-pointer appearance-none pr-3">
                  <option value="claude">Claude 4.6</option>
                  <option value="codex">Codex</option>
                  <option value="ollama">Ollama</option>
                  <option value="travel">API Traveller</option>
                </select>
                <select className="bg-transparent text-[#9ca3af] text-xs border-none outline-none cursor-pointer appearance-none">
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                  <option value="max">Max</option>
                </select>
                {streaming ? (
                  <button onClick={onCancelStream} className="w-6 h-6 bg-[#333648] hover:bg-[#4b5563] rounded flex items-center justify-center transition-colors" title="Stop">
                    <div className="w-2.5 h-2.5 bg-white rounded-sm" />
                  </button>
                ) : (
                  <button
                    onClick={() => { if (input.trim()) { setHistory(prev => [input, ...prev]); setHistoryIdx(-1); onSendMessage(input); setInput(''); } }}
                    disabled={!input.trim()}
                    className="text-[#8b5cf6] text-xs font-medium disabled:opacity-30 transition-colors"
                  >
                    ↵
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message, streaming, elapsed, fmtTime }: { message: Message; streaming?: boolean; elapsed?: number; fmtTime?: (s: number) => string }) {
  const [showAnalysis, setShowAnalysis] = useState(false);

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-[#24283b] border border-[#333648] rounded-2xl rounded-br-sm px-4 py-2.5 max-w-[75%]">
          <p className="text-[#ededec] text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  const parts = parseContent(message.content);

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] w-full">
        {/* Working timer */}
        {streaming && fmtTime && elapsed !== undefined && (
          <div className="text-[#6b7280] text-xs mb-2">Working for {fmtTime(elapsed)}</div>
        )}

        {parts.map((part, i) => {
          if (part.type === 'thinking') return <ThinkingBlock key={i} content={part.content} />;
          if (part.type === 'code') return <CodeBlock key={i} content={part.content} lang={part.lang} />;
          if (part.type === 'tool') return <ToolChip key={i} content={part.content} />;
          return <div key={i} className="text-[#ededec] text-sm whitespace-pre-wrap leading-relaxed mb-2">{part.content}</div>;
        })}

        {/* Agent Analysis */}
        {!streaming && message.role === 'assistant' && message.id !== '__streaming__' && (
          <div className="mt-3">
            <button onClick={() => setShowAnalysis(!showAnalysis)} className="text-[#6b7280] hover:text-[#9ca3af] text-xs flex items-center gap-1 transition-colors">
              <span>{showAnalysis ? '[-]' : '[+]'}</span> SAGE Agent Analysis
            </button>
            {showAnalysis && (
              <div className="mt-1.5 pl-4 border-l-2 border-[#333648] text-xs text-[#9ca3af] space-y-1 py-1">
                <p>Agent: Claude Code (opus-4.6)</p>
                <p>Compression: active — ~85% context saved</p>
                <p>Tokens: ~{Math.round(message.content.length / 4)} used, ~{Math.round(message.content.length / 4 * 5.6)} saved</p>
                <p>Est. cost saved: ${(message.content.length / 4 * 5.6 * 0.000003).toFixed(4)}</p>
                <p>ML Prediction: no risk detected</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ThinkingBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="my-2 border border-[#8b5cf6]/30 rounded-lg overflow-hidden">
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center gap-2 px-3 py-2 bg-[#8b5cf6]/10 text-[#a78bfa] text-xs hover:bg-[#8b5cf6]/15 transition-colors">
        <span>{expanded ? '▾' : '▸'}</span> Reasoning
      </button>
      {expanded && <div className="px-3 py-2 text-[#9ca3af] text-xs whitespace-pre-wrap bg-[#1a1b26]/50 leading-relaxed">{content}</div>}
    </div>
  );
}

function CodeBlock({ content, lang }: { content: string; lang?: string }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div className="my-2 border border-[#4ade80]/30 rounded-lg overflow-hidden">
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center gap-2 px-3 py-2 bg-[#4ade80]/10 text-[#4ade80] text-xs hover:bg-[#4ade80]/15 transition-colors">
        <span>{expanded ? '▾' : '▸'}</span> Coding{lang ? ` (${lang})` : ''}
      </button>
      {expanded && <pre className="px-3 py-2 text-[#ededec] text-xs overflow-x-auto bg-[#16161e] font-mono leading-relaxed">{content}</pre>}
    </div>
  );
}

function ToolChip({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="my-1.5">
      <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-1.5 text-[#3b82f6] text-xs hover:text-[#60a5fa] transition-colors">
        <span>⊙</span> Ran commands <span className="text-[#6b7280]">›</span>
      </button>
      {expanded && <div className="mt-1 pl-4 text-[#9ca3af] text-xs font-mono bg-[#1a1b26] rounded px-3 py-2 border border-[#333648]">{content}</div>}
    </div>
  );
}

interface ContentPart { type: 'text' | 'thinking' | 'code' | 'tool'; content: string; lang?: string; }

function parseContent(raw: string): ContentPart[] {
  const parts: ContentPart[] = [];
  const lines = raw.split('\n');
  let i = 0;

  while (i < lines.length) {
    if (lines[i].match(/^<thinking>/i)) {
      let t = ''; i++;
      while (i < lines.length && !lines[i].match(/<\/thinking>/i)) { t += lines[i]+'\n'; i++; }
      i++;
      if (t.trim()) parts.push({ type: 'thinking', content: t.trim() });
      continue;
    }
    const cm = lines[i].match(/^```(\w*)/);
    if (cm) {
      const lang = cm[1]; let c = ''; i++;
      while (i < lines.length && !lines[i].startsWith('```')) { c += lines[i]+'\n'; i++; }
      i++;
      if (c.trim()) parts.push({ type: 'code', content: c.trimEnd(), lang });
      continue;
    }
    // Detect tool call lines
    if (lines[i].match(/^(Running|⊙|sage run|Ran )/i)) {
      parts.push({ type: 'tool', content: lines[i] });
      i++; continue;
    }
    let text = '';
    while (i < lines.length && !lines[i].match(/^<thinking>/i) && !lines[i].match(/^```/) && !lines[i].match(/^(Running|⊙|sage run|Ran )/i)) {
      text += lines[i]+'\n'; i++;
    }
    if (text.trim()) parts.push({ type: 'text', content: text.trim() });
  }
  if (parts.length === 0) parts.push({ type: 'text', content: raw });
  return parts;
}
