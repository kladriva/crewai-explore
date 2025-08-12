import os, time, logging
from dotenv import load_dotenv
from app.llm import build_llm
from app.agents.monitor_agent import MonitorAgent
from app.agents.detective_agent import DetectiveAgent
from app.agents.fixer_agent import FixerAgent
from app.agents.messenger_agent import MessengerAgent

def _scalar(result):
    try:
        if result and 'value' in result[0]:
            return float(result[0]['value'][1])
    except Exception:
        pass
    return None

def main():
    load_dotenv()
    # logging
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, level, logging.INFO),
                        format='[%(asctime)s] %(levelname)s %(message)s')

    logging.info("Starting AI agent (POC) ...")
    llm = build_llm()
    monitor = MonitorAgent(llm)
    detective = DetectiveAgent(llm)
    fixer = FixerAgent(llm)
    messenger = MessengerAgent(llm)

    interval = int(os.getenv("LOOP_INTERVAL", "60"))
    while True:
        try:
            snap = monitor.snapshot()
            cpu = _scalar(snap.get("cpu"))
            mem = _scalar(snap.get("mem"))
            disk = _scalar(snap.get("disk"))
            logging.info(f"Snapshot: cpu={cpu} mem={mem} disk={disk}")

            analysis = detective.analyze(snap)
            logging.info(f"Analysis: {analysis}")

            if analysis.get("anomaly"):
                actions = fixer.apply(analysis)
                details = analysis["explanation"] + (f" | Actions: {'; '.join(actions)}" if actions else "")
                res = messenger.send("Incident détecté (POC)", details)
                logging.info(f"Notify: {res}")
        except Exception:
            logging.exception("Main loop error")

        time.sleep(interval)

if __name__ == "__main__":
    main()
