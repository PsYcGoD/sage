import { useState, useEffect } from 'react';

export default function TitleBar() {
  const [maximized, setMaximized] = useState(false);

  useEffect(() => {
    window.electronAPI?.window.isMaximized().then(setMaximized);
    window.electronAPI?.window.onMaximizedChange(setMaximized);
  }, []);

  return (
    <div className="titlebar-drag h-9 bg-sage-sidebar flex items-center justify-between px-3 border-b border-sage-border select-none">
      <div className="flex items-center gap-2">
        <span className="text-sage-purple font-bold text-sm">SAGE</span>
        <span className="text-sage-dim text-xs">Desktop</span>
      </div>

      <div className="titlebar-no-drag flex items-center gap-1">
        <button
          onClick={() => window.electronAPI?.window.minimize()}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-sage-surface text-sage-muted hover:text-sage-text transition-colors"
        >
          <svg width="12" height="12" viewBox="0 0 12 12"><rect y="5" width="12" height="1.5" fill="currentColor" rx="0.5"/></svg>
        </button>
        <button
          onClick={() => window.electronAPI?.window.maximize()}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-sage-surface text-sage-muted hover:text-sage-text transition-colors"
        >
          {maximized ? (
            <svg width="12" height="12" viewBox="0 0 12 12"><rect x="1.5" y="3" width="7.5" height="7.5" fill="none" stroke="currentColor" strokeWidth="1.2" rx="0.5"/><path d="M3 3V1.5h7.5V9H9" fill="none" stroke="currentColor" strokeWidth="1.2"/></svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 12 12"><rect x="1" y="1" width="10" height="10" fill="none" stroke="currentColor" strokeWidth="1.5" rx="0.5"/></svg>
          )}
        </button>
        <button
          onClick={() => window.electronAPI?.window.close()}
          className="w-7 h-7 flex items-center justify-center rounded hover:bg-sage-red/20 text-sage-muted hover:text-sage-red transition-colors"
        >
          <svg width="12" height="12" viewBox="0 0 12 12"><path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
        </button>
      </div>
    </div>
  );
}
