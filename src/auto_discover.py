"""Automated model discovery enricher: turns raw deal leads into price-free Gatekeeper-verified catalog entries."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from src.verifier import verify_product

VALID_CATEGORIES = (
    "chargers",
    "keyboards",
    "powerbanks",
    "minipc",
    "mice",
    "audio",
    "storage",
    "lighting",
    "productivity",
    "hubs",
    "controllers",
)

ENRICH_PROMPT_TEMPLATE = """You are a strict hardware catalog curator for GearCompare Hub.
Given these newly spotted cross-border hardware leads, select ONLY genuine standalone hardware models
(NEVER cables, cases, keycap-only sets, or screen protectors) sold across Coupang, Amazon US, and AliExpress.
IMPORTANT COMPLIANCE RULES:
- Do NOT include static retailer `prices` (`coupang_krw`, `amazon_usd`, `ali_usd`, `ali_krw`).
- Only include manufacturer reference `msrp_krw`, `msrp_usd`, and `msrp_source` ("Manufacturer official spec reference").
- Never write exact dollar/won savings or unverified blanket seller guarantees ("100% free returns") in `verdict`.
Return ONLY a valid JSON array (0 to {limit} objects, no markdown fences) matching this exact schema:
[
  {{
    "id": "brand-model-short-slug",
    "category": "one of: chargers, keyboards, powerbanks, minipc, mice, audio, storage, lighting, productivity, hubs, controllers",
    "brand": "Brand",
    "model": "Exact Full Model Name & SKU",
    "updated_at": "{today}",
    "in_stock": true,
    "msrp_krw": 89000,
    "msrp_usd": 69.99,
    "msrp_source": "Manufacturer official MSRP reference ({today})",
    "buying_profile": {{
      "preferred_route_ko": "domestic or direct",
      "preferred_route_en": "amazon or direct",
      "amazon_priority_score": 80,
      "kr_origin_note": "중국발 직구 시 미화 150달러 / 미국발 목록통관 적격 시 200달러 면세 기준 결제창 확인",
      "us_import_note": "Amazon US: check Ships from US · AliExpress: verify import charges at checkout"
    }},
    "urls": {{
      "coupang_query": "정확한 한국어 브랜드+모델명 검색어",
      "ali_query": "Exact English Brand + Model Number",
      "amazon_query": "Exact English Brand + Model Number"
    }},
    "specs": {{
      "spec_key_1": "concise value",
      "spec_key_2": "concise value",
      "spec_key_3": "concise value",
      "spec_key_4": "concise value"
    }},
    "ko": {{
      "title": "자연스러운 한국어 제품명 (모델번호 포함)",
      "summary": "광고 어투 없는 건조한 1문장 스펙·용도 요약.",
      "pros": ["구체적 장점 1", "구체적 장점 2"],
      "cons": ["실사용에서 지적되는 구체적 단점 1 (최소 15자 이상)", "구체적 단점 2"],
      "verdict": "정적 가격 숫자 없이 국내 배송·교환 편의와 직구 프로모션·대기시간 기준의 1문장 구매 판단."
    }},
    "en": {{
      "title": "Clean English Product Title with Model Number",
      "summary": "Dry, factual 1-sentence hardware summary without marketing fluff.",
      "pros": ["Specific strength 1", "Specific strength 2"],
      "cons": ["Specific real-world drawback 1 (at least 20 chars)", "Specific drawback 2"],
      "verdict": "Price-free 1-sentence buying verdict comparing domestic US shipping convenience vs direct-import lead time."
    }}
  }}
]

Raw leads to evaluate:
{leads_json}
"""


def _extract_json_array(raw_text: str) -> list[dict]:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        parsed = json.loads(cleaned[start : end + 1])
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _enrich_via_gemini_free_api(prompt: str, api_key: str) -> list[dict]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        return _extract_json_array(text)
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError, OSError):
        return []


def _enrich_via_claude_cli(prompt: str) -> list[dict]:
    claude_bin = shutil.which("claude") or shutil.which("claude.cmd")
    ps1_path = Path.home() / "AppData" / "Roaming" / "npm" / "claude.ps1"
    if claude_bin:
        cmd = [claude_bin, "-p", "--no-session-persistence", "--output-format", "text"]
    elif ps1_path.exists():
        cmd = ["powershell", "-NoProfile", "-File", str(ps1_path), "-p", "--no-session-persistence", "--output-format", "text"]
    else:
        return []
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0:
            return []
        return _extract_json_array(proc.stdout)
    except (OSError, subprocess.SubprocessError):
        return []


def auto_grow_catalog(project_root: Path, cfg: dict, max_new: int = 5) -> dict:
    """Process queued leads, enrich into price-free records, Gatekeeper-verify, and append to products.json."""
    if max_new <= 0:
        return {"attempted": 0, "added": 0, "rejected": 0, "added_ids": []}

    data_dir = project_root / "data"
    queue_path = data_dir / "discovery_queue.json"
    if not queue_path.exists():
        return {"attempted": 0, "added": 0, "rejected": 0, "added_ids": []}

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if not queue:
        return {"attempted": 0, "added": 0, "rejected": 0, "added_ids": []}

    batch = queue[: max_new * 2]
    remaining_queue = queue[max_new * 2 :]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = ENRICH_PROMPT_TEMPLATE.format(
        limit=max_new,
        today=today,
        leads_json=json.dumps(batch, ensure_ascii=False, indent=2),
    )

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    generated = _enrich_via_gemini_free_api(prompt, gemini_key) if gemini_key else _enrich_via_claude_cli(prompt)

    products_path = data_dir / "products.json"
    catalog = json.loads(products_path.read_text(encoding="utf-8"))
    existing_ids = {item["id"] for item in catalog}

    rejected_path = data_dir / "rejected_leads.json"
    rejected_keys = set(json.loads(rejected_path.read_text(encoding="utf-8"))) if rejected_path.exists() else set()

    added_ids: list[str] = []
    rejected_count = 0

    for item in generated:
        if len(added_ids) >= max_new:
            break
        if not isinstance(item, dict) or not item.get("id"):
            continue
        if item["id"] in existing_ids:
            continue
        if item.get("category") not in VALID_CATEGORIES:
            item["category"] = "hubs"
        item.pop("prices", None)

        res, _ = verify_product(item, cfg)
        if res.passed:
            catalog.append(item)
            existing_ids.add(item["id"])
            added_ids.append(item["id"])
        else:
            rejected_count += 1

    for lead in batch:
        rejected_keys.add(lead["lead_key"])

    if added_ids:
        products_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    queue_path.write_text(json.dumps(remaining_queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rejected_path.write_text(json.dumps(sorted(rejected_keys), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "attempted": len(batch),
        "added": len(added_ids),
        "rejected": rejected_count,
        "added_ids": added_ids,
    }
