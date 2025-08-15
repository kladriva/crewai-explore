import React, { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { time: string; value: number };
type Snapshot = { cpu?: number; mem?: number; disk?: number };

// ---- palette et seuils ----
const PALETTE = {
  cpu:  { stroke: "#fb923c", chip: "bg-amber-500",  border: "border-amber-200",  gradFrom: "from-amber-50",  gradVia: "via-amber-50/60"  },
  mem:  { stroke: "#06b6d4", chip: "bg-cyan-500",   border: "border-cyan-200",   gradFrom: "from-cyan-50",   gradVia: "via-cyan-50/60"   },
  disk: { stroke: "#a78bfa", chip: "bg-violet-500", border: "border-violet-200", gradFrom: "from-violet-50", gradVia: "via-violet-50/60" },
};

const THRESHOLDS = {
  cpu:  { warn: 70, crit: 85 },
  mem:  { warn: 75, crit: 90 },
  disk: { warn: 80, crit: 90 },
};

function pct(n?: number) {
  return typeof n === "number" && isFinite(n) ? `${n.toFixed(1)}%` : "—";
}
function tsToTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

// Helper fetch robuste, sans types DOM ambigus
function fetchWithTimeout(url: string, init: RequestInit = {}, ms = 8000) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  const merged: RequestInit = { ...init, signal: ctrl.signal };
  return fetch(url, merged).finally(() => clearTimeout(id));
}

// renvoie une couleur (texte + barre KPI) en fonction des seuils
function colorFor(value: number | undefined, metric: keyof typeof THRESHOLDS) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return { text: "text-slate-900", bar: "bg-slate-300" };
  }
  const { warn, crit } = THRESHOLDS[metric];
  if (value >= crit) return { text: "text-red-600", bar: "bg-red-500" };
  if (value >= warn) return { text: "text-amber-600", bar: "bg-amber-500" };
  return { text: "text-emerald-700", bar: "bg-emerald-500" };
}

