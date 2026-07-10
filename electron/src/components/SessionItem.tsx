import { useState } from 'react';
import type { Session } from '../types';

interface SessionItemProps {
  session: Session;
  active: boolean;
  onClick: () => void;
}

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d`;
  const weeks = Math.floor(days / 7);
  return `${weeks}w`;
}

export default function SessionItem({ session, active, onClick }: SessionItemProps) {
  const [showMenu, setShowMenu] = useState(false);

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setShowMenu(true);
    const closeMenu = () => {
      setShowMenu(false);
      document.removeEventListener('click', closeMenu);
    };
    setTimeout(() => document.addEventListener('click', closeMenu), 0);
  };

  return (
    <div className="relative">
      <button
        onClick={onClick}
        onContextMenu={handleContextMenu}
        className={`w-full text-left px-2 py-2 rounded-md text-sm transition-all group relative ${
          active
            ? 'bg-sage-surface text-sage-text'
            : 'text-sage-muted hover:bg-sage-surface/50 hover:text-sage-text'
        }`}
      >
        {active && (
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-sage-purple rounded-r" />
        )}
        <div className="flex items-center justify-between pl-2">
          <span className="truncate flex-1">{session.title || 'New Chat'}</span>
          <span className="text-xs text-sage-dim ml-2 flex-shrink-0">
            {relativeTime(session.updated_at)}
          </span>
        </div>
        {session.preview && (
          <div className="text-xs text-sage-dim truncate mt-0.5 pl-2">
            {session.preview}
          </div>
        )}
        {session.unread && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-sage-purple rounded-full" />
        )}
      </button>

      {/* Context Menu */}
      {showMenu && (
        <div className="absolute right-0 top-full z-50 mt-1 w-36 bg-sage-elevated border border-sage-border rounded-lg shadow-xl py-1 text-sm">
          <button className="w-full text-left px-3 py-1.5 text-sage-text hover:bg-sage-surface transition-colors">Rename</button>
          <button className="w-full text-left px-3 py-1.5 text-sage-text hover:bg-sage-surface transition-colors">
            {session.pinned ? 'Unpin' : 'Pin'}
          </button>
          <button className="w-full text-left px-3 py-1.5 text-sage-text hover:bg-sage-surface transition-colors">Mark unread</button>
          <hr className="border-sage-border my-1" />
          <button className="w-full text-left px-3 py-1.5 text-sage-red hover:bg-sage-red/10 transition-colors">Delete</button>
        </div>
      )}
    </div>
  );
}
