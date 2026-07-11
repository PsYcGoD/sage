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
  const statusColor = streaming ? '#4ade80' : '#fb923c';
  const statusText = streaming ? `${AGENTS.length} active` : `${AGENTS.length} idle`;

  return (
    <div className="bg-[#1f2335] border-b border-[#333648] px-5 py-3 mb-2">
      <div className="flex items-center gap-4">
        <span className="text-[#9ca3af] text-sm font-medium">
          Agents ({AGENTS.length}) — <span style={{ color: statusColor }}>{statusText}</span>
        </span>
        <div className="flex items-center gap-2.5 flex-1 overflow-x-auto">
          {AGENTS.map(agent => (
            <div
              key={agent.name}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 flex-shrink-0 border ${
                streaming
                  ? 'bg-[#166534]/40 border-[#166534]'
                  : 'bg-[#78350f]/20 border-[#78350f]/40'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${streaming ? 'bg-[#4ade80]' : 'bg-[#fb923c]'}`} />
              <span className="text-xs">{agent.icon}</span>
              <span className="text-[#ededec] text-sm">{agent.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
