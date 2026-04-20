// KAIROS Merged API Client — combines KAIROS backend + Vibe-Trading style endpoints

// Vibe-Trading style endpoints: /runs, /upload (proxied by Vite)
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.message || body.detail || body.error || detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : ({} as T);
}

// KAIROS-specific endpoints: /api/strategies, /api/ml, /api/artifacts, /api/sessions, v.v.
async function kRequest<T>(path: string, options?: RequestInit): Promise<T> {
  return request<T>(`/api${path}`, options);
}

async function uploadFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/upload", { method: "POST", body: form });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.message || body.detail || body.error || detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  uploadFile,

  // ─── Vibe-Trading Runs (RunData with embedded JSON) ──────────────────────
  listRuns: () => request<RunListItem[]>("/runs"),
  getRun: (id: string) => request<RunData>(`/runs/${id}`),
  getRunCode: (id: string) => request<Record<string, string>>(`/runs/${id}/code`),
  getRunPine: (id: string) => request<PineScriptResult>(`/runs/${id}/pine`),

  // ─── KAIROS Runs (BacktestRun with CSV artifacts) ────────────────────────
  getKairosRun: (runId: string) => kRequest<BacktestRun>(`/runs/${runId}`),
  listKairosRuns: () => kRequest<BacktestRun[]>("/runs"),
  getArtifact: async (runId: string, fileName: string): Promise<string> => {
    const res = await fetch(`/api/artifacts/${runId}/${fileName}`);
    if (!res.ok) throw new Error(`Lỗi tải file: ${fileName}`);
    return res.text();
  },

  // ─── Sessions (Sử dụng kRequest để trỏ vào /api/sessions của FastAPI) ────
  listSessions: () => kRequest<SessionItem[]>("/sessions"),
  createSession: (title?: string) =>
    kRequest<SessionItem>("/sessions", { method: "POST", body: JSON.stringify({ title: title || "" }) }),
  deleteSession: (sid: string) =>
    kRequest<{ status: string }>(`/sessions/${sid}`, { method: "DELETE" }),
  renameSession: (sid: string, title: string) =>
    kRequest<{ status: string }>(`/sessions/${sid}`, { method: "PATCH", body: JSON.stringify({ title }) }),
  sendMessage: (sid: string, content: string) =>
    kRequest<{ message_id: string; attempt_id: string }>(`/sessions/${sid}/messages`, {
      method: "POST", body: JSON.stringify({ content }),
    }),
  cancelSession: (sid: string) =>
    kRequest<{ status: string }>(`/sessions/${sid}/cancel`, { method: "POST" }),
  getSessionMessages: (sid: string) => kRequest<MessageItem[]>(`/sessions/${sid}/messages`),
  
  // SSE Url truyền thống (Backup)
  sseUrl: (sid: string) => `/api/sessions/${sid}/events`,

  // 🟢 KAIROS Server-Sent Events (SSE) URLs 🟢
  kairosChatUrl: () => `/api/chat`,
  kairosSwarmAnalyzeUrl: () => `/api/swarm/analyze_coin`,

  // ─── Swarm ───────────────────────────────────────────────────────────────
  listSwarmPresets: () => kRequest<SwarmPreset[]>("/swarm/presets"),
  createSwarmRun: (preset_name: string, user_vars: Record<string, string>) =>
    kRequest<{ id: string; status: string }>("/swarm/runs", {
      method: "POST", body: JSON.stringify({ preset_name, user_vars }),
    }),
  listSwarmRuns: () => kRequest<SwarmRunSummary[]>("/swarm/runs"),
  getSwarmRun: (id: string) => kRequest<Record<string, unknown>>(`/swarm/runs/${id}`),
  cancelSwarmRun: (id: string) =>
    kRequest<{ status: string }>(`/swarm/runs/${id}/cancel`, { method: "POST" }),

  // ─── KAIROS Strategies ───────────────────────────────────────────────────
  listStrategies: () => kRequest<Strategy[]>("/strategies"),
  runBacktest: (strategyId: string) =>
    kRequest<{ run_id: string }>("/backtest/run", {
      method: "POST", body: JSON.stringify({ strategy_id: strategyId }),
    }),

  // ─── KAIROS ML Center ────────────────────────────────────────────────────
  getMLStatus: () => kRequest<MLModuleStatus[]>("/ml/status"),
  trainModule: (moduleName: string) =>
    kRequest<void>(`/ml/${moduleName}/train`, { method: "POST" }),
  getRegime: () =>
    kRequest<{ state_id: number; state_name: string; confidence: number }>("/ml/regime/current"),
};

// ─── Upload Types ──────────────────────────────────────────────────────────────
export interface UploadResult {
  status: string;
  file_path: string;
  filename: string;
}

