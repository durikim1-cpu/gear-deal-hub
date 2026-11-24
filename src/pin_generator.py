"""Pinterest 1000x1500 visual price-comparison card generator & RSS 2.0 Media Feed builder (Strategy B)."""

from __future__ import annotations

import html
import re
import textwrap
from email.utils import format_datetime
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.affiliate import DISCLOSURE_EN, DISCLOSURE_KO
from src.site_builder import CATEGORY_LABELS_EN, product_slug

FONT_CANDIDATES_BOLD = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_CANDIDATES_REG = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _ascii_clean(text: str) -> str:
    """Ensure clean English/ASCII rendering on cross-platform fonts without missing-glyph boxes."""
    cleaned = re.sub(r"[가-힣]+", "", str(text))
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ·-/,")
    return cleaned


def render_pin_card(item: dict, out_path: Path, domain_label: str) -> None:
    """Render a crisp 1000x1500 (2:3 vertical) Pinterest comparison infographic PNG."""
    W, H = 1000, 1500
    img = Image.new("RGB", (W, H), "#F4F6F8")
    draw = ImageDraw.Draw(img)

    f_tag = _load_font(FONT_CANDIDATES_BOLD, 24)
    f_h1 = _load_font(FONT_CANDIDATES_BOLD, 46)
    f_sub = _load_font(FONT_CANDIDATES_REG, 27)
    f_chip = _load_font(FONT_CANDIDATES_BOLD, 23)
    f_store = _load_font(FONT_CANDIDATES_BOLD, 26)
    f_price = _load_font(FONT_CANDIDATES_BOLD, 62)
    f_meta = _load_font(FONT_CANDIDATES_REG, 23)
    f_banner = _load_font(FONT_CANDIDATES_BOLD, 29)
    f_con_h = _load_font(FONT_CANDIDATES_BOLD, 25)
    f_con = _load_font(FONT_CANDIDATES_REG, 27)
    f_cta = _load_font(FONT_CANDIDATES_BOLD, 22)
    f_disc = _load_font(FONT_CANDIDATES_REG, 19)

    # Outer elevated card
    draw.rounded_rectangle((44, 44, W - 44, H - 44), radius=32, fill="#FFFFFF", outline="#E2E6EC", width=3)

    # Top header pill & brand
    cat_name = CATEGORY_LABELS_EN.get(item["category"], item["category"]).upper()
    brand_tag = f"{cat_name}  ·  {item['brand'].upper()}"
    draw.rounded_rectangle((88, 88, 540, 140), radius=12, fill="#EEF1F5")
    draw.text((110, 99), brand_tag[:34], fill="#374151", font=f_tag)
    draw.text((W - 330, 100), "PRICE COMPARISON", fill="#0F766E", font=f_tag)

    # Product English Title (wrapped up to 3 lines)
    en_title = item["en"]["title"]
    title_lines = textwrap.wrap(en_title, width=32)[:3]
    y = 172
    for line in title_lines:
        draw.text((88, y), line, fill="#111827", font=f_h1)
        y += 58

    # Summary (2 lines)
    y += 14
    for line in textwrap.wrap(item["en"]["summary"], width=54)[:3]:
        draw.text((88, y), line, fill="#4B5563", font=f_sub)
        y += 36

    # Spec pills (up to 3 clean ASCII specs, exact textbbox sizing)
    y += 18
    specs_clean = [_ascii_clean(v) for v in item.get("specs", {}).values()]
    specs_clean = [s for s in specs_clean if len(s) >= 3][:3]
    cx = 88
    for sp in specs_clean:
        label = sp[:26]
        bx0, by0, bx1, by1 = draw.textbbox((0, 0), label, font=f_chip)
        pill_w = (bx1 - bx0) + 36
        if cx + pill_w > W - 88:
            break
        draw.rounded_rectangle((cx, y, cx + pill_w, y + 46), radius=10, fill="#F8FAFC", outline="#D5DBE3", width=2)
        draw.text((cx + 18, y + 9), label, fill="#1F2937", font=f_chip)
        cx += pill_w + 12

    # Side-by-side Price Comparison Boxes
    p = item["prices"]
    m = item["metrics"]
    amz_usd = float(p["amazon_usd"])
    ali_usd = float(p["ali_usd"])
    ali_cheaper = m["en_cheaper"] == "aliexpress" and m["en_savings_pct"] >= 15.0

    box_top = 540
    box_bot = 790
    # Left: Amazon US
    amz_bg = "#F3FAF8" if not ali_cheaper else "#F9FAFB"
    amz_border = "#0F766E" if not ali_cheaper else "#E2E6EC"
    draw.rounded_rectangle((88, box_top, 484, box_bot), radius=22, fill=amz_bg, outline=amz_border, width=3)
    draw.rectangle((116, box_top + 32, 132, box_top + 48), fill="#FFA41C")
    draw.text((146, box_top + 25), "AMAZON US", fill="#111827", font=f_store)
    draw.text((116, box_top + 82), f"${amz_usd:,.2f}", fill="#111827", font=f_price)
    draw.text((116, box_top + 172), "Fast Prime · Easy 30d Return", fill="#5B6472", font=f_meta)

    # Right: AliExpress Direct
    ali_bg = "#F3FAF8" if ali_cheaper else "#F9FAFB"
    ali_border = "#0F766E" if ali_cheaper else "#E2E6EC"
    draw.rounded_rectangle((516, box_top, W - 88, box_bot), radius=22, fill=ali_bg, outline=ali_border, width=3)
    draw.rectangle((544, box_top + 32, 560, box_top + 48), fill="#C93A16")
    draw.text((574, box_top + 25), "ALIEXPRESS DIRECT", fill="#111827", font=f_store)
    draw.text((544, box_top + 82), f"${ali_usd:,.2f}", fill="#0B5A54" if ali_cheaper else "#111827", font=f_price)
    draw.text((544, box_top + 172), "Factory Direct · 7-12d Ship", fill="#5B6472", font=f_meta)

    # Winner Verdict Banner
    ban_top = 820
    if ali_cheaper:
        ban_fill, ban_ink = "#E3F3F0", "#0B5A54"
        ban_txt = f"DIRECT PICK: SAVE ${m['en_diff_usd']:,.2f} ({m['en_savings_pct']:.0f}% OFF VS AMAZON)"
    else:
        ban_fill, ban_ink = "#ECEEFB", "#3443B8"
        ban_txt = "AMAZON PICK: OFFICIAL WARRANTY & FAST PRIME"
    draw.rounded_rectangle((88, ban_top, W - 88, ban_top + 82), radius=16, fill=ban_fill)
    bx0, _, bx1, _ = draw.textbbox((0, 0), ban_txt, font=f_banner)
    draw.text(((W - (bx1 - bx0)) // 2, ban_top + 24), ban_txt, fill=ban_ink, font=f_banner)

    # Honest Real-World Caveat Box
    con_top = 936
    draw.rounded_rectangle((88, con_top, W - 88, 1206), radius=18, fill="#FDF6EA", outline="#F2DEC0", width=2)
    draw.text((118, con_top + 24), "REAL-WORLD CAVEAT BEFORE BUYING", fill="#8A4B08", font=f_con_h)
    cy = con_top + 68
    con_text = item["en"]["cons"][0]
    for line in textwrap.wrap(con_text, width=52)[:3]:
        draw.text((118, cy), line, fill="#374151", font=f_con)
        cy += 38

    # Verdict line
    vy = 1232
    for line in textwrap.wrap("Verdict: " + item["en"]["verdict"], width=56)[:2]:
        draw.text((88, vy), line, fill="#1F2937", font=f_sub)
        vy += 36

    # Bottom Dark CTA Footer (centered exact fit)
    cta_txt = f"Full Specs & Live Links  ->  {domain_label}"
    cx0, _, cx1, _ = draw.textbbox((0, 0), cta_txt, font=f_cta)
    draw.rounded_rectangle((88, 1326, W - 88, 1404), radius=16, fill="#111827")
    draw.text(((W - (cx1 - cx0)) // 2, 1351), cta_txt, fill="#FFFFFF", font=f_cta)

    draw.text(
        (88, 1418),
        "Ad / Affiliate Disclosure: We may earn commissions from Amazon & AliExpress links.",
        fill="#6B7280",
        font=f_disc,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)


def _esc(val: object) -> str:
    return html.escape(str(val))


def build_pinterest_and_rss_feeds(approved_items: list[dict], cfg: dict, dist_dir: Path, max_pins: int = 30) -> dict:
    """Render 1000x1500 PNG cards and generate Pinterest RSS 2.0 Media Feed + Korean RSS Feed."""
    base_url = cfg["site"]["base_url"].rstrip("/")
    domain_label = re.sub(r"^https?://", "", base_url)
    pins_dir = dist_dir / "pins"
    pins_dir.mkdir(parents=True, exist_ok=True)

    # Prioritize highest English spread + diverse categories for Pinterest discovery
    ranked_en = sorted(
        approved_items,
        key=lambda x: (x["metrics"]["en_savings_pct"], x["metrics"]["msrp_drop_en_pct"]),
        reverse=True,
    )[:max_pins]

    now_rfc822 = format_datetime(datetime.now(timezone.utc))
    en_rss_items: list[str] = []

    for item in ranked_en:
        slug = product_slug(item["id"])
        png_path = pins_dir / f"{slug}.png"
        render_pin_card(item, png_path, domain_label)
        file_bytes = png_path.stat().st_size

        page_url = f"{base_url}/en/p/{slug}/"
        img_url = f"{base_url}/pins/{slug}.png"
        p = item["prices"]
        m = item["metrics"]
        pin_title = f"{item['en']['title']} — Amazon (${p['amazon_usd']:.2f}) vs AliExpress (${p['ali_usd']:.2f})"
        pin_desc = (
            f"{item['en']['summary']} Compare Amazon Prime (${p['amazon_usd']:.2f}) vs "
            f"AliExpress Direct (${p['ali_usd']:.2f}, {m['en_savings_pct']:.0f}% gap). "
            f"Caveat: {item['en']['cons'][0]} | {DISCLOSURE_EN}"
        )
        en_rss_items.append(
            f"""    <item>
      <title>{_esc(pin_title)}</title>
      <link>{_esc(page_url)}</link>
      <guid isPermaLink="true">{_esc(page_url)}</guid>
      <pubDate>{now_rfc822}</pubDate>
      <description>{_esc(pin_desc)}</description>
      <enclosure url="{_esc(img_url)}" length="{file_bytes}" type="image/png"/>
      <media:content url="{_esc(img_url)}" medium="image" type="image/png" width="1000" height="1500"/>
    </item>"""
        )

    pinterest_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{_esc(cfg['site']['brand_name'])} — Desk &amp; USB-C Hardware Price Index</title>
    <link>{_esc(base_url)}/en/</link>
    <description>Side-by-side Amazon US vs AliExpress price comparisons and real-world caveats on vetted desk gear.</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="{_esc(base_url)}/en/pinterest-feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(en_rss_items)}
  </channel>
</rss>
"""
    (dist_dir / "en" / "pinterest-feed.xml").write_text(pinterest_xml, encoding="utf-8")

    # Korean RSS feed (/ko/feed.xml) for domestic RSS automation / IFTTT / channel readers
    ranked_ko = sorted(approved_items, key=lambda x: x["metrics"]["kr_diff_krw"], reverse=True)[:max_pins]
    ko_rss_items: list[str] = []
    for item in ranked_ko:
        slug = product_slug(item["id"])
        page_url = f"{base_url}/ko/p/{slug}/"
        p = item["prices"]
        m = item["metrics"]
        ko_title = f"{item['ko']['title']} (쿠팡 {int(p['coupang_krw']):,}원 vs 알리 {int(p['ali_krw']):,}원)"
        ko_desc = (
            f"{item['ko']['summary']} 가격차 {m['kr_diff_krw']:,}원 ({m['kr_savings_pct']:.0f}%). "
            f"단점 체크: {item['ko']['cons'][0]} | {DISCLOSURE_KO}"
        )
        ko_rss_items.append(
            f"""    <item>
      <title>{_esc(ko_title)}</title>
      <link>{_esc(page_url)}</link>
      <guid isPermaLink="true">{_esc(page_url)}</guid>
      <pubDate>{now_rfc822}</pubDate>
      <description>{_esc(ko_desc)}</description>
    </item>"""
        )

    ko_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{_esc(cfg['site']['brand_name'])} KR — PC·데스크 주변기기 국내가·직구가 시세</title>
    <link>{_esc(base_url)}/ko/</link>
    <description>쿠팡 정발 vs 알리익스프레스 직구 동일 모델 가격 비교 및 단점 요약 피드</description>
    <language>ko</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="{_esc(base_url)}/ko/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(ko_rss_items)}
  </channel>
</rss>
"""
    (dist_dir / "ko" / "feed.xml").write_text(ko_xml, encoding="utf-8")

    return {
        "pin_cards_rendered": len(ranked_en),
        "pinterest_feed": f"{base_url}/en/pinterest-feed.xml",
        "ko_rss_feed": f"{base_url}/ko/feed.xml",
    }
