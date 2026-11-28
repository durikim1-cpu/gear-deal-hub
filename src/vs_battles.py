"""Top-15 real-search rival head-to-head pages (/ko/vs/, /en/vs/ and one page per pair, per language).

Every page answers within seconds: two conditional winner cards sit directly under the side-by-side plates
("pick A without hesitation if ...", "pick B without hesitation if ..."), each with both store buttons.
Below that: a spec + manufacturer reference MSRP table, the critical drawbacks of both models side by side,
and the promo calculator entry. No store prices are rendered; MSRP is a launch reference only.
"""

from __future__ import annotations

import html
from types import SimpleNamespace

from src.affiliate import BUTTON_DISCLOSURE_EN, BUTTON_DISCLOSURE_KO
from src.vs_pairs import VS_PAIRS

# Short, search-facing display names for the models that take part in a battle.
VS_NAMES: dict[str, str] = {
    "aula-f75-wireless-keyboard": "AULA F75",
    "wobkey-rainy-75-alu": "WOBKEY Rainy 75",
    "monsgeek-m1-v5-via-alu": "MonsGeek M1 V5",
    "nuphy-air75-v2-lowprofile": "NuPhy Air75 V2",
    "lofree-flow84-lowprofile": "Lofree Flow 84",
    "anker-prime-20000-200w": "Anker Prime 20,000mAh 200W",
    "cuktech-20-powerbank-25000-210w": "CUKTECH 20 (25,000mAh 210W)",
    "anker-737-powercore-24k-140w": "Anker 737 PowerCore 24K",
    "sharge-shargeek-170": "SHARGE Shargeek 170",
    "baseus-blade-hd-100w": "Baseus Blade HD 100W",
    "ugreen-nexode-powerbank-20000-130w": "UGREEN Nexode 20,000mAh 130W",
    "ugreen-nexode-100w-4port": "UGREEN Nexode 100W",
    "anker-prime-100w-a2688": "Anker Prime 100W",
    "ugreen-nexode-pro-160w": "UGREEN Nexode Pro 160W",
    "cuktech-15-gan-140w-charger": "CUKTECH 15 GaN 140W",
    "beelink-ser8-8745hs-minipc": "Beelink SER8",
    "gmktec-nucbox-k8-plus": "GMKtec K8 Plus",
    "beelink-mini-s12-pro-n100": "Beelink S12 Pro (N100)",
    "gmktec-nucbox-g3-plus-n150": "GMKtec G3 Plus (N150)",
    "ugreen-revodok-pro-209-dock": "UGREEN Revodok Pro 209",
    "caldigit-ts4-thunderbolt4-dock": "CalDigit TS4",
    "satechi-usb4-slim-nvme-pro": "Satechi USB4 NVMe Pro",
    "orico-m2pjm-usb4-40gbps-enclosure": "ORICO USB4 40Gbps",
    "8bitdo-ultimate-2c-wireless": "8BitDo Ultimate 2C",
    "gamesir-cyclone-2-tmr-dock": "GameSir Cyclone 2",
    "vxe-dragonfly-r1-pro-max": "VXE R1 Pro Max",
    "atk-blazing-sky-f1-pro": "ATK F1 Pro",
    "samsung-t7-shield-2tb": "Samsung T7 Shield",
    "crucial-x9-pro-2tb-ssd": "Crucial X9 Pro",
}

