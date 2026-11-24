"""Telegram dual-channel (KO & EN) deal alert formatter and sender."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from src.affiliate import DISCLOSURE_EN, DISCLOSURE_KO
from src.site_builder import product_slug


def format_ko_alert(item: dict, base_url: str) -> str:
    p = item["prices"]
    m = item["metrics"]
    links = item["affiliate_links"]
    detail_url = f"{base_url}/ko/p/{product_slug(item['id'])}/"
    cheaper_label = "알리 직구" if m["kr_cheaper"] == "aliexpress" else "쿠팡 로켓"

    return (
        f"[대가성 광고 안내] {DISCLOSURE_KO}\n\n"
        f"🔥 {item['ko']['title']}\n"
        f"• 쿠팡가: {int(p['coupang_krw']):,}원\n"
        f"• 알리 직구가: {int(p['ali_krw']):,}원\n"
        f"👉 {cheaper_label} 선택 시 {m['kr_diff_krw']:,}원 ({m['kr_savings_pct']}%) 절약 (정가 대비 -{m['msrp_drop_kr_pct']}%)\n\n"
        f"⚠️ 구매 전 체크할 단점: {item['ko']['cons'][0]}\n"
        f"💡 추천 결론: {item['ko']['verdict']}\n\n"
        f"🚀 쿠팡 확인: {links['coupang']}\n"
        f"🌏 알리 최저가: {links['aliexpress']}\n"
        f"📊 상세 스펙 비교표: {detail_url}"
    )


def format_en_alert(item: dict, base_url: str) -> str:
    p = item["prices"]
    m = item["metrics"]
    links = item["affiliate_links"]
    detail_url = f"{base_url}/en/p/{product_slug(item['id'])}/"
    cheaper_label = "AliExpress" if m["en_cheaper"] == "aliexpress" else "Amazon"

    return (
        f"🔥 {item['en']['title']}\n"
        f"• Amazon: USD {p['amazon_usd']:.2f}\n"
        f"• AliExpress: USD {p['ali_usd']:.2f}\n"
        f"👉 Save USD {m['en_diff_usd']:.2f} ({m['en_savings_pct']}%) via {cheaper_label} (-{m['msrp_drop_en_pct']}% vs MSRP)\n\n"
        f"⚠️ Watch-out: {item['en']['cons'][0]}\n"
        f"💡 Verdict: {item['en']['verdict']}\n\n"
        f"📦 Amazon Deal: {links['amazon']}\n"
        f"🌏 AliExpress Deal: {links['aliexpress']}\n"
        f"📊 Full Spec Sheet: {detail_url}\n\n"
        f"[{DISCLOSURE_EN}]"
    )


def _send_telegram_message(bot_token: str, chat_id: str, text: str) -> bool:
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = json.dumps(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    ).encode("utf-8")
    req = urllib.request.Request(
        api_url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        return resp.status == 200


def dispatch_alerts(
    approved_items: list[dict], cfg: dict, dist_dir: Path, live_send: bool = False, max_alerts: int = 3
) -> dict:
    """Select top deals exceeding alert threshold, write previews, and optionally send to Telegram."""
    min_pct = float(cfg["gatekeeper"].get("alert_min_savings_pct", 15.0))
    base_url = cfg["site"]["base_url"].rstrip("/")

    hot_ko = [
        it for it in approved_items if it["metrics"]["msrp_drop_kr_pct"] >= min_pct
    ]
    hot_ko.sort(key=lambda x: x["metrics"]["msrp_drop_kr_pct"], reverse=True)
    hot_ko = hot_ko[:max_alerts]

    hot_en = [
        it for it in approved_items if it["metrics"]["msrp_drop_en_pct"] >= min_pct
    ]
    hot_en.sort(key=lambda x: x["metrics"]["msrp_drop_en_pct"], reverse=True)
    hot_en = hot_en[:max_alerts]

    ko_messages = [format_ko_alert(it, base_url) for it in hot_ko]
    en_messages = [format_en_alert(it, base_url) for it in hot_en]

    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "telegram_preview_ko.txt").write_text(
        "\n\n" + ("\n\n" + "=" * 60 + "\n\n").join(ko_messages) + "\n",
        encoding="utf-8",
    )
    (dist_dir / "telegram_preview_en.txt").write_text(
        "\n\n" + ("\n\n" + "=" * 60 + "\n\n").join(en_messages) + "\n",
        encoding="utf-8",
    )

    sent_ko = 0
    sent_en = 0
    token = cfg["telegram"].get("bot_token", "").strip()
    if live_send and token:
        chat_ko = cfg["telegram"].get("chat_id_ko", "").strip()
        chat_en = cfg["telegram"].get("chat_id_en", "").strip()
        if chat_ko:
            for msg in ko_messages:
                if _send_telegram_message(token, chat_ko, msg):
                    sent_ko += 1
        if chat_en:
            for msg in en_messages:
                if _send_telegram_message(token, chat_en, msg):
                    sent_en += 1

    return {
        "queued_ko": len(ko_messages),
        "queued_en": len(en_messages),
        "sent_ko": sent_ko,
        "sent_en": sent_en,
        "live_mode": bool(live_send and token),
    }
