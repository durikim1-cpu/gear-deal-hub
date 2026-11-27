"""Pinterest 1000x1500 problem/setup infographic generator & RSS 2.0 Media Feed builder.

Implements Topic 2 & Topic 3 Consensus:
- ZERO static Amazon/AliExpress dollar prices or % discount badges on PNG cards or in RSS descriptions.
- Replaces AliExpress-discount sorting with problem/setup Buying Guides + MacBook Dock Checker + Amazon-rationale gear.
- Strict 1:1 unique URL mapping per pin (zero duplicate URL spam) with transparent Hub landing + #affiliate & Amazon disclosure.
"""

from __future__ import annotations

import html
import re
import textwrap
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.affiliate import DISCLOSURE_EN, DISCLOSURE_KO
from src.site_builder import CATEGORY_LABELS_EN, product_slug
from src.tools_and_guides import GUIDES_EN

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
    cleaned = re.sub(r"[가-힣]+", "", str(text))
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ·-/,")
    return cleaned


def _render_card_canvas(
    *,
    badge_left: str,
    badge_right: str,
    headline: str,
    subtitle: str,
    chips: list[str],
    left_box_title: str,
    left_box_lines: list[str],
    right_box_title: str,
    right_box_lines: list[str],
    banner_text: str,
    caveat_title: str,
    caveat_body: str,
    footer_note: str,
    domain_label: str,
    out_path: Path,
) -> None:
    """Render a crisp 1000x1500 (2:3 vertical) price-free decision infographic PNG."""
    W, H = 1000, 1500
    img = Image.new("RGB", (W, H), "#F4F6F8")
    draw = ImageDraw.Draw(img)

    f_tag = _load_font(FONT_CANDIDATES_BOLD, 22)
    f_h1 = _load_font(FONT_CANDIDATES_BOLD, 44)
    f_sub = _load_font(FONT_CANDIDATES_REG, 26)
    f_chip = _load_font(FONT_CANDIDATES_BOLD, 22)
    f_store = _load_font(FONT_CANDIDATES_BOLD, 25)
    f_box_body = _load_font(FONT_CANDIDATES_REG, 24)
    f_banner = _load_font(FONT_CANDIDATES_BOLD, 26)
    f_con_h = _load_font(FONT_CANDIDATES_BOLD, 24)
    f_con = _load_font(FONT_CANDIDATES_REG, 26)
    f_cta = _load_font(FONT_CANDIDATES_BOLD, 22)
    f_disc = _load_font(FONT_CANDIDATES_REG, 18)

    draw.rounded_rectangle((44, 44, W - 44, H - 44), radius=32, fill="#FFFFFF", outline="#E2E6EC", width=3)

    draw.rounded_rectangle((88, 88, 560, 140), radius=12, fill="#EEF1F5")
    draw.text((110, 100), _ascii_clean(badge_left)[:34].upper(), fill="#374151", font=f_tag)
    draw.text((W - 340, 100), _ascii_clean(badge_right)[:24].upper(), fill="#0F766E", font=f_tag)

    y = 172
    for line in textwrap.wrap(_ascii_clean(headline), width=31)[:3]:
        draw.text((88, y), line, fill="#111827", font=f_h1)
        y += 56

    y += 12
    for line in textwrap.wrap(_ascii_clean(subtitle), width=54)[:3]:
        draw.text((88, y), line, fill="#4B5563", font=f_sub)
        y += 35

    y += 16
    cx = 88
    for sp in chips[:3]:
        label = _ascii_clean(sp)[:26]
        if len(label) < 3:
            continue
        bx0, _, bx1, _ = draw.textbbox((0, 0), label, font=f_chip)
        pill_w = (bx1 - bx0) + 34
        if cx + pill_w > W - 88:
            break
        draw.rounded_rectangle((cx, y, cx + pill_w, y + 44), radius=10, fill="#F8FAFC", outline="#D5DBE3", width=2)
        draw.text((cx + 17, y + 9), label, fill="#1F2937", font=f_chip)
        cx += pill_w + 12

    box_top, box_bot = 545, 805
    # Left option box (Amazon US / Native)
    draw.rounded_rectangle((88, box_top, 484, box_bot), radius=22, fill="#F3FAF8", outline="#0F766E", width=3)
    draw.rectangle((116, box_top + 30, 132, box_top + 46), fill="#FFA41C")
    draw.text((146, box_top + 24), left_box_title[:22], fill="#111827", font=f_store)
    ly = box_top + 74
    for b_line in left_box_lines[:4]:
        for wrapped in textwrap.wrap(_ascii_clean(b_line), width=26)[:2]:
            if ly < box_bot - 28:
                draw.text((116, ly), wrapped, fill="#1F2937", font=f_box_body)
                ly += 33

    # Right option box (Direct Import / Alternative)
    draw.rounded_rectangle((516, box_top, W - 88, box_bot), radius=22, fill="#F9FAFB", outline="#E2E6EC", width=3)
    draw.rectangle((544, box_top + 30, 560, box_top + 46), fill="#C93A16")
    draw.text((574, box_top + 24), right_box_title[:22], fill="#111827", font=f_store)
    ry = box_top + 74
    for b_line in right_box_lines[:4]:
        for wrapped in textwrap.wrap(_ascii_clean(b_line), width=26)[:2]:
            if ry < box_bot - 28:
                draw.text((544, ry), wrapped, fill="#374151", font=f_box_body)
                ry += 33

    ban_top = 830
    draw.rounded_rectangle((88, ban_top, W - 88, ban_top + 76), radius=16, fill="#ECEEFB")
    ban_clean = _ascii_clean(banner_text)[:48]
    bx0, _, bx1, _ = draw.textbbox((0, 0), ban_clean, font=f_banner)
    draw.text(((W - (bx1 - bx0)) // 2, ban_top + 22), ban_clean, fill="#3443B8", font=f_banner)

    con_top = 936
    draw.rounded_rectangle((88, con_top, W - 88, 1200), radius=18, fill="#FDF6EA", outline="#F2DEC0", width=2)
    draw.text((118, con_top + 22), _ascii_clean(caveat_title)[:40], fill="#8A4B08", font=f_con_h)
    cy = con_top + 66
    for line in textwrap.wrap(_ascii_clean(caveat_body), width=52)[:4]:
        draw.text((118, cy), line, fill="#374151", font=f_con)
        cy += 37

    vy = 1224
    for line in textwrap.wrap(_ascii_clean(footer_note), width=56)[:2]:
        draw.text((88, vy), line, fill="#1F2937", font=f_sub)
        vy += 35

    cta_txt = f"Compatibility Guide & Store Check  ->  {domain_label}"
    cx0, _, cx1, _ = draw.textbbox((0, 0), cta_txt, font=f_cta)
    draw.rounded_rectangle((88, 1322, W - 88, 1398), radius=16, fill="#111827")
    draw.text(((W - (cx1 - cx0)) // 2, 1346), cta_txt, fill="#FFFFFF", font=f_cta)

    draw.text(
        (88, 1414),
        "#affiliate | As an Amazon Associate I earn from qualifying purchases.",
        fill="#6B7280",
        font=f_disc,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)


def render_pin_card(item: dict, out_path: Path, domain_label: str) -> None:
    """Render a price-free problem/compatibility Pinterest PNG card for a standalone product."""
    cat_name = CATEGORY_LABELS_EN.get(item["category"], item["category"])
    specs_clean = [_ascii_clean(v) for v in item.get("specs", {}).values() if len(_ascii_clean(v)) >= 3]
    _render_card_canvas(
        badge_left=f"{cat_name} · {item['brand']}",
        badge_right="BUYING CHECKLIST",
        headline=item["en"]["title"],
        subtitle=item["en"]["summary"],
        chips=specs_clean[:3],
        left_box_title="AMAZON US CHECK",
        left_box_lines=[
            "• Verify Ships from US",
            "• Easy fit/spec return",
            "• Check US plug variant",
        ],
        right_box_title="DIRECT IMPORT CHECK",
        right_box_lines=[
            "• 7-14d transit lead time",
            "• Check import fees at",
            "  checkout (post de minimis)",
        ],
        banner_text="COMPARE LIVE CHECKOUT TOTALS & SPECS",
        caveat_title="REAL-WORLD CAVEAT BEFORE BUYING",
        caveat_body=item["en"]["cons"][0],
        footer_note=item["en"]["verdict"],
        domain_label=domain_label,
        out_path=out_path,
    )


def _esc(val: object) -> str:
    return html.escape(str(val))


def build_pinterest_and_rss_feeds(approved_items: list[dict], cfg: dict, dist_dir: Path, max_pins: int = 24) -> dict:
    """Render 1000x1500 price-free PNG cards and generate 1:1 URL Pinterest RSS + Korean RSS."""
    base_url = cfg["site"]["base_url"].rstrip("/")
    domain_label = re.sub(r"^https?://", "", base_url)
    pins_dir = dist_dir / "pins"
    pins_dir.mkdir(parents=True, exist_ok=True)

    now_rfc822 = format_datetime(datetime.now(timezone.utc))
    en_rss_items: list[str] = []

    # 1. Pin #1: Interactive MacBook Dual-Monitor Dock Compatibility Checker
    tool_png = pins_dir / "tool-macbook-dock-checker.png"
    _render_card_canvas(
        badge_left="MACBOOK SETUP TOOL",
        badge_right="COMPATIBILITY FIX",
        headline="M1 / M2 / M3 / M4 MacBook Dual Monitor Dock Checker",
        subtitle="Avoid dual-HDMI MST hubs that mirror screens on macOS. Match your exact Mac chip & lid mode.",
        chips=["Base M1/M2: DisplayLink", "M3 Closed: Native TB4", "M4 & Pro/Max: Native TB4"],
        left_box_title="NATIVE TB4 DOCKS",
        left_box_lines=["• Zero software drivers", "• Full Netflix HDCP", "• M3 Clamshell / M4 / Pro"],
        right_box_title="DISPLAYLINK DOCKS",
        right_box_lines=["• Unlocks Dual 4K@60Hz", "  on Base M1/M2 Macs", "• Note HDCP DRM caveat"],
        banner_text="STOP BUYING WINDOWS-ONLY MST SPLITTERS",
        caveat_title="WHY GENERIC DUAL-HDMI HUBS FAIL ON MAC",
        caveat_body="macOS blocks DisplayPort MST multi-monitor splitting—both HDMI ports show the exact same mirrored screen unless matched to DisplayLink or native TB4.",
        footer_note="Select your MacBook chip, lid state & streaming needs on the interactive checker.",
        domain_label=domain_label,
        out_path=tool_png,
    )
    tool_url = f"{base_url}/en/tools/macbook-dock-checker/?utm_source=pinterest"
    tool_img_url = f"{base_url}/pins/{tool_png.name}"
    en_rss_items.append(
        f"""    <item>
      <title>{_esc("MacBook Dual-Monitor Dock Compatibility Checker (M1 / M2 / M3 / M4 Fix)")}</title>
      <link>{_esc(tool_url)}</link>
      <guid isPermaLink="true">{_esc(tool_url)}</guid>
      <pubDate>{now_rfc822}</pubDate>
      <description>{_esc(f"Avoid dual-HDMI MST hubs that mirror screens on macOS. Check whether your MacBook chip needs DisplayLink or Clamshell Thunderbolt 4. #affiliate {DISCLOSURE_EN}")}</description>
      <enclosure url="{_esc(tool_img_url)}" length="{tool_png.stat().st_size}" type="image/png"/>
      <media:content url="{_esc(tool_img_url)}" medium="image" type="image/png" width="1000" height="1500"/>
    </item>"""
    )

    # 2. Pins #2–#13: All 12 Non-Template Setup & Compatibility Guides (1:1 unique URLs)
    for g in GUIDES_EN:
        g_png = pins_dir / f"guide-{g['slug']}.png"
        _render_card_canvas(
            badge_left=g["pillar"],
            badge_right="BUYING GUIDE",
            headline=g["title"],
            subtitle=g["summary"],
            chips=g["matrix_headers"][:3],
            left_box_title="WHAT WE TEST FOR",
            left_box_lines=["• Protocol & OS limits", "• Thermal & port drops", "• Seller/warranty risks"],
            right_box_title="WHO SHOULD SKIP",
            right_box_lines=["• Explicit exclusion list", "• Avoid wrong-port traps", "• Live US vs Direct check"],
            banner_text=g["pin_headline"],
            caveat_title="KEY EXCLUSION BEFORE YOU BUY",
            caveat_body=g["exclusions"][0],
            footer_note="Read the full compatibility matrix and vetted hardware options on our hub.",
            domain_label=domain_label,
            out_path=g_png,
        )
        g_url = f"{base_url}/en/guides/{g['slug']}/?utm_source=pinterest"
        g_img_url = f"{base_url}/pins/{g_png.name}"
        g_desc = f"{g['summary']} Caveat: {g['exclusions'][0]} #affiliate {DISCLOSURE_EN}"
        en_rss_items.append(
            f"""    <item>
      <title>{_esc(g['title'])}</title>
      <link>{_esc(g_url)}</link>
      <guid isPermaLink="true">{_esc(g_url)}</guid>
      <pubDate>{now_rfc822}</pubDate>
      <description>{_esc(g_desc)}</description>
      <enclosure url="{_esc(g_img_url)}" length="{g_png.stat().st_size}" type="image/png"/>
      <media:content url="{_esc(g_img_url)}" medium="image" type="image/png" width="1000" height="1500"/>
    </item>"""
        )

    # 3. Remaining slots: Vetted standalone hardware ranked by Amazon US buying rationale (NOT AliExpress discount!)
    remaining = max(0, max_pins - len(en_rss_items))
    ranked_en = sorted(
        approved_items,
        key=lambda x: (x["metrics"]["amazon_priority_score"], x["category"] in {"hubs", "chargers", "controllers", "storage"}),
        reverse=True,
    )[:remaining]

    for item in ranked_en:
        slug = product_slug(item["id"])
        png_path = pins_dir / f"{slug}.png"
        render_pin_card(item, png_path, domain_label)
        file_bytes = png_path.stat().st_size

        page_url = f"{base_url}/en/p/{slug}/?utm_source=pinterest"
        img_url = f"{base_url}/pins/{slug}.png"
        pin_title = f"{item['en']['title']} — Compatibility & Real-World Caveats"
        pin_desc = (
            f"{item['en']['summary']} Caveat before buying: {item['en']['cons'][0]} "
            f"#affiliate {DISCLOSURE_EN}"
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
    <title>{_esc(cfg['site']['brand_name'])} — Desk &amp; MacBook Setup Compatibility Guides</title>
    <link>{_esc(base_url)}/en/</link>
    <description>Hardware compatibility guides, MacBook dock rules, and real-world caveats. #affiliate As an Amazon Associate I earn from qualifying purchases.</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="{_esc(base_url)}/en/pinterest-feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(en_rss_items)}
  </channel>
</rss>
"""
    (dist_dir / "en" / "pinterest-feed.xml").write_text(pinterest_xml, encoding="utf-8")

    # Korean RSS feed (/ko/feed.xml) — zero static store prices
    ko_rss_items: list[str] = [
        f"""    <item>
      <title>{_esc("맥북 모델·칩별 듀얼모니터 독 호환 판별기 (M1·M2·M3·M4)")}</title>
      <link>{_esc(f"{base_url}/ko/tools/macbook-dock-checker/?utm_source=rss")}</link>
      <guid isPermaLink="true">{_esc(f"{base_url}/ko/tools/macbook-dock-checker/?utm_source=rss")}</guid>
      <pubDate>{now_rfc822}</pubDate>
      <description>{_esc(f"맥북 에어·프로 모델별 DisplayLink 필수 여부 및 클램쉘 네이티브 듀얼 호환 판별 도구 | {DISCLOSURE_KO}")}</description>
    </item>"""
    ]
    for item in approved_items[:20]:
        slug = product_slug(item["id"])
        page_url = f"{base_url}/ko/p/{slug}/?utm_source=rss"
        ko_title = f"{item['ko']['title']} — 실사용 단점·통관 기준 체크"
        ko_desc = f"{item['ko']['summary']} 단점 체크: {item['ko']['cons'][0]} | {DISCLOSURE_KO}"
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
    <title>{_esc(cfg['site']['brand_name'])} KR — 데스크·USB-C 기어 호환성·단점 검수 피드</title>
    <link>{_esc(base_url)}/ko/</link>
    <description>동일 모델 국내 배송 vs 해외직구 단점 체크 및 통관 기준 안내 피드</description>
    <language>ko</language>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
    <atom:link href="{_esc(base_url)}/ko/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(ko_rss_items)}
  </channel>
</rss>
"""
    (dist_dir / "ko" / "feed.xml").write_text(ko_xml, encoding="utf-8")

    return {
        "pin_cards_rendered": len(en_rss_items),
        "pinterest_feed": f"{base_url}/en/pinterest-feed.xml",
        "ko_rss_feed": f"{base_url}/ko/feed.xml",
    }
