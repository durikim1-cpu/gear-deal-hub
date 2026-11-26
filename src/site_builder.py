"""Zero-dependency static site generator for Korean (Coupang vs Ali) & Global (Amazon vs Ali) hubs.

URL map (directory-index URLs, never linked with `.html`):
  /                 -> dist/index.html             (region gateway)
  /ko/              -> dist/ko/index.html          (Coupang vs AliExpress faceted index)
  /en/              -> dist/en/index.html          (Amazon vs AliExpress faceted index)
  /ko/c/<cat>/      -> dist/ko/c/<cat>/index.html  (Korean category index)
  /en/c/<cat>/      -> dist/en/c/<cat>/index.html  (English category index)
  /ko/p/<slug>/     -> dist/ko/p/<slug>/index.html (Korean detail)
  /en/p/<slug>/     -> dist/en/p/<slug>/index.html (English detail)
  /policy/          -> dist/policy/index.html      (privacy & affiliate disclosure)
"""

from __future__ import annotations

import html
import json
import re
import shutil
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from src.affiliate import DISCLOSURE_EN, DISCLOSURE_KO

CATEGORY_LABELS_KO = {
    "all": "전체",
    "chargers": "충전기",
    "keyboards": "키보드",
    "powerbanks": "보조배터리",
    "minipc": "미니PC",
    "mice": "마우스",
    "audio": "오디오/마이크",
    "storage": "외장SSD",
    "lighting": "조명",
    "productivity": "생산성 기어",
    "hubs": "독/허브",
    "controllers": "컨트롤러/패드",
}

CATEGORY_LABELS_EN = {
    "all": "All Gear",
    "chargers": "GaN Chargers",
    "keyboards": "Keyboards",
    "powerbanks": "Power Banks",
    "minipc": "Mini PCs",
    "mice": "Mice",
    "audio": "Microphones",
    "storage": "Portable SSDs",
    "lighting": "Desk Lighting",
    "productivity": "Stream & Macros",
    "hubs": "USB-C Docks",
    "controllers": "Controllers",
}

SPEC_LABELS_KO = {
    "max_output": "최대 출력", "ports": "포트 구성", "weight": "무게", "size": "크기",
    "layout": "배열", "connectivity": "연결 방식", "battery": "배터리", "mount": "구조/마운트",
    "capacity": "용량", "input": "입력", "cpu": "CPU", "memory": "메모리", "storage": "저장장치",
    "firmware": "펌웨어", "os_support": "OS 지원", "sensor": "센서", "switches": "스위치",
    "scroll": "스크롤", "thickness": "두께", "capsule": "캡슐", "interface": "인터페이스",
    "controls": "컨트롤", "speed": "속도", "durability": "내구성", "cri": "연색성(CRI)",
    "control": "조작", "color_temp": "색온도", "power": "전원", "keys": "키", "stand": "스탠드",
    "os": "지원 OS", "ecosystem": "생태계", "video": "영상 출력", "pd_passthrough": "PD 충전",
    "network": "네트워크", "data_ports": "데이터 포트", "material": "소재",
}

_SPEC_ACRONYMS = {"cpu", "os", "cri", "pd", "usb", "led"}

# Korea duty-free threshold for most direct-import goods (USD).
KR_CUSTOMS_LIMIT_USD = 150
# Minimum AliExpress advantage before we recommend direct import over domestic delivery.
DIRECT_PICK_MIN_PCT = 15.0

# Index paging: rows revealed per "load more" step.
PAGE_SIZE = 20
# Brands listed in the facet before the "all brands" expander.
TOP_BRANDS = 8
# The top-spreads strip is skipped for scopes too small for it to say anything the list doesn't.
TOPS_MIN_ITEMS = 8
# Price facet brackets on the lowest available price: (upper bound, label). KO bounds are inclusive, EN exclusive.
_PRICE_BRACKETS = {
    "ko": ((50_000, "5만 원 이하"), (100_000, "5~10만 원"), (200_000, "10~20만 원"), (None, "20만 원 이상")),
    "en": ((40, "Under $40"), (80, "$40–$80"), (150, "$80–$150"), (None, "$150+")),
}
_SKU_RE = re.compile(r"^(?=.*\d)[A-Z0-9][A-Z0-9\-]{2,15}$")

FONT_CSS_URL = (
    "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/"
    "pretendardvariable-dynamic-subset.min.css"
)

# --------------------------------------------------------------------------------------
# Inline icons (one consistent 1.75 stroke set)
# --------------------------------------------------------------------------------------

_ICON_PATHS = {
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    "cards": '<rect x="3.5" y="4" width="7" height="16" rx="1.5"/><rect x="13.5" y="4" width="7" height="16" rx="1.5"/>',
    "list": '<path d="M4 6.5h16M4 12h16M4 17.5h16"/>',
    "filter": '<path d="M4 7h9M19 7h1M4 17h1M11 17h9"/><circle cx="16" cy="7" r="2.5"/><circle cx="8" cy="17" r="2.5"/>',
    "x": '<path d="m6 6 12 12M18 6 6 18"/>',
    "down": '<path d="m6 9 6 6 6-6"/>',
    "out": '<path d="M7 17 17 7M9 7h8v8"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "send": '<path d="M21 4 3 11l6.5 2.5L12 20l3-5.5L21 4Z"/><path d="m9.5 13.5 5-5"/>',
    "shield": '<path d="M12 3 5 6v5.5c0 4.2 2.9 7.6 7 9.5 4.1-1.9 7-5.3 7-9.5V6l-7-3Z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
    "chev": '<path d="m9 6 6 6-6 6"/>',
}


def _icon(name: str, size: int = 16) -> str:
    return (
        f'<svg class="i" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_ICON_PATHS[name]}</svg>'
    )


# Icons repeated in every index row are referenced from one per-page sprite to keep 500-row pages light.
_SPRITE_ICONS = ("out", "down", "arrow")
ICON_SPRITE = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
    + "".join(f'<symbol id="i-{n}" viewBox="0 0 24 24">{_ICON_PATHS[n]}</symbol>' for n in _SPRITE_ICONS)
    + "</svg>"
)


def _use(name: str, size: int = 14) -> str:
    return f'<svg class="i" width="{size}" height="{size}" aria-hidden="true"><use href="#i-{name}"/></svg>'


BRAND_MARK = (
    '<svg class="mark" width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">'
    '<rect width="26" height="26" rx="7" fill="#111827"/>'
    '<rect x="6" y="8.5" width="14" height="2.6" rx="1.3" fill="#fff"/>'
    '<rect x="6" y="14.9" width="8" height="2.6" rx="1.3" fill="#5EEAD4"/></svg>'
)

