import os
import sys
import json
import time
import threading
import datetime
import subprocess
import requests
import pygame
from collections import namedtuple
from evdev import InputDevice, categorize, ecodes
from dotenv import load_dotenv
from vision import capture_photo, identify_with_gemini, upload_to_openfoodfacts

load_dotenv()

HA_URL         = os.getenv("HA_URL")
HA_TOKEN       = os.getenv("HA_TOKEN")
HA_TODO_ENTITY = os.getenv("HA_TODO_ENTITY")
SCANNER_DEVICE = os.getenv("SCANNER_DEVICE")
LANG_PRIORITY  = os.getenv("LANG_PRIORITY", "de,es,en").split(",")
DATA_DIR       = os.getenv("DATA_DIR", "./data")
UNKNOWN_LOG    = os.path.join(DATA_DIR, "unknown.jsonl")
CUSTOM_MAP     = os.path.join(DATA_DIR, "custom_barcodes.json")

FRONT_PHOTO    = "/tmp/grocery_front.jpg"
BACK_PHOTO     = "/tmp/grocery_back.jpg"
BLANK_TIMEOUT  = 30  # seconds of inactivity before display off
LIST_PAGE_SIZE = 5   # shopping-list rows per page in the list view

_last_activity: float = 0.0
_screen_blanked: bool = False

KEYMAP = {
    2:"1",3:"2",4:"3",5:"4",6:"5",7:"6",8:"7",9:"8",10:"9",11:"0",
    28:"\n"
}

# ── Display setup ─────────────────────────────────────────────────────────────

os.environ["DISPLAY"] = ":0"
os.environ["SDL_VIDEODRIVER"] = "x11"

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
W, H = screen.get_size()

font_large  = pygame.font.SysFont("dejavu sans", 72, bold=True)
font_medium = pygame.font.SysFont("dejavu sans", 48, bold=True)
font_small  = pygame.font.SysFont("dejavu sans", 36)
font_button = pygame.font.SysFont("dejavu sans", 32, bold=True)
font_tiny   = pygame.font.SysFont("dejavu sans", 24)

C = {
    "green":  ( 34, 139,  34),
    "red":    (180,   0,   0),
    "yellow": (210, 160,   0),
    "idle":   ( 30,  30,  30),
    "dark":   ( 20,  20,  20),
    "blue":   ( 45,  90, 120),
    "grey":   ( 70,  70,  70),
}
WHITE = (255, 255, 255)
LIGHT = (200, 200, 200)
DIM   = (140, 140, 140)

# ── State machine ─────────────────────────────────────────────────────────────

app_state = {
    "screen":           "idle",
    "barcode":          "",
    "result":           None,
    "error":            "",
    "processing_label": "Identifying…",
    "product_name":     "",
    "product_detail":   "",
    "items":            [],
    "items_page":       0,
    "items_error":      "",
}
state_lock   = threading.Lock()
needs_render = threading.Event()
needs_render.set()

def set_state(**kwargs):
    with state_lock:
        app_state.update(kwargs)
    needs_render.set()

def get_state(*keys):
    with state_lock:
        return tuple(app_state.get(k) for k in keys) if len(keys) > 1 else app_state.get(keys[0])

# ── Button helpers ────────────────────────────────────────────────────────────

Button = namedtuple("Button", ["label", "rect", "color", "action"])
active_buttons: list = []

def _draw_button(btn):
    pygame.draw.rect(screen, btn.color, btn.rect, border_radius=10)
    txt = font_button.render(btn.label, True, WHITE)
    screen.blit(txt, txt.get_rect(center=btn.rect.center))

def _hit(pos):
    for btn in active_buttons:
        if btn.rect.collidepoint(pos):
            return btn.action
    return None

# ── Text helpers ──────────────────────────────────────────────────────────────

