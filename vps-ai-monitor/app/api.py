
from fastapi import FastAPI, HTTPException, APIRouter
from app.tools.actions import Actions
import os, time, asyncio
import httpx
from fastapi.middleware.cors import CORSMiddleware
from .routers.inventory import router as containers_router
from .routers.actions_log import router as actions_log_router

router = APIRouter()
app = FastAPI(title="VPS AI Monitor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
actions = Actions(rules_path="rules.yaml")

app.include_router(containers_router)
app.include_router(actions_log_router)

PROM = os.getenv("PROM_URL", "http://prometheus:9090")

async def prom_query(q: str):
    async with httpx.AsyncClient(timeout=8) as c:
        r = await c.get(f"{PROM}/api/v1/query", params={"query": q})
        r.raise_for_status()
        j = r.json()
        if j.get("status") != "success" or not j["data"]["result"]:
            return None
        try:
            return float(j["data"]["result"][0]["value"][1])
        except Exception:
            return None

def prom_expr(metric: str) -> str:
    if metric == "cpu":
        return '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'
    if metric == "mem":
        return '100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)'
    if metric == "disk":
        return ('100 * (1 - (sum by (instance) (node_filesystem_free_bytes'
                '{mountpoint="/",fstype!~"tmpfs|overlay"}) / '
                'sum by (instance) (node_filesystem_size_bytes'
                '{mountpoint="/",fstype!~"tmpfs|overlay"})))')
    raise HTTPException(400, "unknown metric")

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/snapshot")
async def snapshot():
    cpu_q = prom_expr("cpu")
    mem_q = prom_expr("mem")
    disk_q = prom_expr("disk")
    cpu, mem, disk = await asyncio.gather(
        prom_query(cpu_q), prom_query(mem_q), prom_query(disk_q)
    )
    return {"cpu": cpu, "mem": mem, "disk": disk}

@app.get("/api/history")
async def history(metric: str, minutes: int = 60, step: str = "15s"):
    q = prom_expr(metric)
    now = int(time.time())
    start = now - minutes * 60
    async with httpx.AsyncClient(timeout=None) as c:
        r = await c.get(
            f"{PROM}/api/v1/query_range",
            params={"query": q, "start": start, "end": now, "step": step},
        )
        r.raise_for_status()
        return r.json()["data"]

# (facultatif) action de redémarrage d’un conteneur si /var/run/docker.sock est monté
@app.post("/api/actions/restart-container")
async def restart_container(payload: dict):
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(400, "missing 'name'")
    # version 'docker cli' simple; remplace par docker SDK si tu préfères
    import subprocess
    p = subprocess.run(["docker", "restart", name], capture_output=True, text=True)
    if p.returncode != 0:
        raise HTTPException(500, p.stderr.strip() or "restart failed")
    return {"result": p.stdout.strip() or "restarted"}

@router.get("/api/containers")
def api_containers():
    return {"containers": actions.docker_list()}

@router.post("/api/containers/{name}/{op}")
def api_container_control(name: str, op: str):
    return actions.docker_control(name, op)
