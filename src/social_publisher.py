"""Shadowban-safe social feed builder & Meta Threads official free API publisher.

Implements Topic 1 & Topic 3 Consensus:
- Irregular <= 1 post/day cap (strictly ONLY when a genuine live promo/signal match exists — zero 4x/day template spam).
- Zero static retailer prices or % spread claims; includes observation timestamp & Hub bridge URL (?utm_source=threads).
- Verifies public Hub URL HTTP 200 + idempotency key before publishing.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from src.affiliate import DISCLOSURE_EN, DISCLOSURE_KO
from src.deal_sniper import is_active_deal, load_sent_history, save_sent_history
from src.notifier import verify_public_hub_url
from src.site_builder import product_slug


def build_threads_pair_ko(item: dict, base_url: str) -> dict:
    """Build 2-part price-free Korean Threads post (Part 1: caveat + promo signal -> Part 2: Hub URL + disclosure)."""
    sniper = item.get("sniper", {})
    slug = product_slug(item["id"])
    bridge_url = f"{base_url.rstrip('/')}/ko/p/{slug}/?utm_source=threads"
    obs = sniper.get("observed_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    promo_line = (
        f"\n· 포착된 프로모션 코드: {sniper['promo_code']} (선착순·적용조건 변동 가능)"
        if sniper.get("promo_code")
        else ""
    )

    main_post = (
        f"{item['ko']['title']}\n"
        f"(관측 시각: {obs}){promo_line}\n\n"
        f"구매 전 꼭 확인할 단점:\n"
        f"- {item['ko']['cons'][0]}\n\n"
        f"선택 기준: {item['ko']['verdict']}\n"
        f"(사양·통관 체크표와 실시간 판매처 확인 링크는 첫 댓글에 남겨둡니다)"
    )

    reply_post = (
        f"사양·통관 체크표 및 판매처 확인 허브:\n"
        f"{bridge_url}\n\n"
        f"[광고 고지] {DISCLOSURE_KO}"
    )

    return {
        "product_id": item["id"],
        "event_id": sniper.get("event_id", ""),
        "live_matched": bool(sniper.get("live_matched")),
        "promo_code": sniper.get("promo_code"),
        "main_text": main_post,
        "reply_text": reply_post,
        "bridge_url": bridge_url,
    }


def build_social_pair_en(item: dict, base_url: str) -> dict:
    """Build 2-part price-free English social post (Part 1: caveat + compatibility -> Part 2: Hub URL + disclosure)."""
    sniper = item.get("sniper", {})
    slug = product_slug(item["id"])
    bridge_url = f"{base_url.rstrip('/')}/en/p/{slug}/?utm_source=threads"
    obs = sniper.get("observed_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    promo_line = (
        f"\n• Spotted promo code: {sniper['promo_code']} (subject to quota & checkout terms)"
        if sniper.get("promo_code")
        else ""
    )

    main_post = (
        f"{item['en']['title']}\n"
        f"(Observed: {obs}){promo_line}\n\n"
        f"Real-world caveat before buying:\n"
        f"- {item['en']['cons'][0]}\n\n"
        f"Compatibility notes & store links in reply 👇"
    )

    reply_post = (
        f"Compatibility checklist & store options on GearCompare Hub:\n"
        f"{bridge_url}\n\n"
        f"{DISCLOSURE_EN}"
    )

    return {
        "product_id": item["id"],
        "event_id": sniper.get("event_id", ""),
        "live_matched": bool(sniper.get("live_matched")),
        "promo_code": sniper.get("promo_code"),
        "main_text": main_post,
        "reply_text": reply_post,
        "bridge_url": bridge_url,
    }


def _threads_api_post(user_id: str, access_token: str, text: str, reply_to_id: str | None = None) -> str | None:
    create_url = f"https://graph.threads.net/v1.0/{user_id}/threads"
    params = {"media_type": "TEXT", "text": text, "access_token": access_token}
    if reply_to_id:
        params["reply_to_id"] = reply_to_id

    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(create_url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            creation_id = json.loads(resp.read().decode("utf-8")).get("id")
        if not creation_id:
            return None
        time.sleep(1.5)
        pub_url = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        pub_data = urllib.parse.urlencode({"creation_id": creation_id, "access_token": access_token}).encode("utf-8")
        pub_req = urllib.request.Request(pub_url, data=pub_data, method="POST")
        with urllib.request.urlopen(pub_req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8")).get("id")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def stage_social_queues(sniper_result: dict, cfg: dict, dist_dir: Path) -> dict:
    base_url = cfg["site"]["base_url"]
    ko_posts = [build_threads_pair_ko(it, base_url) for it in sniper_result.get("preview_ko", [])]
    en_posts = [build_social_pair_en(it, base_url) for it in sniper_result.get("preview_en", [])]

    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "social_queue_ko.json").write_text(
        json.dumps(ko_posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (dist_dir / "social_queue_en.json").write_text(
        json.dumps(en_posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "ko_queued": len(sniper_result.get("ko_picks", [])),
        "en_queued": len(sniper_result.get("en_picks", [])),
        "threads_published_ko": 0,
    }


def publish_verified_social(ko_picks: list[dict], cfg: dict, data_dir: Path, live_publish: bool = False) -> dict:
    """Publish at most 1 Thread/day ONLY when a genuine live signal matched AND public Hub URL is verified."""
    threads_uid = os.getenv("THREADS_USER_ID", "").strip()
    threads_tok = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
    if not (live_publish and threads_uid and threads_tok and ko_picks):
        return {"threads_published_ko": 0}

    history = load_sent_history(data_dir, cooldown_days=30)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Topic 1 Consensus #3: Irregular <= 1 post/day cap on Threads
    if history.get("threads_daily_cap", {}).get("sent_date") == today:
        return {"threads_published_ko": 0}

    base_url = cfg["site"]["base_url"].rstrip("/")
    top_item = next((item for item in ko_picks if is_active_deal(item.get("sniper", {}))), None)
    if top_item is None:
        return {"threads_published_ko": 0}
    sniper = top_item["sniper"]

    ev_id = sniper.get("event_id", "")
    if ev_id and f"threads_event:{ev_id}" in history:
        return {"threads_published_ko": 0}

    slug = product_slug(top_item["id"])
    if not verify_public_hub_url(f"{base_url}/ko/p/{slug}/", top_item["brand"]):
        return {"threads_published_ko": 0}

    post = build_threads_pair_ko(top_item, base_url)
    root_id = _threads_api_post(threads_uid, threads_tok, post["main_text"])
    published = 0
    if root_id:
        published = 1
        history["threads_daily_cap"] = {"sent_date": today}
        if ev_id:
            history[f"threads_event:{ev_id}"] = {"sent_date": today}
        save_sent_history(data_dir, history)
        _threads_api_post(threads_uid, threads_tok, post["reply_text"], reply_to_id=root_id)

    return {"threads_published_ko": published}
