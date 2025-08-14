// src/MonitoringConsole.tsx
import React, { useEffect, useMemo, useState, useCallback } from "react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

type Point = { time: string; value: number };
type Snapshot = { cpu?: number; mem?: number; disk?: number };

const PALETTE = {
  cpu:  { stroke: "#f59e0b", chip: "bg-amber-500",  border: "border-amber-200",  gradFrom: "from-amber-50",  gradVia: "via-amber-50/60"  },
  mem:  { stroke: "#06b6d4", chip: "bg-cyan-500",   border: "border-cyan-200",   gradFrom: "from-cyan-50",   gradVia: "via-cyan-50/60"   },
  disk: { stroke: "#8b5cf6", chip: "bg-violet-500", border: "border-violet-200", gradFrom: "from-violet-50", gradVia: "via-violet-50/60" },
};

const DEFAULT_API = import.meta.env.PROD ? "/api" : "http://localhost:8000";

const fmtPct = (n?: number) =>
  typeof n === "number" && isFinite(n) ? `${n.toFixed(1)}%` : "—";

const tsToLabel = (ts: number) =>
  new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, ms = 7000) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  const merged = { ...init, signal: ctrl.signal };
  return fetch(input, merged).finally(() => clearTimeout(id));
}

// --- composant ---
export default function MonitoringConsole() {
  // état
  const [apiUrl, setApiUrl] = useState(localStorage.getItem("apiUrl") || DEFAULT_API);
  const [apiKey, setApiKey] = useState(localStorage.getItem("apiKey") || "");
  const [minutes, setMinutes] = useState(15);
  const [loading, setLoading] = useState(false);

  const [snap, setSnap] = useState<Snapshot>({});
  const [cpu, setCpu] = useState<Point[]>([]);
  const [mem, setMem] = useState<Point[]>([]);
  const [disk, setDisk] = useState<Point[]>([]);
  const [target, setTarget] = useState("nginx");
  const [actionBusy, setActionBusy] = useState(false);

  useEffect(() => localStorage.setItem("apiUrl", apiUrl), [apiUrl]);
  useEffect(() => localStorage.setItem("apiKey", apiKey), [apiKey]);

  const headersInit = useMemo<HeadersInit | undefined>(
    () => (apiKey ? { "X-API-Key": apiKey } : undefined),
    [apiKey]
  );
  const reqInit = useCallback((): RequestInit => (headersInit ? { headers: headersInit } : {}), [headersInit]);

  // --- fetchers
  async function fetchSnapshot() {
    const r = await fetchWithTimeout(`${apiUrl}/api/snapshot`, reqInit());
    const j = await r.json();
    setSnap({ cpu: j.cpu, mem: j.mem, disk: j.disk });
  }

  // <— BUG FIX: l’API renvoie `result`, pas `series`. On gère les deux.
  function parseHistory(j: any): Point[] {
    const values =
      j?.result?.[0]?.values ??
      j?.series?.[0]?.values ??
      [];
    return values
      .map((p: any[]) => ({ time: tsToLabel(Number(p[0])), value: Number(p[1]) }))
      .filter((p: Point) => isFinite(p.value));
  }

  async function fetchHistory(metric: "cpu" | "mem" | "disk") {
    const r = await fetchWithTimeout(
      `${apiUrl}/api/history?metric=${metric}&minutes=${minutes}&step=15s`,
      reqInit()
    );
    const pts = parseHistory(await r.json());
    if (metric === "cpu") setCpu(pts);
    if (metric === "mem") setMem(pts);
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
  useEffect(() => {
    refreshAll();
    const id = setInterval(refreshAll, 15000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl, apiKey, minutes]);

  async function restartContainer() {
    try {
      setActionBusy(true);
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey) headers["X-API-Key"] = apiKey;
      const r = await fetchWithTimeout(`${apiUrl}/api/actions/restart-container`, {
        method: "POST",
        headers,
        body: JSON.stringify({ name: target }),
      });
      const j = await r.json();
      alert(j.result || JSON.stringify(j));
    } catch (e: any) {
      alert("Action error: " + (e?.message || e));
    } finally {
      setActionBusy(false);
    }
  }

  const resetApiUrl = () => setApiUrl(DEFAULT_API);

  // --- UI
  return (
    <div className="min-h-screen bg-slate-50">
      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <h1 className="text-5xl font-extrabold tracking-tight text-slate-800 text-center mb-2">
          VPS Monitoring Console
        </h1>

        {/* Barre de contrôle */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <Field label="API URL">
            <div className="flex gap-2">
              <input
                className="border rounded-md p-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-400"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://localhost:8000  ou  /api"
              />
              <button
                onClick={resetApiUrl}
                className="whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium
                           bg-slate-200 hover:bg-slate-300 active:bg-slate-400 transition-colors"
                title="Revenir à la valeur par défaut"
              >
                Reset
              </button>
            </div>
          </Field>

          <Field label="API Key (optionnel)">
            <input
              className="border rounded-md p-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-400"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="X-API-Key"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
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

            {/* Bouton VERT fiable */}
            <div className="flex items-end">
              <button
                onClick={refreshAll}
                disabled={loading}
                className="appearance-none w-full rounded-md px-4 py-2 font-medium text-white
                           bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700
                           disabled:bg-emerald-400 disabled:text-white disabled:opacity-100
                           shadow-sm transition-colors"
              >
                {loading ? "…" : "Rafraîchir"}
              </button>
            </div>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid gap-4 md:grid-cols-3">
          <Kpi title="CPU" value={fmtPct(snap.cpu)} barClass={PALETTE.cpu.chip} />
          <Kpi title="Mémoire" value={fmtPct(snap.mem)} barClass={PALETTE.mem.chip} />
          <Kpi title="Disque /" value={fmtPct(snap.disk)} barClass={PALETTE.disk.chip} />
        </div>

        {/* Graphiques */}
        <div className="grid gap-6 xl:grid-cols-3">
          <Timeseries
            title="CPU (%)" data={cpu}
            stroke={PALETTE.cpu.stroke} border={PALETTE.cpu.border}
            from={PALETTE.cpu.gradFrom} via={PALETTE.cpu.gradVia} gid="cpu"
          />
          <Timeseries
            title="Mémoire (%)" data={mem}
            stroke={PALETTE.mem.stroke} border={PALETTE.mem.border}
            from={PALETTE.mem.gradFrom} via={PALETTE.mem.gradVia} gid="mem"
          />
          <Timeseries
            title="Disque (%)" data={disk}
            stroke={PALETTE.disk.stroke} border={PALETTE.disk.border}
            from={PALETTE.disk.gradFrom} via={PALETTE.disk.gradVia} gid="disk"
          />
        </div>

        {/* Actions */}
        <div className="rounded-xl p-4 border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col sm:flex-row gap-3 items-end">
            <div className="grow">
              <label className="text-xs text-slate-500 block mb-1">
                Conteneur à redémarrer (whitelist dans <code>rules.yaml</code>)
              </label>
              <input
                className="border rounded-md p-2 w-full focus:outline-none focus:ring-2 focus:ring-rose-400"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="ex: nginx"
              />
            </div>
            <button
              onClick={restartContainer}
              disabled={actionBusy}
              className="appearance-none rounded-md px-4 py-2 font-medium text-white
                         bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700
                         disabled:bg-emerald-400 disabled:opacity-60 shadow-sm"
            >
              {actionBusy ? "…" : "Redémarrer le conteneur"}
            </button>
          </div>
        </div>

        <p className="text-xs text-center text-slate-500">
          Données: Prometheus • Actions: API FastAPI • Refresh auto 15s
        </p>
      </main>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs text-slate-500 block mb-1">{label}</label>
      {children}
    </div>
  );
}

function Kpi({ title, value, barClass }: { title: string; value?: string; barClass: string }) {
  return (
    <div className="rounded-xl p-4 border border-slate-200 bg-white shadow-sm">
      <div className="text-sm text-slate-600 mb-2">{title}</div>
      <div className={`h-1.5 w-16 rounded-full mb-3 ${barClass}`} />
      <div className="text-3xl font-semibold text-slate-900">{value || "—"}</div>
    </div>
  );
}

function Timeseries({
  title, data, stroke, border, from, via, gid,
}: { title: string; data: Point[]; stroke: string; border: string; from: string; via: string; gid: string }) {
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
            <Area
              type="monotone" dataKey="value"
              stroke={stroke} strokeWidth={2}
              fill={`url(#${gid})`}
              isAnimationActive animationDuration={300}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
