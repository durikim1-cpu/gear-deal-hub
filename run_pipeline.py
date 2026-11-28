"""End-to-end zero-cost affiliate automation runner:
 Phase 1 (Build): Collect -> Auto-Grow -> Gatekeeper Verify -> Live Offer Cache (community benchmarks + optional
   official AliExpress API) -> Static Site (hubs, tools, KO/EN guides, VS battles) -> Pinterest PNG/RSS -> Stage Broadcast Queue.
 Phase 2 (Post-Deploy Dispatch): IndexNow full-sitemap ping -> Verify live GitHub Pages URL (HTTP 200 + content)
   -> Idempotent Telegram & Threads<=1/day dispatch.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from src.affiliate import load_config
from src.notifier import dispatch_verified_alerts, stage_alerts_preview
from src.social_publisher import publish_verified_social, stage_social_queues

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
INDEXNOW_MAX_URLS_PER_POST = 10000
_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def parse_sitemap_urls(xml_text: str) -> list[str]:
    """Every <loc> in a sitemap, in document order, de-duplicated."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except ET.ParseError:
        return []
    locs = [(el.text or "").strip() for el in root.iter(f"{_SITEMAP_NS}loc")]
    return list(dict.fromkeys(u for u in locs if u))


def collect_indexnow_urls(base_url: str, dist_dir: Path, fetch=None) -> list[str]:
    """Full canonical URL list for IndexNow.

    Source order: the sitemap from this build, the deployed sitemap, then a minimal core list.
    Only URLs within this site's base URL are submitted.
    """
    base = base_url.rstrip("/")
    urls: list[str] = []
    local = Path(dist_dir) / "sitemap.xml"
    if local.exists():
        urls = parse_sitemap_urls(local.read_text(encoding="utf-8"))
    if not urls:
        def _default_fetch(url: str) -> str:
            req = urllib.request.Request(url, headers={"User-Agent": "GearCompareHubIndexer/1.0", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read().decode("utf-8", errors="replace")
        try:
            urls = parse_sitemap_urls((fetch or _default_fetch)(f"{base}/sitemap.xml"))
        except (urllib.error.URLError, TimeoutError, OSError):
            urls = []
    if not urls:
        urls = [
            f"{base}/", f"{base}/ko/", f"{base}/en/",
            f"{base}/ko/tools/macbook-dock-checker/", f"{base}/en/tools/macbook-dock-checker/",
            f"{base}/ko/tools/ali-promo-calculator/", f"{base}/en/tools/ali-promo-calculator/",
            f"{base}/ko/guides/", f"{base}/en/guides/", f"{base}/ko/vs/", f"{base}/en/vs/",
        ]
    return [u for u in urls if u.startswith(f"{base}/")]


def submit_indexnow(base_url: str, key: str, urls: list[str], post=None) -> list[int]:
    """POST the URL list to IndexNow (chunked at the 10,000-URL single-request limit). Returns HTTP statuses."""
    base = base_url.rstrip("/")
    host = urllib.parse.urlparse(base).hostname or ""
    statuses: list[int] = []

    def _default_post(payload: dict) -> int:
        req = urllib.request.Request(
            INDEXNOW_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return int(r.status)

    for start in range(0, len(urls), INDEXNOW_MAX_URLS_PER_POST):
        idx_payload = {
            "host": host,
            "key": key,
            "keyLocation": f"{base}/{key}.txt",
            "urlList": urls[start:start + INDEXNOW_MAX_URLS_PER_POST],
        }
        statuses.append((post or _default_post)(idx_payload))
    return statuses


def select_live_signals(staged: dict) -> list[dict]:
    """All fetched community signals for this run.

    `trend_signals` carries every Reddit + Ppomppu item; `trend_signals_preview` is only an 8-item
    human-readable sample and is used solely as a fallback for staged files written by older builds.
    """
    return staged.get("trend_signals", staged.get("trend_signals_preview", []))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GearCompare Hub unified compliance-verified pipeline.")
    parser.add_argument(
        "--live-network",
        action="store_true",
        help="Fetch live public Reddit JSON + Korean hot-deal RSS feeds and queue new model leads.",
    )
    parser.add_argument(
        "--auto-grow",
        type=int,
        default=0,
        metavar="N",
        help="Automatically enrich, verify, and append up to N newly discovered models to products.json.",
    )
    parser.add_argument(
        "--dispatch-deployed",
        action="store_true",
        help="Run ONLY post-deploy IndexNow ping, public-URL verification & idempotent notification dispatch from pending_broadcast.json.",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Actually dispatch verified live-matched alerts to Telegram after public URL HTTP check.",
    )
    parser.add_argument(
        "--publish-social",
        action="store_true",
        help="Publish <=1/day Threads post if a live signal matched and public URL HTTP check passed.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    data_dir = project_root / "data"
    pending_path = data_dir / "pending_broadcast.json"
    cfg = load_config(project_root)

    if args.dispatch_deployed:
        # Ping IndexNow (Bing, Naver IndexNow partner network, Yandex) with every canonical sitemap URL on each deploy
        idx_key = (cfg.get("site", {}).get("indexnow_key") or "").strip()
        base_url = cfg["site"]["base_url"].rstrip("/")
        if idx_key:
            try:
                idx_urls = collect_indexnow_urls(base_url, dist_dir)
                for status in submit_indexnow(base_url, idx_key, idx_urls):
                    print(f"IndexNow ping status           : HTTP {status} ({len(idx_urls)} sitemap URLs submitted)")
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                print(f"[IndexNow note] {exc}")

        if not pending_path.exists():
            print("No pending_broadcast.json found; skipping post-deploy dispatch.")
            return 0
        staged_payload = json.loads(pending_path.read_text(encoding="utf-8"))
        ko_picks = staged_payload.get("ko_picks", [])
        en_picks = staged_payload.get("en_picks", [])
        alert_stats = dispatch_verified_alerts(ko_picks, en_picks, cfg, data_dir, live_send=args.send_telegram)
        social_stats = publish_verified_social(ko_picks, cfg, data_dir, live_publish=args.publish_social)
        print("=== Post-Deploy Verified Broadcast Summary ===")
        print(f"Telegram sent (post-URL check) : KO={alert_stats['sent_ko']}, EN={alert_stats['sent_en']}")
        print(f"Threads posted (<=1/day cap)   : {social_stats['threads_published_ko']}")
        return 0

    # Build-phase imports (kept lazy so --dispatch-deployed runs with zero external dependencies like Pillow)
    from src.ali_api import refresh_official_offers
    from src.auto_discover import auto_grow_catalog
    from src.collector import collect_candidates
    from src.coupang_api import refresh_coupang_links
    from src.deal_sniper import harvest_community_benchmarks, load_live_offers, snipe_hot_deals
    from src.pin_generator import build_pinterest_and_rss_feeds
    from src.site_builder import build_site
    from src.verifier import verify_batch

    # Step 1: Collect live signals & stage existing + inbox candidates
    staged = collect_candidates(project_root, live_network=args.live_network)
    # 100% of fetched signals reach the sniper and the benchmark harvester (the 8-item preview is display-only).
    live_signals = select_live_signals(staged)

    # Step 1b: Optional automated catalog growth
    grow_stats = {"attempted": 0, "added": 0, "rejected": 0, "added_ids": []}
    if args.auto_grow > 0:
        grow_stats = auto_grow_catalog(project_root, cfg, max_new=args.auto_grow)
        if grow_stats["added"] > 0:
            staged = collect_candidates(project_root, prior_stage=staged)

    candidates = staged["candidates"]

    # Step 2: Gatekeeper verification (enforces zero static prices, cons presence, and verbatim Amazon disclosure)
    approved, audit_entries = verify_batch(candidates, cfg)
    rejected = [e for e in audit_entries if not e["passed"]]
    coupang_stats = refresh_coupang_links(approved, cfg)

    # Step 2b: Live offer cache. Tier 2 (official AliExpress API, only when app key/secret are configured) swaps in
    # s.click promotion links; Tier 1 harvests floor-checked community deal benchmarks with a 48h expiry.
    api_stats = refresh_official_offers(approved, cfg, data_dir)
    benchmark_stats = harvest_community_benchmarks(approved, live_signals, data_dir, cfg=cfg)
    live_offers = load_live_offers(data_dir)

    # Step 3: Build static site (/ko/, /en/, tools, KO+EN guides, VS battles, category & product pages)
    site_stats = build_site(approved, cfg, dist_dir, live_offers=live_offers)

    # Step 4: Build price-free 1000x1500 Pinterest cards & 1:1 URL RSS 2.0 feeds
    pin_stats = build_pinterest_and_rss_feeds(approved, cfg, dist_dir, max_pins=52)

    # Step 5: Snipe verified promo/signal events & stage previews (only dispatch if explicitly invoked AFTER deploy)
    sniper_res = snipe_hot_deals(approved, live_signals, data_dir, cfg=cfg, max_picks=2)
    alert_stats = stage_alerts_preview(sniper_res, cfg, dist_dir)
    social_stats = stage_social_queues(sniper_res, cfg, dist_dir)

    pending_path.write_text(
        json.dumps(
            {
                "staged_at": datetime.now(timezone.utc).isoformat(),
                "ko_picks": sniper_res["ko_picks"],
                "en_picks": sniper_res["en_picks"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if args.send_telegram or args.publish_social:
        alert_stats = dispatch_verified_alerts(
            sniper_res["ko_picks"], sniper_res["en_picks"], cfg, data_dir, live_send=args.send_telegram
        )
        pub_res = publish_verified_social(sniper_res["ko_picks"], cfg, data_dir, live_publish=args.publish_social)
        social_stats.update(pub_res)

    audit_report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(candidates),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "auto_grow_stats": grow_stats,
        "new_leads_queued": staged.get("new_model_leads_found", 0),
        "live_signals_processed": len(live_signals),
        "rejected_details": rejected,
        "site_stats": site_stats,
        "pinterest_rss_stats": pin_stats,
        "live_offer_stats": {"community_benchmark": benchmark_stats, "ali_official_api": api_stats},
        "coupang_deeplink_stats": coupang_stats,
        "sniper_social_stats": social_stats,
        "alert_stats": alert_stats,
    }
    (data_dir / "audit_log.json").write_text(
        json.dumps(audit_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== GearCompare Hub Unified Consensus Pipeline Summary ===")
    print(f"Candidates scanned   : {len(candidates)} (new leads queued: {staged.get('new_model_leads_found', 0)})")
    print(f"Approved products    : {len(approved)} | Blocked by Gatekeeper: {len(rejected)}")
    print(f"Coupang deeplinks    : {coupang_stats['links_swapped']} generated")
    print(
        f"Static pages built   : {site_stats['total_html_pages']} "
        f"(incl. {site_stats['tools_rendered']} tool pages, {site_stats['guides_rendered']} guide pages, "
        f"{site_stats['vs_rendered']} VS pages)"
    )
    print(
        f"Pinterest & RSS      : {pin_stats['pin_cards_rendered']} price-free 1:1 PNG pins + "
        f"{pin_stats['ko_rss_items']} KO feed items"
    )
    print(
        f"Live signals         : {len(live_signals)} processed | community benchmarks active on "
        f"{benchmark_stats['active_products']} models (floor-blocked: {benchmark_stats['blocked_floor']}) | "
        f"Ali API: {'on' if api_stats['enabled'] else 'off'}"
    )
    print(
        f"Sniper live matches  : {sniper_res['live_signal_matches']} "
        f"(KO queued={alert_stats['queued_ko']}, EN queued={alert_stats['queued_en']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
