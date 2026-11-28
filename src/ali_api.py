"""Tier-2 official AliExpress Open Platform hook (zero dependencies, standard library only).

Dormant by default. It activates only when both `ALIEXPRESS_APP_KEY` and `ALIEXPRESS_APP_SECRET`
are present (environment variables or `affiliate.aliexpress_app_key` / `affiliate.aliexpress_app_secret`
in config.local.json). When active it:

1. Signs requests with HMAC-SHA256 (`sign_method=sha256`) for the system gateway.
2. Calls `aliexpress.affiliate.link.generate` (tracking_id from config, "default" unless overridden) so
   outbound AliExpress buttons swap to official `s.click.aliexpress.com` promotion links.
3. Calls `aliexpress.affiliate.productdetail.get` for products that carry `urls.ali_product_id` and writes
   `source_kind: "ali_official_api"` offers into data/live_offers_cache.json, refusing any sale price below
   `min_price_ratio_vs_msrp` (default 0.35) of the manufacturer reference MSRP.

Every network or parsing failure is swallowed and reported in the returned stats (fail-closed): the site
then simply keeps its search-landing links and shows no API offer.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from src.deal_sniper import load_live_offers, price_passes_msrp_floor, save_live_offers, upsert_offer

GATEWAY_URL = "https://api-sg.aliexpress.com/sync"
API_OFFER_TTL_HOURS = 12
LINK_BATCH_SIZE = 40
PROMO_LINK_HOSTS = ("s.click.aliexpress.com", "a.aliexpress.com")

Transport = Callable[[str, dict], dict]


def get_credentials(cfg: dict | None = None) -> tuple[str, str]:
    """Return (app_key, app_secret); empty strings when the Tier-2 hook is not configured."""
    aff = (cfg or {}).get("affiliate", {})
    key = (os.getenv("ALIEXPRESS_APP_KEY") or aff.get("aliexpress_app_key") or "").strip()
    secret = (os.getenv("ALIEXPRESS_APP_SECRET") or aff.get("aliexpress_app_secret") or "").strip()
    return key, secret


def is_enabled(cfg: dict | None = None) -> bool:
    key, secret = get_credentials(cfg)
    return bool(key and secret)


def sign_request(params: dict, app_secret: str, api_path: str = "") -> str:
    """HMAC-SHA256 signature for the AliExpress Open Platform gateway.

    Parameters are sorted by key (ASCII order) and concatenated as key+value with no separators;
    REST-style endpoints prefix the API path, the `/sync` system gateway prefixes nothing.
    The digest is upper-case hex. `sign` itself and empty values never take part.
    """
    base = api_path + "".join(
        f"{k}{params[k]}" for k in sorted(params) if k != "sign" and params[k] is not None and params[k] != ""
    )
    return hmac.new(app_secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest().upper()


def build_signed_params(method: str, app_key: str, app_secret: str, business: dict,
                        timestamp_ms: int | None = None) -> dict:
    params = {
        "app_key": app_key,
        "method": method,
        "sign_method": "sha256",
        "timestamp": str(timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)),
    }
    params.update({k: str(v) for k, v in business.items() if v is not None and v != ""})
    params["sign"] = sign_request(params, app_secret)
    return params


def _http_transport(url: str, params: dict) -> dict:
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _call(method: str, cfg: dict, business: dict, transport: Transport | None = None) -> dict | None:
    key, secret = get_credentials(cfg)
    if not (key and secret):
        return None
    try:
        payload = (transport or _http_transport)(GATEWAY_URL, build_signed_params(method, key, secret, business))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    if not isinstance(payload, dict) or "error_response" in payload:
        return None
    wrapper = payload.get(method.replace(".", "_") + "_response", payload)
    result = (wrapper.get("resp_result") or {}) if isinstance(wrapper, dict) else {}
    if str(result.get("resp_code", "")) != "200":
        return None
    inner = result.get("result")
    return inner if isinstance(inner, dict) else None


def _tracking_id(cfg: dict) -> str:
    return (cfg.get("affiliate", {}).get("aliexpress_tracking_id") or "default").strip() or "default"


def is_promotion_link(url: str) -> bool:
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return False
    return url.startswith("https://") and host in PROMO_LINK_HOSTS


def generate_promotion_links(source_urls: list[str], cfg: dict, transport: Transport | None = None) -> dict[str, str]:
    """`aliexpress.affiliate.link.generate`: map each source URL to its official promotion link."""
    out: dict[str, str] = {}
    urls = [u for u in dict.fromkeys(source_urls) if u]
    for start in range(0, len(urls), LINK_BATCH_SIZE):
        batch = urls[start:start + LINK_BATCH_SIZE]
        result = _call(
            "aliexpress.affiliate.link.generate",
            cfg,
            {"promotion_link_type": "0", "source_values": ",".join(batch), "tracking_id": _tracking_id(cfg)},
            transport,
        )
        links = ((result or {}).get("promotion_links") or {}).get("promotion_link") or []
        for row in links:
            src, promo = row.get("source_value", ""), row.get("promotion_link", "")
            if src in batch and is_promotion_link(promo):
                out[src] = promo
    return out


def fetch_product_details(product_ids: list[str], cfg: dict, transport: Transport | None = None,
                          target_currency: str = "USD", target_language: str = "EN") -> dict[str, dict]:
    """`aliexpress.affiliate.productdetail.get`: {ali_product_id: {"sale_price": float, "promotion_link": str}}."""
    out: dict[str, dict] = {}
    ids = [str(i) for i in dict.fromkeys(product_ids) if i]
    for start in range(0, len(ids), 20):
        batch = ids[start:start + 20]
        result = _call(
            "aliexpress.affiliate.productdetail.get",
            cfg,
            {
                "product_ids": ",".join(batch),
                "target_currency": target_currency,
                "target_language": target_language,
                "tracking_id": _tracking_id(cfg),
            },
            transport,
        )
        for row in ((result or {}).get("products") or {}).get("product") or []:
            pid = str(row.get("product_id", ""))
            raw_price = row.get("target_sale_price") or row.get("sale_price")
            currency = row.get("target_sale_price_currency") or row.get("sale_price_currency") or ""
            try:
                price = float(str(raw_price).replace(",", ""))
            except (TypeError, ValueError):
                continue
            if pid in batch and price > 0 and currency.upper() == target_currency:
                out[pid] = {"sale_price": price, "promotion_link": row.get("promotion_link", "")}
    return out


def refresh_official_offers(approved_items: list[dict], cfg: dict, data_dir: Path,
                            transport: Transport | None = None, now: datetime | None = None) -> dict:
    """Tier-2 auto-upgrade: swap in promotion links and cache floor-checked official sale prices.

    Mutates `affiliate_links["aliexpress"]` on approved items in memory only; products.json is never touched.
    """
    stats = {"enabled": is_enabled(cfg), "links_swapped": 0, "offers_written": 0, "blocked_floor": 0}
    if not stats["enabled"]:
        return stats
    now = now or datetime.now(timezone.utc)
    min_ratio = float(cfg.get("gatekeeper", {}).get("min_price_ratio_vs_msrp", 0.35))

    by_source = {it["affiliate_links"]["aliexpress"]: it for it in approved_items if it.get("affiliate_links")}
    promo = generate_promotion_links([u for u in by_source if not is_promotion_link(u)], cfg, transport)
    for src, link in promo.items():
        by_source[src]["affiliate_links"]["aliexpress"] = link
        stats["links_swapped"] += 1

    with_ids = {str(it["urls"]["ali_product_id"]): it for it in approved_items if it.get("urls", {}).get("ali_product_id")}
    if with_ids:
        details = fetch_product_details(list(with_ids), cfg, transport)
        cache = load_live_offers(data_dir, now=now)
        for ali_id, info in details.items():
            item = with_ids[ali_id]
            if not price_passes_msrp_floor(info["sale_price"], float(item.get("msrp_usd") or 0), min_ratio):
                stats["blocked_floor"] += 1
                continue
            entry = {
                "source_kind": "ali_official_api",
                "currency": "USD",
                "price": info["sale_price"],
                "price_text": f"${info['sale_price']:,.2f}",
                "observed_at": now.isoformat(timespec="seconds"),
                "expires_at": (now + timedelta(hours=API_OFFER_TTL_HOURS)).isoformat(timespec="seconds"),
                "signal_source": "aliexpress.affiliate.productdetail.get",
            }
            if is_promotion_link(info.get("promotion_link", "")):
                entry["promotion_link"] = info["promotion_link"]
                item["affiliate_links"]["aliexpress"] = info["promotion_link"]
            upsert_offer(cache, item["id"], entry)
            stats["offers_written"] += 1
        save_live_offers(data_dir, cache)
    return stats
