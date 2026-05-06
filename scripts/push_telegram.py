import json
import os
import time
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
LATEST_FILE = BASE_DIR / "data" / "latest.json"

# Telegram 单条消息硬限制 4096 字符，留余量用 3800
MAX_MESSAGE_LENGTH = 3800
# 头部预留空间（标题、时间戳、页码等）
HEADER_RESERVE = 200
# 每条消息之间的延迟（秒），避免触发 Telegram 频率限制
SEND_DELAY_SECONDS = 1.5


def load_news():
    if not LATEST_FILE.exists():
        raise FileNotFoundError("data/latest.json not found")
    with open(LATEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def format_item(index, item):
    """格式化单条新闻。返回 None 表示该条无效需跳过。"""
    title = item.get("title", "").strip()
    source = item.get("source", "").strip()
    category = item.get("category", "").strip()
    link = item.get("link", "").strip()
    if not title or not link:
        return None
    lines = [
        f"{index}. {title}",
        f"来源：{source}｜分类：{category}",
        link,
        "",
    ]
    return "\n".join(lines)


def build_messages(items):
    """把所有新闻分页打包成多条消息，自动控制每条长度。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 先格式化所有有效新闻
    blocks = []
    valid_index = 1
    for item in items:
        block = format_item(valid_index, item)
        if block is None:
            continue
        blocks.append(block)
        valid_index += 1

    total = len(blocks)
    if total == 0:
        return []

    # 每页有效内容上限（扣除头部）
    effective_limit = MAX_MESSAGE_LENGTH - HEADER_RESERVE

    # 按长度分页
    chunks = []
    current = []
    current_len = 0
    for block in blocks:
        block_len = len(block) + 1  # +1 for joining newline
        if current and current_len + block_len > effective_limit:
            chunks.append(current)
            current = [block]
            current_len = block_len
        else:
            current.append(block)
            current_len += block_len
    if current:
        chunks.append(current)

    # 拼接最终消息（含头部和页码）
    total_pages = len(chunks)
    messages = []
    for i, chunk in enumerate(chunks, start=1):
        if total_pages == 1:
            header = f"📰 今日热点新闻推送\n更新时间：{now}\n共 {total} 条\n\n"
        elif i == 1:
            header = f"📰 今日热点新闻推送 (1/{total_pages})\n更新时间：{now}\n共 {total} 条\n\n"
        else:
            header = f"📰 新闻推送续 ({i}/{total_pages})\n\n"
        messages.append(header + "\n".join(chunk))

    return messages


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


def send_with_retry(message, max_retries=2):
    """发送单条消息，遇到 429 限流自动等待重试。"""
    for attempt in range(max_retries + 1):
        try:
            send_telegram(message)
            return True
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                retry_after = 5
                try:
                    retry_after = int(e.response.json().get("parameters", {}).get("retry_after", 5))
                except Exception:
                    pass
                print(f"  Rate limited, waiting {retry_after}s before retry...")
                time.sleep(retry_after + 1)
                continue
            print(f"  HTTP error: {e}")
            return False
        except Exception as e:
            print(f"  Send error: {e}")
            return False
    return False


def main():
    items = load_news()
    messages = build_messages(items)
    if not messages:
        print("No news to send.")
        return

    print(f"Sending {len(messages)} message(s) covering {len(items)} news items.")
    success = 0
    for i, msg in enumerate(messages, start=1):
        print(f"Sending {i}/{len(messages)} ({len(msg)} chars)...")
        if send_with_retry(msg):
            success += 1
        if i < len(messages):
            time.sleep(SEND_DELAY_SECONDS)
    print(f"Done. {success}/{len(messages)} messages sent successfully.")


if __name__ == "__main__":
    main()
