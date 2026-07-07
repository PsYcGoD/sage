// Restrict browser access to the dashboard and local SAGE UI.
const ALLOWED_ORIGINS = [
  "http://localhost:8765",           // SAGE GUI local
  "http://127.0.0.1:8765",           // Alternative localhost
  "https://sage.api.marketingstudios.in",  // Public dashboard
  "https://sage-api.pascoaldsouza28.workers.dev", // Workers.dev fallback
];

const MODEL_SAVINGS_PROFILES = [
  { model: "claude-sonnet", label: "Claude Sonnet", provider: "Anthropic", input_rate_per_million: 3.0 },
  { model: "codex", label: "OpenAI Codex", provider: "OpenAI", input_rate_per_million: 1.5 },
  { model: "gemini-pro", label: "Gemini 2.5 Pro", provider: "Google", input_rate_per_million: 1.25 },
];

const AGENT_SAVINGS_PROFILES = [
  { agent: "claude-cli", label: "Claude CLI", provider: "Anthropic", model: "Claude Sonnet", input_rate_per_million: 3.0 },
  { agent: "codex-cli", label: "Codex CLI", provider: "OpenAI", model: "OpenAI Codex", input_rate_per_million: 1.5 },
  { agent: "sage-desktop", label: "SAGE Desktop", provider: "SAGE", model: "Desktop app", input_rate_per_million: 0.0 },
  { agent: "claude-code", label: "Claude Code", provider: "Anthropic", model: "Claude Sonnet", input_rate_per_million: 3.0 },
  { agent: "opencode", label: "OpenCode", provider: "OpenCode", model: "Claude Sonnet", input_rate_per_million: 3.0 },
  { agent: "cursor", label: "Cursor", provider: "Cursor", model: "OpenAI Codex", input_rate_per_million: 1.5 },
  { agent: "windsurf", label: "Windsurf", provider: "Codeium", model: "Claude Sonnet", input_rate_per_million: 3.0 },
  { agent: "aider", label: "Aider", provider: "Aider", model: "Claude Sonnet", input_rate_per_million: 3.0 },
  { agent: "copilot", label: "GitHub Copilot coding agent", provider: "GitHub", model: "GitHub Copilot", input_rate_per_million: 0.0 },
];

function getCorsHeaders(origin) {
  const allowedOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : "null";
  return {
    "Access-Control-Allow-Origin": allowedOrigin,
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-SAGE-Idempotency-Key,X-SAGE-Timestamp",
  };
}