SHARED_CSS = """
:root {
  --canvas: #F6F7F9;
  --surface: #FFFFFF;
  --sunk: #F1F3F6;
  --ink: #111827;
  --ink-2: #374151;
  --muted: #5B6472;
  --line: #E4E7EC;
  --line-2: #D3D8DF;
  --save: #0F766E;
  --save-ink: #0B5A54;
  --save-bg: #E3F3F0;
  --local: #3443B8;
  --local-bg: #ECEEFB;
  --warn-ink: #8A4B08;
  --warn-bg: #FDF1DC;
  --coupang: #2D5BE3;
  --amazon: #FFA41C;
  --ali: #C93A16;
  --radius: 14px;
  --shadow: 0 1px 2px rgba(17, 24, 39, 0.04), 0 4px 14px -6px rgba(17, 24, 39, 0.08);
  --shadow-hi: 0 2px 4px rgba(17, 24, 39, 0.05), 0 14px 32px -12px rgba(17, 24, 39, 0.18);
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
  color-scheme: light;
}
*, *::before, *::after { box-sizing: border-box; }
* { margin: 0; padding: 0; }
[hidden] { display: none !important; }
html { -webkit-text-size-adjust: 100%; scroll-padding-top: 84px; }
body {
  font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  background: var(--canvas);
  color: var(--ink);
  font-size: 15.5px;
  line-height: 1.6;
  font-feature-settings: "ss06";
  -webkit-font-smoothing: antialiased;
  word-break: keep-all;
  overflow-wrap: break-word;
  accent-color: var(--ink);
  caret-color: var(--save);
}
::selection { background: #BFE6DF; color: #062F2B; }
a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: 3px; }
button, input { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--coupang); outline-offset: 2px; border-radius: 6px; }
.num, .price, .amt { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
.i { flex: none; vertical-align: -0.15em; fill: none; stroke: currentColor; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
.wrap { max-width: var(--wrap, 1200px); margin: 0 auto; padding: 0 22px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

/* ---------- Compliance strip ---------- */
.legal-strip { background: #ECEEF2; border-bottom: 1px solid var(--line); color: var(--ink-2); font-size: 12.5px; line-height: 1.5; }
.legal-strip .wrap { display: flex; gap: 10px; align-items: baseline; padding-top: 7px; padding-bottom: 7px; }
.legal-tag { flex: none; font-size: 11px; font-weight: 700; letter-spacing: 0.02em; color: var(--muted); border: 1px solid var(--line-2); border-radius: 4px; padding: 0 5px; background: var(--surface); }

/* ---------- Header ---------- */
.site-head { position: sticky; top: 0; z-index: 20; background: rgba(255, 255, 255, 0.92); backdrop-filter: saturate(1.4) blur(10px); -webkit-backdrop-filter: saturate(1.4) blur(10px); border-bottom: 1px solid var(--line); }
.site-head .wrap { display: flex; align-items: center; justify-content: space-between; gap: 16px; height: 62px; }
.brand { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; font-weight: 750; font-size: 17px; letter-spacing: -0.02em; white-space: nowrap; }
.brand-region { font-size: 11px; font-weight: 700; letter-spacing: 0.04em; color: var(--save-ink); background: var(--save-bg); border-radius: 5px; padding: 1px 6px; }
.head-nav { display: flex; align-items: center; gap: 4px; font-size: 14px; }
.head-nav a { display: inline-flex; align-items: center; gap: 6px; text-decoration: none; padding: 7px 11px; border-radius: 9px; color: var(--ink-2); font-weight: 550; white-space: nowrap; transition: background 0.2s var(--ease); }
.head-nav a:hover { background: var(--sunk); color: var(--ink); }
.head-nav a.tg { background: var(--ink); color: #fff; margin-left: 6px; }
.head-nav a.tg:hover { background: #1F2937; color: #fff; }

/* ---------- Shared deal primitives (detail, related) ---------- */
.tag { flex: none; font-size: 12.5px; font-weight: 600; color: var(--ink-2); background: var(--sunk); border-radius: 6px; padding: 3px 8px; white-space: nowrap; }
.pick { display: inline-flex; align-items: center; font-size: 12.5px; font-weight: 700; border-radius: 7px; padding: 4px 9px; line-height: 1.4; text-align: right; }
.pick.is-ali { color: var(--save-ink); background: var(--save-bg); }
.pick.is-local { color: var(--local); background: var(--local-bg); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; }
.chips li { font-size: 12.5px; font-weight: 550; color: var(--ink-2); border: 1px solid var(--line); border-radius: 6px; padding: 2px 8px; background: var(--surface); }

.battle { display: grid; grid-template-columns: 1fr 1fr; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.side { position: relative; padding: 13px 14px 12px; background: var(--surface); display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.side + .side { border-left: 1px solid var(--line); }
.side.is-win { background: #F3FAF8; box-shadow: inset 0 0 0 1.5px var(--save); border-radius: 0; }
.side:first-child.is-win { border-radius: 11px 0 0 11px; }
.side:last-child.is-win { border-radius: 0 11px 11px 0; }
.side-head { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.store { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; }
.store::before { content: ""; width: 8px; height: 8px; border-radius: 2px; background: var(--c, var(--ink)); flex: none; }
.coupang { --c: var(--coupang); }
.amazon { --c: var(--amazon); }
.ali { --c: var(--ali); }
.perk { font-size: 12px; color: var(--muted); }
.price { font-size: 1.42rem; font-weight: 780; letter-spacing: -0.025em; line-height: 1.25; margin-top: 3px; }
.price small { font-size: 0.85rem; font-weight: 650; margin-left: 1px; }
.side-meta { font-size: 12.5px; color: var(--muted); }
.win-tag { font-size: 11px; font-weight: 750; color: #fff; background: var(--save); border-radius: 4px; padding: 0 5px; line-height: 1.6; }
.customs { align-self: flex-start; margin-top: 5px; font-size: 12px; font-weight: 650; color: var(--warn-ink); background: var(--warn-bg); border-radius: 6px; padding: 2px 7px; }

.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px; padding: 10px 14px; border-radius: 10px; font-weight: 700; font-size: 14.5px; text-decoration: none; color: #fff; transition: filter 0.2s, transform 0.2s var(--ease); text-align: center; line-height: 1.3; }
.btn:hover { filter: brightness(0.93); }
.btn:active { transform: translateY(1px); }
.btn-coupang { background: var(--coupang); }
.btn-amazon { background: var(--amazon); color: #111827; }
.btn-ali { background: var(--ali); }
.kpi-label { font-size: 12.5px; color: var(--muted); font-weight: 600; }

/* ---------- Index: title + summary strip ---------- */
.is-hub { --wrap: 1336px; }
.idx-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 4px 20px; padding: 20px 0 12px; }
.idx-head h1 { font-size: 1.375rem; line-height: 1.3; letter-spacing: -0.022em; font-weight: 760; }
.hub .crumbs { padding-top: 16px; }
.hub .crumbs + .idx-head { padding-top: 6px; }
.stamp { color: var(--muted); font-size: 13px; display: flex; gap: 2px 14px; flex-wrap: wrap; }
.stamp b { color: var(--ink-2); font-weight: 650; }

.summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); background: var(--surface); border: 1px solid var(--line); border-radius: 12px; }
.sm { padding: 10px 16px 11px; border-left: 1px solid var(--line); min-width: 0; }
.sm:first-child { border-left: 0; }
.sm dt { font-size: 12px; font-weight: 650; color: var(--muted); }
.sm dt .store { font-size: 12px; font-weight: 650; }
.sm-v { display: inline-block; font-size: 1.125rem; font-weight: 760; letter-spacing: -0.02em; line-height: 1.4; }
.sm-v small { font-size: 0.8125rem; font-weight: 650; color: var(--ink-2); margin-left: 3px; letter-spacing: 0; }
.sm-v.is-text { font-size: 0.9375rem; font-weight: 700; line-height: 1.68; }
.sm-s { display: block; font-size: 12.5px; color: var(--ink-2); line-height: 1.45; }
.sm a { text-decoration: none; border-radius: 4px; }
.sm a:hover .sm-v { text-decoration: underline; text-decoration-thickness: 1.5px; text-underline-offset: 3px; }

/* ---------- Index: top spreads strip ---------- */
.tops { display: grid; grid-template-columns: auto repeat(var(--n, 4), minmax(0, 1fr)); margin-top: 10px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; }
.tops h2 { display: flex; flex-direction: column; justify-content: center; padding: 8px 16px; font-size: 12.5px; font-weight: 700; line-height: 1.4; white-space: nowrap; background: var(--sunk); border-radius: 11px 0 0 11px; }
.tops h2 small { font-size: 12px; font-weight: 550; color: var(--muted); }
.tops ol { display: contents; list-style: none; }
.tops li { border-left: 1px solid var(--line); min-width: 0; }
.tops a { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0 10px; align-items: center; height: 100%; padding: 8px 14px 9px; text-decoration: none; transition: background 0.15s; }
.tops li:last-child a { border-radius: 0 11px 11px 0; }
.tops a:hover { background: #FAFBFC; }
.tops a:hover .tops-name { text-decoration: underline; }
.tops-name { font-size: 13.5px; font-weight: 650; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tops-pct { grid-row: span 2; font-size: 15px; font-weight: 760; letter-spacing: -0.01em; }
.tops-pct.is-ali { color: var(--save-ink); }
.tops-pct.is-local { color: var(--local); }
.tops-sub { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ---------- Index: faceted workspace ---------- */
.work { display: grid; grid-template-columns: 232px minmax(0, 1fr); gap: 0 28px; margin-top: 8px; align-items: start; }
.side-col { position: sticky; top: 72px; max-height: calc(100dvh - 84px); overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin; scrollbar-color: var(--line-2) transparent; margin-top: 10px; padding: 0 6px 20px 0; }
.facet-h, .facet legend { display: flex; align-items: baseline; gap: 6px; padding: 0 8px 4px; font-size: 12px; font-weight: 700; color: var(--muted); }
.facet legend small { font-size: 11.5px; font-weight: 550; }
.catnav ul { list-style: none; }
.catnav a { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 30px; padding: 4px 8px; border-radius: 7px; font-size: 14px; font-weight: 550; color: var(--ink-2); text-decoration: none; transition: background 0.15s; }
.catnav a:hover { background: #E9ECF0; color: var(--ink); }
.catnav .num, .opt .num { font-size: 12.5px; font-weight: 550; color: var(--muted); }
.catnav a[aria-current] { background: var(--ink); color: #fff; font-weight: 650; }
.catnav a[aria-current] .num { color: #C9CED6; }
.catnav a.is-zero, .opt.is-zero { opacity: 0.45; }
.facet { border: 0; margin-top: 20px; padding: 0; min-width: 0; }
.opt { display: flex; align-items: center; gap: 8px; min-height: 30px; padding: 4px 8px; border-radius: 7px; font-size: 14px; color: var(--ink-2); cursor: pointer; transition: background 0.15s; }
.opt:hover { background: #E9ECF0; color: var(--ink); }
.opt input { flex: none; width: 15px; height: 15px; margin: 0; cursor: pointer; }
.opt .lbl { flex: 1; min-width: 0; }
.opt .lbl small { font-size: 12px; color: var(--muted); margin-left: 2px; }
.opt:has(input:checked) { color: var(--ink); font-weight: 650; }
.opt:has(input:focus-visible) { outline: 2px solid var(--coupang); outline-offset: -2px; }
.opt input:focus-visible { outline: none; }
.opt-sep { margin-top: 6px; }
.facet[data-brands]:not([data-expanded]) .opt.is-extra:not(:has(input:checked)) { display: none; }
.facet-more { display: inline-flex; align-items: center; gap: 4px; margin: 4px 0 0 8px; border: 0; background: none; padding: 4px 0; font-size: 13px; font-weight: 650; color: var(--ink-2); cursor: pointer; text-decoration: underline; text-decoration-color: var(--line-2); text-underline-offset: 3px; }
.facet-more:hover { color: var(--ink); text-decoration-color: currentColor; }
.sheet-head, .sheet-foot, .scrim, .fbtn { display: none; }

.main { container: idx / inline-size; min-width: 0; }
.bar { position: sticky; top: 62px; z-index: 10; display: flex; align-items: center; gap: 8px; padding: 10px 0; background: var(--canvas); }
.search { position: relative; flex: 1 1 220px; min-width: 0; }
.search .i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.search input { width: 100%; height: 40px; border: 1px solid var(--line-2); border-radius: 10px; background: var(--surface); padding: 0 40px 0 36px; font-size: 14.5px; transition: border-color 0.2s, box-shadow 0.2s; }
.search input::placeholder { color: #6B7280; }
.search input::-webkit-search-cancel-button { display: none; }
.search input:focus { outline: none; border-color: var(--ink); box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.08); }
.search kbd { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font: 600 11px/1 inherit; color: var(--muted); border: 1px solid var(--line-2); border-radius: 5px; padding: 3px 6px; background: var(--sunk); pointer-events: none; }
.search input:focus + kbd, .search input:not(:placeholder-shown) + kbd { display: none; }
.sort { position: relative; flex: none; }
.sort select { appearance: none; -webkit-appearance: none; height: 40px; max-width: 100%; border: 1px solid var(--line-2); border-radius: 10px; background: var(--surface); padding: 0 32px 0 12px; font-size: 14px; font-weight: 600; cursor: pointer; transition: border-color 0.2s; }
.sort select:hover { border-color: var(--ink); }
.sort .i { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.fbtn { align-items: center; gap: 6px; flex: none; height: 40px; border: 1px solid var(--line-2); border-radius: 10px; background: var(--surface); padding: 0 12px; font-size: 14px; font-weight: 650; cursor: pointer; }
.fbtn b { min-width: 18px; height: 18px; border-radius: 9px; background: var(--ink); color: #fff; font-size: 11.5px; font-weight: 700; line-height: 18px; text-align: center; padding: 0 5px; }

.status { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; min-height: 32px; margin-bottom: 8px; font-size: 13px; color: var(--muted); }
.status-text strong, .pager-status strong { color: var(--ink); font-weight: 700; }
.on-chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.chip-x { display: inline-flex; align-items: center; gap: 3px; min-height: 26px; border: 1px solid var(--line-2); border-radius: 999px; background: var(--surface); padding: 2px 6px 2px 10px; font-size: 12.5px; font-weight: 600; color: var(--ink-2); cursor: pointer; transition: border-color 0.15s; }
.chip-x:hover { border-color: var(--ink); color: var(--ink); }
.chip-x .i { color: var(--muted); }
.chip-clear { border: 0; background: none; padding: 2px 4px; font-size: 12.5px; font-weight: 650; color: var(--ink-2); cursor: pointer; text-decoration: underline; text-decoration-color: var(--line-2); text-underline-offset: 3px; }
.chip-clear:hover { color: var(--ink); text-decoration-color: currentColor; }
.seg { display: inline-flex; background: var(--surface); border: 1px solid var(--line-2); border-radius: 9px; padding: 2px; gap: 2px; height: 32px; margin-left: auto; }
.seg button { display: inline-flex; align-items: center; gap: 5px; border: 0; background: transparent; padding: 0 10px; border-radius: 6px; font-size: 12.5px; font-weight: 600; color: var(--ink-2); cursor: pointer; white-space: nowrap; transition: background 0.15s, color 0.15s; }
.seg button:hover { color: var(--ink); background: var(--sunk); }
.seg button[aria-pressed="true"] { background: var(--ink); color: #fff; }

/* ---------- Index: ledger rows (one DOM, list or card layout) ---------- */
.rows { list-style: none; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.row { --rg: 10px; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); grid-template-areas: "info info" "dom ali" "verd verd" "act act"; gap: var(--rg) 8px; margin-top: -1px; padding: 14px 14px 12px; border-top: 1px solid var(--line); transition: background 0.15s; }
.row:hover, .row[data-open] { background: #FBFCFD; }
.r-info { grid-area: info; min-width: 0; }
.r-meta { font-size: 12px; font-weight: 600; color: var(--muted); line-height: 1.4; }
.r-title { margin-top: 1px; font-size: 14.5px; line-height: 1.4; font-weight: 700; letter-spacing: -0.012em; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; overflow: hidden; }
.r-title a { text-decoration: none; }
.r-title a:hover { text-decoration: underline; }
.r-spec { margin-top: 3px; font-size: 12.5px; color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.r-spec b { font-weight: 650; color: var(--ink); }
.r-spec span::before { content: "·"; margin: 0 6px; color: #9AA1AC; }
.r-price { display: flex; flex-direction: column; min-width: 0; padding: 7px 10px 8px; background: var(--sunk); border-radius: 8px; }
.r-dom { grid-area: dom; }
.r-ali { grid-area: ali; }
.r-price .store { font-size: 12px; font-weight: 650; color: var(--muted); }
.r-price .store::before { width: 7px; height: 7px; }
.amt { font-size: 15px; line-height: 1.4; font-weight: 600; color: var(--ink-2); letter-spacing: -0.01em; white-space: nowrap; }
.r-price.is-win .amt { font-weight: 780; color: var(--save-ink); }
.r-off { font-size: 12px; line-height: 1.4; color: var(--muted); }
.r-off b { font-weight: 700; color: var(--save-ink); }
.duty { align-self: flex-start; margin-top: 3px; font-size: 11.5px; font-weight: 650; line-height: 1.5; color: var(--warn-ink); background: var(--warn-bg); border-radius: 5px; padding: 0 6px; white-space: nowrap; }
.r-verd { grid-area: verd; display: flex; flex-wrap: wrap; align-items: baseline; gap: 0 8px; min-width: 0; }
.gap { font-size: 14.5px; line-height: 1.45; font-weight: 760; letter-spacing: -0.01em; white-space: nowrap; }
.gap small { font-size: 12.5px; font-weight: 650; color: var(--ink-2); margin-left: 2px; }
.call { font-size: 12.5px; line-height: 1.45; font-weight: 700; white-space: nowrap; }
.is-ali > .call { color: var(--save-ink); }
.is-local > .call { color: var(--local); }
.why { font-size: 12px; line-height: 1.4; color: var(--muted); white-space: nowrap; }
.r-act { grid-area: act; display: flex; flex-wrap: wrap; align-items: center; align-content: flex-start; gap: 4px 6px; }
.buy { flex: 1; display: inline-flex; align-items: center; justify-content: center; gap: 4px; height: 38px; padding: 0 9px; border: 1px solid var(--line-2); border-radius: 8px; background: var(--surface); font-size: 13px; font-weight: 650; color: var(--ink); text-decoration: none; white-space: nowrap; transition: border-color 0.15s, background 0.15s; }
.buy .i { color: var(--muted); }
.buy:hover { border-color: var(--c, var(--ink)); }
.buy.is-pick { background: var(--ink); border-color: var(--ink); color: #fff; }
.buy.is-pick .i { color: #C9CED6; }
.buy.is-pick:hover { background: #1F2937; }
.r-more { display: inline-flex; align-items: center; justify-content: center; gap: 3px; height: 38px; border: 0; border-radius: 8px; background: transparent; padding: 0 6px 0 8px; font-size: 13px; font-weight: 600; color: var(--ink-2); cursor: pointer; white-space: nowrap; transition: background 0.15s; }
.r-more:hover { background: #E9ECF0; color: var(--ink); }
.r-more .i { transition: transform 0.2s var(--ease); }
.row[data-open] .r-more .i { transform: rotate(180deg); }

.drawer { grid-column: 1 / -1; display: grid; grid-template-rows: 0fr; visibility: hidden; margin-top: calc(var(--rg) * -1); transition: grid-template-rows 0.22s var(--ease), visibility 0s 0.22s; }
.row[data-open] .drawer { grid-template-rows: 1fr; visibility: visible; margin-top: 0; transition: grid-template-rows 0.22s var(--ease); }
.drawer-in { min-height: 0; overflow: hidden; }
.drawer-box { display: grid; gap: 10px; padding: 12px 14px; background: var(--sunk); border-radius: 8px; }
.drawer dl { display: grid; gap: 10px 28px; }
.drawer dt { font-size: 12px; font-weight: 700; color: var(--muted); }
.drawer dd { position: relative; font-size: 13.5px; line-height: 1.55; color: var(--ink-2); max-width: 68ch; }
.drawer .cons dd { padding-left: 12px; }
.drawer .cons dd::before { content: ""; position: absolute; left: 1px; top: 0.72em; width: 5px; height: 1.5px; background: #9AA1AC; }
.drawer-link { justify-self: start; display: inline-flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 650; text-decoration: none; }
.drawer-link:hover { text-decoration: underline; }
.drawer-link .i { transition: transform 0.2s var(--ease); }
.drawer-link:hover .i { transform: translateX(3px); }

.hub[data-view="cards"] .rows { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; background: none; border: 0; border-radius: 0; overflow: visible; }
.hub[data-view="cards"] .row { grid-template-rows: 1fr; align-content: start; margin-top: 0; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
.hub[data-view="cards"] .row:hover { border-color: var(--line-2); }
@container idx (max-width: 639.98px) {
  .hub[data-view="cards"] .rows { grid-template-columns: minmax(0, 1fr); }
}
@container idx (min-width: 560px) {
  .drawer dl { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .hub[data-view="cards"] .drawer dl { grid-template-columns: minmax(0, 1fr); }
  .buy, .r-more { height: 32px; }
}
@container idx (min-width: 560px) and (max-width: 879.98px) {
  .hub[data-view="list"] .row { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.5fr); grid-template-areas: "info info act" "dom ali verd"; gap: var(--rg) 10px; padding: 14px 16px 12px; }
  .hub[data-view="list"] .r-act { align-self: start; justify-content: flex-end; }
  .hub[data-view="list"] .buy { flex: none; }
  .hub[data-view="list"] .r-verd { flex-direction: column; flex-wrap: nowrap; align-self: center; padding-left: 6px; }
}
@container idx (min-width: 880px) {
  .hub[data-view="list"] .row { --rg: 0px; grid-template-columns: minmax(0, 1fr) var(--pc, 112px) calc(var(--pc, 112px) + 4px) 168px var(--act, 136px); grid-template-areas: "info dom ali verd act"; gap: 0 16px; padding: 12px 16px; content-visibility: auto; contain-intrinsic-size: auto 92px; }
  .hub[data-view="list"] .r-price { align-items: flex-end; padding: 0; background: none; border-radius: 0; text-align: right; }
  .hub[data-view="list"] .duty { align-self: flex-end; }
  .hub[data-view="list"] .r-verd { flex-direction: column; flex-wrap: nowrap; }
  .hub[data-view="list"] .r-act { justify-content: flex-end; }
  .hub[data-view="list"] .buy { flex: none; }
  .hub[data-view="list"] .drawer-box { margin-top: 12px; grid-template-columns: minmax(0, 1fr) auto; align-items: end; }
}
.en { --act: 152px; --pc: 128px; }

.pager { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px; margin-top: 14px; }
.pager-status { width: 100%; text-align: center; font-size: 13px; color: var(--muted); }
.pager button { height: 40px; border: 1px solid var(--line-2); border-radius: 10px; background: var(--surface); padding: 0 16px; font-size: 14px; font-weight: 650; cursor: pointer; transition: border-color 0.15s, background 0.15s; }
.pager button:hover { border-color: var(--ink); }
.pager button.primary { background: var(--ink); border-color: var(--ink); color: #fff; }
.pager button.primary:hover { background: #1F2937; }
.empty { background: var(--surface); border: 1px dashed var(--line-2); border-radius: 12px; padding: 36px 20px; text-align: center; font-size: 14px; color: var(--ink-2); }
.empty strong { display: block; font-size: 1rem; color: var(--ink); margin-bottom: 2px; }
.empty button { margin-top: 14px; height: 36px; border: 1px solid var(--ink); background: var(--ink); color: #fff; border-radius: 9px; padding: 0 14px; font-size: 13.5px; font-weight: 650; cursor: pointer; }

/* Before app.js runs, clamp to the first page so the full catalog never flashes; without JS everything stays visible. */
html.js .hub:not([data-ready]) .rows > li:nth-child(n+__PAGE_NEXT__) { display: none; }
html:not(.js) .bar, html:not(.js) .status, html:not(.js) .pager, html:not(.js) .facets, html:not(.js) .r-more { display: none; }
html:not(.js) .drawer { grid-template-rows: 1fr; visibility: visible; margin-top: 0; }

/* ---------- Detail page ---------- */
.crumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; padding: 22px 0 0; font-size: 13.5px; color: var(--muted); list-style: none; }
.crumbs a { text-decoration: none; color: var(--ink-2); }
.crumbs a:hover { text-decoration: underline; }
.crumbs .i { color: #9AA1AC; }
.crumbs [aria-current] { color: var(--ink); font-weight: 600; }
.detail { display: grid; grid-template-columns: minmax(0, 1fr) 360px; grid-template-areas: "intro aside" "body aside"; gap: 0 36px; padding: 18px 0 10px; align-items: start; }
.d-intro { grid-area: intro; min-width: 0; }
.d-intro > .tag { display: inline-block; white-space: normal; }
.d-body { grid-area: body; }
.d-aside { grid-area: aside; position: sticky; top: 82px; }
.d-intro h1 { margin-top: 10px; font-size: clamp(1.7rem, 1.2rem + 1.8vw, 2.45rem); line-height: 1.18; letter-spacing: -0.032em; font-weight: 780; text-wrap: balance; }
.d-intro .dek { margin-top: 12px; color: var(--ink-2); font-size: 1.04rem; max-width: 64ch; }
.d-intro .chips { margin-top: 16px; }
.section { margin-top: 34px; }
.section h2 { font-size: 1.32rem; letter-spacing: -0.02em; font-weight: 740; margin-bottom: 12px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); }
.bars { padding: 18px 20px 6px; }
.bar-row { display: grid; grid-template-columns: 8.5em minmax(0, 1fr) 7.5em; gap: 12px; align-items: center; padding: 8px 0; }
.bar-name { font-size: 13.5px; font-weight: 650; }
.bar-track { height: 12px; background: var(--sunk); border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; background: #A9B0BA; transform-origin: left; animation: grow 0.9s var(--ease) both; }
.bar-fill.msrp { background: #D3D8DF; }
.bar-fill.win { background: var(--save); }
.bar-val { text-align: right; font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
.bar-val small { display: block; font-size: 12px; font-weight: 600; color: var(--muted); }
@keyframes grow { from { transform: scaleX(0.06); } to { transform: scaleX(1); } }
.facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--line); margin-top: 10px; }
.fact { padding: 14px 20px; border-left: 1px solid var(--line); }
.fact:first-child { border-left: 0; }
.fact span { display: block; font-size: 12.5px; color: var(--muted); font-weight: 600; }
.fact strong { display: block; margin-top: 2px; font-size: 1.12rem; font-weight: 760; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.customs-note { display: flex; gap: 10px; margin: 0 20px 18px; padding: 11px 13px; border-radius: 10px; background: var(--warn-bg); color: var(--warn-ink); font-size: 13.5px; line-height: 1.55; }
.customs-note strong { white-space: nowrap; }
.spec-table { width: 100%; border-collapse: collapse; font-size: 14.5px; }
.spec-table th, .spec-table td { text-align: left; padding: 12px 20px; border-bottom: 1px solid var(--line); vertical-align: top; }
.spec-table tr:last-child th, .spec-table tr:last-child td { border-bottom: 0; }
.spec-table th { width: 32%; color: var(--muted); font-weight: 600; font-size: 13.5px; background: #FAFBFC; }
.pc { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.pc .panel { padding: 18px 20px; }
.pc h3 { display: flex; align-items: center; gap: 8px; font-size: 1rem; font-weight: 720; margin-bottom: 8px; }
.pc h3::before { content: ""; width: 9px; height: 9px; border-radius: 50%; background: var(--c); }
.pc .pros { --c: var(--save); }
.pc .cons { --c: #D97706; }
.pc ul { list-style: none; display: grid; gap: 8px; }
.pc li { position: relative; padding-left: 16px; font-size: 14.5px; color: var(--ink-2); line-height: 1.6; }
.pc li::before { content: ""; position: absolute; left: 2px; top: 0.7em; width: 6px; height: 1.5px; background: var(--line-2); }
.decide { padding: 20px; }
.decide-title { font-size: 13px; font-weight: 650; color: var(--muted); }
.decide .pick { margin-top: 8px; font-size: 13.5px; text-align: left; }
.decide-verdict { margin-top: 12px; font-size: 14.5px; line-height: 1.6; color: var(--ink-2); }
.decide .battle { margin-top: 14px; }
.decide .battle .price { font-size: 1.25rem; }
.decide .actions { grid-template-columns: 1fr; margin-top: 14px; }
.decide-stamp { margin-top: 12px; font-size: 12.5px; color: var(--muted); }
.decide-switch { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; font-size: 13.5px; font-weight: 600; color: var(--ink-2); text-decoration: none; }
.decide-switch:hover { color: var(--ink); text-decoration: underline; }
.related { margin-top: 52px; padding-top: 30px; border-top: 1px solid var(--line); }
.related h2 { font-size: 1.25rem; letter-spacing: -0.02em; font-weight: 750; margin-bottom: 14px; }
.rel-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.rel { position: relative; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; transition: box-shadow 0.35s var(--ease); }
.rel:hover { box-shadow: var(--shadow-hi); }
.rel h3 { font-size: 1rem; line-height: 1.4; letter-spacing: -0.015em; font-weight: 700; }
.rel h3 a { text-decoration: none; }
.rel h3 a::after { content: ""; position: absolute; inset: 0; border-radius: inherit; }
.rel h3 a:hover { text-decoration: underline; }
.rel-prices { display: flex; gap: 14px; font-size: 13.5px; color: var(--ink-2); flex-wrap: wrap; margin-top: auto; }
.rel-prices b { font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; }
.rel .pick { align-self: flex-start; font-size: 12px; }

/* ---------- Gateway ---------- */
.gate-hero { padding: 64px 0 34px; max-width: 760px; }
.gate-hero h1 { font-size: clamp(2.1rem, 1.3rem + 3.2vw, 3.5rem); line-height: 1.08; letter-spacing: -0.04em; font-weight: 790; text-wrap: balance; }
.gate-hero p { margin-top: 16px; font-size: 1.08rem; color: var(--ink-2); max-width: 58ch; }
.gate-hero p + p { margin-top: 6px; color: var(--muted); font-size: 1rem; }
.regions { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding-bottom: 20px; }
.region { position: relative; background: var(--surface); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); padding: 24px 24px 20px; display: flex; flex-direction: column; gap: 16px; transition: box-shadow 0.35s var(--ease), border-color 0.35s; }
.region:hover { box-shadow: var(--shadow-hi); border-color: var(--line-2); }
.region.is-suggested { border-color: var(--ink); }
.region-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.region h2 { font-size: 1.45rem; letter-spacing: -0.03em; font-weight: 770; line-height: 1.25; }
.region h2 a { text-decoration: none; }
.region h2 a::after { content: ""; position: absolute; inset: 0; border-radius: inherit; }
.region-route { margin-top: 4px; font-size: 14px; color: var(--ink-2); }
.suggest { font-size: 12px; font-weight: 700; color: #fff; background: var(--ink); border-radius: 6px; padding: 3px 8px; white-space: nowrap; }
.region-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.region-stats div { padding: 12px 0 12px 14px; border-left: 1px solid var(--line); min-width: 0; }
.region-stats div:first-child { border-left: 0; padding-left: 0; }
.region-stats span { display: block; font-size: 12px; color: var(--muted); font-weight: 600; }
.region-stats strong { display: block; font-size: 1.15rem; font-weight: 760; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.top3 { list-style: none; display: grid; gap: 0; }
.top3 li { display: flex; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px dashed var(--line); font-size: 14px; }
.top3 li:last-child { border-bottom: 0; }
.top3 b { font-weight: 700; color: var(--save-ink); font-variant-numeric: tabular-nums; white-space: nowrap; }
.region-cta { display: inline-flex; align-items: center; gap: 6px; font-weight: 700; font-size: 14.5px; }

/* ---------- Prose (policy) ---------- */
.prose { max-width: 72ch; padding: 40px 0 10px; }
.prose h1 { font-size: clamp(1.8rem, 1.3rem + 1.6vw, 2.4rem); letter-spacing: -0.03em; line-height: 1.2; font-weight: 780; }
.prose h2 { margin-top: 34px; font-size: 1.15rem; font-weight: 740; letter-spacing: -0.02em; }
.prose p { margin-top: 10px; color: var(--ink-2); }
.prose .lead { margin-top: 12px; font-size: 1.05rem; }

/* ---------- Footer ---------- */
.site-foot { margin-top: 64px; border-top: 1px solid var(--line); background: var(--surface); }
.site-foot .wrap { display: grid; grid-template-columns: 1fr auto; gap: 18px 40px; padding-top: 26px; padding-bottom: 32px; font-size: 13px; color: var(--muted); }
.site-foot p { max-width: 80ch; }
.foot-links { display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-start; }
.foot-links a { color: var(--ink-2); font-weight: 600; text-decoration: none; }
.foot-links a:hover { text-decoration: underline; }

/* ---------- Responsive ---------- */
@media (max-width: 1023.98px) {
  .detail { grid-template-columns: minmax(0, 1fr); grid-template-areas: "intro" "aside" "body"; }
  .d-aside { position: static; margin-top: 22px; }
  .rel-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  /* Index: sidebar dissolves into a category scroller + bottom filter sheet */
  .is-hub .site-head { position: static; }
  .work { display: block; margin-top: 14px; }
  .side-col { display: contents; }
  .catnav .facet-h { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .catnav ul { display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; margin: 0 -22px; padding: 0 22px 2px; }
  .catnav ul::-webkit-scrollbar { display: none; }
  .catnav li { flex: none; }
  .catnav a { min-height: 34px; padding: 4px 12px; border: 1px solid var(--line-2); border-radius: 999px; background: var(--surface); font-size: 13.5px; font-weight: 600; }
  .catnav a:hover { background: var(--surface); border-color: var(--ink); }
  .catnav a[aria-current] { border-color: var(--ink); background: var(--ink); }
  .bar { top: 0; }
  .fbtn { display: inline-flex; }
  .facets { position: fixed; z-index: 40; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; max-height: 86dvh; background: var(--surface); border-radius: 16px 16px 0 0; box-shadow: 0 -12px 40px -12px rgba(17, 24, 39, 0.35); transform: translateY(104%); visibility: hidden; transition: transform 0.28s var(--ease), visibility 0s 0.28s; }
  .facets[data-open] { transform: none; visibility: visible; transition: transform 0.28s var(--ease); }
  .facets-body { overflow-y: auto; overscroll-behavior: contain; padding: 14px 12px 12px; }
  .facets-body .facet:first-child { margin-top: 0; }
  .facets .opt { min-height: 42px; font-size: 15px; }
  .facets .opt input { width: 18px; height: 18px; }
  .facet[data-brands] .opts { display: grid; grid-template-columns: 1fr 1fr; gap: 0 8px; }
  .sheet-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 12px 12px 20px; border-bottom: 1px solid var(--line); font-size: 15px; }
  .sheet-head button { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; border: 0; border-radius: 10px; background: none; color: var(--ink-2); cursor: pointer; }
  .sheet-head button:hover { background: var(--sunk); }
  .sheet-foot { display: grid; grid-template-columns: auto 1fr; gap: 8px; padding: 10px 16px calc(10px + env(safe-area-inset-bottom)); border-top: 1px solid var(--line); }
  .sheet-foot button { height: 46px; border: 1px solid var(--line-2); border-radius: 11px; background: var(--surface); padding: 0 16px; font-size: 14.5px; font-weight: 650; cursor: pointer; }
  .sheet-foot .primary { background: var(--ink); border-color: var(--ink); color: #fff; }
  .scrim { display: block; position: fixed; inset: 0; z-index: 39; background: rgba(17, 24, 39, 0.45); opacity: 0; visibility: hidden; transition: opacity 0.25s, visibility 0s 0.25s; }
  .scrim[data-open] { opacity: 1; visibility: visible; transition: opacity 0.25s; }
  html.sheet-open { overflow: hidden; }
}
@media (max-width: 860px) {
  .regions { grid-template-columns: 1fr; }
  .head-nav .lbl-long { display: none; }
  .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sm:nth-child(3) { border-left: 0; }
  .sm:nth-child(n+3) { border-top: 1px solid var(--line); }
  .tops { display: flex; overflow-x: auto; overscroll-behavior-x: contain; scroll-snap-type: x proximity; scrollbar-width: none; }
  .tops::-webkit-scrollbar { display: none; }
  .tops h2 { flex: none; padding: 8px 14px; }
  .tops li { flex: 0 0 232px; scroll-snap-align: start; }
}
@media (max-width: 620px) {
  body { font-size: 15px; }
  .wrap { padding: 0 16px; }
  .site-head .wrap { height: 56px; }
  .brand-name { display: none; }
  .head-nav { gap: 0; font-size: 13.5px; }
  .head-nav a { padding: 7px 8px; }
  .head-nav .lbl-tg { display: none; }
  .idx-head { padding: 16px 0 10px; }
  .idx-head h1 { font-size: 1.25rem; }
  .sm { padding: 9px 12px 10px; }
  .sm-v { font-size: 1.0625rem; }
  .catnav ul { margin: 0 -16px; padding: 0 16px 2px; }
  .search kbd { display: none; }
  .search input { padding-right: 12px; font-size: 16px; }
  .sort select { width: 132px; text-overflow: ellipsis; }
  .fbtn span { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .seg .lbl { display: none; }
  .seg button { padding: 0 9px; }
  .pick { text-align: left; }
  .price { font-size: 1.22rem; }
  .battle .side { padding: 11px 11px 10px; }
  .actions { grid-template-columns: 1fr; }
  .bar-row { grid-template-columns: 5.6em minmax(0, 1fr) 6.6em; gap: 8px; }
  .facts { grid-template-columns: 1fr; }
  .fact { border-left: 0; border-top: 1px solid var(--line); }
  .fact:first-child { border-top: 0; }
  .pc, .rel-grid { grid-template-columns: 1fr; }
  .spec-table th, .spec-table td { padding: 11px 14px; }
  .spec-table th { width: 38%; }
  .region { padding: 20px 18px 18px; }
  .region-stats { grid-template-columns: 1fr 1fr; }
  .region-stats div:nth-child(3) { grid-column: 1 / -1; border-left: 0; padding-left: 0; border-top: 1px solid var(--line); }
  .site-foot .wrap { grid-template-columns: 1fr; }
  .legal-strip { font-size: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
"""

