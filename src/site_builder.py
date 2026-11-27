"""Zero-dependency static site generator for Korean (Coupang vs Ali) & Global (Amazon vs Ali) hubs.

Implements the unanimous 3-AI consensus (Gemini · Claude · Codex):
- Zero unverified static retailer prices, % spread badges, or price-tier claims in HTML, JSON-LD, meta, or feeds.
- Manufacturer Reference MSRP isolated strictly inside the specification table with source & check date.
- Destination country separated from UI language (Ship to KR: US $200 list-clearance vs $150 other / Ship to US: domestic vs import charges).
- Fail-closed live API offer client hook (with open-tab periodic expiry re-check) + PII-free channel tracking mapper.
- Integrated MacBook Dual-Monitor Dock Compatibility Checker (/ko/tools/..., /en/tools/...) & 12 Buying Guides (/en/guides/...).
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

from src.affiliate import (
    BUTTON_DISCLOSURE_EN,
    BUTTON_DISCLOSURE_KO,
    DISCLOSURE_EN,
    DISCLOSURE_KO,
)
from src.tools_and_guides import (
    GUIDES_EN,
    render_dock_checker_page,
    render_en_guide_detail,
    render_en_guides_index,
)

CATEGORY_LABELS_KO = {
    "all": "전체",
    "hubs": "독/허브",
    "chargers": "충전기",
    "powerbanks": "보조배터리",
    "controllers": "컨트롤러/패드",
    "storage": "외장SSD",
    "keyboards": "키보드",
    "mice": "마우스",
    "audio": "오디오/마이크",
    "lighting": "조명",
    "productivity": "생산성 기어",
    "minipc": "미니PC",
}

CATEGORY_LABELS_EN = {
    "all": "All Gear",
    "hubs": "USB-C Docks",
    "chargers": "GaN Chargers",
    "powerbanks": "Power Banks",
    "controllers": "Controllers",
    "storage": "Portable SSDs",
    "keyboards": "Keyboards",
    "mice": "Mice",
    "audio": "Microphones",
    "lighting": "Desk Lighting",
    "productivity": "Stream & Macros",
    "minipc": "Mini PCs",
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
PAGE_SIZE = 20
TOP_BRANDS = 8
_SKU_RE = re.compile(r"^(?=.*\d)[A-Z0-9][A-Z0-9\-]{2,15}$")

FONT_CSS_URL = (
    "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/"
    "pretendardvariable-dynamic-subset.min.css"
)

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
  -webkit-font-smoothing: antialiased;
  word-break: keep-all;
  overflow-wrap: break-word;
}
a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: 3px; }
button, input, select { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--coupang); outline-offset: 2px; border-radius: 6px; }
.num { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
.i { flex: none; vertical-align: -0.15em; fill: none; stroke: currentColor; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
.wrap { max-width: var(--wrap, 1200px); margin: 0 auto; padding: 0 22px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

.legal-strip { background: #ECEEF2; border-bottom: 1px solid var(--line); color: var(--ink-2); font-size: 12.5px; line-height: 1.5; }
.legal-strip .wrap { display: flex; gap: 10px; align-items: baseline; padding-top: 7px; padding-bottom: 7px; }
.legal-tag { flex: none; font-size: 11px; font-weight: 700; letter-spacing: 0.02em; color: var(--muted); border: 1px solid var(--line-2); border-radius: 4px; padding: 0 5px; background: var(--surface); }

.site-head { position: sticky; top: 0; z-index: 20; background: rgba(255, 255, 255, 0.92); backdrop-filter: saturate(1.4) blur(10px); border-bottom: 1px solid var(--line); }
.site-head .wrap { display: flex; align-items: center; justify-content: space-between; gap: 12px; height: 62px; }
.brand { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; font-weight: 750; font-size: 17px; letter-spacing: -0.02em; white-space: nowrap; }
.brand-region { font-size: 11px; font-weight: 700; letter-spacing: 0.04em; color: var(--save-ink); background: var(--save-bg); border-radius: 5px; padding: 1px 6px; }
.head-nav { display: flex; align-items: center; gap: 4px; font-size: 13.5px; flex-wrap: nowrap; }
.head-nav a { display: inline-flex; align-items: center; gap: 5px; text-decoration: none; padding: 7px 10px; border-radius: 9px; color: var(--ink-2); font-weight: 600; white-space: nowrap; }
.head-nav a:hover { background: var(--sunk); color: var(--ink); }
.head-nav a.nav-hi { background: var(--save-bg); color: var(--save-ink); font-weight: 700; }
.head-nav a.tg { background: var(--ink); color: #fff; margin-left: 4px; }

/* Destination selector banner */
.dest-bar { margin-top: 14px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 11px 16px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 16px; font-size: 13.5px; }
.dest-bar-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.dest-bar-left strong { font-size: 13px; color: var(--ink); }
.dest-sel { height: 32px; border: 1px solid var(--line-2); border-radius: 8px; padding: 0 10px; background: var(--sunk); font-size: 13px; font-weight: 650; cursor: pointer; }
.dest-rule { color: var(--ink-2); font-size: 13px; flex: 1 1 320px; }

/* Featured tool / guide callout */
.feat-strip { margin-top: 10px; background: linear-gradient(90deg, #111827 0%, #1F2937 100%); color: #fff; border-radius: 12px; padding: 14px 18px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px 18px; }
.feat-strip p { font-size: 13.5px; color: #D1D5DB; margin-top: 2px; }
.feat-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.feat-btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 13px; border-radius: 9px; background: #5EEAD4; color: #062F2B; font-weight: 750; font-size: 13.5px; text-decoration: none; white-space: nowrap; }
.feat-btn.sec { background: rgba(255,255,255,0.12); color: #fff; font-weight: 650; }

.tag { flex: none; font-size: 12.5px; font-weight: 600; color: var(--ink-2); background: var(--sunk); border-radius: 6px; padding: 3px 8px; white-space: nowrap; }
.pick { display: inline-flex; align-items: center; font-size: 12.5px; font-weight: 700; border-radius: 7px; padding: 4px 9px; line-height: 1.4; }
.pick.is-ali { color: var(--save-ink); background: var(--save-bg); }
.pick.is-local { color: var(--local); background: var(--local-bg); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; }
.chips li { font-size: 12.5px; font-weight: 550; color: var(--ink-2); border: 1px solid var(--line); border-radius: 6px; padding: 2px 8px; background: var(--surface); }

.battle { display: grid; grid-template-columns: 1fr 1fr; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.side { position: relative; padding: 13px 14px 12px; background: var(--surface); display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.side + .side { border-left: 1px solid var(--line); }
.side.is-win { background: #F3FAF8; box-shadow: inset 0 0 0 1.5px var(--save); }
.side-head { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.store { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; }
.store::before { content: ""; width: 8px; height: 8px; border-radius: 2px; background: var(--c, var(--ink)); flex: none; }
.coupang { --c: var(--coupang); }
.amazon { --c: var(--amazon); }
.ali { --c: var(--ali); }
.perk { font-size: 12.5px; color: var(--ink-2); font-weight: 600; }
.side-meta { font-size: 12px; color: var(--muted); line-height: 1.45; }
.win-tag { font-size: 11px; font-weight: 750; color: #fff; background: var(--save); border-radius: 4px; padding: 0 5px; line-height: 1.6; }
.live-slot { margin-top: 4px; font-size: 13px; font-weight: 700; color: var(--save-ink); }

.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px; padding: 10px 14px; border-radius: 10px; font-weight: 700; font-size: 14px; text-decoration: none; color: #fff; text-align: center; line-height: 1.3; }
.btn:hover { filter: brightness(0.94); }
.btn-coupang { background: var(--coupang); }
.btn-amazon { background: var(--amazon); color: #111827; }
.btn-ali { background: var(--ali); }
.btn-disc { margin-top: 8px; font-size: 11.5px; line-height: 1.45; color: var(--muted); }

/* Index */
.is-hub { --wrap: 1336px; }
.idx-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 4px 20px; padding: 16px 0 10px; }
.idx-head h1 { font-size: 1.375rem; line-height: 1.3; letter-spacing: -0.022em; font-weight: 760; }
.stamp { color: var(--muted); font-size: 13px; display: flex; gap: 2px 14px; flex-wrap: wrap; }
.stamp b { color: var(--ink-2); font-weight: 650; }

.summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); background: var(--surface); border: 1px solid var(--line); border-radius: 12px; }
.sm { padding: 10px 16px 11px; border-left: 1px solid var(--line); min-width: 0; }
.sm:first-child { border-left: 0; }
.sm dt { font-size: 12px; font-weight: 650; color: var(--muted); }
.sm-v { display: inline-block; font-size: 1.08rem; font-weight: 760; line-height: 1.4; }
.sm-s { display: block; font-size: 12.5px; color: var(--ink-2); line-height: 1.45; }
.sm a { text-decoration: none; }

.work { display: grid; grid-template-columns: 232px minmax(0, 1fr); gap: 0 28px; margin-top: 10px; align-items: start; }
.side-col { position: sticky; top: 72px; max-height: calc(100dvh - 84px); overflow-y: auto; margin-top: 10px; padding: 0 6px 20px 0; }
.facet-h, .facet legend { display: flex; align-items: baseline; gap: 6px; padding: 0 8px 4px; font-size: 12px; font-weight: 700; color: var(--muted); }
.catnav ul { list-style: none; }
.catnav a { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 30px; padding: 4px 8px; border-radius: 7px; font-size: 14px; font-weight: 550; color: var(--ink-2); text-decoration: none; }
.catnav a:hover { background: #E9ECF0; color: var(--ink); }
.catnav .num, .opt .num { font-size: 12.5px; color: var(--muted); }
.catnav a[aria-current] { background: var(--ink); color: #fff; font-weight: 650; }
.catnav a[aria-current] .num { color: #C9CED6; }
.catnav a.is-zero, .opt.is-zero { opacity: 0.45; }
.facet { border: 0; margin-top: 20px; padding: 0; min-width: 0; }
.opt { display: flex; align-items: center; gap: 8px; min-height: 30px; padding: 4px 8px; border-radius: 7px; font-size: 14px; color: var(--ink-2); cursor: pointer; }
.opt:hover { background: #E9ECF0; color: var(--ink); }
.opt input { flex: none; width: 15px; height: 15px; cursor: pointer; }
.opt .lbl { flex: 1; min-width: 0; }
.opt:has(input:checked) { color: var(--ink); font-weight: 650; }
.facet[data-brands]:not([data-expanded]) .opt.is-extra:not(:has(input:checked)) { display: none; }
.facet-more { display: inline-flex; margin: 4px 0 0 8px; border: 0; background: none; padding: 4px 0; font-size: 13px; font-weight: 650; color: var(--ink-2); cursor: pointer; text-decoration: underline; }
.sheet-head, .sheet-foot, .scrim, .fbtn { display: none; }

.main { container: idx / inline-size; min-width: 0; }
.bar { position: sticky; top: 62px; z-index: 10; display: flex; align-items: center; gap: 8px; padding: 10px 0; background: var(--canvas); }
.search { position: relative; flex: 1 1 220px; min-width: 0; }
.search .i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.search input { width: 100%; height: 40px; border: 1px solid var(--line-2); border-radius: 10px; background: var(--surface); padding: 0 40px 0 36px; font-size: 14.5px; }
.search kbd { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font: 600 11px/1 inherit; color: var(--muted); border: 1px solid var(--line-2); border-radius: 5px; padding: 3px 6px; background: var(--sunk); pointer-events: none; }
.search input:focus + kbd, .search input:not(:placeholder-shown) + kbd { display: none; }
.sort { position: relative; flex: none; }
.sort select { appearance: none; height: 40px; border: 1px solid var(--line-2); border-radius: 10px; background: var(--surface); padding: 0 32px 0 12px; font-size: 14px; font-weight: 600; cursor: pointer; }
.sort .i { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }

.status { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; min-height: 32px; margin-bottom: 8px; font-size: 13px; color: var(--muted); }
.on-chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.chip-x { display: inline-flex; align-items: center; gap: 3px; min-height: 26px; border: 1px solid var(--line-2); border-radius: 999px; background: var(--surface); padding: 2px 6px 2px 10px; font-size: 12.5px; font-weight: 600; cursor: pointer; }
.chip-clear { border: 0; background: none; padding: 2px 4px; font-size: 12.5px; font-weight: 650; cursor: pointer; text-decoration: underline; }
.seg { display: inline-flex; background: var(--surface); border: 1px solid var(--line-2); border-radius: 9px; padding: 2px; gap: 2px; height: 32px; margin-left: auto; }
.seg button { display: inline-flex; align-items: center; gap: 5px; border: 0; background: transparent; padding: 0 10px; border-radius: 6px; font-size: 12.5px; font-weight: 600; cursor: pointer; }
.seg button[aria-pressed="true"] { background: var(--ink); color: #fff; }

.rows { list-style: none; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.row { display: grid; grid-template-columns: minmax(0, 1fr) 210px 230px; gap: 10px 16px; padding: 14px 16px; border-top: 1px solid var(--line); align-items: center; }
.row:first-child { border-top: 0; }
.row:hover, .row[data-open] { background: #FBFCFD; }
.r-meta { font-size: 12px; font-weight: 600; color: var(--muted); }
.r-title { margin-top: 2px; font-size: 15px; line-height: 1.4; font-weight: 700; }
.r-title a { text-decoration: none; }
.r-title a:hover { text-decoration: underline; }
.r-spec { margin-top: 3px; font-size: 12.5px; color: var(--ink-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.r-spec span::before { content: "·"; margin: 0 6px; color: #9AA1AC; }
.r-verd { display: flex; flex-direction: column; gap: 3px; }
.call { font-size: 13px; font-weight: 700; }
.is-ali > .call { color: var(--save-ink); }
.is-local > .call { color: var(--local); }
.why { font-size: 12px; color: var(--muted); }
.r-act { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 6px; }
.buy { display: inline-flex; align-items: center; justify-content: center; gap: 4px; height: 34px; padding: 0 10px; border: 1px solid var(--line-2); border-radius: 8px; background: var(--surface); font-size: 12.5px; font-weight: 650; text-decoration: none; white-space: nowrap; }
.buy.is-pick { background: var(--ink); border-color: var(--ink); color: #fff; }
.r-more { display: inline-flex; align-items: center; gap: 3px; height: 34px; border: 0; border-radius: 8px; background: transparent; padding: 0 8px; font-size: 12.5px; font-weight: 600; color: var(--ink-2); cursor: pointer; }
.row-disc { grid-column: 1 / -1; font-size: 11px; color: var(--muted); text-align: right; margin-top: -4px; }

.drawer { grid-column: 1 / -1; display: grid; grid-template-rows: 0fr; visibility: hidden; transition: grid-template-rows 0.2s var(--ease); }
.row[data-open] .drawer { grid-template-rows: 1fr; visibility: visible; margin-top: 6px; }
.drawer-in { min-height: 0; overflow: hidden; }
.drawer-box { display: grid; gap: 10px; padding: 12px 14px; background: var(--sunk); border-radius: 8px; }
.drawer dl { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 24px; }
.drawer dt { font-size: 12px; font-weight: 700; color: var(--muted); }
.drawer dd { font-size: 13.5px; line-height: 1.55; color: var(--ink-2); }
.drawer-link { justify-self: start; display: inline-flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 650; text-decoration: none; }

.hub[data-view="cards"] .rows { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; background: none; border: 0; }
.hub[data-view="cards"] .row { grid-template-columns: 1fr; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
.hub[data-view="cards"] .r-act { justify-content: flex-start; }
.hub[data-view="cards"] .row-disc { text-align: left; }

.pager { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px; margin-top: 14px; }
.pager-status { width: 100%; text-align: center; font-size: 13px; color: var(--muted); }
.pager button { height: 40px; border: 1px solid var(--line-2); border-radius: 10px; background: var(--surface); padding: 0 16px; font-size: 14px; font-weight: 650; cursor: pointer; }
.pager button.primary { background: var(--ink); border-color: var(--ink); color: #fff; }
.empty { background: var(--surface); border: 1px dashed var(--line-2); border-radius: 12px; padding: 36px 20px; text-align: center; font-size: 14px; color: var(--ink-2); }
.empty button { margin-top: 14px; height: 36px; border: 1px solid var(--ink); background: var(--ink); color: #fff; border-radius: 9px; padding: 0 14px; font-size: 13.5px; font-weight: 650; cursor: pointer; }

html.js .hub:not([data-ready]) .rows > li:nth-child(n+__PAGE_NEXT__) { display: none; }

/* Detail, Tool & Guide pages */
.crumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 20px 0 0; font-size: 13.5px; color: var(--muted); list-style: none; }
.crumbs a { text-decoration: none; color: var(--ink-2); }
.detail { display: grid; grid-template-columns: minmax(0, 1fr) 370px; grid-template-areas: "intro aside" "body aside"; gap: 0 34px; padding: 16px 0 10px; align-items: start; }
.d-intro { grid-area: intro; min-width: 0; }
.d-body { grid-area: body; }
.d-aside { grid-area: aside; position: sticky; top: 82px; }
.d-intro h1, .tool-hero h1 { margin-top: 10px; font-size: clamp(1.65rem, 1.2rem + 1.6vw, 2.35rem); line-height: 1.2; letter-spacing: -0.03em; font-weight: 780; }
.d-intro .dek, .tool-hero .dek { margin-top: 12px; color: var(--ink-2); font-size: 1.02rem; max-width: 66ch; }
.d-intro .chips { margin-top: 16px; }
.section { margin-top: 32px; }
.section h2 { font-size: 1.28rem; letter-spacing: -0.02em; font-weight: 740; margin-bottom: 12px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); }
.customs-note { display: flex; flex-direction: column; gap: 6px; padding: 14px 18px; border-radius: 12px; background: var(--warn-bg); color: var(--warn-ink); font-size: 13.5px; line-height: 1.55; }
.spec-table { width: 100%; border-collapse: collapse; font-size: 14.5px; }
.spec-table th, .spec-table td { text-align: left; padding: 12px 18px; border-bottom: 1px solid var(--line); vertical-align: top; }
.spec-table tr:last-child th, .spec-table tr:last-child td { border-bottom: 0; }
.spec-table th { width: 32%; color: var(--muted); font-weight: 600; font-size: 13.5px; background: #FAFBFC; }
.guide-matrix thead th { width: auto; color: var(--ink); font-weight: 700; background: var(--sunk); }
.msrp-ref th, .msrp-ref td { background: #F9FAFB; font-size: 13px; color: var(--muted); }
.pc { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.pc .panel { padding: 18px 20px; }
.pc h3 { font-size: 1rem; font-weight: 720; margin-bottom: 8px; }
.pc ul, .guide-excl { list-style: none; display: grid; gap: 8px; }
.pc li, .guide-excl li { position: relative; padding-left: 16px; font-size: 14.5px; color: var(--ink-2); line-height: 1.6; }
.pc li::before, .guide-excl li::before { content: "•"; position: absolute; left: 2px; color: var(--muted); }
.decide { padding: 20px; }
.decide-title { font-size: 13px; font-weight: 650; color: var(--muted); }
.decide .pick { margin-top: 8px; font-size: 13.5px; }
.decide-verdict { margin-top: 12px; font-size: 14px; line-height: 1.6; color: var(--ink-2); }
.decide .battle { margin-top: 14px; }
.decide .actions { grid-template-columns: 1fr; margin-top: 14px; }
.decide-stamp { margin-top: 10px; font-size: 12px; color: var(--muted); }
.decide-switch { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; font-size: 13.5px; font-weight: 600; color: var(--ink-2); text-decoration: none; }
.related { margin-top: 48px; padding-top: 28px; border-top: 1px solid var(--line); }
.rel-grid, .tool-grid, .guide-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 14px; }
.guide-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 22px; }
.rel, .tool-card, .guide-card { position: relative; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px; display: flex; flex-direction: column; gap: 10px; }
.rel h3 a, .guide-card h2 a, .tool-card h4 a { text-decoration: none; }
.rel h3 a:hover, .guide-card h2 a:hover, .tool-card h4 a:hover { text-decoration: underline; }
.guide-card h2 { font-size: 1.12rem; line-height: 1.35; }
.guide-card p, .tc-sum { font-size: 14px; color: var(--ink-2); }
.tc-con { font-size: 13px; color: var(--warn-ink); background: var(--warn-bg); padding: 8px 10px; border-radius: 8px; }
.tc-more, .gc-meta { font-size: 13px; font-weight: 650; color: var(--ink-2); margin-top: auto; }
.guide-p { font-size: 15.5px; line-height: 1.72; color: var(--ink-2); max-width: 74ch; }

/* Dock Checker Tool */
.tool-hero { padding: 18px 0 8px; }
.tool-form { padding: 20px; margin-top: 16px; }
.tool-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 18px; }
.tool-fields label { display: flex; flex-direction: column; gap: 6px; font-size: 13.5px; font-weight: 650; color: var(--ink); }
.tool-sel { height: 42px; border: 1px solid var(--line-2); border-radius: 10px; padding: 0 12px; background: var(--surface); font-size: 14px; font-weight: 550; }
.tool-out { margin-top: 20px; }
.verdict-box { padding: 22px; border-radius: 14px; border: 1.5px solid var(--line); background: var(--surface); }
.verdict-box.is-ok { border-color: var(--save); background: #F4FBF9; }
.verdict-box.is-warn { border-color: #D97706; background: #FFFBEB; }
.verdict-box.is-hold { border-color: #6B7280; background: #F3F4F6; }
.v-badge { display: inline-block; font-size: 12px; font-weight: 750; padding: 3px 9px; border-radius: 6px; background: var(--ink); color: #fff; }
.verdict-box.is-ok .v-badge { background: var(--save); }
.verdict-box.is-warn .v-badge { background: #B45309; }
.verdict-box h2 { margin-top: 10px; font-size: 1.28rem; line-height: 1.35; }
.verdict-box p { margin-top: 8px; color: var(--ink-2); max-width: 74ch; }
.tool-check { margin-top: 12px; padding-left: 18px; color: var(--ink-2); font-size: 14px; display: grid; gap: 6px; }
.tool-alert { margin-top: 14px; padding: 12px 14px; border-radius: 10px; background: var(--warn-bg); color: var(--warn-ink); font-size: 13.5px; display: flex; flex-direction: column; gap: 3px; }
.tool-picks { margin-top: 24px; }
.tool-picks h3 { font-size: 1.15rem; font-weight: 750; }
.tool-foot-note { margin-top: 20px; font-size: 13px; color: var(--muted); }

/* Gateway & Prose */
.gate-hero { padding: 44px 0 24px; max-width: 760px; }
.regions { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding-bottom: 20px; }
.region { position: relative; background: var(--surface); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.region.is-suggested { border-color: var(--ink); }
.region-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.region h2 { font-size: 1.4rem; font-weight: 770; }
.region h2 a { text-decoration: none; }
.region h2 a::after { content: ""; position: absolute; inset: 0; border-radius: inherit; }
.suggest { font-size: 12px; font-weight: 700; color: #fff; background: var(--ink); border-radius: 6px; padding: 3px 8px; }
.region-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.region-stats div { padding: 12px 0 12px 12px; border-left: 1px solid var(--line); }
.region-stats div:first-child { border-left: 0; padding-left: 0; }
.region-stats span { display: block; font-size: 12px; color: var(--muted); font-weight: 600; }
.region-stats strong { display: block; font-size: 1.05rem; font-weight: 760; }
.prose { max-width: 72ch; padding: 36px 0 10px; }
.prose h1 { font-size: 2rem; font-weight: 780; }
.prose h2 { margin-top: 28px; font-size: 1.15rem; font-weight: 740; }
.prose p { margin-top: 10px; color: var(--ink-2); }
.site-foot { margin-top: 60px; border-top: 1px solid var(--line); background: var(--surface); }
.site-foot .wrap { display: grid; grid-template-columns: 1fr auto; gap: 18px 40px; padding-top: 24px; padding-bottom: 30px; font-size: 13px; color: var(--muted); }
.foot-links { display: flex; gap: 16px; flex-wrap: wrap; }
.foot-links a { color: var(--ink-2); font-weight: 600; text-decoration: none; }

@media (max-width: 1023.98px) {
  .detail { grid-template-columns: 1fr; grid-template-areas: "intro" "aside" "body"; }
  .d-aside { position: static; margin-top: 20px; }
  .rel-grid, .tool-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .work { display: block; margin-top: 14px; }
  .side-col { display: contents; }
  .catnav .facet-h { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .catnav ul { display: flex; gap: 6px; overflow-x: auto; margin: 0 -22px; padding: 0 22px 4px; }
  .catnav li { flex: none; }
  .catnav a { padding: 4px 12px; border: 1px solid var(--line-2); border-radius: 999px; background: var(--surface); }
  .fbtn { display: inline-flex; align-items: center; gap: 6px; height: 40px; border: 1px solid var(--line-2); border-radius: 10px; background: var(--surface); padding: 0 12px; font-weight: 650; }
  .facets { position: fixed; z-index: 40; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; max-height: 84dvh; background: var(--surface); border-radius: 16px 16px 0 0; transform: translateY(104%); visibility: hidden; transition: transform 0.25s var(--ease); }
  .facets[data-open] { transform: none; visibility: visible; }
  .facets-body { overflow-y: auto; padding: 14px; }
  .sheet-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .sheet-foot { display: grid; grid-template-columns: auto 1fr; gap: 8px; padding: 10px 16px; border-top: 1px solid var(--line); }
  .scrim { display: block; position: fixed; inset: 0; z-index: 39; background: rgba(17,24,39,0.45); opacity: 0; visibility: hidden; }
  .scrim[data-open] { opacity: 1; visibility: visible; }
}
@media (max-width: 780px) {
  .regions, .pc, .rel-grid, .tool-grid, .guide-grid, .tool-fields, .row, .summary, .drawer dl { grid-template-columns: 1fr; }
  .r-act { justify-content: flex-start; }
  .row-disc { text-align: left; }
  .brand-name, .head-nav .lbl-tg { display: none; }
  .site-foot .wrap { grid-template-columns: 1fr; }
}
"""

