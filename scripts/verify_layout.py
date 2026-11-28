"""Headless layout, overflow and interaction audit for the built site (developer tool, not part of the build).

    python run_pipeline.py            # build dist/ first
    python scripts/verify_layout.py   # needs: pip install playwright (uses the installed Chrome or Edge)

Checks every target page at 320x700, 375x812, 768x1024 and 1440x900:
  * zero horizontal overflow (document scrollWidth <= innerWidth)
  * zero element bleed past the viewport or past its own card, and no silently clipped text
Then exercises the interactive pieces: trap-cut filter chips (live counts, zero layout jump), promo-code copy
chips, the promo calculator maths (compared with the Python reference implementation), the sale traffic light,
and the client-side expiry of live-offer lines (against a temporary build with synthetic cache entries).
Exits non-zero on any failure.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VIEWPORTS = [(320, 700), (375, 812), (768, 1024), (1440, 900)]
AUDITED = {"combos": 0}

AUDIT_JS = r"""
() => {
  const vw = window.innerWidth;
  const out = { scrollWidth: document.documentElement.scrollWidth, innerWidth: vw, bleed: [], clipped: [] };
  const desc = el => {
    const cls = typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).join('.') : '';
    return el.tagName.toLowerCase() + cls + ' "' + (el.textContent || '').trim().slice(0, 40) + '"';
  };
  const clips = el => {
    const s = getComputedStyle(el);
    return ['hidden', 'auto', 'scroll', 'clip'].includes(s.overflowX);
  };
  const shielded = (el, stop) => {
    for (let p = el.parentElement; p && p !== stop; p = p.parentElement) if (clips(p)) return true;
    return false;
  };
  const visible = el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const srOnly = el => !!el.closest('.sr-only') || getComputedStyle(el).clip === 'rect(0px, 0px, 0px, 0px)';

  // 1. Nothing visible may extend past the viewport unless a scroll/clip container owns it.
  document.querySelectorAll('body *').forEach(el => {
    if (!visible(el) || srOnly(el)) return;
    const s = getComputedStyle(el);
    if (s.position === 'fixed') return;
    const r = el.getBoundingClientRect();
    if ((r.right > vw + 0.5 || r.left < -0.5) && !shielded(el, null)) out.bleed.push('viewport: ' + desc(el));
  });

  // 2. Nothing inside a card may poke out of that card.
  const CARDS = '.sheet, .panel, .pcard, .row, .vs-pick, .vs-card, .guide-card, .board > *, .verdict-box, .notice, .side, .tier, .trap, .btn, .buy, .feat-strip, .sm';
  document.querySelectorAll(CARDS).forEach(card => {
    if (!visible(card)) return;
    const c = card.getBoundingClientRect();
    card.querySelectorAll('*').forEach(el => {
      if (!visible(el) || srOnly(el)) return;
      const s = getComputedStyle(el);
      if (s.position === 'absolute' || s.position === 'fixed') return;
      if (shielded(el, card) || clips(card)) return;
      const r = el.getBoundingClientRect();
      if (r.right > c.right + 1 || r.left < c.left - 1) out.bleed.push('card ' + desc(card).slice(0, 50) + ' <- ' + desc(el));
    });
  });

  // 3. Text must not be silently cut off: clipping boxes whose content is wider than the box,
  //    except deliberate ellipsis/line-clamp truncation and real scroll regions.
  document.querySelectorAll('body *').forEach(el => {
    if (!visible(el) || srOnly(el) || !el.textContent.trim()) return;
    const s = getComputedStyle(el);
    if (!['hidden', 'clip'].includes(s.overflowX)) return;
    if (s.textOverflow === 'ellipsis' || s.webkitLineClamp !== 'none') return;
    if (el.scrollWidth > el.clientWidth + 1) {
      // Only report when a descendant with text really sits outside the clip box.
      const box = el.getBoundingClientRect();
      const cut = Array.from(el.querySelectorAll('*')).some(k => {
        if (!visible(k) || !k.textContent.trim() || getComputedStyle(k).position === 'absolute') return false;
        const r = k.getBoundingClientRect();
        return r.right > box.right + 1 && !shielded(k, el);
      });
      if (cut) out.clipped.push(desc(el));
    }
  });
  out.bleed = Array.from(new Set(out.bleed)).slice(0, 8);
  out.clipped = Array.from(new Set(out.clipped)).slice(0, 8);
  return out;
}
"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401 - silence request logging
        pass