APP_JS = r"""
(() => {
  const hub = document.querySelector('[data-hub]');
  if (!hub) return;
  const $ = (s, r) => (r || hub).querySelector(s);
  const $$ = (s, r) => Array.from((r || hub).querySelectorAll(s));
  const L = JSON.parse($('[data-i18n]').textContent);
  const fmt = (tpl, v) => tpl.replace(/\{(\w+)\}/g, (_, k) => v[k]);
  const norm = s => s.normalize('NFKC').toLowerCase();
  const PAGE = parseInt(hub.dataset.pageSize, 10) || 20;
  const scoped = hub.dataset.scope !== 'all';

  const list = $('[data-rows]');
  const items = Array.from(list.children).map(el => {
    const d = el.dataset;
    return { el, c: d.c, b: d.b, r: d.r, d: d.d === '1', pb: d.pb, save: +d.save, pct: +d.pct, price: +d.price, q: d.q };
  });
  const SORTS = {
    save: (a, b) => b.save - a.save,
    pct: (a, b) => b.pct - a.pct,
    price: (a, b) => a.price - b.price,
    name: (a, b) => a.q.localeCompare(b.q),
  };

  const main = $('.main');
  const search = $('[data-search]');
  const sortSel = $('[data-sort]');
  const viewBtns = $$('[data-view-btn]');
  const catLinks = scoped ? [] : $$('[data-cat]');
  const routeIn = $$('input[name="route"]');
  const dutyIn = $('[data-duty]');
  const priceIn = $$('input[data-f="price"]');
  const brandIn = $$('input[data-f="brand"]');
  const brandBox = $('[data-brands]');
  const brandMore = $('[data-brand-more]');
  const counters = $$('[data-n]');
  const statusEls = $$('[data-status]');
  const chipsEl = $('[data-chips]');
  const moreBtn = $('[data-load]');
  const allBtn = $('[data-all]');
  const empty = $('[data-empty]');
  const sheet = $('[data-sheet]');
  const scrim = $('[data-scrim]');
  const fcount = $('[data-fcount]');
  const applyBtn = $('[data-sheet-apply]');
  const xIcon = $('[data-x]');

  const params = new URLSearchParams(location.search);
  const pickMany = (key, inputs) => {
    const valid = new Set(inputs.map(i => i.value));
    return new Set(params.getAll(key).filter(v => valid.has(v)));
  };
  let savedView = null;
  try { savedView = localStorage.getItem('gch-view'); } catch (e) {}
  const state = {
    cat: catLinks.some(a => a.dataset.cat === params.get('cat')) ? params.get('cat') : 'all',
    q: params.get('q') || '',
    route: ['ali', 'dom'].includes(params.get('route')) ? params.get('route') : 'all',
    duty: !!dutyIn && params.get('duty') === '1',
    price: pickMany('price', priceIn),
    brand: pickMany('brand', brandIn),
    sort: SORTS[params.get('sort')] ? params.get('sort') : 'save',
    view: (params.get('view') || savedView) === 'cards' ? 'cards' : 'list',
    limit: PAGE,
  };
  let order = items;

  function syncUrl() {
    const p = new URLSearchParams();
    if (state.cat !== 'all') p.set('cat', state.cat);
    if (state.q.trim()) p.set('q', state.q.trim());
    if (state.route !== 'all') p.set('route', state.route);
    if (state.duty) p.set('duty', '1');
    state.price.forEach(v => p.append('price', v));
    state.brand.forEach(v => p.append('brand', v));
    if (state.sort !== 'save') p.set('sort', state.sort);
    const qs = p.toString();
    history.replaceState(null, '', qs ? '?' + qs : location.pathname);
  }

  // Server order is already `save`; only touch the DOM when the sort actually changes.
  function resort() {
    order = items.slice().sort(SORTS[state.sort]);
    const frag = document.createDocumentFragment();
    order.forEach(it => frag.appendChild(it.el));
    list.appendChild(frag);
  }

  function chip(label, off) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip-x';
    b.textContent = label;
    b.appendChild(xIcon.content.cloneNode(true));
    b.setAttribute('aria-label', fmt(L.remove, { x: label }));
    b.addEventListener('click', () => { off(); changed(); });
    return b;
  }

  function renderChips() {
    const out = [];
    if (state.q.trim()) out.push(chip(fmt(L.q, { q: state.q.trim() }), () => { state.q = ''; }));
    if (state.cat !== 'all') out.push(chip(L.cats[state.cat] || state.cat, () => { state.cat = 'all'; }));
    if (state.route !== 'all') out.push(chip(L.route[state.route], () => { state.route = 'all'; }));
    if (state.duty) out.push(chip(L.duty, () => { state.duty = false; }));
    Array.from(state.price).sort().forEach(v => out.push(chip(L.price[v], () => state.price.delete(v))));
    state.brand.forEach(v => out.push(chip(v, () => state.brand.delete(v))));
    if (out.length > 1) {
      const c = document.createElement('button');
      c.type = 'button';
      c.className = 'chip-clear';
      c.textContent = L.clear;
      c.addEventListener('click', reset);
      out.push(c);
    }
    chipsEl.replaceChildren(...out);
    const facets = (state.cat !== 'all') + (state.route !== 'all') + state.duty + state.price.size + state.brand.size;
    fcount.textContent = facets;
    fcount.hidden = facets === 0;
  }

  function apply() {
    const terms = norm(state.q).split(/\s+/).filter(Boolean);
    const tests = [
      ['cat', it => state.cat === 'all' || it.c === state.cat],
      ['q', it => terms.every(t => it.q.includes(t))],
      ['route', it => state.route === 'all' || it.r === state.route],
      ['duty', it => !state.duty || it.d],
      ['price', it => !state.price.size || state.price.has(it.pb)],
      ['brand', it => !state.brand.size || state.brand.has(it.b)],
    ];
    // Each facet's counts ignore that facet's own selection, so options show what picking them would yield.
    const tally = new Map();
    const bump = k => tally.set(k, (tally.get(k) || 0) + 1);
    let total = 0;
    order.forEach(it => {
      let misses = 0, miss = null;
      for (const [k, fn] of tests) {
        if (!fn(it)) { misses++; miss = k; if (misses > 1) break; }
      }
      it.el.hidden = misses > 0 || ++total > state.limit;
      if (misses > 1) return;
      const open = k => misses === 0 || miss === k;
      if (open('cat')) { bump('cat:all'); bump('cat:' + it.c); }
      if (open('route')) { bump('route:all'); bump('route:' + it.r); }
      if (open('duty') && it.d) bump('duty:1');
      if (open('price')) bump('price:' + it.pb);
      if (open('brand')) bump('brand:' + it.b);
    });
    const shown = Math.min(total, state.limit);

    counters.forEach(el => {
      const n = tally.get(el.dataset.n) || 0;
      el.textContent = n;
      const host = el.closest('.opt, [data-cat]');
      const input = host.querySelector('input');
      const active = input ? input.checked : host.hasAttribute('aria-current');
      host.classList.toggle('is-zero', n === 0 && !active);
    });
    catLinks.forEach(a => {
      if (a.dataset.cat === state.cat) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
    routeIn.forEach(i => { i.checked = i.value === state.route; });
    if (dutyIn) dutyIn.checked = state.duty;
    priceIn.forEach(i => { i.checked = state.price.has(i.value); });
    brandIn.forEach(i => { i.checked = state.brand.has(i.value); });
    sortSel.value = state.sort;
    viewBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.viewBtn === state.view)));
    hub.dataset.view = state.view;

    const text = total
      ? fmt(L.status, { a: 1, b: shown, n: total }) + (total !== items.length ? fmt(L.statusOf, { t: items.length }) : '')
      : fmt(L.statusNone, { t: items.length });
    statusEls.forEach(el => { el.innerHTML = text; });
    const rest = total - shown;
    moreBtn.hidden = rest <= 0;
    moreBtn.textContent = fmt(L.more, { k: Math.min(PAGE, rest), r: rest });
    allBtn.hidden = rest <= PAGE;
    allBtn.textContent = fmt(L.all, { n: total });
    applyBtn.textContent = fmt(L.apply, { n: total });
    empty.hidden = total > 0;
    list.hidden = total === 0;
    renderChips();
  }

  // Any filter change restarts paging and brings the list top back under the sticky bar.
  function changed() {
    state.limit = PAGE;
    apply();
    syncUrl();
    if (main.getBoundingClientRect().top < 0) main.scrollIntoView({ block: 'start' });
  }
  function reset() {
    state.q = ''; state.cat = 'all'; state.route = 'all'; state.duty = false;
    state.price.clear(); state.brand.clear();
    search.value = '';
    changed();
  }

  search.value = state.q;
  search.addEventListener('input', () => { state.q = search.value; changed(); });
  sortSel.addEventListener('change', () => { state.sort = sortSel.value; resort(); changed(); });
  viewBtns.forEach(b => b.addEventListener('click', () => {
    state.view = b.dataset.viewBtn;
    try { localStorage.setItem('gch-view', state.view); } catch (e) {}
    apply();
  }));
  catLinks.forEach(a => a.addEventListener('click', e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault();
    state.cat = a.dataset.cat;
    changed();
  }));
  $$('[data-route-link]').forEach(a => a.addEventListener('click', e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault();
    state.route = a.dataset.routeLink;
    changed();
    main.scrollIntoView({ block: 'start' });
  }));
  routeIn.forEach(i => i.addEventListener('change', () => { state.route = i.value; changed(); }));
  if (dutyIn) dutyIn.addEventListener('change', () => { state.duty = dutyIn.checked; changed(); });
  [[priceIn, state.price], [brandIn, state.brand]].forEach(([inputs, set]) => inputs.forEach(i => {
    i.addEventListener('change', () => { if (i.checked) set.add(i.value); else set.delete(i.value); changed(); });
  }));
  if (brandMore) brandMore.addEventListener('click', () => {
    const open = brandBox.toggleAttribute('data-expanded');
    brandMore.setAttribute('aria-expanded', String(open));
    brandMore.textContent = open ? brandMore.dataset.labelLess : brandMore.dataset.labelMore;
  });
  moreBtn.addEventListener('click', () => { state.limit += PAGE; apply(); });
  allBtn.addEventListener('click', () => { state.limit = Infinity; apply(); });
  $$('[data-reset]').forEach(b => b.addEventListener('click', reset));

  list.addEventListener('click', e => {
    const btn = e.target.closest('[data-more]');
    if (!btn) return;
    const open = btn.closest('li').toggleAttribute('data-open');
    btn.setAttribute('aria-expanded', String(open));
  });

  // Mobile filter sheet: the same facet markup that sits in the desktop sidebar.
  let lastFocus = null;
  const sheetOpen = () => sheet.hasAttribute('data-open');
  function openSheet() {
    lastFocus = document.activeElement;
    sheet.setAttribute('data-open', '');
    scrim.setAttribute('data-open', '');
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-modal', 'true');
    document.documentElement.classList.add('sheet-open');
    $('[data-sheet-close]', sheet).focus();
  }
  function closeSheet() {
    if (!sheetOpen()) return;
    sheet.removeAttribute('data-open');
    scrim.removeAttribute('data-open');
    sheet.removeAttribute('role');
    sheet.removeAttribute('aria-modal');
    document.documentElement.classList.remove('sheet-open');
    if (lastFocus) lastFocus.focus();
  }
  $('[data-sheet-open]').addEventListener('click', openSheet);
  $$('[data-sheet-close]').forEach(b => b.addEventListener('click', closeSheet));
  applyBtn.addEventListener('click', closeSheet);
  scrim.addEventListener('click', closeSheet);
  matchMedia('(min-width: 1024px)').addEventListener('change', closeSheet);
  sheet.addEventListener('keydown', e => {
    if (e.key !== 'Tab' || !sheetOpen()) return;
    const f = $$('button, input, a[href]', sheet).filter(el => el.offsetParent !== null);
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && sheetOpen()) { closeSheet(); return; }
    const typing = document.activeElement.matches('input:not([type="checkbox"]):not([type="radio"]), textarea, select');
    if (e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); search.focus(); search.select(); }
    else if (e.key === 'Escape' && document.activeElement === search && search.value) {
      search.value = ''; state.q = ''; changed();
    }
  });

  if (state.sort !== 'save') resort();
  apply();
  hub.setAttribute('data-ready', '');
})();
"""


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def _esc(val: object) -> str:
    return html.escape(str(val))


