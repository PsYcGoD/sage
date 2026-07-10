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
  const activeCount = streaming ? AGENTS.length : 0;
  const statusColor = streaming ? '#4ade80' : '#fb923c';
  const statusText = streaming ? `${AGENTS.length} active` : `${AGENTS.length} idle`;

  return (
    <div className="bg-[#16161e] border-b border-[#333648] px-4 py-2">
      <div className="flex items-center gap-3">
        <span className="text-[#9ca3af] text-xs">
          Agents ({AGENTS.length}) — <span style={{ color: statusColor }}>{statusText}</span>
        </span>
        <div className="flex items-center gap-2 flex-1 overflow-x-auto">
          {AGENTS.map(agent => (
            <div
              key={agent.name}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 flex-shrink-0 border ${
                streaming
                  ? 'bg-[#166534]/40 border-[#166534]'
                  : 'bg-[#78350f]/20 border-[#78350f]/40'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${streaming ? 'bg-[#4ade80]' : 'bg-[#fb923c]'}`} />
              <span className="text-[10px]">{agent.icon}</span>
              <span className="text-[#ededec] text-xs">{agent.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
