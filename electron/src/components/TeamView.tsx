import { useState, useEffect } from 'react';

interface TeamMember {
  installation_id: string;
  hostname: string;
  platform: string;
  first_seen: string;
  last_seen: string;
  run_count: number;
  saved_tokens: number;
  estimated_savings_usd: number;
}

interface TeamData {
  workspace_hash?: string;
  members: TeamMember[];
  aggregate: {
    total_members: number;
    total_runs: number;
    saved_tokens: number;
    estimated_savings_usd: number;
  };
}

export default function TeamView({ wsRef, onBack }: { wsRef: React.RefObject<WebSocket | null>; onBack: () => void }) {
  const [team, setTeam] = useState<TeamData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type !== 'team.get.response') return;
        if (msg.payload?.ok && msg.payload.team) {
          setTeam(msg.payload.team);
          setError('');
        } else {
          setError(msg.payload?.error || 'No team data');
        }
        setLoading(false);
      } catch (e: any) {
        setError(e.message || 'Failed to parse team data');
        setLoading(false);
      }
    }
    wsRef.current?.addEventListener('message', handleMessage);
    fetchTeam();
    const interval = setInterval(fetchTeam, 30000);
    return () => {
      clearInterval(interval);
      wsRef.current?.removeEventListener('message', handleMessage);
    };
  }, [wsRef]);

  async function fetchTeam() {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setError('SAGE backend is not connected yet.');
      setLoading(false);
      return;
    }
    ws.send(JSON.stringify({ type: 'team.get', payload: {} }));
  }

  function timeAgo(iso: string): string {
    if (!iso) return 'never';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-[#6b7280] text-sm animate-pulse">Loading team data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 p-6">
        <Header onBack={onBack} />
        <div className="bg-[#1e2030] rounded-lg p-6 border border-[#333648]">
          <p className="text-[#9ca3af] text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!team || team.members.length === 0) {
    return (
      <div className="flex-1 p-6">
        <Header onBack={onBack} />
        <div className="bg-[#1e2030] rounded-lg p-6 border border-[#333648] text-center">
          <p className="text-[#9ca3af] text-sm mb-2">No team members found.</p>
          <p className="text-[#6b7280] text-xs">Team view shows all installations sharing the same workspace. Set a workspace_hash on your API key to group machines.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <Header onBack={onBack} />

      {/* Aggregate stats */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Members" value={team.aggregate.total_members} />
        <StatCard label="Total Runs" value={team.aggregate.total_runs.toLocaleString()} />
        <StatCard label="Tokens Saved" value={formatTokens(team.aggregate.saved_tokens)} />
        <StatCard label="Est. Savings" value={`$${team.aggregate.estimated_savings_usd.toFixed(2)}`} accent />
      </div>

      {/* Member roster */}
      <div className="bg-[#1e2030] rounded-lg border border-[#333648] overflow-hidden">
        <div className="grid grid-cols-[1fr_1fr_80px_100px_80px] gap-2 px-4 py-2.5 border-b border-[#333648] text-[#6b7280] text-xs font-medium">
          <span>Host</span>
          <span>Platform</span>
          <span>Runs</span>
          <span>Saved</span>
          <span>Last seen</span>
        </div>
        {team.members.map((m) => (
          <div key={m.installation_id} className="grid grid-cols-[1fr_1fr_80px_100px_80px] gap-2 px-4 py-3 border-b border-[#333648]/50 hover:bg-[#262940] transition-colors">
            <span className="text-[#ededec] text-sm truncate">{m.hostname}</span>
            <span className="text-[#9ca3af] text-sm truncate">{m.platform}</span>
            <span className="text-[#9ca3af] text-sm">{m.run_count}</span>
            <span className="text-[#4ade80] text-sm">${m.estimated_savings_usd.toFixed(2)}</span>
            <span className="text-[#6b7280] text-xs">{timeAgo(m.last_seen)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Header({ onBack }: { onBack: () => void }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h2 className="text-[#ededec] text-lg font-semibold">Team</h2>
        <p className="text-[#6b7280] text-xs mt-1">Local enterprise readiness view. Cloud workspace grouping is on the TODO.</p>
      </div>
      <button onClick={onBack} className="text-[#9ca3af] hover:text-white text-sm px-3 py-1.5 rounded-md border border-[#333648] hover:bg-[#24283b] transition-colors active:scale-[0.97]">
        Back to chat
      </button>
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="bg-[#1e2030] rounded-lg border border-[#333648] p-4">
      <div className="text-[#6b7280] text-xs mb-1">{label}</div>
      <div className={`text-lg font-semibold ${accent ? 'text-[#4ade80]' : 'text-[#ededec]'}`}>{value}</div>
    </div>
  );
}

function formatTokens(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
