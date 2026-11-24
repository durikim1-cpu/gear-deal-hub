"""Zero-cost public trend & deal signal collector (Reddit JSON + local inbox)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REDDIT_FEEDS = [
    "https://www.reddit.com/r/buildapcsales/hot.json?limit=15",
    "https://www.reddit.com/r/UsbCHardware/hot.json?limit=10",
]


def fetch_reddit_signals(timeout_sec: int = 6) -> list[dict]:
    """Fetch public deal posts when network is reachable; gracefully skip if offline."""
    signals: list[dict] = []
    headers = {"User-Agent": "GearCompareHubBot/1.0 (deal-trend-monitor)"}
    for url in REDDIT_FEEDS:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            for child in payload.get("data", {}).get("children", []):
                post = child.get("data", {})
                if post.get("stickied"):
                    continue
                signals.append(
                    {
                        "source": "reddit",
                        "subreddit": post.get("subreddit", ""),
                        "title": post.get("title", ""),
                        "score": post.get("score", 0),
                        "permalink": f"https://www.reddit.com{post.get('permalink', '')}",
                    }
                )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            # Offline/sandboxed execution falls back cleanly without crashing
            continue
    return signals


def collect_candidates(project_root: Path, live_network: bool = False) -> dict:
    """Merge existing catalog with inbox candidates and optional live trend signals."""
    data_dir = project_root / "data"
    catalog = json.loads((data_dir / "products.json").read_text(encoding="utf-8"))
    inbox_path = data_dir / "candidates_inbox.json"
    inbox = json.loads(inbox_path.read_text(encoding="utf-8")) if inbox_path.exists() else []

    by_id = {item["id"]: item for item in catalog}
    for candidate in inbox:
        by_id[candidate["id"]] = candidate

    signals = fetch_reddit_signals() if live_network else []
    staged = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "candidates": list(by_id.values()),
        "trend_signals_count": len(signals),
        "trend_signals_preview": signals[:5],
    }
    (data_dir / "candidates_staged.json").write_text(
        json.dumps(staged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return staged
