"""Zero-cost multi-source hardware deal & model-discovery collector (Reddit JSON + Korean RSS)."""

from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

REDDIT_FEEDS = [
    ("buildapcsales", "https://www.reddit.com/r/buildapcsales/hot.json?limit=25"),
    ("UsbCHardware", "https://www.reddit.com/r/UsbCHardware/hot.json?limit=20"),
    ("MiniPCs", "https://www.reddit.com/r/MiniPCs/hot.json?limit=20"),
    ("MechanicalKeyboards", "https://www.reddit.com/r/MechanicalKeyboards/hot.json?limit=20"),
    ("MouseReview", "https://www.reddit.com/r/MouseReview/hot.json?limit=15"),
    ("Controller", "https://www.reddit.com/r/Controller/hot.json?limit=15"),
]

KR_RSS_FEEDS = [
    ("ppomppu_kr", "https://www.ppomppu.co.kr/rss.php?id=ppomppu"),
    ("ppomppu_global", "https://www.ppomppu.co.kr/rss.php?id=ppomppu4"),
]

# Global cross-border IT/desk gear brands sold simultaneously on Coupang, Amazon, and AliExpress
GLOBAL_BRANDS: dict[str, tuple[str, str]] = {
    "ugreen": ("UGREEN", "chargers"),
    "유그린": ("UGREEN", "chargers"),
    "anker": ("Anker", "chargers"),
    "앤커": ("Anker", "chargers"),
    "baseus": ("Baseus", "powerbanks"),
    "베이스어스": ("Baseus", "powerbanks"),
    "cuktech": ("CUKTECH", "powerbanks"),
    "쿸테크": ("CUKTECH", "powerbanks"),
    "sharge": ("SHARGE", "powerbanks"),
    "iniu": ("INIU", "powerbanks"),
    "aula": ("AULA", "keyboards"),
    "독거미": ("AULA", "keyboards"),
    "keychron": ("Keychron", "keyboards"),
    "키크론": ("Keychron", "keyboards"),
    "nuphy": ("NuPhy", "keyboards"),
    "누피": ("NuPhy", "keyboards"),
    "lofree": ("Lofree", "keyboards"),
    "로프리": ("Lofree", "keyboards"),
    "monsgeek": ("MonsGeek", "keyboards"),
    "몬스긱": ("MonsGeek", "keyboards"),
    "epomaker": ("EPOMAKER", "keyboards"),
    "akko": ("Akko", "keyboards"),
    "wobkey": ("WOBKEY", "keyboards"),
    "레이니": ("WOBKEY", "keyboards"),
    "logitech": ("Logitech", "mice"),
    "로지텍": ("Logitech", "mice"),
    "razer": ("Razer", "mice"),
    "레이저": ("Razer", "mice"),
    "pulsar": ("Pulsar", "mice"),
    "펄사": ("Pulsar", "mice"),
    "vxe": ("VXE", "mice"),
    "atk": ("ATK", "mice"),
    "zaopin": ("Zaopin", "mice"),
    "beelink": ("Beelink", "minipc"),
    "비링크": ("Beelink", "minipc"),
    "minisforum": ("Minisforum", "minipc"),
    "미니스포럼": ("Minisforum", "minipc"),
    "gmktec": ("GMKtec", "minipc"),
    "aoostar": ("AOOSTAR", "minipc"),
    "fifine": ("FIFINE", "audio"),
    "파이파인": ("FIFINE", "audio"),
    "maono": ("Maono", "audio"),
    "moondrop": ("Moondrop", "audio"),
    "수월우": ("Moondrop", "audio"),
    "truthear": ("TRUTHEAR", "audio"),
    "earfun": ("EarFun", "audio"),
    "이어펀": ("EarFun", "audio"),
    "soundcore": ("Soundcore", "audio"),
    "사운드코어": ("Soundcore", "audio"),
    "elgato": ("Elgato", "productivity"),
    "엘가토": ("Elgato", "productivity"),
    "tourbox": ("TourBox", "productivity"),
    "samsung": ("Samsung", "storage"),
    "crucial": ("Crucial", "storage"),
    "마이크론": ("Crucial", "storage"),
    "orico": ("ORICO", "hubs"),
    "오리코": ("ORICO", "hubs"),
    "hagibis": ("Hagibis", "hubs"),
    "하기비스": ("Hagibis", "hubs"),
    "satechi": ("Satechi", "hubs"),
    "caldigit": ("CalDigit", "hubs"),
    "xiaomi": ("Xiaomi", "lighting"),
    "샤오미": ("Xiaomi", "lighting"),
    "yeelight": ("Yeelight", "lighting"),
    "8bitdo": ("8BitDo", "controllers"),
    "팔얼도": ("8BitDo", "controllers"),
    "gamesir": ("GameSir", "controllers"),
    "게임서": ("GameSir", "controllers"),
    "flydigi": ("Flydigi", "controllers"),
    "플라이디지": ("Flydigi", "controllers"),
}

