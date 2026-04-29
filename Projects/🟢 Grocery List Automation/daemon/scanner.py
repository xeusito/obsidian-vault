import os
import sys
import json
import time
import threading
import datetime
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

FRONT_PHOTO = "/tmp/grocery_front.jpg"
BACK_PHOTO  = "/tmp/grocery_back.jpg"

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
    _center("Scanner Menu", font_medium, WHITE, 80)
    btns = [
        Button("Restart",  pygame.Rect( 40, 190, 330, 90), C["blue"], "restart"),
        Button("Close",    pygame.Rect(410, 190, 330, 90), C["red"],  "close"),
        Button("Cancel",   pygame.Rect(W // 2 - 120, 330, 240, 70), C["grey"], "cancel"),
    ]
    active_buttons.extend(btns)
    for b in btns:
        _draw_button(b)
    pygame.display.flip()

def render_current():
    with state_lock:
        s       = app_state["screen"]
        barcode = app_state["barcode"]
        result  = app_state["result"]
        error   = app_state["error"]
        p_name  = app_state["product_name"]
        p_det   = app_state["product_detail"]
        p_label = app_state["processing_label"]

    if   s == "idle":           _render_idle()
    elif s == "lookup":         _render_simple("idle", "Looking up…", barcode)
    elif s == "known_ok":       _render_simple("green",  p_name, p_det)
    elif s == "known_err":      _render_simple("yellow", p_name, p_det + " — not added")
    elif s == "unknown_screen": _render_unknown(barcode)
    elif s == "choice":         _render_choice(barcode)
    elif s == "front_prompt":   _render_front_prompt(error)
    elif s == "back_prompt":    _render_back_prompt(error)
    elif s == "processing":     _render_processing(p_label)
    elif s == "result_screen":  _render_result(result, error)
    elif s == "confirmed":      _render_simple("green", "Added to Bring!", p_name)
    elif s == "webui_hint":     _render_webui_hint()
    elif s == "menu":           _render_menu()

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

    if add_to_bring(name, brand, qty):
        _remove_unknown(barcode)
        _save_custom(barcode, name)
        set_state(screen="confirmed")
        _thread(upload_to_openfoodfacts, barcode, name, brand, qty, FRONT_PHOTO)
        time.sleep(2)
        if get_state("screen") == "confirmed":
            set_state(screen="idle", barcode="", result=None, error="",
                      product_name="", product_detail="")
    else:
        set_state(screen="result_screen", error="HA error — not added")

def _webui_then_idle():
    set_state(screen="webui_hint")
    time.sleep(5)
    if get_state("screen") == "webui_hint":
        set_state(screen="idle", barcode="", result=None, error="")

# ── Touch handler ─────────────────────────────────────────────────────────────

def handle_touch(pos):
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
        if action == "restart":
            pygame.quit()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        elif action == "close":
            pygame.quit()
            sys.exit(0)
        elif action == "cancel":
            set_state(screen="idle")

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

def add_to_bring(name, brand="", quantity=""):
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
        return r.status_code in (200, 201)
    except Exception:
        return False

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
    if get_state("screen") not in ("idle", "known_ok", "known_err", "menu"):
        return
    set_state(screen="lookup", barcode=barcode)

    custom_name = lookup_custom(barcode)
    if custom_name:
        success = add_to_bring(custom_name)
        if success:
            set_state(screen="known_ok", product_name=custom_name, product_detail="Custom barcode")
        else:
            set_state(screen="known_err", product_name=custom_name, product_detail="Custom barcode")
        time.sleep(3)
        if get_state("screen") in ("known_ok", "known_err"):
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
    if add_to_bring(name, brand, qty):
        set_state(screen="known_ok", product_name=name, product_detail=detail)
    else:
        set_state(screen="known_err", product_name=name, product_detail=detail)
    time.sleep(3)
    if get_state("screen") in ("known_ok", "known_err"):
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

            time.sleep(0.05)
    except KeyboardInterrupt:
        pygame.quit()
