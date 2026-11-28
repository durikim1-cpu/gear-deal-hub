"""Pillar 5.1 (full signal pass-through) and Pillar 2 Tier 1 (community benchmark cache: floor + TTL)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import ROOT
from src import collector
from src.collector import parse_krw_price, parse_usd_price
from src.deal_sniper import (
    COMMUNITY_TTL_HOURS,
    harvest_community_benchmarks,
    load_live_offers,
    match_signal_to_product,
    pick_live_offer,
    price_passes_msrp_floor,
)

NOW = datetime(2026, 11, 28, 3, 0, tzinfo=timezone.utc)


def _sig(title: str, source: str = "reddit/buildapcsales", url: str | None = None) -> dict:
    return {"source": source, "title": title, "score": 50, "url": url or f"https://www.reddit.com/r/x/{abs(hash(title))}"}


# ------------------------------------------------------------------ signal pass-through
def test_collector_passes_every_signal_not_only_the_preview(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    for name in ("products.json", "candidates_inbox.json"):
        shutil.copy(ROOT / "data" / name, tmp_path / "data" / name)
    reddit = [_sig(f"Reddit hardware post {i}") for i in range(23)]
    kr = [_sig(f"뽐뿌 게시글 {i}", source="ppomppu_kr") for i in range(14)]
    monkeypatch.setattr(collector, "fetch_reddit_signals", lambda *a, **k: reddit)
    monkeypatch.setattr(collector, "fetch_kr_rss_signals", lambda *a, **k: kr)

    staged = collector.collect_candidates(tmp_path, live_network=True)

    assert staged["trend_signals_count"] == 37
    assert staged["trend_signals"] == reddit + kr, "all fetched signals must be passed through"
    assert staged["trend_signals_preview"] == (reddit + kr)[:8], "the preview stays a compact 8-item sample"
    on_disk = json.loads((tmp_path / "data" / "candidates_staged.json").read_text(encoding="utf-8"))
    assert len(on_disk["trend_signals"]) == 37
    refreshed = collector.collect_candidates(tmp_path, prior_stage=staged)
    assert refreshed["trend_signals"] == reddit + kr
    assert refreshed["new_model_leads_found"] == staged["new_model_leads_found"]


def test_pipeline_reads_full_signal_list_with_preview_fallback():
    import run_pipeline

    full = [{"title": f"s{i}"} for i in range(30)]
    assert run_pipeline.select_live_signals({"trend_signals": full, "trend_signals_preview": full[:8]}) == full
    assert run_pipeline.select_live_signals({"trend_signals_preview": full[:8]}) == full[:8]
    assert run_pipeline.select_live_signals({"trend_signals": [], "trend_signals_preview": full[:8]}) == []
    assert run_pipeline.select_live_signals({}) == []
    source = (ROOT / "run_pipeline.py").read_text(encoding="utf-8")
    assert "live_signals = select_live_signals(staged)" in source


def test_sniper_matches_current_prices_and_codes_after_the_preview(tmp_path, approved, cfg):
    from src.deal_sniper import snipe_hot_deals

    sample = [_sig(f"unrelated {i}") for i in range(8)]
    sample.extend([
        _sig("AULA F75 Pro keyboard promo code WRONG20 $59.99"),
        dict(_sig("Anker Prime 100W A2688 charger $49.99"), destination_url="https://amzn.to/example"),
        _sig("Anker Prime 100W A2688 charger coupon works"),
        dict(_sig("Anker Prime 100W A2688 charger coupon SAVE20 $49.99"), published_at="2000-01-01T00:00:00Z"),
        _sig("[알리] 독거미 F75 키보드 59000원", source="ppomppu_kr"),
    ])
    picks = snipe_hot_deals(approved, sample, tmp_path, cfg)["ko_picks"]
    assert [p["id"] for p in picks] == ["aula-f75-wireless-keyboard"]
    assert picks[0]["sniper"]["promo_code"] is None

    sample.append(_sig("[알리] 독거미 F75 키보드 쿠폰 코드 KRBF07", source="ppomppu_kr"))
    picks = snipe_hot_deals(approved, sample, tmp_path, cfg)["ko_picks"]
    assert [p["sniper"]["promo_code"] for p in picks] == ["KRBF07"]


def test_offline_collect_has_empty_signal_list(tmp_path):
    (tmp_path / "data").mkdir()
    for name in ("products.json", "candidates_inbox.json"):
        shutil.copy(ROOT / "data" / name, tmp_path / "data" / name)
    staged = collector.collect_candidates(tmp_path, live_network=False)
    assert staged["trend_signals"] == [] and staged["trend_signals_preview"] == []


# ------------------------------------------------------------------ price parsing
@pytest.mark.parametrize(
    "title, usd, krw",
    [
        ("[Keyboard] AULA F75 - $49.99 ($69.99 - $20 coupon)", 49.99, None),
        ("USB-C cable option from $2.99", 2.99, None),
        ("$20 off coupon: AULA F75 now $55", 55.0, None),
        ("$20.50 off coupon: AULA F75 now $55.99", 55.99, None),
        ("AULA F75 now $55.99, shipped", 55.99, None),
        ("Beelink SER8 $1,049.00 shipped", 1049.0, None),
        ("[알리] 독거미 F75 키보드 (45,000원/무료)", None, 45000),
        ("[알리] 독거미 F75 키보드 (45000원/무료)", None, 45000),
        ("5,000원 할인 쿠폰 적용 독거미 62,000원", None, 62000),
        ("no price here", None, None),
    ],
)
def test_usd_and_krw_deal_price_parsers(title, usd, krw):
    assert parse_usd_price(title) == usd
    assert parse_krw_price(title) == krw


# ------------------------------------------------------------------ model matching precision
@pytest.mark.parametrize(
    "title, expected",
    [
        ("[Keyboard] AULA F75 75% Wireless - $49.99", "aula-f75-wireless-keyboard"),
        ("[알리] 독거미 F75 키보드 (45,000원/무료)", "aula-f75-wireless-keyboard"),
        ("AULA F75 Pro keyboard $59", None),  # sibling variant
        ("AULA F75 keycaps set $12.99", None),  # accessory
        ("[SSD] Samsung T7 Shield 1TB $79", None),  # other capacity
        ("[SSD] Samsung T7 Shield 2TB $139.99", "samsung-t7-shield-2tb"),
        ("UGREEN Nexode 100W charger $39.99", "ugreen-nexode-100w-4port"),
        ("UGREEN Nexode 100W 20000mAh power bank $49", None),  # other category
        ("Anker Prime 100W GaN charger A2688 $59.99", "anker-prime-100w-a2688"),
        ("8BitDo Ultimate 2 Wireless controller $49", None),  # different model generation
        ("8BitDo Ultimate 2C Wireless controller $24.99", "8bitdo-ultimate-2c-wireless"),
        ("Keychron K2 keyboard $69", None),  # catalog model is the K2 Max
        ("Totally unrelated gadget $19", None),
    ],
)
def test_signal_to_product_matching_prefers_precision(catalog, title, expected):
    match = match_signal_to_product(title, catalog)
    assert (match["id"] if match else None) == expected


# ------------------------------------------------------------------ 0.35 floor + TTL
def test_msrp_floor_boundaries():
    assert price_passes_msrp_floor(24.50, 69.99, 0.35)  # exactly at the floor (69.99 * 0.35 = 24.4965)
    assert not price_passes_msrp_floor(24.49, 69.99, 0.35)
    assert not price_passes_msrp_floor(2.99, 69.99, 0.35)
    assert not price_passes_msrp_floor(0, 69.99, 0.35)
    assert not price_passes_msrp_floor(500, 69.99, 0.35), "implausibly high prices are a different listing"


def test_harvest_writes_floor_checked_benchmarks_with_48h_ttl(tmp_path, catalog, cfg):
    signals = [
        _sig("[Keyboard] AULA F75 75% Wireless - $49.99"),
        _sig("[Keyboard] AULA F99 96% wireless keyboard from $2.99"),  # option-listing trap -> blocked by floor
        _sig("[알리] 독거미 F75 키보드 (59,000원/무료)", source="ppomppu_kr", url="https://www.ppomppu.co.kr/x/1"),
        _sig("[SSD] Samsung T7 Shield 2TB $139.99 on Amazon", url="https://www.amazon.com/dp/B0"),  # Amazon excluded
        _sig("Random post without any catalog model $25"),
    ]
    stats = harvest_community_benchmarks(catalog, signals, tmp_path, cfg=cfg, now=NOW)

    assert stats["signals_scanned"] == 5
    assert stats["blocked_floor"] == 1
    cache = json.loads((tmp_path / "live_offers_cache.json").read_text(encoding="utf-8"))
    assert set(cache["offers"]) == {"aula-f75-wireless-keyboard"}, "floor-blocked and Amazon signals never reach the cache"

    entries = {e["currency"]: e for e in cache["offers"]["aula-f75-wireless-keyboard"]}
    assert entries["USD"]["price"] == 49.99 and entries["USD"]["price_text"] == "$49.99"
    assert entries["KRW"]["price"] == 59000 and entries["KRW"]["price_text"] == "59,000원"
    for e in entries.values():
        assert e["source_kind"] == "community_benchmark"
        observed = datetime.fromisoformat(e["observed_at"])
        expires = datetime.fromisoformat(e["expires_at"])
        assert observed == NOW
        assert expires - observed == timedelta(hours=48) == timedelta(hours=COMMUNITY_TTL_HOURS)


def test_only_deal_boards_supply_price_benchmarks(tmp_path, catalog, cfg):
    discussion = [
        _sig("Is the [Mini PC] Beelink SER8 Ryzen 7 8745HS 32GB/1TB worth $499?", source="reddit/MiniPCs"),
        _sig("[Keyboard] AULA F75 75% Wireless - $49.99", source="reddit/MechanicalKeyboards"),
    ]
    stats = harvest_community_benchmarks(catalog, discussion, tmp_path, cfg=cfg, now=NOW)
    assert stats["matched"] == 0 and stats["written"] == 0
    assert load_live_offers(tmp_path, now=NOW)["offers"] == {}, "discussion-subreddit prices are not deal benchmarks"

    deals = [
        _sig("[Mini PC] Beelink SER8 Ryzen 7 8745HS 32GB/1TB $499", source="reddit/buildapcsales"),
        _sig("[알리] 독거미 F75 키보드 (59,000원/무료)", source="ppomppu_kr", url="https://www.ppomppu.co.kr/x/3"),
    ]
    harvest_community_benchmarks(catalog, deals, tmp_path, cfg=cfg, now=NOW)
    offers = load_live_offers(tmp_path, now=NOW)["offers"]
    assert [(e["currency"], e["price"]) for e in offers["beelink-ser8-8745hs-minipc"]] == [("USD", 499.0)]
    assert [(e["currency"], e["price"]) for e in offers["aula-f75-wireless-keyboard"]] == [("KRW", 59000)]


def test_floor_uses_configured_min_price_ratio(tmp_path, catalog, cfg):
    strict = {**cfg, "gatekeeper": {**cfg["gatekeeper"], "min_price_ratio_vs_msrp": 0.9}}
    stats = harvest_community_benchmarks(catalog, [_sig("[Keyboard] AULA F75 75% Wireless - $49.99")], tmp_path, cfg=strict, now=NOW)
    assert stats["blocked_floor"] == 1 and stats["active_products"] == 0


def test_expired_entries_are_dropped_and_ttl_is_not_extended_by_the_same_post(tmp_path, catalog, cfg):
    sig = _sig("[Keyboard] AULA F75 75% Wireless - $49.99", url="https://www.reddit.com/r/x/same")
    harvest_community_benchmarks(catalog, [sig], tmp_path, cfg=cfg, now=NOW)

    # The same post is still in the hot feed 30 hours later: first-seen timestamps must be kept.
    harvest_community_benchmarks(catalog, [sig], tmp_path, cfg=cfg, now=NOW + timedelta(hours=30))
    entry = load_live_offers(tmp_path, now=NOW + timedelta(hours=30))["offers"]["aula-f75-wireless-keyboard"][0]
    assert datetime.fromisoformat(entry["expires_at"]) == NOW + timedelta(hours=48)

    assert load_live_offers(tmp_path, now=NOW + timedelta(hours=47, minutes=59))["offers"]
    assert load_live_offers(tmp_path, now=NOW + timedelta(hours=48, seconds=1))["offers"] == {}


def test_load_live_offers_is_fail_closed(tmp_path):
    assert load_live_offers(tmp_path)["offers"] == {}
    (tmp_path / "live_offers_cache.json").write_text("{not json", encoding="utf-8")
    assert load_live_offers(tmp_path)["offers"] == {}
    (tmp_path / "live_offers_cache.json").write_text(
        json.dumps({"offers": {"x": [{"source_kind": "mystery", "currency": "USD", "price": 5, "expires_at": "2999-01-01T00:00:00+00:00"},
                                     {"source_kind": "community_benchmark", "currency": "USD", "price": 5}]}}),
        encoding="utf-8",
    )
    assert load_live_offers(tmp_path)["offers"] == {}, "unknown kinds and entries without an expiry are dropped"


def test_pick_live_offer_language_rules_and_api_priority():
    future = (NOW + timedelta(hours=5)).isoformat()
    cache = {"offers": {"p": [
        {"source_kind": "community_benchmark", "currency": "KRW", "price": 59000, "price_text": "59,000원", "expires_at": future},
        {"source_kind": "community_benchmark", "currency": "USD", "price": 49.99, "price_text": "$49.99", "expires_at": future},
    ]}}
    assert pick_live_offer(cache, "p", "ko", now=NOW)["currency"] == "KRW"
    assert pick_live_offer(cache, "p", "en", now=NOW)["currency"] == "USD", "English pages never show KRW benchmarks"
    cache["offers"]["p"].append({"source_kind": "ali_official_api", "currency": "USD", "price": 47.0, "price_text": "$47.00", "expires_at": future})
    assert pick_live_offer(cache, "p", "ko", now=NOW)["source_kind"] == "ali_official_api"
    assert pick_live_offer(cache, "p", "en", now=NOW + timedelta(hours=6)) is None, "expired at read time"
    assert pick_live_offer(None, "p", "en") is None


def test_board_grade_promo_codes_need_ali_context_and_a_real_token(tmp_path, catalog, cfg):
    signals = [
        _sig("[알리] 블프 프로모션 코드 KRBF07 적용 방법", source="ppomppu_kr", url="https://www.ppomppu.co.kr/x/2"),
        _sig("coupon stack works great on this keyboard"),  # no code-shaped token
        _sig("Use code SAVE10 at some other store"),  # no AliExpress context
    ]
    stats = harvest_community_benchmarks(catalog, signals, tmp_path, cfg=cfg, now=NOW)
    codes = load_live_offers(tmp_path, now=NOW)["promo_codes"]
    assert stats["codes_spotted"] == 1
    assert [c["code"] for c in codes] == ["KRBF07"]
    assert datetime.fromisoformat(codes[0]["expires_at"]) - NOW == timedelta(hours=48)


# ------------------------------------------------------------------ strict labels on rendered pages
def test_rendered_labels_never_present_a_community_post_as_a_live_store_price(tmp_path, approved, cfg):
    from src.site_builder import build_site, product_slug

    a, b = approved[0], approved[1]
    future = (NOW + timedelta(hours=40)).isoformat(timespec="seconds")
    cache = {"updated_at": NOW.isoformat(), "promo_codes": [], "offers": {
        a["id"]: [{"source_kind": "community_benchmark", "currency": "USD", "price": 41.0, "price_text": "$41.00",
                   "observed_at": NOW.isoformat(timespec="seconds"), "expires_at": future}],
        b["id"]: [{"source_kind": "ali_official_api", "currency": "USD", "price": 50.5, "price_text": "$50.50",
                   "observed_at": NOW.isoformat(timespec="seconds"), "expires_at": future}],
    }}
    dist = tmp_path / "dist"
    build_site(approved, cfg, dist, live_offers=cache, now=NOW)

    ko = (dist / "ko" / "p" / product_slug(a["id"]) / "index.html").read_text(encoding="utf-8")
    en = (dist / "en" / "p" / product_slug(a["id"]) / "index.html").read_text(encoding="utf-8")
    assert "최근 커뮤니티 포착 핫딜 기준가 (관측일 2026-11-28 · 종료 가능)" in ko
    assert "Recent Community-Spotted Deal Benchmark (Observed 2026-11-28 · May Expire)" in en
    for page in (ko, en):
        assert f'data-expires-at="{future}"' in page, "client-side auto-hide needs the expiry on the element"
        assert 'data-live-kind="community_benchmark"' in page
        assert "실시간 알리 API 특가" not in page and "Live AliExpress API Offer" not in page

    api_ko = (dist / "ko" / "p" / product_slug(b["id"]) / "index.html").read_text(encoding="utf-8")
    api_en = (dist / "en" / "p" / product_slug(b["id"]) / "index.html").read_text(encoding="utf-8")
    assert "실시간 알리 API 특가" in api_ko and "Live AliExpress API Offer" in api_en
    assert 'data-live-kind="ali_official_api"' in api_en

    # Hub cards carry the same strict label; the shared script hides expired lines.
    assert "Recent Community-Spotted Deal Benchmark" in (dist / "en" / "index.html").read_text(encoding="utf-8")
    js = (dist / "assets" / "app.js").read_text(encoding="utf-8")
    assert "[data-expires-at]" in js and "el.hidden = true" in js


def test_cache_file_is_runtime_data_not_tracked():
    assert "data/live_offers_cache.json" in (ROOT / ".gitignore").read_text(encoding="utf-8")
