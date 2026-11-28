"""Generate attributed Coupang Partners links for curated product URLs."""

from __future__ import annotations

import hmac
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlsplit

from src.affiliate import coupang_partner_link


DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
DEEPLINK_URL = f"https://api-gateway.coupang.com{DEEPLINK_PATH}"
PRODUCT_PATH = re.compile(r"/vp/products/\d+/?")
DIRECT_SUB_ID = "gch_ko_direct"


def refresh_coupang_links(approved_items: list[dict], cfg: dict) -> dict:
    affiliate = cfg.get("affiliate", {})
    access = (os.getenv("COUPANG_ACCESS_KEY") or affiliate.get("coupang_access_key") or "").strip()
    secret = (os.getenv("COUPANG_SECRET_KEY") or affiliate.get("coupang_secret_key") or "").strip()
    stats = {"enabled": bool(access and secret), "links_swapped": 0}
    if not stats["enabled"]:
        return stats

    by_source: dict[str, list[dict]] = {}
    for item in approved_items:
        urls = item.get("urls", {})
        if coupang_partner_link(urls.get("coupang_direct")):
            continue
        source = urls.get("coupang_product_url")
        if not isinstance(source, str):
            continue
        try:
            parts = urlsplit(source)
        except ValueError:
            continue
        if parts.scheme == "https" and parts.netloc == "www.coupang.com" and PRODUCT_PATH.fullmatch(parts.path):
            by_source.setdefault(source, []).append(item)

    sources = list(by_source)
    for start in range(0, len(sources), 50):
        batch = sources[start:start + 50]
        signed_date = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
        signature = hmac.digest(secret.encode(), f"{signed_date}POST{DEEPLINK_PATH}".encode(), "sha256").hex()
        req = urllib.request.Request(
            DEEPLINK_URL,
            data=json.dumps({"coupangUrls": batch, "subId": DIRECT_SUB_ID}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"CEA algorithm=HmacSHA256, access-key={access}, signed-date={signed_date}, signature={signature}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.load(response)
        except (OSError, ValueError) as exc:
            print(f"[Coupang note] Link generation failed ({getattr(exc, 'code', type(exc).__name__)})")
            continue
        if not isinstance(payload, dict) or str(payload.get("rCode")) != "0" or not isinstance(payload.get("data"), list):
            print("[Coupang note] No usable deeplink response")
            continue
        for row in payload["data"]:
            if not isinstance(row, dict) or row.get("originalUrl") not in batch:
                continue
            link = coupang_partner_link(row.get("shortenUrl"))
            if link:
                for item in by_source[row["originalUrl"]]:
                    item["affiliate_links"]["coupang"] = link
                    stats["links_swapped"] += 1
    return stats