ACCESSORY_NOISE_RE = re.compile(
    r"\b(case only|cover only|keycap only|screen protector|cable only|케이스 단품|보호필름|실리콘 커버|파우치 단품)\b",
    re.IGNORECASE,
)

MODEL_TOKEN_RE = re.compile(r"\b([A-Z]{1,5}[- ]?\d{1,4}[A-Z0-9+.-]{0,6}|M\d+\s?(?:Pro|Max|Ultra)?)\b")
# Deal-price parsers shared by lead discovery and the community-benchmark harvester (src/deal_sniper.py).
# USD accepts 1-5 digits so "$2.99" option-trap prices are parsed and then rejected by the MSRP floor,
# instead of silently slipping past the regex.
USD_PRICE_RE = re.compile(r"(?<![A-Za-z0-9])(?:US\s?)?\$\s?(\d{1,3}(?:,\d{3})+|\d{1,5})(\.\d{1,2})?(?![,.]?\d|\s*(?:off|coupon|discount|쿠폰|할인))", re.IGNORECASE)
KRW_PRICE_RE = re.compile(r"(?<![\d,])(\d{1,3}(?:,\d{3})+|\d{3,})\s*원(?!\s*(?:할인|쿠폰|적립))")


def parse_usd_price(text: str) -> float | None:
    """First USD deal price in a signal title, or None ("$20 off" style discount amounts are ignored)."""
    m = USD_PRICE_RE.search(text or "")
    if not m:
        return None
    return float(m.group(1).replace(",", "") + (m.group(2) or ""))


def parse_krw_price(text: str) -> int | None:
    """First KRW deal price ("59,000원") in a signal title, or None."""
    m = KRW_PRICE_RE.search(text or "")
    return int(m.group(1).replace(",", "")) if m else None


def _norm_key(text: str) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "", text.lower())


def fetch_reddit_signals(timeout_sec: int = 6) -> list[dict]:
    """Fetch public deal & hardware posts from Reddit JSON endpoints."""
    signals: list[dict] = []
    headers = {"User-Agent": "GearCompareHubBot/2.0 (hardware-index-collector)"}
    for sub_name, url in REDDIT_FEEDS:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            for child in payload.get("data", {}).get("children", []):
                post = child.get("data", {})
                if post.get("stickied"):
                    continue
                title = (post.get("title") or "").strip()
                if not title:
                    continue
                created = post.get("created_utc")
                posted_at = None
                if isinstance(created, (int, float)) and 0 < created < 253402300799:
                    posted_at = datetime.fromtimestamp(created, timezone.utc).isoformat()
                signals.append(
                    {
                        "source": f"reddit/{sub_name}",
                        "title": title,
                        "score": int(post.get("score", 0)),
                        "url": f"https://www.reddit.com{post.get('permalink', '')}",
                        "destination_url": post.get("url_overridden_by_dest") or post.get("url") or "",
                        "published_at": posted_at,
                    }
                )
        except (OSError, ValueError) as exc:
            print(f"[Collect note] reddit/{sub_name}: {getattr(exc, 'code', type(exc).__name__)}")
    return signals


