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
MANUAL_LOG     = os.path.join(DATA_DIR, "manual_items.jsonl")

FRONT_PHOTO    = "/tmp/grocery_front.jpg"
BACK_PHOTO     = "/tmp/grocery_back.jpg"
BLANK_TIMEOUT       = 30  # seconds of inactivity before display off
IDLE_RETURN_TIMEOUT = 90  # seconds of inactivity before transient screens return to idle
LIST_PAGE_SIZE      = 5   # shopping-list rows per page in the list view

# Screens that should auto-return to idle after IDLE_RETURN_TIMEOUT of inactivity.
# Excludes: idle (no-op), lookup/processing/list_loading (mid-network), and the
# confirmed/known_ok/known_err/already_in_list screens that already auto-return
# from their own threads. Mid-Gemini-flow screens (front/back/result) are also
# left alone — bouncing out mid-photo would be jarring.
IDLE_RETURN_FROM = {"list_view", "manual_input", "menu", "webui_hint"}

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
    "input_name":       "",
    "input_desc":       "",
    "desc_open":        False,
    "active_field":     "name",     # name | desc
    "kb_layer":         "letters",  # letters | numbers | accents
    "kb_shift":         False,
    "recents":          [],         # [{"name":..., "desc":...}]
    "suggest":          [],         # autocomplete chips for input_name
}

# ── Virtual keyboard layout ───────────────────────────────────────────────────

KB_KEY_H       = 56
KB_GAP         = 4
KB_BOTTOM_PAD  = 8