_T = {
    "ko": {
        "home": "홈",
        "vs": "1:1 대결",
        "crumb_aria": "이동 경로",
        "index_title": "1:1 라이벌 대결 {n}선: 조건별 승자 즉답 | {brand}",
        "index_desc": "가장 많이 비교하는 동급 라이벌 {n}쌍을 조건별 승자로 바로 정리했습니다. 스펙·출시 참고가 비교표, 치명적 단점 맞대결, 쿠팡·알리 판매처 확인까지 한 페이지에서 끝냅니다.",
        "index_h1": "1:1 라이벌 대결: 조건별 승자 즉답",
        "index_dek": "'둘 다 좋다'로 끝내지 않습니다. 각 대결은 어떤 조건이면 어느 모델을 사야 하는지 두 문장으로 먼저 답하고, 스펙 비교표와 치명적 단점을 그 아래에 둡니다.",
        "index_meta": "동급 라이벌 {n}쌍 · 정적 가격 미보관",
        "card_meta": "{cat} · 조건별 승자 2개",
        "title": "{a} vs {b} 비교: 조건별 승자 즉답 (스펙·단점·출시 참고가) | {brand}",
        "h1": "{a} vs {b}: 조건별 승자 즉답",
        "pick_h": "이 조건이면 무조건 <em>{name}</em>",
        "edge": "결정적 우위",
        "btn_dom": "쿠팡 현재가",
        "btn_ali": "알리 직구",
        "table_h": "스펙·출시 참고가 비교표",
        "table_aria": "스펙 및 출시 참고가 비교표",
        "th_item": "항목",
        "row_cat": "분류",
        "row_msrp": "제조사 출시 참고가 (MSRP)",
        "msrp_note": "제조사 공식 사양 참고치이며 실제 쇼핑몰 판매가·할인 기준가가 아닙니다. 확인일 {date}.",
        "row_reviewed": "스펙 검수일",
        "cons_h": "치명적 단점 맞대결",
        "more_h": "상세 스펙과 다른 대결",
        "detail": "{name} 상세 스펙·통관 기준",
        "other": "다른 대결: {a} vs {b}",
        "all": "전체 대결 {n}선 보기",
        "disc": BUTTON_DISCLOSURE_KO,
        "switch": "English page",
        "stage_aria": "대결 모델",
    },
    "en": {
        "home": "Home",
        "vs": "VS Battles",
        "crumb_aria": "Breadcrumb",
        "index_title": "{n} Head-to-Head VS Battles: The Winner for Your Setup | {brand}",
        "index_desc": "The {n} most-compared same-class rivals, each settled by a concrete buyer condition, with spec and reference-MSRP tables, critical drawbacks, and Amazon US vs AliExpress store checks.",
        "index_h1": "Head-to-Head VS Battles: The Winner for Your Setup",
        "index_dek": "No fence-sitting. Each battle first states, in two sentences, which model to pick under which condition, then backs it with the spec table and both models' critical drawbacks.",
        "index_meta": "{n} same-class rivalries · Zero stale prices",
        "card_meta": "{cat} · 2 conditional winners",
        "title": "{a} vs {b}: Which to Buy, Decided by Your Setup | {brand}",
        "h1": "{a} vs {b}: The Winner for Your Setup",
        "pick_h": "Pick <em>{name}</em> Without Hesitation If…",
        "edge": "Decisive edge",
        "btn_dom": "Amazon US",
        "btn_ali": "AliExpress Direct",
        "table_h": "Spec & Reference MSRP Comparison",
        "table_aria": "Spec and reference MSRP comparison",
        "th_item": "Item",
        "row_cat": "Category",
        "row_msrp": "Manufacturer Reference MSRP",
        "msrp_note": "Manufacturer launch reference, not a current store price. Checked {date}.",
        "row_reviewed": "Specs reviewed",
        "cons_h": "Critical Real-World Drawbacks, Side by Side",
        "more_h": "Full Specs and More Battles",
        "detail": "{name} full specs & caveats",
        "other": "More battles: {a} vs {b}",
        "all": "See all {n} battles",
        "disc": BUTTON_DISCLOSURE_EN,
        "switch": "한국어 페이지",
        "stage_aria": "Models in this battle",
    },
}


def _esc(val: object) -> str:
    return html.escape(str(val))


def vs_name(pid: str, item: dict) -> str:
    return VS_NAMES.get(pid) or f"{item['brand'].strip()} {item['model'].split('(')[0].strip()}"


def active_pairs(items_by_id: dict[str, dict]) -> list[dict]:
    """Battles whose two models both passed the Gatekeeper in this build."""
    return [p for p in VS_PAIRS if p["a"] in items_by_id and p["b"] in items_by_id]


def rivals_by_product(pairs: list[dict]) -> dict[str, list[dict]]:
    """Map each participating product id to the battles it appears in (declaration order)."""
    out: dict[str, list[dict]] = {}
    for p in pairs:
        out.setdefault(p["a"], []).append(p)
        out.setdefault(p["b"], []).append(p)
    return out


def pair_title(pair: dict, items_by_id: dict[str, dict]) -> str:
    return f"{vs_name(pair['a'], items_by_id[pair['a']])} vs {vs_name(pair['b'], items_by_id[pair['b']])}"


