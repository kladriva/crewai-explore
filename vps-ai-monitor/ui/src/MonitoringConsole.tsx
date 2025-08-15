import React, { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/* ----------------------------- Types & helpers ---------------------------- */

type Point = { time: string; value: number };
type Snapshot = { cpu?: number; mem?: number; disk?: number };

type ActionItem = {
  ts: number;                                // epoch seconds
  action: string;
  target?: string;
  outcome?: string;
  reason?: string;
  severity: "info" | "warn" | "crit";
};

const THRESHOLDS = {
  cpu:  { warn: 60,  crit: 85 },
  mem:  { warn: 80,  crit: 90 },
  disk: { warn: 75,  crit: 90 },
} as const;

const PALETTE = {
  cpu:  { stroke: "#fb923c", border: "border-amber-200",  bgFrom: "from-amber-50",  bgVia: "via-amber-50/60"  },
  mem:  { stroke: "#06b6d4", border: "border-cyan-200",   bgFrom: "from-cyan-50",   bgVia: "via-cyan-50/60"   },
  disk: { stroke: "#a78bfa", border: "border-violet-200", bgFrom: "from-violet-50", bgVia: "via-violet-50/60" },
} as const;

function pct(n?: number) {
  return typeof n === "number" && isFinite(n) ? `${n.toFixed(1)}%` : "—";
}

function tsToTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

async function fetchWithTimeout(
  input: string | URL,
  init: RequestInit = {},
  ms = 7_000
): Promise<Response> {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(input, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(id);
  }
}

// KPI color (value is optional, metric first to avoid TS "required after optional")
function colorFor(metric: keyof typeof THRESHOLDS, value?: number) {
  if (value == null || !isFinite(value)) return { text: "text-slate-900", bar: "bg-slate-300" };
  const { warn, crit } = THRESHOLDS[metric];
  if (value >= crit) return { text: "text-red-600", bar: "bg-red-500" };
  if (value >= warn) return { text: "text-amber-600", bar: "bg-amber-500" };
  return { text: "text-emerald-700", bar: "bg-emerald-500" };
}

// Safe parsers for the history API (handles multiple shapes)
function parseSeriesPayload(j: any): Array<[number, number]> {
  // Accepts: {series:[{values:[[ts,val],...] }]}
  //          {result:[{values:[[ts,val],...] }]}
  //          {data:{result:[{values:...}]}}
  const arr =
    j?.series ??
    j?.result ??
    j?.data?.result ??
    [];
  const values = Array.isArray(arr) && arr.length ? arr[0]?.values : [];
  if (!Array.isArray(values)) return [];
  return values
    .map((p: any) => [Number(p[0]), parseFloat(p[1])])
    .filter(([t, v]) => isFinite(t) && isFinite(v)) as Array<[number, number]>;
}

function parseTs(v: any): number {
  if (typeof v === "number" && isFinite(v)) return v;
  const p = Date.parse(String(v ?? ""));
  return isFinite(p) ? p / 1000 : Date.now() / 1000;
}

/* -------------------------------- Component ------------------------------- */

export default function MonitoringConsole() {
  // Defaults: en prod on passe par Nginx => "/api". En dev: port local 8010
  const defaultApi =
    import.meta.env.PROD ? "/api" : "http://localhost:8010/api";

  const [apiUrl, setApiUrl]   = useState<string>(localStorage.getItem("apiUrl") || defaultApi);
  const [apiKey, setApiKey]   = useState<string>(localStorage.getItem("apiKey") || "");
  const [minutes, setMinutes] = useState<number>(60);
  const [loading, setLoading] = useState<boolean>(false);

  const [snap, setSnap] = useState<Snapshot>({});
  const [cpu,  setCpu]  = useState<Point[]>([]);
  const [mem,  setMem]  = useState<Point[]>([]);
  const [disk, setDisk] = useState<Point[]>([]);

  const [actions, setActions] = useState<ActionItem[]>([]);

  useEffect(() => localStorage.setItem("apiUrl", apiUrl), [apiUrl]);
  useEffect(() => localStorage.setItem("apiKey", apiKey), [apiKey]);

  const baseUrl = useMemo(() => apiUrl.replace(/\/$/, ""), [apiUrl]);
  const defaultHeaders = useMemo<HeadersInit | undefined>(
    () => (apiKey ? { "X-API-Key": apiKey } : undefined),
    [apiKey]
  );

  async function getJSON<T>(path: string): Promise<T> {
    const r = await fetchWithTimeout(`${baseUrl}${path}`, {
      headers: defaultHeaders,
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  }

  async function fetchSnapshot() {
    const j = await getJSON<any>("/snapshot");
    setSnap({ cpu: j.cpu, mem: j.mem, disk: j.disk });
  }

  async function fetchHistory(metric: "cpu" | "mem" | "disk") {
    const j = await getJSON<any>(`/history?metric=${metric}&minutes=${minutes}&step=15s`);
    const values = parseSeriesPayload(j);
    const pts: Point[] = values.map(([t, v]) => ({ time: tsToTime(t), value: v }));
    if (metric === "cpu")  setCpu(pts);
    if (metric === "mem")  setMem(pts);
    if (metric === "disk") setDisk(pts);
  }

  async function refreshAll() {
    setLoading(true);
    try {
      await Promise.all([
        fetchSnapshot(),
        fetchHistory("cpu"),
        fetchHistory("mem"),
        fetchHistory("disk"),
      ]);
    } finally {
      setLoading(false);
    }
  }

  // Polling
  useEffect(() => {
    refreshAll();
    const id = setInterval(refreshAll, 15_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseUrl, apiKey, minutes]);

  /* ----------------------- Actions automatiques (logs) ---------------------- */

  function toActionItems(raw: any): ActionItem[] {
    const arr: any[] = Array.isArray(raw) ? raw : (raw.items || raw.results || raw.events || []);
    if (!Array.isArray(arr)) return [];
    return arr
      .map((e: any): ActionItem => {
        if (typeof e === "string") {
          return { ts: Date.now() / 1000, action: e, severity: "info" };
        }
        return {
          ts: parseTs(e.ts ?? e.time ?? e.timestamp ?? e.date),
          action: e.action ?? e.type ?? e.name ?? "action",
          target: e.target ?? e.container ?? e.service,
          outcome: e.outcome ?? e.result ?? e.status,
          reason: e.reason ?? e.explanation ?? e.message,
          severity: (e.severity ?? e.level ?? (e.crit ? "crit" : e.warn ? "warn" : "info")) as ActionItem["severity"],
        };
      })
      .sort((a, b) => b.ts - a.ts)
      .slice(0, 10);
  }

  async function fetchActions() {
    for (const p of ["/auto-actions", "/actions/recent", "/actions/logs"]) {
      try {
        const data = await getJSON<any>(p);
        const list = toActionItems(data);
        if (list.length) {
          setActions(list);
          return;
        }
      } catch {
        // try next
      }
    }
    setActions([]);
  }

  useEffect(() => {
    fetchActions();
    const id = setInterval(fetchActions, 15_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseUrl, apiKey]);

  /* --------------------------------- Render -------------------------------- */

  const cpuColor  = colorFor("cpu",  snap.cpu);
  const memColor  = colorFor("mem",  snap.mem);
  const diskColor = colorFor("disk", snap.disk);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
        <h1 className="text-5xl font-extrabold tracking-tight text-slate-800 text-center">
          VPS Monitoring Console
        </h1>

        {/* Controls */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <Field label="API URL">
            <input
              className="border rounded-md p-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-400"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="/api ou http://host:8010/api"
            />
          </Field>
          <Field label="API Key (optionnel)">
            <input
              className="border rounded-md p-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-400"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="X-API-Key"
            />
          </Field>
          <Field label="Fenêtre">
            <select
              className="border rounded-md p-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-400"
              value={minutes}
              onChange={(e) => setMinutes(parseInt(e.target.value))}
            >
              <option value={15}>15 min</option>
              <option value={60}>1 h</option>
              <option value={180}>3 h</option>
              <option value={720}>12 h</option>
            </select>
          </Field>
          <div className="flex items-end">
            <button
                onClick={refreshAll}
                disabled={loading}
                className="w-full rounded-md px-4 py-2 font-medium
                           !bg-emerald-600 text-white
                           hover:!bg-emerald-500 active:!bg-emerald-700
                           disabled:!bg-emerald-400 disabled:text-white disabled:opacity-100
                           disabled:cursor-not-allowed shadow-sm transition-colors"
              >
                {loading ? "…" : "Rafraîchir"}
              </button>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid gap-4 md:grid-cols-3">
          <Kpi title="CPU" value={pct(snap.cpu)}  color={cpuColor}  />
          <Kpi title="Mémoire" value={pct(snap.mem)} color={memColor} />
          <Kpi title="Disque /" value={pct(snap.disk)} color={diskColor} />
        </div>

        {/* Charts */}
        <div className="grid gap-6 xl:grid-cols-3">
          <Timeseries
            title="CPU (%)"
            data={cpu}
            stroke={PALETTE.cpu.stroke}
            border={PALETTE.cpu.border}
            from={PALETTE.cpu.bgFrom}
            via={PALETTE.cpu.bgVia}
            gid="cpu"
          />
          <Timeseries
            title="Mémoire (%)"
            data={mem}
            stroke={PALETTE.mem.stroke}
            border={PALETTE.mem.border}
            from={PALETTE.mem.bgFrom}
            via={PALETTE.mem.bgVia}
            gid="mem"
          />
          <Timeseries
            title="Disque (%)"
            data={disk}
            stroke={PALETTE.disk.stroke}
            border={PALETTE.disk.border}
            from={PALETTE.disk.bgFrom}
            via={PALETTE.disk.bgVia}
            gid="disk"
          />
        </div>

        {/* Actions automatiques */}
        <div className="rounded-xl p-4 border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium text-slate-700">
              Actions automatiques (10 dernières)
            </div>
            <button
              onClick={fetchActions}
              className="text-emerald-600 hover:text-emerald-700 text-sm"
            >
              Rafraîchir
            </button>
          </div>

          {actions.length === 0 ? (
            <div className="text-sm text-slate-500">Aucune action récente.</div>
          ) : (
            <ul className="space-y-2">
              {actions.map((a, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span
                    className={`mt-1 h-2.5 w-2.5 rounded-full ${
                      a.severity === "crit"
                        ? "bg-red-500"
                        : a.severity === "warn"
                        ? "bg-amber-500"
                        : "bg-emerald-500"
                    }`}
                  />
                  <div className="text-sm">
                    <div className="text-slate-800">
                      <span className="font-medium">{a.action}</span>
                      {a.target ? (
                        <span className="text-slate-500"> • {a.target}</span>
                      ) : null}
                      {a.outcome ? (
                        <span className="text-slate-500"> — {a.outcome}</span>
                      ) : null}
                    </div>
                    {a.reason ? (
                      <div className="text-slate-500">{a.reason}</div>
                    ) : null}
                    <div className="text-xs text-slate-400">
                      {new Date(a.ts * 1000).toLocaleString()}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <p className="text-xs text-center text-slate-500">
          Données: Prometheus • Actions: API FastAPI • Refresh auto 15s
        </p>
      </div>
    </div>
  );
}

/* -------------------------------- Subcomponents --------------------------- */

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs text-slate-500 block mb-1">{label}</label>
      {children}
    </div>
  );
}

function Kpi({
  title,
  value,
  color,
}: {
  title: string;
  value?: string;
  color: { text: string; bar: string };
}) {
  return (
    <div className="rounded-xl p-4 border border-slate-200 bg-white shadow-sm">
      <div className="text-sm text-slate-600 mb-2">{title}</div>
      <div className={`h-1.5 w-16 rounded-full mb-3 ${color.bar}`} />
      <div className={`text-3xl font-semibold ${color.text}`}>{value || "—"}</div>
    </div>
  );
}

function Timeseries({
  title,
  data,
  stroke,
  border,
  from,
  via,
  gid,
}: {
  title: string;
  data: Point[];
  stroke: string;
  border: string;
  from: string;
  via: string;
  gid: string;
}) {
  return (
    <div className={`rounded-xl p-4 border ${border} bg-gradient-to-b ${from} ${via} to-white shadow-sm`}>
      <div className="text-sm text-slate-700 mb-2">{title}</div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={stroke} stopOpacity={0.25} />
                <stop offset="95%" stopColor={stroke} stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
            <XAxis dataKey="time" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} />
            <Tooltip formatter={(v: any) => `${Number(v).toFixed(1)}%`} />
            <Area type="monotone" dataKey="value" stroke={stroke} fill={`url(#${gid})`} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