def fetch_kr_rss_signals(timeout_sec: int = 6) -> list[dict]:
    """Fetch public Korean hot-deal RSS items (handles UTF-8 & EUC-KR/CP949)."""
    signals: list[dict] = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GearCompareHubBot/2.0)"}
    for source_name, url in KR_RSS_FEEDS:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw = resp.read()
            text = None
            for enc in ("utf-8", "cp949", "euc-kr"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if not text:
                continue
            # Strip XML encoding attribute so ElementTree parses decoded unicode string cleanly
            text = re.sub(r'<\?xml[^>]*\?>', "", text, count=1).strip()
            root = ET.fromstring(text)
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                if not title:
                    continue
                try:
                    date = parsedate_to_datetime(item.findtext("pubDate") or "")
                    posted_at = date.isoformat() if date.tzinfo else None
                except ValueError:
                    posted_at = None
                signals.append({"source": source_name, "title": title, "score": 10, "url": link, "published_at": posted_at})
        except (OSError, ET.ParseError) as exc:
            print(f"[Collect note] {source_name}: {getattr(exc, 'code', type(exc).__name__)}")
    return signals


def extract_new_model_leads(
    signals: list[dict], existing_catalog: list[dict], rejected_keys: set[str]
) -> list[dict]:
    """Identify cross-border hardware leads not yet indexed in products.json."""
    existing_norms = []
    for item in existing_catalog:
        existing_norms.append(_norm_key(f"{item.get('brand', '')} {item.get('model', '')}"))
        existing_norms.append(_norm_key(item.get("id", "")))

    leads_by_sig: dict[str, dict] = {}
    for sig in signals:
        title = sig["title"]
        if ACCESSORY_NOISE_RE.search(title):
            continue
        low = title.lower()
        matched_brand = None
        default_cat = "hubs"
        for kw, (canon_brand, cat) in GLOBAL_BRANDS.items():
            if kw in low:
                matched_brand = canon_brand
                default_cat = cat
                break
        if not matched_brand:
            continue

        tokens = MODEL_TOKEN_RE.findall(title)
        model_hint = tokens[0].strip() if tokens else ""
        norm_title = _norm_key(title)

        # Skip if already in catalog or previously rejected
        already_indexed = False
        for ex in existing_norms:
            if ex and len(ex) >= 6 and (ex in norm_title or (model_hint and _norm_key(matched_brand + model_hint) in ex)):
                already_indexed = True
                break
        lead_key = _norm_key(f"{matched_brand}_{model_hint or title[:32]}")
        if already_indexed or lead_key in rejected_keys or lead_key in leads_by_sig:
            continue

        leads_by_sig[lead_key] = {
            "lead_key": lead_key,
            "brand": matched_brand,
            "suggested_category": default_cat,
            "model_hint": model_hint,
            "raw_title": title,
            "observed_usd": parse_usd_price(title),
            "observed_krw": parse_krw_price(title),
            "source": sig["source"],
            "source_url": sig["url"],
            "score": sig.get("score", 0),
            "discovered_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }

    ranked = sorted(leads_by_sig.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:40]


def collect_candidates(project_root: Path, live_network: bool = False, *, prior_stage: dict | None = None) -> dict:
    """Merge catalog + inbox and update discovery_queue.json with newly spotted models."""
    data_dir = project_root / "data"
    catalog = json.loads((data_dir / "products.json").read_text(encoding="utf-8"))
    inbox_path = data_dir / "candidates_inbox.json"
    inbox = json.loads(inbox_path.read_text(encoding="utf-8")) if inbox_path.exists() else []

    rejected_path = data_dir / "rejected_leads.json"
    rejected_keys = set(json.loads(rejected_path.read_text(encoding="utf-8"))) if rejected_path.exists() else set()

    prior_stage = prior_stage or {}
    signals = prior_stage.get("trend_signals", [])
    leads_found = prior_stage.get("new_model_leads_found", 0)
    if live_network:
        signals = fetch_reddit_signals() + fetch_kr_rss_signals()
        new_leads = extract_new_model_leads(signals, catalog, rejected_keys)
        leads_found = len(new_leads)
        queue_path = data_dir / "discovery_queue.json"
        existing_queue = json.loads(queue_path.read_text(encoding="utf-8")) if queue_path.exists() else []
        merged_q = {item["lead_key"]: item for item in existing_queue}
        for lead in new_leads:
            merged_q.setdefault(lead["lead_key"], lead)
        queue_path.write_text(
            json.dumps(list(merged_q.values())[:100], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    by_id = {item["id"]: item for item in catalog}
    for candidate in inbox:
        by_id[candidate["id"]] = candidate

    staged = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "candidates": list(by_id.values()),
        "trend_signals_count": len(signals),
        "new_model_leads_found": leads_found,
        # Full pass-through: every fetched Reddit + Ppomppu signal reaches the sniper and the benchmark harvester.
        "trend_signals": signals,
        # Compact human-readable sample only; never use this slice as pipeline input.
        "trend_signals_preview": signals[:8],
    }
    (data_dir / "candidates_staged.json").write_text(
        json.dumps(staged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return staged