def render_vs_index(*, lang: str, pairs: list[dict], items_by_id: dict[str, dict], cfg: dict, ui: SimpleNamespace) -> str:
    t = _T[lang]
    up = "../../"
    other = "en" if lang == "ko" else "ko"
    n = len(pairs)
    brand = cfg["site"]["brand_name"]

    groups: dict[str, list[dict]] = {}
    for p in pairs:
        groups.setdefault(items_by_id[p["a"]]["category"], []).append(p)

    def card(p: dict) -> str:
        a, b = items_by_id[p["a"]], items_by_id[p["b"]]
        meta = t["card_meta"].format(cat=ui.cat_label(a["category"], lang))
        return (
            f'<article class="sheet vs-card">'
            f'<span class="gc-plates" aria-hidden="true">{ui.plate(a, up)}{ui.plate(b, up)}</span>'
            f'<div class="vs-card-txt"><h3><a href="{_esc(p["slug"])}/">{_esc(pair_title(p, items_by_id))}</a></h3>'
            f'<p>{_esc(p[lang]["dek"])}</p><span class="gc-meta">{_esc(meta)}</span></div>'
            f'</article>'
        )

    sections = "".join(
        f'<section class="guide-group"><h2>{_esc(ui.cat_label(cat, lang))}</h2>'
        f'<div class="vs-list">{"".join(card(p) for p in ps)}</div></section>'
        for cat, ps in groups.items()
    )

    body = f"""
<body class="{lang}">
  {ui.legal(lang)}
  {ui.header(lang, up, cfg, f"{up}{other}/vs/")}
  <main class="wrap">
    <nav aria-label="{t['crumb_aria']}"><ol class="crumbs"><li><a href="../">{t['home']}</a></li><li> / </li><li aria-current="page">{t['vs']}</li></ol></nav>
    <header class="page-head">
      <h1>{_esc(t['index_h1'])}</h1>
      <p class="dek">{_esc(t['index_dek'])}</p>
      <p class="page-meta">{_esc(t['index_meta'].format(n=n))}</p>
    </header>
    {sections}
    {ui.tool_strip("promo", lang, "../tools/ali-promo-calculator/")}
  </main>
  {ui.footer(lang, up, cfg)}
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    return ui.head(
        lang=lang, title=t["index_title"].format(n=n, brand=brand), description=t["index_desc"].format(n=n),
        up=up, cfg=cfg, path=f"/{lang}/vs/", alternates={"ko": "/ko/vs/", "en": "/en/vs/"},
    ) + body


def render_vs_detail(*, lang: str, pair: dict, pairs: list[dict], items_by_id: dict[str, dict], cfg: dict,
                     ui: SimpleNamespace) -> str:
    t = _T[lang]
    up = "../../../"
    other = "en" if lang == "ko" else "ko"
    slug = pair["slug"]
    a, b = items_by_id[pair["a"]], items_by_id[pair["b"]]
    name_a, name_b = vs_name(pair["a"], a), vs_name(pair["b"], b)
    copy = pair[lang]
    brand = cfg["site"]["brand_name"]
    calc_base = "../../tools/ali-promo-calculator/"

    def side(it: dict, name: str) -> str:
        href = f"../../p/{ui.slug(it['id'])}/"
        return (
            f'<div class="vs-side">{ui.plate(it, up, href=href, eager=True)}'
            f'<p class="vs-name"><strong>{_esc(name)}</strong>'
            f'<span class="desig">{_esc(it["brand"].strip())} · {_esc(ui.cat_label(it["category"], lang))}</span></p></div>'
        )

    def pick(it: dict, name: str, cond: str, edge: str) -> str:
        d = ui.profile(it, lang)
        dom_first = not d["direct_pick"]
        rel = 'target="_blank" rel="nofollow sponsored noopener"'
        return f"""
      <article class="sheet vs-pick">
        <h2>{t['pick_h'].format(name=_esc(name))}</h2>
        <p class="vs-cond">{_esc(cond)}</p>
        <p class="vs-edge"><strong>{t['edge']}</strong>{_esc(edge)}</p>
        <div class="vs-buy">
          {ui.live(it, lang)}
          {ui.anchor(it, lang, calc_base)}
          <div class="actions">
            <a class="btn btn-{d['dom_key']}{' is-first' if dom_first else ''}" data-aff="dom" data-store="{d['dom_store_id']}" href="{_esc(d['dom_url'])}" {rel} aria-label="{t['btn_dom']} · {_esc(name)}"><span class="sdot"></span>{t['btn_dom']} {ui.icon('out', 15)}</a>
            <a class="btn btn-ali{'' if dom_first else ' is-first'}" data-aff="ali" data-store="aliexpress" href="{_esc(d['ali_url'])}" {rel} aria-label="{t['btn_ali']} · {_esc(name)}"><span class="sdot"></span>{t['btn_ali']} {ui.icon('out', 15)}</a>
          </div>
        </div>
      </article>"""

    specs_a, specs_b = ui.specs(a, lang), ui.specs(b, lang)
    keys = list(specs_a) + [k for k in specs_b if k not in specs_a]
    dash = "—"
    rows = [
        f'<tr><th scope="row">{_esc(t["row_cat"])}</th><td>{_esc(ui.cat_label(a["category"], lang))}</td>'
        f'<td>{_esc(ui.cat_label(b["category"], lang))}</td></tr>'
    ]
    rows += [
        f'<tr><th scope="row">{_esc(ui.spec_label(k, lang))}</th><td>{_esc(specs_a.get(k, dash))}</td>'
        f'<td>{_esc(specs_b.get(k, dash))}</td></tr>'
        for k in keys
    ]

    def msrp(it: dict) -> str:
        if lang == "ko":
            return f'{int(it["msrp_krw"]):,}원' if it.get("msrp_krw") else dash
        return f'USD {float(it["msrp_usd"]):,.2f}' if it.get("msrp_usd") else dash

    checked = max(a.get("msrp_checked_at", ""), b.get("msrp_checked_at", "")) or "2026-11-26"
    rows.append(
        f'<tr class="msrp-ref"><th scope="row">{_esc(t["row_msrp"])}</th><td class="num">{msrp(a)}</td>'
        f'<td class="num">{msrp(b)}</td></tr>'
    )
    rows.append(
        f'<tr><th scope="row">{_esc(t["row_reviewed"])}</th><td class="num">{_esc(a.get("updated_at", dash))}</td>'
        f'<td class="num">{_esc(b.get("updated_at", dash))}</td></tr>'
    )

    def cons(it: dict, name: str) -> str:
        lis = "".join(f"<li>{_esc(x)}</li>" for x in it[lang].get("cons", []))
        return f'<div class="panel cons"><h3>{_esc(name)}</h3><ul>{lis}</ul></div>'

    arrow = ui.icon("arrow", 14)
    related = [p for p in pairs if p["slug"] != slug and ({p["a"], p["b"]} & {pair["a"], pair["b"]})]
    related += [p for p in pairs if p["slug"] != slug and p not in related
                and items_by_id[p["a"]]["category"] == a["category"]]
    more = [
        f'<li><a class="text-link" href="../../p/{ui.slug(it["id"])}/">{_esc(t["detail"].format(name=nm))} {arrow}</a></li>'
        for it, nm in ((a, name_a), (b, name_b))
    ]
    for p in related[:3]:
        pa, pb = vs_name(p["a"], items_by_id[p["a"]]), vs_name(p["b"], items_by_id[p["b"]])
        more.append(f'<li><a class="text-link" href="../{_esc(p["slug"])}/">{_esc(t["other"].format(a=pa, b=pb))} {arrow}</a></li>')
    more.append(f'<li><a class="text-link" href="../">{_esc(t["all"].format(n=len(pairs)))} {arrow}</a></li>')

    body = f"""