def serve(directory: Path) -> tuple[http.server.ThreadingHTTPServer, str]:
    handler = functools.partial(_Quiet, directory=str(directory))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def launch(pw):
    last = None
    for channel in ("chrome", "msedge", None):
        try:
            return pw.chromium.launch(channel=channel, headless=True) if channel else pw.chromium.launch(headless=True)
        except Exception as exc:  # browser channel not installed
            last = exc
    raise SystemExit(f"No Chromium-family browser available for Playwright: {last}")


def goto(page, url: str) -> None:
    page.goto(url, wait_until="load")
    try:
        page.wait_for_load_state("networkidle", timeout=6000)
    except Exception:
        pass
    page.evaluate("document.fonts && document.fonts.ready")


def audit_pages(browser, base: str, paths: list[str], shots: Path | None) -> list[str]:
    failures: list[str] = []
    for w, h in VIEWPORTS:
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
        page = ctx.new_page()
        for path in paths:
            goto(page, base + path)
            res = page.evaluate(AUDIT_JS)
            AUDITED["combos"] += 1
            ok = res["scrollWidth"] <= res["innerWidth"] and not res["bleed"] and not res["clipped"]
            print(f"  {'ok  ' if ok else 'FAIL'} {w:>4}x{h:<4} {path}  scrollWidth={res['scrollWidth']} innerWidth={res['innerWidth']}"
                  f" bleed={len(res['bleed'])} clipped={len(res['clipped'])}")
            if not ok:
                failures.append(f"{w}x{h} {path}: {json.dumps(res, ensure_ascii=False)}")
            if shots and w in (375, 1440):
                name = (path.strip("/").replace("/", "_").replace("?", "_") or "root") + f"_{w}.png"
                page.screenshot(path=str(shots / name), full_page=False)
        ctx.close()
    return failures


def check_hub_filters(browser, base: str, lang: str, failures: list[str]) -> None:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    goto(page, f"{base}/{lang}/")
    page.wait_for_selector("[data-hub][data-ready]")
    total = int(page.inner_text('[data-n="trap:all"]'))
    geo = "() => { const t = document.querySelector('.traps').getBoundingClientRect(); const l = document.querySelector('.ledger, .empty').getBoundingClientRect(); return [Math.round(t.top + scrollY), Math.round(t.height), Math.round(l.top + scrollY)]; }"
    before = page.evaluate(geo)
    for key in ("mac-dual", "airline-100wh", "low-reset", "direct-edge", "domestic-fast"):
        want = int(page.inner_text(f'[data-n="trap:{key}"]'))
        page.click(f'[data-trap="{key}"]')
        for _ in range(10):
            if page.is_visible("[data-all]"):
                page.click("[data-all]")
            elif page.is_visible("[data-load]"):
                page.click("[data-load]")
            else:
                break
        shown = page.evaluate("() => Array.from(document.querySelectorAll('[data-rows] > li')).filter(li => !li.hidden).length")
        member = page.evaluate(
            "k => Array.from(document.querySelectorAll('[data-rows] > li')).filter(li => !li.hidden).every(li => (li.dataset.traps || '').split(' ').includes(k))", key)
        pressed = page.get_attribute(f'[data-trap="{key}"]', "aria-pressed")
        after = page.evaluate(geo)
        ok = shown == want and member and pressed == "true" and after == before and 0 < want < total
        print(f"  {'ok  ' if ok else 'FAIL'} {lang} trap {key}: chip={want} visible={shown} layout {before}->{after}")
        if not ok:
            failures.append(f"{lang} trap {key}: chip={want} visible={shown} member={member} pressed={pressed} geo {before}->{after}")
        page.click(f'[data-trap="{key}"]')  # toggling the active chip returns to "all"
    back = page.evaluate("() => document.querySelector('[data-trap=\"all\"]').getAttribute('aria-pressed')")
    if back != "true" or int(page.inner_text('[data-n="trap:all"]')) != total:
        failures.append(f"{lang} trap reset did not return to all ({back})")
    ctx.close()