def product_slug(item_id: str, max_len: int = 48) -> str:
    """Short, URL-safe slug derived from a product id (shared with the Telegram notifier)."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(item_id).lower()).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0] or slug[:max_len]
    return slug or "item"


def _short_name(it: dict) -> str:
    """Compact display name, e.g. 'Beelink SER8' or 'UGREEN Nexode 100W'."""
    brand = it["brand"].strip()
    model = it["model"].strip()
    if model.lower().startswith(brand.lower()):
        model = model[len(brand):].strip()
    tokens = model.split()
    if not tokens:
        return brand
    picked = [tokens[0]]
    if tokens[0].isalpha() and len(tokens) > 1 and not re.search(r"[()%/]", tokens[1]):
        picked.append(tokens[1])
    return f"{brand} {' '.join(picked)}"


def _spec_label(key: str, lang: str) -> str:
    if lang == "ko" and key in SPEC_LABELS_KO:
        return SPEC_LABELS_KO[key]
    return " ".join(w.upper() if w in _SPEC_ACRONYMS else w.capitalize() for w in key.split("_"))


def _chip_text(val: str, limit: int = 30) -> str:
    text = re.sub(r"\s*\([^)]*\)", "", str(val)).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip(" ,/+") + "…"
    return text


def _chips(it: dict, n: int = 4) -> str:
    vals = [v for v in it.get("specs", {}).values() if str(v).strip()][:n]
    if not vals:
        return ""
    return '<ul class="chips">' + "".join(f"<li>{_esc(_chip_text(v))}</li>" for v in vals) + "</ul>"


def _money(val: float, lang: str, html_unit: bool = True) -> str:
    if lang == "ko":
        unit = "<small>원</small>" if html_unit else "원"
        return f"{int(round(val)):,}{unit}"
    return f"${val:,.2f}"


def _cat_label(cat: str, lang: str) -> str:
    labels = CATEGORY_LABELS_KO if lang == "ko" else CATEGORY_LABELS_EN
    return labels.get(cat, cat)


def _bracket(best: float, lang: str) -> int:
    brackets = _PRICE_BRACKETS[lang]
    for i, (cap, _) in enumerate(brackets):
        if cap is None or (best <= cap if lang == "ko" else best < cap):
            return i
    return len(brackets) - 1


def _deal(it: dict, lang: str) -> dict:
    """Normalize per-region pricing into one shape so KO & EN share every template."""
    p, m, links = it["prices"], it["metrics"], it["affiliate_links"]
    if lang == "ko":
        dom, ali = float(p["coupang_krw"]), float(p["ali_krw"])
        msrp = float(it.get("msrp_krw") or max(dom, ali))
        ali_wins = m["kr_cheaper"] == "aliexpress"
        diff, pct, off = float(m["kr_diff_krw"]), float(m["kr_savings_pct"]), float(m["msrp_drop_kr_pct"])
        dom_key, dom_url = "coupang", links["coupang"]
    else:
        dom, ali = float(p["amazon_usd"]), float(p["ali_usd"])
        msrp = float(it.get("msrp_usd") or max(dom, ali))
        ali_wins = m["en_cheaper"] == "aliexpress"
        diff, pct, off = float(m["en_diff_usd"]), float(m["en_savings_pct"]), float(m["msrp_drop_en_pct"])
        dom_key, dom_url = "amazon", links["amazon"]
    return {
        "dom": dom,
        "ali": ali,
        "msrp": msrp,
        "ali_wins": ali_wins,
        "diff": diff,
        "pct": pct,
        "off": off,
        "best": min(dom, ali),
        "bracket": _bracket(min(dom, ali), lang),
        "direct_pick": ali_wins and pct >= DIRECT_PICK_MIN_PCT,
        "customs": lang == "ko" and float(p["ali_usd"]) > KR_CUSTOMS_LIMIT_USD,
        "duty_free": float(p["ali_usd"]) <= KR_CUSTOMS_LIMIT_USD,
        "ali_usd": float(p["ali_usd"]),
        "dom_key": dom_key,
        "dom_url": dom_url,
        "ali_url": links["aliexpress"],
        "dom_off": round((msrp - dom) / msrp * 100) if msrp > 0 else 0,
        "ali_off": round((msrp - ali) / msrp * 100) if msrp > 0 else 0,
    }


T = {
    "ko": {
        "html_lang": "ko",
        "region": "KR",
        "disclosure": DISCLOSURE_KO,
        "legal_tag": "광고 고지",
        "dom_store": "쿠팡",
        "dom_perk": "내일 도착 · 간편 반품",
        "ali_store": "알리익스프레스",
        "ali_perk": "직구 특가 · 무료배송",
        "win": "최저가",
        "customs": f"${KR_CUSTOMS_LIMIT_USD} 초과 · 관부가세 유의",
        "btn_dom": "쿠팡 최저가 확인",
        "btn_ali": "알리 직구가 확인",
        "switch": "Global Hub",
        "tg": "텔레그램 알림",
        "tg_long": "핫딜 텔레그램 알림",
        "policy": "정책·고지",
        "home": "홈",
        "msrp": "정가",
        "off_msrp": "정가 대비",
    },
    "en": {
        "html_lang": "en",
        "region": "GLOBAL",
        "disclosure": DISCLOSURE_EN,
        "legal_tag": "Disclosure",
        "dom_store": "Amazon",
        "dom_perk": "Fast Prime · Easy Return",
        "ali_store": "AliExpress",
        "ali_perk": "Direct Saver",
        "win": "Lowest",
        "customs": "",
        "btn_dom": "Amazon",
        "btn_ali": "AliExpress",
        "switch": "한국어 허브",
        "tg": "Telegram alerts",
        "tg_long": "Telegram deal alerts",
        "policy": "Policy",
        "home": "Home",
        "msrp": "MSRP",
        "off_msrp": "vs MSRP",
    },
}


def _pick_badge(d: dict, lang: str) -> str:
    if lang == "ko":
        if d["direct_pick"]:
            return f'<span class="pick is-ali">알리 직구 추천 · {_money(d["diff"], lang, False)} ({d["pct"]:.0f}%) 절약</span>'
        return '<span class="pick is-local">쿠팡 정발 추천 · 빠른 배송·AS 유리</span>'
    if d["direct_pick"]:
        return f'<span class="pick is-ali">AliExpress pick · Save {_money(d["diff"], lang)} ({d["pct"]:.0f}%)</span>'
    return '<span class="pick is-local">Amazon pick · Fast Prime &amp; easy returns</span>'


def _pick_short(d: dict, lang: str) -> str:
    if d["direct_pick"]:
        return '<span class="pick is-ali">' + ("알리 직구" if lang == "ko" else "AliExpress") + "</span>"
    return '<span class="pick is-local">' + ("쿠팡 정발" if lang == "ko" else "Amazon") + "</span>"


def _ext(url: str, cls: str, label: str) -> str:
    return (
        f'<a class="{cls}" href="{_esc(url)}" target="_blank" rel="nofollow sponsored noopener">'
        f'{_esc(label)} {_icon("out", 15)}</a>'
    )


def _battle(d: dict, lang: str) -> str:
    t = T[lang]
    win_tag = f'<span class="win-tag">{t["win"]}</span>'
    dom_win = not d["ali_wins"]
    customs = f'<span class="customs">{_esc(t["customs"])}</span>' if d["customs"] else ""
    return f"""<div class="battle">
        <div class="side{' is-win' if dom_win else ''}">
          <div class="side-head"><span class="store {d['dom_key']}">{t['dom_store']}</span>{win_tag if dom_win else ''}</div>
          <span class="perk">{_esc(t['dom_perk'])}</span>
          <span class="price">{_money(d['dom'], lang)}</span>
          <span class="side-meta num">{t['off_msrp']} −{d['dom_off']}%</span>
        </div>
        <div class="side{' is-win' if not dom_win else ''}">
          <div class="side-head"><span class="store ali">{t['ali_store']}</span>{win_tag if not dom_win else ''}</div>
          <span class="perk">{_esc(t['ali_perk'])}</span>
          <span class="price">{_money(d['ali'], lang)}</span>
          <span class="side-meta num">{t['off_msrp']} −{d['ali_off']}%</span>
          {customs}
        </div>
      </div>"""


def _search_blob(it: dict, lang: str) -> str:
    parts = [it["brand"], it["model"], it["ko"]["title"], it["en"]["title"],
             _cat_label(it["category"], lang), *map(str, it.get("specs", {}).values())]
    return _esc(unicodedata.normalize("NFKC", " ".join(parts)).lower())


def _data_attrs(it: dict, d: dict, lang: str) -> str:
    """Facet/sort keys read by app.js. `data-q` leads with brand + model, so it doubles as the name sort key."""
    duty = f' data-d="{1 if d["duty_free"] else 0}"' if lang == "ko" else ""
    return (
        f'data-c="{_esc(it["category"])}" data-b="{_esc(it["brand"])}" data-r="{"ali" if d["direct_pick"] else "dom"}"{duty} '
        f'data-pb="{d["bracket"]}" data-save="{d["diff"]:.2f}" data-pct="{d["pct"]:.1f}" data-price="{d["best"]:.2f}" '
        f'data-q="{_search_blob(it, lang)}"'
    )


# --------------------------------------------------------------------------------------
# Page shell
# --------------------------------------------------------------------------------------


def _head(*, lang: str, title: str, description: str, up: str, cfg: dict, path: str, alternates: dict | None) -> str:
    base = cfg["site"]["base_url"].rstrip("/")
    alt = ""
    if alternates:
        alt = "".join(
            f'\n  <link rel="alternate" hreflang="{h}" href="{_esc(base + p)}">' for h, p in alternates.items()
        )
    p_verify = (cfg.get("site", {}).get("pinterest_verify_code") or "").strip()
    p_meta = f'\n  <meta name="p:domain_verify" content="{_esc(p_verify)}">' if p_verify else ""
    g_verify = (cfg.get("site", {}).get("google_verify_code") or "").strip()
    g_meta = f'\n  <meta name="google-site-verification" content="{_esc(g_verify)}">' if g_verify else ""
    rss_href = f"{base}/ko/feed.xml" if lang == "ko" else f"{base}/en/pinterest-feed.xml"
    rss_link = f'\n  <link rel="alternate" type="application/rss+xml" title="{_esc(cfg["site"]["brand_name"])} RSS" href="{_esc(rss_href)}">'
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(description)}">
  <meta name="theme-color" content="#FFFFFF">{p_meta}{g_meta}{rss_link}
  <script>document.documentElement.classList.add('js')</script>
  <link rel="canonical" href="{_esc(base + path)}">{alt}
  <meta property="og:title" content="{_esc(title)}">
  <meta property="og:description" content="{_esc(description)}">
  <meta property="og:url" content="{_esc(base + path)}">
  <meta property="og:type" content="website">
  <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
  <link rel="stylesheet" href="{FONT_CSS_URL}">
  <link rel="stylesheet" href="{up}assets/style.css">
</head>"""


