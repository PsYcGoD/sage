const AGENTS = [
  { name: 'Code', icon: '⚙' },
  { name: 'Debug', icon: '🔧' },
  { name: 'Test', icon: '✓' },
  { name: 'Research', icon: '🔍' },
  { name: 'Security', icon: '🔒' },
  { name: 'Dependency', icon: '📦' },
  { name: 'Frontend', icon: '🎨' },
];

interface AgentStripProps {
  connected: boolean;
  streaming?: boolean;
}

export default function AgentStrip({ connected, streaming }: AgentStripProps) {
  const statusColor = streaming ? '#4ade80' : connected ? '#fb923c' : '#6b7280';
  const statusText = streaming ? '1 active' : connected ? 'idle' : 'offline';

  return (
    <div className="bg-[#1f2335] border-b border-[#333648] px-5 py-3 mb-2">
      <div className="flex items-center gap-4">
        <span className="text-[#9ca3af] text-sm font-medium">
          Agents — <span style={{ color: statusColor }}>{statusText}</span>
        </span>
        <div className="flex items-center gap-2.5 flex-1 overflow-x-auto">
          {AGENTS.map((agent, index) => {
            const active = Boolean(streaming && index === 0);
            const idle = Boolean(connected && !active);
            return (
            <div
              key={agent.name}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 flex-shrink-0 border ${
                active
                  ? 'bg-[#166534]/40 border-[#166534]'
                  : idle
                    ? 'bg-[#78350f]/20 border-[#78350f]/40'
                    : 'bg-[#24283b] border-[#333648]'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${active ? 'bg-[#4ade80]' : idle ? 'bg-[#fb923c]' : 'bg-[#6b7280]'}`} />
              <span className="text-xs">{agent.icon}</span>
              <span className="text-[#ededec] text-sm">{agent.name}</span>
            </div>
          )})}
        </div>
      </div>
    </div>
  );
}
