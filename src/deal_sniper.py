"""Hot-deal & promo-code sniper: pairs live discount/coupon signals with vetted catalog models."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROMO_CODE_RE = re.compile(
    r"(?:할인\s*코드|프로모션\s*코드|쿠폰\s*코드|코드|code|coupon|promo)\s*[:：=]?\s*([A-Z0-9]{4,16})\b",
    re.IGNORECASE,
)
HOT_KEYWORDS_RE = re.compile(
    r"(역대가|최저가|코인딜|타임딜|핫딜|할인코드|프로모션|all[- ]time low|promo code|coupon|lightning deal)",
    re.IGNORECASE,
)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", s.lower())


def load_sent_history(data_dir: Path, cooldown_days: int = 7) -> dict[str, dict]:
    path = data_dir / "sent_deals_history.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=cooldown_days)).strftime("%Y-%m-%d")
    return {k: v for k, v in raw.items() if v.get("sent_date", "") >= cutoff}


def save_sent_history(data_dir: Path, history: dict[str, dict]) -> None:
    path = data_dir / "sent_deals_history.json"
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def snipe_hot_deals(
    approved_items: list[dict],
    live_signals: list[dict],
    data_dir: Path,
    max_picks: int = 4,
    record_history: bool = False,
) -> dict:
    """Match live promo/coupon signals to vetted products and pick fresh high-spread deals."""
    history = load_sent_history(data_dir)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Map live signals (promo codes & hot mentions) onto catalog products
    signal_matches: dict[str, dict] = {}
    for sig in live_signals:
        title = sig.get("title", "")
        norm_title = _norm(title)
        code_m = PROMO_CODE_RE.search(title)
        promo_code = code_m.group(1).upper() if code_m else None
        is_hot = bool(promo_code or HOT_KEYWORDS_RE.search(title) or sig.get("score", 0) >= 25)
        if not is_hot:
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
                        "signal_url": sig.get("url", ""),
                    }
                    break

    def score_item(item: dict, lang: str) -> float:
        m = item["metrics"]
        pct = m["kr_savings_pct"] if lang == "ko" else m["en_savings_pct"]
        msrp_drop = m["msrp_drop_kr_pct"] if lang == "ko" else m["msrp_drop_en_pct"]
        sig_bonus = 50.0 if item["id"] in signal_matches else 0.0
        code_bonus = 35.0 if signal_matches.get(item["id"], {}).get("promo_code") else 0.0
        return sig_bonus + code_bonus + (pct * 1.2) + (msrp_drop * 0.5)

    def select_for_lang(lang: str) -> list[dict]:
        ranked = sorted(approved_items, key=lambda x: score_item(x, lang), reverse=True)
        picked: list[dict] = []
        for it in ranked:
            if len(picked) >= max_picks:
                break
            pid = it["id"]
            sig_info = signal_matches.get(pid, {})
            prev = history.get(f"{lang}:{pid}")
            # Skip if already sent within cooldown UNLESS a fresh promo code was spotted
            if prev and not (sig_info.get("promo_code") and sig_info.get("promo_code") != prev.get("promo_code")):
                continue
            entry = dict(it)
            entry["sniper"] = {
                "promo_code": sig_info.get("promo_code"),
                "signal_title": sig_info.get("signal_title"),
                "signal_source": sig_info.get("signal_source"),
                "live_matched": pid in signal_matches,
            }
            picked.append(entry)
            if record_history:
                history[f"{lang}:{pid}"] = {
                    "sent_date": today,
                    "promo_code": sig_info.get("promo_code"),
                }
        return picked

    ko_picks = select_for_lang("ko")
    en_picks = select_for_lang("en")

    if record_history:
        save_sent_history(data_dir, history)

    return {
        "ko_picks": ko_picks,
        "en_picks": en_picks,
        "live_signal_matches": len(signal_matches),
    }
