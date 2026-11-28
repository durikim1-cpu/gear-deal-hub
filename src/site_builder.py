"""Zero-dependency static site generator for Korean (Coupang vs Ali) & Global (Amazon vs Ali) hubs.

Pages render with the standard library alone. Pillow, when installed (the build already needs it for pins),
trims each product photo into a figure-plate derivative; without it the original 360x360 files are used as-is.

Editorial and compliance rules every page follows:
- Zero unverified static retailer prices or % spread badges in HTML, JSON-LD, meta, or feeds. The only price-like
  numbers are (a) the Manufacturer Reference MSRP, always labelled as a launch reference, and (b) entries from
  data/live_offers_cache.json, which carry an observation date, an expiry (`data-expires-at`, hidden client-side
  once passed) and an honest source label: community-spotted benchmark vs official AliExpress API offer.
- Destination country separated from UI language (Ship to KR: US $200 list-clearance vs $150 other / Ship to US: domestic vs import charges).
- Fail-closed live API offer client hook (with open-tab periodic expiry re-check) + PII-free channel tracking mapper.
- Hubs open with the Live Deal & Compatibility Situation Board (sale-window traffic light, promo-code tiers,
  trap-cut filter chips). Tools: MacBook Dock Checker + AliExpress Promo & Customs Calculator (KO/EN).
  Content: 12 buying guides per language and 15 head-to-head VS battles per language, all hreflang-paired.
"""

from __future__ import annotations

import html
import io
import json
import re
import shutil
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

from src.affiliate import (
    BUTTON_DISCLOSURE_EN,
    BUTTON_DISCLOSURE_KO,
    DISCLOSURE_EN,
    DISCLOSURE_KO,
)
from src.deal_sniper import pick_live_offer
from src.tools_and_guides import (
    GUIDES_BY_LANG,
    GUIDES_EN,
    SALE_COPY,
    SALE_TZ_HOURS,
    _tool_strip,
    active_promo,
    kr_customs_anchor,
    load_promo_tiers,
    promo_events_for_lang,
    render_dock_checker_page,
    render_guide_detail,
    render_guides_index,
    render_promo_calculator_page,
    sale_reference_date,
    sale_signal,
)
from src.vs_battles import active_pairs, render_vs_detail, render_vs_index, rivals_by_product, vs_name

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
    "truck": '<path d="M2.5 6.5h11v9h-11z"/><path d="M13.5 9.5h4l3 3v3h-7z"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
    "globe": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.4 3.7 5.2 3.7 8.5s-1.2 6.1-3.7 8.5c-2.5-2.4-3.7-5.2-3.7-8.5S9.5 5.9 12 3.5Z"/>',
    "caution": '<path d="M12 4 21 19.5H3L12 4Z"/><path d="M12 10v4.5M12 17.2v.3"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "dual": '<rect x="2.5" y="6" width="9" height="7" rx="1"/><rect x="12.5" y="6" width="9" height="7" rx="1"/><path d="M7 13v3.5M17 13v3.5M4.5 17.5h15"/>',
    "calc": '<rect x="5" y="3.5" width="14" height="17" rx="2"/><path d="M8.5 7.5h7M8.5 12h.01M12 12h.01M15.5 12h.01M8.5 16h.01M12 16h.01M15.5 16h.01"/>',
    "scale": '<path d="M12 4v16M7 20h10M5 8h14"/><path d="m5 8-2.5 6a2.5 2.5 0 0 0 5 0L5 8ZM19 8l-2.5 6a2.5 2.5 0 0 0 5 0L19 8Z"/>',
}


def _icon(name: str, size: int = 16) -> str:
    return (
        f'<svg class="i" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_ICON_PATHS[name]}</svg>'
    )


_SPRITE_ICONS = ("out", "down", "arrow", "truck", "globe", "caution")
ICON_SPRITE = (
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
    + "".join(f'<symbol id="i-{n}" viewBox="0 0 24 24">{_ICON_PATHS[n]}</symbol>' for n in _SPRITE_ICONS)
    + "</svg>"
)


def _use(name: str, size: int = 14) -> str:
    return f'<svg class="i" width="{size}" height="{size}" aria-hidden="true"><use href="#i-{name}"/></svg>'


BRAND_MARK = (
    '<svg class="mark" width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">'
    '<rect width="26" height="26" rx="6" fill="#74E0CA"/>'
    '<rect x="6" y="8.5" width="14" height="2.6" rx="1.3" fill="#0A2422"/>'
    '<rect x="6" y="14.9" width="8" height="2.6" rx="1.3" fill="#0A2422"/></svg>'
)

