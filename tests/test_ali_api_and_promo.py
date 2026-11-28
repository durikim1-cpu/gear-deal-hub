"""Pillar 2: official AliExpress API hook (Tier 2), promo tiers, sale traffic light, and calculator maths."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from conftest import ROOT, read
from src import ali_api
from src.deal_sniper import load_live_offers
from src.tools_and_guides import (
    SALE_COPY,
    active_promo,
    best_promo_tier,
    compute_promo_checkout,
    kr_customs_anchor,
    load_promo_tiers,
    sale_reference_date,
    sale_signal,
    sale_window,
)

NOW = datetime(2026, 11, 28, 3, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------ Tier 2: signing + hook
def test_hmac_sha256_signature_matches_an_independent_computation():
    params = {"method": "aliexpress.affiliate.link.generate", "app_key": "12345", "timestamp": "1700000000000",
              "sign_method": "sha256", "tracking_id": "default", "promotion_link_type": "0",
              "source_values": "https://www.aliexpress.com/item/1.html"}
    base = "".join(k + params[k] for k in sorted(params))
    expected = hmac.new(b"secret", base.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    assert ali_api.sign_request(params, "secret") == expected
    assert ali_api.sign_request({**params, "sign": "IGNORED", "empty": ""}, "secret") == expected
    assert ali_api.sign_request(params, "other-secret") != expected

    signed = ali_api.build_signed_params("aliexpress.affiliate.productdetail.get", "12345", "secret",
                                         {"product_ids": "1,2", "tracking_id": "default"}, timestamp_ms=1700000000000)
    assert signed["sign_method"] == "sha256" and signed["timestamp"] == "1700000000000"
    assert signed["sign"] == ali_api.sign_request({k: v for k, v in signed.items() if k != "sign"}, "secret")


def test_hook_is_dormant_without_credentials(monkeypatch, tmp_path, approved, cfg):
    monkeypatch.delenv("ALIEXPRESS_APP_KEY", raising=False)
    monkeypatch.delenv("ALIEXPRESS_APP_SECRET", raising=False)
    assert not ali_api.is_enabled(cfg)

    def boom(url, params):  # pragma: no cover - must never be called
        raise AssertionError("network must not be touched when the hook is disabled")

    items = [dict(approved[0], affiliate_links=dict(approved[0]["affiliate_links"]))]
    before = items[0]["affiliate_links"]["aliexpress"]
    stats = ali_api.refresh_official_offers(items, cfg, tmp_path, transport=boom)
    assert stats == {"enabled": False, "links_swapped": 0, "offers_written": 0, "blocked_floor": 0}
    assert items[0]["affiliate_links"]["aliexpress"] == before
    assert not (tmp_path / "live_offers_cache.json").exists()


def _fake_transport(prices: dict[str, str]):
    calls = []

    def transport(url: str, params: dict) -> dict:
        calls.append(params)
        assert url == ali_api.GATEWAY_URL
        assert params["tracking_id"] == "default" and params["sign_method"] == "sha256"
        assert params["sign"] == ali_api.sign_request({k: v for k, v in params.items() if k != "sign"}, "s3cret")
        if params["method"] == "aliexpress.affiliate.link.generate":
            rows = [{"source_value": src, "promotion_link": f"https://s.click.aliexpress.com/e/_{i}"}
                    for i, src in enumerate(params["source_values"].split(","))]
            return {"aliexpress_affiliate_link_generate_response": {"resp_result": {
                "resp_code": 200, "result": {"promotion_links": {"promotion_link": rows}}}}}
        rows = [{"product_id": pid, "target_sale_price": prices[pid], "target_sale_price_currency": "USD",
                 "promotion_link": f"https://s.click.aliexpress.com/e/_item{pid}"}
                for pid in params["product_ids"].split(",") if pid in prices]
        return {"aliexpress_affiliate_productdetail_get_response": {"resp_result": {
            "resp_code": 200, "result": {"products": {"product": rows}}}}}

    transport.calls = calls
    return transport


def test_api_upgrade_swaps_promotion_links_and_enforces_the_msrp_floor(monkeypatch, tmp_path, approved, cfg):
    monkeypatch.setenv("ALIEXPRESS_APP_KEY", "12345")
    monkeypatch.setenv("ALIEXPRESS_APP_SECRET", "s3cret")
    items = []
    for it, ali_id in zip(approved[:3], ("1001", "1002", None)):
        clone = dict(it, urls=dict(it["urls"]), affiliate_links=dict(it["affiliate_links"]))
        if ali_id:
            clone["urls"]["ali_product_id"] = ali_id
        items.append(clone)
    good, trap = items[0], items[1]
    good_price = round(float(good["msrp_usd"]) * 0.8, 2)
    transport = _fake_transport({"1001": f"{good_price:.2f}", "1002": "2.99"})

    stats = ali_api.refresh_official_offers(items, cfg, tmp_path, transport=transport, now=NOW)

    assert stats["enabled"] and stats["links_swapped"] == 3
    assert stats["offers_written"] == 1 and stats["blocked_floor"] == 1
    assert all(it["affiliate_links"]["aliexpress"].startswith("https://s.click.aliexpress.com/") for it in items)
    assert good["affiliate_links"]["aliexpress"] == "https://s.click.aliexpress.com/e/_item1001"

    offers = load_live_offers(tmp_path, now=NOW)["offers"]
    assert set(offers) == {good["id"]}, "a $2.99 'sale price' far below 0.35 x MSRP must be refused"
    entry = offers[good["id"]][0]
    assert entry["source_kind"] == "ali_official_api" and entry["price"] == good_price
    assert entry["promotion_link"].startswith("https://s.click.aliexpress.com/")
    assert datetime.fromisoformat(entry["expires_at"]) - NOW == timedelta(hours=ali_api.API_OFFER_TTL_HOURS)
    assert trap["id"] not in offers
    assert "s3cret" not in (tmp_path / "live_offers_cache.json").read_text(encoding="utf-8")


def test_api_failures_are_fail_closed(monkeypatch, tmp_path, approved, cfg):
    monkeypatch.setenv("ALIEXPRESS_APP_KEY", "12345")
    monkeypatch.setenv("ALIEXPRESS_APP_SECRET", "s3cret")

    def broken(url, params):
        raise OSError("gateway unreachable")

    items = [dict(approved[0], affiliate_links=dict(approved[0]["affiliate_links"]))]
    before = items[0]["affiliate_links"]["aliexpress"]
    stats = ali_api.refresh_official_offers(items, cfg, tmp_path, transport=broken)
    assert stats["links_swapped"] == 0 and items[0]["affiliate_links"]["aliexpress"] == before
    assert ali_api.generate_promotion_links(["https://www.aliexpress.com/x"], cfg,
                                            transport=lambda u, p: {"error_response": {"code": "IllegalAccessToken"}}) == {}
    assert not ali_api.is_promotion_link("https://evil.example/s.click.aliexpress.com")


def test_page_script_never_rewrites_official_promotion_links(built):
    js = read(built["dist"] / "assets" / "app.js")
    assert r"!/^(s\.click|a)\./.test(u.hostname)" in js


def test_affiliate_builder_supports_direct_deep_links(cfg):
    from src.affiliate import build_affiliate_links

    base = {"model": "X1", "urls": {"coupang_query": "브랜드 X1", "ali_query": "Brand X1", "amazon_query": "Brand X1"}}
    plain = build_affiliate_links(base, cfg["affiliate"])
    assert "lptag=AF8784203" in plain["coupang"] and "aff_fcid=default" in plain["aliexpress"]
    assert plain["amazon"].endswith("&tag=gearcomparehu-20")

    direct = dict(base, urls=dict(base["urls"], coupang_direct="https://link.coupang.com/a/abc",
                                  ali_direct="https://s.click.aliexpress.com/e/_xyz",
                                  amazon_direct="https://www.amazon.com/dp/B0ABCDEFGH"))
    links = build_affiliate_links(direct, cfg["affiliate"])
    assert links["coupang"] == "https://link.coupang.com/a/abc"
    assert links["aliexpress"] == "https://s.click.aliexpress.com/e/_xyz", "API promotion links pass through untouched"
    assert links["amazon"] == "https://www.amazon.com/dp/B0ABCDEFGH?tag=gearcomparehu-20"


# ------------------------------------------------------------------ promo tiers + traffic light
def test_promo_tier_file_has_reference_ladder_and_honest_notice():
    data = json.loads((ROOT / "data" / "ali_promo_tiers.json").read_text(encoding="utf-8"))
    ladder = [(t["min_spend_usd"], t["off_usd"]) for t in data["reference_tiers"]["tiers"]]
    assert ladder == [(19, 2), (39, 5), (79, 10), (159, 20), (299, 40)]
    assert data["notice"]["ko"] == "선착순 소진·일부 품목 제외 가능 — 결제창 최종 적용 확인"
    assert data["notice"]["en"] == "Limited redemptions & exclusions apply — verify at checkout"
    for ev in data["events"]:
        assert ev["starts"] <= ev["ends"] and ev["langs"] and ev["source_url"].startswith("https://")
        assert all(t["code"] and 0 < t["off_usd"] < t["min_spend_usd"] for t in ev["tiers"])


@pytest.mark.parametrize(
    "day, window",
    [
        (date(2026, 3, 1), "choice"), (date(2026, 3, 7), "choice"), (date(2026, 3, 8), "standard"),
        (date(2026, 3, 25), "standard"), (date(2026, 3, 26), "hold"), (date(2026, 3, 31), "hold"),
        (date(2026, 11, 10), "standard"), (date(2026, 11, 11), "mega"), (date(2026, 11, 18), "mega"),
        (date(2026, 11, 19), "standard"), (date(2026, 11, 20), "mega"), (date(2026, 11, 28), "mega"),
        (date(2026, 12, 3), "mega"), (date(2026, 12, 4), "choice"), (date(2026, 12, 26), "hold"),
    ],
)
def test_sale_window_by_date(day, window):
    assert sale_window(day) == window


def test_traffic_light_labels_match_the_specification():
    assert sale_signal("ko", date(2026, 5, 3)) | {"sub": ""} == {
        "window": "choice", "tone": "go", "label": "매수 적기 · 알리 초이스데이 주간", "sub": ""}
    assert sale_signal("en", date(2026, 5, 3))["label"] == "BUY WINDOW · Choice Day Week"
    assert sale_signal("ko", date(2026, 11, 28))["label"] == "매수 적기 · 연말 메가세일·블프 구간"
    assert sale_signal("en", date(2026, 11, 28))["label"] == "BUY WINDOW · Mega Sale Window"
    assert sale_signal("ko", date(2026, 5, 27))["label"] == "대기 권장 · 매월 1일 초이스데이 임박 (급하면 쿠팡·아마존)"
    assert sale_signal("en", date(2026, 5, 27))["label"] == "HOLD · Choice Day Opens 1st (Use Prime if Urgent)"
    assert sale_signal("ko", date(2026, 5, 15))["label"] == "상시 코드·카드할인 구간 (쿠팡·아마존 실결제가 대조 필수)"
    assert sale_signal("en", date(2026, 5, 15))["label"] == "STANDARD WINDOW · Compare Prime vs Promo Code"
    tones = {w: SALE_COPY["en"][w][0] for w in SALE_COPY["en"]}
    assert tones == {"mega": "go", "choice": "go", "hold": "hold", "standard": "std"}


def test_reference_clock_per_language():
    at = datetime(2026, 11, 30, 23, 30, tzinfo=timezone.utc)  # Dec 1 08:30 KST, Nov 30 15:30 PT
    assert sale_reference_date("ko", at) == date(2026, 12, 1)
    assert sale_reference_date("en", at) == date(2026, 11, 30)


def test_active_promo_uses_dated_event_then_falls_back_to_reference_tiers():
    data = load_promo_tiers(ROOT)
    assert active_promo(data, "ko", date(2026, 11, 28))["kind"] == "reference"
    ref = active_promo(data, "en", date(2026, 12, 4))
    assert ref["kind"] == "reference" and all(t["code"] is None for t in ref["tiers"])
    for ev in data["events"]:
        lang = ev["langs"][0]
        live = active_promo(data, lang, date.fromisoformat(ev["starts"]))
        assert live["kind"] == "event" and all(t["code"] for t in live["tiers"])
        after = date.fromisoformat(ev["ends"]) + timedelta(days=1)
        assert active_promo(data, lang, after)["kind"] == "reference", "codes disappear the day after the event ends"


def test_load_promo_tiers_falls_back_when_file_is_missing(tmp_path):
    data = load_promo_tiers(tmp_path)
    assert [t["min_spend_usd"] for t in data["reference_tiers"]["tiers"]] == [19, 39, 79, 159, 299]


# ------------------------------------------------------------------ calculator maths
REF = [{"min_spend_usd": s, "off_usd": o, "code": None} for s, o in ((19, 2), (39, 5), (79, 10), (159, 20), (299, 40))]


def test_best_tier_selection():
    assert best_promo_tier(18.99, REF) is None
    assert best_promo_tier(39, REF)["off_usd"] == 5
    assert best_promo_tier(500, REF)["off_usd"] == 40


def test_checkout_applies_coin_then_coupon_then_tier_and_judges_the_150_line():
    r = compute_promo_checkout(169.99, store_coupon_usd=5, coin_pct=2, tiers=REF, origin="cn", msrp_usd=169.0)
    assert r["coin_off_usd"] == 3.4 and r["coupon_off_usd"] == 5.0 and r["subtotal_usd"] == 161.59
    assert r["tier"]["min_spend_usd"] == 159 and r["tier_off_usd"] == 20
    assert r["net_usd"] == 141.59 and r["net_krw"] == 198226
    assert r["duty_free"] and r["customs_threshold_usd"] == 150 and r["customs_margin_usd"] == 8.41
    assert r["vs_msrp_usd"] == 27.41 and r["vs_msrp_pct"] == 16.2


def test_coupon_can_drop_the_cart_below_a_tier():
    with_coupon = compute_promo_checkout(160, store_coupon_usd=5, tiers=REF)
    assert with_coupon["subtotal_usd"] == 155 and with_coupon["tier"]["min_spend_usd"] == 79
    assert with_coupon["next_tier"]["min_spend_usd"] == 159 and with_coupon["next_tier_gap_usd"] == 4.0
    picked = compute_promo_checkout(160, store_coupon_usd=5, tiers=REF, tier_choice=159)
    assert picked["tier"] is None and picked["tier_off_usd"] == 0 and picked["tier_shortfall_usd"] == 4.0


def test_over_threshold_estimates_vat_and_us_route_uses_200():
    cn = compute_promo_checkout(189, tiers=REF, origin="cn")
    assert cn["net_usd"] == 169 and not cn["duty_free"]
    assert cn["customs_margin_usd"] == -19.0 and cn["est_vat_usd"] == 16.9
    us = compute_promo_checkout(189, tiers=REF, origin="us")
    assert us["duty_free"] and us["customs_threshold_usd"] == 200 and us["customs_margin_usd"] == 31.0


def test_custom_none_and_input_clamping():
    assert compute_promo_checkout(100, tiers=REF, tier_choice="none")["net_usd"] == 100
    assert compute_promo_checkout(100, tiers=REF, tier_choice="custom", custom_off_usd=12.5)["net_usd"] == 87.5
    assert compute_promo_checkout(100, tiers=REF, tier_choice="custom", custom_off_usd=999)["net_usd"] == 0
    assert compute_promo_checkout(50, store_coupon_usd=80, coin_pct=250, tiers=REF)["net_usd"] == 0
    assert compute_promo_checkout(-5, tiers=REF)["net_usd"] == 0
    assert compute_promo_checkout(649, store_coupon_usd=20, coin_pct=1.5, tiers=REF)["coin_off_usd"] == 9.74
    en = compute_promo_checkout(120, tiers=REF, origin="cross")
    assert en["customs_threshold_usd"] is None and en["duty_free"] is False
    assert compute_promo_checkout(120, tiers=REF, origin="domestic")["duty_free"] is True


def test_anchor_customs_verdicts():
    assert kr_customs_anchor(59.99) == ("is-in", "$150 면세선 이내")
    assert kr_customs_anchor(150.0)[0] == "is-in"
    assert kr_customs_anchor(199.99)[0] == "is-edge"
    assert kr_customs_anchor(649.0) == ("is-over", "면세선 초과 · 부가세 10% 대상")


# ------------------------------------------------------------------ calculator pages
def test_calculator_pages_render_inputs_presets_and_dual_store_buttons(built, approved):
    ko = read(built["dist"] / "ko" / "tools" / "ali-promo-calculator" / "index.html")
    en = read(built["dist"] / "en" / "tools" / "ali-promo-calculator" / "index.html")
    for page in (ko, en):
        for name in ("preset", "price", "coupon", "coin", "tier", "custom", "origin"):
            assert f'name="{name}"' in page
        assert page.count("<optgroup") == len({it["category"] for it in approved})
        assert page.count('<option value="') >= len(approved) + 3
    assert 'id="pc-rate"' in ko and 'value="1400"' in ko and 'id="pc-rate"' not in en
    assert "중국·기타발 한국 수령 $150 면세" in ko and "미국발 목록통관 $200 면세" in ko
    assert "US Domestic Warehouse" in en and "Cross-Border Direct Import" in en
    assert "알리 프로모션·직구 확인" in ko and "쿠팡 로켓 현재가 대조" in ko
    assert "Check AliExpress Store" in en and "Check Amazon US Prime" in en
    assert "면세 안전권 ({g} 여유)" in ko and "관부가세 부과 구간" in ko
    assert "선착순 소진·일부 품목 제외 가능 — 결제창 최종 적용 확인" in ko
    assert "Limited redemptions &amp; exclusions apply — verify at checkout" in en
    assert 'hreflang="en" href="' in ko and "/en/tools/ali-promo-calculator/" in ko

    payload = json.loads(ko.split("data-promo-json>")[1].split("</script>")[0])
    assert len(payload["products"]) == len(approved)
    sample = payload["products"][0]
    assert sample["msrp_usd"] > 0 and "coupang.com" in sample["dom"] and "aliexpress.com" in sample["ali"]
    en_payload = json.loads(en.split("data-promo-json>")[1].split("</script>")[0])
    assert "amazon.com" in en_payload["products"][0]["dom"]
    assert [t["min_spend_usd"] for t in payload["ref"]["tiers"]] == [19, 39, 79, 159, 299]


def test_calculator_is_wired_into_nav_footer_sitemap_and_product_pages(built, approved):
    from src.site_builder import product_slug

    dist = built["dist"]
    hub = read(dist / "ko" / "index.html")
    assert 'href="../ko/tools/ali-promo-calculator/">알리 코드 계산기</a>' in hub  # header
    assert hub.count("tools/ali-promo-calculator/") >= 3  # header + board + footer + anchors
    detail = read(dist / "ko" / "p" / product_slug(approved[0]["id"]) / "index.html")
    assert f'../../tools/ali-promo-calculator/?p={approved[0]["id"]}' in detail
    sitemap = read(dist / "sitemap.xml")
    for lang in ("ko", "en"):
        assert f"{built['base']}/{lang}/tools/ali-promo-calculator/</loc>" in sitemap
    assert f"{built['base']}/ko/tools/ali-promo-calculator/</link>" in read(dist / "ko" / "feed.xml")
    assert "/en/tools/ali-promo-calculator/?utm_source=pinterest" in read(dist / "en" / "pinterest-feed.xml")