def _legal_strip(lang: str) -> str:
    t = T[lang]
    return (
        f'<div class="legal-strip" role="note"><div class="wrap"><span class="legal-tag">{t["legal_tag"]}</span>'
        f'<span>{_esc(t["disclosure"])}</span></div></div>'
    )


def _site_header(lang: str, up: str, cfg: dict, switch_href: str) -> str:
    t = T[lang]
    brand = _esc(cfg["site"]["brand_name"])
    tg = _esc(cfg["site"]["telegram_channel_ko" if lang == "ko" else "telegram_channel_en"])
    return f"""<header class="site-head">
    <div class="wrap">
      <a class="brand" href="{up}{lang}/" aria-label="{brand} {t['region']}">{BRAND_MARK}<span class="brand-name">{brand}</span><span class="brand-region">{t['region']}</span></a>
      <nav class="head-nav" aria-label="{'주요 메뉴' if lang == 'ko' else 'Primary'}">
        <a href="{switch_href}" hreflang="{'en' if lang == 'ko' else 'ko'}">{t['switch']}</a>
        <a href="{up}policy/">{t['policy']}</a>
        <a class="tg" href="{tg}" target="_blank" rel="noopener" aria-label="{t['tg_long']}">{_icon('send', 15)}<span class="lbl-tg">{t['tg']}</span></a>
      </nav>
    </div>
  </header>"""


def _site_footer(lang: str, up: str, cfg: dict) -> str:
    brand = _esc(cfg["site"]["brand_name"])
    year = datetime.now(timezone.utc).year
    if lang == "ko":
        note = "표기 가격은 수집 시점 기준이며 판매처 사정에 따라 변동될 수 있습니다. 최종 결제 전 판매 페이지의 가격·옵션·배송비를 확인하세요."
        links = f'<a href="{up}ko/">한국어 허브</a><a href="{up}en/">Global Hub</a><a href="{up}policy/">개인정보처리방침·대가성 고지</a>'
    else:
        note = "Prices reflect the time of collection and may change at the retailer. Always confirm price, variant, and shipping on the store page before checkout."
        links = f'<a href="{up}en/">Global Hub</a><a href="{up}ko/">한국어 허브</a><a href="{up}policy/">Privacy &amp; affiliate policy</a>'
    return f"""<footer class="site-foot">
    <div class="wrap">
      <p>© {year} {brand}. {_esc(note)}</p>
      <nav class="foot-links" aria-label="Footer">{links}</nav>
    </div>
  </footer>"""


# --------------------------------------------------------------------------------------
# Index pages (/ko/, /en/, /ko/c/<cat>/, /en/c/<cat>/)
# --------------------------------------------------------------------------------------


