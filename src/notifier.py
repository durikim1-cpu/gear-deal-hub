"""Telegram dual-channel (KO & EN) Hub-routed alert formatter, public-URL verifier, and idempotent sender.

Implements Topic 2 & Topic 3 Consensus + User Formatting Preference:
- ZERO direct Amazon/Coupang/AliExpress affiliate links in Telegram (routes 100% through registered Hub URLs with ?utm_source=telegram).
- ZERO static prices or unverified discount claims; includes UTC observation timestamp & checkout-change notice.
- Verifies that the public Hub URL is live (HTTP 200 + expected slug) BEFORE sending any message, and records idempotency event_id.
- Preserves clean body formatting without [대가성 광고 안내] inside Telegram messages (disclosures sit on the Hub landing page).
"""

from __future__ import annotations

import html
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from src.deal_sniper import load_sent_history, save_sent_history
from src.site_builder import product_slug


def _esc(val: object) -> str:
    return html.escape(str(val))


def verify_public_hub_url(url: str, expected_marker: str, timeout_sec: int = 10) -> bool:
    """Confirm the deployed GitHub Pages URL actually serves HTTP 200 with expected content before notifying."""
    req = urllib.request.Request(url, headers={"User-Agent": "GearCompareHubVerifier/3.0", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status != 200:
                return False
            body = resp.read().decode("utf-8", errors="replace")
            return expected_marker.lower() in body.lower()
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def format_ko_alert(item: dict, base_url: str) -> str:
    slug = product_slug(item["id"])
    detail_url = f"{base_url.rstrip('/')}/ko/p/{slug}/?utm_source=telegram"
    sniper = item.get("sniper", {})
    promo = sniper.get("promo_code")
    obs = sniper.get("observed_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    promo_line = (
        f"\n· 포착된 프로모션 코드: <code>{_esc(promo)}</code> (대상국·최소주문액·선착순 소진 조건 결제창 확인)"
        if promo
        else ""
    )

    return (
        f"<b>{_esc(item['ko']['title'])}</b>\n"
        f"· 관측 시각: {_esc(obs)} (가격·할인 조건 실시간 변동 가능)"
        f"{promo_line}\n\n"
        f"단점 체크: {_esc(item['ko']['cons'][0])}\n"
        f"선택 기준: {_esc(item['ko']['verdict'])}\n\n"
        f'<a href="{_esc(detail_url)}">허브에서 사양·통관 기준 및 판매처 확인 →</a>'
    )


def format_en_alert(item: dict, base_url: str) -> str:
    slug = product_slug(item["id"])
    detail_url = f"{base_url.rstrip('/')}/en/p/{slug}/?utm_source=telegram"
    sniper = item.get("sniper", {})
    promo = sniper.get("promo_code")
    obs = sniper.get("observed_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    promo_line = (
        f"\n• Spotted promo code: <code>{_esc(promo)}</code> (subject to region, minimum spend &amp; quota)"
        if promo
        else ""
    )

    return (
        f"<b>{_esc(item['en']['title'])}</b>\n"
        f"• Observed: {_esc(obs)} (live terms &amp; stock subject to change)"
        f"{promo_line}\n\n"
        f"Caveat: {_esc(item['en']['cons'][0])}\n"
        f"Buying check: {_esc(item['en']['verdict'])}\n\n"
        f'<a href="{_esc(detail_url)}">View Compatibility &amp; Store Links on Hub →</a>'
    )


def _normalize_chat_id(raw: str) -> str:
    val = (raw or "").strip()
    if val.startswith("https://t.me/"):
        val = "@" + val.removeprefix("https://t.me/").strip("/")
    elif val and not val.startswith(("@", "-")):
        val = "@" + val
    return val


def _send_telegram_message(bot_token: str, chat_id: str, text: str) -> bool:
    norm_chat = _normalize_chat_id(chat_id)
    if not norm_chat:
        return False
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = json.dumps(
        {
            "chat_id": norm_chat,
            "text": text,
            "parse_mode": "HTML",
            # Rich previews on: Telegram renders the Hub page's og:image + title card under the message.
            "disable_web_page_preview": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        api_url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"[Telegram warn] Failed to send to {norm_chat}: {exc}")
        return False


def stage_alerts_preview(sniper_res: dict, cfg: dict, dist_dir: Path) -> dict:
    """Write preview files and stage live-matched events for post-deploy verified dispatch."""
    base_url = cfg["site"]["base_url"].rstrip("/")
    ko_previews = [format_ko_alert(it, base_url) for it in sniper_res.get("preview_ko", [])]
    en_previews = [format_en_alert(it, base_url) for it in sniper_res.get("preview_en", [])]

    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "telegram_preview_ko.txt").write_text(
        "\n\n" + ("\n\n" + "=" * 60 + "\n\n").join(ko_previews) + "\n", encoding="utf-8"
    )
    (dist_dir / "telegram_preview_en.txt").write_text(
        "\n\n" + ("\n\n" + "=" * 60 + "\n\n").join(en_previews) + "\n", encoding="utf-8"
    )
    return {
        "queued_ko": len(sniper_res.get("ko_picks", [])),
        "queued_en": len(sniper_res.get("en_picks", [])),
        "sent_ko": 0,
        "sent_en": 0,
    }


def dispatch_verified_alerts(
    ko_picks: list[dict],
    en_picks: list[dict],
    cfg: dict,
    data_dir: Path,
    live_send: bool = False,
) -> dict:
    """Send ONLY live-matched, idempotency-unchecked alerts AFTER verifying public Hub URL is live."""
    base_url = cfg["site"]["base_url"].rstrip("/")
    token = cfg["telegram"].get("bot_token", "").strip()
    if not (live_send and token):
        return {"queued_ko": len(ko_picks), "queued_en": len(en_picks), "sent_ko": 0, "sent_en": 0, "live_mode": False}

    history = load_sent_history(data_dir, cooldown_days=30)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    chat_ko = cfg["telegram"].get("chat_id_ko", "").strip()
    chat_en = cfg["telegram"].get("chat_id_en", "").strip()
    sent_ko = 0
    sent_en = 0

    if chat_ko:
        for it in ko_picks:
            sniper = it.get("sniper", {})
            if not sniper.get("live_matched"):
                continue
            ev_id = sniper.get("event_id", "")
            if ev_id and f"event:{ev_id}" in history:
                continue
            slug = product_slug(it["id"])
            pub_url = f"{base_url}/ko/p/{slug}/"
            if not verify_public_hub_url(pub_url, it["brand"]):
                continue
            if _send_telegram_message(token, chat_ko, format_ko_alert(it, base_url)):
                sent_ko += 1
                history[f"ko:{it['id']}"] = {"sent_date": today, "promo_code": sniper.get("promo_code")}
                if ev_id:
                    history[f"event:{ev_id}"] = {"sent_date": today, "channel": "telegram_ko"}

    if chat_en:
        for it in en_picks:
            sniper = it.get("sniper", {})
            if not sniper.get("live_matched"):
                continue
            ev_id = sniper.get("event_id", "")
            if ev_id and f"event:{ev_id}" in history:
                continue
            slug = product_slug(it["id"])
            pub_url = f"{base_url}/en/p/{slug}/"
            if not verify_public_hub_url(pub_url, "As an Amazon Associate I earn from qualifying purchases."):
                continue
            if _send_telegram_message(token, chat_en, format_en_alert(it, base_url)):
                sent_en += 1
                history[f"en:{it['id']}"] = {"sent_date": today, "promo_code": sniper.get("promo_code")}
                if ev_id:
                    history[f"event:{ev_id}"] = {"sent_date": today, "channel": "telegram_en"}

    if sent_ko or sent_en:
        save_sent_history(data_dir, history)

    return {
        "queued_ko": len(ko_picks),
        "queued_en": len(en_picks),
        "sent_ko": sent_ko,
        "sent_en": sent_en,
        "live_mode": True,
    }