SHARED_CSS = """
:root {
  --ground: #ECEFF0;
  --sheet: #FFFFFF;
  --plate: #EBEEEF;
  --sunk: #F3F5F6;
  --ink: #0F1B1F;
  --ink-2: #33434A;
  --muted: #586970;
  --line: #D9DFE1;
  --line-2: #BCC7CB;
  --shell: #0F302E;
  --shell-deep: #0A2422;
  --shell-line: #2A5550;
  --on-shell: #F0F6F4;
  --on-shell-2: #A9C6C0;
  --mint: #74E0CA;
  --action: #0A7A6C;
  --action-hi: #075E54;
  --action-tint: #E0F0ED;
  --action-line: #A9D5CD;
  --warn-ink: #734000;
  --warn-text: #5A3E12;
  --warn-bg: #FFF4DD;
  --warn-line: #E8BE66;
  --info: #1F4E96;
  --info-tint: #E8EFF9;
  --info-line: #B4C8E6;
  --coupang: #2D5BE3;
  --amazon: #F59A0B;
  --ali: #D8421D;
  --r-1: 6px;
  --r-2: 8px;
  --r-3: 12px;
  --gut: 20px;
  --head-h: 60px;
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
  --ic-check: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m5 12.5 4.5 4.5L19 7.5'/%3E%3C/svg%3E");
  --ic-caution: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 4 21 19.5H3L12 4Z'/%3E%3Cpath d='M12 10v4.5M12 17.2v.3'/%3E%3C/svg%3E");
  --ic-hold: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='8.5'/%3E%3Cpath d='M10 9v6M14 9v6'/%3E%3C/svg%3E");
  color-scheme: light;
}
*, *::before, *::after { box-sizing: border-box; }
* { margin: 0; padding: 0; min-width: 0; }
[hidden] { display: none !important; }
html { -webkit-text-size-adjust: 100%; scroll-padding-top: calc(var(--head-h) + 16px); }
body {
  font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  background: var(--ground);
  color: var(--ink);
  font-size: 0.9375rem;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  word-break: keep-all;
  overflow-wrap: break-word;
  caret-color: var(--action);
  accent-color: var(--action);
}
::selection { background: #BDE6DE; color: var(--ink); }
a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: 3px; }
button, input, select { font: inherit; color: inherit; }
button { cursor: pointer; }
:focus-visible { outline: 2px solid var(--action); outline-offset: 2px; border-radius: 4px; }
.num { font-variant-numeric: tabular-nums; }
.i { flex: none; vertical-align: -0.15em; fill: none; stroke: currentColor; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
.wrap { max-width: var(--wrap, 1200px); margin: 0 auto; padding: 0 var(--gut); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

/* Masthead: disclosure strip + shell header */
.legal-strip { background: var(--shell-deep); color: var(--on-shell-2); font-size: 0.75rem; line-height: 1.5; }
.legal-strip .wrap { display: flex; gap: 10px; align-items: baseline; padding-top: 7px; padding-bottom: 7px; }
.legal-tag { flex: none; font-size: 0.6875rem; font-weight: 700; color: var(--on-shell); border: 1px solid var(--shell-line); border-radius: 4px; padding: 0 6px; line-height: 1.6; }
.site-head { position: sticky; top: 0; z-index: 30; background: var(--shell); color: var(--on-shell); }
.site-head .wrap { display: flex; align-items: center; justify-content: space-between; gap: 8px 16px; min-height: 60px; }
.site-head :focus-visible { outline-color: var(--mint); }
.brand { display: inline-flex; align-items: center; gap: 10px; flex: none; max-width: 100%; text-decoration: none; font-weight: 750; font-size: 1.0625rem; letter-spacing: -0.015em; white-space: nowrap; color: var(--on-shell); }
.brand-region { font-size: 0.6875rem; font-weight: 700; letter-spacing: 0.04em; color: var(--mint); border: 1px solid var(--shell-line); border-radius: 4px; padding: 1px 6px; }
.head-nav { display: flex; align-items: center; flex-wrap: wrap; gap: 2px; font-size: 0.8438rem; }
.head-nav a { display: inline-flex; align-items: center; gap: 6px; flex: none; max-width: 100%; text-decoration: none; padding: 7px 10px; border-radius: var(--r-1); color: var(--on-shell-2); font-weight: 600; white-space: nowrap; }
.head-nav a:hover { background: var(--shell-line); color: var(--on-shell); }
.head-nav a.nav-hi { color: var(--shell-deep); background: var(--mint); font-weight: 700; margin-right: 4px; }
.head-nav a.nav-hi:hover { background: #97EBD9; color: var(--shell-deep); }
.head-nav a.tg { border: 1px solid var(--shell-line); color: var(--on-shell); margin-left: 4px; }

/* Shared atoms */
.sheet, .panel { background: var(--sheet); border: 1px solid var(--line); border-radius: var(--r-2); }
.sel { position: relative; display: block; max-width: 100%; }
.sel select { -webkit-appearance: none; appearance: none; display: block; width: 100%; max-width: 100%; height: 38px; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); padding: 0 34px 0 12px; font-size: 0.8438rem; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; cursor: pointer; box-shadow: 0 1px 0 rgba(15, 27, 31, 0.05); transition: border-color 0.15s; }
.sel select:hover { border-color: var(--ink-2); }
.sel > .i { position: absolute; right: 11px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; max-width: 100%; padding: 9px 14px; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); color: var(--ink); font-weight: 700; font-size: 0.875rem; line-height: 1.3; text-align: center; text-decoration: none; overflow-wrap: anywhere; transition: background-color 0.15s, border-color 0.15s; }
.btn:hover { border-color: var(--ink-2); background: var(--sunk); }
.btn:active { transform: translateY(1px); }
.btn.is-first, .btn-primary { background: var(--action); border-color: var(--action); color: #fff; }
.btn.is-first:hover, .btn-primary:hover { background: var(--action-hi); border-color: var(--action-hi); }
.btn-s { min-height: 38px; padding: 6px 12px; font-size: 0.8438rem; }
.sdot { flex: none; width: 9px; height: 9px; border-radius: 2px; background: var(--c, var(--ink)); }
.is-first > .sdot, .is-pick > .sdot { width: 13px; height: 13px; border: 3px solid #fff; border-radius: 3px; }
.coupang, .btn-coupang { --c: var(--coupang); }
.amazon, .btn-amazon { --c: var(--amazon); }
.ali, .btn-ali { --c: var(--ali); }
.store { display: inline-flex; align-items: center; gap: 7px; font-size: 0.8438rem; font-weight: 700; }
.store::before { content: ""; flex: none; width: 9px; height: 9px; border-radius: 2px; background: var(--c, var(--ink)); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; }
.chips li, .pill { max-width: 100%; font-size: 0.75rem; font-weight: 600; line-height: 18px; color: var(--ink-2); background: var(--sunk); border: 1px solid var(--line); border-radius: 5px; padding: 2px 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-variant-numeric: tabular-nums; }
.pill.code { background: var(--sheet); border-color: var(--line-2); color: var(--ink); font-weight: 700; }
.desig { font-size: 0.7813rem; line-height: 1.5; font-weight: 550; color: var(--muted); overflow-wrap: anywhere; }
.desig b { color: var(--ink-2); font-weight: 700; }
.route { display: inline-flex; align-items: flex-start; gap: 6px; max-width: 100%; font-size: 0.8125rem; font-weight: 700; line-height: 1.4; color: var(--ink); }
.route .i { margin-top: 1px; color: var(--action-hi); }
.why { display: block; font-size: 0.75rem; line-height: 1.45; color: var(--muted); }
.btn-disc { margin-top: 10px; font-size: 0.75rem; line-height: 1.5; color: var(--muted); }
.notice { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 4px 10px; padding: 12px 14px; border: 1px solid var(--warn-line); border-radius: var(--r-2); background: var(--warn-bg); color: var(--warn-text); font-size: 0.8438rem; line-height: 1.55; }
.notice > .i { margin-top: 2px; color: var(--warn-ink); }
.notice strong { display: block; color: var(--warn-ink); }

/* Figure plate: every product photo sits in the same tinted stage */
.plate { position: relative; display: block; flex: none; aspect-ratio: 1; background: var(--plate); border-radius: var(--r-2); overflow: hidden; isolation: isolate; }
.plate img { position: absolute; inset: 11%; width: 78%; height: 78%; object-fit: contain; mix-blend-mode: multiply; transition: transform 0.25s var(--ease); }
a.plate:hover img { transform: scale(1.04); }
.plate-fb { position: absolute; inset: 0; display: grid; place-items: center; padding: 8px; font-size: 0.6875rem; font-weight: 700; line-height: 1.2; color: var(--muted); text-align: center; overflow-wrap: anywhere; }
.plate-cap { position: absolute; left: 12px; right: 12px; bottom: 9px; font-size: 0.75rem; font-weight: 650; line-height: 1.3; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-variant-numeric: tabular-nums; }

/* Destination conditions + featured tool */
.dest-bar { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; gap: 8px 18px; margin-top: 12px; background: var(--sheet); border: 1px solid var(--line); border-radius: var(--r-2); padding: 10px 14px; font-size: 0.8438rem; }
.dest-pick { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; font-weight: 700; }
.dest-pick > span:first-child { flex: none; max-width: 100%; }
.dest-pick .sel { flex: 0 1 auto; width: 196px; }
.dest-rule { color: var(--ink-2); line-height: 1.5; }
.feat-strip { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 10px 14px; margin-top: 10px; background: var(--action-tint); border: 1px solid var(--action-line); border-radius: var(--r-2); padding: 12px 14px; }
.feat-ic { display: grid; place-items: center; width: 40px; height: 40px; border-radius: var(--r-1); background: var(--sheet); border: 1px solid var(--action-line); color: var(--action-hi); }
.feat-strip strong { display: block; font-size: 0.9375rem; line-height: 1.4; }
.feat-strip p { margin-top: 1px; font-size: 0.8125rem; line-height: 1.5; color: var(--ink-2); }
.feat-actions { display: flex; flex-wrap: wrap; gap: 8px; }

/* Index */
.is-hub { --wrap: 1320px; }
.idx-head { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 6px 24px; padding: 22px 0 12px; }
.idx-head h1 { font-size: 1.5rem; line-height: 1.3; letter-spacing: -0.022em; font-weight: 760; text-wrap: balance; }
.stamp { display: flex; flex-wrap: wrap; gap: 2px 14px; font-size: 0.7813rem; color: var(--muted); }
.stamp b { color: var(--ink-2); font-weight: 700; }
.summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-top: 2px solid var(--ink); border-radius: 0 0 var(--r-2) var(--r-2); overflow: hidden; }
.sm { background: var(--sheet); padding: 10px 14px 12px; }
.sm dt { font-size: 0.75rem; font-weight: 650; line-height: 1.5; color: var(--muted); }
.sm dt .store { font-size: inherit; font-weight: inherit; }
.sm-v { display: inline-block; font-size: 1.1875rem; font-weight: 760; line-height: 1.35; letter-spacing: -0.01em; }
.sm-s { display: block; font-size: 0.75rem; line-height: 1.45; color: var(--ink-2); }
.sm a { display: inline-flex; align-items: center; gap: 6px; color: var(--action-hi); text-decoration: underline; text-decoration-color: var(--action-line); text-underline-offset: 4px; }
.sm a:hover { text-decoration-color: currentColor; }

.work { display: grid; grid-template-columns: 228px minmax(0, 1fr); gap: 0 28px; margin-top: 18px; align-items: start; }
.side-col { position: sticky; top: calc(var(--head-h) + 12px); max-height: calc(100dvh - var(--head-h) - 24px); overflow-y: auto; margin-top: 10px; padding: 0 4px 20px 0; scrollbar-width: thin; scrollbar-color: var(--line-2) transparent; }
.facet-h, .facet legend { display: block; padding: 0 8px 6px; font-size: 0.75rem; font-weight: 700; color: var(--ink-2); }
.catnav ul { list-style: none; }
.catnav a { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 32px; padding: 4px 8px; border-radius: var(--r-1); font-size: 0.875rem; font-weight: 550; color: var(--ink-2); text-decoration: none; }
.catnav a:hover { background: #DDE3E5; color: var(--ink); }
.catnav .num, .opt .num { flex: none; font-size: 0.75rem; color: var(--muted); }
.catnav a[aria-current] { background: var(--shell); color: var(--on-shell); font-weight: 700; }
.catnav a[aria-current] .num { color: var(--on-shell-2); }
.catnav a.is-zero, .opt.is-zero { opacity: 0.45; }
.facet { border: 0; margin-top: 22px; padding: 0; }
.opt { display: flex; align-items: center; gap: 8px; min-height: 32px; padding: 4px 8px; border-radius: var(--r-1); font-size: 0.875rem; color: var(--ink-2); cursor: pointer; }
.opt:hover { background: #DDE3E5; color: var(--ink); }
.opt input { flex: none; width: 16px; height: 16px; cursor: pointer; }
.opt .lbl { flex: 1; overflow-wrap: anywhere; }
.opt:has(input:checked) { color: var(--ink); font-weight: 650; }
.facet[data-brands]:not([data-expanded]) .opt.is-extra:not(:has(input:checked)) { display: none; }
.facet-more { display: inline-flex; margin: 4px 0 0 8px; border: 0; background: none; padding: 4px 0; font-size: 0.8125rem; font-weight: 650; color: var(--action-hi); text-decoration: underline; text-underline-offset: 3px; }
.sheet-head, .sheet-foot, .scrim, .fbtn { display: none; }

.main { container: idx / inline-size; }
.bar { position: sticky; top: var(--head-h); z-index: 10; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 10px 0; background: var(--ground); }
.search { position: relative; flex: 1 1 240px; }
.search > .i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.search input { width: 100%; height: 42px; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); padding: 0 40px 0 36px; font-size: 0.9063rem; text-overflow: ellipsis; box-shadow: 0 1px 0 rgba(15, 27, 31, 0.05); transition: border-color 0.15s; }
.search input::placeholder { color: var(--muted); }
.search input:hover { border-color: var(--ink-2); }
.search kbd { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); font-family: inherit; font-size: 0.6875rem; font-weight: 700; line-height: 1; color: var(--muted); border: 1px solid var(--line-2); border-radius: 4px; padding: 3px 6px; background: var(--sunk); pointer-events: none; }
.search input:focus + kbd, .search input:not(:placeholder-shown) + kbd { display: none; }
.sort { flex: 0 1 216px; }
.sort select { height: 42px; }
.fbtn { align-items: center; gap: 6px; flex: none; height: 42px; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); padding: 0 12px; font-size: 0.875rem; font-weight: 650; }
.fbtn b { display: inline-grid; place-items: center; min-width: 18px; height: 18px; border-radius: 9px; background: var(--action); color: #fff; font-size: 0.6875rem; padding: 0 5px; }

.status { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; min-height: 34px; margin-bottom: 10px; font-size: 0.8125rem; color: var(--muted); }
.status-text { flex: 1 1 auto; }
.status-text strong, .pager-status strong { color: var(--ink); font-weight: 700; }
.on-chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; order: 3; flex: 1 0 100%; }
.on-chips:empty { display: none; }
.chip-x { display: inline-flex; align-items: center; gap: 4px; max-width: 100%; min-height: 28px; border: 1px solid var(--line-2); border-radius: 999px; background: var(--sheet); padding: 2px 6px 2px 11px; font-size: 0.7813rem; font-weight: 600; text-align: left; overflow-wrap: anywhere; }
.chip-x:hover { border-color: var(--ink-2); }
.chip-clear { border: 0; background: none; padding: 2px 4px; font-size: 0.7813rem; font-weight: 650; color: var(--action-hi); text-decoration: underline; text-underline-offset: 3px; }
.seg { display: inline-flex; flex: none; height: 34px; gap: 2px; padding: 2px; background: var(--sheet); border: 1px solid var(--line-2); border-radius: var(--r-1); }
.seg button { display: inline-flex; align-items: center; gap: 5px; border: 0; background: transparent; padding: 0 10px; border-radius: 4px; font-size: 0.7813rem; font-weight: 650; color: var(--ink-2); }
.seg button:hover { background: var(--sunk); }
.seg button[aria-pressed="true"] { background: var(--shell); color: var(--on-shell); }

/* Ledger: the list view hangs from an ink rule like a datasheet ordering table */
.ledger { background: var(--sheet); border: 1px solid var(--line); border-top: 2px solid var(--ink); border-radius: 0 0 var(--r-2) var(--r-2); overflow: hidden; }
.ledger:has(> .rows[hidden]) { display: none; }
.rows { list-style: none; }
.rows-head { display: none; }
.row { display: grid; grid-template-columns: 76px minmax(0, 1fr); grid-template-areas: "plate info" "verd verd" "act act" "drawer drawer"; gap: 0 14px; padding: 16px 14px; border-top: 1px solid var(--line); align-items: start; transition: background-color 0.15s; }
.row:first-child { border-top: 0; }
.row:hover, .row[data-open] { background: #FAFBFB; }
.r-plate { grid-area: plate; }
.r-info { grid-area: info; }
.r-title { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; font-size: 0.9688rem; line-height: 1.4; font-weight: 700; letter-spacing: -0.01em; overflow-wrap: anywhere; }
.r-title a { text-decoration: none; }
.r-title a:hover { text-decoration: underline; }
.r-meta { margin-top: 2px; }
.r-spec { display: flex; flex-wrap: wrap; gap: 4px 5px; list-style: none; margin-top: 7px; max-height: 24px; overflow: hidden; }
.r-verd { grid-area: verd; display: flex; align-items: flex-start; justify-content: space-between; gap: 6px 12px; margin-top: 12px; }
.r-more { display: inline-flex; align-items: center; gap: 3px; flex: none; min-height: 30px; margin-left: -6px; border: 0; border-radius: var(--r-1); background: transparent; padding: 0 6px; font-size: 0.7813rem; font-weight: 700; color: var(--action-hi); white-space: nowrap; }
.r-more:hover { background: var(--action-tint); }
.r-more .i { transition: transform 0.2s var(--ease); }
.row[data-open] .r-more .i { transform: rotate(180deg); }
.r-act { grid-area: act; margin-top: 12px; }
.buys { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.buy { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 38px; max-width: 100%; padding: 6px 10px; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); font-size: 0.7813rem; font-weight: 700; line-height: 1.25; text-align: center; text-decoration: none; overflow-wrap: anywhere; transition: background-color 0.15s, border-color 0.15s; }
.buy:hover { border-color: var(--ink-2); background: var(--sunk); }
.buy.is-pick { background: var(--action); border-color: var(--action); color: #fff; }
.buy.is-pick:hover { background: var(--action-hi); border-color: var(--action-hi); }
.buy .i { opacity: 0.7; }
.row-disc { margin-top: 6px; font-size: 0.75rem; line-height: 1.4; color: var(--muted); }

.drawer { grid-area: drawer; display: grid; grid-template-rows: 0fr; visibility: hidden; transition: grid-template-rows 0.22s var(--ease), visibility 0.22s; }
.row[data-open] .drawer { grid-template-rows: 1fr; visibility: visible; margin-top: 14px; }
.drawer-in { min-height: 0; overflow: hidden; }
.drawer-box { display: grid; gap: 12px; padding: 14px 16px; background: var(--sunk); border: 1px solid var(--line); border-radius: var(--r-2); }
.drawer dl { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px 24px; }
.drawer dt { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 0.75rem; font-weight: 700; color: var(--ink-2); }
.drawer .cons dt { color: var(--warn-ink); }
.drawer dd { font-size: 0.8438rem; line-height: 1.55; color: var(--ink-2); }
.drawer .cons dd { position: relative; padding-left: 14px; }
.drawer .cons dd::before { content: ""; position: absolute; left: 2px; top: 0.62em; width: 5px; height: 5px; border-radius: 50%; background: #C98A12; }
.drawer .cons dd + dd { margin-top: 4px; }
.drawer-link { justify-self: start; display: inline-flex; align-items: center; gap: 5px; font-size: 0.8125rem; font-weight: 700; color: var(--action-hi); text-decoration: none; }
.drawer-link:hover { text-decoration: underline; }

@container idx (min-width: 600px) {
  .row { grid-template-columns: 88px minmax(0, 1fr) 176px; grid-template-areas: "plate info act" "plate verd act" "drawer drawer drawer"; gap: 0 16px; padding: 16px; }
  .r-verd { margin-top: 10px; }
  .r-act { margin-top: 0; align-self: center; }
  .buys { grid-template-columns: minmax(0, 1fr); }
  .drawer dl { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@container idx (min-width: 920px) {
  .rows-head { display: grid; grid-template-columns: 96px minmax(0, 1fr) 208px 176px; gap: 0 16px; padding: 8px 16px; background: var(--sunk); border-bottom: 1px solid var(--line-2); font-size: 0.75rem; font-weight: 700; color: var(--ink-2); }
  .row { grid-template-columns: 96px minmax(0, 1fr) 208px 176px; grid-template-areas: "plate info verd act" "drawer drawer drawer drawer"; align-items: center; }
  .r-title { -webkit-line-clamp: 2; }
  .r-verd { flex-direction: column; justify-content: flex-start; gap: 4px; margin-top: 0; }
}

/* Card view: same entries as showcase cards with the plate as a media well */
.hub[data-view="cards"] .ledger { background: none; border: 0; border-radius: 0; overflow: visible; }
.hub[data-view="cards"] .rows-head { display: none; }
.hub[data-view="cards"] .rows { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(264px, 100%), 1fr)); gap: 14px; }
.hub[data-view="cards"] .row { display: flex; flex-direction: column; align-items: stretch; gap: 0; padding: 0 0 8px; border: 1px solid var(--line); border-radius: var(--r-3); background: var(--sheet); overflow: hidden; }
.hub[data-view="cards"] .row:hover { border-color: var(--line-2); }
.hub[data-view="cards"] .r-plate { order: 0; aspect-ratio: 4 / 3; border-radius: 0; }
.hub[data-view="cards"] .r-plate img { inset: 9% 12%; width: 76%; height: 82%; }
.hub[data-view="cards"] .r-info { order: 1; flex: 1 1 auto; padding: 14px 16px 0; }
.hub[data-view="cards"] .r-title { -webkit-line-clamp: 2; min-height: 2.8em; text-wrap: balance; }
.hub[data-view="cards"] .r-spec { max-height: 52px; }
.hub[data-view="cards"] .r-verd { display: contents; }
.hub[data-view="cards"] .r-route { order: 2; margin: 14px 16px 0; padding-top: 12px; border-top: 1px solid var(--line); }
.hub[data-view="cards"] .r-act { order: 3; align-self: stretch; margin: 12px 16px 0; }
.hub[data-view="cards"] .buys { grid-template-columns: minmax(0, 1fr); }
.hub[data-view="cards"] .r-more { order: 4; align-self: flex-start; margin: 6px 0 0 10px; }
.hub[data-view="cards"] .drawer { order: 5; margin-inline: 12px; }
.hub[data-view="cards"] .row[data-open] .drawer { margin-top: 6px; margin-bottom: 6px; }
.hub[data-view="cards"] .drawer dl { grid-template-columns: minmax(0, 1fr); }

.pager { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px; margin-top: 16px; }
.pager-status { width: 100%; text-align: center; font-size: 0.8125rem; color: var(--muted); }
.pager button { min-height: 42px; max-width: 100%; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); padding: 6px 16px; font-size: 0.875rem; font-weight: 700; }
.pager button:hover { border-color: var(--ink-2); background: var(--sunk); }
.pager button.primary { background: var(--action); border-color: var(--action); color: #fff; }
.pager button.primary:hover { background: var(--action-hi); border-color: var(--action-hi); }
.empty { display: grid; justify-items: center; gap: 6px; background: var(--sheet); border: 1px dashed var(--line-2); border-radius: var(--r-2); padding: 36px 20px; text-align: center; font-size: 0.875rem; color: var(--ink-2); }
.empty strong { font-size: 1rem; color: var(--ink); }
.empty button { margin-top: 10px; min-height: 38px; border: 1px solid var(--action); background: var(--action); color: #fff; border-radius: var(--r-1); padding: 0 14px; font-size: 0.8438rem; font-weight: 700; }

html.js .hub:not([data-ready]) .rows > li:nth-child(n+__PAGE_NEXT__) { display: none; }

/* Page heads, crumbs, sections */
.crumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 6px; padding: 16px 0 0; font-size: 0.8125rem; color: var(--muted); list-style: none; }
.crumbs li { overflow-wrap: anywhere; }
.crumbs a { text-decoration: none; color: var(--ink-2); }
.crumbs a:hover { text-decoration: underline; }
.page-head { padding: 20px 0 4px; max-width: 900px; }
.page-head h1, .d-intro h1 { font-size: 1.75rem; line-height: 1.25; letter-spacing: -0.025em; font-weight: 770; text-wrap: balance; overflow-wrap: anywhere; }
.dek { margin-top: 10px; max-width: 70ch; font-size: 1rem; line-height: 1.6; color: var(--ink-2); }
.page-meta { margin-top: 10px; font-size: 0.8125rem; font-weight: 550; color: var(--muted); }
.page-act { margin-top: 16px; }
.section { margin-top: 32px; }
.section > h2, .related > h2, .tool-picks > h3, .guide-group > h2 { margin-bottom: 12px; font-size: 1.1875rem; line-height: 1.35; letter-spacing: -0.018em; font-weight: 750; text-wrap: balance; }
.text-link { display: inline-flex; align-items: flex-start; gap: 6px; max-width: 100%; font-size: 0.875rem; font-weight: 700; line-height: 1.5; color: var(--action-hi); text-decoration: none; }
.text-link:hover { text-decoration: underline; }
.text-link .i { margin-top: 3px; }

/* Detail */
.detail { display: grid; grid-template-columns: minmax(0, 1fr) 372px; grid-template-areas: "hero aside" "body aside"; gap: 0 32px; padding: 16px 0 8px; align-items: start; }
.d-hero { grid-area: hero; display: grid; grid-template-columns: minmax(220px, 40%) minmax(0, 1fr); overflow: hidden; }
.d-plate { aspect-ratio: auto; height: 100%; min-height: 300px; border-radius: 0; }
.d-plate img { inset: 12% 12% 14%; width: 76%; height: 74%; }
.d-intro { padding: 24px 26px 26px; }
.d-intro .desig { margin-top: 8px; font-size: 0.8438rem; }
.d-intro .chips { margin-top: 16px; }
.d-intro .text-link { margin-top: 16px; }
.d-body { grid-area: body; }
.d-aside { grid-area: aside; position: sticky; top: calc(var(--head-h) + 16px); max-height: calc(100dvh - var(--head-h) - 32px); overflow-y: auto; container: aside / inline-size; scrollbar-width: thin; scrollbar-color: var(--line-2) transparent; }
.decide { padding: 18px; }
.decide-title { margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--line); font-size: 0.9375rem; font-weight: 760; }
.pick { display: block; }
.pick .why { margin-top: 2px; padding-left: 22px; }
.decide-verdict { margin-top: 10px; font-size: 0.875rem; line-height: 1.6; color: var(--ink-2); }
.battle { display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; margin-top: 14px; }
.side { display: flex; flex-direction: column; padding: 12px; border: 1px solid var(--line); border-radius: var(--r-2); background: var(--sheet); }
.side.is-win { background: var(--action-tint); border-color: var(--action-line); }
.side-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 4px 8px; }
.win-tag { font-size: 0.6875rem; font-weight: 750; line-height: 1.7; color: var(--action-hi); background: var(--sheet); border: 1px solid var(--action-line); border-radius: 4px; padding: 0 6px; }
.perk { font-size: 0.7813rem; font-weight: 600; line-height: 1.45; color: var(--ink-2); }
.side-meta { font-size: 0.75rem; line-height: 1.45; color: var(--muted); }
.side.is-win .side-meta { color: var(--ink-2); }
.live-slot { font-size: 0.8438rem; font-weight: 700; color: var(--action-hi); }
.side-txt { display: flex; flex-direction: column; gap: 3px; flex: 1 1 auto; padding-bottom: 10px; }
.decide-stamp { margin-top: 6px; font-size: 0.75rem; line-height: 1.5; color: var(--muted); }
.decide-switch { display: inline-flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 0.8125rem; font-weight: 650; color: var(--ink-2); text-decoration: none; }
.decide-switch:hover { color: var(--ink); text-decoration: underline; }
@container aside (min-width: 560px) {
  .battle { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.customs .dest-bar { margin-top: 0; }
.customs .notice { margin-top: 10px; }

/* Tables hang from an ink rule; cards are closed boxes */
.table-sheet { background: var(--sheet); border: 1px solid var(--line); border-top: 2px solid var(--ink); border-radius: 0 0 var(--r-2) var(--r-2); overflow: hidden; }
.table-scroll { overflow-x: auto; scrollbar-width: thin; scrollbar-color: var(--line-2) transparent; }
.spec-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; font-variant-numeric: tabular-nums; }
.spec-table th, .spec-table td { text-align: left; padding: 10px 16px; border-bottom: 1px solid var(--line); vertical-align: top; overflow-wrap: anywhere; }
.spec-table tr:last-child > * { border-bottom: 0; }
.spec-table tbody th { width: 34%; font-size: 0.8125rem; font-weight: 600; color: var(--muted); background: var(--sunk); }
.guide-matrix { min-width: 680px; }
.guide-matrix thead th { font-size: 0.7813rem; font-weight: 700; color: var(--ink-2); background: var(--sunk); border-bottom: 1px solid var(--line-2); }
.guide-matrix td { color: var(--ink-2); }
.guide-matrix td:first-child { font-weight: 650; color: var(--ink); }
.msrp-ref > * { font-size: 0.8125rem; color: var(--muted); }
.msrp-ref small { display: block; margin-top: 2px; font-size: 0.75rem; line-height: 1.45; }
.pc { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.pc .panel { padding: 16px 18px; }
.pc h3 { margin-bottom: 10px; font-size: 0.9375rem; font-weight: 740; }
.pc ul, .guide-excl { list-style: none; display: grid; gap: 8px; }
.pc li, .guide-excl li { position: relative; padding-left: 24px; font-size: 0.875rem; line-height: 1.6; color: var(--ink-2); }
.pc li::before, .guide-excl li::before { content: ""; position: absolute; left: 0; top: 0.25em; width: 16px; height: 16px; background: var(--action); -webkit-mask: var(--ic-check) center / contain no-repeat; mask: var(--ic-check) center / contain no-repeat; }
.pc .cons { background: var(--warn-bg); border-color: var(--warn-line); }
.pc .cons h3 { color: var(--warn-ink); }
.pc .cons li, .guide-excl li { color: var(--warn-text); }
.pc .cons li::before, .guide-excl li::before { background: #A86400; -webkit-mask-image: var(--ic-caution); mask-image: var(--ic-caution); }
.notice.excl { display: block; padding: 16px 18px; }

/* Product cards: related, checker picks, guide references */
.related { margin-top: 44px; padding-top: 28px; border-top: 1px solid var(--line-2); }
.rel-grid, .tool-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.pcard { position: relative; display: flex; flex-direction: column; background: var(--sheet); border: 1px solid var(--line); border-radius: var(--r-3); overflow: hidden; transition: border-color 0.15s; }
.pcard:hover { border-color: var(--line-2); }
.pcard-plate { aspect-ratio: 4 / 3; border-radius: 0; }
.pcard-plate img { inset: 9% 12%; width: 76%; height: 82%; }
.pcard-body { display: flex; flex-direction: column; gap: 8px; flex: 1 1 auto; padding: 14px 16px 0; }
.pcard-title { font-size: 0.9688rem; line-height: 1.4; font-weight: 720; letter-spacing: -0.01em; text-wrap: balance; overflow-wrap: anywhere; }
.pcard-title a { text-decoration: none; }
.pcard-title a:hover { text-decoration: underline; }
.pcard-title + .desig { margin-top: -5px; }
.pcard-sum { font-size: 0.8438rem; line-height: 1.55; color: var(--ink-2); }
.note-c { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 7px; padding: 8px 10px; border: 1px solid var(--warn-line); border-radius: var(--r-1); background: var(--warn-bg); color: var(--warn-text); font-size: 0.7813rem; line-height: 1.5; }
.note-c .i { margin-top: 2px; color: var(--warn-ink); }
.note-c strong { color: var(--warn-ink); }
.pcard-foot { display: grid; gap: 10px; padding: 14px 16px 16px; }
.actions { display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; }
.rel .pcard-body { padding-bottom: 16px; }
.rel .pick { margin-top: auto; padding-top: 4px; }
.rel .pcard-title a::after { content: ""; position: absolute; inset: 0; }
.tool-grid[data-count="1"] { grid-template-columns: minmax(0, 760px); }
.tool-grid[data-count="2"] { grid-template-columns: repeat(2, minmax(0, 1fr)); max-width: 860px; }
.tool-grid[data-count="4"] { grid-template-columns: repeat(4, minmax(0, 1fr)); }

/* Dock checker */
.tool-form { margin-top: 18px; padding: 18px; }
.tool-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 20px; list-style: none; }
.field { display: grid; gap: 8px; align-content: start; }
.field label { display: flex; align-items: flex-start; gap: 9px; font-size: 0.875rem; font-weight: 700; line-height: 1.45; }
.step { flex: none; display: grid; place-items: center; width: 22px; height: 22px; border-radius: 5px; background: var(--shell); color: var(--on-shell); font-size: 0.75rem; font-weight: 750; font-variant-numeric: tabular-nums; }
.field .sel select { height: 48px; padding-left: 14px; font-size: 0.9063rem; box-shadow: 0 1px 0 rgba(15, 27, 31, 0.05), inset 0 -2px 0 var(--sunk); }
.field .sel select:focus-visible { border-color: var(--action); }
.tool-out { margin-top: 18px; }
.verdict-box { padding: 20px 22px; border: 1.5px solid var(--line-2); border-radius: var(--r-3); background: var(--sheet); animation: verdict-in 0.3s var(--ease); }
@keyframes verdict-in { from { opacity: 0.35; transform: translateY(5px); } to { opacity: 1; transform: none; } }
.verdict-box.is-ok { border-color: var(--action); background: #F1F8F6; }
.verdict-box.is-warn { border-color: #C98A12; background: var(--warn-bg); }
.verdict-box.is-hold { border-style: dashed; border-color: var(--muted); background: var(--sunk); }
.v-badge { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; padding: 4px 10px 4px 8px; border-radius: 5px; background: var(--ink-2); color: #fff; font-size: 0.75rem; font-weight: 750; line-height: 1.4; overflow-wrap: anywhere; }
.v-badge::before { content: ""; flex: none; width: 14px; height: 14px; background: currentColor; -webkit-mask: var(--ic-hold) center / contain no-repeat; mask: var(--ic-hold) center / contain no-repeat; }
.is-ok .v-badge { background: var(--action); }
.is-ok .v-badge::before { -webkit-mask-image: var(--ic-check); mask-image: var(--ic-check); }
.is-warn .v-badge { background: #8A5200; }
.is-warn .v-badge::before { -webkit-mask-image: var(--ic-caution); mask-image: var(--ic-caution); }
.verdict-box h2 { margin-top: 12px; max-width: 46ch; font-size: 1.25rem; line-height: 1.4; letter-spacing: -0.018em; font-weight: 760; text-wrap: balance; }
.verdict-box > p { margin-top: 8px; max-width: 72ch; color: var(--ink-2); }
.is-warn > p { color: var(--warn-text); }
.tool-check { display: grid; gap: 6px; margin-top: 12px; padding-left: 20px; font-size: 0.875rem; color: var(--ink-2); }
.tool-alert { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 2px 9px; margin-top: 14px; padding: 11px 13px; border: 1px solid var(--warn-line); border-radius: var(--r-2); background: var(--warn-bg); color: var(--warn-text); font-size: 0.8438rem; line-height: 1.55; }
.tool-alert::before { content: ""; grid-row: 1 / 3; width: 18px; height: 18px; margin-top: 2px; background: var(--warn-ink); -webkit-mask: var(--ic-caution) center / contain no-repeat; mask: var(--ic-caution) center / contain no-repeat; }
.tool-alert strong { grid-column: 2; color: var(--warn-ink); }
.tool-alert span { grid-column: 2; }
.is-warn .tool-alert { background: #FFFBF2; }
.v-cond { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 16px; padding-top: 12px; border-top: 1px solid rgba(15, 27, 31, 0.12); }
.v-cond dt { flex: 1 0 100%; font-size: 0.75rem; font-weight: 700; color: var(--ink-2); }
.v-cond dd { max-width: 100%; padding: 2px 8px; border: 1px solid rgba(15, 27, 31, 0.14); border-radius: 5px; background: rgba(255, 255, 255, 0.7); font-size: 0.75rem; font-weight: 600; line-height: 1.5; color: var(--ink-2); }
.tool-picks { margin-top: 26px; }
.tool-foot-note { margin-top: 22px; max-width: 80ch; font-size: 0.8125rem; color: var(--muted); }
.tool-more { margin-top: 12px; }

/* Guides */
.guide-group { margin-top: 30px; }
.guide-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.guide-card { position: relative; display: flex; flex-direction: column; gap: 8px; padding: 18px; border-radius: var(--r-3); transition: border-color 0.15s; }
.guide-card:hover { border-color: var(--line-2); }
.guide-card h3 { font-size: 1.0313rem; line-height: 1.4; font-weight: 740; letter-spacing: -0.012em; text-wrap: balance; overflow-wrap: anywhere; }
.guide-card h3 a { text-decoration: none; }
.guide-card h3 a::after { content: ""; position: absolute; inset: 0; border-radius: inherit; }
.guide-card:hover h3 a { text-decoration: underline; }
.guide-card p { font-size: 0.8438rem; line-height: 1.6; color: var(--ink-2); }
.gc-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin-top: auto; padding-top: 8px; }
.gc-plates { display: flex; gap: 5px; }
.gc-plates .plate { width: 44px; border-radius: 6px; }
.gc-plates .plate img { inset: 9%; width: 82%; height: 82%; }
.gc-meta { font-size: 0.7813rem; font-weight: 600; color: var(--muted); }
.guide-p { max-width: 72ch; font-size: 0.9688rem; line-height: 1.75; color: var(--ink-2); }
.guide-p.lead { margin-top: 18px; }
.guide-article .feat-strip { margin-top: 18px; }

/* Gateway, policy, footer */
.gate-hero { padding: 36px 0 22px; max-width: 760px; }
.gate-hero h1 { font-size: 2rem; line-height: 1.2; letter-spacing: -0.03em; font-weight: 780; }
.regions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; padding-bottom: 16px; }
.region { position: relative; display: flex; flex-direction: column; border-radius: var(--r-3); overflow: hidden; transition: border-color 0.15s; }
.region:hover { border-color: var(--line-2); }
.region.is-suggested { border-color: var(--action); box-shadow: 0 0 0 1px var(--action); }
.region-plates { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1px; background: var(--sheet); }
.region-plates .plate { border-radius: 0; }
.region-body { display: flex; flex-direction: column; gap: 12px; padding: 18px 20px 20px; }
.region-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 6px 12px; }
.region h2 { font-size: 1.3125rem; line-height: 1.3; letter-spacing: -0.02em; font-weight: 770; }
.region h2 a { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 8px; text-decoration: none; }
.region h2 a::after { content: ""; position: absolute; inset: 0; border-radius: inherit; }
.code-tag { font-size: 0.6875rem; font-weight: 750; letter-spacing: 0.04em; color: var(--ink-2); border: 1px solid var(--line-2); border-radius: 4px; padding: 1px 6px; }
.suggest { font-size: 0.6875rem; font-weight: 700; color: #fff; background: var(--action); border-radius: 4px; padding: 2px 8px; }
.region-sub { font-size: 0.875rem; color: var(--ink-2); }
.region-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; background: var(--line); border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.region-stats div { background: var(--sheet); padding: 10px 10px 10px 0; }
.region-stats div + div { padding-left: 12px; }
.region-stats dt { font-size: 0.75rem; font-weight: 600; color: var(--muted); }
.region-stats dd { font-size: 0.9375rem; font-weight: 740; overflow-wrap: anywhere; }
.region-go { display: inline-flex; align-items: center; gap: 6px; font-size: 0.9063rem; font-weight: 700; color: var(--action-hi); }
.prose { max-width: 78ch; margin-top: 26px; padding: 28px 30px 32px; }
.prose h1 { font-size: 1.75rem; line-height: 1.25; letter-spacing: -0.025em; font-weight: 770; text-wrap: balance; }
.prose h2 { margin-top: 28px; font-size: 1.0938rem; font-weight: 740; }
.prose p { margin-top: 10px; line-height: 1.7; color: var(--ink-2); }
.site-foot { margin-top: 56px; background: var(--shell); color: var(--on-shell-2); }
.site-foot .wrap { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 16px 40px; padding-top: 24px; padding-bottom: 28px; font-size: 0.7813rem; line-height: 1.6; }
.site-foot p { max-width: 76ch; }
.site-foot :focus-visible { outline-color: var(--mint); }
.foot-links { display: flex; flex-wrap: wrap; align-content: flex-start; gap: 6px 16px; }
.foot-links a { color: var(--on-shell); font-weight: 600; text-decoration: none; }
.foot-links a:hover { text-decoration: underline; }


/* Situation board: sale-window signal, promo-code tiers, calculator entry (one ruled sheet, three cells) */
.board { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.7fr) auto; gap: 1px; margin-bottom: 12px; background: var(--line); border: 1px solid var(--line); border-top: 2px solid var(--ink); border-radius: 0 0 var(--r-2) var(--r-2); overflow: hidden; }
.board > * { background: var(--sheet); padding: 12px 14px; }
.board-sig { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 0 12px; align-content: center; transition: background-color 0.2s; }
.board-sig.is-go { background: #F1F8F6; }
.board-sig.is-hold { background: var(--warn-bg); }
.board-sig.is-std { background: var(--info-tint); }
.lamps { display: inline-flex; gap: 5px; align-self: start; margin-top: 4px; padding: 5px 7px; border-radius: 999px; background: var(--shell-deep); }
.lamps i { width: 9px; height: 9px; border-radius: 50%; background: #2C4A46; }
.is-go .lamps i:nth-child(1) { background: #4FD6A8; box-shadow: 0 0 0 2px rgba(79, 214, 168, 0.22); }
.is-hold .lamps i:nth-child(2) { background: #F2B544; box-shadow: 0 0 0 2px rgba(242, 181, 68, 0.24); }
.is-std .lamps i:nth-child(3) { background: #8CB8F7; box-shadow: 0 0 0 2px rgba(140, 184, 247, 0.24); }
.board-state { font-size: 0.9688rem; line-height: 1.4; font-weight: 760; letter-spacing: -0.012em; text-wrap: balance; overflow-wrap: anywhere; }
.is-go .board-state { color: var(--action-hi); }
.is-hold .board-state { color: var(--warn-ink); }
.is-std .board-state { color: var(--info); }
.board-sub { margin-top: 3px; font-size: 0.75rem; line-height: 1.5; color: var(--ink-2); }
.board-date { display: block; margin-top: 2px; color: var(--muted); }
.board-codes { display: grid; gap: 7px; align-content: center; }
.board-h { font-size: 0.75rem; font-weight: 700; line-height: 1.45; color: var(--ink-2); }
.board-h span { font-weight: 550; color: var(--muted); }
.tiers { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; }
.tier { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; min-height: 30px; padding: 3px 9px; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); font-size: 0.7813rem; font-weight: 650; line-height: 1.3; color: var(--ink-2); font-variant-numeric: tabular-nums; white-space: nowrap; }
.tier b { color: var(--ink); font-weight: 760; }
.tier code { font: inherit; font-weight: 760; letter-spacing: 0.02em; color: var(--action-hi); }
button.tier { border-color: var(--action-line); background: var(--action-tint); transition: background-color 0.15s, border-color 0.15s; }
button.tier:hover { border-color: var(--action); background: #D3EAE5; }
button.tier:active { transform: translateY(1px); }
.copy-swap { display: inline-grid; justify-items: center; }
.copy-swap > * { grid-area: 1 / 1; }
.copy-done { visibility: hidden; font-weight: 760; color: var(--action-hi); }
[data-copied] .copy-done { visibility: visible; }
[data-copied] .copy-idle { visibility: hidden; }
.board-note { display: flex; align-items: flex-start; gap: 6px; font-size: 0.75rem; line-height: 1.5; color: var(--muted); }
.board-note .i { margin-top: 2px; color: var(--warn-ink); }
.board-act { display: grid; align-content: center; gap: 8px; }
.board-act .text-link { font-size: 0.8125rem; }

/* Trap-cut filter chips */
.traps { display: flex; align-items: center; gap: 6px 10px; margin: 0 0 8px; }
.traps-h { flex: none; font-size: 0.75rem; font-weight: 700; color: var(--ink-2); }
.traps-row { display: flex; flex-wrap: wrap; gap: 6px; }
.trap { display: inline-flex; align-items: center; gap: 6px; flex: none; max-width: 100%; min-height: 32px; padding: 3px 11px; border: 1px solid var(--line-2); border-radius: 999px; background: var(--sheet); font-size: 0.7813rem; font-weight: 650; color: var(--ink-2); white-space: nowrap; transition: background-color 0.15s, border-color 0.15s, color 0.15s, opacity 0.15s; }
.trap:hover { border-color: var(--ink-2); color: var(--ink); }
.trap[aria-pressed="true"] { background: var(--shell); border-color: var(--shell); color: var(--on-shell); }
.trap .num { display: inline-block; min-width: 2ch; text-align: center; font-size: 0.75rem; color: var(--muted); }
.trap[aria-pressed="true"] .num { color: var(--on-shell-2); }
.trap > span > .num { min-width: 2ch; font-size: inherit; color: inherit; }
.trap.is-zero { opacity: 0.45; }

/* Reference anchor strip + expiring live-offer line (always directly above store buttons) */
.anchor { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; font-size: 0.75rem; line-height: 1.5; color: var(--muted); font-variant-numeric: tabular-nums; }
.anchor b { color: var(--ink-2); font-weight: 700; }
.anchor-rule { max-width: 100%; padding: 0 6px; border: 1px solid var(--line-2); border-radius: 4px; background: var(--sunk); font-weight: 650; line-height: 1.65; color: var(--ink-2); }
.anchor-rule.is-in { border-color: var(--action-line); background: var(--action-tint); color: var(--action-hi); }
.anchor-rule.is-over { border-color: var(--warn-line); background: var(--warn-bg); color: var(--warn-ink); }
.anchor a { font-weight: 700; color: var(--action-hi); text-decoration: underline; text-decoration-color: var(--action-line); text-underline-offset: 3px; }
.anchor a:hover { text-decoration-color: currentColor; }
.live-line { display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 8px; padding: 7px 10px; border: 1px solid var(--action-line); border-radius: var(--r-1); background: #F1F8F6; font-size: 0.75rem; line-height: 1.45; color: var(--ink-2); overflow-wrap: anywhere; }
.live-line b { font-size: 0.9375rem; font-weight: 760; color: var(--ink); }
.live-line.is-api { border-color: var(--action); }
.r-act > .anchor, .r-act > .live-line { margin-bottom: 8px; }
.decide .anchor { margin-top: 12px; }
.decide .live-line { margin-top: 12px; }
.decide .anchor + .battle { margin-top: 10px; }
.rival { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); display: grid; gap: 6px; }
.btn-row { display: flex; flex-wrap: wrap; gap: 8px; }
.link-list { display: grid; gap: 8px; list-style: none; }
.table-note { margin-top: 8px; font-size: 0.75rem; line-height: 1.5; color: var(--muted); }
.kr-check tbody th { width: 24%; color: var(--ink-2); }

/* Promo & customs calculator */
.calc { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 420px); gap: 18px 24px; align-items: start; margin-top: 18px; }
.calc .tool-form { margin-top: 0; }
.calc-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 18px; list-style: none; }
.calc-fields .is-wide { grid-column: 1 / -1; }
.calc-fields label { font-weight: 700; }
.inp { position: relative; display: block; }
.inp input { display: block; width: 100%; height: 48px; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); padding: 0 14px 0 32px; font-size: 1rem; font-weight: 650; font-variant-numeric: tabular-nums; box-shadow: 0 1px 0 rgba(15, 27, 31, 0.05), inset 0 -2px 0 var(--sunk); transition: border-color 0.15s; }
.inp input:hover { border-color: var(--ink-2); }
.inp input:focus-visible { border-color: var(--action); }
.inp .unit { position: absolute; left: 13px; top: 50%; transform: translateY(-50%); font-size: 0.875rem; font-weight: 700; color: var(--muted); pointer-events: none; }
.inp.is-suffix input { padding: 0 40px 0 14px; }
.inp.is-suffix .unit { left: auto; right: 13px; }
.field-hint { font-size: 0.75rem; line-height: 1.5; color: var(--muted); }
.calc-source { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); font-size: 0.75rem; line-height: 1.5; color: var(--ink-2); }
.calc-source:has(span:empty) { display: none; }
.calc-source + .board-note { margin-top: 6px; }
.calc-out { position: sticky; top: calc(var(--head-h) + 16px); display: grid; gap: 12px; }
.calc-sum, .calc-go { padding: 18px; }
.calc-sum h2, .calc-go h2 { margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--line); font-size: 0.9375rem; font-weight: 760; }
.calc-net { display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 12px; }
.calc-net .usd { font-size: 2rem; line-height: 1.15; font-weight: 780; letter-spacing: -0.03em; }
.calc-net .krw { font-size: 1.0625rem; font-weight: 700; color: var(--ink-2); }
.calc-lines { display: grid; margin-top: 12px; font-size: 0.8438rem; }
.calc-lines div { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-top: 1px solid var(--line); }
.calc-lines dt { color: var(--ink-2); overflow-wrap: anywhere; }
.calc-lines dd { flex: none; font-weight: 700; white-space: nowrap; }
.calc-lines .is-off dd { color: var(--action-hi); }
.calc-code { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--line); font-size: 0.8125rem; line-height: 1.5; color: var(--ink-2); }
.calc-sum > .field-hint { display: block; margin-top: 8px; }
.calc-msrp { margin-top: 10px; padding: 8px 10px; border-radius: var(--r-1); background: var(--sunk); font-size: 0.8125rem; line-height: 1.5; font-weight: 650; color: var(--ink); }
.calc-msrp span { display: block; font-size: 0.75rem; font-weight: 500; color: var(--muted); }
.customs-light { padding: 16px 18px; }
.customs-light h2 { font-size: 1.0625rem; }
.customs-light > p { font-size: 0.8438rem; line-height: 1.6; }
.calc-go-name { margin-bottom: 10px; font-size: 0.875rem; font-weight: 700; overflow-wrap: anywhere; }
.calc-cta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.calc-go-more { margin-top: 10px; }

/* VS battles */
.vs-stage { position: relative; container-type: inline-size; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; margin-top: 16px; background: var(--line); overflow: hidden; }
.vs-side { display: flex; flex-direction: column; background: var(--sheet); }
.vs-side .plate { aspect-ratio: 5 / 2; border-radius: 0; }
.vs-side .plate img { inset: 7% 16%; width: 68%; height: 86%; }
.vs-name { padding: 12px 16px 14px; }
.vs-name strong { display: block; font-size: 1.0625rem; line-height: 1.35; font-weight: 760; letter-spacing: -0.015em; overflow-wrap: anywhere; }
.vs-mark { position: absolute; z-index: 1; left: 50%; top: 10cqw; transform: translate(-50%, -50%); display: grid; place-items: center; width: 46px; height: 46px; border: 3px solid var(--sheet); border-radius: 50%; background: var(--shell); color: var(--mint); font-size: 0.8125rem; font-weight: 800; letter-spacing: 0.04em; }
.vs-verdicts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }
.vs-pick { display: flex; flex-direction: column; gap: 10px; padding: 18px; border-top: 2px solid var(--ink); border-radius: 0 0 var(--r-2) var(--r-2); }
.vs-pick h2 { font-size: 1.1875rem; line-height: 1.35; letter-spacing: -0.018em; font-weight: 770; text-wrap: balance; overflow-wrap: anywhere; }
.vs-pick h2 em { font-style: normal; color: var(--action-hi); }
.vs-cond { padding: 10px 12px; border: 1px solid var(--action-line); border-radius: var(--r-1); background: var(--action-tint); font-size: 0.9375rem; font-weight: 680; line-height: 1.55; color: var(--ink); }
.vs-edge { font-size: 0.875rem; line-height: 1.65; color: var(--ink-2); }
.vs-edge strong { display: block; margin-bottom: 2px; font-size: 0.75rem; font-weight: 700; color: var(--muted); }
.vs-buy { display: grid; gap: 8px; margin-top: auto; padding-top: 12px; border-top: 1px solid var(--line); }
.vs-buy .actions { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.vs-page > .btn-disc { margin-top: 12px; }
.vs-table { min-width: 560px; }
.vs-table thead th { font-size: 0.8125rem; font-weight: 740; color: var(--ink); background: var(--sunk); border-bottom: 1px solid var(--line-2); }
.vs-table tbody th { width: 24%; }
.vs-table td { width: 38%; color: var(--ink-2); }
.vs-page .pc .cons h3 { overflow-wrap: anywhere; }
.vs-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.vs-card { position: relative; display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 4px 14px; align-items: start; padding: 16px; border-radius: var(--r-3); transition: border-color 0.15s; }
.vs-card:hover { border-color: var(--line-2); }
.vs-card .gc-plates .plate { width: 56px; }
.vs-card-txt { display: grid; gap: 6px; }
.vs-card h3 { font-size: 1.0313rem; line-height: 1.4; font-weight: 740; letter-spacing: -0.012em; text-wrap: balance; overflow-wrap: anywhere; }
.vs-card h3 a { text-decoration: none; }
.vs-card h3 a::after { content: ""; position: absolute; inset: 0; border-radius: inherit; }
.vs-card:hover h3 a { text-decoration: underline; }
.vs-card p { font-size: 0.8438rem; line-height: 1.6; color: var(--ink-2); }
.wrap > .feat-strip { margin-top: 32px; }

@media (max-width: 1099.98px) {
  .tool-grid[data-count="4"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 1023.98px) {
  :root { --head-h: 0px; }
  .site-head { position: static; }
  .site-head .wrap { flex-wrap: wrap; min-height: 0; padding-top: 10px; padding-bottom: 10px; }
  .head-nav { flex: 1 0 100%; margin-left: -4px; }
  .board { grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr); }
  .board-act { grid-column: 1 / -1; grid-auto-flow: column; justify-content: start; align-items: center; gap: 8px 16px; }
  .traps { display: block; }
  .traps-h { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .traps-row { flex-wrap: nowrap; overflow-x: auto; margin: 0 calc(-1 * var(--gut)); padding: 0 var(--gut) 6px; scrollbar-width: none; }
  .traps-row::-webkit-scrollbar { display: none; }
  .detail { grid-template-columns: minmax(0, 1fr); grid-template-areas: "hero" "aside" "body"; }
  .d-aside { position: static; max-height: none; overflow: visible; margin-top: 16px; }
  .work { display: block; margin-top: 14px; }
  .side-col { display: contents; }
  .catnav .facet-h { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .catnav ul { display: flex; gap: 6px; overflow-x: auto; margin: 0 calc(-1 * var(--gut)); padding: 0 var(--gut) 6px; scrollbar-width: none; }
  .catnav ul::-webkit-scrollbar { display: none; }
  .catnav li { flex: none; }
  .catnav a { min-height: 34px; padding: 4px 12px; border: 1px solid var(--line-2); border-radius: 999px; background: var(--sheet); white-space: nowrap; }
  .catnav a[aria-current] { border-color: var(--shell); }
  .fbtn { display: inline-flex; }
  .facets { position: fixed; z-index: 40; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; max-height: 84dvh; background: var(--sheet); border-radius: 14px 14px 0 0; box-shadow: 0 -10px 32px -12px rgba(10, 36, 34, 0.4); transform: translateY(104%); visibility: hidden; transition: transform 0.25s var(--ease), visibility 0.25s; }
  .facets[data-open] { transform: none; visibility: visible; }
  .facets-body { overflow-y: auto; padding: 0 14px 14px; }
  .facets-body .facet:first-child { margin-top: 14px; }
  .sheet-head { display: flex; justify-content: space-between; align-items: center; padding: 10px 10px 10px 16px; border-bottom: 1px solid var(--line); }
  .sheet-head button { display: grid; place-items: center; width: 38px; height: 38px; border: 0; border-radius: var(--r-1); background: transparent; }
  .sheet-head button:hover { background: var(--sunk); }
  .sheet-foot { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px; padding: 10px 16px calc(10px + env(safe-area-inset-bottom)); border-top: 1px solid var(--line); }
  .sheet-foot button { min-height: 44px; border: 1px solid var(--line-2); border-radius: var(--r-1); background: var(--sheet); padding: 0 14px; font-size: 0.875rem; font-weight: 700; }
  .sheet-foot .primary { background: var(--action); border-color: var(--action); color: #fff; }
  .scrim { display: block; position: fixed; inset: 0; z-index: 39; background: rgba(10, 36, 34, 0.5); opacity: 0; visibility: hidden; transition: opacity 0.2s, visibility 0.2s; }
  .scrim[data-open] { opacity: 1; visibility: visible; }
}
@media (max-width: 899.98px) {
  .calc { grid-template-columns: minmax(0, 1fr); }
  .calc-out { position: static; }
  .tool-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .feat-strip { grid-template-columns: auto minmax(0, 1fr); }
  .feat-actions { grid-column: 1 / -1; }
}
@media (max-width: 860px) {
  .summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
  .dest-bar, .regions, .pc, .guide-grid, .tool-fields, .vs-verdicts, .vs-list, .board { grid-template-columns: minmax(0, 1fr); }
  .board-act { grid-column: auto; }
  .board .tiers { flex-wrap: nowrap; overflow-x: auto; margin: 0 -14px; padding: 0 14px 2px; scrollbar-width: none; -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent); mask-image: linear-gradient(to right, #000 calc(100% - 28px), transparent); }
  .board .tiers::-webkit-scrollbar { display: none; }
  .board .tiers > li { flex: none; }
  .vs-side .plate { aspect-ratio: 4 / 3; }
  .vs-side .plate img { inset: 9% 12%; width: 76%; height: 82%; }
  .vs-mark { top: 18.75cqw; }
  .site-foot .wrap { grid-template-columns: minmax(0, 1fr); }
  .prose { padding: 22px 18px 26px; }
}
@media (min-width: 680px) {
  .tool-grid[data-count="1"] .pcard { display: grid; grid-template-columns: minmax(220px, 38%) minmax(0, 1fr); grid-template-rows: 1fr auto; }
  .tool-grid[data-count="1"] .pcard-plate { grid-row: 1 / 3; aspect-ratio: auto; height: 100%; min-height: 260px; }
  .tool-grid[data-count="1"] .actions { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 699.98px) {
  .rel-grid { grid-template-columns: minmax(0, 1fr); }
  .rel { flex-direction: row; }
  .rel .pcard-plate { width: 108px; aspect-ratio: auto; align-self: stretch; }
  .rel .pcard-plate img { inset: 10%; width: 80%; height: 80%; }
}
@media (max-width: 640px) {
  .head-nav { flex-wrap: nowrap; overflow-x: auto; margin: 0 calc(-1 * var(--gut)); padding: 2px var(--gut); scrollbar-width: none; -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); }
  .head-nav::-webkit-scrollbar { display: none; }
  .head-nav a.tg { margin-right: 24px; }
  .hub { display: flex; flex-direction: column; }
  .hub > .summary { order: 4; margin-top: 28px; }
  .hub > .feat-strip { order: 5; margin-top: 12px; }
  .idx-head { padding: 14px 0 6px; }
  .hub > .dest-bar { margin-top: 6px; }
  .bar { position: static; padding: 8px 0; }
  .status { margin-bottom: 6px; }
  .search { flex: 1 1 100%; }
  .sort { flex: 1 1 0; }
  .page-head h1, .d-intro h1 { font-size: 1.4375rem; }
  .idx-head h1 { font-size: 1.3125rem; }
  .gate-hero h1 { font-size: 1.75rem; }
  .d-hero { grid-template-columns: minmax(0, 1fr); }
  .d-plate { aspect-ratio: 16 / 10; height: auto; min-height: 0; }
  .d-plate img { inset: 9% 14% 13%; width: 72%; height: 78%; }
  .d-intro { padding: 18px 16px 20px; }
  .verdict-box { padding: 16px; }
  .verdict-box h2 { font-size: 1.125rem; }
  .tool-form { padding: 14px; }
}
@media (max-width: 559.98px) {
  .tool-grid, .tool-grid[data-count] { grid-template-columns: minmax(0, 1fr); max-width: none; }
}
@media (max-width: 480px) {
  :root { --gut: 14px; }
  .calc-fields, .calc-cta, .vs-buy .actions { grid-template-columns: minmax(0, 1fr); }
  .vs-mark { width: 36px; height: 36px; border-width: 2px; font-size: 0.6875rem; }
  .vs-name { padding: 10px 12px 12px; }
  .vs-name strong { font-size: 0.9375rem; }
  .vs-pick { padding: 16px 14px; }
  .vs-card { grid-template-columns: minmax(0, 1fr); }
  .board-act { grid-auto-flow: row; }
  .sm { padding: 9px 11px 10px; }
  .sm-s { display: none; }
  .legal-strip .wrap { flex-direction: column; gap: 3px; }
  .legal-tag { align-self: flex-start; }
  .head-nav .lbl-tg { display: none; }
  .head-nav a.tg { padding: 7px 9px; }
  .head-nav a { padding: 7px 8px; }
}
@media (hover: none) {
  .search kbd { display: none; }
  .search input { padding-right: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }
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
        if (store === 'coupang' && u.hostname === 'link.coupang.com' && u.pathname === '/re/AFFSRP') {
          const map = AFF_CFG.coupang_sub_ids_by_source || {};
          const baseSub = map[trafficSource] || map.unknown || 'gch_ko_web';
          u.searchParams.set('subid', `${baseSub}_${destToken}`.slice(0, 30));
          a.href = u.toString();
        } else if (store === 'aliexpress' && u.hostname.endsWith('aliexpress.com') && !/^(s\.click|a)\./.test(u.hostname)) {
          // Official promotion links (s.click / a.aliexpress.com) already carry tracking; never rewrite them.
          const map = AFF_CFG.aliexpress_tracking_by_source || {};
          const key = trafficSource === 'web' ? `web_${pageLang}` : (trafficSource === 'telegram' ? `telegram_${pageLang}` : trafficSource);
          const track = map[key] || map[trafficSource] || map.unknown || 'default';
          u.searchParams.set('aff_fcid', track);
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
  function logStoreClick(e) {
    const aff = e.target.closest('a[data-aff]');
    if (!aff) return;
    const store = aff.dataset.store;
    let hostname, pathname;
    try { ({ hostname, pathname } = new URL(aff.href)); } catch (err) { return; }
    const search = pathname === '/re/AFFSRP' || pathname === '/s' || pathname.startsWith('/w/wholesale-');
    const product = /\/(dp|gp\/product|item)\//.test(pathname);
    const partner = hostname === 'link.coupang.com' || /^(s\.click|a)\.aliexpress\.com$/.test(hostname);
    const linkKind = search ? 'search' : product ? 'product' : partner ? 'partner_deeplink' : 'storefront';
    logFunnel('outbound_click', { store, product_id: aff.dataset.pid, link_kind: linkKind });
  }
  document.addEventListener('click', logStoreClick);
  document.addEventListener('auxclick', e => { if (e.button === 1) logStoreClick(e); });
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

  // 3b. One-click promo-code copy chips with in-place feedback (the label swaps without resizing the chip)
  document.addEventListener('click', e => {
    const chip = e.target.closest('[data-copy]');
    if (!chip) return;
    const text = chip.dataset.copy;
    const done = () => {
      chip.setAttribute('data-copied', '');
      clearTimeout(chip._copyTimer);
      chip._copyTimer = setTimeout(() => chip.removeAttribute('data-copied'), 1600);
      logFunnel('code_copy');
    };
    const legacy = () => {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
      document.body.appendChild(ta);
      ta.select();
      try { if (document.execCommand('copy')) done(); } catch (err) {}
      ta.remove();
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, legacy);
    else legacy();
  });

  // 3c. Static live-offer lines and community-spotted codes hide themselves the moment they expire
  function sweepExpired() {
    const now = Date.now();
    document.querySelectorAll('[data-expires-at]').forEach(el => {
      const at = Date.parse(el.dataset.expiresAt);
      if (Number.isNaN(at) || now >= at) el.hidden = true;
    });
  }
  sweepExpired();
  setInterval(sweepExpired, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) sweepExpired(); });

  // 3d. Situation board: recompute the sale traffic light and active promo ladder on the visitor's visit date
  const board = document.querySelector('[data-board]');
  if (board) {
    const B = JSON.parse(board.querySelector('[data-board-json]').textContent);
    const ref = new Date(Date.now() + B.tz * 3600000);
    const month = ref.getUTCMonth() + 1;
    const day = ref.getUTCDate();
    const iso = ref.toISOString().slice(0, 10);
    const win = ((month === 11 && ((day >= 11 && day <= 18) || day >= 20)) || (month === 12 && day <= 3)) ? 'mega'
      : day <= 7 ? 'choice' : day >= 26 ? 'hold' : 'standard';
    const copy = B.copy[win];
    board.querySelector('[data-board-sig]').className = 'board-sig is-' + copy[0];
    board.querySelector('[data-board-label]').textContent = copy[1];
    board.querySelector('[data-board-sub]').textContent = copy[2];
    board.querySelector('[data-board-date]').textContent = B.date_tpl.replace('{d}', iso);
    board.dataset.window = win;
    const promo = B.events.find(ev => ev.starts <= iso && iso <= ev.ends) || B.ref;
    if (board.dataset.promoId !== promo.id) {
      const amt = v => '$' + (Number.isInteger(v) ? v : v.toFixed(2));
      const list = board.querySelector('[data-board-tiers]');
      list.replaceChildren(...promo.tiers.map(t => {
        const li = document.createElement('li');
        const spend = B.spend_tpl.replace('{m}', amt(t.min_spend_usd));
        if (t.code) {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'tier';
          btn.dataset.copy = t.code;
          btn.setAttribute('aria-label', B.copy_aria.replace('{c}', t.code));
          btn.innerHTML = '<span></span><b></b><span class="copy-swap"><code class="copy-idle"></code><span class="copy-done"></span></span>';
          btn.children[0].textContent = spend;
          btn.children[1].textContent = '\u2212' + amt(t.off_usd);
          btn.querySelector('code').textContent = t.code;
          btn.querySelector('.copy-done').textContent = B.copy_done;
          li.appendChild(btn);
        } else {
          li.className = 'tier';
          li.innerHTML = '<span></span><b></b>';
          li.children[0].textContent = spend;
          li.children[1].textContent = '\u2212' + amt(t.off_usd);
        }
        return li;
      }));
      const label = board.querySelector('[data-board-tiers-label]');
      label.textContent = promo.label;
      if (promo.source) {
        const src = document.createElement('span');
        src.textContent = ' · ' + promo.source;
        label.appendChild(src);
      }
      board.dataset.promoId = promo.id;
    }
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
    return { el, c: d.c, b: d.b, r: d.r, prio: +d.prio, q: d.q, t: (d.traps || '').split(' ').filter(Boolean) };
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
  const trapBtns = $$('[data-trap]');
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
    trap: trapBtns.some(b => b.dataset.trap === params.get('trap')) ? params.get('trap') : 'all',
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
      ['trap', it => state.trap === 'all' || it.t.includes(state.trap)],
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
      if (open('trap')) { bump('trap:all'); it.t.forEach(k => bump('trap:' + k)); }
    });
    const shown = Math.min(total, state.limit);

    counters.forEach(el => {
      const n = tally.get(el.dataset.n) || 0;
      el.textContent = n;
      const host = el.closest('.opt, [data-cat], [data-trap]');
      if (!host) return;
      const input = host.querySelector('input');
      const active = input ? input.checked
        : host.hasAttribute('data-trap') ? host.dataset.trap === state.trap : host.hasAttribute('aria-current');
      host.classList.toggle('is-zero', n === 0 && !active);
    });
    catLinks.forEach(a => {
      if (a.dataset.cat === state.cat) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
    routeIn.forEach(i => { i.checked = i.value === state.route; });
    brandIn.forEach(i => { i.checked = state.brand.has(i.value); });
    trapBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.trap === state.trap)));
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
    state.q = ''; state.cat = 'all'; state.route = 'all'; state.trap = 'all'; state.brand.clear();
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
    // On small screens the summary sits below the list, so bring the filtered list back into view.
    const work = document.getElementById('index');
    if (work && a.getBoundingClientRect().top > work.getBoundingClientRect().top) work.scrollIntoView({ block: 'start' });
  }));
  routeIn.forEach(i => i.addEventListener('change', () => { state.route = i.value; changed(); }));
  brandIn.forEach(i => i.addEventListener('change', () => {
    if (i.checked) state.brand.add(i.value); else state.brand.delete(i.value);
    changed();
  }));
  trapBtns.forEach(b => b.addEventListener('click', () => {
    state.trap = state.trap === b.dataset.trap ? 'all' : b.dataset.trap;
    changed();
  }));
  document.addEventListener('keydown', e => {
    if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
    const tag = (document.activeElement && document.activeElement.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    e.preventDefault();
    search.focus();
  });
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
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && sheet.hasAttribute('data-open')) closeSheet(); });
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


def _model_tail(it: dict) -> str:
    """Model name without a repeated leading brand ("UGREEN" + "UGREEN Revodok ..." -> "Revodok ...")."""
    brand = it["brand"].strip()
    model = it["model"].strip()
    if model.lower().startswith(brand.lower()):
        rest = model[len(brand):].strip(" -·")
        return rest or model
    return model


def _full_name(it: dict) -> str:
    return f"{it['brand'].strip()} {_model_tail(it)}"


def _desig(it: dict, lang: str) -> str:
    """Concise designation line: Brand · SKU · Category (never the full model string)."""
    return (
        f'<p class="desig"><b>{_esc(it["brand"].strip())}</b> · {_esc(_sku(it))} · '
        f'{_esc(_cat_label(it["category"], lang))}</p>'
    )


# --------------------------------------------------------------------------------------
# Figure plates: source photos are 360x360 on white with uneven margins, and roughly a
# quarter are full-bleed marketing shots. Each is trimmed to its content at build time so
# it fills the tinted stage evenly; full-bleed shots get soft corners so they read as a
# mounted print. The page then multiplies every image onto the stage tint.
# --------------------------------------------------------------------------------------
_IMG_SRC_DIR = Path(__file__).resolve().parent.parent / "data" / "product_images"
_PLATE_WHITE_POINT = 246
_PLATE_MIN_SIDE = 240
_PLATE_BLOCK_FILL = 0.92
_MEDIA_CACHE: dict[str, dict | None] = {}


def _process_plate(path: Path) -> dict | None:
    try:
        from PIL import Image, ImageChops, ImageDraw, ImageStat
    except Exception:
        return None
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    lut = [min(255, round(v * 255 / _PLATE_WHITE_POINT)) for v in range(256)]
    im = im.point(lut * 3)
    r, g, b = im.split()
    darkest = ImageChops.darker(ImageChops.darker(r, g), b)
    mask = darkest.point(lambda v: 255 if v < 250 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    block = ImageStat.Stat(mask.crop(bbox)).mean[0] / 255 >= _PLATE_BLOCK_FILL
    pad = 0 if block else 3
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    if max(w, h) < _PLATE_MIN_SIDE:
        grow = _PLATE_MIN_SIDE / max(w, h)
        gx, gy = (w * grow - w) / 2, (h * grow - h) / 2
        x0, y0, x1, y1 = x0 - gx, y0 - gy, x1 + gx, y1 + gy
    box = (max(0, int(x0)), max(0, int(y0)), min(im.width, int(round(x1))), min(im.height, int(round(y1))))
    out = im.crop(box)
    if block:
        alpha = Image.new("L", out.size, 0)
        radius = max(6, round(min(out.size) * 0.05))
        ImageDraw.Draw(alpha).rounded_rectangle((0, 0, out.width - 1, out.height - 1), radius, fill=255)
        out.putalpha(alpha)
    buf = io.BytesIO()
    out.save(buf, "WEBP", quality=90, method=6)
    return {"w": out.width, "h": out.height, "bytes": buf.getvalue()}


def _media(slug: str) -> dict | None:
    """Plate image metadata for a product slug, or None when no photo exists."""
    if slug not in _MEDIA_CACHE:
        src = _IMG_SRC_DIR / f"{slug}.webp"
        if not src.exists():
            _MEDIA_CACHE[slug] = None
        else:
            plate = _process_plate(src)
            if plate:
                _MEDIA_CACHE[slug] = {"src": f"plate/{slug}.webp", **plate}
            else:
                _MEDIA_CACHE[slug] = {"src": f"{slug}.webp", "w": 360, "h": 360, "bytes": None}
    return _MEDIA_CACHE[slug]


def _plate(it: dict, up: str, cls: str = "", *, href: str | None = None, eager: bool = False,
           caption: str | None = None) -> str:
    slug = product_slug(it["id"])
    m = _media(slug)
    if m:
        inner = (
            f'<img src="{up}assets/products/{m["src"]}" alt="{_esc(_full_name(it))}" width="{m["w"]}" '
            f'height="{m["h"]}" loading="{"eager" if eager else "lazy"}" decoding="async">'
        )
    else:
        inner = f'<span class="plate-fb">{_esc(it["brand"])}</span>'
    if caption:
        inner += f'<span class="plate-cap">{_esc(caption)}</span>'
    klass = f"plate {cls}".strip()
    if href:
        return f'<a class="{klass}" href="{href}" tabindex="-1">{inner}</a>'
    return f'<div class="{klass}">{inner}</div>'


def _spec_label(key: str, lang: str) -> str:
    if lang == "ko" and key in SPEC_LABELS_KO:
        return SPEC_LABELS_KO[key]
    return " ".join(w.upper() if w in _SPEC_ACRONYMS else w.capitalize() for w in key.split("_"))


def _chip_text(val: str, limit: int = 30) -> str:
    text = re.sub(r"\s*\([^)]*\)", "", str(val)).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip(" ,/+") + "…"
    return text


def _specs_for_lang(it: dict, lang: str) -> dict:
    if lang == "en" and it.get("specs_en"):
        return it["specs_en"]
    return it.get("specs", {})


def _chips(it: dict, n: int = 4, lang: str = "ko") -> str:
    vals = [v for v in _specs_for_lang(it, lang).values() if str(v).strip()][:n]
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
        "calc_nav": "알리 코드 계산기",
        "guides_nav": "가이드",
        "vs_nav": "1:1 대결",
        "nav_aria": "주요 메뉴",
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
        "calc_nav": "Promo Calculator",
        "guides_nav": "Buying Guides",
        "vs_nav": "VS Battles",
        "nav_aria": "Primary",
    },
}


@dataclass
class _BuildContext:
    """Per-build state shared by the render helpers (set once at the top of build_site)."""

    live_offers: dict | None = None
    promo: dict = field(default_factory=dict)
    pairs: list = field(default_factory=list)
    rivals: dict = field(default_factory=dict)
    now: datetime | None = None
    og_slugs: set = field(default_factory=set)
    site_og: str | None = None


_CTX = _BuildContext()


def _og_card(slug: str) -> bytes | None:
    """1200x630 JPEG share card. Telegram and most social previews need JPEG/PNG; WebP is not reliably rendered."""
    try:
        from PIL import Image
    except Exception:
        return None
    src = _IMG_SRC_DIR / f"{slug}.webp"
    if not src.exists():
        return None
    try:
        im = Image.open(src).convert("RGB")
    except Exception:
        return None
    side = 560
    canvas = Image.new("RGB", (1200, 630), "#FFFFFF")
    canvas.paste(im.resize((side, side), Image.Resampling.LANCZOS), ((1200 - side) // 2, (630 - side) // 2))
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=86, optimize=True)
    return buf.getvalue()


def _site_og_card(slugs: list[str]) -> bytes | None:
    """Site-wide 1200x630 share card: four vetted products on the brand shell colour (no text, no prices)."""
    try:
        from PIL import Image
    except Exception:
        return None
    tiles = []
    for slug in slugs:
        src = _IMG_SRC_DIR / f"{slug}.webp"
        if not src.exists():
            continue
        try:
            tiles.append(Image.open(src).convert("RGB").resize((240, 240), Image.Resampling.LANCZOS))
        except Exception:
            continue
        if len(tiles) == 4:
            break
    if len(tiles) < 4:
        return None
    canvas = Image.new("RGB", (1200, 630), "#0F302E")
    x = 78
    for tile in tiles:
        plate = Image.new("RGB", (252, 252), "#FFFFFF")
        plate.paste(tile, (6, 6))
        canvas.paste(plate, (x, 189))
        x += 264
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=86, optimize=True)
    return buf.getvalue()


def _og_image(it: dict) -> str | None:
    """Site-relative og:image path for a product: the JPEG share card when rendered, else the source WebP."""
    slug = product_slug(it["id"])
    if slug in _CTX.og_slugs:
        return f"/assets/og/{slug}.jpg"
    return f"/assets/products/{slug}.webp" if _media(slug) is not None else None


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


def _head(*, lang: str, title: str, description: str, up: str, cfg: dict, path: str, alternates: dict | None, og_image: str | None = None) -> str:
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
    n_verify = (cfg.get("site", {}).get("naver_verify_code") or "").strip()
    n_meta = f'\n  <meta name="naver-site-verification" content="{_esc(n_verify)}">' if n_verify else ""
    b_verify = (cfg.get("site", {}).get("bing_verify_code") or "").strip()
    b_meta = f'\n  <meta name="msvalidate.01" content="{_esc(b_verify)}">' if b_verify else ""
    rss_href = f"{base}/ko/feed.xml" if lang == "ko" else f"{base}/en/pinterest-feed.xml"
    rss_link = f'\n  <link rel="alternate" type="application/rss+xml" title="{_esc(cfg["site"]["brand_name"])} RSS" href="{_esc(rss_href)}">'
    og_image = og_image or _CTX.site_og
    og_img_tag = f'\n  <meta property="og:image" content="{_esc(base + og_image)}">' if og_image else ""
    if og_image and og_image.endswith(".jpg"):
        og_img_tag += (
            '\n  <meta property="og:image:width" content="1200">\n  <meta property="og:image:height" content="630">'
            '\n  <meta name="twitter:card" content="summary_large_image">'
        )
    # Zero static prices in meta tags, OpenGraph, or structured data (Debate 3 Consensus #1)
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(description)}">
  <meta name="theme-color" content="#0A2422">{p_meta}{g_meta}{n_meta}{b_meta}{rss_link}
  <script>document.documentElement.classList.add('js')</script>
  <link rel="canonical" href="{_esc(base + path)}">{alt}
  <meta property="og:title" content="{_esc(title)}">
  <meta property="og:description" content="{_esc(description)}">
  <meta property="og:url" content="{_esc(base + path)}">
  <meta property="og:type" content="website">{og_img_tag}
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
      <nav class="head-nav" aria-label="{t['nav_aria']}">
        <a class="nav-hi" href="{up}{lang}/tools/macbook-dock-checker/">{t['tool_nav']}</a>
        <a href="{up}{lang}/tools/ali-promo-calculator/">{t['calc_nav']}</a>
        <a href="{up}{lang}/guides/">{t['guides_nav']}</a>
        <a href="{up}{lang}/vs/">{t['vs_nav']}</a>
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
        links = (
            f'<a href="{up}ko/">한국어 허브</a><a href="{up}ko/guides/">구매 가이드</a><a href="{up}ko/vs/">1:1 대결</a>'
            f'<a href="{up}ko/tools/macbook-dock-checker/">맥북 독 판별기</a>'
            f'<a href="{up}ko/tools/ali-promo-calculator/">알리 코드 계산기</a>'
            f'<a href="{up}en/" hreflang="en">Global Hub</a><a href="{up}policy/">개인정보처리방침·대가성 고지</a>'
        )
    else:
        note = "As an Amazon Associate I earn from qualifying purchases. Static store prices are intentionally omitted; always confirm live pricing, seller terms, and import charges on the store page."
        links = (
            f'<a href="{up}en/">Global Hub</a><a href="{up}en/guides/">Buying Guides</a><a href="{up}en/vs/">VS Battles</a>'
            f'<a href="{up}en/tools/macbook-dock-checker/">MacBook Dock Tool</a>'
            f'<a href="{up}en/tools/ali-promo-calculator/">Promo Calculator</a>'
            f'<a href="{up}ko/" hreflang="ko">한국어 허브</a><a href="{up}policy/">Privacy &amp; Disclosure</a>'
        )
    return f"""<footer class="site-foot">
    <div class="wrap">
      <p>© {year} {brand}. {_esc(note)}</p>
      <nav class="foot-links" aria-label="Footer">{links}</nav>
    </div>
  </footer>
  {_aff_config_script(cfg)}"""


def _dest_banner(lang: str) -> str:
    chev = _icon("down", 15)
    if lang == "ko":
        return (
            '<div class="dest-bar" data-dest-box>'
            '<label class="dest-pick"><span>실제 배송 수령국 기준</span>'
            '<span class="sel"><select class="dest-sel" data-dest-select aria-label="배송 수령국 선택">'
            '<option value="KR">대한민국 (KR)</option>'
            '<option value="US">미국 (US)</option>'
            '<option value="OTHER">기타 국가</option>'
            f'</select>{chev}</span></label>'
            '<p class="dest-rule" data-dest-rule>대한민국 수령 기준: 미국발 목록통관 적격 미화 $200 이하 / 일반통관 및 중국·기타국발 미화 $150 이하 면세 (결제창 최종 금액·합산과세 직접 확인)</p>'
            '</div>'
        )
    return (
        '<div class="dest-bar" data-dest-box>'
        '<label class="dest-pick"><span>Shipping destination</span>'
        '<span class="sel"><select class="dest-sel" data-dest-select aria-label="Shipping destination">'
        '<option value="US">United States (US)</option>'
        '<option value="KR">South Korea (KR)</option>'
        '<option value="OTHER">Other Regions</option>'
        f'</select>{chev}</span></label>'
        '<p class="dest-rule" data-dest-rule>Shipping to United States: US de minimis exemption ended — check "Ships from US" on Amazon vs "Import charges included" at checkout on cross-border AliExpress orders.</p>'
        '</div>'
    )


_ROUTE_COPY = {
    ("ko", True): ("직구 프로모션 대조 권장", "글로벌 공식 스토어 운영"),
    ("ko", False): ("국내 배송 우선 확인", "호환성 반품·정식 유통 확인 유리"),
    ("en", True): ("Compare Direct Brand Store", "Seasonal Promo Candidate"),
    ("en", False): ("Check Amazon US First", "Domestic Ship & Compatibility Return"),
}


def _pick_badge(d: dict, lang: str) -> str:
    """Route mark: one consistent icon + label wherever a model's first-check route is named."""
    label, why = _ROUTE_COPY[(lang, bool(d["direct_pick"]))]
    cls, icon = ("is-ali", "globe") if d["direct_pick"] else ("is-local", "truck")
    return (
        f'<p class="pick {cls}"><span class="route">{_icon(icon, 16)}<span>{_esc(label)}</span></span>'
        f'<span class="why">{_esc(why)}</span></p>'
    )


