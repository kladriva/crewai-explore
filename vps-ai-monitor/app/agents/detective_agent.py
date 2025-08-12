from crewai import Agent
from app.tools.anomaly import zscore_anomaly, mad_anomaly

def _extract_scalar(result):
    # Prom renvoie des séries; ici on simplifie: on prend la première valeur quand dispo
    try:
        if result and 'value' in result[0]:
            return float(result[0]['value'][1])
    except Exception:
        pass
    return None

class DetectiveAgent:
    def __init__(self, llm):
        self.agent = Agent(
            role="Analyste Anomalies",
            goal="Détecter anomalies et produire une explication claire.",
            backstory="Séries temporelles, SRE pragmatique.",
            allow_delegation=False,
            llm=llm
        )

    def analyze(self, snapshot, history=None):
        cpu = _extract_scalar(snapshot["cpu"])
        mem = _extract_scalar(snapshot["mem"])
        disk = _extract_scalar(snapshot["disk"])

        suspicions = []
        if cpu is not None and cpu > 90: suspicions.append(f"CPU très élevé ({cpu:.1f}%)")
        if mem is not None and mem > 90: suspicions.append(f"RAM très élevée ({mem:.1f}%)")
        if disk is not None and disk > 85: suspicions.append(f"Disque presque plein ({disk:.1f}%)")

        explanation = " ; ".join(suspicions) if suspicions else "Rien de critique."
        return {"anomaly": bool(suspicions), "explanation": explanation}
