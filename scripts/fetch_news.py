import feedparser
import yaml
import json
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_DIR = BASE_DIR / "sources"
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = DATA_DIR / "archive"

DATA_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)


def load_sources():
    sources = []
    for file in SOURCES_DIR.glob("*.yml"):
        with open(file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
            sources.extend(data)
    return sources


def fetch_source(source):
    print(f"Fetching: {source['name']}")

    feed = feedparser.parse(source["url"])
    items = []

    for entry in feed.entries[:30]:
        item = {
            "source": source["name"],
            "category": source.get("category", "general"),
            "title": entry.get("title", "").strip(),
            "link": entry.get("link", "").strip(),
            "summary": entry.get("summary", "").strip(),
            "published": entry.get("published", ""),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

        if item["title"] and item["link"]:
            items.append(item)

    return items


def dedupe(items):
    seen = set()
    result = []

    for item in items:
        key = item["link"] or item["title"]
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def main():
    sources = load_sources()
    all_items = []

    for source in sources:
        try:
            all_items.extend(fetch_source(source))
        except Exception as e:
            print(f"Failed: {source.get('name')} - {e}")

    all_items = dedupe(all_items)

    latest_path = DATA_DIR / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    today = datetime.now().strftime("%Y-%m-%d")
    archive_path = ARCHIVE_DIR / f"{today}.json"

    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_items)} news items.")


if __name__ == "__main__":
    main()