LAYERS = {
    "letters":  [["q","w","e","r","t","y","u","i","o","p"],
                 ["a","s","d","f","g","h","j","k","l"],
                 [None,"z","x","c","v","b","n","m",None]],   # row3 inner letters
    "numbers":  [["1","2","3","4","5","6","7","8","9","0"],
                 ["-","/",":",";","(",")","€","&","@"],
                 [None,"'",",",".","?","!","-","\"",None]],
    "accents":  [["ä","ö","ü","ß","á","é","í","ó","ú","ñ"],
                 ["Ä","Ö","Ü","À","É","Í","Ó","Ú","Ñ"],
                 [None,"ç","¿","¡","-","'",",",".",None]],
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

    # "+" manual-entry shortcut, top right
    add_btn = Button("+", pygame.Rect(W - 70, 10, 56, 40), C["green"], "manual_add")
    active_buttons.append(add_btn)
    _draw_button(add_btn)

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

def _load_manual_history(limit=8):
    """Read manual_items.jsonl, dedupe by name (latest desc wins), return up to `limit` dicts
    in most-recent-first order."""
    if not os.path.exists(MANUAL_LOG):
        return []
    out, seen = [], set()
    try:
        with open(MANUAL_LOG, encoding="utf-8") as f:
            entries = [json.loads(line) for line in f if line.strip()]
        for e in reversed(entries):
            n = (e.get("name") or "").strip()
            if not n:
                continue
            key = n.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({"name": n, "desc": (e.get("desc") or "").strip()})
            if len(out) >= limit:
                break
    except Exception:
        return []
    return out

def _save_manual(name, desc):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(MANUAL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "name": name,
                "desc": desc,
                "ts":   datetime.datetime.now(datetime.timezone.utc).isoformat()
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _suggest(prefix, history, limit=3):
    if not prefix:
        return []
    p = prefix.lower()
    return [h for h in history if h["name"].lower().startswith(p)][:limit]

def _build_keyboard(kb_layer, kb_shift):
    """Return list of Button objects for current keyboard layer."""
    rows    = LAYERS[kb_layer]
    btns    = []
    key_w   = 76
    side_w  = 100   # shift / backspace / layer toggles
    add_w   = 180

    kb_total_h = 4 * KB_KEY_H + 3 * KB_GAP
    kb_top     = H - kb_total_h - KB_BOTTOM_PAD

    # Row 1 — 10 keys
    keys  = rows[0]
    row_w = 10 * key_w + 9 * KB_GAP
    x0    = (W - row_w) // 2
    y     = kb_top
    for i, ch in enumerate(keys):
        ch_eff = ch.upper() if (kb_shift and ch.isalpha()) else ch
        rect   = pygame.Rect(x0 + i * (key_w + KB_GAP), y, key_w, KB_KEY_H)
        btns.append(Button(ch_eff, rect, (50, 50, 50), ("key", ch_eff)))

    # Row 2 — 9 keys (offset half-key for stagger)
    keys  = rows[1]
    row_w = 9 * key_w + 8 * KB_GAP
    x0    = (W - row_w) // 2
    y     = kb_top + (KB_KEY_H + KB_GAP)
    for i, ch in enumerate(keys):
        ch_eff = ch.upper() if (kb_shift and ch.isalpha()) else ch
        rect   = pygame.Rect(x0 + i * (key_w + KB_GAP), y, key_w, KB_KEY_H)
        btns.append(Button(ch_eff, rect, (50, 50, 50), ("key", ch_eff)))

    # Row 3 — shift/abc + 7 inner keys + backspace
    inner = [k for k in rows[2] if k is not None]
    row_w = side_w + KB_GAP + len(inner) * key_w + (len(inner) - 1) * KB_GAP + KB_GAP + side_w
    x0    = (W - row_w) // 2
    y     = kb_top + 2 * (KB_KEY_H + KB_GAP)

    if kb_layer == "letters":
        sh_label, sh_action, sh_color = "Shift", ("kb", "shift"), (C["blue"] if kb_shift else (60, 60, 70))
    else:
        sh_label, sh_action, sh_color = "abc", ("kb_layer", "letters"), (60, 60, 70)
    btns.append(Button(sh_label, pygame.Rect(x0, y, side_w, KB_KEY_H), sh_color, sh_action))

    x = x0 + side_w + KB_GAP
    for ch in inner:
        ch_eff = ch.upper() if (kb_shift and ch.isalpha()) else ch
        btns.append(Button(ch_eff, pygame.Rect(x, y, key_w, KB_KEY_H), (50, 50, 50), ("key", ch_eff)))
        x += key_w + KB_GAP
    btns.append(Button("⌫", pygame.Rect(x, y, side_w, KB_KEY_H), (60, 60, 70), ("kb", "back")))

    # Row 4 — layer toggles + space + Add
    y = kb_top + 3 * (KB_KEY_H + KB_GAP)
    if kb_layer == "letters":
        t1_label, t1_action = "123",  ("kb_layer", "numbers")
        t2_label, t2_action = "äöü",  ("kb_layer", "accents")
    elif kb_layer == "numbers":
        t1_label, t1_action = "abc",  ("kb_layer", "letters")
        t2_label, t2_action = "äöü",  ("kb_layer", "accents")
    else:  # accents
        t1_label, t1_action = "abc",  ("kb_layer", "letters")
        t2_label, t2_action = "123",  ("kb_layer", "numbers")

    fixed_total = side_w + side_w + add_w + 3 * KB_GAP
    space_w     = (W - 28) - fixed_total
    margin      = (W - (fixed_total + space_w)) // 2
    x           = margin

    btns.append(Button(t1_label, pygame.Rect(x, y, side_w, KB_KEY_H), (60, 60, 70), t1_action))
    x += side_w + KB_GAP
    btns.append(Button(t2_label, pygame.Rect(x, y, side_w, KB_KEY_H), (60, 60, 70), t2_action))
    x += side_w + KB_GAP
    btns.append(Button("space", pygame.Rect(x, y, space_w, KB_KEY_H), (50, 50, 50), ("key", " ")))
    x += space_w + KB_GAP
    btns.append(Button("Add", pygame.Rect(x, y, add_w, KB_KEY_H), C["green"], ("submit",)))

    return btns

def _render_manual_input():
    active_buttons.clear()
    screen.fill(C["dark"])

    name         = get_state("input_name")
    desc         = get_state("input_desc")
    desc_open    = get_state("desc_open")
    active_field = get_state("active_field")
    kb_layer     = get_state("kb_layer")
    kb_shift     = get_state("kb_shift")
    recents      = get_state("recents") or []
    suggest      = get_state("suggest") or []

    # Header
    _center("Add item", font_medium, WHITE, 22)
    close_btn = Button("X", pygame.Rect(W - 60, 6, 50, 38), (90, 60, 60), ("close",))
    active_buttons.append(close_btn)
    _draw_button(close_btn)

    # Name input
    name_y = 50
    name_rect = pygame.Rect(20, name_y, W - 40, 50)
    name_active = active_field == "name"
    border = (110, 160, 220) if name_active else (70, 75, 90)
    pygame.draw.rect(screen, (40, 45, 55), name_rect, border_radius=8)
    pygame.draw.rect(screen, border, name_rect, width=2, border_radius=8)
    if not name:
        ph = font_small.render("Item name", True, DIM)
        screen.blit(ph, (name_rect.x + 14, name_rect.y + (name_rect.h - ph.get_height()) // 2))
    else:
        text = name + ("|" if name_active else "")
        nm = font_small.render(text, True, WHITE)
        screen.blit(nm, (name_rect.x + 14, name_rect.y + (name_rect.h - nm.get_height()) // 2))
    active_buttons.append(Button("name", name_rect, (40, 45, 55), ("focus", "name")))

    # Description input (when open)
    if desc_open:
        desc_y = name_y + 54
        desc_rect = pygame.Rect(20, desc_y, W - 40, 50)
        desc_active = active_field == "desc"
        border = (110, 160, 220) if desc_active else (70, 75, 90)
        pygame.draw.rect(screen, (40, 45, 55), desc_rect, border_radius=8)
        pygame.draw.rect(screen, border, desc_rect, width=2, border_radius=8)
        if not desc:
            ph = font_small.render("Description (optional)", True, DIM)
            screen.blit(ph, (desc_rect.x + 14, desc_rect.y + (desc_rect.h - ph.get_height()) // 2))
        else:
            text = desc + ("|" if desc_active else "")
            dt = font_small.render(text, True, WHITE)
            screen.blit(dt, (desc_rect.x + 14, desc_rect.y + (desc_rect.h - dt.get_height()) // 2))
        active_buttons.append(Button("desc", desc_rect, (40, 45, 55), ("focus", "desc")))
        toggle_y = desc_y + 54
    else:
        toggle_y = name_y + 54

    # +/- desc toggle (small text button, right aligned)
    tog_label = "− desc" if desc_open else "+ desc"
    tog_rect = pygame.Rect(W - 130, toggle_y, 110, 26)
    txt = font_tiny.render(tog_label, True, (140, 200, 255))
    screen.blit(txt, txt.get_rect(center=tog_rect.center))
    active_buttons.append(Button(tog_label, tog_rect, C["dark"], ("toggle_desc",)))

    # Chip row — recents (when name empty) or autocomplete suggestions
    chips_y = toggle_y + 32
    chips_h = 40
    chips = suggest if name else recents

    if chips:
        x = 16
        gap = 6
        for c in chips:
            label = c["name"]
            if c.get("desc"):
                label += f" ({c['desc']})"
            label_w = font_tiny.size(label)[0]
            rect_w = label_w + 24
            if x + rect_w > W - 16:
                break
            rect = pygame.Rect(x, chips_y, rect_w, chips_h)
            pygame.draw.rect(screen, (50, 80, 110), rect, border_radius=chips_h // 2)
            t = font_tiny.render(label, True, WHITE)
            screen.blit(t, t.get_rect(center=rect.center))
            active_buttons.append(Button(label, rect, (50, 80, 110), ("chip", c["name"], c.get("desc", ""))))
            x += rect_w + gap
    elif not name:
        s = font_tiny.render("(no recent items yet)", True, DIM)
        screen.blit(s, s.get_rect(center=(W // 2, chips_y + chips_h // 2)))

    # Keyboard
    for btn in _build_keyboard(kb_layer, kb_shift):
        pygame.draw.rect(screen, btn.color, btn.rect, border_radius=6)
        font = font_button if len(btn.label) <= 5 else font_tiny
        txt = font.render(btn.label, True, WHITE)
        screen.blit(txt, txt.get_rect(center=btn.rect.center))
        active_buttons.append(btn)

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
    elif s == "manual_input":     _render_manual_input()

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

def _do_manual_add(name, desc):
    """Add a manually-typed item to Bring!. Dup-checks first, logs to history on success,
    flashes a confirmation, then returns to the shopping list."""
    set_state(processing_label="Adding…", screen="list_loading")

    # Dup check
    items = fetch_shopping_items()
    if items is not None:
        nl = name.lower()
        if any((it.get("summary") or "").strip().lower() == nl for it in items):
            set_state(screen="already_in_list", product_name=name, product_detail=desc)
            time.sleep(2)
            if get_state("screen") == "already_in_list":
                fresh = fetch_shopping_items() or []
                set_state(screen="list_view", items=fresh, items_page=0, items_error="",
                          input_name="", input_desc="", desc_open=False,
                          active_field="name", kb_shift=False, kb_layer="letters",
                          suggest=[])
            return

    # POST to HA todo.add_item
    payload = {"entity_id": HA_TODO_ENTITY, "item": name}
    if desc:
        payload["description"] = desc
    try:
        r = requests.post(
            f"{HA_URL}/api/services/todo/add_item",
            headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=5,
        )
        ok = r.status_code in (200, 201)
    except Exception:
        ok = False

    if not ok:
        # Re-show the manual_input screen so the user can retry without losing what they typed
        set_state(screen="manual_input")
        return

    _save_manual(name, desc)

    # Brief green confirmation, then back to a refreshed list view
    set_state(screen="confirmed", product_name=name, product_detail=desc)
    time.sleep(1.5)
    if get_state("screen") == "confirmed":
        fresh = fetch_shopping_items() or []
        set_state(screen="list_view", items=fresh, items_page=0, items_error="",
                  input_name="", input_desc="", desc_open=False,
                  active_field="name", kb_shift=False, kb_layer="letters",
                  suggest=[])

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
        elif action == "manual_add":
            set_state(screen="manual_input",
                      input_name="", input_desc="", desc_open=False,
                      active_field="name", kb_shift=False, kb_layer="letters",
                      recents=_load_manual_history(), suggest=[])
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

    elif s == "manual_input":
        if not isinstance(action, tuple):
            return
        tag = action[0]

        if tag == "close":
            _thread(_load_shopping_list)

        elif tag == "toggle_desc":
            now_open = not get_state("desc_open")
            set_state(desc_open=now_open,
                      active_field="desc" if now_open else "name")

        elif tag == "focus":
            set_state(active_field=action[1])

        elif tag == "key":
            ch = action[1]
            # Apply sticky shift: uppercase the char and clear shift
            if get_state("kb_shift") and len(ch) == 1 and ch.isalpha():
                ch = ch.upper()
                set_state(kb_shift=False)
            af = get_state("active_field")
            if af == "name":
                new_name = get_state("input_name") + ch
                set_state(input_name=new_name,
                          suggest=_suggest(new_name, get_state("recents") or []))
            else:
                set_state(input_desc=get_state("input_desc") + ch)

        elif tag == "kb":
            sub = action[1]
            if sub == "shift":
                set_state(kb_shift=not get_state("kb_shift"))
            elif sub == "back":
                af = get_state("active_field")
                if af == "name":
                    new_name = get_state("input_name")[:-1]
                    set_state(input_name=new_name,
                              suggest=_suggest(new_name, get_state("recents") or []))
                else:
                    set_state(input_desc=get_state("input_desc")[:-1])

        elif tag == "kb_layer":
            set_state(kb_layer=action[1], kb_shift=False)

        elif tag == "submit":
            name = (get_state("input_name") or "").strip()
            desc = (get_state("input_desc") or "").strip()
            if name:
                _thread(_do_manual_add, name, desc)

        elif tag == "chip":
            _, cname, cdesc = action
            set_state(input_name=cname, input_desc=cdesc,
                      desc_open=bool(cdesc),
                      active_field="name",
                      suggest=[])

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

            # Return transient screens to idle after a longer inactivity window.
            # Self-limiting: once on idle, the condition no longer matches.
            if time.time() - _last_activity > IDLE_RETURN_TIMEOUT:
                if get_state("screen") in IDLE_RETURN_FROM:
                    set_state(screen="idle", barcode="", result=None, error="",
                              product_name="", product_detail="",
                              items=[], items_page=0, items_error="",
                              input_name="", input_desc="", desc_open=False,
                              active_field="name", kb_shift=False, kb_layer="letters",
                              suggest=[])

            time.sleep(0.05)
    except KeyboardInterrupt:
        pygame.quit()
