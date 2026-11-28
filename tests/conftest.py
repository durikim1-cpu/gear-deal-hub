"""Shared fixtures. Nothing here touches the real dist/ or data/ runtime files or the network."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# A fixed build clock inside the Nov 20 - Dec 3 mega-sale window on both reference clocks (KST and PT).
BUILD_NOW = datetime(2026, 11, 28, 3, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="session")
def cfg() -> dict:
    """The committed example config only (never config.local.json or environment secrets)."""
    return json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def catalog() -> list[dict]:
    return json.loads((ROOT / "data" / "products.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def inbox() -> list[dict]:
    return json.loads((ROOT / "data" / "candidates_inbox.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def approved(catalog, cfg) -> list[dict]:
    from src.verifier import verify_batch

    items, _audit = verify_batch(catalog, cfg)
    return items


@pytest.fixture(scope="session")
def built(tmp_path_factory, approved, cfg) -> dict:
    """One full static build (site + pins + feeds) into a temp directory, shared by the page-level tests."""
    pytest.importorskip("PIL", reason="Pillow is needed for the pin cards")
    from src.pin_generator import build_pinterest_and_rss_feeds
    from src.site_builder import build_site

    dist = tmp_path_factory.mktemp("dist")
    site_stats = build_site(approved, cfg, dist, live_offers=None, now=BUILD_NOW)
    pin_stats = build_pinterest_and_rss_feeds(approved, cfg, dist, max_pins=52)
    return {"dist": dist, "site": site_stats, "pins": pin_stats, "base": cfg["site"]["base_url"].rstrip("/")}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")