<body class="{lang}">
  {ui.legal(lang)}
  {ui.header(lang, up, cfg, f"{up}{other}/vs/{slug}/")}
  <main class="wrap vs-page">
    <nav aria-label="{t['crumb_aria']}">
      <ol class="crumbs">
        <li><a href="../../">{t['home']}</a></li><li> / </li>
        <li><a href="../">{t['vs']}</a></li><li> / </li>
        <li aria-current="page">{_esc(name_a)} vs {_esc(name_b)}</li>
      </ol>
    </nav>
    <header class="page-head">
      <h1>{_esc(t['h1'].format(a=name_a, b=name_b))}</h1>
      <p class="dek">{_esc(copy['dek'])}</p>
    </header>

    <div class="sheet vs-stage" role="group" aria-label="{t['stage_aria']}">
      {side(a, name_a)}
      {side(b, name_b)}
      <span class="vs-mark" aria-hidden="true">VS</span>
    </div>

    <div class="vs-verdicts">
      {pick(a, name_a, copy['cond_a'], copy['edge_a'])}
      {pick(b, name_b, copy['cond_b'], copy['edge_b'])}
    </div>
    <p class="btn-disc">{_esc(t['disc'])}</p>

    <section class="section" aria-labelledby="vs-spec">
      <h2 id="vs-spec">{_esc(t['table_h'])}</h2>
      <div class="table-sheet table-scroll" tabindex="0" role="region" aria-label="{t['table_aria']}">
        <table class="spec-table vs-table">
          <thead><tr><th scope="col">{_esc(t['th_item'])}</th><th scope="col">{_esc(name_a)}</th><th scope="col">{_esc(name_b)}</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
      <p class="table-note">{_esc(t['msrp_note'].format(date=checked))}</p>
    </section>

    <section class="section" aria-labelledby="vs-cons">
      <h2 id="vs-cons">{_esc(t['cons_h'])}</h2>
      <div class="pc">{cons(a, name_a)}{cons(b, name_b)}</div>
    </section>

    {ui.tool_strip("promo", lang, calc_base)}

    <section class="section" aria-labelledby="vs-more">
      <h2 id="vs-more">{_esc(t['more_h'])}</h2>
      <ul class="link-list">{''.join(more)}</ul>
    </section>
  </main>
  {ui.footer(lang, up, cfg)}
  <script src="{up}assets/app.js" defer></script>
</body>
</html>
"""
    og = ui.og_image(a)
    return ui.head(
        lang=lang, title=t["title"].format(a=name_a, b=name_b, brand=brand), description=copy["dek"], up=up, cfg=cfg,
        path=f"/{lang}/vs/{slug}/", alternates={"ko": f"/ko/vs/{slug}/", "en": f"/en/vs/{slug}/"}, og_image=og,
    ) + body
