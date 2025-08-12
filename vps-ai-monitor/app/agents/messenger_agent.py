from crewai import Agent
from app.tools.notify import notify_slack, notify_telegram

class MessengerAgent:
    def __init__(self, llm):
        self.agent = Agent(
            role="Notifier",
            goal="Informer de façon concise, actionnable.",
            backstory="Sait adapter le niveau de détail.",
            allow_delegation=False,
            llm=llm
        )

    def send(self, title: str, details: str):
        text = f"*{title}*\n{details}"
        r1 = notify_slack(text)
        r2 = notify_telegram(text)
        return f"{r1} | {r2}"