// Embedded public proof dashboard HTML
const PUBLIC_PROOF_DASHBOARD_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SAGE Public Proof - Live Token Compression Statistics</title>
  <meta name="description" content="Live public proof for SAGE token compression, ML prediction, and AI agent orchestration.">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh;
      padding: 24px;
      color: #f8fafc;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 20% 10%, rgba(16,185,129,.18), transparent 26%),
        radial-gradient(circle at 80% 0%, rgba(99,102,241,.22), transparent 28%),
        linear-gradient(135deg, #0f172a 0%, #111827 48%, #0b1120 100%);
    }
    .container { max-width: 1280px; margin: 0 auto; }
    header {
      padding: 34px 28px;
      margin-bottom: 28px;
      border: 1px solid rgba(148,163,184,.22);
      border-radius: 18px;
      background: rgba(15,23,42,.72);
      box-shadow: 0 24px 80px rgba(2,6,23,.35);
    }
    h1 { font-size: clamp(2.2rem, 5vw, 4.4rem); line-height: 1; margin-bottom: 14px; }
    .subtitle { color: #cbd5e1; font-size: 1.12rem; line-height: 1.6; max-width: 900px; }
    .badges { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }
    .badge {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 9px 13px;
      border-radius: 999px;
      color: #dbeafe;
      background: rgba(37,99,235,.18);
      border: 1px solid rgba(96,165,250,.34);
      text-decoration: none;
      font-weight: 700;
    }
    .badge.green { color: #bbf7d0; background: rgba(22,163,74,.16); border-color: rgba(74,222,128,.35); }
    .owner { margin-top: 18px; color: #c4b5fd; font-weight: 800; }
    .hero-stats {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .card, .panel {
      border: 1px solid rgba(148,163,184,.18);
      border-radius: 16px;
      background: rgba(15,23,42,.68);
      box-shadow: 0 18px 50px rgba(2,6,23,.22);
    }
    .card { padding: 24px; min-height: 150px; }
    .label { color: #94a3b8; text-transform: uppercase; font-size: .8rem; font-weight: 800; letter-spacing: .08em; }
    .value { margin-top: 12px; font-size: clamp(2rem, 4vw, 3.5rem); font-weight: 900; color: #a7f3d0; }
    .sub { margin-top: 8px; color: #cbd5e1; }
    .panel { padding: 28px; margin-bottom: 24px; }
    .panel h2 { font-size: 1.55rem; margin-bottom: 18px; }
    .bar-wrap { height: 54px; border-radius: 999px; overflow: hidden; background: rgba(2,6,23,.64); border: 1px solid rgba(148,163,184,.2); }
    .bar { height: 100%; width: 0%; min-width: 72px; display: flex; align-items: center; justify-content: flex-end; padding-right: 18px; font-weight: 900; background: linear-gradient(90deg, #10b981, #22c55e); transition: width .6s ease; }
    .bar-labels { display: flex; justify-content: space-between; gap: 12px; margin-top: 14px; color: #cbd5e1; flex-wrap: wrap; }
    .prediction-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    .mini { padding: 18px; border-radius: 12px; background: rgba(2,6,23,.35); border: 1px solid rgba(148,163,184,.15); }
    .agent-savings {
      margin-top: 20px;
      border: 1px solid rgba(148,163,184,.18);
      border-radius: 12px;
      overflow: hidden;
      background: rgba(2,6,23,.22);
    }
    .agent-savings summary {
      list-style: none;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 58px;
      padding: 0 16px;
      cursor: pointer;
      color: #dbeafe;
      font-weight: 900;
    }
    .agent-savings summary::-webkit-details-marker { display: none; }
    .agent-savings summary::after {
      content: "v";
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      flex: 0 0 auto;
      border-radius: 999px;
      color: #a7f3d0;
      background: rgba(15,23,42,.82);
      border: 1px solid rgba(148,163,184,.22);
      transition: transform .16s ease;
    }
    .agent-savings[open] summary::after { transform: rotate(180deg); }
    .agent-savings summary:focus-visible { outline: 2px solid #60a5fa; outline-offset: -2px; }
    .savings-table { width: 100%; border-collapse: collapse; overflow: hidden; }
    .model-savings-table { margin-top: 18px; }
    .savings-table th, .savings-table td { padding: 14px; border-bottom: 1px solid rgba(148,163,184,.16); text-align: left; }
    .savings-table th { color: #94a3b8; text-transform: uppercase; font-size: .76rem; letter-spacing: .08em; }
    .savings-table td:last-child, .savings-table th:last-child { text-align: right; }
    .savings-table tr:last-child td { border-bottom: 0; }
    .ascii {
      margin: 22px 0 16px;
      padding: 18px;
      overflow-x: auto;
      white-space: pre;
      color: #86efac;
      line-height: 1.15;
      font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
      background: rgba(2,6,23,.42);
      border-radius: 12px;
      border: 1px solid rgba(34,197,94,.24);
    }
    .description { color: #dbeafe; line-height: 1.75; font-size: 1.03rem; }
    .refresh { text-align: center; color: #94a3b8; margin: 28px 0; }
    button {
      cursor: pointer;
      border: 0;
      border-radius: 999px;
      padding: 12px 22px;
      color: #fff;
      background: linear-gradient(135deg, #2563eb, #7c3aed);
      font-weight: 800;
      margin-bottom: 12px;
    }
    .error { padding: 18px; border-radius: 14px; background: rgba(127,29,29,.35); border: 1px solid rgba(248,113,113,.45); }
    footer { text-align: center; color: #94a3b8; line-height: 1.7; padding: 22px 0; }
    footer a { color: #a5b4fc; text-decoration: none; font-weight: 800; }
    @media (max-width: 1180px) { .hero-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
    @media (max-width: 980px) { .hero-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 620px) { body { padding: 14px; } .hero-stats, .prediction-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>&#129504; S.A.G.E Public Proof</h1>
      <p class="subtitle">Live proof of token savings, context compression, ML prediction, and active AI agent orchestration from S.A.G.E - Smart Agent Guidance Engine.</p>
      <div class="badges">
        <span class="badge green">&#9679; Live Data</span>
        <span class="badge">Verified Aggregate Proof</span>
        <a class="badge" href="https://github.com/PsYcGoD/sage">GitHub Repository</a>
      </div>
      <div class="owner">Built by PsYc+GoD AI &amp; ML</div>
    </header>

    <main id="dashboard-content" style="display:none">
      <section class="hero-stats">
        <div class="card"><div class="label">Total Runs</div><div class="value" id="total-runs">-</div><div class="sub">Commands executed</div></div>
        <div class="card"><div class="label">Tokens Saved</div><div class="value" id="tokens-saved">-</div><div class="sub" id="tokens-processed-label">-</div></div>
        <div class="card"><div class="label">Estimated Savings</div><div class="value" id="estimated-savings">-</div><div class="sub">Reference terminal-context savings</div></div>
        <div class="card"><div class="label">Compression Rate</div><div class="value" id="compression-rate">-</div><div class="sub">Average across all runs</div></div>
        <div class="card"><div class="label">Success Rate</div><div class="value" id="success-rate">-</div><div class="sub" id="success-label">-</div></div>
      </section>

      <section class="panel">
        <h2>🤖 Agent & ML Activity</h2>
        <div class="hero-stats" style="grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 0;">
          <div class="card" style="min-height: 130px;"><div class="label">Total Agents</div><div class="value" id="total-agents" style="font-size: 2.5rem;">-</div><div class="sub">Active agent types</div></div>
          <div class="card" style="min-height: 130px;"><div class="label">Agent Runs</div><div class="value" id="agent-runs" style="font-size: 2.5rem;">-</div><div class="sub">Total completions</div></div>
          <div class="card" style="min-height: 130px;"><div class="label">ML Examples</div><div class="value" id="ml-examples" style="font-size: 2.5rem;">-</div><div class="sub">Training dataset</div></div>
          <div class="card" style="min-height: 130px;"><div class="label">Quality Metrics</div><div class="value" id="quality-metrics" style="font-size: 2.5rem;">-</div><div class="sub">Tracked signals</div></div>
        </div>
        <p class="description" style="margin-top: 20px; font-size: 0.95rem;">
          SAGE uses <strong>10+ specialized AI agents</strong> (Security, Code, Debug, Test, Dependency, Research, Frontend, Performance, Workflow, Red Team) 
          that analyze every command in real-time. The ML system continuously learns from your command patterns to optimize compression strategies and predict failures.
        </p>
      </section>

      <section class="panel">
        <h2>&#128200; Compression Performance</h2>
        <div class="bar-wrap"><div class="bar" id="compression-bar">0%</div></div>
        <div class="bar-labels">
          <span>Original: <strong id="original-tokens">-</strong> tokens</span>
          <span>Compressed: <strong id="compressed-tokens">-</strong> tokens</span>
        </div>
        <table class="savings-table model-savings-table" aria-label="Estimated savings by model">
          <thead>
            <tr><th>Model/provider</th><th>Reference input rate</th><th>Estimated saved</th></tr>
          </thead>
          <tbody id="model-savings-rows">
            <tr><td colspan="3">Loading model savings...</td></tr>
          </tbody>
        </table>
        <details class="agent-savings">
          <summary>Money Saved by each AI Agent</summary>
          <table class="savings-table" aria-label="Estimated savings by AI agent">
            <thead>
              <tr><th>AI agent/provider</th><th>Model used</th><th>Estimated saved</th></tr>
            </thead>
            <tbody id="agent-savings-rows">
              <tr><td colspan="3">Loading aggregate savings...</td></tr>
            </tbody>
          </table>
        </details>
      </section>

      <section class="panel">
        <h2>&#127919; ML Prediction Performance</h2>
        <div class="prediction-grid">
          <div class="mini"><div class="label">Events with Prediction</div><div class="value" id="events-predicted">-</div><div class="sub">Commands analyzed</div></div>
          <div class="mini"><div class="label">Avg Prediction Score</div><div class="value" id="avg-prediction">-</div><div class="sub">Confidence level</div></div>
        </div>
        <pre class="ascii"> SSSSS    AAAAA    GGGGG    EEEEE
 S        A   A    G        E
 SSSSS    AAAAA    G  GG    EEEE
     S    A   A    G   G    E
 SSSSS    A   A    GGGGG    EEEEE</pre>
        <p class="description">
          <strong>S.A.G.E - Smart Agent Guidance Engine</strong> is a local-first AI development orchestration layer.
          It tracks command runs, compresses noisy terminal output into useful context, records proof-grade token savings,
          coordinates active AI agents, and builds ML signals for predicting failures before they waste time and credits.
          This public dashboard shows safe aggregate counters only: no raw command text, file content, private paths, or model output is exposed.
        </p>
      </section>

      <div class="refresh">
        <div>Auto-refreshes every 10 seconds. Last updated: <strong id="last-updated">-</strong></div>
      </div>
    </main>

    <div id="loading-state" class="panel">Loading live SAGE proof data...</div>
    <div id="error-state" style="display:none"></div>
    <footer>
      <strong>S.A.G.E V2.0</strong> - Smart Agent Guidance Engine<br>
      Privacy-first token compression, ML prediction, and active AI agent orchestration by PsYc+GoD AI &amp; ML<br>
      <a href="https://github.com/PsYcGoD/sage">GitHub Repository</a>
    </footer>
  </div>

  <script>
    const API_ENDPOINT = window.location.origin + "/v1/proof";
    function formatNumber(num) {
      num = Number(num || 0);
      if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
      if (num >= 1000) return (num / 1000).toFixed(1) + "K";
      return num.toLocaleString();
    }
    function formatCurrency(num) {
      return "$" + Number(num || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    function renderModelSavings(rows) {
      const body = document.getElementById("model-savings-rows");
      const safeRows = Array.isArray(rows) ? rows : [];
      if (!safeRows.length) {
        body.innerHTML = '<tr><td colspan="3">No aggregate savings yet.</td></tr>';
        return;
      }
      body.innerHTML = safeRows.map((row) => {
        const label = String(row.label || row.model || "Unknown").replace(/[<>&"]/g, "");
        const provider = String(row.provider || "").replace(/[<>&"]/g, "");
        const rate = Number(row.input_rate_per_million || 0).toFixed(2);
        return '<tr><td><strong>' + label + '</strong><div class="sub">' + provider + '</div></td><td>$' + rate + '/M tokens</td><td><strong>' + formatCurrency(row.estimated_savings_usd) + '</strong></td></tr>';
      }).join("");
    }
    function renderAgentSavings(rows) {
      const body = document.getElementById("agent-savings-rows");
      const safeRows = Array.isArray(rows) ? rows : [];
      if (!safeRows.length) {
        body.innerHTML = '<tr><td colspan="3">No AI agent usage yet.</td></tr>';
        return;
      }
      body.innerHTML = safeRows.map((row) => {
        const label = String(row.label || row.agent || "Unknown").replace(/[<>&"]/g, "");
        const provider = String(row.provider || "").replace(/[<>&"]/g, "");
        const model = String(row.model || "Not used yet").replace(/[<>&"]/g, "");
        const tokens = Number(row.saved_tokens || 0);
        return '<tr><td><strong>' + label + '</strong><div class="sub">' + provider + '</div></td><td><strong>' + model + '</strong><div class="sub">' + formatNumber(tokens) + ' tokens saved</div></td><td><strong>' + formatCurrency(row.estimated_savings_usd) + '</strong></td></tr>';
      }).join("");
    }
    async function loadProofData() {
      const loading = document.getElementById("loading-state");
      const error = document.getElementById("error-state");
      const content = document.getElementById("dashboard-content");
      try {
        loading.style.display = "block";
        error.style.display = "none";
        const response = await fetch(API_ENDPOINT, { cache: "no-store" });
        if (!response.ok) throw new Error("HTTP " + response.status + ": " + response.statusText);
        const data = await response.json();
        if (!data.ok) throw new Error("API returned an error response");
        const totals = data.totals || {};
        document.getElementById("total-runs").textContent = Number(totals.total_runs || 0).toLocaleString();
        document.getElementById("tokens-saved").textContent = formatNumber(totals.tokens_saved);
        document.getElementById("estimated-savings").textContent = formatCurrency(totals.estimated_savings_usd);
        document.getElementById("tokens-processed-label").textContent = formatNumber(totals.tokens_processed) + " processed";
        document.getElementById("compression-rate").textContent = Number(totals.compression_percent || 0).toFixed(1) + "%";
        document.getElementById("success-rate").textContent = Number(totals.success_rate || 0).toFixed(1) + "%";
        document.getElementById("success-label").textContent = Number(totals.successful_runs || 0).toLocaleString() + "/" + Number(totals.total_runs || 0).toLocaleString() + " successful";
        document.getElementById("original-tokens").textContent = formatNumber(totals.tokens_processed);
        document.getElementById("compressed-tokens").textContent = formatNumber(totals.tokens_compressed);
        renderModelSavings(totals.savings_by_model || totals.savings_by_agent);
        renderAgentSavings(totals.savings_by_agent);
        const bar = document.getElementById("compression-bar");
        const pct = Math.max(0, Math.min(100, Number(totals.compression_percent || 0)));
        bar.style.width = pct + "%";
        bar.textContent = pct.toFixed(1) + "%";
        const pred = totals.failure_prediction_stats || {};
        document.getElementById("events-predicted").textContent = Number(pred.events_with_prediction || 0).toLocaleString();
        document.getElementById("avg-prediction").textContent = (Number(pred.avg_prediction_score || 0) * 100).toFixed(1) + "%";
        
        // Load ML and agent stats
        document.getElementById("total-agents").textContent = Number(totals.total_agents || 0).toLocaleString();
        document.getElementById("agent-runs").textContent = Number(totals.agent_runs_completed || 0).toLocaleString();
        document.getElementById("ml-examples").textContent = Number(totals.ml_training_examples || 0).toLocaleString();
        document.getElementById("quality-metrics").textContent = Number(totals.agent_quality_metrics || 0).toLocaleString();
        
        document.getElementById("last-updated").textContent = new Date(data.generated_at).toLocaleString();
        loading.style.display = "none";
        content.style.display = "block";
      } catch (exc) {
        loading.style.display = "none";
        content.style.display = "none";
        error.style.display = "block";
        error.innerHTML = '<div class="error"><strong>Failed to load data.</strong><br>' + String(exc.message || exc) + '<br><br><button onclick="loadProofData()">Retry</button></div>';
      }
    }
    loadProofData();
    setInterval(loadProofData, 10000);
  </script>
</body>
</html>`;


function json(payload, status = 200, origin = null) {
  const corsHeaders = origin ? getCorsHeaders(origin) : {};
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...corsHeaders,
    },
  });
}

function error(message, status = 500, detail = "") {
  return json({ ok: false, error: message, detail }, status);
}

function nowIso() {
  return new Date().toISOString();
}

function randomHex(bytes = 16) {
  const data = new Uint8Array(bytes);
  crypto.getRandomValues(data);
  return Array.from(data, (item) => item.toString(16).padStart(2, "0")).join("");
}

function newId(prefix) {
  return `${prefix}_${randomHex(16)}`;
}

async function sha256(text) {
  const bytes = new TextEncoder().encode(String(text || ""));
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), (item) => item.toString(16).padStart(2, "0")).join("");
}

async function readJson(request) {
  const text = await request.text();
  if (!text.trim()) return {};
  return JSON.parse(text);
}

function textValue(value, maxLength = 200) {
  if (value === null || value === undefined) return "";
  return String(value).slice(0, maxLength);
}

function clampInt(value, min, max, fallback = 0) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, parsed));
}

function numberValue(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function roundMoney(value) {
  return Number(Math.max(0, numberValue(value, 0)).toFixed(4));
}

function buildSavingsByModel(savedTokens) {
  const saved = clampInt(savedTokens, 0, 2147483647, 0);
  return MODEL_SAVINGS_PROFILES.map((profile) => ({
    model: profile.model,
    label: profile.label,
    provider: profile.provider,
    saved_tokens: saved,
    input_rate_per_million: profile.input_rate_per_million,
    estimated_savings_usd: roundMoney((saved / 1000000) * profile.input_rate_per_million),
  }));
}

function buildSavingsByAgent(usageByAgent = {}) {
  return AGENT_SAVINGS_PROFILES.map((profile) => ({
    agent: profile.agent,
    label: profile.label,
    provider: profile.provider,
    model: profile.model,
    saved_tokens: clampInt(usageByAgent[profile.agent], 0, 2147483647, 0),
    input_rate_per_million: profile.input_rate_per_million,
    estimated_savings_usd: roundMoney((clampInt(usageByAgent[profile.agent], 0, 2147483647, 0) / 1000000) * profile.input_rate_per_million),
  }));
}

function sanitizeSavingsByModel(rows, savedTokens) {
  const fallback = buildSavingsByModel(savedTokens);
  if (!Array.isArray(rows) || rows.length === 0) return fallback;
  const sanitized = rows.slice(0, 16).map((row) => {
    const saved = clampInt(row?.saved_tokens, 0, 2147483647, savedTokens);
    const inputRate = roundMoney(row?.input_rate_per_million);
    return {
      model: textValue(row?.model || row?.agent, 80),
      label: textValue(row?.label, 120),
      provider: textValue(row?.provider, 80),
      saved_tokens: saved,
      input_rate_per_million: inputRate,
      estimated_savings_usd: row?.estimated_savings_usd === undefined
        ? roundMoney((saved / 1000000) * inputRate)
        : roundMoney(row?.estimated_savings_usd),
    };
  }).filter((row) => row.model || row.label);
  return sanitized.length ? sanitized : fallback;
}

function sanitizeSavingsByAgent(rows) {
  const fallback = buildSavingsByAgent();
  if (!Array.isArray(rows) || rows.length === 0) return fallback;
  const sanitized = rows.slice(0, 16).map((row) => ({
    agent: textValue(row?.agent, 80),
    label: textValue(row?.label, 120),
    provider: textValue(row?.provider, 80),
    model: textValue(row?.model, 120),
    saved_tokens: clampInt(row?.saved_tokens, 0, 2147483647, 0),
    input_rate_per_million: roundMoney(row?.input_rate_per_million),
    estimated_savings_usd: roundMoney(row?.estimated_savings_usd),
  })).filter((row) => (row.agent || row.label) && row.model);
  return sanitized.length ? sanitized : fallback;
}

function totalModelSavings(rows) {
  return roundMoney((Array.isArray(rows) ? rows : []).reduce(
    (total, row) => total + numberValue(row?.estimated_savings_usd, 0),
    0
  ));
}

function normalizeProofPayload(payload) {
  const totals = payload?.totals || {};
  const saved = clampInt(totals.tokens_saved, 0, 2147483647, 0);
  const modelRows = sanitizeSavingsByModel(totals.savings_by_model, saved);
  const agentRows = sanitizeSavingsByAgent(totals.savings_by_agent);
  return {
    ...payload,
    totals: {
      ...totals,
      estimated_savings_usd: totalModelSavings(modelRows),
      savings_by_model: modelRows,
      savings_by_agent: agentRows,
    },
  };
}

function hasForbiddenRawFields(body) {
  const forbidden = ["command", "stdout", "stderr", "output", "raw", "project", "path", "file", "repository"];
  return forbidden.some((key) => Object.prototype.hasOwnProperty.call(body || {}, key));
}

async function requireKey(env, request, options = {}) {
  const header = request.headers.get("Authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
  const match = token.match(/^sage_live_(key_[A-Za-z0-9]+)_([a-fA-F0-9]+)$/);
  if (!match) return { error: error("Missing or invalid SAGE API key", 401) };

  const keyId = match[1];
  const secretHash = await sha256(token);
  const now = nowIso();

  const key = await env.DB.prepare(
    "SELECT * FROM api_keys WHERE key_id = ? AND secret_hash = ? AND revoked_at = ''"
  ).bind(keyId, secretHash).first();

  if (!key) return { error: error("Invalid or revoked SAGE API key", 401) };

  // Reject expired API keys before applying rate limits.
  if (key.expires_at && key.expires_at !== "" && new Date(key.expires_at) < new Date(now)) {
    return { error: error("API key expired", 401) };
  }

  if (!options.skipRateLimit) {
    // Security: rate limit telemetry ingestion, but do not let telemetry backfill
    // block proof snapshots. Existing keys get the newer 10k/hour floor.
    const hourAgo = new Date(Date.now() - 3600000).toISOString();
    const recentRequests = await env.DB.prepare(
      "SELECT COUNT(*) as count FROM telemetry_events WHERE key_id = ? AND received_at > ?"
    ).bind(keyId, hourAgo).first();

    const maxRequests = Math.max(Number(key.rate_limit_per_hour || 0), 10000);
    const requestCount = Number(recentRequests?.count || 0);

    if (requestCount >= maxRequests) {
      return { error: error("Rate limit exceeded (max " + maxRequests + " requests/hour)", 429) };
    }

    // Security: anomaly detection catches sudden telemetry spikes.
    const fifteenMinAgo = new Date(Date.now() - 900000).toISOString();
    const recentBurst = await env.DB.prepare(
      "SELECT COUNT(*) as count FROM telemetry_events WHERE key_id = ? AND received_at > ?"
    ).bind(keyId, fifteenMinAgo).first();

    const burstCount = Number(recentBurst?.count || 0);
    const normalRate = requestCount / 4; // Historical hourly rate normalized to 15-min window

    if (burstCount > normalRate * 5 && burstCount > 50) {
      const anomalyId = newId("anom");
      await env.DB.prepare(
        `INSERT INTO api_key_anomalies (id, key_id, detected_at, anomaly_type, description, severity, auto_action)
         VALUES (?, ?, ?, 'rate_spike', ?, 'medium', 'throttle')`
      ).bind(
        anomalyId,
        keyId,
        now,
        `Detected ${burstCount} requests in 15 min (5x normal rate of ${normalRate.toFixed(0)})`
      ).run();
      console.log(`Anomaly detected: ${anomalyId} for key ${keyId}`);
    }
  }

  await env.DB.prepare("UPDATE api_keys SET last_used_at = ? WHERE key_id = ?").bind(now, keyId).run();
  return { keyId, key };
}

async function trackDashboardVisit(env, request) {
  if (!env.DB) return;
  const now = nowIso();
  const day = now.slice(0, 10);
  const ip = request.headers.get("CF-Connecting-IP") || request.headers.get("X-Forwarded-For") || "";
  const ua = request.headers.get("User-Agent") || "";
  const country = request.cf?.country || "";
  const visitorHash = await sha256(`sage-dashboard-v1:${ip}:${ua}:${country}`);
  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO dashboard_visitors (visitor_hash, first_seen_at, last_seen_at, visit_count)
       VALUES (?, ?, ?, 1)
       ON CONFLICT(visitor_hash) DO UPDATE SET
        last_seen_at = excluded.last_seen_at,
        visit_count = visit_count + 1`
    ).bind(visitorHash, now, now),
    env.DB.prepare(
      `INSERT INTO dashboard_visit_days (day, visitor_hash, first_seen_at, last_seen_at, visit_count)
       VALUES (?, ?, ?, ?, 1)
       ON CONFLICT(day, visitor_hash) DO UPDATE SET
        last_seen_at = excluded.last_seen_at,
        visit_count = visit_count + 1`
    ).bind(day, visitorHash, now, now),
  ]);
}

async function handleVisitorStats(env, request) {
  const auth = await requireKey(env, request);
  if (auth.error) return auth.error;
  const today = nowIso().slice(0, 10);
  const totals = await env.DB.prepare(
    `SELECT
      COUNT(*) AS unique_visitors,
      COALESCE(SUM(visit_count), 0) AS page_views
     FROM dashboard_visitors`
  ).first();
  const todayTotals = await env.DB.prepare(
    `SELECT
      COUNT(*) AS unique_visitors,
      COALESCE(SUM(d.visit_count), 0) AS page_views,
      COALESCE(SUM(CASE WHEN substr(v.first_seen_at, 1, 10) = ? THEN 1 ELSE 0 END), 0) AS new_visitors,
      COALESCE(SUM(CASE WHEN substr(v.first_seen_at, 1, 10) < ? THEN 1 ELSE 0 END), 0) AS returning_visitors
     FROM dashboard_visit_days d
     JOIN dashboard_visitors v ON v.visitor_hash = d.visitor_hash
     WHERE d.day = ?`
  ).bind(today, today, today).first();
  const recentDays = await env.DB.prepare(
    `SELECT day, COUNT(*) AS unique_visitors, COALESCE(SUM(visit_count), 0) AS page_views
     FROM dashboard_visit_days
     GROUP BY day
     ORDER BY day DESC
     LIMIT 14`
  ).all();
  return json({
    ok: true,
    generated_at: nowIso(),
    today,
    totals: {
      unique_visitors: Number(totals?.unique_visitors || 0),
      page_views: Number(totals?.page_views || 0),
    },
    today_stats: {
      unique_visitors: Number(todayTotals?.unique_visitors || 0),
      page_views: Number(todayTotals?.page_views || 0),
      new_visitors: Number(todayTotals?.new_visitors || 0),
      returning_visitors: Number(todayTotals?.returning_visitors || 0),
    },
    recent_days: (recentDays.results || []).map((row) => ({
      day: row.day,
      unique_visitors: Number(row.unique_visitors || 0),
      page_views: Number(row.page_views || 0),
    })),
  });
}

async function handleGitHubLogin(env, request) {
  // GitHub OAuth login. One GitHub account has one active SAGE API key.
  let body;
  try {
    body = await readJson(request);
  } catch (exc) {
    return error("Invalid JSON", 400, String(exc.message || exc));
  }

  const authCode = textValue(body.github_auth_code, 200);
  const suppliedToken = textValue(body.github_access_token, 4000);
  if (!authCode && !suppliedToken) {
    return error("Missing github_auth_code or github_access_token", 400);
  }
  const redirectUri = textValue(body.redirect_uri, 200);

  // Exchange auth code for GitHub access token, or validate a token supplied
  // by GitHub CLI fallback. The token is never stored.
  let githubToken = suppliedToken;
  if (!githubToken) {
    try {
      const tokenResponse = await fetch("https://github.com/login/oauth/access_token", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify({
          client_id: "Ov23libLspfxbzmPhMSv",
          client_secret: env.GITHUB_CLIENT_SECRET,
          code: authCode,
          ...(redirectUri ? { redirect_uri: redirectUri } : {}),
        }),
      });

      const tokenData = await tokenResponse.json();
      githubToken = tokenData.access_token;

      if (!githubToken) {
        return error(
          "GitHub OAuth failed - invalid auth code",
          401,
          tokenData.error_description || tokenData.error || ""
        );
      }
    } catch (exc) {
      return error("GitHub OAuth exchange failed", 500, String(exc.message || exc));
    }
  }

  // Get GitHub user info
  let githubUser;
  try {
    const userResponse = await fetch("https://api.github.com/user", {
      headers: {
        "Authorization": `Bearer ${githubToken}`,
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SAGE-API/1.0",
      },
    });

    githubUser = await userResponse.json();

    if (!githubUser.id || !githubUser.login) {
      return error("Failed to fetch GitHub user info", 500);
    }
  } catch (exc) {
    return error("GitHub user info fetch failed", 500, String(exc.message || exc));
  }

  const githubId = String(githubUser.id);
  const githubUsername = githubUser.login;
  const displayName = textValue(body.display_name || githubUser.name || githubUsername, 80);
  const createdAt = nowIso();

  // Check if this GitHub user already has a key. Because full API keys are
  // stored only as hashes, reconnecting must rotate/reissue instead of trying
  // to return the old secret.
  const existingKey = await env.DB.prepare(
    "SELECT * FROM api_keys WHERE github_id = ? AND revoked_at = ''"
  ).bind(githubId).first();

  if (existingKey) {
    await env.DB.prepare(
      "UPDATE api_keys SET revoked_at = ? WHERE key_id = ? AND revoked_at = ''"
    ).bind(createdAt, existingKey.key_id).run();
  }

  // Generate new API key
  const keyId = newId("key");
  const secret = randomHex(32);
  const token = `sage_live_${keyId}_${secret}`;

  // Key expiration
  const expiryDays = clampInt(body.expiry_days, 1, 365, 30);
  const expiresAt = new Date(Date.now() + expiryDays * 24 * 60 * 60 * 1000).toISOString();

  // Rate limiting
  const rateLimitPerHour = 10000; // Default for GitHub users and telemetry backfills

  const publicProfile = body.public_profile === true || body.public_profile === 1 ? 1 : 0;

  await env.DB.prepare(
    `INSERT INTO api_keys
      (key_id, secret_hash, prefix, scope, display_name, username, github_id, github_username,
       public_profile, privacy_max, expires_at, rate_limit_per_hour, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      keyId,
      await sha256(token),
      "sage_live",
      "personal",
      displayName,
      githubUsername,
      githubId,
      githubUsername,
      publicProfile,
      1,
      expiresAt,
      rateLimitPerHour,
      createdAt
    )
    .run();

  return json({
    ok: true,
    key_id: keyId,
    api_key: token,
    github_username: githubUsername,
    github_id: parseInt(githubId, 10),
    display_name: displayName,
    created_at: createdAt,
    expires_at: expiresAt,
    rate_limit_per_hour: rateLimitPerHour,
    profile: {
      display_name: displayName,
      username: githubUsername,
      public_profile: !!publicProfile,
    },
    rotated_from: existingKey ? existingKey.key_id : "",
    warning: "This key is shown once. Store it locally; SAGE stores only the hash.",
  }, existingKey ? 200 : 201);
}

async function handleCreateKey(env, request) {
  // Key creation is restricted to trusted clients.
  const masterKey = request.headers.get("X-SAGE-Master-Key");
  if (!masterKey || !env.MASTER_KEY_SECRET || masterKey !== env.MASTER_KEY_SECRET) {
    return error("Unauthorized - Key generation requires master key", 403);
  }

  let body;
  try {
    body = await readJson(request);
  } catch (exc) {
    return error("Invalid JSON", 400, String(exc.message || exc));
  }

  const keyId = newId("key");
  const secret = randomHex(32);
  const token = `sage_live_${keyId}_${secret}`;
  const createdAt = nowIso();

  const expiryDays = clampInt(body.expiry_days, 1, 365, 30);
  const expiresAt = new Date(Date.now() + expiryDays * 24 * 60 * 60 * 1000).toISOString();

  const rateLimitPerHour = clampInt(body.rate_limit_per_hour, 100, 10000, 10000);

  const displayName = textValue(body.display_name || body.profile_name || body.name, 80);
  const username = textValue(body.username || body.handle, 80);
  const publicProfile = body.public_profile === true || body.public_profile === 1 ? 1 : 0;
  const privacyMax = clampInt(body.privacy_max ?? 1, 0, 4, 1);
  const scope = textValue(body.scope || "personal", 40);

  await env.DB.prepare(
    `INSERT INTO api_keys
      (key_id, secret_hash, prefix, scope, display_name, username, public_profile, privacy_max,
       expires_at, rate_limit_per_hour, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      keyId,
      await sha256(token),
      "sage_live",
      scope,
      displayName,
      username,
      publicProfile,
      privacyMax,
      expiresAt,
      rateLimitPerHour,
      createdAt
    )
    .run();

  return json({
    ok: true,
    key_id: keyId,
    api_key: token,
    created_at: createdAt,
    expires_at: expiresAt,
    rate_limit_per_hour: rateLimitPerHour,
    profile: {
      display_name: displayName,
      username,
      public_profile: !!publicProfile,
    },
    warning: "This key is shown once. Store it locally; SAGE stores only the hash.",
  }, 201);
}

async function handleTelemetry(env, request) {
  const auth = await requireKey(env, request);
  if (auth.error) return auth.error;

  let body;
  try {
    body = await readJson(request);
  } catch (exc) {
    return error("Invalid telemetry JSON", 400, String(exc.message || exc));
  }

  // Reject stale telemetry requests to reduce replay risk.
  const timestamp = request.headers.get("X-SAGE-Timestamp") || body.request_timestamp || body.timestamp;
  if (timestamp) {
    const requestTime = new Date(timestamp).getTime();
    const now = Date.now();
    const fiveMinutes = 5 * 60 * 1000;

    if (Math.abs(now - requestTime) > fiveMinutes) {
      return error("Request timestamp expired or invalid (must be within 5 minutes)", 401);
    }
  }

  const privacyLevel = clampInt(body.privacy_level ?? 1, 0, 4, 1);
  if (privacyLevel > clampInt(auth.key.privacy_max, 0, 4, 1)) {
    return error("Telemetry level exceeds API key privacy scope", 403);
  }
  if (privacyLevel <= 1 && hasForbiddenRawFields(body)) {
    return error("Level 1 telemetry cannot include raw command, output, path, repository, or file content fields", 400);
  }

  const idempotencyKey = textValue(
    request.headers.get("X-SAGE-Idempotency-Key") || body.idempotency_key || body.run_id_local_hash || newId("idem"),
    160
  );
  const existing = await env.DB.prepare("SELECT id FROM telemetry_events WHERE idempotency_key = ?")
    .bind(idempotencyKey)
    .first();
  if (existing) return json({ ok: true, duplicate: true, event_id: existing.id });

  const eventId = newId("evt");
  const receivedAt = nowIso();
  const metrics = body.metrics || body;
  const originalTokens = clampInt(metrics.original_tokens, 0, 2147483647, 0);
  const compressedTokens = clampInt(metrics.compressed_tokens, 0, 2147483647, 0);
  const savedTokens = clampInt(metrics.saved_tokens, 0, 2147483647, Math.max(0, originalTokens - compressedTokens));
  const success = body.success === true || clampInt(body.exit_code ?? metrics.exit_code, -999999, 999999, 0) === 0 ? 1 : 0;
  const exitCode = clampInt(body.exit_code ?? metrics.exit_code, -999999, 999999, success ? 0 : 1);
  const day = receivedAt.slice(0, 10);

  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO telemetry_events
        (id, key_id, installation_id, workspace_hash, run_hash, idempotency_key, event_type,
         command_kind, command_family, original_tokens, compressed_tokens, saved_tokens,
         compression_rate, duration_ms, exit_code, success, prediction_score, agent_count,
         privacy_level, client_created_at, received_at, payload_json)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    ).bind(
      eventId,
      auth.keyId,
      textValue(body.installation_id, 120),
      textValue(body.workspace_hash, 160),
      textValue(body.run_hash || body.run_id_local_hash, 160),
      idempotencyKey,
      textValue(body.event_type || "command_completed", 80),
      textValue(body.command_kind || metrics.command_kind || "unknown", 80),
      textValue(body.command_family || metrics.command_family || "unknown", 80),
      originalTokens,
      compressedTokens,
      savedTokens,
      numberValue(metrics.compression_rate, originalTokens ? (savedTokens / originalTokens) * 100 : 0),
      clampInt(metrics.duration_ms ?? body.duration_ms, 0, 2147483647, 0),
      exitCode,
      success,
      body.prediction_score === undefined ? null : numberValue(body.prediction_score, null),
      clampInt(body.agent_count ?? metrics.agent_count, 0, 100000, 0),
      privacyLevel,
      textValue(body.client_created_at || body.created_at || body.timestamp, 80),
      receivedAt,
      JSON.stringify({
        schema_version: textValue(body.schema_version || "1.0", 20),
        client_version: textValue(body.client_version, 80),
        platform: textValue(body.platform, 80),
      })
    ),
    env.DB.prepare(
      `INSERT INTO aggregate_daily
        (day, key_id, runs, successful_runs, failed_runs, original_tokens, compressed_tokens, saved_tokens, duration_ms)
       VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(day, key_id) DO UPDATE SET
        runs = runs + 1,
        successful_runs = successful_runs + excluded.successful_runs,
        failed_runs = failed_runs + excluded.failed_runs,
        original_tokens = original_tokens + excluded.original_tokens,
        compressed_tokens = compressed_tokens + excluded.compressed_tokens,
        saved_tokens = saved_tokens + excluded.saved_tokens,
        duration_ms = duration_ms + excluded.duration_ms`
    ).bind(
      day,
      auth.keyId,
      success,
      success ? 0 : 1,
      originalTokens,
      compressedTokens,
      savedTokens,
      clampInt(metrics.duration_ms ?? body.duration_ms, 0, 2147483647, 0)
    ),
  ]);

  if (env.TELEMETRY_QUEUE) {
    await env.TELEMETRY_QUEUE.send({ event_id: eventId, key_id: auth.keyId, received_at: receivedAt });
  }

  return json({ ok: true, event_id: eventId, duplicate: false });
}

async function handleProof(env) {
  const snapshot = await env.DB.prepare(
    `SELECT payload_json FROM public_proof_snapshots ORDER BY created_at DESC LIMIT 1`
  ).first();
  if (snapshot?.payload_json) {
    try {
      return json(normalizeProofPayload(JSON.parse(snapshot.payload_json)));
    } catch (_exc) {
      // Fall back to event aggregates if the stored snapshot is invalid.
    }
  }

  const total = await env.DB.prepare(
    `SELECT
      COALESCE(SUM(runs), 0) AS total_runs,
      COALESCE(SUM(successful_runs), 0) AS successful_runs,
      COALESCE(SUM(failed_runs), 0) AS failed_runs,
      COALESCE(SUM(original_tokens), 0) AS original_tokens,
      COALESCE(SUM(compressed_tokens), 0) AS compressed_tokens,
      COALESCE(SUM(saved_tokens), 0) AS saved_tokens,
      COALESCE(SUM(duration_ms), 0) AS duration_ms
     FROM aggregate_daily`
  ).first();
  const prediction = await env.DB.prepare(
    `SELECT
      COUNT(*) AS events_with_prediction,
      AVG(prediction_score) AS avg_prediction_score
     FROM telemetry_events
     WHERE prediction_score IS NOT NULL`
  ).first();
  const contributors = await env.DB.prepare(
    `SELECT
      k.display_name,
      k.username,
      COALESCE(SUM(a.runs), 0) AS runs,
      COALESCE(SUM(a.saved_tokens), 0) AS saved_tokens,
      COALESCE(SUM(a.original_tokens), 0) AS original_tokens
     FROM api_keys k
     LEFT JOIN aggregate_daily a ON a.key_id = k.key_id
     WHERE k.public_profile = 1
     GROUP BY k.display_name, k.username
     HAVING runs > 0
     ORDER BY saved_tokens DESC, runs DESC
     LIMIT 25`
  ).all();
  const original = Number(total.original_tokens || 0);
  const saved = Number(total.saved_tokens || 0);
  const totalRuns = Number(total.total_runs || 0);
  const successful = Number(total.successful_runs || 0);
  const savingsByModel = buildSavingsByModel(saved);
  const savingsByAgent = buildSavingsByAgent();
  return json({
    ok: true,
    generated_at: nowIso(),
    public_fields: [
      "total_runs",
      "successful_runs",
      "failed_runs",
      "tokens_processed",
      "tokens_compressed",
      "tokens_saved",
      "estimated_savings_usd",
      "savings_by_model",
      "savings_by_agent",
      "compression_percent",
      "success_rate",
      "failure_prediction_stats",
      "public_contributors",
    ],
    totals: {
      total_runs: totalRuns,
      successful_runs: successful,
      failed_runs: Number(total.failed_runs || 0),
      tokens_processed: original,
      tokens_compressed: Number(total.compressed_tokens || 0),
      tokens_saved: saved,
      estimated_savings_usd: totalModelSavings(savingsByModel),
      savings_by_model: savingsByModel,
      savings_by_agent: savingsByAgent,
      compression_percent: original ? Number(((saved / original) * 100).toFixed(2)) : 0,
      success_rate: totalRuns ? Number(((successful / totalRuns) * 100).toFixed(2)) : 0,
      failure_prediction_stats: {
        events_with_prediction: Number(prediction.events_with_prediction || 0),
        avg_prediction_score:
          prediction.avg_prediction_score === null || prediction.avg_prediction_score === undefined
            ? null
            : Number(Number(prediction.avg_prediction_score).toFixed(4)),
      },
    },
    public_contributors: (contributors.results || []).map((row) => ({
      display_name: row.display_name || "",
      username: row.username || "",
      runs: Number(row.runs || 0),
      tokens_saved: Number(row.saved_tokens || 0),
      tokens_processed: Number(row.original_tokens || 0),
    })),
  });
}

async function handleProofSnapshot(env, request) {
  const auth = await requireKey(env, request, { skipRateLimit: true });
  if (auth.error) return auth.error;
  let body;
  try {
    body = await readJson(request);
  } catch (exc) {
    return error("Invalid proof snapshot JSON", 400, String(exc.message || exc));
  }
  if (hasForbiddenRawFields(body)) {
    return error("Proof snapshots cannot include raw command, output, path, repository, or file content fields", 400);
  }
  const totals = body.totals || {};
  const original = clampInt(totals.tokens_processed, 0, 2147483647, 0);
  const saved = clampInt(totals.tokens_saved, 0, 2147483647, 0);
  const totalRuns = clampInt(totals.total_runs, 0, 2147483647, 0);
  const successful = clampInt(totals.successful_runs, 0, 2147483647, 0);
  const compressed = clampInt(totals.tokens_compressed, 0, 2147483647, 0);
  const savingsByModel = sanitizeSavingsByModel(totals.savings_by_model, saved);
  const savingsByAgent = sanitizeSavingsByAgent(totals.savings_by_agent);
  const snapshot = {
    ok: true,
    generated_at: nowIso(),
    source: "authenticated_local_snapshot",
    owner: {
      display_name: textValue(body.owner?.display_name || body.display_name || "PsYc+GoD AI & ML", 120),
      username: textValue(body.owner?.username || body.username || "PsYcGoD", 80),
    },
    public_fields: [
      "total_runs",
      "successful_runs",
      "failed_runs",
      "tokens_processed",
      "tokens_compressed",
      "tokens_saved",
      "estimated_savings_usd",
      "savings_by_model",
      "savings_by_agent",
      "compression_percent",
      "success_rate",
      "failure_prediction_stats",
    ],
    totals: {
      total_runs: totalRuns,
      successful_runs: successful,
      failed_runs: clampInt(totals.failed_runs, 0, 2147483647, Math.max(0, totalRuns - successful)),
      tokens_processed: original,
      tokens_compressed: compressed,
      tokens_saved: saved,
      estimated_savings_usd: totalModelSavings(savingsByModel),
      savings_by_model: savingsByModel,
      savings_by_agent: savingsByAgent,
      compression_percent: original ? Number(((saved / original) * 100).toFixed(2)) : 0,
      success_rate: totalRuns ? Number(((successful / totalRuns) * 100).toFixed(2)) : 0,
      failure_prediction_stats: {
        events_with_prediction: clampInt(totals.failure_prediction_stats?.events_with_prediction, 0, 2147483647, 0),
        avg_prediction_score: numberValue(totals.failure_prediction_stats?.avg_prediction_score, 0),
      },
    },
  };
  await env.DB.prepare(
    `INSERT INTO public_proof_snapshots (id, created_at, payload_json)
     VALUES ('latest', ?, ?)
     ON CONFLICT(id) DO UPDATE SET created_at = excluded.created_at, payload_json = excluded.payload_json`
  ).bind(snapshot.generated_at, JSON.stringify(snapshot)).run();
  return json({ ok: true, snapshot: snapshot.totals, generated_at: snapshot.generated_at });
}

async function route(request, env) {
  const url = new URL(request.url);
  const origin = request.headers.get("Origin");
  const corsHeaders = origin ? getCorsHeaders(origin) : {};
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders });

  // Serve public proof dashboard HTML
  if (request.method === "GET" && url.pathname === "/dashboard") {
    await trackDashboardVisit(env, request);
    return new Response(PUBLIC_PROOF_DASHBOARD_HTML, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "public, max-age=300",
        ...corsHeaders,
      },
    });
  }

  if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
    return json({ ok: true, service: "sage-api", status: "healthy", generated_at: nowIso() });
  }
  if (request.method === "POST" && url.pathname === "/v1/keys") return handleCreateKey(env, request);
  if (request.method === "POST" && url.pathname === "/v1/github-login") return handleGitHubLogin(env, request);
  if (request.method === "POST" && url.pathname === "/v1/telemetry") return handleTelemetry(env, request);
  if (request.method === "POST" && url.pathname === "/v1/proof-snapshot") return handleProofSnapshot(env, request);
  if (request.method === "GET" && url.pathname === "/v1/admin/visitors") return handleVisitorStats(env, request);
  if (request.method === "GET" && url.pathname === "/v1/proof") return handleProof(env);
  return error("Not found", 404);
}

export default {
  fetch(request, env) {
    return route(request, env).catch((exc) => error("Internal error", 500, String(exc?.message || exc)));
  },
};
