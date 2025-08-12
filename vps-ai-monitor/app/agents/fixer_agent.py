import time
import yaml
from crewai import Agent
from app.tools.actions import Actions

class FixerAgent:
    def __init__(self, llm, rules_path="rules.yaml"):
        self.actions = Actions(rules_path)
        self.rules = yaml.safe_load(open(rules_path))
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
            results.append(self.actions.restart_service("nginx"))
            time.sleep(2)
        return results
