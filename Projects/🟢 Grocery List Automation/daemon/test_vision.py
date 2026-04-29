#!/usr/bin/env python3
"""
Vision test for the grocery scanner — Google Gemini 2.5 Flash.

Supports multiple photos of the same product (front, back, side of cylindrical
items) sent together in one API call so the model can synthesise across views.

Usage:
  # Single photo
  python3 test_vision.py front.jpg

  # Multiple angles of the same product
  python3 test_vision.py front.jpg back.jpg side.jpg

Requires:
  pip3 install --break-system-packages google-genai python-dotenv

Environment variable (add to .env or export):
  GEMINI_API_KEY=<Google AI Studio API key>
"""

import sys
import os
import base64
import time
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"

PROMPT_SINGLE = (
    "You are helping identify a grocery product from a photo of its label. "
    "Return ONLY a JSON object with these fields:\n"
    '  "name": the product name (string, required)\n'
    '  "brand": the brand name (string, empty string if not visible)\n'
    '  "quantity": weight, volume, or count shown on the label (string, empty string if not visible)\n'
    '  "confidence": "high", "medium", or "low"\n'
    '  "notes": anything unusual or ambiguous (string, empty string if nothing to add)\n\n'
    "Respond with valid JSON only, no markdown fences, no extra text."
)

PROMPT_MULTI = (
    "You are helping identify a grocery product. "
    "You have been given {n} photos of the same product from different angles. "
    "Use all views together to identify it as accurately as possible. "
    "Return ONLY a JSON object with these fields:\n"
    '  "name": the product name (string, required)\n'
    '  "brand": the brand name (string, empty string if not visible)\n'
    '  "quantity": weight, volume, or count shown on the label (string, empty string if not visible)\n'
    '  "confidence": "high", "medium", or "low"\n'
    '  "notes": anything unusual or ambiguous (string, empty string if nothing to add)\n\n'
    "Respond with valid JSON only, no markdown fences, no extra text."
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_image_bytes(path: str) -> tuple[bytes, str]:
    path = Path(path)
    ext = path.suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
    return path.read_bytes(), mime


def try_parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        stripped = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(stripped)
        except Exception:
            return {"raw": text}


# ── Gemini ────────────────────────────────────────────────────────────────────

def query_gemini(image_paths: list[str]) -> dict:
    try:
        from google import genai
        from google.genai import types as gtypes
    except ImportError:
        return {"error": "google-genai not installed — run: pip3 install --break-system-packages google-genai"}

    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not set"}

    client = genai.Client(api_key=GEMINI_API_KEY)

    contents = []
    for p in image_paths:
        data, mime = load_image_bytes(p)
        contents.append(gtypes.Part.from_bytes(data=data, mime_type=mime))

    prompt = PROMPT_MULTI.format(n=len(image_paths)) if len(image_paths) > 1 else PROMPT_SINGLE
    contents.append(prompt)

    t0 = time.perf_counter()
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=gtypes.GenerateContentConfig(temperature=0.0, max_output_tokens=512),
        )
        elapsed = time.perf_counter() - t0
        raw = resp.text or ""
        return {"result": try_parse_json(raw), "latency_s": round(elapsed, 2)}
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.perf_counter() - t0, 2)}


# ── Output ────────────────────────────────────────────────────────────────────

def print_result(data: dict):
    w = 60
    print(f"\n{'─' * w}")
    if "error" in data:
        print(f"  ERROR: {data['error']}")
        return
    print(f"  Latency : {data.get('latency_s', '?')} s")
    r = data.get("result", {})
    if "raw" in r and len(r) == 1:
        print(f"  Parse failed — raw response:")
        print(f"  {r['raw'][:500]}")
    else:
        print(f"  Name       : {r.get('name', '—')}")
        print(f"  Brand      : {r.get('brand') or '—'}")
        print(f"  Quantity   : {r.get('quantity') or '—'}")
        print(f"  Confidence : {r.get('confidence', '—')}")
        if r.get("notes"):
            print(f"  Notes      : {r['notes']}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)

    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        for p in missing:
            print(f"File not found: {p}")
        sys.exit(1)

    w = 60
    print(f"\n{'═' * w}")
    if len(paths) == 1:
        print(f"  Image : {paths[0]}")
    else:
        print(f"  Images: {len(paths)} photos of the same product")
        for p in paths:
            print(f"    • {p}")
    print(f"  Model : {GEMINI_MODEL}")
    print(f"{'═' * w}")

    print("\nQuerying Gemini ...")
    result = query_gemini(paths)
    print_result(result)


if __name__ == "__main__":
    main()
