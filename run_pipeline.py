"""End-to-end zero-cost affiliate automation runner: Collect -> Gatekeeper Verify -> Build Site -> Notify."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src.affiliate import load_config
from src.collector import collect_candidates
from src.notifier import dispatch_alerts
from src.site_builder import build_site
from src.verifier import verify_batch


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GearCompare Hub automated pipeline.")
    parser.add_argument(
        "--live-network",
        action="store_true",
        help="Fetch live public Reddit trend JSON feeds during collection.",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Actually dispatch deal alerts to Telegram if bot_token is configured.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    data_dir = project_root / "data"

    cfg = load_config(project_root)

    # Step 1: Collect candidates
    staged = collect_candidates(project_root, live_network=args.live_network)
    candidates = staged["candidates"]

    # Step 2: Gatekeeper verification (blocks accessory traps & missing disclosures)
    approved, audit_entries = verify_batch(candidates, cfg)
    rejected = [e for e in audit_entries if not e["passed"]]

    # Step 3: Build static multilingual site (/ko for Coupang+Ali, /en for Amazon+Ali)
    site_stats = build_site(approved, cfg, dist_dir)

    # Step 4: Format & optionally send Telegram alerts
    alert_stats = dispatch_alerts(approved, cfg, dist_dir, live_send=args.send_telegram)

    audit_report = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(candidates),
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "rejected_details": rejected,
        "site_stats": site_stats,
        "alert_stats": alert_stats,
    }
    (data_dir / "audit_log.json").write_text(
        json.dumps(audit_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== GearCompare Hub Pipeline Summary ===")
    print(f"Candidates scanned : {len(candidates)}")
    print(f"Approved products  : {len(approved)}")
    print(f"Blocked by Gatekeeper: {len(rejected)}")
    for r in rejected:
        print(f"  [BLOCKED] {r['product_id']} -> {', '.join(r['reasons'])}")
    print(f"Static pages built : {site_stats['total_html_pages']} -> {dist_dir}")
    print(
        f"Telegram alerts    : KO={alert_stats['queued_ko']} queued ({alert_stats['sent_ko']} sent), "
        f"EN={alert_stats['queued_en']} queued ({alert_stats['sent_en']} sent)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