APP_JS = r"""
(() => {
  // 1. Destination Country Switcher (separates UI language from actual shipping destination)
  const DEST_RULES = {
    ko: {
      KR: '대한민국 수령 기준: 미국발 목록통관 적격 미화 $200 이하 / 일반통관 및 중국·기타국발 미화 $150 이하 면세 (결제창 최종 금액·합산과세 직접 확인)',
      US: '미국 수령 기준: 미국 소액면세(de minimis) 중단 — Amazon 미국 내 발송(Ships from US) 여부 및 AliExpress 결제창 수입관세(Import charges) 포함 여부 확인',
      OTHER: '기타 국가 수령 기준: 수령국 관세·부가세(VAT/GST) 면세 한도 및 결제창 세금 포함 여부를 확인하세요.'
    },
    en: {
      US: 'Shipping to United States: US de minimis exemption ended — check "Ships from US" on Amazon vs "Import charges included" at checkout on cross-border AliExpress orders.',
      KR: 'Shipping to South Korea: Duty-free up to USD 200 for eligible US list-clearance shipments / USD 150 for China & general clearance (verify final checkout total).',
      OTHER: 'Other Destinations: Verify local VAT/GST/import duty thresholds and checkout tax inclusion on the store page.'
    }
  };

  const pageLang = document.documentElement.lang === 'ko' ? 'ko' : 'en';
  let savedDest = null;
  try { savedDest = localStorage.getItem('gch-dest'); } catch (e) {}
  const defaultDest = pageLang === 'ko' ? 'KR' : 'US';
  let currentDest = ['KR', 'US', 'OTHER'].includes(savedDest) ? savedDest : defaultDest;

  document.querySelectorAll('[data-dest-box]').forEach(box => {
    const sel = box.querySelector('[data-dest-select]');
    const ruleEl = box.querySelector('[data-dest-rule]');
    const applyDest = (val) => {
      currentDest = val;
      try { localStorage.setItem('gch-dest', val); } catch (e) {}
      if (sel) sel.value = val;
      if (ruleEl) ruleEl.textContent = (DEST_RULES[pageLang] || DEST_RULES.en)[val];
      if (window.__gchApplyAttribution) window.__gchApplyAttribution(document);
    };
    if (sel) sel.addEventListener('change', () => applyDest(sel.value));
    applyDest(currentDest);
  });

  // 2. PII-Free Channel & Destination Attribution Mapper + Zero-Cost Funnel Hooks
  const cfgEl = document.querySelector('[data-aff-config]');
  const AFF_CFG = cfgEl ? JSON.parse(cfgEl.textContent) : {};

  function detectSource() {
    const p = new URLSearchParams(location.search);
    const raw = (p.get('utm_source') || p.get('src') || '').toLowerCase().replace(/[^a-z0-9_-]/g, '');
    if (['pinterest', 'telegram', 'threads', 'tool', 'rss'].includes(raw)) return raw === 'rss' ? 'pinterest' : raw;
    if (location.pathname.includes('/tools/')) return 'tool';
    const ref = (document.referrer || '').toLowerCase();
    if (ref.includes('pinterest.')) return 'pinterest';
    if (ref.includes('t.me') || ref.includes('telegram.')) return 'telegram';
    if (ref.includes('threads.net')) return 'threads';
    if (!ref || ref.includes(location.hostname)) return 'web';
    return 'unknown';
  }
  const trafficSource = detectSource();

  window.__gchApplyAttribution = function(root) {
    const scope = root || document;
    const destToken = currentDest.toLowerCase();
    scope.querySelectorAll('a[data-aff]').forEach(a => {
      try {
        const u = new URL(a.href);
        const store = a.dataset.store || '';
        if (store === 'coupang' && u.hostname.endsWith('coupang.com')) {
          const map = AFF_CFG.coupang_sub_ids_by_source || {};
          const baseSub = map[trafficSource] || map.unknown || 'gch_ko_web';
          u.searchParams.set('subid', `${baseSub}_${destToken}`.slice(0, 30));
          a.href = u.toString();
        } else if (store === 'aliexpress' && u.hostname.endsWith('aliexpress.com')) {
          const map = AFF_CFG.aliexpress_tracking_by_source || {};
          const key = trafficSource === 'web' ? `web_${pageLang}` : (trafficSource === 'telegram' ? `telegram_${pageLang}` : trafficSource);
          const track = map[key] || map[trafficSource] || map.unknown || 'gearhub_global';
          u.searchParams.set('aff_fcid', `${track}_${destToken}`.slice(0, 30));
          a.href = u.toString();
        } else if (store === 'amazon' && u.hostname.endsWith('amazon.com')) {
          // Strictly use only issued Associate tags from config; never fabricate unissued tags.
          const map = AFF_CFG.amazon_tags_by_source || {};
          const tag = map[trafficSource] || map.default || 'gearcomparehu-20';
          u.searchParams.set('tag', tag);
          a.href = u.toString();
        }
      } catch (e) {}
    });
  };
  window.__gchApplyAttribution(document);

  function logFunnel(event, extra) {
    const payload = Object.assign({ event, lang: pageLang, src: trafficSource, dest: currentDest, path: location.pathname, ts: Date.now() }, extra || {});
    if (AFF_CFG.analytics_beacon_url && navigator.sendBeacon) {
      try { navigator.sendBeacon(AFF_CFG.analytics_beacon_url, JSON.stringify(payload)); } catch (e) {}
    }
  }
  logFunnel('page_view');
  document.addEventListener('click', e => {
    const aff = e.target.closest('a[data-aff]');
    if (aff) logFunnel('outbound_click', { store: aff.dataset.store || '' });
  });
  window.addEventListener('gch:funnel', e => logFunnel((e.detail && e.detail.event) || 'tool_event', e.detail));

  // 3. Fail-Closed Live API Offer Hydrator (periodic re-check on open tabs; hides immediately on expiry/failure)
  let cachedLiveOffers = null;
  function renderLiveOffers() {
    const slots = document.querySelectorAll('[data-live-offer]');
    if (!slots.length) return;
    const now = Date.now();
    slots.forEach(slot => {
      const pid = slot.dataset.pid;
      const store = slot.dataset.store;
      const entry = cachedLiveOffers && cachedLiveOffers[pid] && cachedLiveOffers[pid][store];
      const exp = entry && entry.expires_at ? Date.parse(entry.expires_at) : NaN;
      if (!entry || !entry.price_text || Number.isNaN(exp) || now >= exp) {
        slot.textContent = '';
        slot.hidden = true;
        return;
      }
      slot.textContent = `${entry.price_text} (${entry.fetched_label || 'API verified'})`;
      slot.hidden = false;
    });
  }

  if (AFF_CFG.live_offers_endpoint) {
    fetch(AFF_CFG.live_offers_endpoint, { cache: 'no-store' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => { cachedLiveOffers = data; renderLiveOffers(); })
      .catch(() => { cachedLiveOffers = null; renderLiveOffers(); });
    setInterval(renderLiveOffers, 60000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) renderLiveOffers(); });
  }

  // 4. Hub Faceted Search & Filter Controller
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
    return { el, c: d.c, b: d.b, r: d.r, prio: +d.prio, q: d.q };
  });
  const SORTS = {
    prio: (a, b) => b.prio - a.prio || a.q.localeCompare(b.q),
    name: (a, b) => a.q.localeCompare(b.q),
  };

  const main = $('.main');
  const search = $('[data-search]');
  const sortSel = $('[data-sort]');
  const viewBtns = $$('[data-view-btn]');
  const catLinks = scoped ? [] : $$('[data-cat]');
  const routeIn = $$('input[name="route"]');
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
  const validBrands = new Set(brandIn.map(i => i.value));
  let savedView = null;
  try { savedView = localStorage.getItem('gch-view'); } catch (e) {}
  const state = {
    cat: catLinks.some(a => a.dataset.cat === params.get('cat')) ? params.get('cat') : 'all',
    q: params.get('q') || '',
    route: ['ali', 'dom'].includes(params.get('route')) ? params.get('route') : 'all',
    brand: new Set(params.getAll('brand').filter(v => validBrands.has(v))),
    sort: SORTS[params.get('sort')] ? params.get('sort') : 'prio',
    view: (params.get('view') || savedView) === 'cards' ? 'cards' : 'list',
    limit: PAGE,
  };
  let order = items;

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
    b.addEventListener('click', () => { off(); changed(); });
    return b;
  }

  function renderChips() {
    const out = [];
    if (state.q.trim()) out.push(chip(fmt(L.q, { q: state.q.trim() }), () => { state.q = ''; search.value = ''; }));
    if (state.cat !== 'all') out.push(chip(L.cats[state.cat] || state.cat, () => { state.cat = 'all'; }));
    if (state.route !== 'all') out.push(chip(L.route[state.route], () => { state.route = 'all'; }));
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
    const facets = (state.cat !== 'all') + (state.route !== 'all') + state.brand.size;
    if (fcount) { fcount.textContent = facets; fcount.hidden = facets === 0; }
  }

  function apply() {
    const terms = norm(state.q).split(/\s+/).filter(Boolean);
    const tests = [
      ['cat', it => state.cat === 'all' || it.c === state.cat],
      ['q', it => terms.every(t => it.q.includes(t))],
      ['route', it => state.route === 'all' || it.r === state.route],
      ['brand', it => !state.brand.size || state.brand.has(it.b)],
    ];
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
      if (open('brand')) bump('brand:' + it.b);
    });
    const shown = Math.min(total, state.limit);

    counters.forEach(el => {
      const n = tally.get(el.dataset.n) || 0;
      el.textContent = n;
      const host = el.closest('.opt, [data-cat]');
      if (!host) return;
      const input = host.querySelector('input');
      const active = input ? input.checked : host.hasAttribute('aria-current');
      host.classList.toggle('is-zero', n === 0 && !active);
    });
    catLinks.forEach(a => {
      if (a.dataset.cat === state.cat) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
    routeIn.forEach(i => { i.checked = i.value === state.route; });
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
    if (applyBtn) applyBtn.textContent = fmt(L.apply, { n: total });
    empty.hidden = total > 0;
    list.hidden = total === 0;
    renderChips();
  }

  function changed() { state.limit = PAGE; apply(); }
  function reset() {
    state.q = ''; state.cat = 'all'; state.route = 'all'; state.brand.clear();
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
    e.preventDefault();
    state.route = a.dataset.routeLink;
    changed();
  }));
  routeIn.forEach(i => i.addEventListener('change', () => { state.route = i.value; changed(); }));
  brandIn.forEach(i => i.addEventListener('change', () => {
    if (i.checked) state.brand.add(i.value); else state.brand.delete(i.value);
    changed();
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

  const openBtn = $('[data-sheet-open]');
  if (openBtn && sheet && scrim) {
    const closeSheet = () => { sheet.removeAttribute('data-open'); scrim.removeAttribute('data-open'); };
    openBtn.addEventListener('click', () => { sheet.setAttribute('data-open', ''); scrim.setAttribute('data-open', ''); });
    $$('[data-sheet-close]').forEach(b => b.addEventListener('click', closeSheet));
    if (applyBtn) applyBtn.addEventListener('click', closeSheet);
    scrim.addEventListener('click', closeSheet);
  }

  resort();
  apply();
  hub.setAttribute('data-ready', '');
})();
"""