HUB = {
    "ko": {
        "h1": "PC·데스크 주변기기 국내가 · 직구가 시세표",
        "h1_cat": "{cat} 국내가 · 직구가 시세표",
        "title": "{brand} KR — PC·데스크 주변기기 국내가 vs 직구가 비교",
        "title_cat": "{cat} 쿠팡 vs 알리 직구 가격 비교 ({n}종) | {brand}",
        "desc": "동일 모델 PC·데스크 주변기기 {n}종의 쿠팡 가격, 알리익스프레스 직구가, 가격차, 관부가세 대상 여부를 분류·브랜드·가격대별로 정리한 시세표.",
        "desc_cat": "{cat} {n}개 모델의 쿠팡 가격과 알리익스프레스 직구가, 가격차, 관부가세 대상 여부 비교표. 수록 브랜드: {brands}.",
        "stamp": '<span>기준일 <b class="num">{date}</b></span><span>쿠팡 · 알리익스프레스 동일 모델</span><span>면세 한도 미화 {limit}달러</span>',
        "dom_short": "쿠팡",
        "ali_short": "알리",
        "summary_lbl": "요약 지표",
        "m_models": "등록 모델",
        "m_models_v": "{k}<small>종</small>",
        "m_models_sub": "{c}개 분류 · {b}개 브랜드",
        "m_models_sub_cat": "{b}개 브랜드 · 전체 {t}종 중",
        "m_share_v": "{k}<small>종 · {p}%</small>",
        "m_direct": "알리 직구 유리",
        "m_direct_sub": "평균 차액 {avg} · 15% 이상 저렴",
        "m_local": "쿠팡 정발 유리",
        "m_local_sub": "국내가 더 저렴 {a}종 · 차액 15% 미만 {b}종",
        "m_none": "해당 모델 없음",
        "m_filter": "수집·오매칭 필터",
        "m_filter_v": "케이스·단품 매물 제외",
        "m_filter_sub": "정가의 {r}% 미만 이상 저가 차단",
        "m_filter_sub_plain": "정가 대비 이상 저가 매물 차단",
        "tops": "가격차 상위 {n}",
        "tops_by": "할인율 기준",
        "cats": "분류",
        "filters": "필터",
        "close": "필터 닫기",
        "f_route": "구매 경로",
        "r_all": "전체",
        "r_ali": "알리 직구 유리",
        "r_ali_note": "15%+",
        "r_dom": "쿠팡 정발 유리",
        "duty": f"무관세 (${KR_CUSTOMS_LIMIT_USD} 이하)",
        "f_price": "가격대",
        "f_price_note": "최저가 기준",
        "f_brand": "브랜드",
        "brand_more": "브랜드 전체 보기 (+{n})",
        "brand_less": "상위 브랜드만 보기",
        "search_lbl": "모델 검색",
        "search_ph": "모델명, 브랜드, 스펙 검색 (예: CD226, 100W, F75)",
        "sort_lbl": "정렬",
        "sorts": [("save", "가격차(절약액) 큰순"), ("pct", "할인율 높은순"), ("price", "낮은 가격순"), ("name", "브랜드·모델명순")],
        "view_lbl": "보기 방식",
        "views": [("list", "리스트", "시세표 리스트 뷰"), ("cards", "카드", "2열 카드 뷰")],
        "list_h": "모델 목록",
        "more_btn": "단점·요약",
        "con": "단점 체크",
        "verdict": "구매 판단",
        "detail": "상세 페이지",
        "call_ali": "알리 직구 유리",
        "call_dom": "쿠팡 정발 추천",
        "why_gap": "차액 15% 미만",
        "why_dom": "국내가가 더 저렴",
        "why_same": "가격 동일",
        "at_msrp": "정가와 동일",
        "duty_badge": f"${KR_CUSTOMS_LIMIT_USD} 초과 · 관부가세",
        "empty_t": "조건에 맞는 모델이 없습니다",
        "empty_d": "검색어를 줄이거나 적용 중인 필터를 해제하세요.",
        "reset": "필터 초기화",
        "js": {
            "status": "<strong>{a}–{b}</strong> / 총 <strong>{n}</strong>개 모델 표시 중",
            "statusOf": " · 전체 {t}개",
            "statusNone": "표시할 모델 없음 · 전체 {t}개",
            "more": "더보기 (+{k}개 · 남은 {r}개)",
            "all": "전체 보기 ({n}개)",
            "apply": "{n}개 모델 보기",
            "q": "검색: {q}",
            "remove": "{x} 필터 해제",
            "clear": "모두 해제",
        },
    },
    "en": {
        "h1": "Desk & USB-C Hardware Price Index",
        "h1_cat": "{cat} Price Index",
        "title": "{brand} — Desk & USB-C Hardware Price Index (Amazon vs AliExpress)",
        "title_cat": "{cat} Price Index — Amazon vs AliExpress ({n} models) | {brand}",
        "desc": "Model-for-model price index of {n} desk and USB-C hardware models: Amazon US vs. AliExpress direct prices, spreads, and the cheaper route by category, brand, and price range.",
        "desc_cat": "Amazon US vs. AliExpress direct prices, spreads, and the cheaper route for {n} {cat} models. Brands: {brands}.",
        "stamp": '<span>Updated <b class="num">{date}</b></span><span>Amazon US vs. AliExpress direct (USD)</span>',
        "dom_short": "Amazon",
        "ali_short": "Ali",
        "summary_lbl": "Summary",
        "m_models": "Tracked models",
        "m_models_v": "{k}",
        "m_models_sub": "{c} categories · {b} brands",
        "m_models_sub_cat": "{b} brands · of {t} tracked",
        "m_share_v": "{k}<small>· {p}%</small>",
        "m_direct": "AliExpress cheaper",
        "m_direct_sub": "Avg. gap {avg} · 15%+ below Amazon",
        "m_local": "Amazon preferred",
        "m_local_sub": "{a} cheaper on Amazon · {b} under 15% gap",
        "m_none": "No models",
        "m_filter": "Listing filter",
        "m_filter_v": "Accessory-only listings excluded",
        "m_filter_sub": "Blocks prices under {r}% of MSRP",
        "m_filter_sub_plain": "Blocks outlier prices far below MSRP",
        "tops": "Top {n} spreads",
        "tops_by": "by % gap",
        "cats": "Categories",
        "filters": "Filters",
        "close": "Close filters",
        "f_route": "Best route",
        "r_all": "All",
        "r_ali": "AliExpress cheaper",
        "r_ali_note": "15%+",
        "r_dom": "Amazon preferred",
        "duty": "",
        "f_price": "Price range",
        "f_price_note": "lowest price",
        "f_brand": "Brand",
        "brand_more": "All brands (+{n})",
        "brand_less": "Top brands only",
        "search_lbl": "Search models",
        "search_ph": "Search brand, model number, or spec (e.g. CD226, 100W, QMK)",
        "sort_lbl": "Sort",
        "sorts": [("save", "Largest spread ($)"), ("pct", "Highest % gap"), ("price", "Lowest price"), ("name", "Brand · model A–Z")],
        "view_lbl": "View",
        "views": [("list", "List", "Index list view"), ("cards", "Cards", "2-column card view")],
        "list_h": "Models",
        "more_btn": "Caveats",
        "con": "Caveats",
        "verdict": "Verdict",
        "detail": "Full details",
        "call_ali": "AliExpress cheaper",
        "call_dom": "Amazon preferred",
        "why_gap": "Gap under 15%",
        "why_dom": "Lower on Amazon",
        "why_same": "Same price",
        "at_msrp": "At MSRP",
        "duty_badge": "",
        "empty_t": "No models match these filters",
        "empty_d": "Shorten the query or remove an active filter.",
        "reset": "Reset filters",
        "js": {
            "status": "Showing <strong>{a}–{b}</strong> of <strong>{n}</strong> models",
            "statusOf": " · {t} total",
            "statusNone": "No models to show · {t} total",
            "more": "Load {k} more ({r} remaining)",
            "all": "Show all {n}",
            "apply": "View {n} models",
            "q": "Search: {q}",
            "remove": "Remove filter: {x}",
            "clear": "Clear all",
        },
    },
}


def _region_summary(items: list[dict], lang: str) -> dict:
    deals = [(it, _deal(it, lang)) for it in items]
    if not deals:
        return {"count": 0, "avg": 0.0, "top": None, "top_deal": None, "ranked": []}
    avg = sum((d["dom"] - d["ali"]) / d["dom"] * 100 for _, d in deals) / len(deals)
    ali_side = [x for x in deals if x[1]["ali_wins"]]
    top = max(ali_side, key=lambda x: x[1]["diff"]) if ali_side else None
    ranked = sorted(deals, key=lambda x: x[1]["diff"], reverse=True)
    return {"count": len(deals), "avg": avg, "top": top[0] if top else None,
            "top_deal": top[1] if top else None, "ranked": ranked}


def _cat_slug(cat: str) -> str:
    return product_slug(cat)


def _ranked(counts: Counter) -> list[str]:
    """Keys by descending count, then alphabetically."""
    return sorted(counts, key=lambda k: (-counts[k], k.lower()))


def _sku(it: dict) -> str:
    """Manufacturer code when the model string carries one, e.g. '(CD226)'; otherwise the short model name."""
    for group in reversed(re.findall(r"\(([^)]*)\)", it["model"])):
        for token in reversed(group.split(",")):
            if _SKU_RE.match(token.strip()):
                return token.strip()
    short = _short_name(it)
    return short[len(it["brand"].strip()):].strip() or short


def _off_text(off: int, lang: str) -> str:
    label = T[lang]["msrp"]
    if off > 0:
        return f"{label} −{off}%"
    if off < 0:
        return f"{label} +{-off}%"
    return HUB[lang]["at_msrp"]


def _signed_gap(d: dict, lang: str) -> tuple[str, str]:
    """AliExpress price relative to the domestic store: negative means direct import is cheaper."""
    sign = "−" if d["ali"] < d["dom"] else "+" if d["ali"] > d["dom"] else ""
    return f'{sign}{_money(d["diff"], lang, False)}', f'{sign}{d["pct"]:.0f}%'


def _route_call(d: dict, lang: str) -> tuple[str, str, str]:
    h = HUB[lang]
    if d["direct_pick"]:
        return "is-ali", h["call_ali"], ""
    why = h["why_gap"] if d["ali_wins"] else h["why_same"] if d["diff"] == 0 else h["why_dom"]
    return "is-local", h["call_dom"], why


def _render_row(it: dict, lang: str, pfx: str) -> str:
    """One catalog entry. The same markup is laid out as a ledger row or a card purely in CSS."""
    t, h, d, loc = T[lang], HUB[lang], _deal(it, lang), it[lang]
    slug = product_slug(it["id"])
    href = f"{pfx}{slug}/"
    name = _esc(_short_name(it))
    spec_vals = [v for v in it.get("specs", {}).values() if str(v).strip()][:3]
    specs = "".join(f"<span>{_esc(_chip_text(v, 34))}</span>" for v in spec_vals)
    dom_win = not d["ali_wins"]
    gap, pct = _signed_gap(d, lang)
    cls, call, why = _route_call(d, lang)
    why_html = f'<span class="why">{_esc(why)}</span>' if why else ""
    duty = f'<span class="duty">{_esc(h["duty_badge"])}</span>' if d["customs"] else ""
    cons = "".join(f"<dd>{_esc(c)}</dd>" for c in loc.get("cons", [])[:2])

    def price(area: str, store_cls: str, store: str, val: float, off: int, win: bool, extra: str = "") -> str:
        lead = f'<b>{t["win"]}</b> · ' if win else ""
        return (
            f'<div class="r-price r-{area}{" is-win" if win else ""}"><span class="store {store_cls}">{store}</span>'
            f'<span class="amt num">{_money(val, lang, False)}</span>'
            f'<span class="r-off num">{lead}{_off_text(off, lang)}</span>{extra}</div>'
        )

    def buy(store_cls: str, url: str, label: str, pick: bool) -> str:
        return (
            f'<a class="buy {store_cls}{" is-pick" if pick else ""}" href="{_esc(url)}" target="_blank" '
            f'rel="nofollow sponsored noopener" aria-label="{label} · {name}">{label} {_use("out", 13)}</a>'
        )

    return f"""
        <li class="row" {_data_attrs(it, d, lang)}>
          <div class="r-info">
            <p class="r-meta">{_esc(_cat_label(it['category'], lang))} · {_esc(it['brand'])}</p>
            <h3 class="r-title"><a href="{href}">{_esc(loc['title'])}</a></h3>
            <p class="r-spec"><b>{_esc(_sku(it))}</b>{specs}</p>
          </div>
          {price('dom', d['dom_key'], h['dom_short'], d['dom'], d['dom_off'], dom_win)}
          {price('ali', 'ali', h['ali_short'], d['ali'], d['ali_off'], not dom_win, duty)}
          <div class="r-verd {cls}"><span class="gap num">{gap}<small>{pct}</small></span><span class="call">{_esc(call)}</span>{why_html}</div>
          <div class="r-act">
            {buy(d['dom_key'], d['dom_url'], h['dom_short'], not d['direct_pick'])}
            {buy('ali', d['ali_url'], h['ali_short'], d['direct_pick'])}
            <button type="button" class="r-more" data-more aria-expanded="false" aria-controls="d-{slug}">{h['more_btn']} {_use('down')}</button>
          </div>
          <div class="drawer" id="d-{slug}"><div class="drawer-in"><div class="drawer-box">
            <dl><div class="cons"><dt>{h['con']}</dt>{cons}</div><div><dt>{h['verdict']}</dt><dd>{_esc(loc['verdict'])}</dd></div></dl>
            <a class="drawer-link" href="{href}">{h['detail']} {_use('arrow')}</a>
          </div></div></div>
        </li>"""


def _opt(kind: str, attrs: str, label: str, key: str, count: int, cls: str = "") -> str:
    return (
        f'<label class="opt{cls}"><input type="{kind}" {attrs}><span class="lbl">{label}</span>'
        f'<span class="num" data-n="{_esc(key)}">{count}</span></label>'
    )


def _render_summary(deals: list[tuple[dict, dict]], cfg: dict, lang: str, models_sub: str) -> str:
    h = HUB[lang]
    n = len(deals)
    direct = [d for _, d in deals if d["direct_pick"]]
    local = [d for _, d in deals if not d["direct_pick"]]
    dom_cheaper = sum(1 for d in local if not d["ali_wins"])

    def share(k: int) -> str:
        return h["m_share_v"].format(k=k, p=round(k / n * 100) if n else 0)

    direct_sub = (
        h["m_direct_sub"].format(avg=f'<b class="num">{_money(sum(d["diff"] for d in direct) / len(direct), lang, False)}</b>')
        if direct else h["m_none"]
    )
    local_sub = h["m_local_sub"].format(a=dom_cheaper, b=len(local) - dom_cheaper) if local else h["m_none"]
    ratio = cfg.get("gatekeeper", {}).get("min_price_ratio_vs_msrp")
    filter_sub = h["m_filter_sub"].format(r=round(float(ratio) * 100)) if ratio else h["m_filter_sub_plain"]
    dom_key = "coupang" if lang == "ko" else "amazon"
    return f"""
      <div class="sm"><dt>{h['m_models']}</dt><dd><span class="sm-v num">{h['m_models_v'].format(k=n)}</span><span class="sm-s">{models_sub}</span></dd></div>
      <div class="sm"><dt><span class="store ali">{h['m_direct']}</span></dt><dd><a href="?route=ali" data-route-link="ali"><span class="sm-v num">{share(len(direct))}</span></a><span class="sm-s">{direct_sub}</span></dd></div>
      <div class="sm"><dt><span class="store {dom_key}">{h['m_local']}</span></dt><dd><a href="?route=dom" data-route-link="dom"><span class="sm-v num">{share(len(local))}</span></a><span class="sm-s num">{local_sub}</span></dd></div>
      <div class="sm"><dt>{h['m_filter']}</dt><dd><span class="sm-v is-text">{_esc(h['m_filter_v'])}</span><span class="sm-s num">{_esc(filter_sub)}</span></dd></div>"""


