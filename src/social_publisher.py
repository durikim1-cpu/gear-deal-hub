"""Shadowban-safe social feed builder & Meta Threads official free API publisher (Strategy A)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from src.affiliate import DISCLOSURE_EN, DISCLOSURE_KO
from src.site_builder import product_slug


def build_threads_pair_ko(item: dict, base_url: str) -> dict:
    """Build 2-part Korean Threads post (Part 1: pure info, zero links -> Part 2: reply with bridge URL)."""
    p = item["prices"]
    m = item["metrics"]
    sniper = item.get("sniper", {})
    slug = product_slug(item["id"])
    bridge_url = f"{base_url.rstrip('/')}/ko/p/{slug}/"

    cheaper_kr = m["kr_cheaper"] == "aliexpress"
    headline_diff = (
        f"알리 직구가 {m['kr_diff_krw']:,}원 ({m['kr_savings_pct']:.0f}%) 저렴"
        if cheaper_kr
        else f"쿠팡 정발이 오히려 유리 (차액 {m['kr_diff_krw']:,}원)"
    )
    promo_line = f"\n· 감지된 할인코드: {sniper['promo_code']}" if sniper.get("promo_code") else ""
    duty_line = "\n· 주의: 미화 150달러 초과로 직구 시 통관 부가세(10%) 별도 계산 필요" if float(p["ali_usd"]) > 150 else ""

    main_post = (
        f"{item['ko']['title']}\n\n"
        f"· 쿠팡 시세: {int(p['coupang_krw']):,}원\n"
        f"· 알리 직구: {int(p['ali_krw']):,}원 ({headline_diff})"
        f"{promo_line}{duty_line}\n\n"
        f"구매 전 단점 체크:\n"
        f"- {item['ko']['cons'][0]}\n\n"
        f"한줄 판단: {item['ko']['verdict']}\n"
        f"(상세 스펙표와 양쪽 판매처 링크는 첫 댓글에 남겨둡니다)"
    )

    reply_post = (
        f"쿠팡 vs 알리 스펙·가격 비교표 바로가기:\n"
        f"{bridge_url}\n\n"
        f"[광고 고지] {DISCLOSURE_KO}"
    )

    return {
        "product_id": item["id"],
        "promo_code": sniper.get("promo_code"),
        "main_text": main_post,
        "reply_text": reply_post,
        "bridge_url": bridge_url,
    }


def build_social_pair_en(item: dict, base_url: str) -> dict:
    """Build 2-part English X / Threads post (Part 1: link-free price spread -> Part 2: reply with bridge URL)."""
    p = item["prices"]
    m = item["metrics"]
    sniper = item.get("sniper", {})
    slug = product_slug(item["id"])
    bridge_url = f"{base_url.rstrip('/')}/en/p/{slug}/"

    cheaper_ali = m["en_cheaper"] == "aliexpress"
    spread_str = (
        f"Save USD {m['en_diff_usd']:.2f} ({m['en_savings_pct']:.0f}%) via AliExpress"
        if cheaper_ali
        else f"Amazon Prime preferred (within USD {m['en_diff_usd']:.2f})"
    )
    promo_line = f"\n• Promo code spotted: {sniper['promo_code']}" if sniper.get("promo_code") else ""

    main_post = (
        f"{item['en']['title']}\n\n"
        f"• Amazon US: USD {p['amazon_usd']:.2f}\n"
        f"• AliExpress: USD {p['ali_usd']:.2f} ({spread_str})"
        f"{promo_line}\n\n"
        f"Caveat before buying:\n"
        f"- {item['en']['cons'][0]}\n\n"
        f"Full spec comparison & store links in reply 👇"
    )

    reply_post = (
        f"Spec sheet & live Amazon / AliExpress comparison:\n"
        f"{bridge_url}\n\n"
        f"[{DISCLOSURE_EN}]"
    )

    return {
        "product_id": item["id"],
        "promo_code": sniper.get("promo_code"),
        "main_text": main_post,
        "reply_text": reply_post,
        "bridge_url": bridge_url,
    }


def _threads_api_post(user_id: str, access_token: str, text: str, reply_to_id: str | None = None) -> str | None:
    """Publish a single post via Meta's official free Threads Graph API; returns published media ID."""
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


def publish_social_feeds(sniper_result: dict, cfg: dict, dist_dir: Path, live_publish: bool = False) -> dict:
    """Generate shadowban-safe Threads/X queues and optionally auto-post to Meta Threads."""
    base_url = cfg["site"]["base_url"]
    ko_posts = [build_threads_pair_ko(it, base_url) for it in sniper_result["ko_picks"]]
    en_posts = [build_social_pair_en(it, base_url) for it in sniper_result["en_picks"]]

    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "social_queue_ko.json").write_text(
        json.dumps(ko_posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (dist_dir / "social_queue_en.json").write_text(
        json.dumps(en_posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    published_ko = 0
    threads_uid = os.getenv("THREADS_USER_ID", "").strip()
    threads_tok = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
    if live_publish and threads_uid and threads_tok and ko_posts:
        # Publish top 1 fresh sniper deal per run (4 runs/day = 4 clean Threads/day, zero spam risk)
        top_post = ko_posts[0]
        root_id = _threads_api_post(threads_uid, threads_tok, top_post["main_text"])
        if root_id:
            _threads_api_post(threads_uid, threads_tok, top_post["reply_text"], reply_to_id=root_id)
            published_ko += 1

    return {
        "ko_queued": len(ko_posts),
        "en_queued": len(en_posts),
        "threads_published_ko": published_ko,
    }