def _esc(val: object) -> str:
    return html.escape(str(val))


def product_slug(item_id: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(item_id).lower()).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rsplit("-", 1)[0] or slug[:max_len]
    return slug or "item"


def _cat_slug(cat: str) -> str:
    return product_slug(cat)


def _short_name(it: dict) -> str:
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


def _sku(it: dict) -> str:
    for group in reversed(re.findall(r"\(([^)]*)\)", it["model"])):
        for token in reversed(group.split(",")):
            if _SKU_RE.match(token.strip()):
                return token.strip()
    short = _short_name(it)
    return short[len(it["brand"].strip()):].strip() or short


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


def _cat_label(cat: str, lang: str) -> str:
    labels = CATEGORY_LABELS_KO if lang == "ko" else CATEGORY_LABELS_EN
    return labels.get(cat, cat)


def _ranked(counts: Counter) -> list[str]:
    return sorted(counts, key=lambda k: (-counts[k], k.lower()))


def _profile(it: dict, lang: str) -> dict:
    m = it["metrics"]
    links = it["affiliate_links"]
    bp = it.get("buying_profile", {})
    if lang == "ko":
        direct_pick = m["preferred_route_ko"] == "direct"
        return {
            "direct_pick": direct_pick,
            "prio": 90 if not direct_pick else 75,
            "dom_key": "coupang",
            "dom_store_id": "coupang",
            "dom_url": links["coupang"],
            "ali_url": links["aliexpress"],
            "customs_note": bp.get(
                "kr_customs_note",
                "대한민국 수령 시 중국·기타국발 미화 150달러 이하 / 미국발 목록통관 적격 200달러 이하 면세 기준을 실제 결제창 금액으로 확인하세요.",
            ),
        }
    direct_pick = m["preferred_route_en"] == "direct"
    return {
        "direct_pick": direct_pick,
        "prio": int(m.get("amazon_priority_score", 80)),
        "dom_key": "amazon",
        "dom_store_id": "amazon",
        "dom_url": links["amazon"],
        "ali_url": links["aliexpress"],
        "customs_note": bp.get(
            "us_import_note",
            "US buyers: check 'Ships from US' on Amazon vs 'Import charges included' at checkout on cross-border AliExpress orders.",
        ),
    }


