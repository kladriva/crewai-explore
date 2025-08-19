# VPS AI Monitor — Monitoring + Actions (Prometheus · FastAPI · React)

Un système léger de **monitoring VPS** avec **actions automatiques** pilotées par un agent IA :

* **Prometheus** collecte les métriques (via **node-exporter**)
* **ai\_agent** (FastAPI + Python) expose une API `/api` et applique des **règles** (seuils CPU/Mémoire/Disque)
* **UI Web** (React + Vite + Tailwind) pour visualiser les courbes, les KPIs et déclencher des actions (ex: restart d’un conteneur)

---

## Aperçu

* **KPIs temps réel** : CPU, Mémoire, Disque
* **Courbes historiques** (fenêtres 15 min → 12 h)
* **Seuils colorés** (vert / ambre / rouge)
* **Actions auto** quand seuil critique (ex: redémarrer un service, vider le cache)
* **Journal des actions** dans l’UI

---

## Architecture

```
                ┌────────────────────────────┐
                │         UI (React)         │
                │  Vite + Tailwind           │
                │  Nginx (proxy /api → agent)│
                └────────────┬───────────────┘
                             │  /api
                             ▼
                 ┌───────────────────────────┐
                 │   ai_agent (FastAPI)      │
                 │ - /api/health             │
                 │ - /api/snapshot           │
                 │ - /api/history            │
                 │ - /api/actions/*          │
                 │ - /api/events             │
                 └────────────┬──────────────┘
                              │  PromQL
                              ▼
                 ┌───────────────────────────┐
                 │       Prometheus          │
                 └────────────┬──────────────┘
                              │
                              ▼
                 ┌───────────────────────────┐
                 │      Node Exporter         │
                 │ (métriques hôte :9100)     │
                 └───────────────────────────┘
```

---

## Structure des dossiers

```
vps-ai-monitor/
├─ app/                # ai_agent (FastAPI + règles)
│  ├─ app/             # code Python
│  ├─ rules.yaml       # règles & actions
│  └─ Dockerfile
├─ ui/                 # interface web (React)
│  ├─ src/
│  ├─ docker/nginx.conf
│  └─ Dockerfile
├─ prometheus/
│  └─ prometheus.yml   # scrape configs
├─ docker-compose.yml
└─ README.md
```

---

## Prérequis

* Docker + Docker Compose
* Ports libres (par défaut) :

  * **Prometheus** : `9091` (host → conteneur 9090)
  * **ai\_agent** : `8010` (host → conteneur 8000)
  * **UI** : `8091` (host → conteneur 80)
  * **node-exporter** : `9110` (optionnel en host)

---

##  Démarrage rapide

```bash
# 1) builder l'UI
docker compose build ui

# 2) tout démarrer
docker compose up -d

# 3) vérifier
curl -s http://localhost:8010/api/health
curl -s http://localhost:8091/api/health
```

