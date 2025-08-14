from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, time
from app.tools.prom import PromClient
from app.tools.actions import Actions

API_TOKEN = os.getenv("API_TOKEN")  

app = FastAPI(title="AI Monitoring API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

prom = PromClient()
rules_path = os.path.join(os.path.dirname(__file__), "rules.yaml")
actions = Actions(rules_path if os.path.isfile(rules_path) else "rules.yaml")

def auth(x_api_key: str | None = Header(default=None)):
    if API_TOKEN and x_api_key != API_TOKEN:
        raise HTTPException(401, "Invalid API key")
    return True

class RestartReq(BaseModel):
    name: str

def _scalar(res):
    try:
        return float(res[0]["value"][1])
    except Exception:
        return None

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/snapshot")
def snapshot(_: bool = Depends(auth)):
    cpu = _scalar(prom.cpu_usage())
    mem = _scalar(prom.mem_usage())
    disk = _scalar(prom.disk_usage_root())
    return {"cpu": cpu, "mem": mem, "disk": disk}

@app.get("/api/history")
def history(metric: str = "cpu", minutes: int = 60, step: str = "15s", _: bool = Depends(auth)):
    end = int(time.time()); start = end - minutes * 60
    if metric == "cpu":
        q = '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'
    elif metric == "mem":
        q = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
    elif metric == "disk":
        q = '100 - (node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}) * 100'
    else:
        q = metric
    data = prom.query_range(q, start, end, step)
    series = []
    for s in data:
        pts = []
        for t, v in s.get("values", []):
            try:
                pts.append([int(t), float(v)])
            except Exception:
                pass
        series.append({"metric": s.get("metric", {}), "values": pts})
    return {"series": series, "from": start, "to": end, "step": step}

@app.post("/api/actions/restart-container")
def restart_container(req: RestartReq, _: bool = Depends(auth)):
    res = actions.restart_container(req.name)
    return {"result": res}