T = {
    "ko": {
        "region": "KR",
        "disclosure": DISCLOSURE_KO,
        "btn_disc": BUTTON_DISCLOSURE_KO,
        "legal_tag": "광고 고지",
        "dom_store": "쿠팡 (국내 배송)",
        "dom_short": "쿠팡 가격 확인",
        "dom_perk": "빠른 국내 수령 · 반품/교환 편의 확인",
        "dom_meta": "와우할인·카드할인 및 판매자 정발 여부를 상품 페이지에서 직접 확인",
        "ali_store": "알리익스프레스 (해외직구)",
        "ali_short": "알리 직구가 확인",
        "ali_perk": "글로벌 공식 스토어 · 시즌 코드 적용 가능",
        "ali_meta": "선착순 프로모션 코드·통관 대행료 및 배송 리드타임(5~12일) 확인",
        "win": "우선 확인 권장",
        "switch": "Global Hub",
        "tg": "텔레그램 알림",
        "tg_long": "특가·코드 텔레그램 채널",
        "policy": "정책·고지",
        "home": "홈",
        "tool_nav": "맥북 독 판별기",
    },
    "en": {
        "region": "GLOBAL",
        "disclosure": DISCLOSURE_EN,
        "btn_disc": BUTTON_DISCLOSURE_EN,
        "legal_tag": "Disclosure",
        "dom_store": "Amazon US",
        "dom_short": "Check Amazon",
        "dom_perk": "Domestic US Fulfillment · Fit/Spec Return Ease",
        "dom_meta": "Verify seller, US NEMA plug spec, and return terms on Amazon before checkout",
        "ali_store": "AliExpress Direct",
        "ali_short": "Check AliExpress",
        "ali_perk": "Brand Factory Store · Seasonal Promo Option",
        "ali_meta": "Check 7–14d transit time and whether import charges are included at checkout",
        "win": "Recommended First Check",
        "switch": "한국어 허브",
        "tg": "Telegram",
        "tg_long": "Telegram deal & code alerts",
        "policy": "Policy",
        "home": "Home",
        "tool_nav": "MacBook Dock Tool",
    },
}


