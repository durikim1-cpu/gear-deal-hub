"""Pillar 5: Naver-compliant KO feed, 52 evergreen 1:1 pins, Telegram previews, IndexNow full sitemap."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from email.utils import parsedate_to_datetime

from conftest import ROOT, read
from src.pin_generator import ko_feed_entries, pin_plan, vs_pin_copy
from src.tools_and_guides import GUIDES_EN, GUIDES_KO
from src.vs_pairs import VS_PAIRS

HANGUL = re.compile(r"[ᄀ-ᇿ㄰-㆏가-힯]")
PRICE_OR_DISCOUNT = re.compile(r"[$₩€]\s?\d|\d[\d,]*\s?원|\d+\s?%\s*(?:off|discount|할인)|save\s+\d+\s?%", re.I)


# ------------------------------------------------------------------ Korean feed (Naver Search Advisor format)
def test_ko_feed_keeps_naver_search_advisor_format(built):
    raw = read(built["dist"] / "ko" / "feed.xml")
    assert "xmlns:atom" not in raw and "<atom:" not in raw
    assert "utm_source" not in raw and "?" not in "".join(re.findall(r"<(?:link|guid)[^>]*>([^<]*)<", raw))
    root = ET.fromstring(raw.encode("utf-8"))
    assert root.tag == "rss" and root.attrib == {"version": "2.0"}
    channel = root.find("channel")
    assert channel.findtext("link") == "https://durikim1-cpu.github.io/"
    assert channel.findtext("language") == "ko"

    items = channel.findall("item")
    assert 45 <= len(items) <= 50
    links = [i.findtext("link") for i in items]
    assert len(set(links)) == len(links)
    dates = []
    for item in items:
        link, guid = item.findtext("link"), item.find("guid")
        assert link.startswith(built["base"] + "/ko/") and link.endswith("/")
        assert guid.text == link and guid.attrib == {"isPermaLink": "true"}
        pub = item.findtext("pubDate")
        assert pub.endswith("+0900"), pub
        dates.append(parsedate_to_datetime(pub))
        assert "수수료" in item.findtext("description"), "Korean disclosure stays in every item description"
    assert len(set(dates)) == len(dates), "pubDates are staggered, never identical"
    assert all(a - b == timedelta(minutes=12) for a, b in zip(dates, dates[1:]))
    assert parsedate_to_datetime(channel.findtext("lastBuildDate")).utcoffset() == timedelta(hours=9)


def test_ko_feed_lineup(built, approved, cfg):
    entries = ko_feed_entries(approved, cfg)
    paths = [e["path"] for e in entries]
    assert paths[:2] == ["/ko/tools/macbook-dock-checker/", "/ko/tools/ali-promo-calculator/"]
    assert paths[2:14] == [f"/ko/guides/{g['slug']}/" for g in GUIDES_KO]
    assert paths[14:29] == [f"/ko/vs/{p['slug']}/" for p in VS_PAIRS]
    assert len(paths) == 2 + 12 + 15 + 20 == built["pins"]["ko_rss_items"]
    assert all((built["dist"] / p.strip("/") / "index.html").exists() for p in paths)


# ------------------------------------------------------------------ Pinterest: 52 unique 1:1 evergreen pins
def test_pin_plan_is_52_unique_one_to_one_urls(approved, cfg):
    plan = pin_plan(approved, cfg, max_pins=52)
    kinds = [e["kind"] for e in plan]
    assert (kinds.count("tool"), kinds.count("guide"), kinds.count("vs"), kinds.count("product")) == (2, 12, 15, 23)
    assert len(plan) == 52
    assert len({e["url"] for e in plan}) == 52 and len({e["png"] for e in plan}) == 52
    assert {e["png"] for e in plan if e["kind"] == "tool"} == {"tool-macbook-dock-checker.png", "tool-ali-promo-calculator.png"}
    assert {e["png"] for e in plan if e["kind"] == "guide"} == {f"guide-{g['slug']}.png" for g in GUIDES_EN}
    assert {e["png"] for e in plan if e["kind"] == "vs"} == {f"vs-{p['slug']}.png" for p in VS_PAIRS}
    assert all(e["path"].startswith("/en/") and e["url"].endswith("?utm_source=pinterest") for e in plan)
    assert len(pin_plan(approved, cfg, max_pins=24)) == 24


def test_pinterest_feed_and_png_cards(built):
    from PIL import Image

    dist, base = built["dist"], built["base"]
    assert built["pins"]["pin_cards_rendered"] == 52
    assert built["pins"]["pin_breakdown"] == {"tool": 2, "guide": 12, "vs": 15, "product": 23}
    root = ET.parse(dist / "en" / "pinterest-feed.xml").getroot()
    items = root.find("channel").findall("item")
    assert len(items) == 52
    links, images = [], []
    for item in items:
        link = item.findtext("link")
        enclosure = item.find("enclosure").attrib
        links.append(link)
        images.append(enclosure["url"])
        page = link.split("?")[0][len(base) + 1:]
        assert (dist / page / "index.html").exists(), f"pin lands on a missing page: {link}"
        png = dist / "pins" / enclosure["url"].rsplit("/", 1)[1]
        assert png.exists() and int(enclosure["length"]) == png.stat().st_size
        text = f"{item.findtext('title')} {item.findtext('description')}"
        assert "#affiliate" in text and "As an Amazon Associate I earn from qualifying purchases." in text
        assert not PRICE_OR_DISCOUNT.search(text), f"price or discount claim in pin copy: {text[:120]}"
        assert not HANGUL.search(text)
    assert len(set(links)) == 52 and len(set(images)) == 52, "one unique landing URL and one unique image per pin"
    assert len(list((dist / "pins").glob("*.png"))) == 52
    for name in ("tool-ali-promo-calculator.png", f"vs-{VS_PAIRS[0]['slug']}.png"):
        with Image.open(dist / "pins" / name) as im:
            assert im.size == (1000, 1500)


def test_vs_pin_copy_is_price_free_and_carries_the_vs_badge(approved):
    by_id = {it["id"]: it for it in approved}
    for pair in VS_PAIRS:
        copy = vs_pin_copy(pair, by_id)
        assert copy["badge_right"] == "HEAD-TO-HEAD VS"
        assert len(copy["left_box_title"]) <= 22 and len(copy["right_box_title"]) <= 22
        assert copy["left_box_lines"][0].startswith("+ ") and copy["left_box_lines"][1].startswith("! ")
        assert copy["right_box_lines"][0].startswith("+ ") and copy["right_box_lines"][1].startswith("! ")
        flat = " ".join(v if isinstance(v, str) else " ".join(v) for v in copy.values())
        assert not PRICE_OR_DISCOUNT.search(flat), flat
        assert not HANGUL.search(flat)


def test_every_text_drawn_on_a_pin_card_is_price_free(approved, cfg):
    by_id = {it["id"]: it for it in approved}
    drawn = []
    for entry in pin_plan(approved, cfg, max_pins=52):
        if entry["kind"] == "product":
            it = by_id[entry["key"]]
            drawn += [it["en"]["title"], it["en"]["summary"], it["en"]["cons"][0], it["en"]["verdict"]]
            drawn += [str(v) for v in (it.get("specs_en") or {}).values()]
        elif entry["kind"] == "guide":
            g = next(x for x in GUIDES_EN if x["slug"] == entry["key"])
            drawn += [g["title"], g["summary"], g["pin_headline"], g["exclusions"][0], *g["matrix_headers"]]
    assert drawn
    for text in drawn:
        assert not PRICE_OR_DISCOUNT.search(text), f"price or discount claim on a pin card: {text!r}"
    source = (ROOT / "src" / "pin_generator.py").read_text(encoding="utf-8")
    assert "max_pins: int = 52" in source and "max_pins=52" in (ROOT / "run_pipeline.py").read_text(encoding="utf-8")


# ------------------------------------------------------------------ Telegram
def test_telegram_previews_enabled_and_bodies_stay_disclosure_free(monkeypatch, approved):
    from src import notifier

    sent = {}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=10):
        sent.update(json.loads(req.data.decode("utf-8")))
        return _Resp()

    monkeypatch.setattr(notifier.urllib.request, "urlopen", fake_urlopen)
    item = dict(approved[0], sniper={"promo_code": "KRBF07", "observed_at": "2026-11-28 03:00 UTC", "live_matched": True})
    ko = notifier.format_ko_alert(item, "https://example.test/site")
    en = notifier.format_en_alert(item, "https://example.test/site")
    assert notifier._send_telegram_message("token", "@channel", ko)
    assert sent["disable_web_page_preview"] is False and sent["parse_mode"] == "HTML"
    for body in (ko, en):
        assert "[대가성 광고 안내]" not in body and "대가성" not in body
        assert "utm_source=telegram" in body
        assert not re.search(r"(coupang\.com|aliexpress\.com|amazon\.com)", body), "Telegram routes through the Hub only"
        assert not re.search(r"[$₩]\s?\d|\d[\d,]*\s?원", body), "no prices in Telegram text"
    assert "[대가성 광고 안내]" not in (ROOT / "src" / "notifier.py").read_text(encoding="utf-8").split('"""', 2)[2]


