// src/MonitoringConsole.tsx
import React, { useEffect, useMemo, useState, useCallback } from "react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

type Point = { time: string; value: number };
type Snapshot = { cpu?: number; mem?: number; disk?: number };

const DEFAULT_API = import.meta.env.PROD ? "/api" : "http://localhost:8000";

// Seuils par métrique (editable)
const THRESHOLDS: Record<"cpu" | "mem" | "disk", { warn: number; crit: number }> = {
  cpu:  { warn: 70, crit: 90 },
  mem:  { warn: 80, crit: 90 },
  disk: { warn: 80, crit: 90 },
};
type Sev = "ok" | "warn" | "crit";
const sevOf = (metric: keyof typeof THRESHOLDS, v?: number): Sev => {
  if (!isFinite(v ?? NaN)) return "ok";
  const { warn, crit } = THRESHOLDS[metric];
  if ((v ?? 0) >= crit) return "crit";
  if ((v ?? 0) >= warn) return "warn";
  return "ok";
};

// Couleurs dynamiques pour KPI (texte + chip) selon la sévérité
const SEV_STYLE: Record<Sev, { text: string; chip: string }> = {
  ok:   { text: "text-emerald-700", chip: "bg-emerald-500" },
  warn: { text: "text-amber-600",   chip: "bg-amber-500"   },
  crit: { text: "text-rose-600",    chip: "bg-rose-500"    },
};

// Couleurs des graphes (on reste pastel par métrique)
const CHART_STYLE = {
  cpu:  { stroke: "#f59e0b", border: "border-amber-200",  from: "from-amber-50",  via: "via-amber-50/60"  },
  mem:  { stroke: "#06b6d4", border: "border-cyan-200",   from: "from-cyan-50",   via: "via-cyan-50/60"   },
  disk: { stroke: "#8b5cf6", border: "border-violet-200", from: "from-violet-50", via: "via-violet-50/60" },
};

const fmtPct = (n?: number) =>
  typeof n === "number" && isFinite(n) ? `${n.toFixed(1)}%` : "—";

const toLabel = (ts: number) =>
  new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, ms = 7000) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), ms);
  const merged = { ...init, signal: ctrl.signal };
  return fetch(input, merged).finally(() => clearTimeout(id));
}

type EventItem = { time: string; message: string; severity?: Sev; source?: "api" | "local" };

