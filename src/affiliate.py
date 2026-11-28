"""Affiliate URL builder, PII-free source tracking map, and mandatory legal disclosure constants."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit

DISCLOSURE_KO = (
    "이 페이지는 쿠팡 파트너스 및 알리익스프레스 제휴 활동의 일환으로, "
    "이에 따른 일정액의 수수료를 제공받을 수 있습니다. (구매자에게 추가 비용은 발생하지 않습니다.)"
)

BUTTON_DISCLOSURE_KO = "제휴 링크 안내: 아래 판매처 이동 후 구매 시 쿠팡 파트너스·알리익스프레스로부터 일정액의 수수료를 제공받을 수 있습니다."

# Exact Amazon Operating Agreement sentence ("As an Amazon Associate I earn from qualifying purchases.") included verbatim.
DISCLOSURE_EN = (
    "As an Amazon Associate I earn from qualifying purchases. "
    "GearCompare Hub also participates in the AliExpress Affiliate Program and may earn commissions "
    "from qualifying store links at no extra cost to you."
)

BUTTON_DISCLOSURE_EN = (
    "Paid affiliate links: As an Amazon Associate I earn from qualifying purchases "
    "(AliExpress links may also earn a commission)."
)

_SAFE_TRACK_RE = re.compile(r"^[A-Za-z0-9_-]{2,32}$")
_ASIN_RE = re.compile(r"[A-Z0-9]{10}")


def _clean_track_id(raw: str, fallback: str) -> str:
    """Enforce alphanumeric/underscore/hyphen PII-free tracking tokens."""
    val = (raw or "").strip()
    return val if _SAFE_TRACK_RE.match(val) else fallback


def _store_url(value: object, hosts: set[str]) -> str:
    if not isinstance(value, str):
        return ""
    url = value.strip()
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    return url if parts.scheme == "https" and parts.netloc.lower() in hosts else ""


def _with_query_param(url: str, key: str, value: str) -> str:
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() != key]
    return parts._replace(query=urlencode([*query, (key, value)])).geturl()


def coupang_partner_link(value: object) -> str:
    return _store_url(value, {"link.coupang.com"})


def load_config(project_root: Path) -> dict:
    example_cfg = json.loads((project_root / "config.example.json").read_text(encoding="utf-8"))
    local_path = project_root / "config.local.json"
    if local_path.exists():
        local_cfg = json.loads(local_path.read_text(encoding="utf-8"))
        for section, values in local_cfg.items():
            if isinstance(values, dict) and isinstance(example_cfg.get(section), dict):
                example_cfg[section].update(values)
            else:
                example_cfg[section] = values
    cfg = example_cfg

    # Allow environment variable overrides (useful for GitHub Actions Secrets)
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        cfg["telegram"]["bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]
    if os.getenv("TELEGRAM_CHAT_ID_KO"):
        cfg["telegram"]["chat_id_ko"] = os.environ["TELEGRAM_CHAT_ID_KO"]
    if os.getenv("TELEGRAM_CHAT_ID_EN"):
        cfg["telegram"]["chat_id_en"] = os.environ["TELEGRAM_CHAT_ID_EN"]
    if os.getenv("AMAZON_ASSOCIATE_TAG"):
        tag = os.environ["AMAZON_ASSOCIATE_TAG"].strip()
        cfg["affiliate"]["amazon_associate_tag"] = tag
        for k in list(cfg["affiliate"].get("amazon_tags_by_source", {})):
            if cfg["affiliate"]["amazon_tags_by_source"][k] == "gearcomparehu-20":
                cfg["affiliate"]["amazon_tags_by_source"][k] = tag
    if os.getenv("COUPANG_PARTNERS_ID"):
        cfg["affiliate"]["coupang_partners_id"] = os.environ["COUPANG_PARTNERS_ID"]
    if os.getenv("ALIEXPRESS_TRACKING_ID"):
        ali_t = os.environ["ALIEXPRESS_TRACKING_ID"].strip()
        cfg["affiliate"]["aliexpress_tracking_id"] = ali_t
        for k in list(cfg["affiliate"].get("aliexpress_tracking_by_source", {})):
            if cfg["affiliate"]["aliexpress_tracking_by_source"][k] in ("default", "gearhub_global"):
                cfg["affiliate"]["aliexpress_tracking_by_source"][k] = ali_t
    if os.getenv("NAVER_VERIFY_CODE"):
        cfg["site"]["naver_verify_code"] = os.environ["NAVER_VERIFY_CODE"].strip()
    if os.getenv("BING_VERIFY_CODE"):
        cfg["site"]["bing_verify_code"] = os.environ["BING_VERIFY_CODE"].strip()
    if os.getenv("SITE_BASE_URL"):
        cfg["site"]["base_url"] = os.environ["SITE_BASE_URL"].rstrip("/")
    if os.getenv("PINTEREST_VERIFY_CODE"):
        cfg["site"]["pinterest_verify_code"] = os.environ["PINTEREST_VERIFY_CODE"].strip()
    if os.getenv("LIVE_OFFERS_ENDPOINT"):
        cfg["site"]["live_offers_endpoint"] = os.environ["LIVE_OFFERS_ENDPOINT"].strip()
    if os.getenv("ANALYTICS_BEACON_URL"):
        cfg["site"]["analytics_beacon_url"] = os.environ["ANALYTICS_BEACON_URL"].strip()
    return cfg


def build_affiliate_links(product: dict, affiliate_cfg: dict, source: str = "web") -> dict[str, str]:
    """Return transparent destination affiliate URLs with PII-free channel attribution."""
    urls = product.get("urls", {})
    cp_id = _clean_track_id(affiliate_cfg.get("coupang_partners_id", "AF8784203"), "AF8784203")

    cp_map = affiliate_cfg.get("coupang_sub_ids_by_source", {})
    cp_sub = _clean_track_id(
        cp_map.get(source) or affiliate_cfg.get("coupang_sub_id", "gch_ko_web"),
        "gch_ko_web",
    )

    ali_default = _clean_track_id(affiliate_cfg.get("aliexpress_tracking_id", "default"), "default")
    ali_map = affiliate_cfg.get("aliexpress_tracking_by_source", {})
    ali_track = _clean_track_id(ali_map.get(source, ali_default), ali_default)

    amz_default = _clean_track_id(affiliate_cfg.get("amazon_associate_tag", "gearcomparehu-20"), "gearcomparehu-20")
    amz_map = affiliate_cfg.get("amazon_tags_by_source", {})
    # Never invent unissued Amazon Associate tags; only use explicitly configured issued tags.
    amz_tag = _clean_track_id(amz_map.get(source, amz_default), amz_default)

    # Deep-link precedence: an explicit direct link always wins over the exact-token search landing.
    #   coupang_direct : Coupang Partners deep link (link.coupang.com/...)
    #   ali_direct     : official s.click.aliexpress.com promotion link or item URL (API links pass through untouched)
    #   amazon_direct  : a curated product or storefront URL with the configured Associate tag
    coupang_url = coupang_partner_link(urls.get("coupang_direct")) or (
        f"https://link.coupang.com/re/AFFSRP?lptag={quote_plus(cp_id)}"
        f"&subid={quote_plus(cp_sub)}"
        f"&pageKey={quote_plus(urls.get('coupang_query', product['model']))}"
    )

    ali_direct = _store_url(urls.get("ali_direct"), {"aliexpress.com", "www.aliexpress.com", "ko.aliexpress.com", "s.click.aliexpress.com", "a.aliexpress.com"})
    if ali_direct:
        promotion_host = urlsplit(ali_direct).hostname in {"s.click.aliexpress.com", "a.aliexpress.com"}
        ali_url = ali_direct if promotion_host else _with_query_param(ali_direct, "aff_fcid", ali_track)
    else:
        ali_url = (
            f"https://www.aliexpress.com/w/wholesale-{quote_plus(urls.get('ali_query', product['model'])).replace('+', '-')}.html"
            f"?aff_fcid={quote_plus(ali_track)}"
        )

    asin = (urls.get("amazon_asin") or "").strip().upper()
    amazon_url = _store_url(urls.get("amazon_direct"), {"amazon.com", "www.amazon.com"})
    if not amazon_url and _ASIN_RE.fullmatch(asin):
        amazon_url = f"https://www.amazon.com/dp/{asin}"
    if not amazon_url:
        amazon_url = f"https://www.amazon.com/s?k={quote_plus(urls.get('amazon_query', product['model']))}"
    amazon_url = _with_query_param(amazon_url, "tag", amz_tag)

    return {
        "coupang": coupang_url,
        "aliexpress": ali_url,
        "amazon": amazon_url,
    }
