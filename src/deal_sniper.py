"""Promo-code & deal-signal sniper with idempotency keys and Amazon price-tracking exclusion.

Implements Topic 1 & Topic 3 Consensus:
- Never tracks or alerts on Amazon price drops unless separate written approval is explicitly enabled.
- Generates deterministic `event_id` idempotency keys so retries never send duplicate notifications.
- Distinguishes genuine `live_matched` promo/signal events from local preview samples (zero daily spam).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROMO_CODE_RE = re.compile(
    r"(?:할인\s*코드|프로모션\s*코드|쿠폰\s*코드|코드|code|coupon|promo)\s*[:：=]?\s*([A-Z0-9]{4,16})\b",
    re.IGNORECASE,
)
HOT_KEYWORDS_RE = re.compile(
    r"(할인코드|프로모션|쿠폰|코인딜|promo code|coupon|choice day)",
    re.IGNORECASE,
)
AMAZON_SIGNAL_RE = re.compile(r"\b(amazon|amzn\.to)\b", re.IGNORECASE)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", s.lower())


def load_sent_history(data_dir: Path, cooldown_days: int = 30) -> dict[str, dict]:
    path = data_dir / "sent_deals_history.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=cooldown_days)).strftime("%Y-%m-%d")
    return {k: v for k, v in raw.items() if isinstance(v, dict) and v.get("sent_date", "9999") >= cutoff}


def save_sent_history(data_dir: Path, history: dict[str, dict]) -> None:
    path = data_dir / "sent_deals_history.json"
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _make_event_id(lang: str, product_id: str, promo_code: str | None, date_str: str) -> str:
    seed = f"{lang}:{product_id}:{promo_code or 'signal'}:{date_str}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:14]


def snipe_hot_deals(
    approved_items: list[dict],
    live_signals: list[dict],
    data_dir: Path,
    cfg: dict | None = None,
    max_picks: int = 2,
) -> dict:
    """Match verified non-Amazon promo/coupon signals to vetted products with idempotency keys."""
    cfg = cfg or {}
    allow_amazon_tracking = bool(cfg.get("affiliate", {}).get("allow_amazon_price_tracking", False))
    history = load_sent_history(data_dir, cooldown_days=14)
    now_utc = datetime.now(timezone.utc)
    today = now_utc.strftime("%Y-%m-%d")
    observed_at = now_utc.strftime("%Y-%m-%d %H:%M UTC")

    signal_matches: dict[str, dict] = {}
    for sig in live_signals:
        title = sig.get("title", "")
        # Amazon Operating Policies §5: never run unauthorized Amazon price-drop/tracking alerts.
        if not allow_amazon_tracking and (AMAZON_SIGNAL_RE.search(title) or "amazon" in sig.get("url", "").lower()):
            continue

        norm_title = _norm(title)
        code_m = PROMO_CODE_RE.search(title)
        promo_code = code_m.group(1).upper() if code_m else None
        is_actionable = bool(promo_code or HOT_KEYWORDS_RE.search(title))
        if not is_actionable:
            continue

        for item in approved_items:
            brand_norm = _norm(item["brand"])
            model_tokens = [t for t in re.split(r"[\s()/,-]+", item["model"]) if len(t) >= 3]
            if brand_norm and brand_norm in norm_title:
                if any(_norm(tok) in norm_title for tok in model_tokens[:3]):
                    signal_matches[item["id"]] = {
                        "promo_code": promo_code,
                        "signal_title": title,
                        "signal_source": sig.get("source", ""),
                        "observed_at": observed_at,
                    }
                    break

    def build_live_picks(lang: str) -> list[dict]:
        picks: list[dict] = []
        for it in approved_items:
            pid = it["id"]
            if pid not in signal_matches:
                continue
            sig_info = signal_matches[pid]
            event_id = _make_event_id(lang, pid, sig_info.get("promo_code"), today)
            if f"event:{event_id}" in history:
                continue
            prev = history.get(f"{lang}:{pid}")
            if prev and not (sig_info.get("promo_code") and sig_info.get("promo_code") != prev.get("promo_code")):
                continue
            entry = dict(it)
            entry["sniper"] = {
                "event_id": event_id,
                "promo_code": sig_info.get("promo_code"),
                "signal_title": sig_info.get("signal_title"),
                "signal_source": sig_info.get("signal_source"),
                "observed_at": observed_at,
                "live_matched": True,
            }
            picks.append(entry)
            if len(picks) >= max_picks:
                break
        return picks

    ko_live = build_live_picks("ko")
    en_live = build_live_picks("en")

    # Local dry-run preview sample (never auto-sent unless live_matched is True)
    preview_ko = ko_live or [
        dict(it, sniper={"event_id": "preview", "promo_code": None, "observed_at": observed_at, "live_matched": False})
        for it in approved_items[:2]
    ]
    preview_en = en_live or [
        dict(it, sniper={"event_id": "preview", "promo_code": None, "observed_at": observed_at, "live_matched": False})
        for it in approved_items[:2]
    ]

    return {
        "ko_picks": ko_live,
        "en_picks": en_live,
        "preview_ko": preview_ko,
        "preview_en": preview_en,
        "live_signal_matches": len(signal_matches),
        "observed_at": observed_at,
    }
