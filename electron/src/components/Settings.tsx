import { useState, useEffect } from 'react';

interface SettingsProps {
  onClose: () => void;
  wsRef: React.RefObject<WebSocket | null>;
  connected: boolean;
  externalSettings?: Partial<GuiSettings>;
  onExternalChange?: (patch: Partial<GuiSettings>) => void;
}

type SettingsPage =
  | 'general' | 'profile' | 'appearance' | 'voice' | 'personalization'
  | 'configuration' | 'pets' | 'keyboard' | 'usage'
  | 'plugins' | 'providers' | 'mcp-servers' | 'skills'
  | 'hooks' | 'connections' | 'git' | 'environment' | 'worktrees' | 'archived';

interface GuiSettings {
  permission_mode: 'ask' | 'approve' | 'full';
  sandbox_mode: string;
  speed: string;
  send_shortcut: string;
  completion_notifications: boolean;
  permission_notifications: boolean;
  question_notifications: boolean;
  reasoning_effort: string;
  api_travel: boolean;
  auth_mode: string;
  api_endpoint: string;
}

const DEFAULT_GUI_SETTINGS: GuiSettings = {
  permission_mode: 'ask',
  sandbox_mode: 'Read & write',
  speed: 'Standard',
  send_shortcut: 'Enter to send',
  completion_notifications: true,
  permission_notifications: true,
  question_notifications: true,
  reasoning_effort: 'High',
  api_travel: false,
  auth_mode: 'direct',
  api_endpoint: 'sage.api.marketingstudios.in',
};

function normalizeSettings(settings: Partial<GuiSettings>): GuiSettings {
  const rawPermission = String(settings.permission_mode || DEFAULT_GUI_SETTINGS.permission_mode);
  const permission_mode =
    rawPermission === 'Full access' || rawPermission === 'full'
      ? 'full'
      : rawPermission === 'Auto-approve' || rawPermission === 'approve'
        ? 'approve'
        : 'ask';
  return { ...DEFAULT_GUI_SETTINGS, ...settings, permission_mode };
}

function permissionLabel(value: GuiSettings['permission_mode']): string {
  if (value === 'full') return 'Full access';
  if (value === 'approve') return 'Auto-approve safe';
  return 'On request';
}

const NAV_SECTIONS = [
  {
    title: 'Personal',
    items: [
      { id: 'general' as SettingsPage, label: 'General', icon: '⚙' },
      { id: 'profile' as SettingsPage, label: 'Profile', icon: '👤' },
      { id: 'personalization' as SettingsPage, label: 'Personalization', icon: '🧠' },
      { id: 'configuration' as SettingsPage, label: 'Configuration', icon: '⚡' },
      { id: 'pets' as SettingsPage, label: 'Pets', icon: '🐾' },
      { id: 'keyboard' as SettingsPage, label: 'Keyboard shortcuts', icon: '⌨' },
      { id: 'usage' as SettingsPage, label: 'Usage & billing', icon: '📊' },
    ],
  },
  {
    title: 'Integrations',
    items: [
      { id: 'plugins' as SettingsPage, label: 'Plugins', icon: '🧩' },
      { id: 'providers' as SettingsPage, label: 'AI Providers', icon: '🤖' },
      { id: 'mcp-servers' as SettingsPage, label: 'MCP Servers', icon: '🔌' },
      { id: 'skills' as SettingsPage, label: 'Skills', icon: '✨' },
    ],
  },
  {
    title: 'Coding',
    items: [
      { id: 'hooks' as SettingsPage, label: 'Hooks', icon: '🪝' },
      { id: 'connections' as SettingsPage, label: 'Connections', icon: '🔗' },
      { id: 'git' as SettingsPage, label: 'Git', icon: '📁' },
      { id: 'environment' as SettingsPage, label: 'Environment', icon: '🖥' },
      { id: 'worktrees' as SettingsPage, label: 'Worktrees', icon: '🌲' },
      { id: 'archived' as SettingsPage, label: 'Archived chats', icon: '🗄' },
    ],
  },
];