export default function MonitoringConsole() {
  // --- état de page ---
  const [apiUrl, setApiUrl] = useState(localStorage.getItem("apiUrl") || DEFAULT_API);
  const [apiKey, setApiKey] = useState(localStorage.getItem("apiKey") || "");
  const [minutes, setMinutes] = useState(15);
  const [loading, setLoading] = useState(false);

  const [snap, setSnap] = useState<Snapshot>({});
  const [cpu, setCpu] = useState<Point[]>([]);
  const [mem, setMem] = useState<Point[]>([]);
  const [disk, setDisk] = useState<Point[]>([]);

  // suivi de sévérité précédente pour détecter franchissements
  const [prevSev, setPrevSev] = useState<{ cpu: Sev; mem: Sev; disk: Sev }>({
    cpu: "ok", mem: "ok", disk: "ok",
  });

  // événements (API si dispo + locaux)
  const [events, setEvents] = useState<EventItem[]>([]);

  const [target, setTarget] = useState("nginx");
  const [actionBusy, setActionBusy] = useState(false);

  useEffect(() => localStorage.setItem("apiUrl", apiUrl), [apiUrl]);
  useEffect(() => localStorage.setItem("apiKey", apiKey), [apiKey]);

  const headersInit = useMemo<HeadersInit | undefined>(
    () => (apiKey ? { "X-API-Key": apiKey } : undefined),
    [apiKey]
  );
  const reqInit = useCallback((): RequestInit => (headersInit ? { headers: headersInit } : {}), [headersInit]);

  // --- fetch snapshot + history ---
  async function fetchSnapshot() {
    const r = await fetchWithTimeout(`${apiUrl}/api/snapshot`, reqInit());
    const j = await r.json();
    setSnap({ cpu: j.cpu, mem: j.mem, disk: j.disk });

    // détection des franchissements -> événement local
    const sev = {
      cpu: sevOf("cpu", j.cpu),
      mem: sevOf("mem", j.mem),
      disk: sevOf("disk", j.disk),
    };
    (["cpu", "mem", "disk"] as const).forEach((m) => {
      if (sev[m] === "crit" && prevSev[m] !== "crit") {
        setEvents((E) => [
          {
            time: new Date().toLocaleTimeString(),
            message: `Seuil critique atteint: ${m.toUpperCase()} = ${fmtPct(j[m as keyof Snapshot] as number)}`,
            severity: "crit",
            source: "local",
          },
          ...E,
        ]);
      }
    });
    setPrevSev(sev);
  }

  // l’API renvoie .result[0].values (format Prometheus); on gère aussi .series[0].values.
  function parseHistory(j: any): Point[] {
    const arr = j?.result?.[0]?.values ?? j?.series?.[0]?.values ?? [];
    return arr
      .map((p: any[]) => ({ time: toLabel(Number(p[0])), value: Number(p[1]) }))
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

  // événements côté API si dispo
  async function tryFetchEvents() {
    try {
      const r = await fetchWithTimeout(`${apiUrl}/api/events?limit=20`, reqInit(), 5000);
      if (!r.ok) return; // silencieux si 404
      const data = await r.json();
      // normalisation légère: {time, message, severity?}
      const list: EventItem[] = Array.isArray(data)
        ? data.map((x: any) => ({
            time: x.time || x.ts || new Date().toLocaleTimeString(),
            message: x.message || x.msg || JSON.stringify(x),
            severity: (x.severity as Sev) || undefined,
            source: "api",
          }))
        : [];
      if (list.length) setEvents((E) => [...list, ...E].slice(0, 50));
    } catch {/* ignore si endpoint absent */}
  }

  async function refreshAll() {
    setLoading(true);
    try {
      await Promise.all([
        fetchSnapshot(),
        fetchHistory("cpu"),
        fetchHistory("mem"),
        fetchHistory("disk"),
        tryFetchEvents(),
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
      setEvents((E) => [
        {
          time: new Date().toLocaleTimeString(),
          message: `Redémarrage demandé pour "${target}": ${j.result || "OK"}`,
          severity: "warn",
          source: "api",
        },
        ...E,
      ]);
      alert(j.result || JSON.stringify(j));
    } catch (e: any) {
      alert("Action error: " + (e?.message || e));
    } finally {
      setActionBusy(false);
    }
  }

  const resetApiUrl = () => setApiUrl(DEFAULT_API);

  // ---- RENDER ----
  return (
    <div className="min-h-screen bg-slate-50 flex justify-center">
      <main className="w-full max-w-screen-2xl px-6 py-8 space-y-6">
        <h1 className="text-5xl font-extrabold tracking-tight text-slate-800 text-center mb-2">
          VPS Monitoring Console
        </h1>

        {/* Barre de contrôle */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 items-end">
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
                className="rounded-md px-3 py-2 text-sm font-medium
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

          {/* Bouton bien vert, même en disabled */}
          <div className="flex items-end">
            <button
              onClick={refreshAll}
              disabled={loading}
              className="inline-flex items-center justify-center w-full rounded-lg px-4 py-2
                         font-semibold text-white shadow-sm ring-1 ring-emerald-200
                         bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700
                         disabled:opacity-60 disabled:hover:bg-emerald-600 disabled:cursor-not-allowed"
            >
              {loading ? "…" : "Rafraîchir"}
            </button>
          </div>
        </div>

        {/* KPIs (couleur dynamique selon le taux) */}
        <div className="grid gap-4 md:grid-cols-3">
          <Kpi metric="cpu"  value={snap.cpu} />
          <Kpi metric="mem"  value={snap.mem} />
          <Kpi metric="disk" value={snap.disk} />
        </div>

        {/* Graphes */}
        <div className="grid gap-6 xl:grid-cols-3">
          <Timeseries
            title="CPU (%)"   data={cpu}
            stroke={CHART_STYLE.cpu.stroke}  border={CHART_STYLE.cpu.border}
            from={CHART_STYLE.cpu.from}      via={CHART_STYLE.cpu.via} gid="cpu"
          />
          <Timeseries
            title="Mémoire (%)" data={mem}
            stroke={CHART_STYLE.mem.stroke}  border={CHART_STYLE.mem.border}
            from={CHART_STYLE.mem.from}      via={CHART_STYLE.mem.via} gid="mem"
          />
          <Timeseries
            title="Disque (%)"  data={disk}
            stroke={CHART_STYLE.disk.stroke} border={CHART_STYLE.disk.border}
            from={CHART_STYLE.disk.from}     via={CHART_STYLE.disk.via} gid="disk"
          />
        </div>

        {/* Actions manuelles */}
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
              className="inline-flex items-center justify-center rounded-lg px-4 py-2
                         font-semibold text-white shadow-sm ring-1 ring-emerald-200
                         bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700
                         disabled:opacity-60 disabled:hover:bg-emerald-600"
            >
              {actionBusy ? "…" : "Redémarrer le conteneur"}
            </button>
          </div>
        </div>

        {/* Evénements (actions auto + franchissements locaux) */}
        <div className="rounded-xl p-4 border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-slate-700">Événements récents</h2>
            <button
              onClick={() => setEvents([])}
              className="text-xs rounded px-2 py-1 bg-slate-100 hover:bg-slate-200"
            >
              Effacer
            </button>
          </div>
          {events.length === 0 ? (
            <p className="text-sm text-slate-500">
              Aucun événement pour l’instant. Si votre API expose <code>/api/events</code>,
              ils apparaîtront ici. Sinon, les franchissements de seuils critiques sont journalisés localement.
            </p>
          ) : (
            <ul className="space-y-1 text-sm">
              {events.slice(0, 20).map((e, i) => (
                <li key={i} className="flex gap-2 items-start">
                  <span className="text-xs text-slate-400 mt-[2px]">{e.time}</span>
                  <span
                    className={
                      e.severity === "crit" ? "text-rose-600" :
                      e.severity === "warn" ? "text-amber-600" : "text-slate-700"
                    }
                  >
                    {e.message}
                    {e.source ? <span className="text-slate-400"> · {e.source}</span> : null}
                  </span>
                </li>
              ))}
            </ul>
          )}
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

function Kpi({ metric, value }: { metric: "cpu" | "mem" | "disk"; value?: number }) {
  const sev = sevOf(metric, value);
  const { text, chip } = SEV_STYLE[sev];
  return (
    <div className="rounded-xl p-4 border border-slate-200 bg-white shadow-sm">
      <div className="text-sm text-slate-600 mb-2">
        {metric === "cpu" ? "CPU" : metric === "mem" ? "Mémoire" : "Disque /"}
      </div>
      <div className={`h-1.5 w-16 rounded-full mb-3 ${chip}`} />
      <div className={`text-3xl font-semibold ${text}`}>{fmtPct(value)}</div>
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