export default function MonitoringConsole() {
  // API root : par défaut "/api" (via Nginx). En dev local, tu peux mettre "http://localhost:8000"
  const [apiRoot, setApiRoot] = useState(
    localStorage.getItem("apiUrl") || "/api"
  );
  const [apiKey, setApiKey] = useState(localStorage.getItem("apiKey") || "");
  const [minutes, setMinutes] = useState(60);
  const [loading, setLoading] = useState(false);

  const [snap, setSnap] = useState<Snapshot>({});
  const [cpu, setCpu] = useState<Point[]>([]);
  const [mem, setMem] = useState<Point[]>([]);
  const [disk, setDisk] = useState<Point[]>([]);
  const [actions, setActions] = useState<string[]>([]); // actions auto (si API dispo)

  const [target, setTarget] = useState("nginx");
  const [actionBusy, setActionBusy] = useState(false);

  useEffect(() => localStorage.setItem("apiUrl", apiRoot), [apiRoot]);
  useEffect(() => localStorage.setItem("apiKey", apiKey), [apiKey]);

  // en-têtes facultatifs
  const baseInit = useMemo<RequestInit>(() => {
    if (!apiKey) return {};
    const headers: Record<string, string> = { "X-API-Key": apiKey };
    return { headers };
  }, [apiKey]);

  // helper JSON
  async function getJSON<T>(path: string) {
    const url = path.startsWith("http") ? path : `${apiRoot}${path.startsWith("/") ? path : `/${path}`}`;
    const r = await fetchWithTimeout(url, baseInit);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json() as Promise<T>;
  }

  async function fetchSnapshot() {
    const j = await getJSON<{ cpu: number; mem: number; disk: number }>("/snapshot");
    setSnap({ cpu: j.cpu, mem: j.mem, disk: j.disk });
  }

  async function fetchHistory(metric: "cpu" | "mem" | "disk") {
    const j = await getJSON<{ result?: Array<{ values: [number, string][] }> }>(
      `/history?metric=${metric}&minutes=${minutes}&step=15s`
    );
    const series = j.result?.[0]?.values || [];
    const pts: Point[] = series
      .map(([ts, val]) => ({ time: tsToTime(ts), value: parseFloat(val) }))
      .filter(p => Number.isFinite(p.value));
    if (metric === "cpu") setCpu(pts);
    if (metric === "mem") setMem(pts);
    if (metric === "disk") setDisk(pts);
  }

  async function fetchActions() {
    // facultatif : si l’endpoint n’existe pas => on ignore
    try {
      const j = await getJSON<{ items?: string[] }>("/actions?limit=10");
      setActions(Array.isArray(j.items) ? j.items : []);
    } catch {
      setActions([]);
    }
  }

  async function refreshAll() {
    setLoading(true);
    try {
      await Promise.all([
        fetchSnapshot(),
        fetchHistory("cpu"),
        fetchHistory("mem"),
        fetchHistory("disk"),
        fetchActions(),
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
  }, [apiRoot, apiKey, minutes]);

  async function restartContainer() {
    try {
      setActionBusy(true);
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey) headers["X-API-Key"] = apiKey;
      const url = `${apiRoot}/actions/restart-container`;
      const r = await fetchWithTimeout(url, { method: "POST", headers, body: JSON.stringify({ name: target }) });
      const j = await r.json();
      alert(j.result || JSON.stringify(j));
      fetchActions();
    } catch (e: any) {
      alert("Action error: " + (e?.message || e));
    } finally {
      setActionBusy(false);
    }
  }

  const cpuClr  = colorFor(snap.cpu,  "cpu");
  const memClr  = colorFor(snap.mem,  "mem");
  const diskClr = colorFor(snap.disk, "disk");

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8 space-y-6">
      <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-800 text-center">
        VPS Monitoring Console
      </h1>

      {/* Connexion / contrôles */}
      <div className="rounded-xl p-4 border border-slate-200 bg-white shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <Field label="API URL">
            <input
              className="border rounded-md p-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-400"
              value={apiRoot}
              onChange={(e) => setApiRoot(e.target.value)}
              placeholder="/api"
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
        </div>
      </div>

      {/* KPIs */}
      <div className="grid gap-4 md:grid-cols-3">
        <Kpi title="CPU"     value={pct(snap.cpu)}  textClass={cpuClr.text}  barClass={cpuClr.bar}  />
        <Kpi title="Mémoire" value={pct(snap.mem)}  textClass={memClr.text}  barClass={memClr.bar}  />
        <Kpi title="Disque /" value={pct(snap.disk)} textClass={diskClr.text} barClass={diskClr.bar} />
      </div>

      {/* Graphiques */}
      <div className="grid gap-6 xl:grid-cols-3">
        <Timeseries title="CPU (%)"     data={cpu}  stroke={PALETTE.cpu.stroke}  border={PALETTE.cpu.border}  from={PALETTE.cpu.gradFrom}  via={PALETTE.cpu.gradVia}  gid="cpu" />
        <Timeseries title="Mémoire (%)" data={mem}  stroke={PALETTE.mem.stroke}  border={PALETTE.mem.border}  from={PALETTE.mem.gradFrom}  via={PALETTE.mem.gradVia}  gid="mem" />
        <Timeseries title="Disque (%)"  data={disk} stroke={PALETTE.disk.stroke} border={PALETTE.disk.border} from={PALETTE.disk.gradFrom} via={PALETTE.disk.gradVia} gid="disk" />
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
              value={target} onChange={(e) => setTarget(e.target.value)} placeholder="ex: nginx"
            />
          </div>
          <button
            onClick={restartContainer}
            disabled={actionBusy}
            className="rounded-md px-4 py-2 font-medium
                       !bg-emerald-600 text-white
                       hover:!bg-emerald-500 active:!bg-emerald-700
                       disabled:!bg-emerald-400 disabled:opacity-60 shadow-sm"
          >
            {actionBusy ? "…" : "Redémarrer le conteneur"}
          </button>
        </div>

        {/* Journal d'actions auto (affiché seulement si l'API existe) */}
        {actions.length > 0 && (
          <div className="mt-4">
            <div className="text-xs text-slate-500 mb-1">Dernières actions automatiques</div>
            <ul className="text-sm list-disc pl-5 space-y-1">
              {actions.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </div>
        )}
      </div>

      <p className="text-xs text-center text-slate-500">
        Données: Prometheus • Actions: API FastAPI (CrewAI) • Refresh auto 15s
      </p>
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

function Kpi({ title, value, textClass, barClass }:
  { title: string; value?: string; textClass: string; barClass: string }) {
  return (
    <div className="rounded-xl p-4 border border-slate-200 bg-white shadow-sm">
      <div className="text-sm text-slate-600 mb-2">{title}</div>
      <div className={`h-1.5 w-16 rounded-full mb-3 ${barClass}`} />
      <div className={`text-3xl font-semibold ${textClass}`}>{value || "—"}</div>
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
            <Area type="monotone" dataKey="value" stroke={stroke} fill={`url(#${gid})`} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