def _battle(it: dict, d: dict, lang: str, dom_btn_lbl: str, ali_btn_lbl: str) -> str:
    """Ordering block: both stores in a fixed order, the first-check store holding the only filled button."""
    t = T[lang]
    pid = _esc(it["id"])
    win_tag = f'<span class="win-tag">{t["win"]}</span>'
    dom_win = not d["direct_pick"]

    def side(win: bool, store_cls: str, store_lbl: str, perk: str, meta: str, store_id: str, url: str,
             btn_lbl: str) -> str:
        return f"""<div class="side{' is-win' if win else ''}">
          <div class="side-txt">
            <div class="side-head"><span class="store {store_cls}">{store_lbl}</span>{win_tag if win else ''}</div>
            <span class="perk">{_esc(perk)}</span>
            <span class="side-meta">{_esc(meta)}</span>
            <span class="live-slot" data-live-offer data-pid="{pid}" data-store="{store_id}" hidden></span>
          </div>
          <a class="btn btn-{store_cls}{' is-first' if win else ''}" data-aff="{store_cls}" data-store="{store_id}" data-pid="{pid}" href="{_esc(url)}" target="_blank" rel="nofollow sponsored noopener"><span class="sdot"></span>{btn_lbl} {_icon('out', 15)}</a>
        </div>"""

    return f"""<div class="battle">
        {side(dom_win, d['dom_key'], t['dom_store'], t['dom_perk'], t['dom_meta'], d['dom_store_id'], d['dom_url'], dom_btn_lbl)}
        {side(not dom_win, 'ali', t['ali_store'], t['ali_perk'], t['ali_meta'], 'aliexpress', d['ali_url'], ali_btn_lbl)}
      </div>"""


