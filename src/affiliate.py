"""Affiliate URL builder and mandatory legal disclosure constants."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote_plus

DISCLOSURE_KO = (
    "이 페이지 및 알림은 쿠팡 파트너스 및 알리익스프레스 제휴 활동의 일환으로, "
    "이에 따른 일정액의 수수료를 제공받을 수 있습니다. (구매자에게 추가 비용은 발생하지 않습니다.)"
)

DISCLOSURE_EN = (
    "Disclosure: As an Amazon Associate and AliExpress Affiliate, we earn from qualifying "
    "purchases at no additional cost to you. Prices and availability are accurate as of the "
    "timestamp shown and are subject to change."
)


def load_config(project_root: Path) -> dict:
    local_cfg = project_root / "config.local.json"
    example_cfg = project_root / "config.example.json"
    cfg_path = local_cfg if local_cfg.exists() else example_cfg
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    # Allow environment variable overrides (useful for GitHub Actions Secrets)
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        cfg["telegram"]["bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]
    if os.getenv("TELEGRAM_CHAT_ID_KO"):
        cfg["telegram"]["chat_id_ko"] = os.environ["TELEGRAM_CHAT_ID_KO"]
    if os.getenv("TELEGRAM_CHAT_ID_EN"):
        cfg["telegram"]["chat_id_en"] = os.environ["TELEGRAM_CHAT_ID_EN"]
    if os.getenv("AMAZON_ASSOCIATE_TAG"):
        cfg["affiliate"]["amazon_associate_tag"] = os.environ["AMAZON_ASSOCIATE_TAG"]
    if os.getenv("COUPANG_PARTNERS_ID"):
        cfg["affiliate"]["coupang_partners_id"] = os.environ["COUPANG_PARTNERS_ID"]
    if os.getenv("ALIEXPRESS_TRACKING_ID"):
        cfg["affiliate"]["aliexpress_tracking_id"] = os.environ["ALIEXPRESS_TRACKING_ID"]
    if os.getenv("SITE_BASE_URL"):
        cfg["site"]["base_url"] = os.environ["SITE_BASE_URL"].rstrip("/")
    return cfg


def build_affiliate_links(product: dict, affiliate_cfg: dict) -> dict[str, str]:
    """Return affiliate-ready URLs.

    If direct verified shortlinks (`coupang_direct`, `ali_direct`, `amazon_direct`) are set
    on a product (e.g. from official APIs), use them directly; otherwise build tagged search
    URLs that never break or 404 during initial approval stages.
    """
    urls = product.get("urls", {})
    amz_tag = affiliate_cfg.get("amazon_associate_tag", "gearhub-20")
    cp_sub = affiliate_cfg.get("coupang_sub_id", "gearhub_ko")
    ali_track = affiliate_cfg.get("aliexpress_tracking_id", "gearhub_global")

    coupang_url = urls.get("coupang_direct") or (
        f"https://www.coupang.com/np/search?q={quote_plus(urls.get('coupang_query', product['model']))}"
        f"&channel=user&subId={quote_plus(cp_sub)}"
    )
    ali_url = urls.get("ali_direct") or (
        f"https://www.aliexpress.com/w/wholesale-{quote_plus(urls.get('ali_query', product['model'])).replace('+', '-')}.html"
        f"?aff_fcid={quote_plus(ali_track)}"
    )
    amazon_url = urls.get("amazon_direct") or (
        f"https://www.amazon.com/s?k={quote_plus(urls.get('amazon_query', product['model']))}"
        f"&tag={quote_plus(amz_tag)}"
    )

    return {
        "coupang": coupang_url,
        "aliexpress": ali_url,
        "amazon": amazon_url,
    }
