"""Gatekeeper verification engine: blocks accessory mismatches, unverified static prices, and policy violations."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from src.affiliate import DISCLOSURE_EN, DISCLOSURE_KO, build_affiliate_links

BLANKET_GUARANTEE_RE = re.compile(
    r"(100%\s*(?:정품|보장|무료\s*반품)|무조건\s*무료\s*반품|guaranteed\s+100%\s+authentic|guaranteed\s+free\s+returns)",
    re.IGNORECASE,
)


@dataclass
class VerificationResult:
    product_id: str
    passed: bool
    reasons: list[str]
    metrics: dict


def compute_buying_metrics(product: dict) -> dict:
    """Compute price-free buying profile metrics (zero static retailer prices or % spread claims)."""
    bp = product.get("buying_profile", {})
    pref_ko = bp.get("preferred_route_ko", "domestic")
    pref_en = bp.get("preferred_route_en", "amazon")
    return {
        "preferred_route_ko": pref_ko if pref_ko in ("domestic", "direct") else "domestic",
        "preferred_route_en": pref_en if pref_en in ("amazon", "direct") else "amazon",
        "amazon_priority_score": int(bp.get("amazon_priority_score", 80 if pref_en == "amazon" else 40)),
        "kr_customs_rule": bp.get("kr_customs_rule", "china_150_us_200"),
    }


def verify_product(product: dict, cfg: dict) -> tuple[VerificationResult, dict | None]:
    """Run deterministic Gatekeeper checks. Returns (VerificationResult, enriched_product_or_None)."""
    reasons: list[str] = []
    gk = cfg["gatekeeper"]
    min_ratio = float(gk.get("min_price_ratio_vs_msrp", 0.35))
    forbidden_words = [w.lower() for w in gk.get("forbidden_accessory_keywords", [])]

    # 1. Stock check
    if not product.get("in_stock", False):
        reasons.append("OUT_OF_STOCK: Product marked out of stock.")

    # 2. Policy guard (Debate 2 & 3 Consensus): Block unverified static retailer prices in catalog!
    # Retailer prices may ONLY be served via a separate TTL-enforced API response (`live_offer` with expires_at),
    # never hardcoded inside static HTML, JSON-LD, meta tags, RSS feeds, or Git-tracked product records.
    if "prices" in product and product["prices"]:
        # Before rejecting, check if an inbox candidate is a low-price accessory trap for clear audit logging
        prices = product["prices"]
        msrp_krw = float(product.get("msrp_krw", 0))
        msrp_usd = float(product.get("msrp_usd", 0))
        cp_krw = float(prices.get("coupang_krw", 0) or 0)
        ali_krw = float(prices.get("ali_krw", 0) or 0)
        amz_usd = float(prices.get("amazon_usd", 0) or 0)
        ali_usd = float(prices.get("ali_usd", 0) or 0)
        low_krw = min(x for x in (cp_krw, ali_krw) if x > 0) if (cp_krw > 0 or ali_krw > 0) else 0
        low_usd = min(x for x in (amz_usd, ali_usd) if x > 0) if (amz_usd > 0 or ali_usd > 0) else 0
        if msrp_krw > 0 and 0 < low_krw < msrp_krw * min_ratio:
            reasons.append(
                f"ABNORMAL_LOW_PRICE_KRW: Observed KRW price is below {int(min_ratio * 100)}% of MSRP (accessory/fake trap)."
            )
        if msrp_usd > 0 and 0 < low_usd < msrp_usd * min_ratio:
            reasons.append(
                f"ABNORMAL_LOW_PRICE_USD: Observed USD price is below {int(min_ratio * 100)}% of MSRP (accessory/fake trap)."
            )
        reasons.append(
            "UNVERIFIED_STATIC_RETAILER_PRICE: Static store prices are prohibited; use TTL-enforced live API offers only."
        )

    # Optional observed lead sanity check (when auto_discover evaluates raw deal leads without storing static prices)
    obs_krw = float(product.get("observed_lead_krw", 0) or 0)
    obs_usd = float(product.get("observed_lead_usd", 0) or 0)
    msrp_krw = float(product.get("msrp_krw", 0) or 0)
    msrp_usd = float(product.get("msrp_usd", 0) or 0)
    if msrp_krw > 0 and 0 < obs_krw < msrp_krw * min_ratio:
        reasons.append(
            f"ABNORMAL_LOW_PRICE_KRW: Lead KRW price is below {int(min_ratio * 100)}% of MSRP (likely accessory)."
        )
    if msrp_usd > 0 and 0 < obs_usd < msrp_usd * min_ratio:
        reasons.append(
            f"ABNORMAL_LOW_PRICE_USD: Lead USD price is below {int(min_ratio * 100)}% of MSRP (likely accessory)."
        )

    # 3. Accessory / wrong-item keyword trap guard + blanket seller guarantee guard
    combined_text = " ".join(
        [
            product.get("model", ""),
            product.get("ko", {}).get("title", ""),
            product.get("en", {}).get("title", ""),
        ]
    ).lower()

    for bad_kw in forbidden_words:
        if bad_kw in combined_text:
            reasons.append(f"ACCESSORY_TRAP_KEYWORD: Detected '{bad_kw}' in title/model.")
            break

    copy_blob = " ".join(
        [
            product.get("ko", {}).get("verdict", ""),
            product.get("en", {}).get("verdict", ""),
            product.get("ko", {}).get("summary", ""),
            product.get("en", {}).get("summary", ""),
        ]
    )
    if BLANKET_GUARANTEE_RE.search(copy_blob):
        reasons.append("UNVERIFIED_SELLER_GUARANTEE: Blanket 100% authenticity/free-return claim without seller verification.")

    # 4. Anti-spam content quality guard: must include genuine cons in both KO and EN
    ko_cons = product.get("ko", {}).get("cons", [])
    en_cons = product.get("en", {}).get("cons", [])
    if not ko_cons or len(ko_cons[0].strip()) < 10:
        reasons.append("MISSING_HONEST_CON_KO: Korean review must list at least one detailed drawback.")
    if not en_cons or len(en_cons[0].strip()) < 10:
        reasons.append("MISSING_HONEST_CON_EN: English review must list at least one detailed drawback.")

    # 5. Affiliate link & verbatim legal disclosure integrity check
    links = build_affiliate_links(product, cfg["affiliate"])
    for platform, url in links.items():
        if not url.startswith("https://"):
            reasons.append(f"INVALID_AFFILIATE_URL: {platform} URL is invalid.")
    if not DISCLOSURE_KO or "As an Amazon Associate I earn from qualifying purchases." not in DISCLOSURE_EN:
        reasons.append("MISSING_LEGAL_DISCLOSURE: Mandatory disclosure text (including exact Amazon Associate sentence) missing.")

    metrics = compute_buying_metrics(product)
    passed = len(reasons) == 0
    result = VerificationResult(
        product_id=product.get("id", "unknown"),
        passed=passed,
        reasons=reasons,
        metrics=metrics,
    )

    if not passed:
        return result, None

    enriched = dict(product)
    enriched.pop("observed_lead_krw", None)
    enriched.pop("observed_lead_usd", None)
    enriched["affiliate_links"] = links
    enriched["metrics"] = metrics
    enriched["disclosures"] = {"ko": DISCLOSURE_KO, "en": DISCLOSURE_EN}
    return result, enriched


def verify_batch(candidates: list[dict], cfg: dict) -> tuple[list[dict], list[dict]]:
    """Verify all candidates; return (approved_products, audit_entries)."""
    approved: list[dict] = []
    audit: list[dict] = []
    for item in candidates:
        res, enriched = verify_product(item, cfg)
        audit.append(asdict(res))
        if enriched is not None:
            approved.append(enriched)
    return approved, audit
