from crewai import Agent
from app.tools.prom import PromClient
from app.tools.logs import tail_journal

class MonitorAgent:
    def __init__(self, llm):
        self.prom = PromClient()
        self.agent = Agent(
            role="Système Observer",
            goal="Synthétiser l'état actuel (CPU, RAM, Disque) et signaux de logs.",
            backstory="Expert monitoring Linux.",
            allow_delegation=False,
            llm=llm
        )

    def snapshot(self):
        cpu = self.prom.cpu_usage()
        mem = self.prom.mem_usage()
        disk = self.prom.disk_usage_root()
        logs = tail_journal(lines=80)

        return {"cpu": cpu, "mem": mem, "disk": disk, "logs_tail": logs[-5:]}