def _search_blob(it: dict, lang: str) -> str:
    parts = [
        it["brand"], it["model"], it[lang]["title"],
        _cat_label(it["category"], lang), *map(str, _specs_for_lang(it, lang).values()),
    ]
    if lang == "ko":
        parts.append(it["en"]["title"])  # Korean shoppers also search by the English model name
    return _esc(unicodedata.normalize("NFKC", " ".join(parts)).lower())


# --------------------------------------------------------------------------------------
# Trap-cut filters: deterministic membership computed from category, specs, cons and the
# buying profile. No hand-tagging, so a new catalog entry is classified the moment it lands.
# --------------------------------------------------------------------------------------
TRAPS = (
    ("mac-dual", "M1~M4 맥북 듀얼모니터 호환", "Mac Dual-Monitor Ready"),
    ("airline-100wh", "100Wh 이하 기내반입", "Airline-Safe <=100Wh"),
    ("low-reset", "단일 고출력·저소음 검증", "Sustained Output / Quiet"),
    ("direct-edge", "알리 직구 메리트 우위", "Direct-Import Value"),
    ("domestic-fast", "쿠팡 로켓·프라임 권장", "Domestic Fast-Ship Pick"),
)
_MAC_DUAL_RE = re.compile(r"(displaylink|thunderbolt\s?4|썬더볼트\s?4)", re.IGNORECASE)
_RESET_RE = re.compile(r"(리셋|재분배|재협상|renegotiat|\breset\b)", re.IGNORECASE)
_QUIET_RE = re.compile(r"(무소음|팬리스|fanless|silent|0\s?dba)", re.IGNORECASE)
_WH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*Wh", re.IGNORECASE)
_MAH_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{4,6})\s*mAh", re.IGNORECASE)
_WATT_RE = re.compile(r"(\d{2,3})\s*W\b")