Ouvre l’UI sur **[http://localhost:8091](http://localhost:8091)**
Dans le champ **API URL**, mets **`/api`** (le Nginx de l’UI proxifie vers l’agent).

---

## Configuration des services

### Variables d’environnement (ai\_agent)

* `PROM_URL` : URL Prometheus (ex. `http://prometheus:9090`)
* `PORT` : port interne de FastAPI (par défaut `8000`)
* `LOOP_INTERVAL` : période d’analyse (s)
* `API_TOKEN` / `X-API-Key` (facultatif) : clé d’API si tu veux protéger l’agent
* `READ_JOURNAL` : lecture journald (0/1) si activé dans tes outils

### Mapping de ports (par défaut)

* UI : `8091:80`
* ai\_agent : `8010:8000`
* Prometheus : `9091:9090`

---

## API de l’agent (FastAPI)

Prefix commun : **`/api`**

| Méthode | Endpoint                                      | Description                                      |
| ------: | --------------------------------------------- | ------------------------------------------------ |
|     GET | `/api/health`                                 | Status de l’agent `{status:"ok"}`                |
|     GET | `/api/snapshot`                               | KPIs courants `{cpu, mem, disk}` (en %)          |
|     GET | `/api/history?metric=cpu&minutes=60&step=15s` | Série temporelle PromQL                          |
|    POST | `/api/actions/restart-container`              | `{"name":"nginx"}` (whitelist dans `rules.yaml`) |
|     GET | `/api/events?limit=50`                        | Journal des actions auto (trié du plus récent)   |

> Si une `X-API-Key` est requise, envoie l’en-tête `X-API-Key: <clé>`.

---

## 🖥️ UI : utilisation

* **API URL** : `/api` (quand tu utilises l’image UI fournie — Nginx proxifie vers l’agent)
* **Fenêtre** : 15 min / 1 h / 3 h / 12 h
* **Codes couleur** (dynamiques selon seuils) :

  * **Vert** : OK
  * **Ambre** : alerte
  * **Rouge** : critique → **actions auto** éventuelles
* **Bloc “Dernières actions automatiques”** : liste live des actions déclenchées par les règles (`/api/events`)

---

## Seuils & règles (rules.yaml)

Exemple minimal (dans `app/rules.yaml`) :

```yaml
thresholds:
  cpu:
    warn: 70
    crit: 90
  mem:
    warn: 80
    crit: 90
  disk:
    warn: 80
    crit: 95

actions:
  # action exécutée si la mémoire atteint le seuil critique
  - id: clear-cache
    when: "mem >= crit"
    run: ["sh", "-lc", "sync; echo 3 > /proc/sys/vm/drop_caches || true"]
    description: "Purge du cache fichiers (drop_caches)"
    safe: true

  # action exécutée si le CPU est critique
  - id: restart-web
    when: "cpu >= crit"
    run: ["docker", "restart", "nginx"]
    description: "Redémarrage du conteneur nginx"
    whitelist: ["nginx"]

  # disque critique → alerte (exemple)
  - id: warn-disk
    when: "disk >= crit"
    run: ["sh", "-lc", "echo '[WARN] Disk critical'"]
    description: "Alerte: espace disque critique"
```

> Le moteur de règles de l’agent évalue `when` à chaque cycle et exécute `run` si condition vraie.
> L’agent pousse un **événement** dans son journal interne, visible via `/api/events` et dans l’UI.

---

## Commandes courantes

```bash
# Journaux (suivi)
docker compose logs -f ai_agent
docker compose logs -f ui
docker compose logs -f prometheus

# Rebuild UI si tu modifies le code
docker compose build ui --no-cache
docker compose up -d ui

# Recréation de l'agent (ex: si port modifié)
docker compose up -d --force-recreate --no-deps ai_agent
```

---

## Sécurité

* Active une **clé d’API** : mets `API_TOKEN` et exige l’en-tête `X-API-Key`
* Restreins les actions sensibles via **`whitelist`** dans `rules.yaml`
* N’expose pas Prometheus en public si ce n’est pas nécessaire

---

## Dépannage

* **UI 502 /api** :

  * Vérifie que **ai\_agent** répond sur `http://localhost:8010/api/health`
  * Vérifie le Nginx de l’UI (`docker/nginx.conf`) → proxy vers `host.docker.internal:8010`
* **ai\_agent restart loop** :

  * `docker compose logs -f ai_agent` → souvent une import/mauvaise variable d’env
* **Pas de métriques** :

  * `node_exporter` doit être up, Prometheus doit scraper `host.docker.internal:9100` ou l’instance voulue
* **Port déjà utilisé** :

  * Change les `ports:` dans `docker-compose.yml` (ex. `8010:8000`, `8091:80`)
  * Ou arrête le service occupant le port

---

## Roadmap (idées)

* Auth UI + RBAC de déclenchement d’actions
* Notifications (Slack/Telegram) configurables
* Actions “pilotées IA” plus fines (diagnostic + correctifs ciblés)
* Découverte automatique de cibles Prometheus

---

## Licence

MIT — utilise/étends librement.

