import os
import re
import json
import subprocess

GEMINI_MODEL = "gemini-2.5-flash"

_PROMPT_SINGLE = (
    "You are helping identify a grocery product from a photo of its label. "
    "Return ONLY a JSON object with these fields:\n"
    '  "name": the product name (string, required)\n'
    '  "brand": the brand name (string, empty string if not visible)\n'
    '  "quantity": weight, volume, or count shown on the label (string, empty string if not visible)\n'
    '  "confidence": "high", "medium", or "low"\n\n'
    "Respond with valid JSON only, no markdown fences, no extra text."
)

_PROMPT_MULTI = (
    "You are helping identify a grocery product. "
    "You have been given {n} photos of the same product from different angles. "
    "Use all views together to identify it as accurately as possible. "
    "Return ONLY a JSON object with these fields:\n"
    '  "name": the product name (string, required)\n'
    '  "brand": the brand name (string, empty string if not visible)\n'
    '  "quantity": weight, volume, or count shown on the label (string, empty string if not visible)\n'
    '  "confidence": "high", "medium", or "low"\n\n'
    "Respond with valid JSON only, no markdown fences, no extra text."
)


def capture_photo(path: str = "/tmp/grocery_front.jpg") -> tuple[bool, str]:
    try:
        subprocess.run(
            ["rpicam-jpeg", "--nopreview", "-o", path,
             "-t", "2000", "--width", "1280", "--height", "960"],
            check=True, timeout=15, capture_output=True,
        )
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode(errors="replace").strip() or "rpicam-jpeg failed"
    except Exception as e:
        return False, str(e)


def identify_with_gemini(paths: list[str]) -> tuple[dict | None, str]:
    try:
        from google import genai
        from google.genai import types as gtypes
    except ImportError:
        return None, "google-genai not installed"

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None, "GEMINI_API_KEY not set in .env"

    client   = genai.Client(api_key=api_key)
    contents = []
    for p in paths:
        with open(p, "rb") as f:
            contents.append(gtypes.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

    prompt = _PROMPT_MULTI.format(n=len(paths)) if len(paths) > 1 else _PROMPT_SINGLE
    contents.append(prompt)

    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=gtypes.GenerateContentConfig(temperature=0.0, max_output_tokens=512),
        )
        raw = (resp.text or "").strip()
        return _parse_json(raw), ""
    except _JsonParseError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


class _JsonParseError(Exception):
    pass


def _parse_json(text: str) -> dict:
    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2. Strip markdown fences
    stripped = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # 3. Extract first {...} block via regex
    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    # 4. Quote unquoted keys (Gemini sometimes emits JS-style {key: "value"})
    fixed = re.sub(r'(?<=[{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', r' "\1":', stripped)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    raise _JsonParseError(f"Unparseable: {text[:120]}")


def upload_to_openfoodfacts(barcode: str, name: str, brand: str, quantity: str,
                            front_path: str = "") -> str:
    import requests as req
    user     = os.getenv("OFF_USER", "")
    password = os.getenv("OFF_PASSWORD", "")
    if not user or not password:
        return "OFF credentials not configured"

    try:
        r = req.post(
            "https://world.openfoodfacts.org/cgi/product_jqm2.pl",
            data={"code": barcode, "product_name": name, "brands": brand,
                  "quantity": quantity, "user_id": user, "password": password},
            timeout=10,
        )
        if r.status_code not in (200, 201):
            return f"HTTP {r.status_code}"
    except Exception as e:
        return str(e)

    if front_path and os.path.exists(front_path):
        try:
            with open(front_path, "rb") as f:
                req.post(
                    "https://world.openfoodfacts.org/cgi/product_image_upload.pl",
                    data={"code": barcode, "imagefield": "front",
                          "user_id": user, "password": password},
                    files={"imgupload_front": (f"front_{barcode}.jpg", f, "image/jpeg")},
                    timeout=15,
                )
        except Exception:
            pass  # photo upload failure is non-fatal

    return ""