def _center(text, font, color, y, max_w=None):
    if max_w:
        while font.size(text)[0] > max_w and len(text) > 4:
            text = text[:-4] + "…"
    s = font.render(text, True, color)
    screen.blit(s, s.get_rect(center=(W // 2, y)))

# ── Per-screen renderers ──────────────────────────────────────────────────────

def _render_idle():
    active_buttons.clear()
    screen.fill(C["idle"])
    _center("Grocery Scanner", font_large, WHITE, H // 2 - 40)
    _center("Ready — scan a product", font_small, DIM, H // 2 + 60)
    pygame.display.flip()

def _render_simple(bg, line1, line2=""):
    active_buttons.clear()
    screen.fill(C.get(bg, C["idle"]))
    _center(line1, font_large, WHITE, H // 2 - 40, max_w=W - 40)
    if line2:
        _center(line2, font_small, WHITE, H // 2 + 60, max_w=W - 40)
    pygame.display.flip()

def _render_unknown(barcode):
    active_buttons.clear()
    screen.fill(C["red"])
    _center("Unknown product", font_large, WHITE, H // 2 - 80)
    _center(barcode, font_small, WHITE, H // 2)
    _center("Tap anywhere to identify", font_small, (255, 200, 200), H // 2 + 70)
    pygame.display.flip()

def _render_choice(barcode):
    active_buttons.clear()
    screen.fill(C["dark"])
    _center("How to identify?", font_medium, WHITE, 70)
    _center(barcode, font_small, DIM, 130)
    btns = [
        Button("Auto  (camera)", pygame.Rect(40,           200, W // 2 - 60, 100), C["blue"], "auto"),
        Button("Use web UI",     pygame.Rect(W // 2 + 20,  200, W // 2 - 60, 100), C["grey"], "webui"),
    ]
    active_buttons.extend(btns)
    for b in btns:
        _draw_button(b)
    _center("192.168.0.162:5000", font_tiny, DIM, 370)
    pygame.display.flip()

def _render_front_prompt(error=""):
    active_buttons.clear()
    screen.fill(C["dark"])
    _center("Place front toward camera", font_medium, WHITE, 100)
    if error:
        _center(error, font_tiny, (255, 120, 120), 165)
    btns = [
        Button("Take photo", pygame.Rect(W // 2 - 200, 220, 400, 100), C["blue"], "take_front"),
        Button("Cancel",     pygame.Rect(W // 2 - 100, 370, 200,  60), C["grey"], "cancel"),
    ]
    active_buttons.extend(btns)
    for b in btns:
        _draw_button(b)
    pygame.display.flip()

def _render_back_prompt(error=""):
    active_buttons.clear()
    screen.fill(C["dark"])
    _center("Add back photo?", font_medium, WHITE, 80)
    _center("Useful for cylindrical products", font_small, DIM, 150)
    if error:
        _center(error, font_tiny, (255, 120, 120), 195)
    btns = [
        Button("Take back photo", pygame.Rect(30,           230, W // 2 - 50, 100), C["blue"], "take_back"),
        Button("Identify now",    pygame.Rect(W // 2 + 20,  230, W // 2 - 50, 100), C["grey"], "identify_now"),
        Button("Cancel",          pygame.Rect(W // 2 - 100, 375, 200,          60), C["grey"], "cancel"),
    ]
    active_buttons.extend(btns)
    for b in btns:
        _draw_button(b)
    pygame.display.flip()

def _render_processing(label="Identifying…"):
    active_buttons.clear()
    screen.fill(C["dark"])
    _center(label, font_large, WHITE, H // 2 - 40)
    _center("Please wait", font_small, DIM, H // 2 + 60)
    pygame.display.flip()

def _render_result(result, error=""):
    active_buttons.clear()
    screen.fill((20, 35, 20))

    if not result:
        _center("Identification failed", font_medium, WHITE, 80)
        _center(error or "Unknown error", font_small, (255, 120, 120), 155)
        btns = [
            Button("Try again", pygame.Rect(W // 2 - 230, 290, 210, 80), C["grey"], "retry"),
            Button("Cancel",    pygame.Rect(W // 2 +  20, 290, 210, 80), C["grey"], "cancel"),
        ]
        active_buttons.extend(btns)
        for b in btns:
            _draw_button(b)
        pygame.display.flip()
        return

    name       = result.get("name", "")
    brand      = result.get("brand", "")
    quantity   = result.get("quantity", "")
    confidence = result.get("confidence", "")
    detail     = " • ".join(p for p in [brand, quantity] if p)

    _center(name,   font_medium, WHITE, 80,  max_w=W - 40)
    if detail:
        _center(detail, font_small, LIGHT, 148, max_w=W - 40)
    conf_color = {"high": (80, 200, 80), "medium": (210, 210, 80), "low": (210, 100, 80)}.get(confidence, DIM)
    _center(f"Confidence: {confidence}", font_tiny, conf_color, 208)

    btns = [
        Button("Accept",    pygame.Rect( 30, 300, 240, 80), C["green"], "accept"),
        Button("Try again", pygame.Rect(290, 300, 220, 80), C["grey"],  "retry"),
        Button("Web UI",    pygame.Rect(530, 300, 220, 80), C["grey"],  "webui"),
    ]
    active_buttons.extend(btns)
    for b in btns:
        _draw_button(b)
    pygame.display.flip()

def _render_webui_hint():
    active_buttons.clear()
    screen.fill(C["dark"])
    _center("Open web UI on your phone:", font_small, WHITE, H // 2 - 70)
    _center("192.168.0.162:5000", font_medium, (120, 200, 255), H // 2)
    btn = Button("Back to main menu", pygame.Rect(W // 2 - 160, H // 2 + 90, 320, 70), C["grey"], "back")
    active_buttons.append(btn)
    _draw_button(btn)
    pygame.display.flip()

def _render_menu():
    active_buttons.clear()
    screen.fill(C["dark"])
    _center("Scanner Menu", font_medium, WHITE, 50)
    btns = [
        Button("Shopping List", pygame.Rect( 40, 130, W - 80, 80),       C["blue"],  "shopping_list"),
        Button("Restart",       pygame.Rect( 40, 230, 330, 80),          C["blue"],  "restart"),
        Button("Close",         pygame.Rect(410, 230, 330, 80),          C["red"],   "close"),
        Button("Cancel",        pygame.Rect(W // 2 - 120, 340, 240, 60), C["grey"],  "cancel"),
    ]
    active_buttons.extend(btns)
    for b in btns:
        _draw_button(b)
    pygame.display.flip()

def _render_already_in_list(name, detail):
    active_buttons.clear()
    screen.fill(C["yellow"])
    _center("Already in shopping list", font_medium, WHITE, H // 2 - 80, max_w=W - 40)
    _center(name, font_large, WHITE, H // 2, max_w=W - 40)
    if detail:
        _center(detail, font_small, (240, 230, 200), H // 2 + 70, max_w=W - 40)
    pygame.display.flip()

def _render_list_view(items, page, error):
    active_buttons.clear()
    screen.fill(C["dark"])

    n = len(items)
    n_pages = max(1, (n + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE)
    page = max(0, min(page, n_pages - 1))

    # Header
    title = f"Shopping List · {n} item{'s' if n != 1 else ''}" if n else "Shopping List"
    _center(title, font_medium, WHITE, 28)
    if error:
        _center(error, font_tiny, (255, 150, 150), 60)

    if n == 0:
        _center("List is empty", font_small, DIM, H // 2 - 20)
    else:
        start = page * LIST_PAGE_SIZE
        page_items = items[start:start + LIST_PAGE_SIZE]
        y0, row_h, gap = 75, 64, 6
        x_color = (140, 50, 50)

        for i, it in enumerate(page_items):
            y = y0 + i * (row_h + gap)
            name = (it.get("summary") or "").strip()
            uid  = it.get("uid") or name

            pygame.draw.rect(screen, (50, 50, 50), pygame.Rect(20, y, W - 40, row_h), border_radius=6)

            display_name = name
            max_w = W - 60 - 90
            while font_button.size(display_name)[0] > max_w and len(display_name) > 4:
                display_name = display_name[:-4] + "…"
            txt = font_button.render(display_name, True, WHITE)
            screen.blit(txt, (40, y + (row_h - txt.get_height()) // 2))

            x_btn = Button("X", pygame.Rect(W - 95, y + 7, 75, row_h - 14), x_color, ("delete", uid, name))
            active_buttons.append(x_btn)
            _draw_button(x_btn)

    # Footer
    fy = H - 55
    btn_h = 48
    if n_pages > 1:
        prev_color = C["grey"] if page > 0 else (40, 40, 40)
        next_color = C["grey"] if page < n_pages - 1 else (40, 40, 40)
        prev_btn = Button("Prev", pygame.Rect(20,        fy, 130, btn_h), prev_color, "prev")
        next_btn = Button("Next", pygame.Rect(W - 150,   fy, 130, btn_h), next_color, "next")
        active_buttons.extend([prev_btn, next_btn])
        _draw_button(prev_btn)
        _draw_button(next_btn)

    back_btn = Button("Back", pygame.Rect(W // 2 - 90, fy, 180, btn_h), C["grey"], "back")
    active_buttons.append(back_btn)
    _draw_button(back_btn)

    if n_pages > 1:
        _center(f"{page + 1}/{n_pages}", font_tiny, DIM, fy - 12)

    pygame.display.flip()

def render_current():
    with state_lock:
        s            = app_state["screen"]
        barcode      = app_state["barcode"]
        result       = app_state["result"]
        error        = app_state["error"]
        p_name       = app_state["product_name"]
        p_det        = app_state["product_detail"]
        p_label      = app_state["processing_label"]
        items        = app_state["items"]
        items_page   = app_state["items_page"]
        items_error  = app_state["items_error"]

    if   s == "idle":             _render_idle()
    elif s == "lookup":           _render_simple("idle", "Looking up…", barcode)
    elif s == "known_ok":         _render_simple("green",  p_name, p_det)
    elif s == "known_err":        _render_simple("yellow", p_name, p_det + " — not added")
    elif s == "already_in_list":  _render_already_in_list(p_name, p_det)
    elif s == "unknown_screen":   _render_unknown(barcode)
    elif s == "choice":           _render_choice(barcode)
    elif s == "front_prompt":     _render_front_prompt(error)
    elif s == "back_prompt":      _render_back_prompt(error)
    elif s == "processing":       _render_processing(p_label)
    elif s == "result_screen":    _render_result(result, error)
    elif s == "confirmed":        _render_simple("green", "Added to Bring!", p_name)
    elif s == "webui_hint":       _render_webui_hint()
    elif s == "menu":             _render_menu()
    elif s == "list_loading":     _render_processing(p_label)
    elif s == "list_view":        _render_list_view(items, items_page, items_error)

# ── Display power management ──────────────────────────────────────────────────

def _mark_activity():
    global _last_activity
    _last_activity = time.time()

def _blank_screen():
    global _screen_blanked
    if _screen_blanked:
        return
    _screen_blanked = True
    screen.fill((0, 0, 0))
    pygame.display.flip()
    subprocess.run(["vcgencmd", "display_power", "0"], capture_output=True)

def _wake_screen():
    global _screen_blanked, _last_activity
    if not _screen_blanked:
        return
    subprocess.run(["vcgencmd", "display_power", "1"], capture_output=True)
    time.sleep(0.2)  # brief wait for panel to come back
    _screen_blanked = False
    _last_activity = time.time()
    needs_render.set()

# ── Background tasks ──────────────────────────────────────────────────────────

def _thread(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()

def _capture_front():
    set_state(processing_label="Taking photo…", screen="processing")
    ok, err = capture_photo(FRONT_PHOTO)
    if ok:
        set_state(screen="back_prompt", error="")
    else:
        set_state(screen="front_prompt", error=f"Camera: {err}")

def _capture_back():
    set_state(processing_label="Taking back photo…", screen="processing")
    ok, err = capture_photo(BACK_PHOTO)
    if ok:
        _run_gemini_inner()
    else:
        set_state(screen="back_prompt", error=f"Camera: {err}")

def _run_gemini():
    set_state(processing_label="Identifying…", screen="processing")
    _run_gemini_inner()

def _run_gemini_inner():
    photos = [p for p in [FRONT_PHOTO, BACK_PHOTO] if os.path.exists(p)]
    result, err = identify_with_gemini(photos)
    set_state(screen="result_screen", result=result, error=err)

def _do_confirm(barcode, result):
    name   = result.get("name", "")
    brand  = result.get("brand", "")
    qty    = result.get("quantity", "")
    detail = " • ".join(p for p in [brand, qty] if p)
    set_state(product_name=name, product_detail=detail)

    status = add_to_bring(name, brand, qty)
    if status in ("added", "duplicate"):
        # Either way the barcode → name mapping is now known: learn it.
        _remove_unknown(barcode)
        _save_custom(barcode, name)
        next_screen = "confirmed" if status == "added" else "already_in_list"
        set_state(screen=next_screen)
        _thread(upload_to_openfoodfacts, barcode, name, brand, qty, FRONT_PHOTO)
        time.sleep(3 if status == "duplicate" else 2)
        if get_state("screen") == next_screen:
            set_state(screen="idle", barcode="", result=None, error="",
                      product_name="", product_detail="")
    else:
        set_state(screen="result_screen", error="HA error — not added")

def _load_shopping_list():
    set_state(processing_label="Loading list…", screen="list_loading")
    items = fetch_shopping_items()
    if items is None:
        set_state(screen="list_view", items=[], items_page=0,
                  items_error="Failed to load list")
    else:
        set_state(screen="list_view", items=items, items_page=0, items_error="")

def _delete_item(uid, name):
    set_state(processing_label="Removing…", screen="list_loading")
    ok = remove_from_bring(uid)
    if not ok and uid != name:
        # Fall back to deleting by summary if uid-based delete failed
        ok = remove_from_bring(name)
    if not ok:
        items = fetch_shopping_items() or get_state("items")
        set_state(screen="list_view", items=items,
                  items_error=f"Failed to remove '{name}'")
        return
    items = fetch_shopping_items() or []
    n_pages = max(1, (len(items) + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE)
    page = min(get_state("items_page") or 0, n_pages - 1)
    set_state(screen="list_view", items=items, items_page=page, items_error="")

def _webui_then_idle():
    set_state(screen="webui_hint")
    time.sleep(5)
    if get_state("screen") == "webui_hint":
        set_state(screen="idle", barcode="", result=None, error="")

# ── Touch handler ─────────────────────────────────────────────────────────────

def handle_touch(pos):
    if _screen_blanked:
        _wake_screen()
        return  # consume the tap; don't trigger buttons
    _mark_activity()
    s, barcode, result = get_state("screen", "barcode", "result")

    if s == "idle":
        set_state(screen="menu")
        return

    if s == "unknown_screen":
        set_state(screen="choice")
        return

    action = _hit(pos)
    if not action:
        return

    if s == "menu":
        if action == "shopping_list":
            _thread(_load_shopping_list)
        elif action == "restart":
            pygame.quit()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        elif action == "close":
            pygame.quit()
            sys.exit(0)
        elif action == "cancel":
            set_state(screen="idle")

    elif s == "list_view":
        if action == "back":
            set_state(screen="menu")
        elif action == "prev":
            page = get_state("items_page") or 0
            if page > 0:
                set_state(items_page=page - 1)
        elif action == "next":
            n = len(get_state("items") or [])
            page = get_state("items_page") or 0
            n_pages = max(1, (n + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE)
            if page < n_pages - 1:
                set_state(items_page=page + 1)
        elif isinstance(action, tuple) and action and action[0] == "delete":
            _, uid, name = action
            _thread(_delete_item, uid, name)

    elif s == "choice":
        if action == "auto":
            for p in [FRONT_PHOTO, BACK_PHOTO]:
                if os.path.exists(p):
                    os.remove(p)
            set_state(screen="front_prompt", error="")
        elif action == "webui":
            _thread(_webui_then_idle)

    elif s == "front_prompt":
        if action == "take_front":
            _thread(_capture_front)
        elif action == "cancel":
            set_state(screen="idle", barcode="", result=None, error="")

    elif s == "back_prompt":
        if action == "take_back":
            _thread(_capture_back)
        elif action == "identify_now":
            _thread(_run_gemini)
        elif action == "cancel":
            set_state(screen="idle", barcode="", result=None, error="")

    elif s == "webui_hint":
        if action == "back":
            set_state(screen="idle")

    elif s == "result_screen":
        if action == "accept" and result:
            _thread(_do_confirm, barcode, result)
        elif action == "retry":
            if os.path.exists(BACK_PHOTO):
                os.remove(BACK_PHOTO)
            set_state(screen="front_prompt", error="")
        elif action == "webui":
            _thread(_webui_then_idle)
        elif action == "cancel":
            set_state(screen="idle", barcode="", result=None, error="")

# ── Data helpers ──────────────────────────────────────────────────────────────

def lookup_custom(barcode):
    try:
        with open(CUSTOM_MAP) as f:
            return json.load(f).get(barcode)
    except Exception:
        return None

def lookup_product(barcode):
    try:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        r   = requests.get(url, headers={"User-Agent": "GroceryScanner/0.1 (nelsonmoreira@gmail.com)"}, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("status") != 1:
            return None
        p    = data.get("product", {})
        name = ""
        for lang in LANG_PRIORITY:
            name = p.get(f"product_name_{lang}", "").strip()
            if name:
                break
        if not name:
            name = p.get("product_name", "").strip()
        # Wider fallback: try any product_name_* field
        if not name:
            for key, val in p.items():
                if key.startswith("product_name_") and val and val.strip():
                    name = val.strip()
                    break
        brand    = p.get("brands", "").split(",")[0].strip()
        quantity = p.get("quantity", "").strip()
        if not name and not brand:
            return None
        if not name:
            name, brand = brand, ""
        return {"name": name, "brand": brand, "quantity": quantity}
    except Exception:
        return None

def fetch_shopping_items():
    """Returns active items [{uid, summary, status}, …] or None on error."""
    try:
        r = requests.post(
            f"{HA_URL}/api/services/todo/get_items?return_response",
            headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"},
            json={"entity_id": HA_TODO_ENTITY}, timeout=5,
        )
        if r.status_code != 200:
            return None
        data   = r.json()
        bucket = data.get("service_response", {}).get(HA_TODO_ENTITY, {})
        items  = bucket.get("items", []) or []
        return [it for it in items if it.get("status") != "completed"]
    except Exception:
        return None

def remove_from_bring(uid_or_name):
    try:
        r = requests.post(
            f"{HA_URL}/api/services/todo/remove_item",
            headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"},
            json={"entity_id": HA_TODO_ENTITY, "item": uid_or_name}, timeout=5,
        )
        return r.status_code in (200, 201)
    except Exception:
        return False

def add_to_bring(name, brand="", quantity=""):
    """Returns one of 'added', 'duplicate', 'error'."""
    items = fetch_shopping_items()
    if items is not None:
        nl = name.strip().lower()
        if any((it.get("summary") or "").strip().lower() == nl for it in items):
            return "duplicate"
    # else: list fetch failed → fall through and add (best-effort)

    parts   = [p for p in [brand, quantity] if p]
    payload = {"entity_id": HA_TODO_ENTITY, "item": name}
    if parts:
        payload["description"] = " • ".join(parts)
    try:
        r = requests.post(
            f"{HA_URL}/api/services/todo/add_item",
            headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=5,
        )
        return "added" if r.status_code in (200, 201) else "error"
    except Exception:
        return "error"

def _log_unknown(barcode):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(UNKNOWN_LOG, "a") as f:
        f.write(json.dumps({"barcode": barcode,
                            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat()}) + "\n")

def _remove_unknown(barcode):
    if not os.path.exists(UNKNOWN_LOG):
        return
    lines = []
    with open(UNKNOWN_LOG) as f:
        for line in f:
            try:
                if json.loads(line).get("barcode") != barcode:
                    lines.append(line)
            except Exception:
                lines.append(line)
    with open(UNKNOWN_LOG, "w") as f:
        f.writelines(lines)

def _save_custom(barcode, name):
    try:
        data = {}
        if os.path.exists(CUSTOM_MAP):
            with open(CUSTOM_MAP) as f:
                data = json.load(f)
        data[barcode] = name
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CUSTOM_MAP, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ── Barcode handler ───────────────────────────────────────────────────────────

def handle_barcode(barcode):
    barcode = barcode.strip()
    if not barcode:
        return
    if _screen_blanked:
        _wake_screen()
    _mark_activity()
    if get_state("screen") not in ("idle", "known_ok", "known_err", "already_in_list", "menu"):
        return
    set_state(screen="lookup", barcode=barcode)

    custom_name = lookup_custom(barcode)
    if custom_name:
        status = add_to_bring(custom_name)
        if status == "added":
            set_state(screen="known_ok",        product_name=custom_name, product_detail="Custom barcode")
        elif status == "duplicate":
            set_state(screen="already_in_list", product_name=custom_name, product_detail="Custom barcode")
        else:
            set_state(screen="known_err",       product_name=custom_name, product_detail="Custom barcode")
        time.sleep(3)
        if get_state("screen") in ("known_ok", "known_err", "already_in_list"):
            set_state(screen="idle", barcode="")
        return

    product = lookup_product(barcode)
    if product is None:
        _log_unknown(barcode)
        set_state(screen="unknown_screen", barcode=barcode)
        return

    name   = product["name"]
    brand  = product["brand"]
    qty    = product["quantity"]
    detail = " • ".join(p for p in [brand, qty] if p)
    status = add_to_bring(name, brand, qty)
    if status == "added":
        set_state(screen="known_ok",        product_name=name, product_detail=detail)
    elif status == "duplicate":
        set_state(screen="already_in_list", product_name=name, product_detail=detail)
    else:
        set_state(screen="known_err",       product_name=name, product_detail=detail)
    time.sleep(3)
    if get_state("screen") in ("known_ok", "known_err", "already_in_list"):
        set_state(screen="idle", barcode="")

# ── Scanner loop ──────────────────────────────────────────────────────────────

def scanner_loop():
    dev = InputDevice(SCANNER_DEVICE)
    dev.grab()
    buf = ""
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            key = categorize(event)
            if key.keystate == key.key_up:
                ch = KEYMAP.get(key.scancode)
                if ch == "\n":
                    threading.Thread(target=handle_barcode, args=(buf,), daemon=True).start()
                    buf = ""
                elif ch:
                    buf += ch

# ── Main loop ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Disable X11 auto-blanking so we control the display ourselves
    subprocess.run(["xset", "-display", ":0", "s", "off"],      capture_output=True)
    subprocess.run(["xset", "-display", ":0", "s", "noblank"],  capture_output=True)
    subprocess.run(["xset", "-display", ":0", "-dpms"],         capture_output=True)

    _mark_activity()
    set_state(screen="idle")
    threading.Thread(target=scanner_loop, daemon=True).start()
    print("Scanner daemon running. Ctrl+C to quit.")
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    handle_touch(event.pos)

            if needs_render.is_set():
                needs_render.clear()
                render_current()

            if not _screen_blanked and time.time() - _last_activity > BLANK_TIMEOUT:
                _blank_screen()

            time.sleep(0.05)
    except KeyboardInterrupt:
        pygame.quit()
