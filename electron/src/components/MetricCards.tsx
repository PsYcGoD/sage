import { useState, useEffect, useRef } from 'react';

interface MetricCardsProps {
  connected: boolean;
  wsRef: React.RefObject<WebSocket | null>;
}

interface Metrics {
  total_runs: number;
  tokens_processed: number;
  tokens_saved: number;
  compression_pct: number;
  successful_runs?: number;
  failed_runs?: number;
  running_agents?: number;
  waiting_agents?: number;
}

export default function MetricCards({ connected, wsRef }: MetricCardsProps) {
  const [metrics, setMetrics] = useState<Metrics>({ total_runs: 0, tokens_processed: 0, tokens_saved: 0, compression_pct: 0 });
  const [sessionRuns, setSessionRuns] = useState(0);
  const baselineRef = useRef<Metrics | null>(null);

  useEffect(() => {
    if (!connected || !wsRef.current) return;

    function handleMsg(event: MessageEvent) {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'metrics.get.response') {
          const m = msg.payload as Metrics;
          if (!baselineRef.current) baselineRef.current = { ...m };
          setMetrics(m);
        }
        if (msg.type === 'chat.stream.done') {
          setSessionRuns(p => p + 1);
        }
      } catch {}
    }

    const ws = wsRef.current;
    ws.addEventListener('message', handleMsg);
    ws.send(JSON.stringify({ type: 'metrics.get', payload: {} }));

    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'metrics.get', payload: {} }));
      }
    }, 3000);

    return () => {
      ws.removeEventListener('message', handleMsg);
      clearInterval(interval);
    };
  }, [connected, wsRef]);

  const fmt = (n: number) => n >= 1_000_000 ? (n/1_000_000).toFixed(1)+'M' : n >= 1_000 ? (n/1_000).toFixed(0)+'K' : n.toString();

  const savedTokens = metrics.tokens_saved;
  const usedTokens = metrics.tokens_processed - savedTokens;
  const totalRuns = metrics.total_runs;

  // Session delta from baseline
  const baseline = baselineRef.current || metrics;
  const sessionTokensSaved = metrics.tokens_saved - baseline.tokens_saved;
  const sessionTokensUsed = (metrics.tokens_processed - metrics.tokens_saved) - (baseline.tokens_processed - baseline.tokens_saved);
  const sessionPct = sessionTokensSaved > 0 && (sessionTokensUsed + sessionTokensSaved) > 0
    ? Math.round(sessionTokensSaved / (sessionTokensUsed + sessionTokensSaved) * 100) : 0;

  const successCount = metrics.successful_runs ?? 0;
  const failedCount = metrics.failed_runs ?? Math.max(0, totalRuns - successCount);
  const successRate = totalRuns > 0 ? ((successCount / totalRuns) * 100).toFixed(0) : '0';
  const sessionSuccessRate = sessionRuns > 0 ? '—' : '—';

  return (
    <div className="w-64 bg-[#16161e] border-l border-[#333648] flex flex-col p-3 gap-3 overflow-y-auto">
      <h3 className="text-[#4ade80] text-xs font-semibold uppercase tracking-wider">Live Metrics</h3>

      <MetricCard title="Commands">
        <Row left={fmt(totalRuns)} leftSub="Runs" right={String(sessionRuns)} rightSub="Runs" />
      </MetricCard>

      <MetricCard title="Context Tokens">
        <Row
          left={`${fmt(usedTokens)} / ${fmt(savedTokens)}`} leftSub="Used / saved"
          right={`${fmt(sessionTokensUsed)} / ${fmt(sessionTokensSaved)}`} rightSub={`${sessionPct}% saved this session`}
        />
      </MetricCard>

      <MetricCard title="Agents">
        <Row left={String(metrics.running_agents ?? 0)} leftSub="Running" right={String(metrics.waiting_agents ?? 0)} rightSub="Waiting" leftColor="#fb923c" />
      </MetricCard>

      <MetricCard title="Success">
        <Row left={`${successRate}%`} leftSub={`${successCount}/${totalRuns}`} right={String(failedCount)} rightSub="Failed" leftColor="#4ade80" rightColor="#f87171" />
      </MetricCard>
    </div>
  );
}

function MetricCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#1f2335] rounded-lg p-3 border border-[#333648] min-w-0">
      <div className="text-[#9ca3af] text-[10px] font-medium uppercase tracking-wider mb-2 truncate">{title}</div>
      {children}
    </div>
  );
}

function Row({ left, leftSub, right, rightSub, leftColor, rightColor }: {
  left: string; leftSub: string; right: string; rightSub: string; leftColor?: string; rightColor?: string;
}) {
  return (
    <div className="grid grid-cols-2 gap-2 min-w-0">
      <div className="min-w-0">
        <div className="text-base font-bold leading-tight truncate" style={{ color: leftColor || 'white' }} title={left}>{left}</div>
        <div className="text-[#6b7280] text-[10px] truncate" title={leftSub}>{leftSub}</div>
      </div>
      <div className="text-right min-w-0">
        <div className="text-base font-bold leading-tight truncate" style={{ color: rightColor || 'white' }} title={right}>{right}</div>
        <div className="text-[#6b7280] text-[10px] truncate" title={rightSub}>{rightSub}</div>
      </div>
    </div>
  );
}
