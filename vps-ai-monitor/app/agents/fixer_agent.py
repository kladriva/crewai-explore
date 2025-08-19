import time
import yaml
from pathlib import Path
from crewai import Agent
from app.tools.actions import Actions
import time

class FixerAgent:
    def __init__(self, llm, rules_path: str = "rules.yaml"):
        self.llm = llm
        self.actions = Actions(rules_path)
        
        self.agent = Agent(
            role="Remediator",
            goal="Appliquer des remédiations sûres, documentées et conformes aux règles.",
            backstory="SRE axé sécurité, whitelist stricte.",
            allow_delegation=False,
            llm=llm
        )

    def _derive_triggers(self, analysis: dict) -> set[str]:
        triggers = set()
        exp = (analysis.get("explanation") or "").lower()
        if analysis.get("anomaly"):
            if "cpu" in exp:
                triggers.add("cpu_high")
            if "mémoire" in exp or "memory" in exp:
                triggers.add("mem_high")
            if "disque" in exp or "disk" in exp:
                triggers.add("disk_high")
        return triggers

    def apply(self, analysis):
        results = []
        triggers = self._derive_triggers(analysis)
        rules = getattr(self.actions, "rules", {}) or {}

        if not rules:
            if "cpu_high" in triggers:
                results.append(self.actions.restart_container("nginx"))
            if "mem_high" in triggers:
                results.append(self.actions.clear_cache(container="nginx", path="/var/cache/nginx"))
            return results

        for rule in rules.get("rules", []):
            trig = rule.get("trigger")
            if trig and trig in triggers:
                for act in rule.get("actions", []):
                    if isinstance(act, dict):
                        if "restart_container" in act:
                            name = act["restart_container"].get("name")
                            results.append(self.actions.restart_container(name))
                        elif "clear_cache" in act:
                            p = act["clear_cache"] or {}
                            results.append(self.actions.clear_cache(
                                container=p.get("container"),
                                path=p.get("path")
                            ))
                        elif "notify" in act:
                            msg = act["notify"]
                            results.append(self.actions.notify(msg))
                        elif "log" in act:
                            msg = act["log"]
                            results.append(self.actions.log(msg))
                time.sleep(1)  # petit délai entre lots d’actions
        return results

