"""Pillars 1, 3, 4 and site-wide rules: situation board, trap filters, KO guides, VS battles, compliance."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest

from conftest import ROOT, read
from src.affiliate import DISCLOSURE_KO
from src.site_builder import TRAPS, battery_wh, product_slug, single_port_watts, site_url_paths, trap_keys
from src.tools_and_guides import GUIDES_EN, GUIDES_KO
from src.vs_battles import VS_NAMES, active_pairs, rivals_by_product
from src.vs_pairs import VS_PAIRS

HANGUL = re.compile(r"[ᄀ-ᇿ㄰-㆏가-힯]")
KO_SWITCH_LINK = re.compile(r'<a\b[^>]*hreflang="ko"[^>]*>.*?</a>', re.S)
AMAZON_SENTENCE = "As an Amazon Associate I earn from qualifying purchases."


# ------------------------------------------------------------------ gatekeeper + catalog rules
def test_gatekeeper_approves_the_whole_catalog_and_blocks_the_inbox_trap(catalog, inbox, cfg):
    from src.verifier import verify_batch

    approved, audit = verify_batch(catalog + inbox, cfg)
    assert len(approved) == len(catalog) >= 69
    rejected = [a for a in audit if not a["passed"]]
    assert [r["product_id"] for r in rejected] == [c["id"] for c in inbox]
    assert any("UNVERIFIED_STATIC_RETAILER_PRICE" in reason for reason in rejected[0]["reasons"])


def test_no_static_retailer_prices_in_the_catalog_and_the_guard_still_blocks_them(catalog, cfg):
    from src.verifier import verify_product

    assert not any("prices" in p for p in catalog)
    tainted = dict(catalog[0], prices={"coupang_krw": 59000})
    result, enriched = verify_product(tainted, cfg)
    assert not result.passed and enriched is None


def test_affiliate_ids_are_unchanged(cfg):
    aff = cfg["affiliate"]
    assert aff["coupang_partners_id"] == "AF8784203"
    assert aff["aliexpress_tracking_id"] == "default"
    assert aff["amazon_associate_tag"] == "gearcomparehu-20"


def test_affiliate_queries_are_exact_brand_and_model_tokens(catalog):
    from src.collector import GLOBAL_BRANDS

    aliases: dict[str, set[str]] = {}
    for kw, (brand, _cat) in GLOBAL_BRANDS.items():
        aliases.setdefault(brand.lower(), set()).add(kw.lower())
    filler = re.compile(r"(정품|추천|인기|최저가|특가|best|cheap|deal|original|new 20\d\d)", re.I)
    for p in catalog:
        brand = p["brand"].lower()
        names = aliases.get(brand, set()) | {brand, brand.replace(" ", "")}
        for key in ("coupang_query", "ali_query", "amazon_query"):
            q = p["urls"][key]
            assert not re.search(r"[()/]", q), f"{p['id']} {key}: no parenthetical or slash noise"
            assert not filler.search(q), f"{p['id']} {key}: vague filler word in {q!r}"
            assert 2 <= len(q.split()) <= 9, f"{p['id']} {key}: {q!r}"
            assert re.search(r"\d", q) or len(q.split()) >= 3, f"{p['id']} {key}: needs a model token"
            if key != "coupang_query":
                assert q.lower().replace(" ", "").startswith(brand.replace(" ", "")), f"{p['id']} {key}: {q!r}"
                assert not HANGUL.search(q)
            else:
                # The Korean query must share at least one exact model/SKU token with the AliExpress query.
                model_tokens = {t.lower() for t in re.findall(r"[A-Za-z0-9.-]+", p["urls"]["ali_query"])
                                if re.search(r"\d", t) or len(t) >= 4}
                shared = model_tokens & {t.lower() for t in re.findall(r"[A-Za-z0-9.-]+", q)}
                assert shared, f"{p['id']} {key}: no exact model token in {q!r}"
        assert names


def test_no_personal_handle_in_tracked_sources():
    pattern = re.compile(r"\bsol\b", re.I)
    files = [ROOT / "run_pipeline.py", ROOT / "config.example.json", ROOT / "README.md", ROOT / "data" / "ali_promo_tiers.json"]
    files += sorted((ROOT / "src").glob("*.py")) + sorted((ROOT / "tests").glob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    this_file = __file__
    for f in files:
        if str(f) == this_file:
            continue
        assert not pattern.search(f.read_text(encoding="utf-8")), f"personal handle found in {f.name}"


# ------------------------------------------------------------------ build shape, sitemap, compliance
def test_build_writes_every_page_and_the_sitemap_lists_them_all(built, approved):
    dist, base = built["dist"], built["base"]
    pages = sorted(dist.rglob("index.html"))
    cats = {it["category"] for it in approved}
    expected = 4 + 4 + 2 * 13 + 2 * 16 + 2 * len(cats) + 2 * len(approved)
    assert len(pages) == expected == built["site"]["total_html_pages"]
    assert expected >= 226

    root = ET.parse(dist / "sitemap.xml").getroot()
    locs = [el.text for el in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert len(locs) == len(set(locs)) == expected == len(site_url_paths(approved))
    for loc in locs:
        assert loc.startswith(base + "/")
        assert (dist / loc[len(base) + 1:] / "index.html").exists(), f"sitemap URL without a page: {loc}"
    for needle in ("/ko/tools/ali-promo-calculator/", "/en/tools/ali-promo-calculator/", "/ko/guides/",
                   f"/ko/guides/{GUIDES_KO[0]['slug']}/", "/ko/vs/", "/en/vs/",
                   f"/ko/vs/{VS_PAIRS[0]['slug']}/", f"/en/vs/{VS_PAIRS[-1]['slug']}/"):
        assert base + needle in locs


def test_zero_hangul_on_english_pages_except_the_language_switcher(built):
    en_pages = sorted((built["dist"] / "en").rglob("*.html"))
    assert len(en_pages) >= 112
    leaks = {}
    for page in en_pages:
        text = KO_SWITCH_LINK.sub("", read(page))
        hit = HANGUL.search(text)
        if hit:
            leaks[str(page.relative_to(built["dist"]))] = text[max(0, hit.start() - 40): hit.start() + 20]
    assert leaks == {}
    hub = read(built["dist"] / "en" / "index.html")
    assert re.search(r'<a href="[^"]+" hreflang="ko">한국어 허브</a>', hub), "the intentional switcher link stays"


def test_mandatory_disclosures_on_every_page(built):
    dist = built["dist"]
    for page in sorted((dist / "en").rglob("*.html")):
        assert AMAZON_SENTENCE in read(page), page
    for page in sorted((dist / "ko").rglob("*.html")):
        assert DISCLOSURE_KO in read(page), page
    assert AMAZON_SENTENCE in read(dist / "policy" / "index.html") and DISCLOSURE_KO in read(dist / "policy" / "index.html")


def test_internal_links_resolve(built):
    dist = built["dist"]
    broken = []
    for page in sorted(dist.rglob("index.html")):
        for href in re.findall(r'(?:href|src)="([^"#]+)"', read(page)):
            if re.match(r"^(https?:|mailto:|data:|//)", href) or "${" in href:
                continue
            target = (page.parent / href.split("?")[0]).resolve()
            if href.split("?")[0].endswith("/"):
                target = target / "index.html"
            if not target.exists():
                broken.append((str(page.relative_to(dist)), href))
    assert broken == []


def test_zero_overflow_css_contract(built):
    css = read(built["dist"] / "assets" / "style.css")
    assert "* { margin: 0; padding: 0; min-width: 0; }" in css
    for selector in (".board-state", ".vs-pick h2", ".vs-name strong", ".live-line", ".calc-lines dt", ".vs-card h3"):
        rule = css.split(selector + " {", 1)[1].split("}", 1)[0]
        assert "overflow-wrap: anywhere" in rule, selector
    assert ".traps-row { flex-wrap: nowrap; overflow-x: auto;" in css


# ------------------------------------------------------------------ Pillar 1: situation board + trap filters
@pytest.mark.parametrize("lang, label, calc", [
    ("ko", "매수 적기 · 연말 메가세일·블프 구간", "tools/ali-promo-calculator/"),
    ("en", "BUY WINDOW · Mega Sale Window", "tools/ali-promo-calculator/"),
])
def test_hub_situation_board(built, lang, label, calc):
    hub = read(built["dist"] / lang / "index.html")
    board = hub.split('<section class="board"', 1)[1].split("</section>", 1)[0]
    assert hub.index('<section class="board"') < hub.index('<dl class="summary"'), "board sits above the fold"
    assert 'data-window="mega"' in board and "board-sig is-go" in board
    assert f"data-board-label>{label}</h2>" in board
    assert f'href="{calc}"' in board
    payload = json.loads(board.split("data-board-json>")[1].split("</script>")[0])
    assert set(payload["copy"]) == {"mega", "choice", "hold", "standard"}
    assert payload["tz"] == (9 if lang == "ko" else -8)
    assert [t["min_spend_usd"] for t in payload["ref"]["tiers"]] == [19, 39, 79, 159, 299]
    notice = "선착순 소진·일부 품목 제외 가능 — 결제창 최종 적용 확인" if lang == "ko" else "Limited redemptions &amp; exclusions apply — verify at checkout"
    assert notice in board
    assert payload["copy_done"] == ("복사됨 ✓" if lang == "ko" else "Copied ✓")
    # Every copy chip carries a code and the swap label; chips without a code are plain tier guides.
    for chip in re.findall(r'<button type="button" class="tier" data-copy="([^"]*)"', board):
        assert re.fullmatch(r"[A-Z0-9]{4,16}", chip)
    assert board.count("data-copy=") == board.count('class="copy-done"')
    js = read(built["dist"] / "assets" / "app.js")
    assert "navigator.clipboard.writeText(text)" in js and "data-copied" in js


def test_category_hubs_do_not_repeat_the_board(built):
    page = read(built["dist"] / "ko" / "c" / "powerbanks" / "index.html")
    assert 'class="board"' not in page and 'class="traps"' not in page


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_trap_filter_chips_and_row_attributes(built, approved, lang):
    hub = read(built["dist"] / lang / "index.html")
    labels = {"all": "전체" if lang == "ko" else "All Vetted"}
    labels.update({key: (ko if lang == "ko" else en) for key, ko, en in TRAPS})
    assert [k for k, _, _ in TRAPS] == ["mac-dual", "airline-100wh", "low-reset", "direct-edge", "domestic-fast"]
    expected = {key: sum(1 for it in approved if key in trap_keys(it, lang)) for key, _, _ in TRAPS}
    assert f'data-trap="all" aria-pressed="true"><span>{labels["all"]} (<span class="num" data-n="trap:all">{len(approved)}</span>)' in hub
    for key, count in expected.items():
        label = labels[key].replace("<", "&lt;")
        assert f'data-trap="{key}" aria-pressed="false">{label} <span class="num" data-n="trap:{key}">{count}</span>' in hub
        assert count > 0
    rows = re.findall(r'<li class="row"[^>]*data-traps="([^"]*)"', hub)
    assert len(rows) == len(approved)
    assert sum("airline-100wh" in r.split() for r in rows) == expected["airline-100wh"]
    assert hub.index('class="traps"') < hub.index('class="ledger"'), "chips sit right above the product grid"
    i18n = json.loads(hub.split("data-i18n>")[1].split("</script>")[0])
    assert i18n["traps"]["mac-dual"] == labels["mac-dual"]


def test_trap_membership_is_derived_from_catalog_data(approved):
    by_id = {it["id"]: it for it in approved}
    assert {i for i, it in by_id.items() if "mac-dual" in trap_keys(it, "ko")} == {
        "ugreen-revodok-pro-209-dock", "caldigit-ts4-thunderbolt4-dock"}
    assert "mac-dual" not in trap_keys(by_id["anker-575-usbc-dock-13in1"], "ko"), "Windows MST dock is not Mac dual-ready"
    banks = [it for it in approved if it["category"] == "powerbanks"]
    assert all(battery_wh(it) is not None and battery_wh(it) <= 100 for it in banks)
    assert battery_wh(by_id["cuktech-20-powerbank-25000-210w"]) == 90
    assert battery_wh(by_id["baseus-blade-hd-100w"]) == 72.0  # 20,000mAh x 3.6V
    assert single_port_watts(by_id["anker-prime-20000-200w"]) == 100
    assert single_port_watts(by_id["ugreen-nexode-pro-160w"]) == 140
    assert single_port_watts(by_id["baseus-nomos-140w-5in1"]) is None, "a shared total is not a verified single-port figure"
    assert "low-reset" not in trap_keys(by_id["ugreen-nexode-100w-4port"], "ko"), "its documented con is the reset drop"
    assert "low-reset" in trap_keys(by_id["satechi-usb4-slim-nvme-pro"], "en"), "fanless = quiet"
    for it in approved:
        keys = trap_keys(it, "ko")
        assert ("direct-edge" in keys) != ("domestic-fast" in keys) or float(it["msrp_usd"]) > 150
        if "direct-edge" in keys:
            assert float(it["msrp_usd"]) <= 150
    assert "direct-edge" not in trap_keys(by_id["beelink-ser8-8745hs-minipc"], "ko"), "over the $150 line"


def test_reference_anchor_strip_sits_above_store_buttons_everywhere(built, approved):
    dist = built["dist"]
    it = approved[0]
    slug = product_slug(it["id"])
    ko_hub, en_hub = read(dist / "ko" / "index.html"), read(dist / "en" / "index.html")
    assert ko_hub.count('<p class="anchor">') == len(approved) == en_hub.count('<p class="anchor">')
    row = next(r for r in ko_hub.split('<li class="row"')[1:] if f'href="p/{slug}/"' in r)
    assert row.index('class="anchor"') < row.index('class="buys"')
    assert f'출시 참고가 MSRP <b class="num">{int(it["msrp_krw"]):,}원</b>' in row
    assert "$150 면세선 이내" in row and "코드 체감가 계산</a>" in row
    en_row = next(r for r in en_hub.split('<li class="row"')[1:] if f'href="p/{slug}/"' in r)
    assert f'Ref MSRP <b class="num">${float(it["msrp_usd"]):,.2f}</b>' in en_row and "Promo Calc</a>" in en_row

    detail = read(dist / "ko" / "p" / slug / "index.html")
    assert detail.index('class="anchor"') < detail.index('class="battle"')
    guide = read(dist / "ko" / "guides" / GUIDES_KO[0]["slug"] / "index.html")
    card = guide.split('class="pcard-foot"', 1)[1]
    assert card.index('class="anchor"') < card.index('class="actions"')


# ------------------------------------------------------------------ Pillar 3: Korean guides
def test_guides_ko_matches_english_slugs_and_schema():
    assert len(GUIDES_KO) == len(GUIDES_EN) == 12
    assert [g["slug"] for g in GUIDES_KO] == [g["slug"] for g in GUIDES_EN]
    labels = ["KC 인증·전파 인증", "플러그·전압 (220V)", "통관 기준 ($150 / $200)", "쿠팡 로켓 vs 알리 초이스데이"]
    for ko, en in zip(GUIDES_KO, GUIDES_EN):
        assert ko["product_ids"] == en["product_ids"]
        assert HANGUL.search(ko["title"]) and len(ko["title"]) <= 70 and len(ko["summary"]) <= 160
        assert len(ko["matrix_headers"]) == 4 and 3 <= len(ko["matrix_rows"]) <= 6
        assert all(len(row) == 4 for row in ko["matrix_rows"])
        assert 2 <= len(ko["sections"]) <= 3 and 2 <= len(ko["exclusions"]) <= 4
        assert [k for k, _ in ko["kr_check"]] == labels
        assert all(len(text) >= 40 for _, text in ko["kr_check"])
        assert ko["tool"] in ("dock", "promo")
        blob = json.dumps(ko, ensure_ascii=False)
        assert "$150" in blob and "$200" in blob
        assert not re.search(r"₩|\d\s?만\s?원대|원대", blob), "no static price tiers in guides"
        assert not re.search(r"100%\s*정품|무조건\s*무료\s*반품", blob)


def test_ko_guides_pages_render_with_hreflang_pairs_and_tool_ctas(built, approved):
    dist = built["dist"]
    index = read(dist / "ko" / "guides" / "index.html")
    assert index.count('class="sheet guide-card"') == 12
    assert '<link rel="alternate" hreflang="en" href="' + built["base"] + '/en/guides/">' in index
    by_id = {it["id"] for it in approved}
    for ko in GUIDES_KO:
        page = read(dist / "ko" / "guides" / ko["slug"] / "index.html")
        en_page = read(dist / "en" / "guides" / ko["slug"] / "index.html")
        for html in (page, en_page):
            assert f'hreflang="ko" href="{built["base"]}/ko/guides/{ko["slug"]}/"' in html
            assert f'hreflang="en" href="{built["base"]}/en/guides/{ko["slug"]}/"' in html
            assert "../../tools/ali-promo-calculator/" in html
        assert "<h2>이런 분은 사지 마세요</h2>" in page
        assert "<h2>한국 구매자 체크: KC·220V·통관·구매 경로</h2>" in page
        assert page.count('class="pcard tool-card"') == len([p for p in ko["product_ids"] if p in by_id])
        assert f'href="../../../en/guides/{ko["slug"]}/" hreflang="en"' in page, "header switch points at the EN twin"
        if ko["tool"] == "dock":
            assert "../../tools/macbook-dock-checker/" in page.split("<main", 1)[1]


def test_korean_header_and_footer_link_guides_vs_and_calculator(built):
    hub = read(built["dist"] / "ko" / "index.html")
    header = hub.split('<header class="site-head">', 1)[1].split("</header>", 1)[0]
    assert '<a href="../ko/guides/">가이드</a>' in header
    assert '<a href="../ko/vs/">1:1 대결</a>' in header
    footer = hub.split('<footer class="site-foot">', 1)[1]
    assert "ko/guides/" in footer and "ko/vs/" in footer and "ko/tools/ali-promo-calculator/" in footer
    en_header = read(built["dist"] / "en" / "index.html").split('<header class="site-head">', 1)[1].split("</header>", 1)[0]
    assert '<a href="../en/vs/">VS Battles</a>' in en_header and "Promo Calculator" in en_header


# ------------------------------------------------------------------ Pillar 4: VS battles
def test_vs_pairs_are_15_same_category_rivalries_of_real_products(catalog):
    by_id = {p["id"]: p for p in catalog}
    assert len(VS_PAIRS) == 15 and len({p["slug"] for p in VS_PAIRS}) == 15
    assert len({frozenset((p["a"], p["b"])) for p in VS_PAIRS}) == 15
    cats = set()
    for p in VS_PAIRS:
        assert p["a"] in by_id and p["b"] in by_id and p["a"] != p["b"]
        assert by_id[p["a"]]["category"] == by_id[p["b"]]["category"], p["slug"]
        assert p["a"] in VS_NAMES and p["b"] in VS_NAMES
        assert re.fullmatch(r"[a-z0-9-]+-vs-[a-z0-9-]+", p["slug"])
        cats.add(by_id[p["a"]]["category"])
        for lang in ("ko", "en"):
            copy = p[lang]
            assert set(copy) == {"dek", "cond_a", "edge_a", "cond_b", "edge_b"}
            assert all(len(v) >= 20 for v in copy.values())
            assert copy["cond_a"] != copy["cond_b"]
            assert not any(re.search(r"[$₩]\s?\d|\d+\s?%\s*(off|할인)", v) for v in copy.values()), "no store prices"
        assert not any(HANGUL.search(v) for v in p["en"].values())
    assert cats >= {"keyboards", "powerbanks", "chargers", "minipc", "hubs", "controllers", "mice", "storage"}


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_vs_pages_answer_with_two_conditional_winners(built, approved, lang):
    dist, base = built["dist"], built["base"]
    by_id = {it["id"]: it for it in approved}
    index = read(dist / lang / "vs" / "index.html")
    assert index.count('class="sheet vs-card"') == 15
    for pair in VS_PAIRS:
        page = read(dist / lang / "vs" / pair["slug"] / "index.html")
        name_a, name_b = VS_NAMES[pair["a"]], VS_NAMES[pair["b"]]
        assert f'hreflang="ko" href="{base}/ko/vs/{pair["slug"]}/"' in page
        assert f'hreflang="en" href="{base}/en/vs/{pair["slug"]}/"' in page
        if lang == "ko":
            heads = [f"이 조건이면 무조건 <em>{n}</em>" for n in (name_a, name_b)]
            buttons, cons_h = ("쿠팡 현재가", "알리 직구"), "치명적 단점 맞대결"
        else:
            heads = [f"Pick <em>{n}</em> Without Hesitation If…" for n in (name_a, name_b)]
            buttons, cons_h = ("Amazon US", "AliExpress Direct"), "Critical Real-World Drawbacks, Side by Side"
        body = page.split("<main", 1)[1]
        order = [body.index("<h1>"), body.index('class="sheet vs-stage"'), body.index(heads[0]),
                 body.index(heads[1]), body.index('class="spec-table vs-table"'), body.index(cons_h),
                 body.index("tools/ali-promo-calculator/\">")]
        assert order == sorted(order), "H1 -> plates -> winner A -> winner B -> spec table -> drawbacks -> calculator"
        picks = body.split('<article class="sheet vs-pick">')[1:]
        assert len(picks) == 2
        for pick, item_id in zip(picks, (pair["a"], pair["b"])):
            card = pick.split("</article>", 1)[0]
            assert card.count('rel="nofollow sponsored noopener"') == 2
            assert f">{buttons[0]} <" in card.replace('<span class="sdot"></span>', "") and buttons[1] in card
            assert 'class="vs-cond"' in card and 'class="vs-edge"' in card and 'class="anchor"' in card
            links = by_id[item_id]["affiliate_links"]
            dom = links["coupang" if lang == "ko" else "amazon"].replace("&", "&amp;")
            assert dom in card and links["aliexpress"].replace("&", "&amp;") in card
        assert pair[lang]["cond_a"].replace("'", "&#x27;") in body and pair[lang]["cond_b"].replace("'", "&#x27;") in body
        cons_block = body.split(cons_h, 1)[1]
        assert by_id[pair["a"]][lang]["cons"][0].replace("'", "&#x27;").replace('"', "&quot;").replace("&", "&amp;") in cons_block \
            or by_id[pair["a"]][lang]["cons"][0][:20] in cons_block
        assert ("제조사 출시 참고가 (MSRP)" if lang == "ko" else "Manufacturer Reference MSRP") in body


def test_participating_products_link_to_their_rival_battle(built, approved):
    dist = built["dist"]
    rivals = rivals_by_product(active_pairs({it["id"]: it for it in approved}))
    assert len(rivals) == len(VS_NAMES)
    for pid, pairs in rivals.items():
        ko = read(dist / "ko" / "p" / product_slug(pid) / "index.html")
        en = read(dist / "en" / "p" / product_slug(pid) / "index.html")
        assert "이 모델과 가장 많이 비교하는 라이벌" in ko and "Most-compared rival for this model" in en
        assert f'href="../../vs/{pairs[0]["slug"]}/"' in ko and f'href="../../vs/{pairs[0]["slug"]}/"' in en
    outsider = next(it for it in approved if it["id"] not in rivals)
    assert "가장 많이 비교하는 라이벌" not in read(dist / "ko" / "p" / product_slug(outsider["id"]) / "index.html")
