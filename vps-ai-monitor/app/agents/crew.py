# app/crew.py
import os, time
from dotenv import load_dotenv
from crewai import Crew, Process
from app.llm import build_llm
from app.agents.monitor_agent import MonitorAgent
from app.agents.detective_agent import DetectiveAgent
from app.agents.fixer_agent import FixerAgent
from app.agents.messenger_agent import MessengerAgent

def main():
    load_dotenv()
    llm = build_llm()

    monitor = MonitorAgent(llm)
    detective = DetectiveAgent(llm)
    fixer = FixerAgent(llm)
    messenger = MessengerAgent(llm)

    while True:
        snap = monitor.snapshot()
        analysis = detective.analyze(snap)
        if analysis["anomaly"]:
            actions = fixer.apply(analysis)
            details = analysis["explanation"] + ("\nActions: " + "; ".join(actions) if actions else "")
            messenger.send("Incident détecté (POC)", details)
        time.sleep(60)

if __name__ == "__main__":
    main()
