"""Zero-dependency static site generator for Korean (Coupang vs Ali) & Global (Amazon vs Ali) hubs.

URL map (directory-index URLs, never linked with `.html`):
  /                 -> dist/index.html             (region gateway)
  /ko/              -> dist/ko/index.html          (Coupang vs AliExpress hub)
  /en/              -> dist/en/index.html          (Amazon vs AliExpress hub)
  /ko/p/<slug>/     -> dist/ko/p/<slug>/index.html (Korean detail)
  /en/p/<slug>/     -> dist/en/p/<slug>/index.html (English detail)
  /policy/          -> dist/policy/index.html      (privacy & affiliate disclosure)
"""

from __future__ import annotations

import html
import re
import shutil
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
    "table": '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><path d="M3.5 9.5h17M3.5 14.5h17M9 9.5v10"/>',
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
.num, .price, .kpi-value, .ledger td.n { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
.i { flex: none; vertical-align: -0.15em; }
.wrap { max-width: 1200px; margin: 0 auto; padding: 0 22px; }
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

/* ---------- Hero + KPI ledger ---------- */
.hero { padding: 44px 0 26px; }
.hero h1 { font-size: clamp(1.9rem, 1.15rem + 2.6vw, 3rem); line-height: 1.12; letter-spacing: -0.035em; font-weight: 780; text-wrap: balance; max-width: 18ch; }
.hero .dek { margin-top: 14px; color: var(--ink-2); font-size: 1.04rem; max-width: 62ch; text-wrap: pretty; }
.hero .dek strong { color: var(--ink); font-weight: 650; }
.stamp { margin-top: 16px; color: var(--muted); font-size: 13px; display: flex; gap: 14px; flex-wrap: wrap; }
.kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); margin-bottom: 30px; }
.kpi { padding: 18px 20px 17px; border-left: 1px solid var(--line); min-width: 0; }
.kpi:first-child { border-left: 0; }
.kpi-label { font-size: 12.5px; color: var(--muted); font-weight: 600; }
.kpi-value { margin-top: 4px; font-size: 1.5rem; font-weight: 760; letter-spacing: -0.025em; line-height: 1.25; }
.kpi-value small { font-size: 0.95rem; font-weight: 650; margin-left: 1px; }
.kpi-value a { text-decoration: none; }
.kpi-value a:hover { text-decoration: underline; }
.kpi-sub { margin-top: 2px; font-size: 13px; color: var(--ink-2); }
.kpi-sub b { color: var(--save-ink); font-weight: 700; }
.gk { display: inline-flex; align-items: center; gap: 7px; margin-top: 7px; font-size: 13.5px; font-weight: 650; color: var(--save-ink); background: var(--save-bg); border-radius: 8px; padding: 5px 10px 5px 8px; line-height: 1.35; }
.gk .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--save); box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.18); flex: none; }

