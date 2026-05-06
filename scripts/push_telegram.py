import json
import os
import requests
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
LATEST_FILE = BASE_DIR / "data" / "latest.json"


def load_news():
    if not LATEST_FILE.exists():
        raise FileNotFoundError("data/latest.json not found")

    with open(LATEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_message(items, max_items=12):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append(f"📰 今日热点新闻推送")
    lines.append(f"更新时间：{now}")
    lines.append("")

    selected = items[:max_items]

    for index, item in enumerate(selected, start=1):
        title = item.get("title", "").strip()
        source = item.get("source", "").strip()
        category = item.get("category", "").strip()
        link = item.get("link", "").strip()

        if not title or not link:
            continue

        lines.append(f"{index}. {title}")
        lines.append(f"来源：{source}｜分类：{category}")
        lines.append(link)
        lines.append("")

    message = "\n".join(lines)

    # Telegram 单条消息不能太长，这里做一个保守截断
    if len(message) > 3800:
        message = message[:3800] + "\n\n内容较多，已截断。"

    return message


def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise ValueError("Missing TELEGRAM_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=20,
    )

    response.raise_for_status()
    print("Telegram message sent successfully.")


def main():
    items = load_news()
    message = build_message(items)
    send_telegram(message)


if __name__ == "__main__":
    main()