def _aff_config_script(cfg: dict) -> str:
    payload = {
        "coupang_sub_ids_by_source": cfg["affiliate"].get("coupang_sub_ids_by_source", {}),
        "aliexpress_tracking_by_source": cfg["affiliate"].get("aliexpress_tracking_by_source", {}),
        "amazon_tags_by_source": cfg["affiliate"].get("amazon_tags_by_source", {}),
        "live_offers_endpoint": cfg["site"].get("live_offers_endpoint", ""),
        "analytics_beacon_url": cfg["site"].get("analytics_beacon_url", ""),
    }
    raw = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" data-aff-config>{raw}</script>'


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
    # Zero static prices in meta tags, OpenGraph, or structured data (Debate 3 Consensus #1)
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
    guides_link = f'<a href="{up}en/guides/">Buying Guides</a>' if lang == "en" else ""
    return f"""<header class="site-head">
    <div class="wrap">
      <a class="brand" href="{up}{lang}/" aria-label="{brand} {t['region']}">{BRAND_MARK}<span class="brand-name">{brand}</span><span class="brand-region">{t['region']}</span></a>
      <nav class="head-nav" aria-label="{'주요 메뉴' if lang == 'ko' else 'Primary'}">
        <a class="nav-hi" href="{up}{lang}/tools/macbook-dock-checker/">{t['tool_nav']}</a>
        {guides_link}
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
        note = "본 허브는 비공인 정적 쇼핑몰 가격을 저장·표시하지 않습니다. 최종 판매가·할인 자격·재고·통관 세액은 각 판매처 결제창에서 직접 확인하세요."
        links = f'<a href="{up}ko/">한국어 허브</a><a href="{up}ko/tools/macbook-dock-checker/">맥북 독 판별기</a><a href="{up}en/">Global Hub</a><a href="{up}policy/">개인정보처리방침·대가성 고지</a>'
    else:
        note = "As an Amazon Associate I earn from qualifying purchases. Static store prices are intentionally omitted; always confirm live pricing, seller terms, and import charges on the store page."
        links = f'<a href="{up}en/">Global Hub</a><a href="{up}en/guides/">Buying Guides</a><a href="{up}en/tools/macbook-dock-checker/">MacBook Dock Tool</a><a href="{up}ko/">한국어 허브</a><a href="{up}policy/">Privacy &amp; Disclosure</a>'
    return f"""<footer class="site-foot">
    <div class="wrap">
      <p>© {year} {brand}. {_esc(note)}</p>
      <nav class="foot-links" aria-label="Footer">{links}</nav>
    </div>
  </footer>
  {_aff_config_script(cfg)}"""


def _dest_banner(lang: str) -> str:
    if lang == "ko":
        return (
            '<div class="dest-bar" data-dest-box>'
            '<div class="dest-bar-left"><strong>실제 배송 수령국 기준:</strong>'
            '<select class="dest-sel" data-dest-select aria-label="배송 수령국 선택">'
            '<option value="KR">대한민국 (KR)</option>'
            '<option value="US">미국 (US)</option>'
            '<option value="OTHER">기타 국가</option>'
            '</select></div>'
            '<p class="dest-rule" data-dest-rule>대한민국 수령 기준: 미국발 목록통관 적격 미화 $200 이하 / 일반통관 및 중국·기타국발 미화 $150 이하 면세 (결제창 최종 금액·합산과세 직접 확인)</p>'
            '</div>'
        )
    return (
        '<div class="dest-bar" data-dest-box>'
        '<div class="dest-bar-left"><strong>Shipping Destination:</strong>'
        '<select class="dest-sel" data-dest-select aria-label="Shipping destination">'
        '<option value="US">United States (US)</option>'
        '<option value="KR">South Korea (KR)</option>'
        '<option value="OTHER">Other Regions</option>'
        '</select></div>'
        '<p class="dest-rule" data-dest-rule>Shipping to United States: US de minimis exemption ended — check "Ships from US" on Amazon vs "Import charges included" at checkout on cross-border AliExpress orders.</p>'
        '</div>'
    )


def _pick_badge(d: dict, lang: str) -> str:
    if lang == "ko":
        if d["direct_pick"]:
            return '<span class="pick is-ali">직구 프로모션 대조 권장 · 글로벌 공식 스토어 운영</span>'
        return '<span class="pick is-local">국내 배송 우선 확인 · 호환성 반품·정식 유통 확인 유리</span>'
    if d["direct_pick"]:
        return '<span class="pick is-ali">Compare Direct Brand Store · Seasonal Promo Candidate</span>'
    return '<span class="pick is-local">Check Amazon US First · Domestic Ship &amp; Compatibility Return</span>'


def _battle(it: dict, d: dict, lang: str) -> str:
    t = T[lang]
    pid = _esc(it["id"])
    win_tag = f'<span class="win-tag">{t["win"]}</span>'
    dom_win = not d["direct_pick"]
    return f"""<div class="battle">
        <div class="side{' is-win' if dom_win else ''}">
          <div class="side-head"><span class="store {d['dom_key']}">{t['dom_store']}</span>{win_tag if dom_win else ''}</div>
          <span class="perk">{_esc(t['dom_perk'])}</span>
          <span class="side-meta">{_esc(t['dom_meta'])}</span>
          <span class="live-slot" data-live-offer data-pid="{pid}" data-store="{d['dom_store_id']}" hidden></span>
        </div>
        <div class="side{' is-win' if not dom_win else ''}">
          <div class="side-head"><span class="store ali">{t['ali_store']}</span>{win_tag if not dom_win else ''}</div>
          <span class="perk">{_esc(t['ali_perk'])}</span>
          <span class="side-meta">{_esc(t['ali_meta'])}</span>
          <span class="live-slot" data-live-offer data-pid="{pid}" data-store="aliexpress" hidden></span>
        </div>
      </div>"""


def _search_blob(it: dict, lang: str) -> str:
    parts = [
        it["brand"], it["model"], it["ko"]["title"], it["en"]["title"],
        _cat_label(it["category"], lang), *map(str, it.get("specs", {}).values()),
    ]
    return _esc(unicodedata.normalize("NFKC", " ".join(parts)).lower())


HUB = {
    "ko": {
        "h1": "PC·데스크 주변기기 국내 정발 vs 해외직구 의사결정 허브",
        "h1_cat": "{cat} 국내 배송 vs 해외직구 구매 조건 비교",
        "title": "{brand} KR — PC·데스크 기어 호환성·단점·통관 기준 비교 허브",
        "title_cat": "{cat} 국내 배송 vs 알리 직구 단점·통관 비교 ({n}종) | {brand}",
        "desc": "동일 모델 PC·데스크 주변기기 {n}종의 실사용 단점, 호환 주의사항, 대한민국 수령 통관 기준(미국발 목록통관 $200 / 기타국발 $150) 및 실시간 판매처 확인 허브.",
        "desc_cat": "{cat} {n}개 모델의 실사용 단점, 통관 확인 사항, 쿠팡·알리익스프레스 구매 경로 비교표. 브랜드: {brands}.",
        "stamp": '<span>검수 기준일 <b class="num">{date}</b></span><span>정적 가격 미보관 · 실시간 판매처 직결</span>',
        "summary_lbl": "요약 지표",
        "m_models": "검수 완료 모델",
        "m_models_v": "{k}종",
        "m_models_sub": "{c}개 분류 · {b}개 브랜드",
        "m_models_sub_cat": "{b}개 브랜드 · 전체 {t}종 중",
        "m_local": "국내 배송 우선 확인",
        "m_local_sub": "호환 반품·가품 주의·콘센트 규격 중요 품목",
        "m_direct": "직구 프로모션 대조",
        "m_direct_sub": "글로벌 브랜드 공식 스토어·코드 시즌 유리 품목",
        "m_filter": "게이트키퍼 검수",
        "m_filter_v": "단품·가짜 매물 차단",
        "m_filter_sub": "전 모델 실사용 단점 필수 수록",
        "cats": "분류",
        "filters": "필터",
        "close": "필터 닫기",
        "f_route": "구매 판단 유형",
        "r_all": "전체",
        "r_dom": "국내 배송 우선 확인",
        "r_ali": "직구 프로모션 대조",
        "f_brand": "브랜드",
        "brand_more": "브랜드 전체 보기 (+{n})",
        "brand_less": "상위 브랜드만 보기",
        "search_lbl": "모델 검색",
        "search_ph": "모델명, 브랜드, 스펙 검색 (예: Revodok, 100W, F75, DisplayLink)",
        "sort_lbl": "정렬",
        "sorts": [("prio", "추천 검토 우선순"), ("name", "브랜드·모델명순")],
        "view_lbl": "보기 방식",
        "views": [("list", "리스트", "리스트 뷰"), ("cards", "카드", "2열 카드 뷰")],
        "list_h": "모델 목록",
        "more_btn": "단점·판단",
        "con": "구매 전 필수 단점 체크",
        "verdict": "경로 선택 기준",
        "detail": "상세 스펙·통관 기준 보기",
        "call_ali": "직구 프로모션 대조 권장",
        "call_dom": "국내 배송 우선 확인",
        "why_ali": "공식 스토어 할인코드 시즌 유리",
        "why_dom": "반품 편의·정식 보증·규격 확인 중요",
        "row_disc": "제휴 링크 (수수료 제공 가능)",
        "empty_t": "조건에 맞는 모델이 없습니다",
        "empty_d": "검색어를 줄이거나 필터를 해제하세요.",
        "reset": "필터 초기화",
        "js": {
            "status": "<strong>{a}–{b}</strong> / 총 <strong>{n}</strong>개 모델 표시 중",
            "statusOf": " · 전체 {t}개",
            "statusNone": "표시할 모델 없음 · 전체 {t}개",
            "more": "더보기 (+{k}개 · 남은 {r}개)",
            "all": "전체 보기 ({n}개)",
            "apply": "{n}개 모델 보기",
            "q": "검색: {q}",
            "clear": "모두 해제",
        },
    },
    "en": {
        "h1": "Desk & USB-C Hardware Compatibility & Buying Index",
        "h1_cat": "{cat} Compatibility & Buying Index",
        "title": "{brand} — Vetted Desk & USB-C Hardware Buying Index (Amazon US vs Direct)",
        "title_cat": "{cat} Buying Guide & Caveats ({n} models) | {brand}",
        "desc": "Price-free hardware compatibility index of {n} vetted desk and USB-C gear models: real-world caveats, US domestic vs cross-border import rules, and live Amazon US / AliExpress store checks.",
        "desc_cat": "Compatibility notes, honest drawbacks, and domestic vs direct-import guidance across {n} {cat} models. Brands: {brands}.",
        "stamp": '<span>Reviewed <b class="num">{date}</b></span><span>Zero stale prices · Spec-verified standalone hardware</span>',
        "summary_lbl": "Summary",
        "m_models": "Vetted models",
        "m_models_v": "{k} models",
        "m_models_sub": "{c} categories · {b} brands",
        "m_models_sub_cat": "{b} brands · of {t} vetted",
        "m_local": "Check Amazon US first",
        "m_local_sub": "Domestic US ship, plug spec & compatibility return",
        "m_direct": "Compare Direct Store",
        "m_direct_sub": "Factory brand storefronts & promo-event candidates",
        "m_filter": "Gatekeeper policy",
        "m_filter_v": "Accessory traps blocked",
        "m_filter_sub": "Mandatory real-world caveats on every model",
        "cats": "Categories",
        "filters": "Filters",
        "close": "Close filters",
        "f_route": "Buying route rationale",
        "r_all": "All models",
        "r_dom": "Check Amazon US first",
        "r_ali": "Compare Direct Store",
        "f_brand": "Brand",
        "brand_more": "All brands (+{n})",
        "brand_less": "Top brands only",
        "search_lbl": "Search models",
        "search_ph": "Search brand, model number, or spec (e.g. DisplayLink, 100W, TMR, QMK)",
        "sort_lbl": "Sort",
        "sorts": [("prio", "Recommended priority"), ("name", "Brand · model A–Z")],
        "view_lbl": "View",
        "views": [("list", "List", "List view"), ("cards", "Cards", "2-column card view")],
        "list_h": "Models",
        "more_btn": "Caveats",
        "con": "Real-world caveats",
        "verdict": "Buying rationale",
        "detail": "Full specs & compatibility",
        "call_ali": "Compare Direct Store",
        "call_dom": "Check Amazon US First",
        "why_ali": "Compare checkout import fees vs promo savings",
        "why_dom": "Domestic US ship & easy compatibility return",
        "row_disc": "Paid affiliate links (Amazon Associate & AliExpress)",
        "empty_t": "No models match these filters",
        "empty_d": "Shorten the query or clear active filters.",
        "reset": "Reset filters",
        "js": {
            "status": "Showing <strong>{a}–{b}</strong> of <strong>{n}</strong> models",
            "statusOf": " · {t} total",
            "statusNone": "No models to show · {t} total",
            "more": "Load {k} more ({r} remaining)",
            "all": "Show all {n}",
            "apply": "View {n} models",
            "q": "Search: {q}",
            "clear": "Clear all",
        },
    },
}


def _render_row(it: dict, lang: str, pfx: str) -> str:
    t, h, d, loc = T[lang], HUB[lang], _profile(it, lang), it[lang]
    slug = product_slug(it["id"])
    href = f"{pfx}{slug}/"
    name = _esc(_short_name(it))
    spec_vals = [v for v in it.get("specs", {}).values() if str(v).strip()][:3]
    specs = "".join(f"<span>{_esc(_chip_text(v, 34))}</span>" for v in spec_vals)
    cls = "is-ali" if d["direct_pick"] else "is-local"
    call = h["call_ali"] if d["direct_pick"] else h["call_dom"]
    why = h["why_ali"] if d["direct_pick"] else h["why_dom"]
    cons = "".join(f"<dd>{_esc(c)}</dd>" for c in loc.get("cons", [])[:2])
    attrs = (
        f'data-c="{_esc(it["category"])}" data-b="{_esc(it["brand"])}" '
        f'data-r="{"ali" if d["direct_pick"] else "dom"}" data-prio="{d["prio"]}" '
        f'data-q="{_search_blob(it, lang)}"'
    )

    def buy(store_cls: str, store_id: str, url: str, label: str, pick: bool) -> str:
        return (
            f'<a class="buy {store_cls}{" is-pick" if pick else ""}" data-aff="{store_cls}" data-store="{store_id}" '
            f'href="{_esc(url)}" target="_blank" rel="nofollow sponsored noopener" aria-label="{label} · {name}">'
            f'{label} {_use("out", 13)}</a>'
        )

    return f"""
        <li class="row" {attrs}>
          <div class="r-info">
            <p class="r-meta">{_esc(_cat_label(it['category'], lang))} · {_esc(it['brand'])}</p>
            <h3 class="r-title"><a href="{href}">{_esc(loc['title'])}</a></h3>
            <p class="r-spec"><b>{_esc(_sku(it))}</b>{specs}</p>
          </div>
          <div class="r-verd {cls}">
            <span class="call">{_esc(call)}</span>
            <span class="why">{_esc(why)}</span>
          </div>
          <div class="r-act">
            {buy(d['dom_key'], d['dom_store_id'], d['dom_url'], t['dom_short'], not d['direct_pick'])}
            {buy('ali', 'aliexpress', d['ali_url'], t['ali_short'], d['direct_pick'])}
            <button type="button" class="r-more" data-more aria-expanded="false" aria-controls="d-{slug}">{h['more_btn']} {_use('down')}</button>
          </div>
          <p class="row-disc">{_esc(h['row_disc'])}</p>
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