def battery_wh(it: dict) -> float | None:
    """Rated watt-hours: the printed Wh figure when present, else mAh x 3.6 V nominal cell voltage."""
    text = " ".join(str(v) for v in it.get("specs", {}).values()) + " " + it.get("model", "")
    m = _WH_RE.search(text)
    if m:
        return float(m.group(1))
    m = _MAH_RE.search(text)
    return round(int(m.group(1).replace(",", "")) * 3.6 / 1000, 1) if m else None


def single_port_watts(it: dict) -> int | None:
    """Single-port output in watts from the max_output spec; None when only a shared total is stated."""
    raw = str(it.get("specs", {}).get("max_output", ""))
    if not raw:
        return None
    m = re.search(r"(\d{2,3})\s*W\s*Single", raw, re.IGNORECASE)
    if m:
        return int(m.group(1))
    paren = re.search(r"\(([^)]*)\)", raw)
    if paren:
        vals = [int(x) for x in _WATT_RE.findall(paren.group(1))]
        if vals:
            return max(vals)
    if re.search(r"total", raw, re.IGNORECASE):
        return None
    m = _WATT_RE.search(raw)
    return int(m.group(1)) if m else None


def trap_keys(it: dict, lang: str) -> list[str]:
    """Trap-cut filter keys a model belongs to (language decides the route-based keys)."""
    keys: list[str] = []
    specs = it.get("specs", {})
    if it["category"] == "hubs" and specs.get("video") and _MAC_DUAL_RE.search(f'{it["model"]} {specs["video"]}'):
        keys.append("mac-dual")
    if it["category"] == "powerbanks":
        wh = battery_wh(it)
        if wh is not None and wh <= 100:
            keys.append("airline-100wh")
    spec_text = " ".join(str(v) for v in list(specs.values()) + list(it.get("specs_en", {}).values()))
    cons_text = " ".join(it.get("ko", {}).get("cons", []) + it.get("en", {}).get("cons", []))
    watts = single_port_watts(it) if it["category"] in ("chargers", "powerbanks") else None
    if (watts is not None and watts >= 100 and not _RESET_RE.search(cons_text)) or _QUIET_RE.search(spec_text):
        keys.append("low-reset")
    if _profile(it, lang)["direct_pick"]:
        # For Korea-bound orders a direct-import edge only holds under the USD 150 duty-free line.
        if lang == "en" or float(it.get("msrp_usd") or 0) <= 150:
            keys.append("direct-edge")
    else:
        keys.append("domestic-fast")
    return keys