def _render_tops(deals: list[tuple[dict, dict]], lang: str, pfx: str) -> str:
    """Largest spreads by percentage: a different cut from the default amount-sorted list below it."""
    h = HUB[lang]
    if len(deals) < TOPS_MIN_ITEMS:
        return ""
    top = sorted(deals, key=lambda x: x[1]["pct"], reverse=True)[:4]
    cells = []
    for it, d in top:
        pct = _signed_gap(d, lang)[1]
        cells.append(
            f'<li><a href="{pfx}{product_slug(it["id"])}/"><span class="tops-name">{_esc(_short_name(it))}</span>'
            f'<span class="tops-pct num {"is-ali" if d["ali_wins"] else "is-local"}">{pct}</span>'
            f'<span class="tops-sub num">{h["dom_short"]} {_money(d["dom"], lang, False)} · '
            f'{h["ali_short"]} {_money(d["ali"], lang, False)}</span></a></li>'
        )
    return (
        f'<section class="tops" aria-labelledby="tops-h" style="--n:{len(top)}"><h2 id="tops-h">{h["tops"].format(n=len(top))}'
        f'<small>{h["tops_by"]}</small></h2><ol>{"".join(cells)}</ol></section>'
    )


def _render_facets(deals: list[tuple[dict, dict]], lang: str) -> str:
    h = HUB[lang]
    n = len(deals)
    n_direct = sum(1 for _, d in deals if d["direct_pick"])
    note = f' <small>{h["r_ali_note"]}</small>'
    route = [
        _opt("radio", 'name="route" value="all" checked', h["r_all"], "route:all", n),
        _opt("radio", 'name="route" value="ali"', h["r_ali"] + note, "route:ali", n_direct),
        _opt("radio", 'name="route" value="dom"', h["r_dom"], "route:dom", n - n_direct),
    ]
    if lang == "ko":
        n_duty = sum(1 for _, d in deals if d["duty_free"])
        route.append(_opt("checkbox", "data-duty", _esc(h["duty"]), "duty:1", n_duty, " opt-sep"))

    per_bracket = [0] * len(_PRICE_BRACKETS[lang])
    for _, d in deals:
        per_bracket[d["bracket"]] += 1
    price = [
        _opt("checkbox", f'data-f="price" value="{i}"', _esc(label), f"price:{i}", per_bracket[i])
        for i, (_, label) in enumerate(_PRICE_BRACKETS[lang])
    ]

    per_brand = Counter(it["brand"] for it, _ in deals)
    ranked = _ranked(per_brand)
    brands = [
        _opt("checkbox", f'data-f="brand" value="{_esc(b)}"', _esc(b), f"brand:{b}", per_brand[b],
             " is-extra" if i >= TOP_BRANDS else "")
        for i, b in enumerate(ranked)
    ]
    extra = len(ranked) - TOP_BRANDS
    more = (
        f'<button type="button" class="facet-more" data-brand-more aria-expanded="false" '
        f'data-label-more="{_esc(h["brand_more"].format(n=extra))}" data-label-less="{_esc(h["brand_less"])}">'
        f'{_esc(h["brand_more"].format(n=extra))}</button>'
        if extra > 0 else ""
    )
    return f"""
            <fieldset class="facet"><legend>{h['f_route']}</legend>{''.join(route)}</fieldset>
            <fieldset class="facet"><legend>{h['f_price']} <small>{h['f_price_note']}</small></legend>{''.join(price)}</fieldset>
            <fieldset class="facet" data-brands><legend>{h['f_brand']}</legend><div class="opts">{''.join(brands)}</div>{more}</fieldset>"""


def _render_hub(items: list[dict], cfg: dict, lang: str, cat: str | None = None,
                all_items: list[dict] | None = None) -> str:
    """Faceted index. With `cat`, renders the static category landing page scoped to `items` of that category."""
    t, h = T[lang], HUB[lang]
    other = "en" if lang == "ko" else "ko"
    brand = cfg["site"]["brand_name"]
    all_items = items if all_items is None else all_items
    deals = sorted(((it, _deal(it, lang)) for it in items), key=lambda x: x[1]["diff"], reverse=True)
    n = len(deals)
    latest = max((it.get("updated_at", "") for it in items), default="")
    cat_counts = Counter(it["category"] for it in all_items)
    cats = sorted(cat_counts, key=lambda c: (-cat_counts[c], _cat_label(c, lang)))
    per_brand = Counter(it["brand"] for it in items)

    if cat is None:
        up, pfx, cat_pfx, all_href, path = "../", "p/", "c/", "./", f"/{lang}/"
        switch = f"{up}{other}/"
        alternates = {"ko": "/ko/", "en": "/en/", "x-default": "/"}
        title, desc, h1 = h["title"].format(brand=brand), h["desc"].format(n=n), h["h1"]
        models_sub = h["m_models_sub"].format(c=len(cats), b=len(per_brand))
        crumbs = ""
    else:
        slug, label = _cat_slug(cat), _cat_label(cat, lang)
        up, pfx, cat_pfx, all_href, path = "../../../", "../../p/", "../", "../../", f"/{lang}/c/{slug}/"
        switch = f"{up}{other}/c/{slug}/"
        alternates = {"ko": f"/ko/c/{slug}/", "en": f"/en/c/{slug}/"}
        title = h["title_cat"].format(cat=label, n=n, brand=brand)
        desc = h["desc_cat"].format(cat=label, n=n, brands=", ".join(_ranked(per_brand)[:6]))
        h1 = h["h1_cat"].format(cat=label)
        models_sub = h["m_models_sub_cat"].format(b=len(per_brand), t=len(all_items))
        crumbs = (
            f'<nav aria-label="{"이동 경로" if lang == "ko" else "Breadcrumb"}"><ol class="crumbs">'
            f'<li><a href="{all_href}">{t["home"]}</a></li><li>{_icon("chev", 14)}</li>'
            f'<li aria-current="page">{_esc(label)}</li></ol></nav>'
        )

    # Hub: category links filter in place (app.js) and fall back to the static pages. Category page: plain links.
    if cat is None:
        cat_links = [
            f'<li><a href="{all_href}" data-cat="all" aria-current="true">{_esc(_cat_label("all", lang))} '
            f'<span class="num" data-n="cat:all">{n}</span></a></li>'
        ]
        cat_links += [
            f'<li><a href="{cat_pfx}{_cat_slug(c)}/" data-cat="{_esc(c)}">{_esc(_cat_label(c, lang))} '
            f'<span class="num" data-n="cat:{_esc(c)}">{cat_counts[c]}</span></a></li>'
            for c in cats
        ]
    else:
        cat_links = [
            f'<li><a href="{all_href}">{_esc(_cat_label("all", lang))} <span class="num">{len(all_items)}</span></a></li>'
        ]
        current = ' aria-current="page"'
        cat_links += [
            f'<li><a href="{cat_pfx}{_cat_slug(c)}/"{current if c == cat else ""}>'
            f'{_esc(_cat_label(c, lang))} <span class="num">{cat_counts[c]}</span></a></li>'
            for c in cats
        ]

    sort_html = "".join(f'<option value="{k}">{_esc(v)}</option>' for k, v in h["sorts"])
    view_html = "".join(
        f'<button type="button" data-view-btn="{k}" aria-pressed="{"true" if k == "list" else "false"}" title="{_esc(tip)}">'
        f'{_icon(k, 15)}<span class="lbl">{_esc(v)}</span></button>'
        for k, v, tip in h["views"]
    )
    strings = dict(h["js"])
    strings.update({
        "cats": {c: _cat_label(c, lang) for c in cats},
        "route": {"ali": h["r_ali"], "dom": h["r_dom"]},
        "duty": h["duty"],
        "price": [label for _, label in _PRICE_BRACKETS[lang]],
    })
    i18n = json.dumps(strings, ensure_ascii=False).replace("</", "<\\/")
    stamp = h["stamp"].format(date=_esc(latest), limit=KR_CUSTOMS_LIMIT_USD)

    body = f"""
<body class="{lang} is-hub">
  {_legal_strip(lang)}
  {_site_header(lang, up, cfg, switch)}
  {ICON_SPRITE}
  <main class="wrap hub" data-hub data-view="list" data-scope="{_esc(cat or 'all')}" data-page-size="{PAGE_SIZE}">
    {crumbs}
    <header class="idx-head">
      <h1>{_esc(h1)}</h1>
      <p class="stamp">{stamp}</p>
    </header>
    <dl class="summary" aria-label="{h['summary_lbl']}">{_render_summary(deals, cfg, lang, models_sub)}
    </dl>
    {_render_tops(deals, lang, pfx)}

    <div class="work" id="index">
      <div class="side-col">
        <nav class="catnav" aria-labelledby="cat-h">
          <h2 class="facet-h" id="cat-h">{h['cats']}</h2>
          <ul>{''.join(cat_links)}</ul>
        </nav>
        <aside class="facets" id="facets" aria-label="{h['filters']}" data-sheet>
          <div class="sheet-head"><strong>{h['filters']}</strong><button type="button" data-sheet-close aria-label="{h['close']}">{_icon('x', 18)}</button></div>
          <div class="facets-body">{_render_facets(deals, lang)}
          </div>
          <div class="sheet-foot"><button type="button" data-reset>{h['reset']}</button><button type="button" class="primary" data-sheet-apply></button></div>
        </aside>
      </div>

      <div class="main">
        <div class="bar">
          <label class="search"><span class="sr-only">{h['search_lbl']}</span>{_icon('search', 16)}<input type="search" data-search placeholder="{_esc(h['search_ph'])}" autocomplete="off" enterkeyhint="search"><kbd>/</kbd></label>
          <label class="sort"><span class="sr-only">{h['sort_lbl']}</span><select data-sort>{sort_html}</select>{_icon('down', 15)}</label>
          <button type="button" class="fbtn" data-sheet-open aria-controls="facets">{_icon('filter', 16)}<span>{h['filters']}</span><b class="num" data-fcount hidden>0</b></button>
        </div>
        <div class="status">
          <p class="status-text num" data-status aria-live="polite"></p>
          <div class="on-chips" data-chips></div>
          <div class="seg" role="group" aria-label="{h['view_lbl']}">{view_html}</div>
        </div>
        <h2 class="sr-only">{h['list_h']}</h2>
        <ol class="rows" data-rows>{''.join(_render_row(it, lang, pfx) for it, _ in deals)}
        </ol>
        <div class="empty" data-empty hidden><strong>{h['empty_t']}</strong>{h['empty_d']}<br><button type="button" data-reset>{h['reset']}</button></div>
        <div class="pager"><p class="pager-status num" data-status></p><button type="button" class="primary" data-load></button><button type="button" data-all></button></div>
      </div>
    </div>
    <div class="scrim" data-scrim></div>
    <template data-x>{_icon('x', 13)}</template>
    <script type="application/json" data-i18n>{i18n}</script>
  </main>
  {_site_footer(lang, up, cfg)}
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    return _head(lang=lang, title=title, description=desc, up=up, cfg=cfg, path=path, alternates=alternates) + body


def _render_ko_index(items: list[dict], cfg: dict) -> str:
    return _render_hub(items, cfg, "ko")


def _render_en_index(items: list[dict], cfg: dict) -> str:
    return _render_hub(items, cfg, "en")


# --------------------------------------------------------------------------------------
# Detail pages (/ko/p/<slug>/, /en/p/<slug>/)
# --------------------------------------------------------------------------------------


def _related(it: dict, items: list[dict], n: int = 3) -> list[dict]:
    others = [x for x in items if x["id"] != it["id"]]
    same = [x for x in others if x["category"] == it["category"]]
    rest = sorted((x for x in others if x["category"] != it["category"]),
                  key=lambda x: x["metrics"]["kr_savings_pct"], reverse=True)
    return (same + rest)[:n]


def _render_detail_page(it: dict, lang: str, cfg: dict, items: list[dict] | None = None) -> str:
    t, d, loc = T[lang], _deal(it, lang), it[lang]
    brand = cfg["site"]["brand_name"]
    up = "../../../"
    slug = product_slug(it["id"])
    other = "en" if lang == "ko" else "ko"
    cat = it["category"]

    spec_rows = "".join(
        f'<tr><th scope="row">{_esc(_spec_label(k, lang))}</th><td>{_esc(v)}</td></tr>'
        for k, v in it.get("specs", {}).items()
    )
    pros_li = "".join(f"<li>{_esc(x)}</li>" for x in loc.get("pros", []))
    cons_li = "".join(f"<li>{_esc(x)}</li>" for x in loc.get("cons", []))

    def bar(name: str, val: float, cls: str, sub: str) -> str:
        width = max(4.0, min(100.0, val / d["msrp"] * 100)) if d["msrp"] > 0 else 100.0
        return (
            f'<div class="bar-row"><span class="bar-name">{name}</span>'
            f'<div class="bar-track"><div class="bar-fill {cls}" style="width:{width:.1f}%"></div></div>'
            f'<span class="bar-val">{_money(val, lang, False)}<small>{sub}</small></span></div>'
        )

    win_dom = not d["ali_wins"]
    bars = "".join([
        bar(t["msrp"], d["msrp"], "msrp", "권장소비자가" if lang == "ko" else "list price"),
        bar(t["dom_store"], d["dom"], "win" if win_dom else "", f"−{d['dom_off']}%"),
        bar(t["ali_store"] if lang == "en" else "알리 직구", d["ali"], "" if win_dom else "win", f"−{d['ali_off']}%"),
    ])
    cheaper_name = t["dom_store"] if win_dom else (t["ali_store"] if lang == "en" else "알리 직구")

    if lang == "ko":
        facts = f"""
          <div class="fact"><span>가격 차이</span><strong>{_money(d['diff'], lang, False)} <small class="num" style="font-size:.8em;color:var(--muted)">({d['pct']:.1f}%)</small></strong></div>
          <div class="fact"><span>더 싼 곳</span><strong>{cheaper_name}</strong></div>
          <div class="fact"><span>정가 대비 최저가</span><strong>−{d['off']:.1f}%</strong></div>"""
        customs_note = (
            f'<div class="customs-note"><strong>⚠️ 관부가세</strong><span>알리 결제 예상가 ${d["ali_usd"]:,.2f}로 개인 직구 면세 한도(${KR_CUSTOMS_LIMIT_USD})를 넘습니다. '
            f'통관 시 관세·부가세가 부과될 수 있으니 실제 부담액을 포함해 쿠팡가와 비교하세요.</span></div>'
            if d["customs"] else ""
        )
        title = f"{loc['title']} — 쿠팡 vs 알리 직구 가격·단점 비교 | {brand}"
        h_price, h_spec, h_pc = "정가 vs 현재 가격", "전체 기술 사양", "장점과 실사용 단점"
        pros_h, cons_h = "장점", "구매 전 꼭 확인할 단점"
        rel_h, decide_h = "함께 검수한 다른 기어", "구매 판단"
        stamp = f"가격 기준일 {_esc(it.get('updated_at', ''))} · 결제 전 판매 페이지에서 최종가를 확인하세요."
        switch = f"English page {_icon('arrow', 14)}"
    else:
        facts = f"""
          <div class="fact"><span>Price spread</span><strong>{_money(d['diff'], lang)} <small class="num" style="font-size:.8em;color:var(--muted)">({d['pct']:.1f}%)</small></strong></div>
          <div class="fact"><span>Cheaper at</span><strong>{cheaper_name}</strong></div>
          <div class="fact"><span>Best price vs MSRP</span><strong>−{d['off']:.1f}%</strong></div>"""
        customs_note = ""
        title = f"{loc['title']} — Amazon vs AliExpress Price & Review | {brand}"
        h_price, h_spec, h_pc = "MSRP vs. current prices", "Technical specifications", "Strengths & real-world caveats"
        pros_h, cons_h = "Strengths", "Real-world caveats"
        rel_h, decide_h = "Other vetted gear", "Buying decision"
        stamp = f"Last checked {_esc(it.get('updated_at', ''))}. Confirm the final price on the store page."
        switch = f"한국어 페이지 {_icon('arrow', 14)}"

    related_html = ""
    rel_items = _related(it, items or [], 3)
    if rel_items:
        rel_cards = []
        for r in rel_items:
            rd = _deal(r, lang)
            rel_cards.append(f"""
        <article class="rel">
          <span class="tag" style="align-self:flex-start">{_esc(_cat_label(r['category'], lang))} · {_esc(r['brand'])}</span>
          <h3><a href="../{product_slug(r['id'])}/">{_esc(r[lang]['title'])}</a></h3>
          {_pick_short(rd, lang)}
          <div class="rel-prices"><span>{t['dom_store']} <b>{_money(rd['dom'], lang, False)}</b></span><span>{'알리' if lang == 'ko' else 'Ali'} <b>{_money(rd['ali'], lang, False)}</b></span></div>
        </article>""")
        related_html = f'<section class="related" aria-labelledby="rel-h"><h2 id="rel-h">{rel_h}</h2><div class="rel-grid">{"".join(rel_cards)}</div></section>'

    body = f"""
