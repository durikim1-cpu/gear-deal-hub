"""End-to-end zero-cost affiliate automation runner:
 Phase 1 (Build): Collect -> Auto-Grow -> Gatekeeper Verify -> Static Site + Dock Checker + 12 Guides -> Pinterest PNG/RSS -> Stage Broadcast Queue.
 Phase 2 (Post-Deploy Dispatch): Verify live GitHub Pages URL (HTTP 200 + content) -> Idempotent Telegram & Threads<=1/day dispatch.
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
from src.notifier import dispatch_verified_alerts, stage_alerts_preview
from src.pin_generator import build_pinterest_and_rss_feeds
from src.site_builder import build_site
from src.social_publisher import publish_verified_social, stage_social_queues
from src.verifier import verify_batch


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
        help="Run ONLY post-deploy public-URL verification & idempotent notification dispatch from pending_broadcast.json.",
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

    # Step 2: Gatekeeper verification (enforces zero static prices, cons presence, and verbatim Amazon disclosure)
    approved, audit_entries = verify_batch(candidates, cfg)
    rejected = [e for e in audit_entries if not e["passed"]]

    # Step 3: Build static site (/ko/, /en/, MacBook Dock Checker, 12 Buying Guides, category & product pages)
    site_stats = build_site(approved, cfg, dist_dir)

    # Step 4: Build price-free 1000x1500 Pinterest cards & 1:1 URL RSS 2.0 feeds
    pin_stats = build_pinterest_and_rss_feeds(approved, cfg, dist_dir, max_pins=24)

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

    print("=== GearCompare Hub Unified Consensus Pipeline Summary ===")
    print(f"Candidates scanned   : {len(candidates)} (new leads queued: {staged.get('new_model_leads_found', 0)})")
    print(f"Approved products    : {len(approved)} | Blocked by Gatekeeper: {len(rejected)}")
    print(
        f"Static pages built   : {site_stats['total_html_pages']} "
        f"(incl. {site_stats['tools_rendered']} Dock Checkers + {site_stats['guides_rendered']} EN Buying Guides)"
    )
    print(f"Pinterest & RSS      : {pin_stats['pin_cards_rendered']} price-free 1:1 PNG pins + feeds")
    print(
        f"Sniper live matches  : {sniper_res['live_signal_matches']} "
        f"(KO queued={alert_stats['queued_ko']}, EN queued={alert_stats['queued_en']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
