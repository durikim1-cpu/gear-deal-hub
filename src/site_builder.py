"""Zero-dependency static site generator for Korean (Coupang vs Ali) & Global (Amazon vs Ali) hubs."""

from __future__ import annotations

import html
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

SHARED_CSS = """
:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-hover: #263449;
  --border: #334155;
  --text: #f8fafc;
  --muted: #94a3b8;
  --accent: #38bdf8;
  --coupang: #ef4444;
  --amazon: #f59e0b;
  --ali: #f97316;
  --good: #22c55e;
  --warn: #eab308;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}
a { color: var(--accent); text-decoration: none; }
.container { max-width: 1120px; margin: 0 auto; padding: 24px 18px 64px; }
.disclosure-bar {
  background: #172554;
  border-bottom: 1px solid #1e40af;
  color: #dbeafe;
  font-size: 0.84rem;
  padding: 10px 18px;
  text-align: center;
}
header.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 20px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}
.brand { font-size: 1.35rem; font-weight: 800; color: var(--text); letter-spacing: -0.02em; }
.nav-links { display: flex; gap: 14px; font-size: 0.92rem; align-items: center; }
.pill-link {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--text);
  background: var(--surface);
}
.hero { margin-bottom: 26px; }
.hero h1 { font-size: 1.85rem; margin-bottom: 8px; letter-spacing: -0.02em; }
.hero p { color: var(--muted); font-size: 0.98rem; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 22px; }
.filter-btn {
  cursor: pointer;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--muted);
  font-size: 0.86rem;
  font-weight: 600;
}
.filter-btn.active, .filter-btn:hover {
  background: var(--accent);
  color: #0f172a;
  border-color: var(--accent);
}
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 20px; }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 14px;
}
.badge-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; }
.cat-badge {
  background: #0f172a;
  color: var(--accent);
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
}
.save-badge { color: var(--good); font-weight: 700; }
.card h2 { font-size: 1.08rem; line-height: 1.4; }
.card h2 a { color: var(--text); }
.card h2 a:hover { color: var(--accent); }
.summary { color: var(--muted); font-size: 0.88rem; }
.price-compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  background: #0f172a;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
}
.price-box { display: flex; flex-direction: column; gap: 3px; }
.price-label { font-size: 0.76rem; color: var(--muted); }
.price-val { font-size: 1.08rem; font-weight: 800; }
.con-note {
  background: rgba(234, 179, 8, 0.1);
  border-left: 3px solid var(--warn);
  padding: 8px 10px;
  font-size: 0.82rem;
  color: #fef08a;
  border-radius: 4px;
}
.cta-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.btn {
  display: inline-block;
  text-align: center;
  padding: 10px 12px;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.86rem;
  color: #fff;
}
.btn-coupang { background: var(--coupang); }
.btn-amazon { background: var(--amazon); color: #111827; }
.btn-ali { background: var(--ali); }
.btn:hover { opacity: 0.92; }
.spec-table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.92rem; }
.spec-table th, .spec-table td {
  border: 1px solid var(--border);
  padding: 10px 12px;
  text-align: left;
}
.spec-table th { background: #0f172a; color: var(--muted); width: 34%; }
.detail-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 26px;
}
.pros-cons { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 18px 0; }
@media (max-width: 640px) { .pros-cons { grid-template-columns: 1fr; } }
.list-panel { background: #0f172a; border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
.list-panel h3 { font-size: 0.95rem; margin-bottom: 8px; }
.list-panel ul { padding-left: 18px; font-size: 0.9rem; color: #cbd5e1; }
footer {
  margin-top: 48px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  font-size: 0.82rem;
  color: var(--muted);
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
"""


def _esc(val: object) -> str:
    return html.escape(str(val))


