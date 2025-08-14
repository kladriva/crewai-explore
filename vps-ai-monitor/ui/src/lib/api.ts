export function apiBase(): string {
  // Si l'utilisateur a saisi une URL absolue (champ "API URL" de l'UI, stocké en localStorage)
  const saved = localStorage.getItem("apiUrl")?.trim();
  if (saved && !saved.startsWith("/")) {
    // On force un suffixe /api sans doublon
    return `${saved.replace(/\/+$/, "")}/api`;
  }

  // En build de prod (servi derrière Nginx) on utilise le proxy relatif
  if (import.meta.env.PROD) return "/api";

  // En dev (vite) on tape directement l'API exposée par l'agent
  return "http://localhost:8010/api";
}

type FetchOpts = RequestInit & { apiKey?: string };

export async function apiFetch(path: string, opts: FetchOpts = {}) {
  const base = apiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  // Ajoute X-API-Key automatiquement si fournie
  const headers: Record<string, string> = { ...(opts.headers as any) };
  if (opts.apiKey) headers["X-API-Key"] = opts.apiKey;

  const res = await fetch(url, { ...opts, headers });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res;
}
