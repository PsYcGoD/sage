import { useState, useMemo, useRef, useEffect } from 'react';
import SessionItem from './SessionItem';
import type { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeSession: Session | null;
  onSelectSession: (session: Session) => void;
  onNewChat: (folder?: string) => void;
  onOpenSettings: () => void;
  onCollapse: () => void;
}

export default function Sidebar({ sessions, activeSession, onSelectSession, onNewChat, onOpenSettings, onCollapse }: SidebarProps) {
  const [search, setSearch] = useState('');
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowProfileMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const grouped = useMemo(() => {
    const filtered = sessions.filter(
      (s) => s.title.toLowerCase().includes(search.toLowerCase())
    );
    const groups: Record<string, Session[]> = {};
    for (const session of filtered) {
      const key = session.project || 'Ungrouped';
      if (!groups[key]) groups[key] = [];
      groups[key].push(session);
    }
    return groups;
  }, [sessions, search]);

  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (group: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  };

  async function handleNewChat() {
    const folder = await (window as any).electronAPI?.dialog?.pickFolder();
    onNewChat(folder || undefined);
  }

  return (
    <div className="h-full bg-[#16161e] flex flex-col border-r border-[#333648]">
      {/* Profile row — clickable, opens dropdown */}
      <div className="relative px-3 pt-3 pb-1" ref={menuRef}>
        <button
          onClick={() => setShowProfileMenu(!showProfileMenu)}
          className="w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-[#24283b] transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-[#8b5cf6] flex items-center justify-center text-white text-xs font-bold shrink-0">P</div>
          <span className="text-[#ededec] text-sm font-medium flex-1 text-left">PsYcGoD</span>
          <svg width="12" height="12" viewBox="0 0 12 12" className="text-[#6b7280]"><path d="M3 5l3-3 3 3M3 7l3 3 3-3" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
        </button>

        {showProfileMenu && (
          <div className="absolute top-full left-3 right-3 mt-1 bg-[#1f2335] border border-[#333648] rounded-lg shadow-xl py-1 z-50">
            <button className="w-full text-left px-3 py-2 text-sm text-[#ededec] hover:bg-[#24283b] transition-colors flex items-center gap-2">
              🐾 Pet
            </button>
            <button className="w-full text-left px-3 py-2 text-sm text-[#ededec] hover:bg-[#24283b] transition-colors flex items-center gap-2">
              📊 Usage
            </button>
            <button
              onClick={() => { setShowProfileMenu(false); onOpenSettings(); }}
              className="w-full text-left px-3 py-2 text-sm text-[#ededec] hover:bg-[#24283b] transition-colors flex items-center gap-2"
            >
              ⚙️ Settings
            </button>
            <hr className="border-[#333648] my-1" />
            <button className="w-full text-left px-3 py-2 text-sm text-[#f87171] hover:bg-[#f87171]/10 transition-colors flex items-center gap-2">
              🚪 Sign out
            </button>
          </div>
        )}
      </div>

      {/* SAGE branding — beside "By PsYcGoD" */}
      <div className="px-4 pb-2 flex items-baseline gap-2">
        <span className="text-[#8b5cf6] text-base font-bold">SAGE</span>
        <span className="text-[#a78bfa] text-[10px]">By PsYcGoD AI&ML</span>
      </div>

      {/* New Chat button */}
      <div className="px-3 pb-2">
        <button
          onClick={handleNewChat}
          className="w-full bg-[#8b5cf6]/10 hover:bg-[#8b5cf6]/20 text-[#a78bfa] text-sm font-medium py-2 px-3 rounded-lg transition-colors"
        >
          + New Chat
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pb-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search chats..."
          className="w-full bg-[#24283b] text-[#ededec] text-sm px-3 py-1.5 rounded-md border border-[#333648] focus:border-[#8b5cf6] focus:outline-none placeholder:text-[#6b7280]"
        />
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto px-1.5">
        {Object.keys(grouped).length === 0 && sessions.length === 0 && (
          <div className="text-center text-[#6b7280] text-xs mt-8 px-4">No sessions yet. Start a new chat!</div>
        )}
        {Object.entries(grouped).map(([group, items]) => (
          <div key={group} className="mb-1">
            <button
              onClick={() => toggleGroup(group)}
              className="w-full text-left px-2 py-1 text-xs font-medium text-[#9ca3af] hover:text-white flex items-center gap-1 transition-colors"
            >
              <svg width="10" height="10" viewBox="0 0 10 10" className={`transition-transform ${expandedGroups.has(group) || expandedGroups.size === 0 ? 'rotate-90' : ''}`}>
                <path d="M3 1l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
              </svg>
              {group}
            </button>
            {(expandedGroups.has(group) || expandedGroups.size === 0) &&
              items.map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  active={activeSession?.id === session.id}
                  onClick={() => onSelectSession(session)}
                />
              ))}
          </div>
        ))}
      </div>

      {/* Bottom: AI Provider selector */}
      <div className="p-3 border-t border-[#333648] space-y-2">
        <div className="text-[#6b7280] text-[10px] uppercase tracking-wider font-medium">AI Provider</div>
        <select
          className="w-full bg-[#24283b] text-[#ededec] text-sm px-3 py-2 rounded-lg border border-[#333648] focus:border-[#8b5cf6] focus:outline-none cursor-pointer"
          defaultValue="Claude"
        >
          <option value="Claude">Claude</option>
          <option value="Codex">Codex</option>
          <option value="Ollama">Ollama</option>
          <option value="Gemini">Gemini</option>
          <option value="API Travel">API Travel</option>
        </select>
      </div>
    </div>
  );
}