def check_board(browser, base: str, lang: str, failures: list[str]) -> None:
    from src.tools_and_guides import active_promo, load_promo_tiers, sale_reference_date, sale_signal

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.grant_permissions(["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    goto(page, f"{base}/{lang}/")
    day = sale_reference_date(lang)
    sig = sale_signal(lang, day)
    label = page.inner_text("[data-board-label]").strip()
    cls = page.get_attribute("[data-board-sig]", "class")
    ok = label == sig["label"] and f"is-{sig['tone']}" in cls
    print(f"  {'ok  ' if ok else 'FAIL'} {lang} traffic light: {label!r} ({cls})")
    if not ok:
        failures.append(f"{lang} board label {label!r} != {sig['label']!r} / {cls}")

    promo = active_promo(load_promo_tiers(), lang, day)
    chips = page.locator("[data-board-tiers] > li").count()
    if chips != len(promo["tiers"]):
        failures.append(f"{lang} board shows {chips} tiers, expected {len(promo['tiers'])}")
    coded = [t for t in promo["tiers"] if t.get("code")]
    if coded:
        btn = page.locator(f'[data-board-tiers] [data-copy="{coded[0]["code"]}"]')
        w0 = btn.bounding_box()["width"]
        btn.click()
        page.wait_for_selector("[data-board-tiers] [data-copied]")
        w1 = btn.bounding_box()["width"]
        clip = page.evaluate("navigator.clipboard.readText()")
        done = btn.locator(".copy-done").inner_text().strip()
        want_done = "복사됨 ✓" if lang == "ko" else "Copied ✓"
        ok = clip == coded[0]["code"] and done == want_done and abs(w0 - w1) < 0.5
        print(f"  {'ok  ' if ok else 'FAIL'} {lang} copy chip: clipboard={clip!r} feedback={done!r} width {w0:.1f}->{w1:.1f}")
        if not ok:
            failures.append(f"{lang} copy chip clipboard={clip!r} feedback={done!r} width {w0}->{w1}")
    else:
        print(f"  ok   {lang} board: {chips} reference tier guides (no verified code in ali_promo_tiers.json for this edition)")
    ctx.close()


def check_calculator(browser, base: str, lang: str, failures: list[str]) -> None:
    from src.tools_and_guides import active_promo, compute_promo_checkout, load_promo_tiers, sale_reference_date

    products = json.loads((ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    promo = active_promo(load_promo_tiers(), lang, sale_reference_date(lang))
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.grant_permissions(["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    goto(page, f"{base}/{lang}/tools/ali-promo-calculator/")
    origins = ("cn", "us") if lang == "ko" else ("domestic", "cross")
    cases = [
        (products[0], 59.99, 3, 2, origins[0]),
        (next(p for p in products if p["msrp_usd"] > 160 and p["msrp_usd"] < 200), 189.0, 0, 0, origins[0]),
        (next(p for p in products if p["msrp_usd"] > 160 and p["msrp_usd"] < 200), 189.0, 0, 0, origins[1]),
        (next(p for p in products if p["msrp_usd"] > 600), 649.0, 20, 1.5, origins[0]),
    ]
    for prod, price, coupon, coin, origin in cases:
        page.select_option('[name="preset"]', prod["id"])
        filled = float(page.input_value('[name="price"]'))
        if abs(filled - float(prod["msrp_usd"])) > 0.001:
            failures.append(f"{lang} calc preset did not fill MSRP for {prod['id']}: {filled}")
        page.fill('[name="price"]', str(price))
        page.fill('[name="coupon"]', str(coupon))
        page.fill('[name="coin"]', str(coin))
        page.select_option('[name="tier"]', "auto")
        page.select_option('[name="origin"]', origin)
        want = compute_promo_checkout(price, store_coupon_usd=coupon, coin_pct=coin, tiers=promo["tiers"],
                                      origin=origin, msrp_usd=prod["msrp_usd"])
        got = float(page.inner_text("[data-net-usd]").replace("$", "").replace(",", ""))
        state = page.get_attribute("[data-customs]", "data-customs")
        want_state = "ok" if want["duty_free"] else "over"
        cta = page.locator(".calc-cta a").count()
        vs = page.locator("[data-vs-msrp]").count()
        ok = abs(got - want["net_usd"]) < 0.005 and state == want_state and cta == 2 and vs == 1
        if lang == "ko":
            krw = int("".join(ch for ch in page.inner_text("[data-net-krw]") if ch.isdigit()))
            ok = ok and krw == want["net_krw"]
        print(f"  {'ok  ' if ok else 'FAIL'} {lang} calc {prod['id'][:28]:28s} list={price} origin={origin}: net ${got} (py ${want['net_usd']}) customs={state}")
        if not ok:
            failures.append(f"{lang} calc {prod['id']} price={price}: js={got}/{state} py={want['net_usd']}/{want_state} cta={cta} vs={vs}")
    # deep link from a product card
    goto(page, f"{base}/{lang}/tools/ali-promo-calculator/?p={products[1]['id']}")
    if page.input_value('[name="preset"]') != products[1]["id"]:
        failures.append(f"{lang} calc ?p= deep link did not preselect the product")
    ctx.close()


def check_live_offer_expiry(browser, failures: list[str]) -> None:
    """Build a throwaway site with synthetic cache entries and confirm labels + client-side auto-hide."""
    from src.affiliate import load_config
    from src.site_builder import build_site
    from src.verifier import verify_batch

    cfg = load_config(ROOT)
    products = json.loads((ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    approved, _ = verify_batch(products, cfg)
    now = datetime.now(timezone.utc)
    a, b = approved[0], approved[1]

    def entry(kind: str, currency: str, text: str, expires: datetime) -> dict:
        return {"source_kind": kind, "currency": currency, "price": 1.0, "price_text": text,
                "observed_at": now.isoformat(timespec="seconds"), "expires_at": expires.isoformat(timespec="seconds"),
                "signal_source": "verify"}

    cache = {"updated_at": now.isoformat(), "promo_codes": [], "offers": {
        a["id"]: [entry("community_benchmark", "USD", "$41.00", now + timedelta(seconds=75))],
        b["id"]: [entry("community_benchmark", "USD", "$52.00", now + timedelta(hours=40)),
                  entry("ali_official_api", "USD", "$50.50", now + timedelta(hours=10))],
    }}
    with tempfile.TemporaryDirectory() as tmp:
        dist = Path(tmp) / "dist"
        build_site(approved, cfg, dist, live_offers=cache, now=now)
        httpd, base = serve(dist)
        try:
            from src.site_builder import product_slug
            # Live-offer lines must not break the layout either (hub rows, cards view, detail, VS).
            live_paths = ["/ko/", "/en/", "/en/?view=cards", f"/ko/p/{product_slug(a['id'])}/", f"/en/p/{product_slug(b['id'])}/"]
            failures += audit_pages(browser, base, live_paths, None)
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            for lang, want in (("ko", "최근 커뮤니티 포착 핫딜 기준가 (관측일"), ("en", "Recent Community-Spotted Deal Benchmark (Observed")):
                goto(page, f"{base}/{lang}/p/{product_slug(a['id'])}/")
                line = page.locator(".decide .live-line")
                text = line.inner_text() if line.count() else ""
                ok = want in text and "$41.00" in text and line.get_attribute("data-live-kind") == "community_benchmark"
                print(f"  {'ok  ' if ok else 'FAIL'} {lang} community benchmark label: {text!r}")
                if not ok:
                    failures.append(f"{lang} community label wrong: {text!r}")
            goto(page, f"{base}/en/p/{product_slug(b['id'])}/")
            api = page.locator(".decide .live-line").inner_text()
            if "Live AliExpress API Offer" not in api or "$50.50" not in api:
                failures.append(f"API offer should outrank the community benchmark: {api!r}")
            remaining = (now + timedelta(seconds=76) - datetime.now(timezone.utc)).total_seconds()
            page.wait_for_timeout(max(0, int(remaining * 1000)))
            goto(page, f"{base}/ko/p/{product_slug(a['id'])}/")
            hidden = page.evaluate("() => { const el = document.querySelector('.decide .live-line'); return !el || el.hidden; }")
            print(f"  {'ok  ' if hidden else 'FAIL'} expired benchmark auto-hidden client-side: {hidden}")
            if not hidden:
                failures.append("expired live-offer line stayed visible")
            ctx.close()
        finally:
            httpd.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dist", default=str(ROOT / "dist"))
    parser.add_argument("--shots", default="", help="Directory for 375px and 1440px screenshots of each target page.")
    args = parser.parse_args()
    dist = Path(args.dist)
    if not (dist / "index.html").exists():
        raise SystemExit("dist/ is empty: run `python run_pipeline.py` first.")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed: pip install playwright")

    from src.vs_pairs import VS_PAIRS
    from src.tools_and_guides import GUIDES_KO

    products = json.loads((ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    from src.site_builder import product_slug

    slug = product_slug(products[0]["id"])
    vs_a, vs_b = VS_PAIRS[0]["slug"], VS_PAIRS[3]["slug"]
    paths = [
        "/ko/", "/en/",
        "/ko/tools/ali-promo-calculator/", "/en/tools/ali-promo-calculator/",
        f"/ko/tools/ali-promo-calculator/?p={products[0]['id']}",
        "/ko/guides/", f"/ko/guides/{GUIDES_KO[0]['slug']}/", f"/ko/guides/{GUIDES_KO[5]['slug']}/",
        "/en/guides/", f"/en/guides/{GUIDES_KO[0]['slug']}/",
        "/ko/vs/", "/en/vs/", f"/ko/vs/{vs_a}/", f"/en/vs/{vs_a}/", f"/ko/vs/{vs_b}/", f"/en/vs/{vs_b}/",
        f"/ko/p/{slug}/", f"/en/p/{slug}/", "/ko/?view=cards", "/en/?view=cards",
        "/ko/c/powerbanks/", "/ko/tools/macbook-dock-checker/", "/",
    ]
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    httpd, base = serve(dist)
    failures: list[str] = []
    with sync_playwright() as pw:
        browser = launch(pw)
        print(f"Layout & overflow audit ({len(paths)} pages x {len(VIEWPORTS)} viewports)")
        failures += audit_pages(browser, base, paths, shots)
        print("Interaction checks")
        for lang in ("ko", "en"):
            check_hub_filters(browser, base, lang, failures)
            check_board(browser, base, lang, failures)
            check_calculator(browser, base, lang, failures)
        check_live_offer_expiry(browser, failures)
        browser.close()
    httpd.shutdown()

    print(f"\n{AUDITED['combos']} page/viewport combinations audited; failures: {len(failures)}")
    for f in failures:
        print("  -", f[:900])
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