def test_product_pages_expose_og_image_cards_for_link_previews(built, approved):
    from src.site_builder import product_slug

    slug = product_slug(approved[0]["id"])
    page = read(built["dist"] / "ko" / "p" / slug / "index.html")
    assert f'<meta property="og:image" content="{built["base"]}/assets/og/{slug}.jpg">' in page
    assert '<meta property="og:image:width" content="1200">' in page and "summary_large_image" in page
    assert (built["dist"] / "assets" / "og" / f"{slug}.jpg").stat().st_size > 5000
    hub = read(built["dist"] / "ko" / "index.html")
    assert f'{built["base"]}/assets/og/site.jpg' in hub


# ------------------------------------------------------------------ IndexNow
def test_indexnow_submits_every_sitemap_url(built, cfg):
    import run_pipeline

    base = built["base"]
    urls = run_pipeline.collect_indexnow_urls(base, built["dist"])
    sitemap = run_pipeline.parse_sitemap_urls(read(built["dist"] / "sitemap.xml"))
    assert urls == sitemap and len(urls) >= 225
    for needle in ("/ko/tools/ali-promo-calculator/", "/ko/guides/", "/ko/vs/", "/en/vs/"):
        assert base + needle in urls

    posted = []
    statuses = run_pipeline.submit_indexnow(base, "abc123", urls, post=lambda payload: posted.append(payload) or 200)
    assert statuses == [200] and len(posted) == 1
    assert posted[0]["urlList"] == urls and len(urls) <= run_pipeline.INDEXNOW_MAX_URLS_PER_POST
    assert posted[0]["host"] == "durikim1-cpu.github.io"
    assert posted[0]["keyLocation"] == f"{base}/abc123.txt"


def test_indexnow_falls_back_to_the_deployed_sitemap_then_core_urls(tmp_path, built):
    import run_pipeline

    base = built["base"]
    live_xml = read(built["dist"] / "sitemap.xml")
    fetched = []

    def fetch(url):
        fetched.append(url)
        return live_xml

    # The post-deploy CI job has no dist/ checkout, so the live sitemap is used.
    urls = run_pipeline.collect_indexnow_urls(base, tmp_path / "missing-dist", fetch=fetch)
    assert fetched == [f"{base}/sitemap.xml"] and len(urls) >= 225

    def offline(url):
        raise OSError("offline")

    core = run_pipeline.collect_indexnow_urls(base, tmp_path / "missing-dist", fetch=offline)
    assert f"{base}/ko/tools/ali-promo-calculator/" in core and f"{base}/ko/vs/" in core
    foreign = "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>https://other.example/x/</loc></url></urlset>"
    assert run_pipeline.collect_indexnow_urls(base, tmp_path / "missing-dist", fetch=lambda u: foreign) == []
    assert run_pipeline.parse_sitemap_urls("<not xml") == []