# --------------------------------------------------------------------------------------
# Reference anchor strip + live offer line: the numeric anchor shown above every store CTA.
# --------------------------------------------------------------------------------------
def _anchor_strip(it: dict, lang: str, calc_base: str) -> str:
    """Manufacturer reference MSRP, customs-line verdict and a deep link into the promo calculator."""
    href = f"{calc_base}?p={quote(it['id'])}"
    if lang == "ko":
        if not it.get("msrp_krw"):
            return ""
        cls, rule = kr_customs_anchor(float(it.get("msrp_usd") or 0))
        return (
            f'<p class="anchor"><span>출시 참고가 MSRP <b class="num">{int(it["msrp_krw"]):,}원</b></span>'
            f'<span class="anchor-rule {cls}">{rule}</span><a href="{href}">코드 체감가 계산</a></p>'
        )
    if not it.get("msrp_usd"):
        return ""
    return (
        f'<p class="anchor"><span>Ref MSRP <b class="num">${float(it["msrp_usd"]):,.2f}</b></span>'
        f'<span class="anchor-rule">Direct import: duties at checkout</span><a href="{href}">Promo Calc</a></p>'
    )


def _live_line(it: dict, lang: str) -> str:
    """Unexpired live_offers_cache entry for a model, labelled strictly by where the number came from."""
    entry = pick_live_offer(_CTX.live_offers, it["id"], lang, now=_CTX.now)
    if not entry:
        return ""
    day = _esc(str(entry.get("observed_at", ""))[:10])
    price = _esc(entry.get("price_text") or "")
    if not price:
        return ""
    if entry["source_kind"] == "ali_official_api":
        label = "실시간 알리 API 특가" if lang == "ko" else "Live AliExpress API Offer"
        meta = f" (조회일 {day})" if lang == "ko" else f" (Fetched {day})"
        cls = "is-api"
    else:
        label = (
            f"최근 커뮤니티 포착 핫딜 기준가 (관측일 {day} · 종료 가능)"
            if lang == "ko"
            else f"Recent Community-Spotted Deal Benchmark (Observed {day} · May Expire)"
        )
        meta, cls = "", "is-community"
    return (
        f'<p class="live-line {cls}" data-live-kind="{_esc(entry["source_kind"])}" '
        f'data-expires-at="{_esc(entry.get("expires_at", ""))}"><span class="live-lbl">{label}{meta}</span>'
        f'<b class="num">{price}</b></p>'
    )


def _money(value: float) -> str:
    return f"${int(value)}" if float(value).is_integer() else f"${value:,.2f}"


def _tier_chip(tier: dict, lang: str) -> str:
    """Promo tier chip: a one-click copy button when a code exists, otherwise a plain tier guide."""
    h = HUB[lang]
    spend = h["spend"].format(m=_money(tier["min_spend_usd"]))
    off = f"−{_money(tier['off_usd'])}"
    if tier.get("code"):
        code = _esc(tier["code"])
        return (
            f'<li><button type="button" class="tier" data-copy="{code}" aria-label="{_esc(h["copy_aria"].format(c=tier["code"]))}">'
            f'<span>{spend}</span><b>{off}</b><span class="copy-swap"><code class="copy-idle">{code}</code>'
            f'<span class="copy-done">{h["copy_done"]}</span></span></button></li>'
        )
    return f'<li class="tier"><span>{spend}</span><b>{off}</b></li>'


def _community_codes(lang: str) -> str:
    """Copy chips for promo codes spotted in community posts (Ppomppu -> KO board, Reddit -> EN board)."""
    h = HUB[lang]
    chips = []
    for c in (_CTX.live_offers or {}).get("promo_codes", []):
        if ("ppomppu" in str(c.get("signal_source", ""))) != (lang == "ko"):
            continue
        code = _esc(c["code"])
        chips.append(
            f'<li data-expires-at="{_esc(c.get("expires_at", ""))}"><button type="button" class="tier" data-copy="{code}" '
            f'aria-label="{_esc(h["copy_aria"].format(c=c["code"]))}"><span class="copy-swap"><code class="copy-idle">{code}</code>'
            f'<span class="copy-done">{h["copy_done"]}</span></span></button></li>'
        )
    if not chips:
        return ""
    day = _esc(str((_CTX.live_offers or {}).get("updated_at", ""))[:10])
    return f'<p class="board-h">{_esc(h["community_codes"].format(d=day))}</p><ul class="tiers">{"".join(chips[:6])}</ul>'


