"""Gatekeeper verification engine: blocks accessory mismatches, fake deals, and policy violations."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from src.affiliate import DISCLOSURE_EN, DISCLOSURE_KO, build_affiliate_links


@dataclass
class VerificationResult:
    product_id: str
    passed: bool
    reasons: list[str]
    metrics: dict


def compute_deal_metrics(product: dict) -> dict:
    p = product["prices"]
    cp_krw = float(p["coupang_krw"])
    ali_krw = float(p["ali_krw"])
    amz_usd = float(p["amazon_usd"])
    ali_usd = float(p["ali_usd"])
    msrp_krw = float(product.get("msrp_krw", max(cp_krw, ali_krw)))
    msrp_usd = float(product.get("msrp_usd", max(amz_usd, ali_usd)))

    kr_cheaper = "aliexpress" if ali_krw < cp_krw else "coupang"
    kr_diff_krw = int(abs(cp_krw - ali_krw))
    kr_savings_pct = round((kr_diff_krw / max(cp_krw, ali_krw)) * 100, 1)

    en_cheaper = "aliexpress" if ali_usd < amz_usd else "amazon"
    en_diff_usd = round(abs(amz_usd - ali_usd), 2)
    en_savings_pct = round((en_diff_usd / max(amz_usd, ali_usd)) * 100, 1)

    best_krw = min(cp_krw, ali_krw)
    best_usd = min(amz_usd, ali_usd)
    msrp_drop_kr_pct = round(((msrp_krw - best_krw) / msrp_krw) * 100, 1) if msrp_krw > 0 else 0.0
    msrp_drop_en_pct = round(((msrp_usd - best_usd) / msrp_usd) * 100, 1) if msrp_usd > 0 else 0.0

    return {
        "kr_cheaper": kr_cheaper,
        "kr_diff_krw": kr_diff_krw,
        "kr_savings_pct": kr_savings_pct,
        "en_cheaper": en_cheaper,
        "en_diff_usd": en_diff_usd,
        "en_savings_pct": en_savings_pct,
        "msrp_drop_kr_pct": msrp_drop_kr_pct,
        "msrp_drop_en_pct": msrp_drop_en_pct,
    }


def verify_product(product: dict, cfg: dict) -> tuple[VerificationResult, dict | None]:
    """Run deterministic Gatekeeper checks. Returns (VerificationResult, enriched_product_or_None)."""
    reasons: list[str] = []
    gk = cfg["gatekeeper"]
    min_ratio = float(gk.get("min_price_ratio_vs_msrp", 0.35))
    forbidden_words = [w.lower() for w in gk.get("forbidden_accessory_keywords", [])]

    # 1. Stock & positive price validation
    if not product.get("in_stock", False):
        reasons.append("OUT_OF_STOCK: Product marked out of stock.")

    prices = product.get("prices", {})
    for key in ("coupang_krw", "ali_krw", "amazon_usd", "ali_usd"):
        if float(prices.get(key, 0)) <= 0:
            reasons.append(f"INVALID_PRICE: {key} must be positive.")

    # 2. Accessory / wrong-item trap guard (keyword + abnormal price ratio check)
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

    msrp_krw = float(product.get("msrp_krw", 0))
    msrp_usd = float(product.get("msrp_usd", 0))
    if msrp_krw > 0 and (min(float(prices.get("coupang_krw", 0)), float(prices.get("ali_krw", 0))) / msrp_krw) < min_ratio:
        reasons.append(
            f"ABNORMAL_LOW_PRICE_KRW: Lowest KRW price is below {int(min_ratio * 100)}% of MSRP (likely accessory/fake match)."
        )
    if msrp_usd > 0 and (min(float(prices.get("amazon_usd", 0)), float(prices.get("ali_usd", 0))) / msrp_usd) < min_ratio:
        reasons.append(
            f"ABNORMAL_LOW_PRICE_USD: Lowest USD price is below {int(min_ratio * 100)}% of MSRP (likely accessory/fake match)."
        )

    # 3. Anti-spam content quality guard: must include genuine cons in both KO and EN
    ko_cons = product.get("ko", {}).get("cons", [])
    en_cons = product.get("en", {}).get("cons", [])
    if not ko_cons or len(ko_cons[0].strip()) < 10:
        reasons.append("MISSING_HONEST_CON_KO: Korean review must list at least one detailed drawback.")
    if not en_cons or len(en_cons[0].strip()) < 10:
        reasons.append("MISSING_HONEST_CON_EN: English review must list at least one detailed drawback.")

    # 4. Affiliate link & legal disclosure integrity check
    links = build_affiliate_links(product, cfg["affiliate"])
    for platform, url in links.items():
        if not url.startswith("https://"):
            reasons.append(f"INVALID_AFFILIATE_URL: {platform} URL is invalid.")
    if not DISCLOSURE_KO or not DISCLOSURE_EN:
        reasons.append("MISSING_LEGAL_DISCLOSURE: Mandatory disclosure text is empty.")

    metrics = compute_deal_metrics(product) if not any(r.startswith("INVALID_PRICE") for r in reasons) else {}
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