def _render_facets(profiles: list[tuple[dict, dict]], lang: str) -> str:
    h = HUB[lang]
    n = len(profiles)
    n_direct = sum(1 for _, d in profiles if d["direct_pick"])
    route = [
        _opt("radio", 'name="route" value="all" checked', h["r_all"], "route:all", n),
        _opt("radio", 'name="route" value="dom"', h["r_dom"], "route:dom", n - n_direct),
        _opt("radio", 'name="route" value="ali"', h["r_ali"], "route:ali", n_direct),
    ]
    per_brand = Counter(it["brand"] for it, _ in profiles)
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
            <fieldset class="facet" data-brands><legend>{h['f_brand']}</legend><div class="opts">{''.join(brands)}</div>{more}</fieldset>"""


def _featured_strip(lang: str, up_to_lang: str) -> str:
    if lang == "ko":
        return (
            f'<section class="feat-strip" aria-label="핵심 호환 판별기">'
            f'<div><strong>맥북 모델·칩별 듀얼모니터 독 호환 판별기 (M1·M2·M3·M4)</strong>'
            f'<p>화면 복제(미러링) 실패 없이 내 맥북 칩셋·클램쉘·OTT 조건에 맞는 도킹스테이션 구성을 10초 만에 확인하세요.</p></div>'
            f'<div class="feat-actions"><a class="feat-btn" href="{up_to_lang}tools/macbook-dock-checker/">판별기 열기 →</a></div>'
            f'</section>'
        )
    return (
        f'<section class="feat-strip" aria-label="Compatibility Tools and Buying Guides">'
        f'<div><strong>MacBook Dual-Monitor Dock Checker &amp; 12 Engineering Buying Guides</strong>'
        f'<p>Verify M1–M4 external monitor limits, USB4 NVMe thermals, TSA 100Wh power banks, and Hall-effect/TMR controllers before buying.</p></div>'
        f'<div class="feat-actions">'
        f'<a class="feat-btn" href="{up_to_lang}tools/macbook-dock-checker/">MacBook Dock Checker →</a>'
        f'<a class="feat-btn sec" href="{up_to_lang}guides/">12 Buying Guides →</a>'
        f'</div></section>'
    )


def _render_hub(items: list[dict], cfg: dict, lang: str, cat: str | None = None,
                all_items: list[dict] | None = None) -> str:
    t, h = T[lang], HUB[lang]
    other = "en" if lang == "ko" else "ko"
    brand = cfg["site"]["brand_name"]
    all_items = items if all_items is None else all_items
    profiles = sorted(((it, _profile(it, lang)) for it in items), key=lambda x: (-x[1]["prio"], x[0]["id"]))
    n = len(profiles)
    latest = max((it.get("updated_at", "") for it in items), default="2026-11-26")
    cat_counts = Counter(it["category"] for it in all_items)
    cats = sorted(cat_counts, key=lambda c: (-cat_counts[c], _cat_label(c, lang)))
    per_brand = Counter(it["brand"] for it in items)

    if cat is None:
        up, pfx, cat_pfx, all_href, up_lang, path = "../", "p/", "c/", "./", "", f"/{lang}/"
        switch = f"{up}{other}/"
        alternates = {"ko": "/ko/", "en": "/en/", "x-default": "/"}
        title, desc, h1 = h["title"].format(brand=brand), h["desc"].format(n=n), h["h1"]
        models_sub = h["m_models_sub"].format(c=len(cats), b=len(per_brand))
        crumbs = ""
    else:
        slug, label = _cat_slug(cat), _cat_label(cat, lang)
        up, pfx, cat_pfx, all_href, up_lang, path = "../../../", "../../p/", "../", "../../", "../../", f"/{lang}/c/{slug}/"
        switch = f"{up}{other}/c/{slug}/"
        alternates = {"ko": f"/ko/c/{slug}/", "en": f"/en/c/{slug}/"}
        title = h["title_cat"].format(cat=label, n=n, brand=brand)
        desc = h["desc_cat"].format(cat=label, n=n, brands=", ".join(_ranked(per_brand)[:6]))
        h1 = h["h1_cat"].format(cat=label)
        models_sub = h["m_models_sub_cat"].format(b=len(per_brand), t=len(all_items))
        crumbs = (
            f'<nav aria-label="{"이동 경로" if lang == "ko" else "Breadcrumb"}"><ol class="crumbs">'
            f'<li><a href="{all_href}">{t["home"]}</a></li><li> / </li>'
            f'<li aria-current="page">{_esc(label)}</li></ol></nav>'
        )

    if cat is None:
        cat_links = [
            f'<li><a href="{all_href}" data-cat="all" aria-current="true">{_esc(_cat_label("all", lang))} '
            f'<span class="num" data-n="cat:all">{n}</span></a></li>'
        ] + [
            f'<li><a href="{cat_pfx}{_cat_slug(c)}/" data-cat="{_esc(c)}">{_esc(_cat_label(c, lang))} '
            f'<span class="num" data-n="cat:{_esc(c)}">{cat_counts[c]}</span></a></li>'
            for c in cats
        ]
    else:
        current = ' aria-current="page"'
        cat_links = [
            f'<li><a href="{all_href}">{_esc(_cat_label("all", lang))} <span class="num">{len(all_items)}</span></a></li>'
        ] + [
            f'<li><a href="{cat_pfx}{_cat_slug(c)}/"{current if c == cat else ""}>'
            f'{_esc(_cat_label(c, lang))} <span class="num">{cat_counts[c]}</span></a></li>'
            for c in cats
        ]

    n_direct = sum(1 for _, d in profiles if d["direct_pick"])
    n_local = n - n_direct
    dom_key = "coupang" if lang == "ko" else "amazon"
    summary_html = f"""
      <div class="sm"><dt>{h['m_models']}</dt><dd><span class="sm-v num">{h['m_models_v'].format(k=n)}</span><span class="sm-s">{models_sub}</span></dd></div>
      <div class="sm"><dt><span class="store {dom_key}">{h['m_local']}</span></dt><dd><a href="?route=dom" data-route-link="dom"><span class="sm-v num">{n_local}</span></a><span class="sm-s">{_esc(h['m_local_sub'])}</span></dd></div>
      <div class="sm"><dt><span class="store ali">{h['m_direct']}</span></dt><dd><a href="?route=ali" data-route-link="ali"><span class="sm-v num">{n_direct}</span></a><span class="sm-s">{_esc(h['m_direct_sub'])}</span></dd></div>
      <div class="sm"><dt>{h['m_filter']}</dt><dd><span class="sm-v">{_esc(h['m_filter_v'])}</span><span class="sm-s">{_esc(h['m_filter_sub'])}</span></dd></div>"""

    sort_html = "".join(f'<option value="{k}">{_esc(v)}</option>' for k, v in h["sorts"])
    view_html = "".join(
        f'<button type="button" data-view-btn="{k}" aria-pressed="{"true" if k == "list" else "false"}" title="{_esc(tip)}">'
        f'{_icon(k, 15)}<span class="lbl">{_esc(v)}</span></button>'
        for k, v, tip in h["views"]
    )
    strings = dict(h["js"])
    strings.update({"cats": {c: _cat_label(c, lang) for c in cats}, "route": {"ali": h["r_ali"], "dom": h["r_dom"]}})
    i18n = json.dumps(strings, ensure_ascii=False).replace("</", "<\\/")

    body = f"""