<body class="{lang}">
  {_legal_strip(lang)}
  {_site_header(lang, up, cfg, f"{up}{other}/p/{slug}/")}
  <main class="wrap">
    <nav aria-label="{'이동 경로' if lang == 'ko' else 'Breadcrumb'}">
      <ol class="crumbs">
        <li><a href="../../">{t['home']}</a></li>
        <li>{_icon('chev', 14)}</li>
        <li><a href="../../c/{_cat_slug(cat)}/">{_esc(_cat_label(cat, lang))}</a></li>
        <li>{_icon('chev', 14)}</li>
        <li aria-current="page">{_esc(_short_name(it))}</li>
      </ol>
    </nav>

    <div class="detail">
      <header class="d-intro">
        <span class="tag">{_esc(it['brand'])} · {_esc(it['model'])}</span>
        <h1>{_esc(loc['title'])}</h1>
        <p class="dek">{_esc(loc['summary'])}</p>
        {_chips(it, 4)}
      </header>

      <aside class="d-aside" aria-label="{decide_h}">
        <div class="panel decide">
          <div class="decide-title">{decide_h}</div>
          {_pick_badge(d, lang)}
          <p class="decide-verdict">{_esc(loc['verdict'])}</p>
          {_battle(d, lang)}
          <div class="actions">
            {_ext(d['dom_url'], 'btn btn-' + d['dom_key'], ('쿠팡 최저가 확인' if lang == 'ko' else 'Check Amazon'))}
            {_ext(d['ali_url'], 'btn btn-ali', ('알리 직구가 확인' if lang == 'ko' else 'Check AliExpress'))}
          </div>
          <p class="decide-stamp">{stamp}</p>
          <a class="decide-switch" href="{up}{other}/p/{slug}/" hreflang="{other}">{switch}</a>
        </div>
      </aside>

      <div class="d-body">
        <section class="section" aria-labelledby="h-price">
          <h2 id="h-price">{h_price}</h2>
          <div class="panel">
            <div class="bars">{bars}</div>
            <div class="facts">{facts}
            </div>
            {customs_note}
          </div>
        </section>

        <section class="section" aria-labelledby="h-spec">
          <h2 id="h-spec">{h_spec}</h2>
          <div class="panel" style="overflow:hidden"><table class="spec-table"><tbody>{spec_rows}</tbody></table></div>
        </section>

        <section class="section" aria-labelledby="h-pc">
          <h2 id="h-pc">{h_pc}</h2>
          <div class="pc">
            <div class="panel pros"><h3>{pros_h}</h3><ul>{pros_li}</ul></div>
            <div class="panel cons"><h3>{cons_h}</h3><ul>{cons_li}</ul></div>
          </div>
        </section>
      </div>
    </div>

    {related_html}
  </main>
  {_site_footer(lang, up, cfg)}
</body>
</html>
"""
    head = _head(lang=lang, title=title, description=loc["summary"], up=up, cfg=cfg, path=f"/{lang}/p/{slug}/",
                 alternates={"ko": f"/ko/p/{slug}/", "en": f"/en/p/{slug}/"})
    return head + body


# --------------------------------------------------------------------------------------
# Gateway (/) and policy (/policy/)
# --------------------------------------------------------------------------------------


def _render_root_gateway(cfg: dict, items: list[dict] | None = None) -> str:
    items = items or []
    brand = _esc(cfg["site"]["brand_name"])
    panels = []
    for lang in ("ko", "en"):
        s = _region_summary(items, lang)
        top3 = "".join(
            f'<li><span>{_esc(_short_name(it))}</span><b>{_money(d["diff"], lang, False)}</b></li>'
            for it, d in s["ranked"][:3]
        )
        top_name = _esc(_short_name(s["top"])) if s["top"] else "—"
        if lang == "ko":
            head = f'<h2><a href="ko/" hreflang="ko">🇰🇷 한국어 허브</a></h2><p class="region-route">쿠팡 로켓배송 vs 알리익스프레스 직구 · 원화 기준</p>'
            stats = (f'<div><span>검수 통과</span><strong>{s["count"]}종</strong></div>'
                     f'<div><span>평균 직구 절약률</span><strong>{s["avg"]:.1f}%</strong></div>'
                     f'<div><span>최대 절약 픽</span><strong>{top_name}</strong></div>')
            cta, list_lbl = "한국어 비교표 열기", "가격 차이 큰 순"
        else:
            head = f'<h2><a href="en/" hreflang="en">🌐 Global Hub</a></h2><p class="region-route">Amazon Prime vs AliExpress direct · priced in USD</p>'
            stats = (f'<div><span>Vetted models</span><strong>{s["count"]}</strong></div>'
                     f'<div><span>Avg. Ali savings</span><strong>{s["avg"]:.1f}%</strong></div>'
                     f'<div><span>Biggest saving</span><strong>{top_name}</strong></div>')
            cta, list_lbl = "Open the global comparison", "Largest price gaps"
        panels.append(f"""
      <section class="region" data-region="{lang}">
        <div class="region-head"><div>{head}</div><span class="suggest" hidden>{'브라우저 언어 기준 추천' if lang == 'ko' else 'Suggested for you'}</span></div>
        <div class="region-stats">{stats}</div>
        <div><div class="kpi-label" style="margin-bottom:2px">{list_lbl}</div><ol class="top3">{top3}</ol></div>
        <span class="region-cta">{cta} {_icon('arrow', 16)}</span>
      </section>""")

    return f"""{_head(lang="en", title=f"{cfg['site']['brand_name']} — Desk & Tech Gear Price Intelligence (KR · Global)",
             description="Compare fast domestic delivery against direct-import prices on vetted desk and tech gear. Korean hub: Coupang vs AliExpress. Global hub: Amazon vs AliExpress.",
             up="", cfg=cfg, path="/", alternates={"ko": "/ko/", "en": "/en/", "x-default": "/"})}
<body>
  <header class="site-head">
    <div class="wrap">
      <a class="brand" href="./">{BRAND_MARK}<span>{brand}</span></a>
      <nav class="head-nav" aria-label="Primary"><a href="policy/">Policy · 정책</a></nav>
    </div>
  </header>
  <main class="wrap">
    <section class="gate-hero" style="padding:36px 0 22px;">
      <h1 style="font-size:clamp(1.6rem,1.2rem + 1.5vw,2.2rem);">{brand}</h1>
      <p>동일 모델 오픈마켓 · 해외직구 시세 비교 / Model-level domestic vs. direct-import price index</p>
    </section>
    <div class="regions">{''.join(panels)}
    </div>
  </main>
  <footer class="site-foot"><div class="wrap"><p>{_esc(DISCLOSURE_EN)}</p><nav class="foot-links" aria-label="Footer"><a href="ko/">한국어 허브</a><a href="en/">Global Hub</a><a href="policy/">Policy</a></nav></div></footer>
  <script>
    (function () {{
      var ko = (navigator.language || '').toLowerCase().indexOf('ko') === 0;
      var el = document.querySelector('[data-region="' + (ko ? 'ko' : 'en') + '"]');
      if (!el) return;
      el.classList.add('is-suggested');
      el.querySelector('.suggest').hidden = false;
    }})();
  </script>
</body>
</html>
"""


def _render_policy_page(cfg: dict) -> str:
    brand = _esc(cfg["site"]["brand_name"])
    return f"""{_head(lang="en", title=f"Privacy Policy & Affiliate Disclosure | {cfg['site']['brand_name']}",
             description="How GearCompare Hub earns affiliate commissions and what data third-party retailers may collect.",
             up="../", cfg=cfg, path="/policy/", alternates=None)}
<body>
  <header class="site-head">
    <div class="wrap">
      <a class="brand" href="../">{BRAND_MARK}<span>{brand}</span></a>
      <nav class="head-nav" aria-label="Primary"><a href="../ko/" hreflang="ko">🇰🇷 한국어 허브</a><a href="../en/" hreflang="en">🌐 Global Hub</a></nav>
    </div>
  </header>
  <main class="wrap">
    <article class="prose">
      <h1>Affiliate Disclosure &amp; Privacy Policy</h1>
      <p class="lead">{brand} is an independent price-comparison publication. Here is exactly how it is funded and what happens when you click a store link.</p>

      <h2>1. Affiliate disclosure</h2>
      <p>{_esc(DISCLOSURE_EN)}</p>
      <p>{brand} participates in the Amazon Services LLC Associates Program and the AliExpress Portals Affiliate Program, affiliate advertising programs designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com and AliExpress.com.</p>

      <section lang="ko">
        <h2>2. 제휴 마케팅 대가성 고지</h2>
        <p>{_esc(DISCLOSURE_KO)}</p>
        <p>모든 상품은 자동 검수(게이트키퍼)를 거쳐 액세서리 단품·이상 저가 매물을 걸러낸 뒤 게시되며, 각 상품마다 실사용 단점을 함께 표기합니다.</p>
      </section>

      <h2>3. Editorial process</h2>
      <p>Every listing passes an automated gatekeeper before publication: out-of-stock items, accessory-only matches, and prices abnormally far below MSRP are rejected, and each product must carry at least one honest drawback in both Korean and English.</p>

      <h2>4. Privacy &amp; cookies</h2>
      <p>{brand} is a static site and does not collect personal registration data, passwords, or payment details. When you click outbound retail links (Amazon, AliExpress, Coupang), those merchants may set standard affiliate attribution cookies under their own privacy policies. The hub remembers your preferred list/card view in your browser's local storage only.</p>
    </article>
  </main>
  <footer class="site-foot"><div class="wrap"><p>© {datetime.now(timezone.utc).year} {brand}</p><nav class="foot-links" aria-label="Footer"><a href="../ko/">한국어 허브</a><a href="../en/">Global Hub</a><a href="../">Home</a></nav></div></footer>
</body>
</html>
"""


def _render_sitemap(items: list[dict], cfg: dict) -> str:
    base = cfg["site"]["base_url"].rstrip("/")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [f"{base}/", f"{base}/ko/", f"{base}/en/", f"{base}/policy/"]
    for cat in sorted({it["category"] for it in items}):
        urls.append(f"{base}/ko/c/{_cat_slug(cat)}/")
        urls.append(f"{base}/en/c/{_cat_slug(cat)}/")
    for it in items:
        slug = product_slug(it["id"])
        urls.append(f"{base}/ko/p/{slug}/")
        urls.append(f"{base}/en/p/{slug}/")
    entries = "\n".join(
        f"  <url><loc>{_esc(u)}</loc><lastmod>{today}</lastmod></url>" for u in urls
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _clean_dist(dist_dir: Path) -> None:
    """Remove the previous build so stale `.html` files never linger."""
    target = dist_dir.resolve()
    if target == Path(target.anchor) or (target / "run_pipeline.py").exists() or (target / ".git").exists():
        raise ValueError(f"Refusing to wipe suspicious dist_dir: {target}")
    if not target.exists():
        return
    # Clear contents rather than the folder itself so a locked dist/ (e.g. a dev server cwd) still rebuilds.
    for child in target.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def build_site(approved_items: list[dict], cfg: dict, dist_dir: Path) -> dict:
    """Generate clean-URL static pages for root, /ko/, /en/, category indexes, product details, policy, and sitemap."""
    _clean_dist(dist_dir)

    css = SHARED_CSS.strip().replace("__PAGE_NEXT__", str(PAGE_SIZE + 1))
    _write(dist_dir / "assets" / "style.css", css + "\n")
    _write(dist_dir / "assets" / "app.js", APP_JS.strip() + "\n")
    _write(dist_dir / "index.html", _render_root_gateway(cfg, approved_items))
    _write(dist_dir / "policy" / "index.html", _render_policy_page(cfg))
    _write(dist_dir / "ko" / "index.html", _render_ko_index(approved_items, cfg))
    _write(dist_dir / "en" / "index.html", _render_en_index(approved_items, cfg))

    categories = sorted({it["category"] for it in approved_items})
    for cat in categories:
        scoped = [it for it in approved_items if it["category"] == cat]
        for lang in ("ko", "en"):
            _write(dist_dir / lang / "c" / _cat_slug(cat) / "index.html",
                   _render_hub(scoped, cfg, lang, cat=cat, all_items=approved_items))

    for item in approved_items:
        slug = product_slug(item["id"])
        _write(dist_dir / "ko" / "p" / slug / "index.html", _render_detail_page(item, "ko", cfg, approved_items))
        _write(dist_dir / "en" / "p" / slug / "index.html", _render_detail_page(item, "en", cfg, approved_items))

    _write(dist_dir / "sitemap.xml", _render_sitemap(approved_items, cfg))
    _write(dist_dir / ".nojekyll", "")

    return {
        "approved_products_rendered": len(approved_items),
        "total_html_pages": 4 + (len(categories) * 2) + (len(approved_items) * 2),
        "output_dir": str(dist_dir),
    }