def _render_ko_index(items: list[dict], cfg: dict) -> str:
    brand = _esc(cfg["site"]["brand_name"])
    tg_url = _esc(cfg["site"]["telegram_channel_ko"])
    cats_present = ["all"] + sorted({it["category"] for it in items})

    filter_btns = "\n".join(
        f'<button class="filter-btn{" active" if c == "all" else ""}" data-cat="{_esc(c)}">'
        f'{_esc(CATEGORY_LABELS_KO.get(c, c))}</button>'
        for c in cats_present
    )

    cards = []
    for it in items:
        p = it["prices"]
        m = it["metrics"]
        links = it["affiliate_links"]
        cheaper = "알리 직구" if m["kr_cheaper"] == "aliexpress" else "쿠팡"
        cards.append(
            f"""
            <article class="card" data-cat="{_esc(it['category'])}">
              <div>
                <div class="badge-row">
                  <span class="cat-badge">{_esc(CATEGORY_LABELS_KO.get(it['category'], it['category']))} · {_esc(it['brand'])}</span>
                  <span class="save-badge">{cheaper} {m['kr_diff_krw']:,}원 절약</span>
                </div>
                <h2 style="margin-top:10px;"><a href="products/{_esc(it['id'])}.html">{_esc(it['ko']['title'])}</a></h2>
                <p class="summary" style="margin-top:6px;">{_esc(it['ko']['summary'])}</p>
              </div>
              <div>
                <div class="price-compare">
                  <div class="price-box">
                    <span class="price-label">쿠팡 로켓/국내</span>
                    <span class="price-val">{int(p['coupang_krw']):,}원</span>
                  </div>
                  <div class="price-box">
                    <span class="price-label">알리익스프레스 직구</span>
                    <span class="price-val">{int(p['ali_krw']):,}원</span>
                  </div>
                </div>
                <div class="con-note" style="margin-top:10px;">
                  ⚠️ 단점 체크: {_esc(it['ko']['cons'][0])}
                </div>
                <div class="cta-row" style="margin-top:12px;">
                  <a class="btn btn-coupang" href="{_esc(links['coupang'])}" target="_blank" rel="nofollow sponsored noopener">쿠팡 최저가 보기</a>
                  <a class="btn btn-ali" href="{_esc(links['aliexpress'])}" target="_blank" rel="nofollow sponsored noopener">알리 직구가 보기</a>
                </div>
              </div>
            </article>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{brand} KR — 데스크/IT 기어 쿠팡 vs 알리 실시간 가성비 비교</title>
  <meta name="description" content="검증된 글로벌 IT·데스크 기어의 쿠팡 로켓배송 가격과 알리익스프레스 직구 최저가, 실사용 단점을 한눈에 비교하세요.">
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
  <div class="disclosure-bar">{_esc(DISCLOSURE_KO)}</div>
  <div class="container">
    <header class="top-nav">
      <a class="brand" href="index.html">⚡ {brand} <span style="font-size:0.85rem;color:#38bdf8;">KR</span></a>
      <nav class="nav-links">
        <a class="pill-link" href="{tg_url}" target="_blank" rel="noopener">📢 텔레그램 핫딜 알림</a>
        <a class="pill-link" href="../en/index.html">🌐 Global (EN)</a>
        <a href="../privacy.html">제휴고지·정책</a>
      </nav>
    </header>
    <section class="hero">
      <h1>내일 바로 받을까, 직구로 아낄까?</h1>
      <p>동일 모델 IT·데스크 주변기기의 <strong>쿠팡 가격 vs 알리 직구 가격</strong>과 실제 구매 전 꼭 알아야 할 단점만 요약했습니다.</p>
    </section>
    <div class="filter-bar">{filter_btns}</div>
    <main class="grid" id="product-grid">
      {"".join(cards)}
    </main>
    <footer>
      <span>© 2026 {brand}. 표기 가격은 수집 시점 기준이며 변동될 수 있습니다.</span>
      <span><a href="../privacy.html">개인정보처리방침 및 대가성 고지</a></span>
    </footer>
  </div>
  <script>
    document.querySelectorAll('.filter-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cat = btn.dataset.cat;
        document.querySelectorAll('#product-grid .card').forEach(card => {{
          card.style.display = (cat === 'all' || card.dataset.cat === cat) ? 'flex' : 'none';
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def _render_en_index(items: list[dict], cfg: dict) -> str:
    brand = _esc(cfg["site"]["brand_name"])
    tg_url = _esc(cfg["site"]["telegram_channel_en"])
    cats_present = ["all"] + sorted({it["category"] for it in items})

    filter_btns = "\n".join(
        f'<button class="filter-btn{" active" if c == "all" else ""}" data-cat="{_esc(c)}">'
        f'{_esc(CATEGORY_LABELS_EN.get(c, c))}</button>'
        for c in cats_present
    )

    cards = []
    for it in items:
        p = it["prices"]
        m = it["metrics"]
        links = it["affiliate_links"]
        cheaper = "AliExpress" if m["en_cheaper"] == "aliexpress" else "Amazon"
        cards.append(
            f"""
            <article class="card" data-cat="{_esc(it['category'])}">
              <div>
                <div class="badge-row">
                  <span class="cat-badge">{_esc(CATEGORY_LABELS_EN.get(it['category'], it['category']))} · {_esc(it['brand'])}</span>
                  <span class="save-badge">Save USD {m['en_diff_usd']:.2f} on {cheaper}</span>
                </div>
                <h2 style="margin-top:10px;"><a href="products/{_esc(it['id'])}.html">{_esc(it['en']['title'])}</a></h2>
                <p class="summary" style="margin-top:6px;">{_esc(it['en']['summary'])}</p>
              </div>
              <div>
                <div class="price-compare">
                  <div class="price-box">
                    <span class="price-label">Amazon (Fast Ship)</span>
                    <span class="price-val">USD {p['amazon_usd']:.2f}</span>
                  </div>
                  <div class="price-box">
                    <span class="price-label">AliExpress Direct</span>
                    <span class="price-val">USD {p['ali_usd']:.2f}</span>
                  </div>
                </div>
                <div class="con-note" style="margin-top:10px;">
                  ⚠️ Caveat: {_esc(it['en']['cons'][0])}
                </div>
                <div class="cta-row" style="margin-top:12px;">
                  <a class="btn btn-amazon" href="{_esc(links['amazon'])}" target="_blank" rel="nofollow sponsored noopener">Check Amazon</a>
                  <a class="btn btn-ali" href="{_esc(links['aliexpress'])}" target="_blank" rel="nofollow sponsored noopener">Check AliExpress</a>
                </div>
              </div>
            </article>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{brand} — Desk & Tech Gear Price Comparison (Amazon vs AliExpress)</title>
  <meta name="description" content="Side-by-side price comparison between Amazon fast shipping and AliExpress direct deals on vetted GaN chargers, keyboards, mini PCs, and desk gear.">
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
  <div class="disclosure-bar">{_esc(DISCLOSURE_EN)}</div>
  <div class="container">
    <header class="top-nav">
      <a class="brand" href="index.html">⚡ {brand} <span style="font-size:0.85rem;color:#38bdf8;">GLOBAL</span></a>
      <nav class="nav-links">
        <a class="pill-link" href="{tg_url}" target="_blank" rel="noopener">📢 Telegram Deal Feed</a>
        <a class="pill-link" href="../ko/index.html">🇰🇷 한국어 (KR)</a>
        <a href="../privacy.html">Privacy & Disclosure</a>
      </nav>
    </header>
    <section class="hero">
      <h1>Fast Prime Shipping vs. Direct Factory Savings</h1>
      <p>We track identical desk &amp; USB-C tech models across <strong>Amazon and AliExpress</strong>—complete with honest real-world drawbacks before you buy.</p>
    </section>
    <div class="filter-bar">{filter_btns}</div>
    <main class="grid" id="product-grid">
      {"".join(cards)}
    </main>
    <footer>
      <span>© 2026 {brand}. { _esc(DISCLOSURE_EN) }</span>
      <span><a href="../privacy.html">Privacy &amp; Affiliate Policy</a></span>
    </footer>
  </div>
  <script>
    document.querySelectorAll('.filter-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cat = btn.dataset.cat;
        document.querySelectorAll('#product-grid .card').forEach(card => {{
          card.style.display = (cat === 'all' || card.dataset.cat === cat) ? 'flex' : 'none';
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def _render_detail_page(it: dict, lang: str, cfg: dict) -> str:
    brand = _esc(cfg["site"]["brand_name"])
    p = it["prices"]
    m = it["metrics"]
    links = it["affiliate_links"]
    spec_rows = "\n".join(
        f"<tr><th>{_esc(k.upper())}</th><td>{_esc(v)}</td></tr>" for k, v in it.get("specs", {}).items()
    )

    if lang == "ko":
        loc = it["ko"]
        pros_li = "".join(f"<li>{_esc(x)}</li>" for x in loc["pros"])
        cons_li = "".join(f"<li>{_esc(x)}</li>" for x in loc["cons"])
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(loc['title'])} — 쿠팡 vs 알리 직구 가격·단점 비교 | {brand}</title>
  <meta name="description" content="{_esc(loc['summary'])}">
  <link rel="stylesheet" href="../../assets/style.css">
</head>
<body>
  <div class="disclosure-bar">{_esc(DISCLOSURE_KO)}</div>
  <div class="container">
    <header class="top-nav">
      <a class="brand" href="../index.html">← {brand} KR 목록으로</a>
      <nav class="nav-links">
        <a class="pill-link" href="../../en/products/{_esc(it['id'])}.html">🌐 English Page</a>
      </nav>
    </header>
    <main class="detail-box">
      <span class="cat-badge">{_esc(it['brand'])} · {_esc(it['model'])}</span>
      <h1 style="margin:12px 0 8px;">{_esc(loc['title'])}</h1>
      <p class="summary">기준일: {_esc(it['updated_at'])} · {_esc(loc['summary'])}</p>

      <div class="price-compare" style="margin-top:20px;">
        <div class="price-box">
          <span class="price-label">쿠팡 (로켓배송·국내 정발/직구)</span>
          <span class="price-val">{int(p['coupang_krw']):,}원</span>
        </div>
        <div class="price-box">
          <span class="price-label">알리익스프레스 직구 최저가</span>
          <span class="price-val">{int(p['ali_krw']):,}원</span>
        </div>
      </div>

      <p style="margin-top:14px;font-weight:700;color:#38bdf8;">💡 구매 가이드: {_esc(loc['verdict'])} (가격 차이 {m['kr_diff_krw']:,}원 / {m['kr_savings_pct']}%)</p>

      <div class="cta-row" style="margin-top:16px;">
        <a class="btn btn-coupang" href="{_esc(links['coupang'])}" target="_blank" rel="nofollow sponsored noopener">🚀 쿠팡 현재 가격·재고 확인</a>
        <a class="btn btn-ali" href="{_esc(links['aliexpress'])}" target="_blank" rel="nofollow sponsored noopener">🌏 알리익스프레스 할인가 확인</a>
      </div>

      <h2 style="margin-top:28px;font-size:1.15rem;">주요 스펙 요약</h2>
      <table class="spec-table">{spec_rows}</table>

      <div class="pros-cons">
        <div class="list-panel">
          <h3 style="color:#22c55e;">👍 장점 (Pros)</h3>
          <ul>{pros_li}</ul>
        </div>
        <div class="list-panel">
          <h3 style="color:#eab308;">⚠️ 구매 전 꼭 확인할 단점 (Cons)</h3>
          <ul>{cons_li}</ul>
        </div>
      </div>
    </main>
    <footer>
      <span>{_esc(DISCLOSURE_KO)}</span>
      <span><a href="../../privacy.html">정책 및 고지사항</a></span>
    </footer>
  </div>
</body>
</html>
"""

    loc = it["en"]
    pros_li = "".join(f"<li>{_esc(x)}</li>" for x in loc["pros"])
    cons_li = "".join(f"<li>{_esc(x)}</li>" for x in loc["cons"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(loc['title'])} — Amazon vs AliExpress Price & Review | {brand}</title>
  <meta name="description" content="{_esc(loc['summary'])}">
  <link rel="stylesheet" href="../../assets/style.css">
</head>
<body>
  <div class="disclosure-bar">{_esc(DISCLOSURE_EN)}</div>
  <div class="container">
    <header class="top-nav">
      <a class="brand" href="../index.html">← Back to {brand} Global</a>
      <nav class="nav-links">
        <a class="pill-link" href="../../ko/products/{_esc(it['id'])}.html">🇰🇷 한국어 페이지</a>
      </nav>
    </header>
    <main class="detail-box">
      <span class="cat-badge">{_esc(it['brand'])} · {_esc(it['model'])}</span>
      <h1 style="margin:12px 0 8px;">{_esc(loc['title'])}</h1>
      <p class="summary">Last checked: {_esc(it['updated_at'])} · {_esc(loc['summary'])}</p>

      <div class="price-compare" style="margin-top:20px;">
        <div class="price-box">
          <span class="price-label">Amazon (Fast Prime Delivery)</span>
          <span class="price-val">USD {p['amazon_usd']:.2f}</span>
        </div>
        <div class="price-box">
          <span class="price-label">AliExpress Direct Saver</span>
          <span class="price-val">USD {p['ali_usd']:.2f}</span>
        </div>
      </div>

      <p style="margin-top:14px;font-weight:700;color:#38bdf8;">💡 Buying Verdict: {_esc(loc['verdict'])} (Spread: USD {m['en_diff_usd']:.2f} / {m['en_savings_pct']}%)</p>

      <div class="cta-row" style="margin-top:16px;">
        <a class="btn btn-amazon" href="{_esc(links['amazon'])}" target="_blank" rel="nofollow sponsored noopener">📦 Check Amazon Price</a>
        <a class="btn btn-ali" href="{_esc(links['aliexpress'])}" target="_blank" rel="nofollow sponsored noopener">🌏 Check AliExpress Deal</a>
      </div>

      <h2 style="margin-top:28px;font-size:1.15rem;">Technical Specifications</h2>
      <table class="spec-table">{spec_rows}</table>

      <div class="pros-cons">
        <div class="list-panel">
          <h3 style="color:#22c55e;">👍 Strengths</h3>
          <ul>{pros_li}</ul>
        </div>
        <div class="list-panel">
          <h3 style="color:#eab308;">⚠️ Real-World Caveats</h3>
          <ul>{cons_li}</ul>
        </div>
      </div>
    </main>
    <footer>
      <span>{_esc(DISCLOSURE_EN)}</span>
      <span><a href="../../privacy.html">Privacy &amp; Affiliate Disclosure</a></span>
    </footer>
  </div>
</body>
</html>
"""


def _render_root_gateway(cfg: dict) -> str:
    brand = _esc(cfg["site"]["brand_name"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{brand} — Global Desk & Tech Gear Price Comparison</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <div class="container" style="text-align:center;padding-top:80px;">
    <h1 style="font-size:2.1rem;margin-bottom:12px;">⚡ {brand}</h1>
    <p style="color:#94a3b8;max-width:560px;margin:0 auto 32px;">
      Select your region to compare fast domestic delivery against direct global deals.
    </p>
    <div style="display:flex;justify-content:center;gap:16px;flex-wrap:wrap;">
      <a class="btn btn-coupang" style="padding:14px 28px;font-size:1rem;" href="ko/index.html">🇰🇷 한국어 허브 (쿠팡 vs 알리 비교)</a>
      <a class="btn btn-amazon" style="padding:14px 28px;font-size:1rem;" href="en/index.html">🌐 Global Hub (Amazon vs AliExpress)</a>
    </div>
    <p id="auto-hint" style="margin-top:24px;font-size:0.85rem;color:#64748b;"></p>
  </div>
  <script>
    const userLang = (navigator.language || '').toLowerCase();
    const hint = document.getElementById('auto-hint');
    if (userLang.startsWith('ko')) {{
      hint.innerHTML = '한국어 브라우저가 감지되었습니다. <a href="ko/index.html">한국어 비교 페이지로 바로 이동 →</a>';
    }} else {{
      hint.innerHTML = 'English / Global browser detected. <a href="en/index.html">Continue to Global Hub →</a>';
    }}
  </script>
</body>
</html>
"""


def _render_privacy_page(cfg: dict) -> str:
    brand = _esc(cfg["site"]["brand_name"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Privacy Policy & Affiliate Disclosure | {brand}</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <div class="container">
    <header class="top-nav">
      <a class="brand" href="index.html">⚡ {brand}</a>
      <nav class="nav-links">
        <a class="pill-link" href="ko/index.html">한국어</a>
        <a class="pill-link" href="en/index.html">English</a>
      </nav>
    </header>
    <main class="detail-box">
      <h1>Affiliate Disclosure &amp; Privacy Policy</h1>
      <h2 style="margin-top:20px;font-size:1.1rem;">1. Affiliate Disclosure (English)</h2>
      <p style="margin-top:8px;color:#cbd5e1;">
        {_esc(DISCLOSURE_EN)} {brand} participates in the Amazon Services LLC Associates Program and the AliExpress Portals Affiliate Program, affiliate advertising programs designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com and AliExpress.com.
      </p>
      <h2 style="margin-top:20px;font-size:1.1rem;">2. 제휴 마케팅 대가성 고지 (한국어)</h2>
      <p style="margin-top:8px;color:#cbd5e1;">
        {_esc(DISCLOSURE_KO)}
      </p>
      <h2 style="margin-top:20px;font-size:1.1rem;">3. Privacy &amp; Cookies</h2>
      <p style="margin-top:8px;color:#cbd5e1;">
        {brand} is a static comparison site and does not collect personal registration data, passwords, or payment details. When you click outbound retail links (Amazon, AliExpress, Coupang), those third-party merchants may place standard affiliate attribution cookies in accordance with their respective privacy policies.
      </p>
    </main>
  </div>
</body>
</html>
"""


def _render_sitemap(items: list[dict], cfg: dict) -> str:
    base = cfg["site"]["base_url"].rstrip("/")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [f"{base}/", f"{base}/ko/index.html", f"{base}/en/index.html", f"{base}/privacy.html"]
    for it in items:
        urls.append(f"{base}/ko/products/{it['id']}.html")
        urls.append(f"{base}/en/products/{it['id']}.html")
    entries = "\n".join(
        f"  <url><loc>{_esc(u)}</loc><lastmod>{today}</lastmod></url>" for u in urls
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'


def build_site(approved_items: list[dict], cfg: dict, dist_dir: Path) -> dict:
    """Generate static HTML files for root, /ko, /en, product pages, privacy policy, and sitemap."""
    (dist_dir / "assets").mkdir(parents=True, exist_ok=True)
    (dist_dir / "ko" / "products").mkdir(parents=True, exist_ok=True)
    (dist_dir / "en" / "products").mkdir(parents=True, exist_ok=True)

    (dist_dir / "assets" / "style.css").write_text(SHARED_CSS.strip() + "\n", encoding="utf-8")
    (dist_dir / "index.html").write_text(_render_root_gateway(cfg), encoding="utf-8")
    (dist_dir / "privacy.html").write_text(_render_privacy_page(cfg), encoding="utf-8")
    (dist_dir / "ko" / "index.html").write_text(_render_ko_index(approved_items, cfg), encoding="utf-8")
    (dist_dir / "en" / "index.html").write_text(_render_en_index(approved_items, cfg), encoding="utf-8")

    for item in approved_items:
        (dist_dir / "ko" / "products" / f"{item['id']}.html").write_text(
            _render_detail_page(item, "ko", cfg), encoding="utf-8"
        )
        (dist_dir / "en" / "products" / f"{item['id']}.html").write_text(
            _render_detail_page(item, "en", cfg), encoding="utf-8"
        )

    (dist_dir / "sitemap.xml").write_text(_render_sitemap(approved_items, cfg), encoding="utf-8")
    (dist_dir / ".nojekyll").write_text("", encoding="utf-8")

    return {
        "approved_products_rendered": len(approved_items),
        "total_html_pages": 4 + (len(approved_items) * 2),
        "output_dir": str(dist_dir),
    }
