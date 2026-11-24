"""End-to-end zero-cost affiliate automation runner:
Collect -> Auto-Grow -> Gatekeeper Verify -> Build Faceted Site -> Strategy B (Pinterest PNG + RSS) -> Strategy A (Deal Sniper + Telegram + Threads/X).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.affiliate import load_config
from src.auto_discover import auto_grow_catalog
from src.collector import collect_candidates
from src.deal_sniper import snipe_hot_deals
from src.notifier import dispatch_alerts
from src.pin_generator import build_pinterest_and_rss_feeds
from src.site_builder import build_site
from src.social_publisher import publish_social_feeds
from src.verifier import verify_batch


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GearCompare Hub unified A+B automation pipeline.")
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
        "--send-telegram",
        action="store_true",
        help="Actually dispatch deal alerts to Telegram if bot_token is configured.",
    )
    parser.add_argument(
        "--publish-social",
        action="store_true",
        help="Publish shadowban-safe 2-part post to Meta Threads if THREADS_ACCESS_TOKEN is configured.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    data_dir = project_root / "data"

    cfg = load_config(project_root)

    # Step 1: Collect live signals & stage existing + inbox candidates
    staged = collect_candidates(project_root, live_network=args.live_network)
    live_signals = staged.get("trend_signals_preview", [])

    # Step 1b: Optional automated catalog growth
    grow_stats = {"attempted": 0, "added": 0, "rejected": 0, "added_ids": []}
    if args.auto_grow > 0:
        grow_stats = auto_grow_catalog(project_root, cfg, max_new=args.auto_grow)
        if grow_stats["added"] > 0:
            staged = collect_candidates(project_root, live_network=False)

    candidates = staged["candidates"]

    # Step 2: Gatekeeper verification
    approved, audit_entries = verify_batch(candidates, cfg)
    rejected = [e for e in audit_entries if not e["passed"]]

    # Step 3: Build static multilingual faceted site (/ko/, /en/, /ko/c/*, /en/c/*, /ko/p/*, /en/p/*)
    site_stats = build_site(approved, cfg, dist_dir)

    # Step 4 (Strategy B): Build 1000x1500 Pinterest infographic PNGs & auto-publish RSS 2.0 feeds
    pin_stats = build_pinterest_and_rss_feeds(approved, cfg, dist_dir, max_pins=30)

    # Step 5 (Strategy A): Snipe urgent hot deals / promo codes -> Telegram + Threads/X queues
    live_broadcast = bool(args.send_telegram or args.publish_social)
    sniper_res = snipe_hot_deals(
        approved,
        live_signals,
        data_dir,
        max_picks=4,
        record_history=live_broadcast,
    )
    alert_stats = dispatch_alerts(sniper_res["ko_picks"] or approved, cfg, dist_dir, live_send=args.send_telegram)
    social_stats = publish_social_feeds(sniper_res, cfg, dist_dir, live_publish=args.publish_social)

    audit_report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(candidates),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "auto_grow_stats": grow_stats,
        "new_leads_queued": staged.get("new_model_leads_found", 0),
        "rejected_details": rejected,
        "site_stats": site_stats,
        "pinterest_rss_stats": pin_stats,
        "sniper_social_stats": social_stats,
        "alert_stats": alert_stats,
    }
    (data_dir / "audit_log.json").write_text(
        json.dumps(audit_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== GearCompare Hub Unified (A + B) Pipeline Summary ===")
    print(f"Candidates scanned   : {len(candidates)} (new leads queued: {staged.get('new_model_leads_found', 0)})")
    print(f"Approved products    : {len(approved)} | Blocked by Gatekeeper: {len(rejected)}")
    print(f"Static pages built   : {site_stats['total_html_pages']} -> {dist_dir}")
    print(f"[B] Pinterest & RSS  : {pin_stats['pin_cards_rendered']} PNG cards (1000x1500) + pinterest-feed.xml + ko/feed.xml")
    print(
        f"[A] Sniper & Social  : Threads/X queued KO={social_stats['ko_queued']}, EN={social_stats['en_queued']} "
        f"(Threads live posted={social_stats['threads_published_ko']})"
    )
    print(
        f"[A] Telegram alerts  : KO={alert_stats['queued_ko']} queued ({alert_stats['sent_ko']} sent), "
        f"EN={alert_stats['queued_en']} queued ({alert_stats['sent_en']} sent)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