/* ---------- Toolbar ---------- */
.toolbar { position: sticky; top: 62px; z-index: 10; background: rgba(246, 247, 249, 0.94); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); padding: 12px 0 12px; margin: 0 -22px; padding-left: 22px; padding-right: 22px; border-bottom: 1px solid transparent; }
.toolbar-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.search { position: relative; flex: 1 1 280px; }
.search .i { position: absolute; left: 13px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.search input { width: 100%; height: 42px; border: 1px solid var(--line-2); border-radius: 11px; background: var(--surface); padding: 0 44px 0 38px; font-size: 15px; transition: border-color 0.2s, box-shadow 0.2s; }
.search input::placeholder { color: #6B7280; }
.search input:focus { outline: none; border-color: var(--ink); box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.08); }
.search kbd { position: absolute; right: 11px; top: 50%; transform: translateY(-50%); font: 600 11px/1 inherit; color: var(--muted); border: 1px solid var(--line-2); border-radius: 5px; padding: 3px 6px; background: var(--sunk); }
.seg { display: inline-flex; background: var(--surface); border: 1px solid var(--line-2); border-radius: 11px; padding: 3px; gap: 2px; height: 42px; }
.seg button { display: inline-flex; align-items: center; gap: 6px; border: 0; background: transparent; padding: 0 12px; border-radius: 8px; font-size: 13.5px; font-weight: 600; color: var(--ink-2); cursor: pointer; white-space: nowrap; transition: background 0.2s var(--ease), color 0.2s; }
.seg button:hover { color: var(--ink); background: var(--sunk); }
.seg button[aria-pressed="true"] { background: var(--ink); color: #fff; }
.seg-label { font-size: 12.5px; color: var(--muted); font-weight: 600; margin-right: 2px; }
.cats { display: flex; gap: 6px; margin-top: 10px; overflow-x: auto; scrollbar-width: none; padding-bottom: 2px; }
.cats::-webkit-scrollbar { display: none; }
.cat { flex: none; display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--line-2); background: var(--surface); border-radius: 999px; padding: 5px 12px; font-size: 13.5px; font-weight: 600; color: var(--ink-2); cursor: pointer; transition: border-color 0.2s, background 0.2s; }
.cat:hover { border-color: var(--ink); color: var(--ink); }
.cat .num { font-size: 12px; color: var(--muted); font-weight: 600; }
.cat[aria-pressed="true"] { background: var(--ink); border-color: var(--ink); color: #fff; }
.cat[aria-pressed="true"] .num { color: #C9CED6; }
.cat:disabled { opacity: 0.45; cursor: default; border-color: var(--line); color: var(--muted); }
.result-line { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin: 16px 0 12px; font-size: 13.5px; color: var(--muted); }
.result-line strong { color: var(--ink); }

/* ---------- Deal cards ---------- */
.deal-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.deal { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); padding: 20px 20px 16px; display: flex; flex-direction: column; gap: 14px; transition: box-shadow 0.35s var(--ease), border-color 0.35s var(--ease); }
.deal:hover { box-shadow: var(--shadow-hi); border-color: var(--line-2); }
.deal-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.tag { flex: none; font-size: 12.5px; font-weight: 600; color: var(--ink-2); background: var(--sunk); border-radius: 6px; padding: 3px 8px; white-space: nowrap; }
.pick { display: inline-flex; align-items: center; font-size: 12.5px; font-weight: 700; border-radius: 7px; padding: 4px 9px; line-height: 1.4; text-align: right; }
.pick.is-ali { color: var(--save-ink); background: var(--save-bg); }
.pick.is-local { color: var(--local); background: var(--local-bg); }
.deal-title { font-size: 1.14rem; line-height: 1.38; letter-spacing: -0.02em; font-weight: 720; text-wrap: balance; }
.deal-title a { text-decoration: none; }
.deal-title a:hover { text-decoration: underline; }
.deal-sum { margin-top: 6px; color: var(--ink-2); font-size: 14.5px; line-height: 1.6; }
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
.store::before { content: ""; width: 8px; height: 8px; border-radius: 2px; background: var(--c, var(--ink)); }
.store.coupang { --c: var(--coupang); }
.store.amazon { --c: var(--amazon); }
.store.ali { --c: var(--ali); }
.perk { font-size: 12px; color: var(--muted); }
.price { font-size: 1.42rem; font-weight: 780; letter-spacing: -0.025em; line-height: 1.25; margin-top: 3px; }
.price small { font-size: 0.85rem; font-weight: 650; margin-left: 1px; }
.side-meta { font-size: 12.5px; color: var(--muted); }
.win-tag { font-size: 11px; font-weight: 750; color: #fff; background: var(--save); border-radius: 4px; padding: 0 5px; line-height: 1.6; }
.customs { align-self: flex-start; margin-top: 5px; font-size: 12px; font-weight: 650; color: var(--warn-ink); background: var(--warn-bg); border-radius: 6px; padding: 2px 7px; }

.callout { display: grid; gap: 0; border-top: 1px solid var(--line); }
.callout > div { display: grid; grid-template-columns: 5.6em 1fr; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--line); font-size: 14px; line-height: 1.55; }
.callout dt { font-weight: 700; color: var(--ink); white-space: nowrap; }
.callout dd { color: var(--ink-2); }
.en .callout > div { grid-template-columns: 6.6em 1fr; }

.actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px; padding: 10px 14px; border-radius: 10px; font-weight: 700; font-size: 14.5px; text-decoration: none; color: #fff; transition: filter 0.2s, transform 0.2s var(--ease); text-align: center; line-height: 1.3; }
.btn:hover { filter: brightness(0.93); }
.btn:active { transform: translateY(1px); }
.btn-coupang { background: var(--coupang); }
.btn-amazon { background: var(--amazon); color: #111827; }
.btn-ali { background: var(--ali); }
.more { display: inline-flex; align-items: center; gap: 6px; align-self: flex-start; font-size: 14px; font-weight: 650; color: var(--ink); text-decoration: none; padding: 2px 0; }
.more:hover { text-decoration: underline; }
.more .i { transition: transform 0.25s var(--ease); }
.more:hover .i { transform: translateX(3px); }

/* ---------- Dense ledger table ---------- */
.ledger-wrap { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow-x: auto; scrollbar-width: thin; scrollbar-color: var(--line-2) transparent; }
.ledger { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; min-width: 980px; }
.ledger th { position: sticky; top: 0; text-align: left; font-size: 12px; font-weight: 650; color: var(--muted); background: var(--sunk); padding: 10px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
.ledger td { padding: 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
.ledger tr:last-child td { border-bottom: 0; }
.ledger tbody tr:hover td { background: #FAFBFC; }
.ledger th.n, .ledger td.n { text-align: right; white-space: nowrap; }
.ledger td.n { font-weight: 650; }
.ledger td.n.win { color: var(--save-ink); font-weight: 780; }
.ledger td.n.win::before { content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--save); margin-right: 6px; vertical-align: 0.15em; }
.ledger .model { position: sticky; left: 0; background: inherit; min-width: 230px; max-width: 290px; }
.ledger tbody .model { background: var(--surface); }
.ledger thead .model { background: var(--sunk); z-index: 1; }
.ledger .model a { font-weight: 700; text-decoration: none; line-height: 1.4; display: block; }
.ledger .model a:hover { text-decoration: underline; }
.ledger .model span { display: block; font-size: 12.5px; color: var(--muted); margin-top: 2px; }
.ledger .chips li { font-size: 12px; }
.ledger .spread { font-size: 12.5px; color: var(--muted); font-weight: 550; display: block; }
.ledger .pick { font-size: 12px; white-space: nowrap; }
.ledger .buy { white-space: nowrap; }
.ledger td.n .customs { display: block; width: fit-content; margin: 6px 0 0 auto; font-weight: 650; }
.ledger td.n.win .customs::before { content: none; }
.ledger .buy a { display: inline-flex; align-items: center; gap: 3px; font-size: 13px; font-weight: 700; text-decoration: none; padding: 5px 9px; border-radius: 7px; color: #fff; }
.ledger .buy a + a { margin-left: 4px; }
.hub[data-view="cards"] .ledger-wrap { display: none; }
.hub[data-view="table"] .deal-grid { display: none; }

.empty { background: var(--surface); border: 1px dashed var(--line-2); border-radius: var(--radius); padding: 40px 20px; text-align: center; color: var(--ink-2); }
.empty strong { display: block; font-size: 1.05rem; color: var(--ink); margin-bottom: 4px; }
.empty button { margin-top: 14px; border: 1px solid var(--ink); background: var(--ink); color: #fff; border-radius: 9px; padding: 8px 14px; font-weight: 650; cursor: pointer; }

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
@media (max-width: 1020px) {
  .detail { grid-template-columns: minmax(0, 1fr); grid-template-areas: "intro" "aside" "body"; }
  .d-aside { position: static; margin-top: 22px; }
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .kpi:nth-child(3) { border-left: 0; }
  .kpi:nth-child(n+3) { border-top: 1px solid var(--line); }
  .rel-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 860px) {
  .deal-grid, .regions { grid-template-columns: 1fr; }
  .head-nav .lbl-long { display: none; }
}
@media (max-width: 620px) {
  body { font-size: 15px; }
  .wrap { padding: 0 16px; }
  .toolbar { margin: 0 -16px; padding-left: 16px; padding-right: 16px; }
  .site-head .wrap { height: 56px; }
  .toolbar { top: 56px; }
  .brand-name { display: none; }
  .head-nav { gap: 0; font-size: 13.5px; }
  .head-nav a { padding: 7px 8px; }
  .head-nav .lbl-tg { display: none; }
  .hero { padding: 30px 0 20px; }
  .kpi { padding: 14px 14px 13px; }
  .kpi-value { font-size: 1.22rem; }
  .seg-label { display: none; }
  .seg { flex: 1 1 auto; }
  .seg button { flex: 1; justify-content: center; padding: 0 8px; font-size: 13px; }
  .view-seg { flex: none; }
  .view-seg .lbl { display: none; }
  .search kbd { display: none; }
  .deal { padding: 16px 16px 14px; }
  .deal-top { flex-direction: column; align-items: flex-start; }
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
  const grid = hub.querySelector('[data-grid]');
  const tbody = hub.querySelector('[data-rows]');
  const cards = Array.from(grid.children);
  const rows = Array.from(tbody.children);
  const search = hub.querySelector('[data-search]');
  const catBtns = Array.from(hub.querySelectorAll('[data-cat]'));
  const sortBtns = Array.from(hub.querySelectorAll('[data-sort]'));
  const viewBtns = Array.from(hub.querySelectorAll('[data-view-btn]'));
  const countEl = hub.querySelector('[data-count]');
  const empty = hub.querySelector('[data-empty]');
  const tpl = countEl.dataset.tpl;
  const params = new URLSearchParams(location.search);
  let savedView = null;
  try { savedView = localStorage.getItem('gch-view'); } catch (e) {}
  const state = {
    cat: catBtns.some(b => b.dataset.cat === params.get('cat')) ? params.get('cat') : 'all',
    q: params.get('q') || '',
    sort: 'save',
    view: (params.get('view') || savedView) === 'table' ? 'table' : 'cards',
  };
  search.value = state.q;
  const norm = s => s.normalize('NFKC').toLowerCase();
  const matchesQuery = (el, terms) => terms.every(t => el.dataset.q.includes(t));

  function syncUrl() {
    const p = new URLSearchParams();
    if (state.cat !== 'all') p.set('cat', state.cat);
    if (state.q.trim()) p.set('q', state.q.trim());
    const qs = p.toString();
    history.replaceState(null, '', qs ? '?' + qs : location.pathname);
  }

  function apply() {
    const terms = norm(state.q).split(/\s+/).filter(Boolean);
    const key = state.sort;
    const cmp = (a, b) => key === 'price'
      ? parseFloat(a.dataset.price) - parseFloat(b.dataset.price)
      : parseFloat(b.dataset[key]) - parseFloat(a.dataset[key]);
    let shown = 0;
    [[cards, grid], [rows, tbody]].forEach(([list, parent], idx) => {
      list.slice().sort(cmp).forEach(el => {
        const ok = (state.cat === 'all' || el.dataset.c === state.cat) && matchesQuery(el, terms);
        el.hidden = !ok;
        if (ok && idx === 0) shown++;
        parent.appendChild(el);
      });
    });
    catBtns.forEach(btn => {
      const c = btn.dataset.cat;
      const n = cards.filter(el => (c === 'all' || el.dataset.c === c) && matchesQuery(el, terms)).length;
      btn.querySelector('.num').textContent = n;
      btn.setAttribute('aria-pressed', String(c === state.cat));
      btn.disabled = n === 0 && c !== state.cat;
    });
    sortBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.sort === state.sort)));
    viewBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.viewBtn === state.view)));
    hub.dataset.view = state.view;
    countEl.innerHTML = tpl.replace('{n}', '<strong>' + shown + '</strong>').replace('{t}', cards.length);
    empty.hidden = shown > 0;
  }

  search.addEventListener('input', () => { state.q = search.value; apply(); syncUrl(); });
  catBtns.forEach(b => b.addEventListener('click', () => { state.cat = b.dataset.cat; apply(); syncUrl(); }));
  sortBtns.forEach(b => b.addEventListener('click', () => { state.sort = b.dataset.sort; apply(); }));
  viewBtns.forEach(b => b.addEventListener('click', () => {
    state.view = b.dataset.viewBtn;
    try { localStorage.setItem('gch-view', state.view); } catch (e) {}
    apply();
  }));
  hub.querySelectorAll('[data-reset]').forEach(b => b.addEventListener('click', () => {
    state.q = ''; state.cat = 'all'; search.value = ''; apply(); syncUrl(); search.focus();
  }));
  document.addEventListener('keydown', e => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if (e.key === '/' && !typing) { e.preventDefault(); search.focus(); }
    else if (e.key === 'Escape' && document.activeElement === search && search.value) {
      search.value = ''; state.q = ''; apply(); syncUrl();
    }
  });
  apply();
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
        "direct_pick": ali_wins and pct >= DIRECT_PICK_MIN_PCT,
        "customs": lang == "ko" and float(p["ali_usd"]) > KR_CUSTOMS_LIMIT_USD,
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
        "customs": f"⚠️ ${KR_CUSTOMS_LIMIT_USD} 초과 관부가세 유의",
        "verdict": "💡 결론",
        "con": "⚠️ 단점 체크",
        "btn_dom": "쿠팡 최저가 확인",
        "btn_ali": "알리 직구가 확인",
        "more": "상세 스펙·장단점 더보기",
        "switch": "🌐 Global Hub",
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
        "verdict": "💡 Verdict",
        "con": "⚠️ Caveat",
        "btn_dom": "Amazon",
        "btn_ali": "AliExpress",
        "more": "Full specs, pros & caveats",
        "switch": "🇰🇷 한국어 허브",
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
            return f'<span class="pick is-ali">🌏 알리 직구 추천 · {_money(d["diff"], lang, False)} ({d["pct"]:.0f}%) 절약</span>'
        return '<span class="pick is-local">🚀 쿠팡 정발 추천 · 빠른 배송·AS 유리</span>'
    if d["direct_pick"]:
        return f'<span class="pick is-ali">🌏 AliExpress pick · Save {_money(d["diff"], lang)} ({d["pct"]:.0f}%)</span>'
    return '<span class="pick is-local">🚀 Amazon pick · Fast Prime &amp; easy returns</span>'


def _pick_short(d: dict, lang: str) -> str:
    if d["direct_pick"]:
        return '<span class="pick is-ali">🌏 ' + ("알리 직구" if lang == "ko" else "AliExpress") + "</span>"
    return '<span class="pick is-local">🚀 ' + ("쿠팡 정발" if lang == "ko" else "Amazon") + "</span>"


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
    parts = [it["brand"], it["model"], it[lang]["title"], it["ko"]["title"], it["en"]["title"],
             _cat_label(it["category"], lang), *map(str, it.get("specs", {}).values())]
    return _esc(" ".join(parts).lower())


def _data_attrs(it: dict, d: dict, lang: str) -> str:
    return (
        f'data-c="{_esc(it["category"])}" data-save="{d["diff"]:.2f}" data-off="{d["off"]:.1f}" '
        f'data-price="{d["best"]:.2f}" data-q="{_search_blob(it, lang)}"'
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
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(description)}">
  <meta name="theme-color" content="#FFFFFF">
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
# Hub pages (/ko/, /en/)
# --------------------------------------------------------------------------------------


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


def _render_card(it: dict, lang: str) -> str:
    t, d, loc = T[lang], _deal(it, lang), it[lang]
    href = f"p/{product_slug(it['id'])}/"
    con = loc["cons"][0] if loc.get("cons") else ""
    return f"""
    <article class="deal" {_data_attrs(it, d, lang)}>
      <div class="deal-top">
        <span class="tag">{_esc(_cat_label(it['category'], lang))} · {_esc(it['brand'])}</span>
        {_pick_badge(d, lang)}
      </div>
      <div>
        <h2 class="deal-title"><a href="{href}">{_esc(loc['title'])}</a></h2>
        <p class="deal-sum">{_esc(loc['summary'])}</p>
      </div>
      {_chips(it, 4)}
      {_battle(d, lang)}
      <dl class="callout">
        <div><dt>{t['verdict']}</dt><dd>{_esc(loc['verdict'])}</dd></div>
        <div><dt>{t['con']}</dt><dd>{_esc(con)}</dd></div>
      </dl>
      <div class="actions">
        {_ext(d['dom_url'], 'btn btn-' + d['dom_key'], ('쿠팡 최저가 확인' if lang == 'ko' else 'Amazon'))}
        {_ext(d['ali_url'], 'btn btn-ali', ('알리 직구가 확인' if lang == 'ko' else 'AliExpress'))}
      </div>
      <a class="more" href="{href}">{t['more']} {_icon('arrow', 15)}</a>
    </article>"""


def _render_row(it: dict, lang: str) -> str:
    t, d, loc = T[lang], _deal(it, lang), it[lang]
    href = f"p/{product_slug(it['id'])}/"
    customs = f'<span class="customs">{_esc(t["customs"])}</span>' if d["customs"] else ""
    spread = f'{_money(d["diff"], lang, False)}'
    return f"""
        <tr {_data_attrs(it, d, lang)}>
          <td class="model"><a href="{href}">{_esc(loc['title'])}</a><span>{_esc(_cat_label(it['category'], lang))} · {_esc(it['brand'])}</span></td>
          <td>{_chips(it, 2)}</td>
          <td class="n{' win' if not d['ali_wins'] else ''}">{_money(d['dom'], lang, False)}</td>
          <td class="n{' win' if d['ali_wins'] else ''}">{_money(d['ali'], lang, False)}{customs}</td>
          <td class="n">{spread}<span class="spread">{d['pct']:.1f}% · {t['msrp']} −{d['off']:.0f}%</span></td>
          <td>{_pick_short(d, lang)}</td>
          <td class="buy"><a class="btn-{d['dom_key']}" style="background:var(--{d['dom_key']});{'color:#111827;' if d['dom_key'] == 'amazon' else ''}" href="{_esc(d['dom_url'])}" target="_blank" rel="nofollow sponsored noopener">{t['dom_store']} {_icon('out', 13)}</a><a style="background:var(--ali)" href="{_esc(d['ali_url'])}" target="_blank" rel="nofollow sponsored noopener">{'알리' if lang == 'ko' else 'Ali'} {_icon('out', 13)}</a></td>
        </tr>"""


def _render_hub(items: list[dict], cfg: dict, lang: str) -> str:
    t = T[lang]
    brand = cfg["site"]["brand_name"]
    up = "../"
    s = _region_summary(items, lang)
    latest = max((it.get("updated_at", "") for it in items), default="")
    ordered = [it for it, _ in s["ranked"]]

    counts: dict[str, int] = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    cat_btns = [f'<button type="button" class="cat" data-cat="all" aria-pressed="true">{_esc(_cat_label("all", lang))} <span class="num">{len(items)}</span></button>']
    for c in sorted(counts, key=lambda c: (-counts[c], _cat_label(c, lang))):
        cat_btns.append(
            f'<button type="button" class="cat" data-cat="{_esc(c)}" aria-pressed="false">{_esc(_cat_label(c, lang))} <span class="num">{counts[c]}</span></button>'
        )

    if s["top"]:
        top_href = f'p/{product_slug(s["top"]["id"])}/'
        top_name = _esc(_short_name(s["top"]))
        top_gap = _money(s["top_deal"]["diff"], lang, False)
    else:
        top_href, top_name, top_gap = "#deals", "—", ""

    if lang == "ko":
        title = f"{brand} KR — 데스크/IT 기어 쿠팡 vs 알리 직구 가격 비교"
        desc = "검수를 통과한 IT·데스크 기어의 쿠팡 가격과 알리익스프레스 직구가, 실사용 단점을 한눈에 비교합니다."
        h1 = "내일 받을까, 직구로 아낄까?"
        dek = "같은 모델의 <strong>쿠팡 가격과 알리 직구가</strong>를 나란히 놓고, 사기 전에 알아야 할 단점까지 한 장에 정리했습니다."
        stamp = f'<span>가격 기준일 <b class="num">{_esc(latest)}</b></span><span>쿠팡 · 알리익스프레스 동일 모델 비교</span>'
        kpis = f"""
      <div class="kpi"><div class="kpi-label">검수 통과 기어</div><div class="kpi-value num">{s['count']}<small>종</small></div><div class="kpi-sub">{len(counts)}개 카테고리</div></div>
      <div class="kpi"><div class="kpi-label">평균 직구 절약률</div><div class="kpi-value num">{s['avg']:.1f}<small>%</small></div><div class="kpi-sub">쿠팡가 대비 알리 직구가</div></div>
      <div class="kpi"><div class="kpi-label">최대 절약 픽</div><div class="kpi-value"><a href="{top_href}">{top_name}</a></div><div class="kpi-sub"><b class="num">{top_gap}</b> 차이</div></div>
      <div class="kpi"><div class="kpi-label">게이트키퍼 상태</div><div class="gk"><span class="dot"></span>자동 오매칭·가품 필터 작동 중</div><div class="kpi-sub" style="margin-top:6px">액세서리 단품·이상 저가 매물 차단</div></div>"""
        ph = "브랜드, 모델, 스펙으로 검색 (예: 100W, 기계식)"
        sorts = [("save", "절약 금액 큰순"), ("off", "할인율 높은순"), ("price", "낮은 가격순")]
        views = [("cards", "카드 비교 뷰"), ("table", "한눈에 가격·스펙 표 뷰")]
        sort_lbl, view_lbl = "정렬", "보기"
        count_tpl = "{n}개 표시 · 전체 {t}개"
        sort_note = "절약 금액 = 두 판매처 가격 차이"
        head_cols = ["모델", "핵심 스펙", "쿠팡", "알리 직구", "가격 차이", "구매 판정", "바로 구매"]
        empty_t, empty_d, reset = "조건에 맞는 기어가 없습니다", "검색어를 줄이거나 다른 카테고리를 선택해 보세요.", "필터 초기화"
        search_lbl = "기어 검색"
    else:
        title = f"{brand} — Desk & Tech Gear Price Comparison (Amazon vs AliExpress)"
        desc = "Side-by-side Amazon vs AliExpress prices on vetted GaN chargers, keyboards, mini PCs, and desk gear, with honest drawbacks."
        h1 = "Fast Prime delivery, or direct-import savings?"
        dek = "We track identical desk &amp; USB-C models on <strong>Amazon and AliExpress</strong>, side by side, with the real-world drawbacks you should know before you buy."
        stamp = f'<span>Prices checked <b class="num">{_esc(latest)}</b></span><span>Same model, two storefronts</span>'
        kpis = f"""
      <div class="kpi"><div class="kpi-label">Vetted models</div><div class="kpi-value num">{s['count']}</div><div class="kpi-sub">across {len(counts)} categories</div></div>
      <div class="kpi"><div class="kpi-label">Avg. AliExpress savings</div><div class="kpi-value num">{s['avg']:.1f}<small>%</small></div><div class="kpi-sub">vs. the Amazon price</div></div>
      <div class="kpi"><div class="kpi-label">Biggest saving</div><div class="kpi-value"><a href="{top_href}">{top_name}</a></div><div class="kpi-sub"><b class="num">{top_gap}</b> gap</div></div>
      <div class="kpi"><div class="kpi-label">Gatekeeper</div><div class="gk"><span class="dot"></span>Mismatch &amp; fake-listing filter active</div><div class="kpi-sub" style="margin-top:6px">Accessory-only &amp; too-cheap listings blocked</div></div>"""
        ph = "Search brand, model, or spec (e.g. 100W, QMK)"
        sorts = [("save", "Biggest savings"), ("off", "Highest % off"), ("price", "Lowest price")]
        views = [("cards", "Cards"), ("table", "Price &amp; spec table")]
        sort_lbl, view_lbl = "Sort", "View"
        count_tpl = "Showing {n} of {t}"
        sort_note = "Savings = gap between the two stores"
        head_cols = ["Model", "Key specs", "Amazon", "AliExpress", "Spread", "Verdict", "Buy"]
        empty_t, empty_d, reset = "No gear matches", "Try a shorter search or another category.", "Reset filters"
        search_lbl = "Search gear"

    sort_html = "".join(
        f'<button type="button" data-sort="{k}" aria-pressed="{"true" if k == "save" else "false"}">{v}</button>' for k, v in sorts
    )
    view_html = "".join(
        f'<button type="button" data-view-btn="{k}" aria-pressed="{"true" if k == "cards" else "false"}" title="{v}">{_icon(k, 16)}<span class="lbl">{v}</span></button>'
        for k, v in views
    )
    th = "".join(
        f'<th scope="col" class="{"model" if i == 0 else ("n" if i in (2, 3, 4) else "")}">{c}</th>' for i, c in enumerate(head_cols)
    )

    body = f"""
<body class="{lang}">
  {_legal_strip(lang)}
  {_site_header(lang, up, cfg, f"{up}{'en' if lang == 'ko' else 'ko'}/")}
  <main class="wrap hub" data-hub data-view="cards">
    <section class="hero">
      <h1>{h1}</h1>
      <p class="dek">{dek}</p>
      <p class="stamp">{stamp}</p>
    </section>
    <section class="kpis" aria-label="{'요약 지표' if lang == 'ko' else 'Summary'}">{kpis}
    </section>

    <div class="toolbar" id="deals">
      <div class="toolbar-row">
        <label class="search"><span class="sr-only">{search_lbl}</span>{_icon('search', 17)}<input type="search" data-search placeholder="{_esc(ph)}" autocomplete="off" enterkeyhint="search"><kbd>/</kbd></label>
        <div class="seg" role="group" aria-label="{sort_lbl}"><span class="seg-label" style="align-self:center;padding-left:8px">{sort_lbl}</span>{sort_html}</div>
        <div class="seg view-seg" role="group" aria-label="{view_lbl}">{view_html}</div>
      </div>
      <div class="cats" role="group" aria-label="{'카테고리' if lang == 'ko' else 'Categories'}">{''.join(cat_btns)}</div>
    </div>

    <div class="result-line"><span data-count data-tpl="{_esc(count_tpl)}" aria-live="polite">{count_tpl.replace('{n}', f'<strong>{len(items)}</strong>').replace('{t}', str(len(items)))}</span><span>{sort_note}</span></div>

    <div class="deal-grid" data-grid>{''.join(_render_card(it, lang) for it in ordered)}
    </div>
    <div class="ledger-wrap">
      <table class="ledger">
        <thead><tr>{th}</tr></thead>
        <tbody data-rows>{''.join(_render_row(it, lang) for it in ordered)}
        </tbody>
      </table>
    </div>
    <div class="empty" data-empty hidden><strong>{empty_t}</strong>{empty_d}<br><button type="button" data-reset>{reset}</button></div>
  </main>
  {_site_footer(lang, up, cfg)}
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    head = _head(lang=lang, title=title, description=desc, up=up, cfg=cfg, path=f"/{lang}/",
                 alternates={"ko": "/ko/", "en": "/en/", "x-default": "/"})
    return head + body


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
        <li><a href="../../?cat={_esc(cat)}">{_esc(_cat_label(cat, lang))}</a></li>
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
    <section class="gate-hero">
      <h1>Same gear, two routes. Know which one is worth it.</h1>
      <p>We match identical desk and USB-C models across fast domestic stores and AliExpress direct import, then filter out accessory-only and fake listings before anything is published.</p>
      <p lang="ko">같은 모델, 두 가지 구매 경로. 빠른 배송과 직구 절약 중 무엇이 이득인지 지역별로 비교하세요.</p>
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
      <p>{brand} is a static site and does not collect personal registration data, passwords, or payment details. When you click outbound retail links (Amazon, AliExpress, Coupang), those merchants may set standard affiliate attribution cookies under their own privacy policies. The hub remembers your preferred card/table view in your browser's local storage only.</p>
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
    """Generate clean-URL static pages for root, /ko/, /en/, product details, policy, and sitemap."""
    _clean_dist(dist_dir)

    _write(dist_dir / "assets" / "style.css", SHARED_CSS.strip() + "\n")
    _write(dist_dir / "assets" / "app.js", APP_JS.strip() + "\n")
    _write(dist_dir / "index.html", _render_root_gateway(cfg, approved_items))
    _write(dist_dir / "policy" / "index.html", _render_policy_page(cfg))
    _write(dist_dir / "ko" / "index.html", _render_ko_index(approved_items, cfg))
    _write(dist_dir / "en" / "index.html", _render_en_index(approved_items, cfg))

    for item in approved_items:
        slug = product_slug(item["id"])
        _write(dist_dir / "ko" / "p" / slug / "index.html", _render_detail_page(item, "ko", cfg, approved_items))
        _write(dist_dir / "en" / "p" / slug / "index.html", _render_detail_page(item, "en", cfg, approved_items))

    _write(dist_dir / "sitemap.xml", _render_sitemap(approved_items, cfg))
    _write(dist_dir / ".nojekyll", "")

    return {
        "approved_products_rendered": len(approved_items),
        "total_html_pages": 4 + (len(approved_items) * 2),
        "output_dir": str(dist_dir),
    }
