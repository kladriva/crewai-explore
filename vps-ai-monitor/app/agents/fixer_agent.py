import time
import yaml
from pathlib import Path
from crewai import Agent
from tools.actions import Actions

class FixerAgent:
    def __init__(self, llm, rules_path=None):
        # chemin du fichier à côté du code (app/rules.yaml)
        base = Path(__file__).resolve().parents[1]  # => /workspace/app
        rules_file = Path(rules_path) if rules_path else (base / "rules.yaml")
        self.actions = Actions(str(rules_file))
        self.agent = Agent(
            role="Remediator",
            goal="Appliquer des remédiations sûres, documentées et conformes aux règles.",
            backstory="SRE axé sécurité, whitelist stricte.",
            allow_delegation=False,
            llm=llm
        )

    def apply(self, analysis):
        results = []
        if "CPU" in analysis["explanation"]:
            # exemple d’action (voir note plus bas sur systemd dans un conteneur)
            results.append(self.actions.restart_service("nginx"))
            time.sleep(2)
        return results
