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
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
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
      {/* Header */}
      <div className="p-3 flex items-center justify-between">
        <button
          onClick={handleNewChat}
          className="flex-1 bg-[#8b5cf6]/10 hover:bg-[#8b5cf6]/20 text-[#a78bfa] text-sm font-medium py-2 px-3 rounded-lg transition-colors"
        >
          + New Chat
        </button>
        <button
          onClick={onCollapse}
          className="ml-2 p-2 rounded hover:bg-[#24283b] text-[#9ca3af] hover:text-white transition-colors"
          title="Collapse sidebar"
        >
          <svg width="14" height="14" viewBox="0 0 14 14"><path d="M9 3L5 7l4 4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
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

      {/* User profile footer */}
      <div className="relative p-3 border-t border-[#333648]" ref={menuRef}>
        {showUserMenu && (
          <div className="absolute bottom-full left-3 right-3 mb-1 bg-[#1f2335] border border-[#333648] rounded-lg shadow-xl py-1 z-50">
            <div className="px-3 py-2 border-b border-[#333648]">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-[#8b5cf6] flex items-center justify-center text-white text-xs font-bold">P</div>
                <div>
                  <div className="text-[#ededec] text-sm font-medium">PsYcGoD</div>
                  <div className="text-[#6b7280] text-xs">@psycgod</div>
                </div>
              </div>
            </div>
            <button className="w-full text-left px-3 py-2 text-sm text-[#ededec] hover:bg-[#24283b] transition-colors flex items-center gap-2">
              <svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.2"/><path d="M4.5 7h5M7 4.5v5" stroke="currentColor" strokeWidth="1.2"/></svg>
              Usage
            </button>
            <button
              onClick={() => { setShowUserMenu(false); onOpenSettings(); }}
              className="w-full text-left px-3 py-2 text-sm text-[#ededec] hover:bg-[#24283b] transition-colors flex items-center justify-between"
            >
              <span className="flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 14 14"><path d="M7 9a2 2 0 100-4 2 2 0 000 4z" fill="none" stroke="currentColor" strokeWidth="1.2"/><path d="M11.4 8.6l.9.5a.5.5 0 01.2.7l-1 1.7a.5.5 0 01-.6.2l-.9-.4a4.5 4.5 0 01-1 .6l-.1 1a.5.5 0 01-.5.4H6.6a.5.5 0 01-.5-.4l-.1-1a4.5 4.5 0 01-1-.6l-.9.4a.5.5 0 01-.6-.2l-1-1.7a.5.5 0 01.2-.7l.9-.5a4.5 4.5 0 010-1.2l-.9-.5a.5.5 0 01-.2-.7l1-1.7a.5.5 0 01.6-.2l.9.4a4.5 4.5 0 011-.6l.1-1a.5.5 0 01.5-.4h1.8a.5.5 0 01.5.4l.1 1a4.5 4.5 0 011 .6l.9-.4a.5.5 0 01.6.2l1 1.7a.5.5 0 01-.2.7l-.9.5a4.5 4.5 0 010 1.2z" fill="none" stroke="currentColor" strokeWidth="1"/></svg>
                Settings
              </span>
              <span className="text-[#6b7280] text-xs">Ctrl+,</span>
            </button>
            <hr className="border-[#333648] my-1" />
            <button className="w-full text-left px-3 py-2 text-sm text-[#f87171] hover:bg-[#f87171]/10 transition-colors flex items-center gap-2">
              <svg width="14" height="14" viewBox="0 0 14 14"><path d="M5 2h7v10H5M2 7h7M7 4l3 3-3 3" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
              Log out
            </button>
          </div>
        )}

        <button
          onClick={() => setShowUserMenu(!showUserMenu)}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#24283b] transition-colors"
        >
          <div className="w-7 h-7 rounded-full bg-[#8b5cf6] flex items-center justify-center text-white text-xs font-bold">P</div>
          <span className="text-[#ededec] text-sm flex-1 text-left">PsYcGoD</span>
          <svg width="12" height="12" viewBox="0 0 12 12" className="text-[#6b7280]"><path d="M3 5l3-3 3 3M3 7l3 3 3-3" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
        </button>
      </div>
    </div>
  );
}
