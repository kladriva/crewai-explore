import { useEffect, useMemo, useState } from "react";

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
  const [query, setQuery] = useState("");


  const rawApiUrl =
    localStorage.getItem("apiUrl") ||
    (import.meta.env.PROD ? "/api" : "http://localhost:8000");
  const apiUrl = rawApiUrl.replace(/\/+$/, "");
  const base = /\/api$/.test(apiUrl) ? apiUrl : `${apiUrl}/api`;

  const apiKey = localStorage.getItem("apiKey") || "";
  const headers: HeadersInit = apiKey ? { "X-API-Key": apiKey } : {};

  async function load() {
    setLoading(true);
    try {
      const res = await fetch(`${base}/containers`, { headers });
      if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
      const j = await res.json();
      const list: Item[] = Array.isArray(j) ? j : (j?.containers ?? j?.items ?? []);
      setItems(Array.isArray(list) ? list : []);
    } catch (e) {
      console.error("containers load:", e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  async function control(name: string, op: "start" | "stop" | "restart") {
    setBusyName(`${name}:${op}`);
    try {
      const res = await fetch(
        `${base}/containers/${encodeURIComponent(name)}/${op}`,
        { method: "POST", headers }
      );
      const j = await res.json().catch(() => ({}));
      if (!res.ok || j?.ok === false) throw new Error(j?.error || res.statusText);
      await load();
    } catch (e: any) {
      alert(`Action ${op} sur ${name} : ${e?.message || e}`);
    } finally {
      setBusyName(null);
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [base, apiKey]);

  // --- filtrage client ------------------------------------------------------
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((c) => {
      const inName = c.name.toLowerCase().includes(q);
      const inImage = (c.image || "").toLowerCase().includes(q);
      const inPorts =
        c.ports?.some(
          (p) =>
            String(p.public ?? "").includes(q) ||
            String(p.private).includes(q) ||
            p.protocol.toLowerCase().includes(q)
        ) || false;
      return inName || inImage || inPorts;
    });
  }, [items, query]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-2xl font-semibold text-slate-800">Conteneurs Docker</h2>
        <div className="flex items-center gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filtrer (nom, image, port...)"
            className="border rounded-md px-3 py-2 text-sm
                       focus:outline-none focus:ring-2 focus:ring-sky-400"
          />
          <button
            onClick={load}
            disabled={loading}
            className="rounded-md px-3 py-2 text-sm font-medium
                       text-white hover:bg-slate-600
                       !bg-emerald-600 text-white
                        hover:!bg-emerald-500 active:!bg-emerald-700
                        disabled:!bg-emerald-400 disabled:text-white disabled:opacity-100
                        disabled:cursor-not-allowed shadow-sm transition-colors
                       disabled:opacity-60"
          >
            {loading ? "…" : "Rafraîchir"}
          </button>
        </div>
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
            {filtered.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-500">
                  {items.length ? "Aucun résultat pour ce filtre." : "Aucun conteneur détecté."}
                </td>
              </tr>
            )}

            {filtered.map((c) => {
              const running = c.state.toLowerCase() === "running";
              const ports =
                c.ports?.length
                  ? c.ports
                      .map((p) =>
                        p.public
                          ? `${p.public}→${p.private}/${p.protocol}`
                          : `${p.private}/${p.protocol}`
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
                  <td className="px-4 py-3">
                    <div className="flex justify-end items-center gap-2 whitespace-nowrap">
                      <button
                        onClick={() => control(c.name, running ? "stop" : "start")}
                        disabled={busyName === `${c.name}:${running ? "stop" : "start"}`}
                        className={`inline-flex items-center rounded-md px-3 py-2 text-sm font-medium shadow-sm
                          ${running
                            ? "bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white"
                            : "bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white"}
                          disabled:opacity-60`}
                      >
                        {busyName?.startsWith(`${c.name}:`) ? "…" : running ? "Arrêter" : "Lancer"}
                      </button>

                      <button
                        onClick={() => control(c.name, "restart")}
                        disabled={busyName === `${c.name}:restart`}
                        className="inline-flex items-center rounded-md px-3 py-2 text-sm font-medium
                                   bg-slate-700 hover:bg-slate-600 active:bg-slate-800
                                   text-white disabled:opacity-60"
                      >
                        {busyName === `${c.name}:restart` ? "…" : "Redémarrer"}
                      </button>
                    </div>
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
