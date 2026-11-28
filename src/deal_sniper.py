"""Promo-code & deal-signal sniper with idempotency keys, Amazon price-tracking exclusion,
and the Tier-1 community deal-benchmark harvester behind data/live_offers_cache.json.

Implements Topic 1 & Topic 3 Consensus:
- Never tracks or alerts on Amazon price drops unless separate written approval is explicitly enabled.
- Generates deterministic `event_id` idempotency keys so retries never send duplicate notifications.
- Distinguishes genuine `live_matched` promo/signal events from local preview samples (zero daily spam).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.collector import GLOBAL_BRANDS, parse_krw_price, parse_usd_price

AMAZON_SIGNAL_RE = re.compile(r"\b(?:amazon|amzn\.(?:to|com)|a\.co)\b|아마존", re.IGNORECASE)
DEAL_SOURCES = {"reddit/buildapcsales", "ppomppu_kr", "ppomppu_global"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", s.lower())


def _is_amazon_signal(signal: dict) -> bool:
    return any(AMAZON_SIGNAL_RE.search(signal.get(field) or "") for field in ("title", "url", "destination_url"))


def load_sent_history(data_dir: Path, cooldown_days: int = 30) -> dict[str, dict]:
    path = data_dir / "sent_deals_history.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=cooldown_days)).strftime("%Y-%m-%d")
    if not isinstance(raw, dict):
        return {}
    return {
        key: row for key, row in raw.items()
        if isinstance(row, dict) and isinstance(row.get("sent_date"), str) and row["sent_date"] >= cutoff
    }


def save_sent_history(data_dir: Path, history: dict[str, dict]) -> None:
    path = data_dir / "sent_deals_history.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _make_event_id(lang: str, product_id: str, promo_code: str | None, date_str: str) -> str:
    seed = f"{lang}:{product_id}:{promo_code or 'signal'}:{date_str}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:14]


def snipe_hot_deals(
    approved_items: list[dict],
    live_signals: list[dict],
    data_dir: Path,
    cfg: dict | None = None,
    max_picks: int = 2,
) -> dict:
    """Match community deal prices and promo codes to vetted products with idempotency keys."""
    cfg = cfg or {}
    allow_amazon_tracking = bool(cfg.get("affiliate", {}).get("allow_amazon_price_tracking", False))
    min_ratio = float(cfg.get("gatekeeper", {}).get("min_price_ratio_vs_msrp", 0.35))
    history = load_sent_history(data_dir, cooldown_days=14)
    now_utc = datetime.now(timezone.utc)
    observed_at = now_utc.strftime("%Y-%m-%d %H:%M UTC")

    signal_matches: dict[str, dict] = {}
    for sig in live_signals:
        title = sig.get("title") or ""
        # Amazon Operating Policies §5: never run unauthorized Amazon price-drop/tracking alerts.
        if not allow_amazon_tracking and _is_amazon_signal(sig):
            continue

        source = sig.get("source", "")
        published = _signal_time(sig, now_utc)
        if now_utc >= published + timedelta(hours=COMMUNITY_TTL_HOURS):
            continue
        code_m = _BOARD_CODE_RE.search(title)
        promo_code = code_m.group(1) if code_m else None
        prices = {"usd": parse_usd_price(title), "krw": parse_krw_price(title)} if source in DEAL_SOURCES else {}
        if not promo_code and not any(prices.values()):
            continue

        item = match_signal_to_product(title, approved_items)
        if item is None:
            continue
        if any(prices.values()) and not any(
            price_passes_msrp_floor(price, float(item.get(f"msrp_{currency}") or 0), min_ratio)
            for currency, price in prices.items() if price is not None
        ):
            continue
        previous = signal_matches.get(item["id"])
        if previous is None or (bool(promo_code), published) > (bool(previous["promo_code"]), previous["published"]):
            signal_matches[item["id"]] = {
                "promo_code": promo_code,
                "signal_title": title,
                "signal_source": source,
                "published": published,
            }

    def build_live_picks(lang: str) -> list[dict]:
        picks: list[dict] = []
        for it in approved_items:
            pid = it["id"]
            if pid not in signal_matches:
                continue
            sig_info = signal_matches[pid]
            published = sig_info["published"]
            event_id = _make_event_id(lang, pid, sig_info.get("promo_code"), published.strftime("%Y-%m-%d"))
            if f"event:{event_id}" in history:
                continue
            prev = history.get(f"{lang}:{pid}")
            if prev and not (sig_info.get("promo_code") and sig_info.get("promo_code") != prev.get("promo_code")):
                continue
            entry = dict(it)
            entry["sniper"] = {
                "event_id": event_id,
                "promo_code": sig_info.get("promo_code"),
                "signal_title": sig_info.get("signal_title"),
                "signal_source": sig_info.get("signal_source"),
                "observed_at": published.strftime("%Y-%m-%d %H:%M UTC"),
                "expires_at": (published + timedelta(hours=COMMUNITY_TTL_HOURS)).isoformat(),
                "live_matched": True,
            }
            picks.append(entry)
            if len(picks) >= max_picks:
                break
        return picks

    ko_live = build_live_picks("ko")
    en_live = build_live_picks("en")

    # Local dry-run preview sample (never auto-sent unless live_matched is True)
    preview_ko = ko_live or [
        dict(it, sniper={"event_id": "preview", "promo_code": None, "observed_at": observed_at, "live_matched": False})
        for it in approved_items[:2]
    ]
    preview_en = en_live or [
        dict(it, sniper={"event_id": "preview", "promo_code": None, "observed_at": observed_at, "live_matched": False})
        for it in approved_items[:2]
    ]

    return {
        "ko_picks": ko_live,
        "en_picks": en_live,
        "preview_ko": preview_ko,
        "preview_en": preview_en,
        "live_signal_matches": len(signal_matches),
        "observed_at": observed_at,
    }


# --------------------------------------------------------------------------------------
# Live offer cache (data/live_offers_cache.json)
#
# Tier 1 - community_benchmark: a deal price spotted in a public Reddit / Ppomppu post title.
#   It is a benchmark someone reported, never a store quote, so pages must label it as such
#   and hide it once `expires_at` (observed_at + 48h) passes.
# Tier 2 - ali_official_api: a sale price returned by the AliExpress Open Platform API
#   (src/ali_api.py) when ALIEXPRESS_APP_KEY / ALIEXPRESS_APP_SECRET are configured.
# Both tiers refuse any price below `min_price_ratio_vs_msrp` (default 0.35) of the
# manufacturer reference MSRP, which is what blocks "$2.99" cable/option listing traps.
# --------------------------------------------------------------------------------------

LIVE_OFFERS_FILE = "live_offers_cache.json"
COMMUNITY_TTL_HOURS = 48
MAX_PRICE_RATIO_VS_MSRP = 1.6

_ACCESSORY_RE = re.compile(
    r"(\bcase\b|\bcover\b|\bkeycaps?\b|\bswitch(?:es)? only\b|\bcable only\b|\bpouch\b|\bskin\b|\bscreen protector\b|"
    r"\bstand only\b|\breplacement\b|\bparts?\b|케이스|키캡|파우치|보호필름|커버|스킨|단품|교체용|부품)",
    re.IGNORECASE,
)
_PRICE_TEXT_RE = re.compile(r"(?:US\s?)?\$\s?[\d,]+(?:\.\d+)?|\d[\d,]*\s*원")
_ALI_CONTEXT_RE = re.compile(r"(알리|aliexpress|ali\s?express|\bali\b)", re.IGNORECASE)
# Board-grade promo token: must sit right after a code keyword, be upper-case in the source text,
# and mix letters with digits (so "CODE WORKS" or "COUPON STACK" can never be shown as a code).
_BOARD_CODE_RE = re.compile(
    r"(?:할인\s*코드|프로모션\s*코드|쿠폰\s*코드|코드|[Cc]ode|CODE|[Cc]oupon|COUPON|[Pp]romo|PROMO)\s*[:：=]?\s*"
    r"\b((?=[A-Z0-9]*\d)(?=[A-Z0-9]*[A-Z])[A-Z0-9]{5,12})\b"
)

# Descriptor words that never identify a specific model. STOP words end the core-token scan once a
# usable core exists; SKIP words (CPU vendors, series prefixes) are stepped over without ending it.
_MODEL_STOPWORDS = frozenset(
    """wireless wired mechanical keyboard gasket tri mode gan charger wall desktop power bank usb c a type
    portable ssd docking station dock hub controller mouse gaming microphone dynamic podcast studio broadcast
    pc with and the for in of to low profile qmk via zmk cnc aluminum alu compact slim
    ultra thin port ports laptop led screen light bar monitor computer earbuds earphones headphones anc
    noise canceling adaptive hybrid ear enclosure nvme m2 magsafe thunderbolt hall effect
    sticks trigger lock edition mobile pass through charging ergonomic vertical quiet performance
    symmetrical ultralight hot swappable switch one handed photo video editing sensor webcam ai dual mic
    key keys macro deck side status adjustable slot stand numpad rapid disassembly scissor hd pd tmr
    transparent lcd infobar touch points lossless ldac aptx 1dd 3ba dsp iem xlr 4k 8k ready sony
    industry leading 30k focus hero polling update kailh pom oculink g dram equipped
    tool free cooling asymmetric razer chroma matter rgb backlight""".split()
)
_MODEL_SKIPWORDS = frozenset(
    "ryzen intel amd core twin lake alder nucbox mini venus anker soundcore ampligame smartcam dragonfly "
    "blazing sky usb4 40gbps 20gbps 10gbps inch gen".split()
)
_VARIANT_TOKENS = frozenset("pro max plus ultra mini lite se he v2 v3 v4 v5 ii iii 2 3".split())
_COUNT_SUFFIXES = frozenset("port ports in key keys x slot pack".split())
_CAPACITY_RE = re.compile(r"^\d+(?:tb|gb)$")
_SKU_TOKEN_RE = re.compile(r"^(?!ra\d+$)[a-z][a-z0-9]{3,}$")

_CATEGORY_WORDS: dict[str, tuple[str, ...]] = {
    "chargers": ("charger", "충전기", "gan", "charging station"),
    "powerbanks": ("power bank", "powerbank", "보조배터리", "mah"),
    "keyboards": ("keyboard", "키보드"),
    "mice": ("mouse", "마우스"),
    "minipc": ("mini pc", "minipc", "미니pc", "미니 pc", "nucbox"),
    "storage": ("ssd",),
    "hubs": ("dock", "hub", "허브", "도킹", "enclosure", "인클로저", "외장케이스"),
    "controllers": ("controller", "gamepad", "컨트롤러", "패드"),
    "audio": ("mic", "마이크", "earbud", "이어폰", "headphone", "헤드폰", "iem", "earphone"),
    "lighting": ("light bar", "lightbar", "라이트바", "스크린바", "조명"),
    "productivity": ("stream deck", "스트림덱", "webcam", "웹캠", "laptop stand", "거치대", "tourbox", "macro"),
}


def _tokens(text: str) -> list[str]:
    """Lower-case alphanumeric tokens; thousands separators, intra-model dots and "2.4G" radio labels are normalised."""
    t = re.sub(r"(?<![0-9.])2\.4\s?g(?:hz)?(?![a-z0-9])", " ", text.lower())
    t = re.sub(r"(?<![0-9])[0-9]/[0-9](?:-inch)?", " ", t)
    t = re.sub(r"(?<=\d),(?=\d{3})", "", t)
    t = re.sub(r"(?<=[a-z])\.(?=\d)", "", t)
    return re.findall(r"[a-z0-9]+", t)


def _is_mixed(tok: str) -> bool:
    return bool(re.search(r"[a-z]", tok) and re.search(r"\d", tok))


def _brand_aliases(brand: str) -> set[str]:
    canon = brand.strip().lower()
    aliases = {_norm(brand)}
    for kw, (canon_brand, _cat) in GLOBAL_BRANDS.items():
        if canon_brand.lower() == canon:
            aliases.add(_norm(kw))
    return {a for a in aliases if a}


def _core_tokens(plain_tail: str) -> list[str]:
    """Leading identifying tokens of a model name, e.g. "F75", "Nexode Pro 160W", "PRO X SUPERLIGHT 2"."""
    toks = _tokens(plain_tail)
    core: list[str] = []
    last_idx = -2
    for i, tok in enumerate(toks):
        if tok in _MODEL_SKIPWORDS or _CAPACITY_RE.match(tok):
            continue
        if tok in _MODEL_STOPWORDS:
            if core and (len(core) >= 2 or any(_is_mixed(c) for c in core)):
                break
            continue
        if len(core) >= 3:
            # A full core still absorbs a directly attached generation/variant marker ("... SUPERLIGHT 2").
            if tok in _VARIANT_TOKENS and i == last_idx + 1:
                core.append(tok)
                last_idx = i
                continue
            break
        if tok.isdigit():
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if len(tok) == 1 and (i != last_idx + 1 or nxt in _COUNT_SUFFIXES):
                continue  # "4-Port", "7-in-1", "Ryzen 7"
            if len(tok) < 3 and any(_is_mixed(c) for c in core) and i == last_idx + 1 and len(tok) == 2:
                continue  # "F75 75%"
        core.append(tok)
        last_idx = i
    if len(core) == 1 and not ((_is_mixed(core[0]) and len(core[0]) >= 2) or (core[0].isdigit() and len(core[0]) >= 3)):
        return []
    return core


def model_signature(item: dict) -> dict:
    """Deterministic match signature for a catalog model: SKU, core tokens, capacity tokens, own variant words."""
    brand = item["brand"].strip()
    model = item["model"].strip()
    tail = model[len(brand):].strip() if model.lower().startswith(brand.lower()) else model
    skus = []
    for group in re.findall(r"\(([^)]*)\)", model):
        for part in re.split(r"[,/]", group):
            sq = re.sub(r"[^a-z0-9]", "", part.lower())
            if " " not in part.strip() and _is_mixed(sq) and _SKU_TOKEN_RE.match(sq):
                skus.append(sq)
    core = _core_tokens(re.sub(r"\([^)]*\)", " ", tail))
    return {
        "brand_aliases": _brand_aliases(brand),
        "skus": skus,
        "core": core,
        # A one-token core shorter than 3 chars ("T9") is only trusted next to its own category word.
        "strict_cat": len(core) == 1 and len(core[0]) < 3,
        "capacity": [t for t in _tokens(model) if _CAPACITY_RE.match(t)][-1:],
        "own_tokens": set(_tokens(model)),
    }


def match_signal_to_product(title: str, items: list[dict]) -> dict | None:
    """Return the single catalog model a deal title unambiguously refers to, or None.

    Precision over recall: accessory listings, sibling variants ("F75 Pro"), other capacities,
    cross-category titles and ties between two catalog models all return None.
    """
    if not title or _ACCESSORY_RE.search(title):
        return None
    title = _PRICE_TEXT_RE.sub(" ", title)
    low = title.lower()
    squashed = re.sub(r"[^a-z0-9가-힣]", "", low)
    title_tokens = _tokens(title)
    token_set = set(title_tokens)
    best: list[tuple[int, dict]] = []
    for item in items:
        sig = model_signature(item)
        if not any(alias in squashed for alias in sig["brand_aliases"]):
            continue
        sku_hit = any(sku in squashed for sku in sig["skus"])
        core_hit = bool(sig["core"]) and all(tok in token_set for tok in sig["core"])
        if not (sku_hit or core_hit):
            continue
        if not sku_hit:
            # Sibling-variant guard: a variant word in the title that this model does not carry.
            if any(tok in _VARIANT_TOKENS and tok not in sig["own_tokens"] for tok in title_tokens):
                continue
            if sig["capacity"] and not all(tok in token_set for tok in sig["capacity"]):
                continue
            own_words = _CATEGORY_WORDS.get(item["category"], ())
            if not any(w in low for w in own_words):
                other = any(w in low for cat, ws in _CATEGORY_WORDS.items() if cat != item["category"] for w in ws)
                if other or sig["strict_cat"] or not any(_is_mixed(tok) for tok in sig["core"]):
                    continue
        score = (100 if sku_hit else 0) + len(sig["core"])
        best.append((score, item))
    if not best:
        return None
    best.sort(key=lambda x: -x[0])
    if len(best) > 1 and best[0][0] == best[1][0]:
        return None
    return best[0][1]


def _parse_iso(value: object) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _signal_time(signal: dict, now: datetime) -> datetime:
    published = _parse_iso(signal.get("published_at"))
    return min(now, published).astimezone(timezone.utc) if published else now


def is_active_deal(sniper: dict) -> bool:
    if not sniper.get("live_matched"):
        return False
    if "expires_at" not in sniper:
        return True  # Queues staged before expiration was recorded.
    expires = _parse_iso(sniper["expires_at"])
    return expires is not None and expires > datetime.now(timezone.utc)


def load_live_offers(data_dir: Path, now: datetime | None = None) -> dict:
    """Read the cache and drop every expired or malformed entry (fail-closed)."""
    now = now or datetime.now(timezone.utc)
    path = Path(data_dir) / LIVE_OFFERS_FILE
    empty: dict = {"updated_at": "", "offers": {}, "promo_codes": []}
    if not path.exists():
        return empty
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return empty
    if not isinstance(raw, dict):
        return empty

    def alive(entry: object) -> bool:
        if not isinstance(entry, dict):
            return False
        exp = _parse_iso(entry.get("expires_at", ""))
        return bool(exp and exp > now)

    def valid_offer(entry: object) -> bool:
        if not alive(entry):
            return False
        try:
            return entry.get("source_kind") in ("community_benchmark", "ali_official_api") and float(entry.get("price") or 0) > 0
        except (TypeError, ValueError):
            return False

    offers: dict[str, list[dict]] = {}
    for pid, entries in (raw.get("offers") or {}).items():
        kept = [e for e in entries if valid_offer(e)] if isinstance(entries, list) else []
        if kept:
            offers[pid] = kept
    codes = [c for c in (raw.get("promo_codes") or []) if alive(c) and c.get("code")]
    return {"updated_at": raw.get("updated_at", ""), "offers": offers, "promo_codes": codes}


def save_live_offers(data_dir: Path, cache: dict) -> None:
    path = Path(data_dir) / LIVE_OFFERS_FILE
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "offers": cache.get("offers", {}),
        "promo_codes": cache.get("promo_codes", []),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def price_passes_msrp_floor(price: float, msrp: float, min_ratio: float = 0.35,
                            max_ratio: float = MAX_PRICE_RATIO_VS_MSRP) -> bool:
    """True only when a price sits inside [min_ratio, max_ratio] x manufacturer reference MSRP."""
    if not (price and msrp) or price <= 0 or msrp <= 0:
        return False
    return msrp * min_ratio <= price <= msrp * max_ratio


def upsert_offer(cache: dict, product_id: str, entry: dict) -> None:
    """Insert or replace the (source_kind, currency) slot for a product.

    A community post that is still sitting in the hot feed keeps its first-seen timestamps,
    so one long-lived post can never extend its own 48h window.
    """
    slots = cache.setdefault("offers", {}).setdefault(product_id, [])
    for i, old in enumerate(slots):
        if old.get("source_kind") == entry["source_kind"] and old.get("currency") == entry["currency"]:
            if entry["source_kind"] == "community_benchmark":
                if old.get("signal_url") == entry.get("signal_url") or old.get("observed_at", "") > entry["observed_at"]:
                    return
            slots[i] = entry
            return
    slots.append(entry)


def harvest_community_benchmarks(
    approved_items: list[dict],
    live_signals: list[dict],
    data_dir: Path,
    cfg: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """Tier 1: parse USD/KRW deal prices from live community signals into live_offers_cache.json."""
    cfg = cfg or {}
    now = now or datetime.now(timezone.utc)
    min_ratio = float(cfg.get("gatekeeper", {}).get("min_price_ratio_vs_msrp", 0.35))
    allow_amazon = bool(cfg.get("affiliate", {}).get("allow_amazon_price_tracking", False))
    cache = load_live_offers(data_dir, now=now)
    stats = {"signals_scanned": len(live_signals), "matched": 0, "written": 0, "blocked_floor": 0, "codes_spotted": 0}
    known_codes = {c["code"] for c in cache["promo_codes"]}

    for sig in live_signals:
        title = (sig.get("title") or "").strip()
        url = sig.get("url", "") or ""
        if not title:
            continue
        # Amazon Operating Policies: never surface Amazon prices outside the official API.
        if not allow_amazon and _is_amazon_signal(sig):
            continue

        published = _signal_time(sig, now)
        expires_at = published + timedelta(hours=COMMUNITY_TTL_HOURS)
        if now >= expires_at:
            continue
        observed = published.isoformat(timespec="seconds")
        expires = expires_at.isoformat(timespec="seconds")

        code_m = _BOARD_CODE_RE.search(title)
        if code_m and _ALI_CONTEXT_RE.search(title) and code_m.group(1) not in known_codes:
            known_codes.add(code_m.group(1))
            cache["promo_codes"].append({
                "code": code_m.group(1),
                "source_kind": "community_spotted",
                "signal_source": sig.get("source", ""),
                "signal_url": url,
                "observed_at": observed,
                "expires_at": expires,
            })
            stats["codes_spotted"] += 1

        # Price benchmarks only come from dedicated deal boards: a "$499 worth it?"
        # discussion post on a hobby subreddit is not an observed deal price.
        if sig.get("source", "") not in DEAL_SOURCES:
            continue
        usd, krw = parse_usd_price(title), parse_krw_price(title)
        if usd is None and krw is None:
            continue
        item = match_signal_to_product(title, approved_items)
        if item is None:
            continue
        stats["matched"] += 1
        for currency, price, msrp, text in (
            ("USD", usd, float(item.get("msrp_usd") or 0), f"${usd:,.2f}" if usd is not None else ""),
            ("KRW", krw, float(item.get("msrp_krw") or 0), f"{krw:,}원" if krw is not None else ""),
        ):
            if price is None:
                continue
            if not price_passes_msrp_floor(float(price), msrp, min_ratio):
                stats["blocked_floor"] += 1
                continue
            upsert_offer(cache, item["id"], {
                "source_kind": "community_benchmark",
                "currency": currency,
                "price": float(price),
                "price_text": text,
                "observed_at": observed,
                "expires_at": expires,
                "signal_source": sig.get("source", ""),
                "signal_url": url,
                "signal_title": title[:160],
            })
            stats["written"] += 1

    cache["promo_codes"] = cache["promo_codes"][-12:]
    save_live_offers(data_dir, cache)
    stats["active_products"] = len(cache["offers"])
    return stats


def pick_live_offer(cache: dict | None, product_id: str, lang: str, now: datetime | None = None) -> dict | None:
    """Best unexpired offer to show for a product in a language: official API first, then community.

    English pages only ever show USD benchmarks; Korean pages prefer KRW and fall back to USD.
    """
    if not cache:
        return None
    now = now or datetime.now(timezone.utc)
    live = []
    for e in cache.get("offers", {}).get(product_id, []):
        exp = _parse_iso(e.get("expires_at", ""))
        if exp and exp > now:
            live.append(e)
    if not live:
        return None
    order = ["USD"] if lang == "en" else ["KRW", "USD"]
    for kind in ("ali_official_api", "community_benchmark"):
        for cur in order:
            for e in live:
                if e.get("source_kind") == kind and e.get("currency") == cur:
                    return e
    return None