export default function Settings({ onClose, wsRef, connected, externalSettings, onExternalChange }: SettingsProps) {
  const [page, setPage] = useState<SettingsPage>('general');
  const [search, setSearch] = useState('');
  const [settings, setSettings] = useState<GuiSettings>(() => {
    try {
      return { ...DEFAULT_GUI_SETTINGS, ...(externalSettings || {}) };
    } catch {
      return DEFAULT_GUI_SETTINGS;
    }
  });
  const activeItem = NAV_SECTIONS.flatMap(section => section.items).find(item => item.id === page);

  useEffect(() => {
    if (!connected || !wsRef.current) return;
    function handleMsg(event: MessageEvent) {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'settings.get.response') {
          const next = normalizeSettings({ ...DEFAULT_GUI_SETTINGS, ...(msg.payload.settings || {}), ...(externalSettings || {}) });
          setSettings(next);
        }
      } catch {}
    }
    wsRef.current.addEventListener('message', handleMsg);
    wsRef.current.send(JSON.stringify({ type: 'settings.get', payload: {} }));
    return () => { wsRef.current?.removeEventListener('message', handleMsg); };
  }, [connected, wsRef, externalSettings]);

  function updateSettings(patch: Partial<GuiSettings>) {
    const normalized = normalizeSettings({ ...settings, ...patch });
    setSettings(normalized);
    onExternalChange?.(patch);
  }

  function saveSettings() {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'settings.set', payload: { settings } }));
    }
    onClose();
  }

  const filteredSections = NAV_SECTIONS.map(section => ({
    ...section,
    items: section.items.filter(item =>
      item.label.toLowerCase().includes(search.toLowerCase())
    ),
  })).filter(s => s.items.length > 0);

  return (
    <div className="h-full w-full flex bg-[#151622]">
      {/* Left nav */}
      <div className="w-72 bg-[#11131d] border-r border-[#2a2d3d] flex flex-col">
        <button onClick={onClose} className="flex items-center gap-2 px-5 py-4 text-[#9ca3af] hover:text-white text-sm transition-colors border-b border-[#2a2d3d] active:scale-[0.99]">
          <svg width="14" height="14" viewBox="0 0 14 14"><path d="M9 3L5 7l4 4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Back to app
        </button>
        <div className="px-4 py-4 border-b border-[#2a2d3d]">
          <div className="text-white text-lg font-semibold mb-1">Settings</div>
          <div className="text-[#7d8498] text-xs mb-3">Find and tune SAGE behavior.</div>
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search settings..."
            className="w-full bg-[#1b1e2d] text-[#ededec] text-sm px-3 py-2 rounded-md border border-[#303449] focus:border-[#8b5cf6] focus:outline-none placeholder:text-[#6b7280]"
          />
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          {filteredSections.map(section => (
            <div key={section.title} className="mb-5">
              <div className="text-[#727891] text-[11px] font-semibold uppercase tracking-wider px-2 mb-2">{section.title}</div>
              {section.items.map(item => (
                <button
                  key={item.id}
                  onClick={() => setPage(item.id)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm flex items-center justify-between transition-colors active:scale-[0.99] ${
                    page === item.id ? 'bg-[#24283b] text-white shadow-[inset_3px_0_0_#8b5cf6]' : 'text-[#a6adbd] hover:text-white hover:bg-[#1b1e2d]'
                  }`}
                >
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          ))}
          {filteredSections.length === 0 && (
            <div className="px-3 py-6 text-center text-[#7d8498] text-sm">
              No settings match "{search}".
            </div>
          )}
        </div>
      </div>

      {/* Content — centered with generous padding */}
      <div className="flex-1 overflow-y-auto relative">
        <div className="max-w-5xl mx-auto px-6 xl:px-10 py-8 pb-24">
          <div className="mb-8 border-b border-[#2a2d3d] pb-5">
            <div className="text-[#7d8498] text-xs uppercase tracking-wider mb-2">SAGE Preferences</div>
            <h1 className="text-white text-2xl font-semibold">{activeItem?.label || 'Settings'}</h1>
          </div>
          {page === 'general' && <GeneralPage settings={settings} onChange={updateSettings} />}
          {page === 'profile' && <ProfilePage />}
          {page === 'appearance' && <AppearancePage />}
          {page === 'voice' && <VoicePage />}
          {page === 'personalization' && <PersonalizationPage />}
          {page === 'configuration' && <ConfigurationPage />}
          {page === 'pets' && <PetsPage />}
          {page === 'keyboard' && <KeyboardPage />}
          {page === 'usage' && <UsagePage />}
          {page === 'plugins' && <PluginsPage />}
          {page === 'providers' && <ProvidersPage wsRef={wsRef} connected={connected} settings={settings} onChange={updateSettings} />}
          {page === 'mcp-servers' && <MCPPage />}
          {page === 'skills' && <SkillsPage />}
          {page === 'hooks' && <HooksPage />}
          {page === 'connections' && <ConnectionsPage />}
          {page === 'git' && <GitPage />}
          {page === 'environment' && <EnvironmentPage />}
          {page === 'worktrees' && <WorktreesPage />}
          {page === 'archived' && <ArchivedChatsPage />}
        </div>

        {/* Sticky save bar */}
        <div className="sticky bottom-0 left-0 right-0 bg-[#151622]/92 backdrop-blur border-t border-[#2a2d3d] px-10 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-[#9ca3af] hover:text-white rounded-md border border-[#333648] hover:bg-[#24283b] transition-colors active:scale-[0.97]"
          >Cancel</button>
          <button
            onClick={saveSettings}
            className="px-5 py-2 text-sm text-white bg-[#8b5cf6] hover:bg-[#7c3aed] rounded-md font-medium transition-colors active:scale-[0.97]"
          >Save Changes</button>
        </div>
      </div>
    </div>
  );
}

// ─── PAGE COMPONENTS ─────────────────────────────────────────────────

function GeneralPage({ settings, onChange }: { settings: GuiSettings; onChange: (patch: Partial<GuiSettings>) => void }) {
  return (
    <div>
      <PageTitle title="General" />
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-3 mb-8">
        <SummaryCard label="Safety" value={permissionLabel(settings.permission_mode)} desc="Approvals before risky actions" />
        <SummaryCard label="Sandbox" value={settings.sandbox_mode} desc="Project edits allowed" />
        <SummaryCard label="Model" value={`${settings.reasoning_effort} reasoning`} desc="Default for complex tasks" />
      </div>
      <Section title="Permissions">
        <p className="text-[#6b7280] text-xs mb-3">Configure approval policy and sandbox settings</p>
        <Card>
          <RowSelect label="Approval policy" desc="Choose when SAGE asks for approval" options={['ask', 'approve', 'full']} labels={{ ask: 'On request', approve: 'Auto-approve safe', full: 'Full access' }} value={settings.permission_mode} onChange={permission_mode => onChange({ permission_mode: permission_mode as GuiSettings['permission_mode'] })} />
          <RowSelect label="Sandbox settings" desc="Choose how much SAGE can do when running commands" options={['Read only', 'Read & write', 'Full access']} value={settings.sandbox_mode} onChange={sandbox_mode => onChange({ sandbox_mode })} />
        </Card>
      </Section>
      <Section title="Speed">
        <Card>
          <RowSelect label="Default speed" desc="How quickly SAGE runs across tasks and agents" options={['Standard', 'Fast', 'Turbo']} value={settings.speed} onChange={speed => onChange({ speed })} />
        </Card>
      </Section>
      <Section title="Send shortcut">
        <Card>
          <RowSelect label="Send message" desc="Choose when Enter sends a prompt" options={['Enter to send', 'Ctrl+Enter to send']} value={settings.send_shortcut} onChange={send_shortcut => onChange({ send_shortcut })} />
        </Card>
      </Section>
      <Section title="Notifications">
        <Card>
          <ToggleRow label="Completion notifications" desc="Alert when SAGE finishes a task" checked={settings.completion_notifications} onChange={completion_notifications => onChange({ completion_notifications })} />
          <ToggleRow label="Permission notifications" desc="Show alerts when permissions are required" checked={settings.permission_notifications} onChange={permission_notifications => onChange({ permission_notifications })} />
          <ToggleRow label="Question notifications" desc="Show alerts when input is needed" checked={settings.question_notifications} onChange={question_notifications => onChange({ question_notifications })} />
        </Card>
      </Section>
      <Section title="Model features">
        <Card>
          <RowSelect label="Reasoning effort" desc="Choose default reasoning level" options={['Low', 'Medium', 'High', 'Max']} value={settings.reasoning_effort} onChange={reasoning_effort => onChange({ reasoning_effort })} />
        </Card>
      </Section>
    </div>
  );
}

function ProfilePage() {
  const [providers, setProviders] = useState<any[]>([]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:19480');
    ws.onopen = () => ws.send(JSON.stringify({ type: 'provider.list', payload: {} }));
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === 'provider.list.response') {
          setProviders(msg.payload.providers || []);
          ws.close();
        }
      } catch {}
    };
    ws.onerror = () => ws.close();
    return () => { try { ws.close(); } catch {} };
  }, []);

  return (
    <div>
      <PageTitle title="Profile" />
      <Section title="Identity">
        <Card>
          <RowInput label="Display Name" placeholder="PsYcGoD" defaultVal="PsYcGoD" />
          <RowInput label="Username" placeholder="@psycgod" defaultVal="@psycgod" />
          <RowInput label="Email" placeholder="email@example.com" />
        </Card>
        <button className="mt-3 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white text-sm px-4 py-2 rounded-lg transition-colors">Save Profile</button>
      </Section>

      <Section title="Connected AI Agents">
        <p className="text-[#6b7280] text-xs mb-2">Agents detected on this system. Toggle to connect/disconnect.</p>
        <Card>
          {providers.map((p, i) => (
            <div key={p.id} className={`flex items-center justify-between py-3 ${i < providers.length - 1 ? 'border-b border-[#333648]' : ''}`}>
              <div className="flex items-center gap-2.5">
                <span className={`w-2.5 h-2.5 rounded-full ${p.status === 'connected' ? 'bg-[#4ade80]' : 'bg-[#4b5563]'}`} />
                <div>
                  <span className="text-[#ededec] text-sm">{p.name}</span>
                  <span className="text-[#6b7280] text-xs ml-2">{p.model}</span>
                </div>
              </div>
              <ToggleSwitch defaultOn={p.status === 'connected'} />
            </div>
          ))}
        </Card>
      </Section>
    </div>
  );
}

function AppearancePage() {
  const [theme, setTheme] = useState<'system' | 'light' | 'dark'>(() => {
    return (localStorage.getItem('sage-theme') as any) || 'dark';
  });

  function applyTheme(t: 'system' | 'light' | 'dark') {
    setTheme(t);
    localStorage.setItem('sage-theme', t);
    const root = document.documentElement;
    if (t === 'light') {
      root.style.setProperty('--bg-primary', '#f8f9fa');
      root.style.setProperty('--bg-secondary', '#e9ecef');
      root.style.setProperty('--text-primary', '#1a1b26');
      root.style.setProperty('--text-muted', '#6b7280');
      document.body.style.background = '#f8f9fa';
      document.body.style.color = '#1a1b26';
    } else {
      root.style.setProperty('--bg-primary', '#1a1b26');
      root.style.setProperty('--bg-secondary', '#16161e');
      root.style.setProperty('--text-primary', '#ededec');
      root.style.setProperty('--text-muted', '#6b7280');
      document.body.style.background = '#1a1b26';
      document.body.style.color = '#ededec';
    }
  }

  return (
    <div>
      <PageTitle title="Appearance" />
      <Section title="Theme">
        <div className="flex gap-3 mb-4">
          {(['system', 'light', 'dark'] as const).map(t => (
            <button
              key={t}
              onClick={() => applyTheme(t)}
              className={`flex-1 rounded-lg border-2 p-3 transition-colors ${
                theme === t ? 'border-[#8b5cf6]' : 'border-[#333648] hover:border-[#4b5563]'
              }`}
            >
              <div className={`h-16 rounded mb-2 ${t === 'dark' ? 'bg-[#1a1b26]' : t === 'light' ? 'bg-[#f8f9fa]' : 'bg-gradient-to-r from-[#f8f9fa] to-[#1a1b26]'}`}>
                <div className={`h-full w-1/3 rounded-l ${t === 'dark' ? 'bg-[#16161e]' : t === 'light' ? 'bg-[#e9ecef]' : 'bg-[#e9ecef]/50'}`} />
              </div>
              <div className="text-[#ededec] text-xs text-center capitalize">{t}</div>
            </button>
          ))}
        </div>
      </Section>
      <Section title="Colors">
        <Card>
          <RowInput label="Accent" placeholder="#8b5cf6" defaultVal="#8b5cf6" />
          <RowInput label="Background" placeholder="#1a1b26" defaultVal="#1a1b26" />
          <RowInput label="Foreground" placeholder="#ededec" defaultVal="#ededec" />
          <RowInput label="UI font" placeholder="Inter, system-ui" defaultVal="Inter, system-ui" />
          <RowInput label="Code font" placeholder="JetBrains Mono" defaultVal="JetBrains Mono" />
        </Card>
      </Section>
      <Section title="Layout">
        <Card>
          <ToggleRow label="Translucent sidebar" desc="Use a translucent sidebar background" defaultOn={false} />
          <RowSelect label="Contrast" desc="UI contrast level" options={['Low (35)', 'Medium (45)', 'High (68)']} defaultVal="Medium (45)" />
        </Card>
      </Section>
    </div>
  );
}

function PersonalizationPage() {
  return (
    <div>
      <PageTitle title="Personalization" />
      <div className="bg-[#fbbf24]/10 border border-[#fbbf24]/30 rounded-lg px-4 py-2.5 mb-4 flex items-center gap-2">
        <span className="text-[#fbbf24]">⚠</span>
        <span className="text-[#ededec] text-sm">Personality settings apply per model. Not all models support customization.</span>
      </div>
      <Section title="Personality">
        <Card>
          <RowSelect label="Response tone" desc="Choose a default tone for SAGE responses" options={['Friendly', 'Professional', 'Concise', 'Detailed']} defaultVal="Friendly" />
        </Card>
      </Section>
      <Section title="Custom instructions">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[#6b7280] text-xs">Give SAGE extra instructions and context for all tasks</p>
          <button className="text-[#9ca3af] text-xs hover:text-white transition-colors">Save</button>
        </div>
        <textarea
          defaultValue="# SAGE MANAGED BLOCK START&#10;## SAGE Integration - MANDATORY&#10;&#10;This system has SAGE installed. You MUST route every shell command through SAGE."
          className="w-full h-32 bg-[#24283b] text-[#ededec] text-sm px-4 py-3 rounded-lg border border-[#333648] focus:border-[#8b5cf6] focus:outline-none resize-y font-mono"
        />
      </Section>
      <Section title="Memory">
        <p className="text-[#6b7280] text-xs mb-2">Configure how SAGE collects, retains, and consolidates memories</p>
        <Card>
          <ToggleRow label="Enable memories" desc="Generate new memories from tasks and bring them into new tasks" defaultOn={true} />
          <ToggleRow label="Memory from tool-assisted tasks" desc="Generate memories from tasks that used MCP tools" defaultOn={true} />
          <div className="flex items-center justify-between py-2.5">
            <div>
              <span className="text-[#ededec] text-sm">Reset memories</span>
              <p className="text-[#6b7280] text-xs mt-0.5">Delete all SAGE memories</p>
            </div>
            <button className="text-[#f87171] text-xs px-3 py-1 rounded border border-[#f87171]/30 hover:bg-[#f87171]/10 transition-colors">Reset</button>
          </div>
        </Card>
      </Section>
    </div>
  );
}

function ConfigurationPage() {
  return (
    <div>
      <PageTitle title="Configuration" />
      <Section title="Workspace Dependencies">
        <Card>
          <ToggleRow label="SAGE dependencies" desc="Allow SAGE to install and expose bundled Python tools" defaultOn={true} />
          <div className="flex items-center justify-between py-2.5 border-b border-[#333648]">
            <div>
              <span className="text-[#ededec] text-sm">Diagnose issues</span>
              <p className="text-[#6b7280] text-xs mt-0.5">Check the workspace bundle and record diagnostic logs</p>
            </div>
            <button className="text-[#ededec] text-xs px-3 py-1 rounded border border-[#333648] hover:bg-[#24283b] transition-colors">🔍 Diagnose</button>
          </div>
          <div className="flex items-center justify-between py-2.5">
            <div>
              <span className="text-[#ededec] text-sm">Reset and install Workspace</span>
              <p className="text-[#6b7280] text-xs mt-0.5">Delete the local bundle, download it again, and reload tools</p>
            </div>
            <button className="text-[#f87171] text-xs px-3 py-1 rounded border border-[#f87171]/30 hover:bg-[#f87171]/10 transition-colors">⬇ Reinstall</button>
          </div>
        </Card>
      </Section>
      <Section title="ML Daemon">
        <Card>
          <ToggleRow label="ML predictions" desc="Predict command failures before execution" defaultOn={true} />
          <ToggleRow label="Context compression" desc="Compress verbose command output automatically" defaultOn={true} />
          <ToggleRow label="SAGE agents" desc="Run background agents for code analysis" defaultOn={true} />
          <ToggleRow label="Telemetry" desc="Send usage stats to SAGE dashboard" defaultOn={true} />
        </Card>
      </Section>
    </div>
  );
}

function KeyboardPage() {
  const shortcuts = [
    { key: 'Ctrl+N', action: 'New chat' },
    { key: 'Ctrl+L', action: 'Clear conversation' },
    { key: 'Ctrl+K', action: 'Search chats' },
    { key: 'Ctrl+,', action: 'Open settings' },
    { key: 'Ctrl+T', action: 'New tab' },
    { key: 'Ctrl+W', action: 'Close tab' },
    { key: 'Ctrl+Q', action: 'Quit' },
    { key: 'Up arrow', action: 'Previous message' },
    { key: 'Ctrl+Z', action: 'Undo / restore last input' },
    { key: 'Ctrl+Shift+C', action: 'Copy code block' },
  ];
  return (
    <div>
      <PageTitle title="Keyboard Shortcuts" />
      <Card>
        {shortcuts.map((s, i) => (
          <div key={i} className={`flex items-center justify-between py-2.5 ${i < shortcuts.length - 1 ? 'border-b border-[#333648]' : ''}`}>
            <span className="text-[#ededec] text-sm">{s.action}</span>
            <kbd className="bg-[#1a1b26] text-[#9ca3af] text-xs px-2 py-1 rounded border border-[#333648] font-mono">{s.key}</kbd>
          </div>
        ))}
      </Card>
    </div>
  );
}

function UsagePage() {
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:19480');
    ws.onopen = () => ws.send(JSON.stringify({ type: 'metrics.get', payload: {} }));
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'metrics.get.response') {
        setMetrics(msg.payload);
        ws.close();
      }
    };
    ws.onerror = () => ws.close();
    return () => ws.close();
  }, []);

  const fmt = (n: number) => n >= 1_000_000 ? (n/1_000_000).toFixed(2)+'M' : n >= 1_000 ? (n/1_000).toFixed(1)+'K' : n.toString();
  const costPerToken = 0.000003;
  const actualTokens = metrics?.tokens_processed || 0;
  const savedTokens = metrics?.tokens_saved || 0;
  const compressedTokens = actualTokens - savedTokens;
  const costSaved = savedTokens * costPerToken;

  return (
    <div>
      <PageTitle title="Usage" />
      <p className="text-[#9ca3af] text-sm mb-6">Local SAGE usage on this PC. All data stored locally in SQLite.</p>

      {/* 4-column stats grid */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-[#24283b] rounded-lg p-4 border border-[#333648] text-center">
          <div className="text-[#6b7280] text-xs mb-1">Actual Tokens</div>
          <div className="text-[#3b82f6] text-xl font-bold">{fmt(actualTokens)}</div>
          <div className="text-[#6b7280] text-[10px] mt-1">Total input tokens</div>
        </div>
        <div className="bg-[#24283b] rounded-lg p-4 border border-[#333648] text-center">
          <div className="text-[#6b7280] text-xs mb-1">Compressed To</div>
          <div className="text-[#8b5cf6] text-xl font-bold">{fmt(compressedTokens)}</div>
          <div className="text-[#6b7280] text-[10px] mt-1">After compression</div>
        </div>
        <div className="bg-[#24283b] rounded-lg p-4 border border-[#333648] text-center">
          <div className="text-[#6b7280] text-xs mb-1">Tokens Saved</div>
          <div className="text-[#4ade80] text-xl font-bold">{fmt(savedTokens)}</div>
          <div className="text-[#6b7280] text-[10px] mt-1">{metrics?.compression_pct || 0}% saved</div>
        </div>
        <div className="bg-[#24283b] rounded-lg p-4 border border-[#333648] text-center">
          <div className="text-[#6b7280] text-xs mb-1">Cost Saved</div>
          <div className="text-[#fbbf24] text-xl font-bold">${costSaved.toFixed(2)}</div>
          <div className="text-[#6b7280] text-[10px] mt-1">~$0.003/1K tokens</div>
        </div>
      </div>

      <Section title="Session Stats">
        <Card>
          <RowDisplay label="Total runs" value={metrics ? String(metrics.total_runs) : '...'} />
          <RowDisplay label="Compression rate" value={metrics ? `${metrics.compression_pct}%` : '...'} valueColor="#4ade80" />
        </Card>
      </Section>
    </div>
  );
}

function ProvidersPage({ wsRef, connected, settings, onChange }: { wsRef: React.RefObject<WebSocket | null>; connected: boolean; settings: GuiSettings; onChange: (patch: Partial<GuiSettings>) => void }) {
  const [providers, setProviders] = useState<any[]>([]);

  useEffect(() => {
    if (!connected || !wsRef.current) return;
    function handleMsg(event: MessageEvent) {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'provider.list.response') setProviders(msg.payload.providers || []);
      } catch {}
    }
    wsRef.current.addEventListener('message', handleMsg);
    wsRef.current.send(JSON.stringify({ type: 'provider.list', payload: {} }));
    return () => { wsRef.current?.removeEventListener('message', handleMsg); };
  }, [connected, wsRef]);

  return (
    <div>
      <PageTitle title="AI Providers" />
      <p className="text-[#9ca3af] text-sm mb-6">Auto-detected agents, manual fallback credentials, and API routing in one place.</p>
      <Section title="Detected Agents">
        <Card>
          {providers.length === 0 && <div className="text-[#6b7280] text-sm py-4 text-center">Scanning...</div>}
          {providers.map((p, i) => (
            <div key={p.id} className={`flex items-center justify-between py-3.5 ${i < providers.length - 1 ? 'border-b border-[#333648]' : ''}`}>
              <div className="flex items-center gap-3">
                <span className={`w-2.5 h-2.5 rounded-full ${p.status === 'connected' ? 'bg-[#4ade80]' : 'bg-[#4b5563]'}`} />
                <div>
                  <span className="text-[#ededec] text-sm">{p.name}</span>
                  <span className="text-[#6b7280] text-xs ml-2">{p.model}</span>
                </div>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${p.status === 'connected' ? 'bg-[#4ade80]/10 text-[#4ade80]' : 'bg-[#4b5563]/20 text-[#6b7280]'}`}>{p.status === 'connected' ? 'Connected' : 'Not found'}</span>
            </div>
          ))}
        </Card>
      </Section>
      <Section title="Routing">
        <Card>
          <ToggleRow label="Auto-route to cheapest capable agent" desc="When enabled, SAGE can pick the lowest-cost available provider for each message." checked={settings.api_travel} onChange={api_travel => onChange({ api_travel })} />
        </Card>
      </Section>
      <Section title="SAGE API">
        <Card>
          <RowInput label="API Key" placeholder="sk-sage-..." type="password" />
          <RowInput label="Endpoint" placeholder="sage.api.marketingstudios.in" defaultVal={settings.api_endpoint} />
          <RowDisplay label="Status" value="Connected" valueColor="#4ade80" />
        </Card>
      </Section>
      <Section title="Manual Fallback Credentials">
        <Card>
          <RowSelect label="Auth mode" desc="Used only when you bypass CLI agents or no CLI agent is available." options={['direct', 'bedrock', 'gateway']} value={settings.auth_mode} onChange={auth_mode => onChange({ auth_mode })} />
          {settings.auth_mode === 'direct' && (
            <div className="pt-1">
              <RowInput label="API Key" placeholder="sk-ant-..." type="password" fullWidth />
              <RowInput label="Base URL" placeholder="https://api.anthropic.com" fullWidth />
            </div>
          )}
          {settings.auth_mode === 'bedrock' && (
            <div className="pt-1">
              <RowInput label="Access Key" placeholder="AKIA..." fullWidth />
              <RowInput label="Secret Key" placeholder="..." type="password" fullWidth />
              <RowInput label="Region" placeholder="us-east-1" fullWidth />
              <RowInput label="Session Token" placeholder="(optional)" fullWidth />
            </div>
          )}
          {settings.auth_mode === 'gateway' && (
            <div className="pt-1">
              <RowInput label="Gateway URL" placeholder="https://gateway.example.com" fullWidth />
              <RowInput label="API Key" placeholder="..." type="password" fullWidth />
            </div>
          )}
        </Card>
      </Section>
      <Section title="API Travel Providers">
        <p className="text-[#6b7280] text-xs mb-2">Keys for cloud providers used by API Travel routing (all have permanent free tiers)</p>
        <Card>
          <RowInput label="Groq" placeholder="gsk_..." type="password" fullWidth />
          <RowInput label="Google Gemini" placeholder="AIza..." type="password" fullWidth />
          <RowInput label="OpenRouter" placeholder="sk-or-..." type="password" fullWidth />
        </Card>
      </Section>
      <Section title="Custom Binary Paths">
        <p className="text-[#6b7280] text-xs mb-2">Override auto-detection with custom paths</p>
        <Card>
          {providers.map(p => (
            <RowInput key={p.id} label={p.name} placeholder="auto-detect" />
          ))}
        </Card>
      </Section>
    </div>
  );
}

function APITravelPage() {
  const [authMode, setAuthMode] = useState('direct');
  return (
    <div>
      <PageTitle title="API & Travel" />
      <Section title="SAGE API">
        <Card>
          <RowInput label="API Key" placeholder="sk-sage-..." type="password" />
          <RowInput label="Endpoint" placeholder="sage.api.marketingstudios.in" defaultVal="sage.api.marketingstudios.in" />
          <RowDisplay label="Status" value="Connected" valueColor="#4ade80" />
        </Card>
      </Section>
      <Section title="API Travel">
        <Card>
          <ToggleRow label="Auto-route to cheapest agent" desc="Automatically routes requests to the most cost-effective provider" defaultOn={false} />
        </Card>
      </Section>
      <Section title="Agent Credentials">
        <Card>
          <div className="py-2">
            <label className="text-[#9ca3af] text-xs block mb-1.5">Auth Mode</label>
            <select value={authMode} onChange={e => setAuthMode(e.target.value)} className="settings-input w-full">
              <option value="direct">Direct API Key</option>
              <option value="bedrock">AWS Bedrock</option>
              <option value="gateway">Gateway / Proxy</option>
            </select>
          </div>
          {authMode === 'direct' && (
            <div className="space-y-2 mt-2 pt-2 border-t border-[#333648]">
              <RowInput label="API Key" placeholder="sk-ant-..." type="password" fullWidth />
              <RowInput label="Base URL" placeholder="https://api.anthropic.com" fullWidth />
            </div>
          )}
          {authMode === 'bedrock' && (
            <div className="space-y-2 mt-2 pt-2 border-t border-[#333648]">
              <RowInput label="Access Key" placeholder="AKIA..." fullWidth />
              <RowInput label="Secret Key" placeholder="..." type="password" fullWidth />
              <RowInput label="Region" placeholder="us-east-1" fullWidth />
              <RowInput label="Session Token" placeholder="(optional)" fullWidth />
            </div>
          )}
          {authMode === 'gateway' && (
            <div className="space-y-2 mt-2 pt-2 border-t border-[#333648]">
              <RowInput label="Gateway URL" placeholder="https://gateway.example.com" fullWidth />
              <RowInput label="API Key" placeholder="..." type="password" fullWidth />
            </div>
          )}
          <div className="flex gap-2 mt-3 pt-2 border-t border-[#333648]">
            <button className="bg-[#8b5cf6] hover:bg-[#7c3aed] text-white text-xs px-3 py-1.5 rounded-md transition-colors">Save & Apply</button>
            <button className="bg-[#24283b] hover:bg-[#333648] text-[#9ca3af] text-xs px-3 py-1.5 rounded-md transition-colors">Test Connection</button>
            <button className="text-[#f87171] text-xs px-3 py-1.5 rounded-md hover:bg-[#f87171]/10 transition-colors">Clear</button>
          </div>
        </Card>
      </Section>
    </div>
  );
}

function MCPPage() {
  return (
    <div>
      <PageTitle title="MCP Servers" />
      <Section title="Connected Servers">
        <Card>
          <div className="text-[#6b7280] text-sm py-4 text-center">No MCP servers configured</div>
        </Card>
        <button className="mt-3 bg-[#8b5cf6]/10 hover:bg-[#8b5cf6]/20 text-[#a78bfa] text-sm px-4 py-2 rounded-lg transition-colors">+ Add MCP Server</button>
      </Section>
    </div>
  );
}

function HooksPage() {
  return (
    <div>
      <PageTitle title="Hooks" />
      <p className="text-[#6b7280] text-xs mb-4">Shell commands that execute in response to events (tool calls, submissions, etc.)</p>
      <Section title="Configured Hooks">
        <Card>
          <div className="py-2.5 border-b border-[#333648]">
            <div className="flex items-center justify-between">
              <span className="text-[#ededec] text-sm">PreToolUse: enforce_sage.py</span>
              <span className="text-[#4ade80] text-xs">active</span>
            </div>
            <p className="text-[#6b7280] text-xs mt-0.5">Enforces SAGE routing for all shell commands</p>
          </div>
          <div className="py-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[#ededec] text-sm">PostToolUse: telemetry</span>
              <span className="text-[#4ade80] text-xs">active</span>
            </div>
            <p className="text-[#6b7280] text-xs mt-0.5">Records tool usage metrics</p>
          </div>
        </Card>
      </Section>
    </div>
  );
}

function ConnectionsPage() {
  return (
    <div>
      <PageTitle title="Connections" />
      <Section title="GitHub">
        <Card>
          <RowDisplay label="Account" value="PsYcGoD" />
          <RowInput label="Default remote" placeholder="origin" defaultVal="origin" />
        </Card>
      </Section>
      <Section title="SAGE Dashboard">
        <Card>
          <RowDisplay label="Endpoint" value="sage.api.marketingstudios.in" />
          <RowDisplay label="Status" value="Connected" valueColor="#4ade80" />
        </Card>
      </Section>
    </div>
  );
}

function GitPage() {
  return (
    <div>
      <PageTitle title="Git" />
      <Section title="Repository">
        <Card>
          <RowDisplay label="Current branch" value="main" />
          <RowDisplay label="Remote" value="origin → github.com/PsYcGoD/sage" />
          <RowDisplay label="User" value="PsYcGoD" />
        </Card>
      </Section>
      <Section title="Settings">
        <Card>
          <ToggleRow label="Auto-commit" desc="Automatically commit changes after successful edits" defaultOn={false} />
          <ToggleRow label="Show git changes" desc="Display branch and changes in status bar" defaultOn={true} />
        </Card>
      </Section>
    </div>
  );
}

function WorktreesPage() {
  return (
    <div>
      <PageTitle title="Worktrees" />
      <Section title="Active Worktrees">
        <Card>
          <div className="text-[#6b7280] text-sm py-4 text-center">No active worktrees</div>
        </Card>
        <p className="text-[#6b7280] text-xs mt-2">Worktrees are created automatically when agents need isolated file access.</p>
      </Section>
    </div>
  );
}

function VoicePage() {
  return (
    <div>
      <PageTitle title="Voice" />
      <Section title="Voice Input">
        <Card>
          <ToggleRow label="Enable voice input" desc="Use microphone to dictate messages to SAGE" defaultOn={false} />
          <RowSelect label="Input language" desc="Language for speech recognition" options={['English (US)', 'English (UK)', 'Hindi', 'Auto-detect']} defaultVal="English (US)" />
          <RowSelect label="Activation" desc="How to start voice input" options={['Push-to-talk (hold Space)', 'Toggle button', 'Always listening']} defaultVal="Push-to-talk (hold Space)" />
        </Card>
      </Section>
      <Section title="Voice Output">
        <Card>
          <ToggleRow label="Read responses aloud" desc="SAGE speaks responses using text-to-speech" defaultOn={false} />
          <RowSelect label="Voice" desc="Choose the TTS voice" options={['Alloy', 'Echo', 'Fable', 'Onyx', 'Nova', 'Shimmer']} defaultVal="Nova" />
          <RowSelect label="Speed" desc="Playback speed" options={['0.75x', '1x', '1.25x', '1.5x', '2x']} defaultVal="1x" />
        </Card>
      </Section>
      <Section title="Audio">
        <Card>
          <RowSelect label="Microphone" desc="Input device" options={['System default', 'Built-in Microphone']} defaultVal="System default" />
          <RowSelect label="Speaker" desc="Output device" options={['System default', 'Built-in Speakers']} defaultVal="System default" />
        </Card>
      </Section>
    </div>
  );
}

function PetsPage() {
  const [selectedPet, setSelectedPet] = useState('digambar');
  const pets = [
    { id: 'digambar', name: 'Digambar', emoji: '🐕‍🦺', desc: 'A lively robotic dog whose tiny bird antenna perches when calm and orbits around the dog during command-running animations.' },
    { id: 'fox', name: 'Fox', emoji: '🦊', desc: 'Curious and quick — reacts to your code explorations' },
    { id: 'cat', name: 'Cat', emoji: '🐱', desc: 'Calm and independent — celebrates passing tests quietly' },
    { id: 'owl', name: 'Owl', emoji: '🦉', desc: 'Wise — pays attention during debugging sessions' },
    { id: 'dragon', name: 'Dragon', emoji: '🐉', desc: 'Fierce — breathes fire when builds fail' },
    { id: 'robot', name: 'Robot', emoji: '🤖', desc: 'Logical — shows stats about your coding patterns' },
  ];

  return (
    <div>
      <PageTitle title="Pets" />
      <p className="text-[#9ca3af] text-sm mb-4">Choose a virtual coding companion that reacts to your activity.</p>
      <Section title="Your Pet">
        <Card>
          <ToggleRow label="Show pet" desc="Display your coding pet in the bottom-right corner" defaultOn={true} />
          <ToggleRow label="Pet animations" desc="Animate reactions to coding events" defaultOn={true} />
          <ToggleRow label="Pet sounds" desc="Play sound effects for pet reactions" defaultOn={false} />
        </Card>
      </Section>
      <Section title="Choose Pet">
        <div className="grid grid-cols-3 gap-2">
          {pets.map(pet => (
            <button
              key={pet.id}
              onClick={() => setSelectedPet(pet.id)}
              className={`p-3 rounded-lg border-2 text-center transition-colors ${
                selectedPet === pet.id ? 'border-[#8b5cf6] bg-[#8b5cf6]/10' : 'border-[#333648] hover:border-[#4b5563] bg-[#24283b]'
              }`}
            >
              <div className="text-3xl mb-1">{pet.emoji}</div>
              <div className="text-[#ededec] text-xs font-medium">{pet.name}</div>
            </button>
          ))}
        </div>
        <p className="text-[#6b7280] text-xs mt-2">{pets.find(p => p.id === selectedPet)?.desc}</p>
      </Section>
      <Section title="Pet Reactions">
        <Card>
          <ToggleRow label="Tests pass" desc="Pet celebrates when all tests pass" defaultOn={true} />
          <ToggleRow label="Build fails" desc="Pet reacts sadly when builds fail" defaultOn={true} />
          <ToggleRow label="New commit" desc="Pet acknowledges git commits" defaultOn={true} />
          <ToggleRow label="Long session" desc="Pet nudges you to take breaks" defaultOn={true} />
          <ToggleRow label="Idle" desc="Pet does idle animations when you're away" defaultOn={true} />
        </Card>
      </Section>
    </div>
  );
}

function PluginsPage() {
  const plugins = [
    { name: 'SAGE ML Predictor', version: '2.0.0', status: 'active', desc: 'Predicts command failures before execution' },
    { name: 'SAGE Compression', version: '2.0.0', status: 'active', desc: 'Context compression for AI interactions' },
    { name: 'SAGE Telemetry', version: '1.5.0', status: 'active', desc: 'Usage tracking and proof dashboard sync' },
    { name: 'SAGE Agents', version: '1.2.0', status: 'active', desc: 'Background code analysis agents' },
  ];

  return (
    <div>
      <PageTitle title="Plugins" />
      <p className="text-[#9ca3af] text-sm mb-4">Extend SAGE with plugins that add new capabilities.</p>
      <Section title="Installed Plugins">
        <Card>
          {plugins.map((p, i) => (
            <div key={p.name} className={`flex items-center justify-between py-3 ${i < plugins.length - 1 ? 'border-b border-[#333648]' : ''}`}>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[#ededec] text-sm">{p.name}</span>
                  <span className="text-[#6b7280] text-xs">v{p.version}</span>
                </div>
                <p className="text-[#6b7280] text-xs mt-0.5">{p.desc}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${p.status === 'active' ? 'bg-[#4ade80]/10 text-[#4ade80]' : 'bg-[#4b5563]/20 text-[#6b7280]'}`}>{p.status}</span>
            </div>
          ))}
        </Card>
      </Section>
      <Section title="Plugin Store">
        <button className="bg-[#8b5cf6]/10 hover:bg-[#8b5cf6]/20 text-[#a78bfa] text-sm px-4 py-2 rounded-lg transition-colors">Browse Plugins ↗</button>
      </Section>
    </div>
  );
}

function SkillsPage() {
  const skills = [
    { name: 'code-review', desc: 'Review diffs for correctness and simplification', trigger: '/code-review' },
    { name: 'deep-research', desc: 'Multi-source fact-checked research reports', trigger: '/deep-research' },
    { name: 'security-review', desc: 'Security audit of pending changes', trigger: '/security-review' },
    { name: 'simplify', desc: 'Review changed code for reuse and efficiency', trigger: '/simplify' },
    { name: 'verify', desc: 'End-to-end verification of code changes', trigger: '/verify' },
    { name: 'init', desc: 'Initialize CLAUDE.md documentation', trigger: '/init' },
    { name: 'review', desc: 'Review GitHub pull requests', trigger: '/review' },
    { name: 'run', desc: 'Launch and drive the app', trigger: '/run' },
  ];

  return (
    <div>
      <PageTitle title="Skills" />
      <p className="text-[#9ca3af] text-sm mb-4">Skills are specialized capabilities invoked with slash commands.</p>
      <Section title="Available Skills">
        <Card>
          {skills.map((s, i) => (
            <div key={s.name} className={`flex items-center justify-between py-2.5 ${i < skills.length - 1 ? 'border-b border-[#333648]' : ''}`}>
              <div>
                <span className="text-[#ededec] text-sm">{s.name}</span>
                <p className="text-[#6b7280] text-xs mt-0.5">{s.desc}</p>
              </div>
              <kbd className="bg-[#1a1b26] text-[#a78bfa] text-xs px-2 py-0.5 rounded border border-[#333648] font-mono">{s.trigger}</kbd>
            </div>
          ))}
        </Card>
      </Section>
      <Section title="Custom Skills">
        <Card>
          <div className="text-[#6b7280] text-sm py-3 text-center">No custom skills configured</div>
        </Card>
        <button className="mt-3 bg-[#8b5cf6]/10 hover:bg-[#8b5cf6]/20 text-[#a78bfa] text-sm px-4 py-2 rounded-lg transition-colors">+ Create Skill</button>
      </Section>
    </div>
  );
}

function EnvironmentPage() {
  return (
    <div>
      <PageTitle title="Environment" />
      <Section title="Runtime">
        <Card>
          <RowDisplay label="Python" value="3.13" />
          <RowDisplay label="Node.js" value="22.x" />
          <RowDisplay label="Platform" value="Windows 11 (win32 x64)" />
          <RowDisplay label="Shell" value="PowerShell" />
        </Card>
      </Section>
      <Section title="Environment Variables">
        <p className="text-[#6b7280] text-xs mb-2">Variables injected into SAGE command execution</p>
        <Card>
          <RowInput label="SAGE_DATA_DIR" placeholder="auto" fullWidth />
          <RowInput label="SAGE_LOG_LEVEL" placeholder="INFO" defaultVal="INFO" fullWidth />
          <RowInput label="ANTHROPIC_API_KEY" placeholder="sk-ant-..." type="password" fullWidth />
        </Card>
      </Section>
      <Section title="Sandbox">
        <Card>
          <RowSelect label="File access" desc="What SAGE can access on your filesystem" options={['Project only', 'Home directory', 'Full system']} defaultVal="Project only" />
          <RowSelect label="Network access" desc="Whether SAGE can make network requests" options={['Blocked', 'Allow listed', 'Full']} defaultVal="Full" />
          <ToggleRow label="Allow command execution" desc="Let SAGE run shell commands" defaultOn={true} />
        </Card>
      </Section>
    </div>
  );
}

function ArchivedChatsPage() {
  return (
    <div>
      <PageTitle title="Archived Chats" />
      <p className="text-[#9ca3af] text-sm mb-4">Conversations you've archived. They won't appear in your main chat list.</p>
      <Section title="Archives">
        <Card>
          <div className="text-[#6b7280] text-sm py-8 text-center">
            <p className="mb-2">No archived chats</p>
            <p className="text-xs">Right-click a chat in the sidebar → Archive to move it here</p>
          </div>
        </Card>
      </Section>
      <Section title="Storage">
        <Card>
          <RowDisplay label="Archived sessions" value="0" />
          <RowDisplay label="Total messages" value="0" />
          <div className="flex items-center justify-between py-2.5">
            <div>
              <span className="text-[#ededec] text-sm">Delete all archives</span>
              <p className="text-[#6b7280] text-xs mt-0.5">Permanently remove all archived chats</p>
            </div>
            <button className="text-[#f87171] text-xs px-3 py-1 rounded border border-[#f87171]/30 hover:bg-[#f87171]/10 transition-colors">Delete All</button>
          </div>
        </Card>
      </Section>
    </div>
  );
}

// ─── REUSABLE COMPONENTS ─────────────────────────────────────────────

function PageTitle({ title }: { title: string }) {
  return <span className="sr-only">{title}</span>;
}

function SummaryCard({ label, value, desc }: { label: string; value: string; desc: string }) {
  return (
    <div className="bg-[#1d2131] border border-[#303449] rounded-md p-4">
      <div className="text-[#7d8498] text-xs mb-2">{label}</div>
      <div className="text-[#ededec] text-sm font-medium mb-1">{value}</div>
      <div className="text-[#7d8498] text-xs leading-5">{desc}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <h2 className="text-[#ededec] text-sm font-semibold mb-3">{title}</h2>
      {children}
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return <div className="bg-[#1d2131] rounded-md px-5 py-1 border border-[#303449]">{children}</div>;
}

function RowSelect({ label, desc, options, defaultVal, value, onChange }: { label: string; desc?: string; options: string[]; defaultVal?: string; value?: string; onChange?: (value: string) => void }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_13rem] gap-6 items-center py-4 border-b border-[#303449] last:border-0">
      <div>
        <span className="text-[#ededec] text-sm font-medium">{label}</span>
        {desc && <p className="text-[#7d8498] text-xs mt-1 leading-5">{desc}</p>}
      </div>
      <select value={value} defaultValue={value === undefined ? defaultVal : undefined} onChange={e => onChange?.(e.target.value)} className="settings-input w-auto">
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

function RowInput({ label, placeholder, defaultVal, type, fullWidth }: { label: string; placeholder?: string; defaultVal?: string; type?: string; fullWidth?: boolean }) {
  return (
    <div className={`${fullWidth ? 'flex flex-col gap-2' : 'grid grid-cols-[minmax(0,1fr)_13rem] gap-6 items-center'} py-4 border-b border-[#303449] last:border-0`}>
      <span className="text-[#ededec] text-sm font-medium">{label}</span>
      <input type={type || 'text'} placeholder={placeholder} defaultValue={defaultVal} className={`settings-input ${fullWidth ? 'w-full' : ''}`} />
    </div>
  );
}

function RowDisplay({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_13rem] gap-6 items-center py-3 border-b border-[#303449] last:border-0">
      <span className="text-[#ededec] text-sm font-medium">{label}</span>
      <span className="text-sm" style={{ color: valueColor || '#9ca3af' }}>{value}</span>
    </div>
  );
}

function ToggleRow({ label, desc, defaultOn, checked, onChange }: { label: string; desc?: string; defaultOn?: boolean; checked?: boolean; onChange?: (checked: boolean) => void }) {
  const [localOn, setLocalOn] = useState(defaultOn ?? false);
  const on = checked ?? localOn;
  function toggle() {
    const next = !on;
    if (checked === undefined) setLocalOn(next);
    onChange?.(next);
  }
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_3rem] gap-6 items-center py-4 border-b border-[#303449] last:border-0">
      <div>
        <span className="text-[#ededec] text-sm font-medium">{label}</span>
        {desc && <p className="text-[#7d8498] text-xs mt-1 leading-5">{desc}</p>}
      </div>
      <button onClick={toggle} className={`w-10 h-[22px] rounded-full transition-colors relative flex-shrink-0 ${on ? 'bg-[#8b5cf6]' : 'bg-[#4b5563]'}`}>
        <div className={`w-4 h-4 bg-white rounded-full absolute top-[3px] transition-all ${on ? 'left-[21px]' : 'left-[3px]'}`} />
      </button>
    </div>
  );
}

function ToggleSwitch({ defaultOn }: { defaultOn: boolean }) {
  const [on, setOn] = useState(defaultOn);
  return (
    <button onClick={() => setOn(!on)} className={`w-10 h-[22px] rounded-full transition-colors relative flex-shrink-0 ${on ? 'bg-[#8b5cf6]' : 'bg-[#4b5563]'}`}>
      <div className={`w-4 h-4 bg-white rounded-full absolute top-[3px] transition-all ${on ? 'left-[21px]' : 'left-[3px]'}`} />
    </button>
  );
}
