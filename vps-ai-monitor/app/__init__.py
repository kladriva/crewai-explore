import os
from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="VPS AI Monitor API")

API_TOKEN = os.getenv("API_TOKEN", "").strip()

def check_token(x_api_key: str | None):
    if API_TOKEN and (x_api_key or "").strip() != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Tu pourras ajouter les endpoints réels ici en important tes agents :
# from app.llm import build_llm
# from app.agents.monitor_agent import MonitorAgent
# from app.agents.fixer_agent import FixerAgent
# llm = build_llm()
# monitor = MonitorAgent(llm)
# fixer = FixerAgent(llm)
#
# @app.get("/api/snapshot")
# def get_snapshot(x_api_key: str | None = Header(None, alias="X-API-Key")):
#     check_token(x_api_key)
#     snap = monitor.snapshot()
#     # si tu as une analyse séparée :
#     # analysis = monitor.analyze(snap)
#     return {"snapshot": snap}
