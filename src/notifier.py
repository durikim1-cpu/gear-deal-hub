"""Telegram dual-channel (KO & EN) deal alert formatter and sender."""

from __future__ import annotations

import html
import json
import urllib.request
from pathlib import Path
from src.site_builder import product_slug


def _esc(val: object) -> str:
    return html.escape(str(val))


def format_ko_alert(item: dict, base_url: str) -> str:
    p = item["prices"]
    m = item["metrics"]
    links = item["affiliate_links"]
    detail_url = f"{base_url}/ko/p/{product_slug(item['id'])}/"
    cheaper_label = "알리 직구" if m["kr_cheaper"] == "aliexpress" else "쿠팡 정발"
    promo = item.get("sniper", {}).get("promo_code")
    promo_line = f"\n· 할인코드: <code>{_esc(promo)}</code>" if promo else ""

    return (
        f"<b>{_esc(item['ko']['title'])}</b>\n\n"
        f"· 쿠팡: {int(p['coupang_krw']):,}원\n"
        f"· 알리 직구: {int(p['ali_krw']):,}원\n"
        f"→ {cheaper_label} 기준 {m['kr_diff_krw']:,}원 ({m['kr_savings_pct']:.0f}%) 차이 (정가 대비 -{m['msrp_drop_kr_pct']:.0f}%)"
        f"{promo_line}\n\n"
        f"단점 체크: {_esc(item['ko']['cons'][0])}\n"
        f"판단: {_esc(item['ko']['verdict'])}\n\n"
        f'<a href="{_esc(links["coupang"])}">쿠팡 확인</a>  |  '
        f'<a href="{_esc(links["aliexpress"])}">알리 최저가</a>  |  '
        f'<a href="{_esc(detail_url)}">상세 스펙 비교표</a>'
    )


def format_en_alert(item: dict, base_url: str) -> str:
    p = item["prices"]
    m = item["metrics"]
    links = item["affiliate_links"]
    detail_url = f"{base_url}/en/p/{product_slug(item['id'])}/"
    cheaper_label = "AliExpress" if m["en_cheaper"] == "aliexpress" else "Amazon"
    promo = item.get("sniper", {}).get("promo_code")
    promo_line = f"\n• Promo code: <code>{_esc(promo)}</code>" if promo else ""

    return (
        f"<b>{_esc(item['en']['title'])}</b>\n\n"
        f"• Amazon US: ${p['amazon_usd']:.2f}\n"
        f"• AliExpress: ${p['ali_usd']:.2f}\n"
        f"→ Save ${m['en_diff_usd']:.2f} ({m['en_savings_pct']:.0f}%) via {cheaper_label} (-{m['msrp_drop_en_pct']:.0f}% vs MSRP)"
        f"{promo_line}\n\n"
        f"Caveat: {_esc(item['en']['cons'][0])}\n"
        f"Verdict: {_esc(item['en']['verdict'])}\n\n"
        f'<a href="{_esc(links["amazon"])}">Amazon US</a>  |  '
        f'<a href="{_esc(links["aliexpress"])}">AliExpress</a>  |  '
        f'<a href="{_esc(detail_url)}">Full Spec Sheet</a>'
    )


def _send_telegram_message(bot_token: str, chat_id: str, text: str) -> bool:
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
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