<body class="{lang} is-hub">
  {_legal_strip(lang)}
  {_site_header(lang, up, cfg, switch)}
  {ICON_SPRITE}
  <main class="wrap hub" data-hub data-view="list" data-scope="{_esc(cat or 'all')}" data-page-size="{PAGE_SIZE}">
    {crumbs}
    {_dest_banner(lang)}
    {_featured_strip(lang, up_lang)}
    <header class="idx-head">
      <h1>{_esc(h1)}</h1>
      <p class="stamp">{h['stamp'].format(date=_esc(latest))}</p>
    </header>
    <dl class="summary" aria-label="{h['summary_lbl']}">{summary_html}</dl>

    <div class="work" id="index">
      <div class="side-col">
        <nav class="catnav" aria-labelledby="cat-h">
          <h2 class="facet-h" id="cat-h">{h['cats']}</h2>
          <ul>{''.join(cat_links)}</ul>
        </nav>
        <aside class="facets" id="facets" aria-label="{h['filters']}" data-sheet>
          <div class="sheet-head"><strong>{h['filters']}</strong><button type="button" data-sheet-close aria-label="{h['close']}">{_icon('x', 18)}</button></div>
          <div class="facets-body">{_render_facets(profiles, lang)}</div>
          <div class="sheet-foot"><button type="button" data-reset>{h['reset']}</button><button type="button" class="primary" data-sheet-apply></button></div>
        </aside>
      </div>

      <div class="main">
        <div class="bar">
          <label class="search"><span class="sr-only">{h['search_lbl']}</span>{_icon('search', 16)}<input type="search" data-search placeholder="{_esc(h['search_ph'])}" autocomplete="off"><kbd>/</kbd></label>
          <label class="sort"><span class="sr-only">{h['sort_lbl']}</span><select data-sort>{sort_html}</select>{_icon('down', 15)}</label>
          <button type="button" class="fbtn" data-sheet-open aria-controls="facets">{_icon('filter', 16)}<span>{h['filters']}</span><b class="num" data-fcount hidden>0</b></button>
        </div>
        <div class="status">
          <p class="status-text num" data-status aria-live="polite"></p>
          <div class="on-chips" data-chips></div>
          <div class="seg" role="group" aria-label="{h['view_lbl']}">{view_html}</div>
        </div>
        <h2 class="sr-only">{h['list_h']}</h2>
        <ol class="rows" data-rows>{''.join(_render_row(it, lang, pfx) for it, _ in profiles)}</ol>
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


def _related(it: dict, items: list[dict], n: int = 3) -> list[dict]:
    others = [x for x in items if x["id"] != it["id"]]
    same = [x for x in others if x["category"] == it["category"]]
    rest = [x for x in others if x["category"] != it["category"]]
    return (same + rest)[:n]


def _render_detail_page(it: dict, lang: str, cfg: dict, items: list[dict] | None = None) -> str:
    t, d, loc = T[lang], _profile(it, lang), it[lang]
    brand = cfg["site"]["brand_name"]
    up = "../../../"
    slug = product_slug(it["id"])
    other = "en" if lang == "ko" else "ko"
    cat = it["category"]

    # Manufacturer Reference MSRP sits ONLY inside the specification table with explicit source & date (Debate 3 Consensus #1)
    msrp_row = ""
    if lang == "ko" and it.get("msrp_krw"):
        msrp_row = (
            f'<tr class="msrp-ref"><th scope="row">제조사 출시 참고 출고가 (MSRP)</th>'
            f'<td>{int(it["msrp_krw"]):,}원 <small>(출처: 제조사 공식 사양 참고치 · 확인일 {_esc(it.get("msrp_checked_at", "2026-11-26"))} · 실제 쇼핑몰 판매가 및 할인 기준가가 아님)</small></td></tr>'
        )
    elif lang == "en" and it.get("msrp_usd"):
        msrp_row = (
            f'<tr class="msrp-ref"><th scope="row">Manufacturer Reference MSRP</th>'
            f'<td>USD {float(it["msrp_usd"]):,.2f} <small>(Manufacturer launch spec reference · checked {_esc(it.get("msrp_checked_at", "2026-11-26"))} · NOT current store price)</small></td></tr>'
        )

    spec_rows = "".join(
        f'<tr><th scope="row">{_esc(_spec_label(k, lang))}</th><td>{_esc(v)}</td></tr>'
        for k, v in it.get("specs", {}).items()
    ) + msrp_row

    pros_li = "".join(f"<li>{_esc(x)}</li>" for x in loc.get("pros", []))
    cons_li = "".join(f"<li>{_esc(x)}</li>" for x in loc.get("cons", []))

    if lang == "ko":
        title = f"{loc['title']} — 국내 배송 vs 알리 직구 단점·통관 비교 | {brand}"
        h_cust, h_spec, h_pc = "수령국별 통관 · 발송 조건 체크리스트", "전체 기술 사양 (참고 출고가 포함)", "장점과 실사용 단점"
        pros_h, cons_h = "장점", "구매 전 꼭 확인할 단점"
        rel_h, decide_h = "같은 분류 검수 기어", "구매 경로 판단"
        stamp = f"스펙 검수일 {_esc(it.get('updated_at', ''))} · 최종 판매가·할인·재고는 판매 페이지에서 확인하세요."
        switch = f"English page {_icon('arrow', 14)}"
        dom_btn_lbl, ali_btn_lbl = "쿠팡 실시간 가격·옵션 확인", "알리익스프레스 조건 확인"
    else:
        title = f"{loc['title']} — Specs, Caveats & Buying Guide | {brand}"
        h_cust, h_spec, h_pc = "Destination Customs & Fulfillment Checklist", "Technical Specifications", "Strengths & Real-World Caveats"
        pros_h, cons_h = "Strengths", "Real-World Caveats"
        rel_h, decide_h = "Related Vetted Hardware", "Buying Decision"
        stamp = f"Specs reviewed {_esc(it.get('updated_at', ''))}. Confirm live price, seller terms, and shipping on the store page."
        switch = f"한국어 페이지 {_icon('arrow', 14)}"
        dom_btn_lbl, ali_btn_lbl = "Check Price on Amazon", "Check AliExpress"

    dock_callout = ""
    if cat == "hubs":
        dock_href = "../../tools/macbook-dock-checker/"
        dock_txt = (
            "맥북 M1·M2·M3·M4 모델별 듀얼모니터 호환 여부를 판별기에서 먼저 확인하세요 →"
            if lang == "ko"
            else "Using a MacBook? Verify M1/M2/M3/M4 dual-monitor compatibility in our interactive checker first →"
        )
        dock_callout = f'<p style="margin-top:14px;font-weight:700;font-size:14px"><a href="{dock_href}">{dock_txt}</a></p>'

    rel_items = _related(it, items or [], 3)
    related_html = ""
    if rel_items:
        rel_cards = []
        for r in rel_items:
            rd = _profile(r, lang)
            rel_cards.append(f"""
        <article class="rel">
          <span class="tag" style="align-self:flex-start">{_esc(_cat_label(r['category'], lang))} · {_esc(r['brand'])}</span>
          <h3><a href="../{product_slug(r['id'])}/">{_esc(r[lang]['title'])}</a></h3>
          {_pick_badge(rd, lang)}
        </article>""")
        related_html = f'<section class="related" aria-labelledby="rel-h"><h2 id="rel-h">{rel_h}</h2><div class="rel-grid">{"".join(rel_cards)}</div></section>'

    body = f"""
<body class="{lang}">
  {_legal_strip(lang)}
  {_site_header(lang, up, cfg, f"{up}{other}/p/{slug}/")}
  <main class="wrap">
    <nav aria-label="{'이동 경로' if lang == 'ko' else 'Breadcrumb'}">
      <ol class="crumbs">
        <li><a href="../../">{t['home']}</a></li><li> / </li>
        <li><a href="../../c/{_cat_slug(cat)}/">{_esc(_cat_label(cat, lang))}</a></li><li> / </li>
        <li aria-current="page">{_esc(_short_name(it))}</li>
      </ol>
    </nav>
    {_dest_banner(lang)}

    <div class="detail">
      <header class="d-intro">
        <span class="tag">{_esc(it['brand'])} · {_esc(it['model'])}</span>
        <h1>{_esc(loc['title'])}</h1>
        <p class="dek">{_esc(loc['summary'])}</p>
        {_chips(it, 4)}
        {dock_callout}
      </header>

      <aside class="d-aside" aria-label="{decide_h}">
        <div class="panel decide">
          <div class="decide-title">{decide_h}</div>
          {_pick_badge(d, lang)}
          <p class="decide-verdict">{_esc(loc['verdict'])}</p>
          {_battle(it, d, lang)}
          <div class="actions">
            <a class="btn btn-{d['dom_key']}" data-aff="{d['dom_key']}" data-store="{d['dom_store_id']}" href="{_esc(d['dom_url'])}" target="_blank" rel="nofollow sponsored noopener">{dom_btn_lbl} {_icon('out', 15)}</a>
            <a class="btn btn-ali" data-aff="ali" data-store="aliexpress" href="{_esc(d['ali_url'])}" target="_blank" rel="nofollow sponsored noopener">{ali_btn_lbl} {_icon('out', 15)}</a>
          </div>
          <p class="btn-disc">{_esc(t['btn_disc'])}</p>
          <p class="decide-stamp">{stamp}</p>
          <a class="decide-switch" href="{up}{other}/p/{slug}/" hreflang="{other}">{switch}</a>
        </div>
      </aside>

      <div class="d-body">
        <section class="section" aria-labelledby="h-cust">
          <h2 id="h-cust">{h_cust}</h2>
          <div class="customs-note">
            <strong>{'통관 · 발송지 체크' if lang == 'ko' else 'Customs & Fulfillment Note'}</strong>
            <span>{_esc(d['customs_note'])}</span>
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
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    head = _head(lang=lang, title=title, description=loc["summary"], up=up, cfg=cfg, path=f"/{lang}/p/{slug}/",
                 alternates={"ko": f"/ko/p/{slug}/", "en": f"/en/p/{slug}/"})
    return head + body


def _render_root_gateway(cfg: dict, items: list[dict] | None = None) -> str:
    items = items or []
    brand = _esc(cfg["site"]["brand_name"])
    n_models = len(items)
    n_cats = len({it["category"] for it in items})
    return f"""{_head(lang="en", title=f"{cfg['site']['brand_name']} — Desk & USB-C Hardware Compatibility & Buying Hub",
             description="Compare vetted standalone desk and USB-C hardware with honest caveats, compatibility checkers, and destination-specific customs rules.",
             up="", cfg=cfg, path="/", alternates={"ko": "/ko/", "en": "/en/", "x-default": "/"})}