// ─── Swarm Types ──────────────────────────────────────────────────────────────
export interface SwarmPreset {
  name: string;
  title: string;
  description: string;
  agent_count: number;
  variables: { name: string; description: string; required: boolean }[];
}

export interface SwarmRunSummary {
  id: string;
  preset_name: string;
  status: string;
  created_at: string;
  task_count: number;
  completed_count: number;
}

// ─── Vibe-Trading Run Types ────────────────────────────────────────────────────
export interface RunListItem {
  run_id: string;
  status: string;
  created_at: string;
  prompt?: string;
  total_return?: number;
  sharpe?: number;
  codes?: string[];
  start_date?: string;
  end_date?: string;
}

export interface PriceBar {
  time: string;
  timestamp?: string;
  code?: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TradeMarker {
  time: string;
  timestamp?: string;
  code?: string;
  side: "BUY" | "SELL";
  price: number;
  qty?: number;
  reason?: string;
  text?: string;
}

export interface EquityPoint {
  time: string;
  equity: string | number;
  drawdown: string | number;
}

export interface ValidationData {
  monte_carlo?: {
    actual_sharpe: number;
    actual_max_dd: number;
    p_value_sharpe: number;
    p_value_max_dd: number;
    simulated_sharpe_mean: number;
    simulated_sharpe_std: number;
    simulated_sharpe_p5: number;
    simulated_sharpe_p95: number;
    n_simulations: number;
    n_trades: number;
    error?: string;
  };
  bootstrap?: {
    observed_sharpe: number;
    ci_lower: number;
    ci_upper: number;
    median_sharpe: number;
    prob_positive: number;
    confidence: number;
    n_bootstrap: number;
    error?: string;
  };
  walk_forward?: {
    n_windows: number;
    windows: Array<{
      window: number;
      start: string;
      end: string;
      return: number;
      sharpe: number;
      max_dd: number;
      trades: number;
      win_rate: number;
    }>;
    profitable_windows: number;
    consistency_rate: number;
    return_mean: number;
    return_std: number;
    sharpe_mean: number;
    sharpe_std: number;
    error?: string;
  };
}

export interface RunData {
  status: string;
  run_id: string;
  prompt?: string;
  elapsed_seconds?: number;
  run_directory?: string;
  run_stage?: string;
  run_context?: Record<string, unknown>;
  metrics?: BacktestMetrics;
  artifacts?: ArtifactInfo[];
  validation?: ValidationData;
  price_series?: Record<string, PriceBar[]>;
  indicator_series?: Record<string, Record<string, IndicatorPoint[]>>;
  trade_markers?: TradeMarker[];
  equity_curve?: EquityPoint[];
  trade_log?: Array<Record<string, string>>;
  run_logs?: Array<{ source?: string; line_number?: number; message?: string }>;
}

export interface BacktestMetrics {
  final_value: number;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe: number;
  win_rate: number;
  trade_count: number;
  [key: string]: number;
}

export interface IndicatorPoint {
  time: string;
  value: number;
}

export interface ArtifactInfo {
  name: string;
  path: string;
  type: string;
  size: number;
  exists: boolean;
}

export interface PineScriptResult {
  exists: boolean;
  content: string | null;
}

export interface SessionItem {
  session_id: string;
  title?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  last_attempt_id?: string;
}

export interface MessageItem {
  message_id: string;
  session_id: string;
  role: string;
  content: string;
  created_at: string;
  linked_attempt_id?: string;
  metadata?: Record<string, unknown>;
}

// ─── KAIROS-specific Types ─────────────────────────────────────────────────────
export interface BacktestRun {
  run_id: string;
  strategy_id: string;
  strategy_name: string;
  status: "running" | "completed" | "failed";
  config: {
    codes: string[];
    start_date: string;
    end_date: string;
    htf: string;
    initial_cash: number;
  };
  metrics?: {
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    profit_factor: number;
    total_trades: number;
    avg_win: number;
    avg_loss: number;
    rr_ratio: number;
    expectancy: number;
  };
}

export interface Trade {
  id: string;
  time_open: string;
  time_close: string;
  side: "long" | "short";
  entry_price: number;
  exit_price: number;
  pnl_usd: number;
  duration_h: number;
  filter_date?: string;
  filter_weekday?: number;
  filter_hour?: number;
  filter_side?: "long" | "short";
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  htf: string;
  codes: string[];
  last_return: number;
  sharpe: number;
  max_drawdown: number;
  win_rate: number;
  mode: string;
  exchange: string;
  tags: string[];
  params: Record<string, unknown>;
  description_detail: string;
  backtest_mode: string;
  created_at: string;
}

export interface MLModuleStatus {
  name: string;
  label: string;
  trained: boolean;
  last_trained?: string;
  accuracy?: number;
  f1_score?: number;
  n_samples?: number;
}