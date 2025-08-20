
import { useEffect, useState } from "react";

type Port = { private: number; public?: number | null; protocol: string };
type Item = {
  id: string;
  name: string;
  image: string;
  state: string;            
  status?: string | null;   
  ports: Port[];
  first_deploy: string;     
  last_start?: string | null;
};

function apiBase(): string {
  // même logique que la page Monitoring : on lit localStorage
  const base =
    localStorage.getItem("apiUrl") ||
    (import.meta.env.PROD ? "/api" : "http://localhost:8000");
  return base.replace(/\/+$/, "");
}

async function apiJSON<T>(path: string, opt?: RequestInit): Promise<T> {
  const base = apiBase();
  const url = path.startsWith("/") ? base + path : base + "/" + path;

  const headers: HeadersInit = { "Content-Type": "application/json" };
  const apiKey = localStorage.getItem("apiKey");
  if (apiKey) (headers as any)["X-API-Key"] = apiKey;

  const r = await fetch(url, { ...opt, headers });
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`${r.status} ${r.statusText} – ${t}`);
  }
  return r.json();
}

function fmtDate(s?: string | null): string {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d.getTime())) return s;
  return d.toLocaleString();
}

function badgeClass(state: string): string {
  const up = state.toLowerCase() === "running";
  return up
    ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
    : "bg-rose-100 text-rose-700 border border-rose-200";
}

export default function ContainersPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyName, setBusyName] = useState<string | null>(null);


  async function load() {
    setLoading(true);
    try {
      const data = await apiJSON<Item[]>("/api/containers");
      setItems(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  async function toggle(name: string, running: boolean) {
    setBusyName(name);
    try {
      const path = running
        ? `/api/containers/${encodeURIComponent(name)}/stop`
        : `/api/containers/${encodeURIComponent(name)}/start`;
      await apiJSON(path, { method: "POST" });
      await load();
    } catch (e: any) {
      alert("Action échouée: " + (e?.message || e));
    } finally {
      setBusyName(null);
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-slate-800">
          Conteneurs Docker
        </h2>
        <button
          onClick={load}
          disabled={loading}
          className="rounded-md px-3 py-2 text-sm font-medium
                     bg-slate-700 text-white hover:bg-slate-600 active:bg-slate-800
                     disabled:opacity-60"
        >
          {loading ? "…" : "Rafraîchir"}
        </button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3 text-left">Nom</th>
              <th className="px-4 py-3 text-left">Image</th>
              <th className="px-4 py-3 text-left">Ports</th>
              <th className="px-4 py-3 text-left">1er déploiement</th>
              <th className="px-4 py-3 text-left">Dernier démarrage</th>
              <th className="px-4 py-3 text-left">État</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-500">
                  Aucun conteneur détecté.
                </td>
              </tr>
            )}

            {items.map((c) => {
              const running = c.state.toLowerCase() === "running";
              const ports =
                c.ports && c.ports.length
                  ? c.ports
                      .map((p) =>
                        p.public ? `${p.public}→${p.private}/${p.protocol}` : `${p.private}/${p.protocol}`
                      )
                      .join(", ")
                  : "—";

              return (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-medium text-slate-800">{c.name}</td>
                  <td className="px-4 py-3 text-slate-700">{c.image}</td>
                  <td className="px-4 py-3 text-slate-700">{ports}</td>
                  <td className="px-4 py-3 text-slate-700">{fmtDate(c.first_deploy)}</td>
                  <td className="px-4 py-3 text-slate-700">{fmtDate(c.last_start)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-1 rounded-md text-xs ${badgeClass(c.state)}`}>
                      {running ? "Up" : "Down"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => toggle(c.name, running)}
                      disabled={busyName === c.name}
                      className={`rounded-md px-3 py-2 text-sm font-medium shadow-sm
                                 ${running
                                   ? "bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white"
                                   : "bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white"}
                                 disabled:opacity-60`}
                    >
                      {busyName === c.name ? "…" : running ? "Arrêter" : "Lancer"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500">
        Source: Docker Engine via socket <code>/var/run/docker.sock</code>
      </p>
    </div>
  );
}