<body>
  <header class="site-head">
    <div class="wrap">
      <a class="brand" href="./">{BRAND_MARK}<span>{brand}</span></a>
      <nav class="head-nav" aria-label="Primary">
        <a class="nav-hi" href="en/tools/macbook-dock-checker/">MacBook Dock Checker</a>
        <a href="en/guides/">12 Buying Guides</a>
        <a href="policy/">Policy · 정책</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="gate-hero">
      <h1 style="font-size:clamp(1.7rem,1.2rem + 1.8vw,2.5rem);font-weight:790;">{brand}</h1>
      <p style="margin-top:10px;color:var(--ink-2)">동일 모델 데스크·USB-C 기어 호환성 판별 및 국내 배송 vs 해외직구 조건 비교 / Vetted hardware compatibility &amp; buying hub</p>
    </section>
    <div class="regions">
      <section class="region" data-region="ko">
        <div class="region-head"><div><h2><a href="ko/" hreflang="ko">🇰🇷 한국어 허브 (KR)</a></h2><p style="color:var(--ink-2);font-size:14px;margin-top:4px">쿠팡 국내 배송 vs 알리익스프레스 직구 · 통관/단점 검수</p></div><span class="suggest" hidden>브라우저 언어 기준 추천</span></div>
        <div class="region-stats">
          <div><span>검수 모델</span><strong>{n_models}종</strong></div>
          <div><span>분류</span><strong>{n_cats}개 카테고리</strong></div>
          <div><span>핵심 도구</span><strong>맥북 독 판별기</strong></div>
        </div>
        <span style="font-weight:700;font-size:14.5px">한국어 비교 허브 열기 {_icon('arrow', 16)}</span>
      </section>
      <section class="region" data-region="en">
        <div class="region-head"><div><h2><a href="en/" hreflang="en">🌐 Global Hub (EN)</a></h2><p style="color:var(--ink-2);font-size:14px;margin-top:4px">Amazon US vs Direct Import · 12 Engineering Buying Guides</p></div><span class="suggest" hidden>Suggested for you</span></div>
        <div class="region-stats">
          <div><span>Vetted gear</span><strong>{n_models} models</strong></div>
          <div><span>Guides</span><strong>12 deep dives</strong></div>
          <div><span>Interactive</span><strong>Dock Checker</strong></div>
        </div>
        <span style="font-weight:700;font-size:14.5px">Open Global Hub {_icon('arrow', 16)}</span>
      </section>
    </div>
  </main>
  <footer class="site-foot"><div class="wrap"><p>{_esc(DISCLOSURE_EN)}</p><nav class="foot-links" aria-label="Footer"><a href="ko/">한국어 허브</a><a href="en/">Global Hub</a><a href="en/guides/">Guides</a><a href="policy/">Policy</a></nav></div></footer>
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
    return f"""{_head(lang="en", title=f"Privacy Policy, Pricing Architecture & Affiliate Disclosure | {cfg['site']['brand_name']}",
             description="Affiliate disclosures, zero-stale price policy, and destination customs guidance for GearCompare Hub.",
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
      <h1>Affiliate Disclosure, Zero-Stale Pricing &amp; Privacy Policy</h1>
      <p>{brand} is an independent hardware compatibility and buying-decision publication.</p>

      <h2>1. Affiliate Disclosure (US / Global)</h2>
      <p><strong>As an Amazon Associate I earn from qualifying purchases.</strong></p>
      <p>{brand} also participates in the AliExpress Portals Affiliate Program. Clicking outbound links to Amazon.com or AliExpress.com may earn an advertising commission at no extra cost to you.</p>

      <section lang="ko">
        <h2>2. 한국어 제휴 마케팅 대가성 고지</h2>
        <p>{_esc(DISCLOSURE_KO)}</p>
      </section>

      <h2>3. Zero-Stale Pricing &amp; Manufacturer Reference MSRP Policy</h2>
      <p>To prevent misleading price discrepancies and strictly honor retailer API caching policies, static HTML pages, structured metadata, and RSS feeds do not store or display unverified retailer prices or percentage-discount claims. Any MSRP shown inside a technical specification table is strictly a manufacturer launch reference with source attribution, never a live store offer. Where official retailer APIs are enabled, offers include an explicit fetch timestamp and automatic server/client expiration (fail-closed).</p>

      <h2>4. Editorial Gatekeeper &amp; Privacy</h2>
      <p>Every model passes deterministic verification that blocks accessory-only mismatches and requires documented real-world drawbacks. {brand} collects no personal registration data or PII; outbound affiliate tags carry only anonymous channel/region identifiers.</p>
    </article>
  </main>
  <footer class="site-foot"><div class="wrap"><p>© {datetime.now(timezone.utc).year} {brand}</p><nav class="foot-links" aria-label="Footer"><a href="../ko/">한국어 허브</a><a href="../en/">Global Hub</a><a href="../">Home</a></nav></div></footer>
</body>
</html>
"""


def _render_sitemap(items: list[dict], cfg: dict) -> str:
    base = cfg["site"]["base_url"].rstrip("/")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [
        f"{base}/",
        f"{base}/ko/",
        f"{base}/en/",
        f"{base}/policy/",
        f"{base}/ko/tools/macbook-dock-checker/",
        f"{base}/en/tools/macbook-dock-checker/",
        f"{base}/en/guides/",
    ]
    for g in GUIDES_EN:
        urls.append(f"{base}/en/guides/{g['slug']}/")
    for cat in sorted({it["category"] for it in items}):
        urls.append(f"{base}/ko/c/{_cat_slug(cat)}/")
        urls.append(f"{base}/en/c/{_cat_slug(cat)}/")
    for it in items:
        slug = product_slug(it["id"])
        urls.append(f"{base}/ko/p/{slug}/")
        urls.append(f"{base}/en/p/{slug}/")
    entries = "\n".join(f"  <url><loc>{_esc(u)}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _clean_dist(dist_dir: Path) -> None:
    target = dist_dir.resolve()
    if target == Path(target.anchor) or (target / "run_pipeline.py").exists() or (target / ".git").exists():
        raise ValueError(f"Refusing to wipe suspicious dist_dir: {target}")
    if not target.exists():
        return
    for child in target.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def build_site(approved_items: list[dict], cfg: dict, dist_dir: Path) -> dict:
    """Generate clean-URL static pages for root, hubs, category pages, details, Dock Checker, 12 Guides, policy, and sitemap."""
    _clean_dist(dist_dir)
    items_by_id = {it["id"]: it for it in approved_items}

    css = SHARED_CSS.strip().replace("__PAGE_NEXT__", str(PAGE_SIZE + 1))
    _write(dist_dir / "assets" / "style.css", css + "\n")
    _write(dist_dir / "assets" / "app.js", APP_JS.strip() + "\n")
    _write(dist_dir / "index.html", _render_root_gateway(cfg, approved_items))
    _write(dist_dir / "policy" / "index.html", _render_policy_page(cfg))
    _write(dist_dir / "ko" / "index.html", _render_hub(approved_items, cfg, "ko"))
    _write(dist_dir / "en" / "index.html", _render_hub(approved_items, cfg, "en"))

    # Topic 1 Unanimous Consensus: MacBook Dual-Monitor Dock Compatibility Checker (KO & EN)
    for lang in ("ko", "en"):
        _write(
            dist_dir / lang / "tools" / "macbook-dock-checker" / "index.html",
            render_dock_checker_page(
                lang=lang,
                items_by_id=items_by_id,
                cfg=cfg,
                head_fn=_head,
                legal_fn=_legal_strip,
                header_fn=_site_header,
                footer_fn=_site_footer,
                slug_fn=product_slug,
            ),
        )

    # Topic 2 Unanimous Consensus: 12 Non-Template Hardware Decision Guides (/en/guides/ + /en/guides/<slug>/)
    _write(
        dist_dir / "en" / "guides" / "index.html",
        render_en_guides_index(
            cfg=cfg,
            head_fn=_head,
            legal_fn=_legal_strip,
            header_fn=_site_header,
            footer_fn=_site_footer,
        ),
    )
    for g in GUIDES_EN:
        _write(
            dist_dir / "en" / "guides" / g["slug"] / "index.html",
            render_en_guide_detail(
                guide=g,
                items_by_id=items_by_id,
                cfg=cfg,
                head_fn=_head,
                legal_fn=_legal_strip,
                header_fn=_site_header,
                footer_fn=_site_footer,
                slug_fn=product_slug,
            ),
        )

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

    total_pages = 4 + 2 + (1 + len(GUIDES_EN)) + (len(categories) * 2) + (len(approved_items) * 2)
    return {
        "approved_products_rendered": len(approved_items),
        "guides_rendered": len(GUIDES_EN),
        "tools_rendered": 2,
        "total_html_pages": total_pages,
        "output_dir": str(dist_dir),
    }
