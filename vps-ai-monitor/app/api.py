import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

# ---- déjà présent ----
app = FastAPI(title="VPS AI Monitor API")
API_TOKEN = os.getenv("API_TOKEN", "").strip()

def check_token(x_api_key: str | None):
    if API_TOKEN and (x_api_key or "").strip() != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/api/health")
def health():
    return {"status": "ok"}

# ---- nouveau : monitoring / snapshot ----
try:
    # importe le client Prometheus de ton POC
    from app.tools.prom import PromClient
except Exception as e:
    PromClient = None

@app.get("/api/snapshot")
def get_snapshot(x_api_key: str | None = Header(None, alias="X-API-Key")):
    check_token(x_api_key)
    if PromClient is None:
        raise HTTPException(500, "Prometheus client not available")
    prom = PromClient()
    return {
        "cpu": prom.cpu_usage(),     # % CPU
        "mem": prom.mem_usage(),     # % mémoire
        "disk": prom.disk_usage(),   # % disque
    }

# ---- nouveau : actions (restart container) ----
class RestartReq(BaseModel):
    name: str  # nom du conteneur à redémarrer (ex: "prometheus")

@app.post("/api/actions/restart-container")
def restart_container(
    body: RestartReq,
    x_api_key: str | None = Header(None, alias="X-API-Key")
):
    check_token(x_api_key)
    try:
        import docker  # SDK officiel
    except Exception:
        raise HTTPException(500, "Docker SDK not installed")

    try:
        cli = docker.DockerClient(base_url="unix:///var/run/docker.sock")
        c = cli.containers.get(body.name)
        c.restart()
        return {"ok": True, "container": body.name}
    except Exception as e:
        raise HTTPException(500, f"Restart failed: {e}")
