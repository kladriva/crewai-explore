import os, requests
from telegram import Bot

def notify_slack(text: str):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url: return "Slack non configuré"
    r = requests.post(url, json={"text": text}, timeout=5)
    return "Slack OK" if r.ok else f"Slack error {r.status_code}"

def notify_telegram(text: str):
    tok = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not tok or not chat: return "Telegram non configuré"
    Bot(tok).send_message(chat_id=chat, text=text)
    return "Telegram OK"