def _situation_board(lang: str, lang_pfx: str) -> str:
    """Above-the-fold Live Deal & Compatibility Situation Board for the main hubs."""
    h = HUB[lang]
    day = sale_reference_date(lang, _CTX.now)
    sig = sale_signal(lang, day)
    promo = active_promo(_CTX.promo, lang, day)
    ref = active_promo({**_CTX.promo, "events": []}, lang, day)
    notice = (_CTX.promo.get("notice") or {}).get(lang, "")
    src = f'<span> · {_esc(promo["source"])}</span>' if promo["kind"] == "event" and promo.get("source") else ""
    payload = json.dumps(
        {
            "tz": SALE_TZ_HOURS[lang],
            "copy": {k: list(v) for k, v in SALE_COPY[lang].items()},
            "date_tpl": h["board_date"],
            "spend_tpl": h["spend"],
            "copy_done": h["copy_done"],
            "copy_aria": h["copy_aria"],
            "ref": {"id": ref["id"], "label": ref["label"], "source": "", "tiers": ref["tiers"]},
            "events": promo_events_for_lang(_CTX.promo, lang),
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")
    arrow = _icon("arrow", 14)
    return f"""<section class="board" aria-label="{h['board_aria']}" data-board data-window="{sig['window']}" data-promo-id="{_esc(promo['id'])}">
      <div class="board-sig is-{sig['tone']}" data-board-sig>
        <span class="lamps" aria-hidden="true"><i></i><i></i><i></i></span>
        <div>
          <h2 class="board-state" data-board-label>{_esc(sig['label'])}</h2>
          <p class="board-sub"><span data-board-sub>{_esc(sig['sub'])}</span><span class="board-date num" data-board-date>{_esc(h['board_date'].format(d=day.isoformat()))}</span></p>
        </div>
      </div>
      <div class="board-codes">
        <p class="board-h" data-board-tiers-label>{_esc(promo['label'])}{src}</p>
        <ul class="tiers" data-board-tiers>{''.join(_tier_chip(t, lang) for t in promo['tiers'])}</ul>
        {_community_codes(lang)}
        <p class="board-note">{_icon('caution', 14)}<span>{_esc(notice)}</span></p>
      </div>
      <div class="board-act">
        <a class="btn btn-primary btn-s" href="{lang_pfx}tools/ali-promo-calculator/">{_icon('calc', 15)}{h['board_calc']} {arrow}</a>
        <a class="text-link" href="{lang_pfx}vs/">{_esc(h['board_vs'].format(n=len(_CTX.pairs)))} {arrow}</a>
      </div>
      <script type="application/json" data-board-json>{payload}</script>
    </section>"""


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
        "views": [("list", "리스트", "리스트 뷰"), ("cards", "카드", "카드 뷰")],
        "cols": ("모델 · 주요 사양", "구매 경로 판단", "판매처 확인"),
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
        "traps_h": "오구매 컷 필터",
        "trap_all": "전체",
        "board_aria": "실시간 구매 타이밍·프로모 코드 현황판",
        "board_calc": "코드 체감가 계산기",
        "board_vs": "1:1 라이벌 대결 {n}선",
        "board_date": "기준일 {d} (KST)",
        "spend": "{m} 이상",
        "copy_done": "복사됨 ✓",
        "copy_aria": "프로모 코드 {c} 복사",
        "community_codes": "커뮤니티 포착 코드 (관측일 {d} · 종료 가능)",
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
        "views": [("list", "List", "List view"), ("cards", "Cards", "Card view")],
        "cols": ("Model · key specs", "Buying route", "Store check"),
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
        "traps_h": "Trap-cut filters",
        "trap_all": "All Vetted",
        "board_aria": "Live deal timing and promo code board",
        "board_calc": "Promo Calculator",
        "board_vs": "{n} VS Battles",
        "board_date": "As of {d} (PT)",
        "spend": "{m}+",
        "copy_done": "Copied ✓",
        "copy_aria": "Copy promo code {c}",
        "community_codes": "Community-spotted codes (Observed {d} · May Expire)",
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


def _render_row(it: dict, lang: str, pfx: str, up: str, idx: int = 99) -> str:
    t, h, d, loc = T[lang], HUB[lang], _profile(it, lang), it[lang]
    slug = product_slug(it["id"])
    href = f"{pfx}{slug}/"
    name = _esc(_short_name(it))
    spec_vals = [v for v in _specs_for_lang(it, lang).values() if str(v).strip()][:3]
    specs = "".join(f'<li class="pill">{_esc(_chip_text(v, 34))}</li>' for v in spec_vals)
    call = h["call_ali"] if d["direct_pick"] else h["call_dom"]
    why = h["why_ali"] if d["direct_pick"] else h["why_dom"]
    cons = "".join(f"<dd>{_esc(c)}</dd>" for c in loc.get("cons", [])[:2])
    attrs = (
        f'data-c="{_esc(it["category"])}" data-b="{_esc(it["brand"])}" '
        f'data-r="{"ali" if d["direct_pick"] else "dom"}" data-prio="{d["prio"]}" '
        f'data-traps="{" ".join(trap_keys(it, lang))}" data-q="{_search_blob(it, lang)}"'
    )
    calc_base = f"{pfx[:-2]}tools/ali-promo-calculator/"

    def buy(store_cls: str, store_id: str, url: str, label: str, pick: bool) -> str:
        return (
            f'<a class="buy {store_cls}{" is-pick" if pick else ""}" data-aff="{store_cls}" data-store="{store_id}" data-pid="{_esc(it["id"])}" '
            f'href="{_esc(url)}" target="_blank" rel="nofollow sponsored noopener" aria-label="{label} · {name}">'
            f'<span class="sdot"></span>{label} {_use("out", 13)}</a>'
        )

    return f"""
        <li class="row" {attrs}>
          {_plate(it, up, "r-plate", href=href, eager=(idx < 6))}
          <div class="r-info">
            <h3 class="r-title"><a href="{href}">{_esc(loc['title'])}</a></h3>
            <p class="desig r-meta"><b>{_esc(it['brand'])}</b> · {_esc(_cat_label(it['category'], lang))}</p>
            <ul class="r-spec"><li class="pill code">{_esc(_sku(it))}</li>{specs}</ul>
          </div>
          <div class="r-verd">
            <div class="r-route {'is-ali' if d['direct_pick'] else 'is-local'}">
              <span class="route">{_use('globe' if d['direct_pick'] else 'truck', 16)}<span>{_esc(call)}</span></span>
              <span class="why">{_esc(why)}</span>
            </div>
            <button type="button" class="r-more" data-more aria-expanded="false" aria-controls="d-{slug}">{h['more_btn']} {_use('down')}</button>
          </div>
          <div class="r-act">
            {_live_line(it, lang)}{_anchor_strip(it, lang, calc_base)}
            <div class="buys">
              {buy(d['dom_key'], d['dom_store_id'], d['dom_url'], t['dom_short'], not d['direct_pick'])}
              {buy('ali', 'aliexpress', d['ali_url'], t['ali_short'], d['direct_pick'])}
            </div>
            <p class="row-disc">{_esc(h['row_disc'])}</p>
          </div>
          <div class="drawer" id="d-{slug}"><div class="drawer-in"><div class="drawer-box">
            <dl><div class="cons"><dt>{_use('caution', 14)}{h['con']}</dt>{cons}</div><div><dt>{h['verdict']}</dt><dd>{_esc(loc['verdict'])}</dd></div></dl>
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
    ic = f'<span class="feat-ic">{_icon("dual", 22)}</span>'
    arrow = _icon("arrow", 14)
    n_guides = len(GUIDES_BY_LANG[lang])
    if lang == "ko":
        return (
            f'<section class="feat-strip" aria-label="핵심 호환 판별기와 구매 가이드">{ic}'
            f'<div><strong>맥북 듀얼모니터 독 호환 판별기 (M1·M2·M3·M4) · 구매 가이드 {n_guides}편</strong>'
            f'<p>화면 복제(미러링) 실패 없이 내 맥북 칩셋·클램쉘·OTT 조건에 맞는 도킹스테이션 구성을 10초 만에 확인하세요.</p></div>'
            f'<div class="feat-actions">'
            f'<a class="btn btn-primary btn-s" href="{up_to_lang}tools/macbook-dock-checker/">판별기 열기 {arrow}</a>'
            f'<a class="btn btn-s" href="{up_to_lang}guides/">구매 가이드 {n_guides}편 {arrow}</a>'
            f'</div></section>'
        )
    return (
        f'<section class="feat-strip" aria-label="Compatibility Tools and Buying Guides">{ic}'
        f'<div><strong>MacBook Dual-Monitor Dock Checker &amp; {n_guides} Engineering Buying Guides</strong>'
        f'<p>Verify M1–M4 external monitor limits, USB4 NVMe thermals, TSA 100Wh power banks, and Hall-effect/TMR controllers before buying.</p></div>'
        f'<div class="feat-actions">'
        f'<a class="btn btn-primary btn-s" href="{up_to_lang}tools/macbook-dock-checker/">MacBook Dock Checker {arrow}</a>'
        f'<a class="btn btn-s" href="{up_to_lang}guides/">{n_guides} Buying Guides {arrow}</a>'
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
      <div class="sm"><dt><span class="store {dom_key}">{h['m_local']}</span></dt><dd><a href="?route=dom" data-route-link="dom"><span class="sm-v num">{n_local}</span>{_icon('filter', 14)}</a><span class="sm-s">{_esc(h['m_local_sub'])}</span></dd></div>
      <div class="sm"><dt><span class="store ali">{h['m_direct']}</span></dt><dd><a href="?route=ali" data-route-link="ali"><span class="sm-v num">{n_direct}</span>{_icon('filter', 14)}</a><span class="sm-s">{_esc(h['m_direct_sub'])}</span></dd></div>
      <div class="sm"><dt>{h['m_filter']}</dt><dd><span class="sm-v">{_esc(h['m_filter_v'])}</span><span class="sm-s">{_esc(h['m_filter_sub'])}</span></dd></div>"""

    sort_html = "".join(f'<option value="{k}">{_esc(v)}</option>' for k, v in h["sorts"])
    view_html = "".join(
        f'<button type="button" data-view-btn="{k}" aria-pressed="{"true" if k == "list" else "false"}" title="{_esc(tip)}">'
        f'{_icon(k, 15)}<span class="lbl">{_esc(v)}</span></button>'
        for k, v, tip in h["views"]
    )
    strings = dict(h["js"])
    trap_labels = {key: (ko if lang == "ko" else en) for key, ko, en in TRAPS}
    strings.update({
        "cats": {c: _cat_label(c, lang) for c in cats},
        "route": {"ali": h["r_ali"], "dom": h["r_dom"]},
        "traps": trap_labels,
    })
    board_html, traps_html = "", ""
    if cat is None:
        board_html = _situation_board(lang, up_lang)
        trap_counts = Counter(k for it, _ in profiles for k in trap_keys(it, lang))
        trap_btns = [
            f'<button type="button" class="trap" data-trap="all" aria-pressed="true"><span>{_esc(h["trap_all"])} '
            f'(<span class="num" data-n="trap:all">{n}</span>)</span></button>'
        ] + [
            f'<button type="button" class="trap" data-trap="{key}" aria-pressed="false">{_esc(trap_labels[key])} '
            f'<span class="num" data-n="trap:{key}">{trap_counts[key]}</span></button>'
            for key, _ko, _en in TRAPS
        ]
        traps_html = (
            f'<div class="traps" role="group" aria-label="{h["traps_h"]}"><span class="traps-h">{h["traps_h"]}</span>'
            f'<div class="traps-row">{"".join(trap_btns)}</div></div>'
        )
    i18n = json.dumps(strings, ensure_ascii=False).replace("</", "<\\/")

    body = f"""
<body class="{lang} is-hub">
  {_legal_strip(lang)}
  {_site_header(lang, up, cfg, switch)}
  {ICON_SPRITE}
  <main class="wrap hub" data-hub data-view="list" data-scope="{_esc(cat or 'all')}" data-page-size="{PAGE_SIZE}">
    {crumbs}
    <header class="idx-head">
      <h1>{_esc(h1)}</h1>
      <p class="stamp">{h['stamp'].format(date=_esc(latest))}</p>
    </header>
    {board_html}
    <dl class="summary" aria-label="{h['summary_lbl']}">{summary_html}</dl>
    {_dest_banner(lang)}
    {_featured_strip(lang, up_lang)}

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
          <label class="sort sel"><span class="sr-only">{h['sort_lbl']}</span><select data-sort>{sort_html}</select>{_icon('down', 15)}</label>
          <button type="button" class="fbtn" data-sheet-open aria-controls="facets">{_icon('filter', 16)}<span>{h['filters']}</span><b class="num" data-fcount hidden>0</b></button>
        </div>
        {traps_html}
        <div class="status">
          <p class="status-text num" data-status aria-live="polite"></p>
          <div class="on-chips" data-chips></div>
          <div class="seg" role="group" aria-label="{h['view_lbl']}">{view_html}</div>
        </div>
        <h2 class="sr-only">{h['list_h']}</h2>
        <div class="ledger">
          <div class="rows-head" aria-hidden="true"><span></span><span>{h['cols'][0]}</span><span>{h['cols'][1]}</span><span>{h['cols'][2]}</span></div>
          <ol class="rows" data-rows>{''.join(_render_row(it, lang, pfx, up, idx=i) for i, (it, _) in enumerate(profiles))}</ol>
        </div>
        <div class="empty" data-empty hidden><strong>{h['empty_t']}</strong><p>{h['empty_d']}</p><button type="button" data-reset>{h['reset']}</button></div>
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


def _product_card(it: dict, lang: str, pfx: str = "../../p/", up: str = "../../../", hl: str = "h4") -> str:
    """Showcase card used by the Dock Checker results and the guide hardware lists."""
    loc, d = it[lang], _profile(it, lang)
    slug = product_slug(it["id"])
    href = f"{pfx}{slug}/"
    if lang == "ko":
        dom_lbl, ali_lbl = "쿠팡 실시간 가격·재고 확인", "알리 직구 조건 확인"
        detail_lbl, con_lbl = "상세 스펙·단점 보기", "주의할 단점:"
    else:
        dom_lbl, ali_lbl = "Check Price on Amazon", "Check AliExpress"
        detail_lbl, con_lbl = "Specs & Caveats", "Caveat:"
    dom_first = not d["direct_pick"]
    return (
        f'<article class="pcard tool-card">'
        f'{_plate(it, up, "pcard-plate", href=href)}'
        f'<div class="pcard-body">'
        f'<{hl} class="pcard-title"><a href="{href}">{_esc(loc["title"])}</a></{hl}>'
        f'{_desig(it, lang)}'
        f'<p class="pcard-sum">{_esc(loc["summary"])}</p>'
        f'<p class="note-c">{_icon("caution", 15)}<span><strong>{con_lbl}</strong> {_esc(loc["cons"][0])}</span></p>'
        f'</div>'
        f'<div class="pcard-foot">'
        f'{_live_line(it, lang)}{_anchor_strip(it, lang, pfx[:-2] + "tools/ali-promo-calculator/")}'
        f'<div class="actions">'
        f'<a class="btn btn-{d["dom_key"]}{" is-first" if dom_first else ""}" data-aff="dom" data-store="{d["dom_store_id"]}" data-pid="{_esc(it["id"])}" href="{_esc(d["dom_url"])}" target="_blank" rel="nofollow sponsored noopener"><span class="sdot"></span>{dom_lbl}</a>'
        f'<a class="btn btn-ali{"" if dom_first else " is-first"}" data-aff="ali" data-store="aliexpress" data-pid="{_esc(it["id"])}" href="{_esc(d["ali_url"])}" target="_blank" rel="nofollow sponsored noopener"><span class="sdot"></span>{ali_lbl}</a>'
        f'</div>'
        f'<a class="text-link" href="{href}">{_esc(detail_lbl)} {_icon("arrow", 14)}</a>'
        f'</div>'
        f'</article>'
    )


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
        for k, v in _specs_for_lang(it, lang).items()
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
        fig, cust_lbl = "그림 1", "통관 · 발송지 체크"
    else:
        title = f"{loc['title']} — Specs, Caveats & Buying Guide | {brand}"
        h_cust, h_spec, h_pc = "Destination Customs & Fulfillment Checklist", "Technical Specifications", "Strengths & Real-World Caveats"
        pros_h, cons_h = "Strengths", "Real-World Caveats"
        rel_h, decide_h = "Related Vetted Hardware", "Buying Decision"
        stamp = f"Specs reviewed {_esc(it.get('updated_at', ''))}. Confirm live price, seller terms, and shipping on the store page."
        switch = f"한국어 페이지 {_icon('arrow', 14)}"
        dom_btn_lbl, ali_btn_lbl = "Check Price on Amazon", "Check AliExpress"
        fig, cust_lbl = "Fig. 1", "Customs & Fulfillment Note"

    dock_callout = ""
    if cat == "hubs":
        dock_txt = (
            "맥북 M1·M2·M3·M4 모델별 듀얼모니터 호환 여부를 판별기에서 먼저 확인하세요"
            if lang == "ko"
            else "Using a MacBook? Verify M1/M2/M3/M4 dual-monitor compatibility in our interactive checker first"
        )
        dock_callout = (
            f'<p><a class="text-link" href="../../tools/macbook-dock-checker/">{_icon("dual", 16)}'
            f'<span>{dock_txt}</span></a></p>'
        )

    rival_html = ""
    for i, pair in enumerate(_CTX.rivals.get(it["id"], [])[:3]):
        rid = pair["b"] if pair["a"] == it["id"] else pair["a"]
        rival = next((x for x in (items or []) if x["id"] == rid), None)
        if rival is None:
            continue
        rname = vs_name(rid, rival)
        if lang == "ko":
            label = f"이 모델과 가장 많이 비교하는 라이벌: {rname}" if i == 0 else f"다른 1:1 대결: vs {rname}"
        else:
            label = f"Most-compared rival for this model: {rname}" if i == 0 else f"Also compared: vs {rname}"
        rival_html += (
            f'<a class="text-link" href="../../vs/{_esc(pair["slug"])}/">{_icon("scale", 16)}'
            f'<span>{_esc(label)}</span>{_icon("arrow", 14)}</a>'
        )
    if rival_html:
        rival_html = f'<p class="rival">{rival_html}</p>'

    rel_items = _related(it, items or [], 3)
    related_html = ""
    if rel_items:
        rel_cards = []
        for r in rel_items:
            r_slug = product_slug(r["id"])
            rel_cards.append(f"""
        <article class="pcard rel">
          {_plate(r, up, "pcard-plate", href=f"../{r_slug}/")}
          <div class="pcard-body">
            <h3 class="pcard-title"><a href="../{r_slug}/">{_esc(r[lang]['title'])}</a></h3>
            {_desig(r, lang)}
            {_pick_badge(_profile(r, lang), lang)}
          </div>
        </article>""")
        related_html = f'<section class="related" aria-labelledby="rel-h"><h2 id="rel-h">{rel_h}</h2><div class="rel-grid">{"".join(rel_cards)}</div></section>'

    has_img = _media(slug) is not None
    caption = f"{fig} · {it['brand'].strip()} {_sku(it)}"

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

    <div class="detail">
      <header class="sheet d-hero">
        {_plate(it, up, "d-plate", eager=True, caption=caption)}
        <div class="d-intro">
          <h1>{_esc(loc["title"])}</h1>
          <p class="desig"><b>{_esc(it["brand"].strip())}</b> · {_esc(_model_tail(it))}</p>
          <p class="dek">{_esc(loc["summary"])}</p>
          {_chips(it, 4, lang=lang)}
          {dock_callout}
        </div>
      </header>

      <aside class="d-aside" aria-label="{decide_h}">
        <div class="sheet decide">
          <h2 class="decide-title">{decide_h}</h2>
          {_pick_badge(d, lang)}
          <p class="decide-verdict">{_esc(loc['verdict'])}</p>
          {_live_line(it, lang)}
          {_anchor_strip(it, lang, "../../tools/ali-promo-calculator/")}
          {_battle(it, d, lang, dom_btn_lbl, ali_btn_lbl)}
          <p class="btn-disc">{_esc(t['btn_disc'])}</p>
          <p class="decide-stamp">{stamp}</p>
          <a class="decide-switch" href="{up}{other}/p/{slug}/" hreflang="{other}">{switch}</a>
          {rival_html}
        </div>
      </aside>

      <div class="d-body">
        <section class="section customs" aria-labelledby="h-cust">
          <h2 id="h-cust">{h_cust}</h2>
          {_dest_banner(lang)}
          <div class="notice customs-note">
            {_icon('caution', 18)}
            <div><strong>{cust_lbl}</strong><span>{_esc(d['customs_note'])}</span></div>
          </div>
        </section>

        <section class="section" aria-labelledby="h-spec">
          <h2 id="h-spec">{h_spec}</h2>
          <div class="table-sheet"><table class="spec-table"><tbody>{spec_rows}</tbody></table></div>
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
    og_img = _og_image(it) if has_img else None
    head = _head(lang=lang, title=title, description=loc["summary"], up=up, cfg=cfg, path=f"/{lang}/p/{slug}/",
                 alternates={"ko": f"/ko/p/{slug}/", "en": f"/en/p/{slug}/"}, og_image=og_img)
    return head + body


def _gate_plates(items: list[dict], start: int, n: int = 4) -> str:
    """A strip of real product plates for the gateway, one model per category for variety."""
    seen: set[str] = set()
    picks = []
    for it in sorted(items, key=lambda x: x["id"]):
        if it["category"] in seen or _media(product_slug(it["id"])) is None:
            continue
        seen.add(it["category"])
        picks.append(it)
    chosen = picks[start:start + n]
    if len(chosen) < n:
        return ""
    return '<div class="region-plates" aria-hidden="true">' + "".join(_plate(it, "") for it in chosen) + "</div>"


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
        <a href="en/tools/ali-promo-calculator/">Promo Calculator</a>
        <a href="en/guides/">Buying Guides</a>
        <a href="en/vs/">VS Battles</a>
        <a href="policy/">Policy · 정책</a>
      </nav>
    </div>
  </header>
  <main class="wrap">
    <section class="gate-hero">
      <h1>{brand}</h1>
      <p class="dek" lang="ko">동일 모델 데스크·USB-C 기어 호환성 판별 및 국내 배송 vs 해외직구 조건 비교</p>
      <p class="page-meta">Vetted hardware compatibility &amp; buying hub</p>
    </section>
    <div class="regions">
      <section class="sheet region" data-region="ko" lang="ko">
        {_gate_plates(items, 0)}
        <div class="region-body">
          <div class="region-head"><h2><a href="ko/" hreflang="ko">한국어 허브 <span class="code-tag">KR</span></a></h2><span class="suggest" hidden>브라우저 언어 기준 추천</span></div>
          <p class="region-sub">쿠팡 국내 배송 vs 알리익스프레스 직구 · 통관/단점 검수</p>
          <dl class="region-stats">
            <div><dt>검수 모델</dt><dd>{n_models}종</dd></div>
            <div><dt>분류</dt><dd>{n_cats}개 카테고리</dd></div>
            <div><dt>가이드·대결</dt><dd>가이드 {len(GUIDES_BY_LANG['ko'])}편 · 1:1 대결 {len(_CTX.pairs)}선</dd></div>
          </dl>
          <span class="region-go">한국어 비교 허브 열기 {_icon('arrow', 16)}</span>
        </div>
      </section>
      <section class="sheet region" data-region="en">
        {_gate_plates(items, 4)}
        <div class="region-body">
          <div class="region-head"><h2><a href="en/" hreflang="en">Global Hub <span class="code-tag">EN</span></a></h2><span class="suggest" hidden>Suggested for you</span></div>
          <p class="region-sub">Amazon US vs Direct Import · {len(GUIDES_EN)} Buying Guides · {len(_CTX.pairs)} VS Battles</p>
          <dl class="region-stats">
            <div><dt>Vetted gear</dt><dd>{n_models} models</dd></div>
            <div><dt>Guides</dt><dd>12 deep dives</dd></div>
            <div><dt>Interactive</dt><dd>Dock Checker</dd></div>
          </dl>
          <span class="region-go">Open Global Hub {_icon('arrow', 16)}</span>
        </div>
      </section>
    </div>
  </main>
  <footer class="site-foot"><div class="wrap"><p>{_esc(DISCLOSURE_EN)}</p><nav class="foot-links" aria-label="Footer"><a href="ko/">한국어 허브</a><a href="ko/guides/">구매 가이드</a><a href="ko/vs/">1:1 대결</a><a href="en/">Global Hub</a><a href="en/guides/">Guides</a><a href="en/vs/">VS Battles</a><a href="policy/">Policy</a></nav></div></footer>
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
      <nav class="head-nav" aria-label="Primary"><a href="../ko/" hreflang="ko">한국어 허브</a><a href="../en/" hreflang="en">Global Hub</a></nav>
    </div>
  </header>
  <main class="wrap">
    <article class="sheet prose">
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


def site_url_paths(items: list[dict]) -> list[str]:
    """Every canonical page path the build writes, in sitemap order (also the IndexNow submission list)."""
    paths = ["/", "/ko/", "/en/", "/policy/"]
    for lang in ("ko", "en"):
        paths += [f"/{lang}/tools/macbook-dock-checker/", f"/{lang}/tools/ali-promo-calculator/"]
    for lang in ("ko", "en"):
        paths.append(f"/{lang}/guides/")
        paths += [f"/{lang}/guides/{g['slug']}/" for g in GUIDES_BY_LANG[lang]]
    pairs = active_pairs({it["id"]: it for it in items})
    for lang in ("ko", "en"):
        paths.append(f"/{lang}/vs/")
        paths += [f"/{lang}/vs/{p['slug']}/" for p in pairs]
    for cat in sorted({it["category"] for it in items}):
        paths += [f"/ko/c/{_cat_slug(cat)}/", f"/en/c/{_cat_slug(cat)}/"]
    for it in items:
        slug = product_slug(it["id"])
        paths += [f"/ko/p/{slug}/", f"/en/p/{slug}/"]
    return paths


def _render_sitemap(items: list[dict], cfg: dict) -> str:
    base = cfg["site"]["base_url"].rstrip("/")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries = "\n".join(
        f"  <url><loc>{_esc(base + path)}</loc><lastmod>{today}</lastmod></url>" for path in site_url_paths(items)
    )
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


def build_site(approved_items: list[dict], cfg: dict, dist_dir: Path, live_offers: dict | None = None,
               now: datetime | None = None) -> dict:
    """Generate every static page: gateway, hubs (with the situation board), category and product pages,
    both tools, KO + EN buying guides, KO + EN VS battles, policy, and the sitemap."""
    _clean_dist(dist_dir)
    items_by_id = {it["id"]: it for it in approved_items}
    pairs = active_pairs(items_by_id)

    global _CTX
    _CTX = _BuildContext(
        live_offers=live_offers,
        promo=load_promo_tiers(),
        pairs=pairs,
        rivals=rivals_by_product(pairs),
        now=now or datetime.now(timezone.utc),
    )

    css = SHARED_CSS.strip().replace("__PAGE_NEXT__", str(PAGE_SIZE + 1))
    _write(dist_dir / "assets" / "style.css", css + "\n")
    _write(dist_dir / "assets" / "app.js", APP_JS.strip() + "\n")

    # Copy vetted 360x360 WebP product images into dist/assets/products/ (feeds), write the trimmed
    # figure-plate derivatives the pages display, and render 1200x630 JPEG share cards for link previews.
    dst_img_dir = dist_dir / "assets" / "products"
    og_dir = dist_dir / "assets" / "og"
    if _IMG_SRC_DIR.exists():
        (dst_img_dir / "plate").mkdir(parents=True, exist_ok=True)
        og_dir.mkdir(parents=True, exist_ok=True)
        for img_file in sorted(_IMG_SRC_DIR.glob("*.webp")):
            shutil.copy2(img_file, dst_img_dir / img_file.name)
            plate = _media(img_file.stem)
            if plate and plate.get("bytes"):
                (dst_img_dir / "plate" / img_file.name).write_bytes(plate["bytes"])
            card = _og_card(img_file.stem)
            if card:
                (og_dir / f"{img_file.stem}.jpg").write_bytes(card)
                _CTX.og_slugs.add(img_file.stem)
        seen_cats: set[str] = set()
        site_slugs = []
        for it in sorted(approved_items, key=lambda x: x["id"]):
            slug = product_slug(it["id"])
            if it["category"] not in seen_cats and slug in _CTX.og_slugs:
                seen_cats.add(it["category"])
                site_slugs.append(slug)
        site_card = _site_og_card(site_slugs)
        if site_card:
            (og_dir / "site.jpg").write_bytes(site_card)
            _CTX.site_og = "/assets/og/site.jpg"

    _write(dist_dir / "index.html", _render_root_gateway(cfg, approved_items))
    _write(dist_dir / "policy" / "index.html", _render_policy_page(cfg))
    _write(dist_dir / "ko" / "index.html", _render_hub(approved_items, cfg, "ko"))
    _write(dist_dir / "en" / "index.html", _render_hub(approved_items, cfg, "en"))

    shell = dict(head_fn=_head, legal_fn=_legal_strip, header_fn=_site_header, footer_fn=_site_footer)

    for lang in ("ko", "en"):
        # MacBook Dual-Monitor Dock Compatibility Checker
        _write(
            dist_dir / lang / "tools" / "macbook-dock-checker" / "index.html",
            render_dock_checker_page(lang=lang, items_by_id=items_by_id, cfg=cfg, card_fn=_product_card,
                                     icon_fn=_icon, **shell),
        )
        # 2-tier AliExpress Promo & Customs Calculator
        _write(
            dist_dir / lang / "tools" / "ali-promo-calculator" / "index.html",
            render_promo_calculator_page(
                lang=lang, items=approved_items, cfg=cfg, promo_data=_CTX.promo, icon_fn=_icon,
                cat_label_fn=_cat_label, name_fn=_full_name, slug_fn=product_slug, now=_CTX.now, **shell,
            ),
        )
        # 12 buying guides per language (/ko/guides/ localized for Korean buyers, /en/guides/)
        _write(
            dist_dir / lang / "guides" / "index.html",
            render_guides_index(lang=lang, cfg=cfg, items_by_id=items_by_id, plate_fn=_plate, icon_fn=_icon, **shell),
        )
        for g in GUIDES_BY_LANG[lang]:
            _write(
                dist_dir / lang / "guides" / g["slug"] / "index.html",
                render_guide_detail(lang=lang, guide=g, items_by_id=items_by_id, cfg=cfg, card_fn=_product_card,
                                    icon_fn=_icon, **shell),
            )

    # Head-to-head VS battles (index + one page per rival pair, per language)
    ui = SimpleNamespace(
        head=_head, legal=_legal_strip, header=_site_header, footer=_site_footer, icon=_icon, plate=_plate,
        anchor=_anchor_strip, live=_live_line, profile=_profile, specs=_specs_for_lang, spec_label=_spec_label,
        cat_label=_cat_label, slug=product_slug, og_image=_og_image,
        tool_strip=lambda kind, lang, href: _tool_strip(kind, lang, href, _icon),
    )
    for lang in ("ko", "en"):
        _write(dist_dir / lang / "vs" / "index.html",
               render_vs_index(lang=lang, pairs=pairs, items_by_id=items_by_id, cfg=cfg, ui=ui))
        for pair in pairs:
            _write(dist_dir / lang / "vs" / pair["slug"] / "index.html",
                   render_vs_detail(lang=lang, pair=pair, pairs=pairs, items_by_id=items_by_id, cfg=cfg, ui=ui))

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
    indexnow_key = (cfg.get("site", {}).get("indexnow_key") or "").strip()
    if indexnow_key:
        _write(dist_dir / f"{indexnow_key}.txt", indexnow_key)
    _write(dist_dir / ".nojekyll", "")

    n_guide_pages = sum(1 + len(GUIDES_BY_LANG[lang]) for lang in ("ko", "en"))
    n_vs_pages = 2 * (1 + len(pairs))
    return {
        "approved_products_rendered": len(approved_items),
        "guides_rendered": n_guide_pages,
        "tools_rendered": 4,
        "vs_rendered": n_vs_pages,
        "live_offer_models": len((live_offers or {}).get("offers", {})),
        "total_html_pages": sum(1 for _ in dist_dir.rglob("index.html")),
        "sitemap_urls": len(site_url_paths(approved_items)),
        "output_dir": str(dist_dir),
    }
