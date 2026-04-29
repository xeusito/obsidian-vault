import os
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

load_dotenv()

HA_URL         = os.getenv("HA_URL")
HA_TOKEN       = os.getenv("HA_TOKEN")
HA_TODO_ENTITY = os.getenv("HA_TODO_ENTITY")
DATA_DIR       = os.getenv("DATA_DIR", "./data")
UNKNOWN_LOG    = os.path.join(DATA_DIR, "unknown.jsonl")
CUSTOM_MAP     = os.path.join(DATA_DIR, "custom_barcodes.json")

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.after_request
def allow_iframe(resp):
    resp.headers["X-Frame-Options"] = "ALLOWALL"
    resp.headers["Content-Security-Policy"] = "frame-ancestors *"
    return resp

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_unknown():
    if not os.path.exists(UNKNOWN_LOG):
        return []
    seen, items = set(), []
    with open(UNKNOWN_LOG) as f:
        for line in f:
            try:
                entry = json.loads(line)
                bc = entry.get("barcode", "")
                if bc and bc not in seen and not entry.get("resolved"):
                    seen.add(bc)
                    items.append(entry)
            except Exception:
                pass
    return items

def remove_unknown(barcode):
    if not os.path.exists(UNKNOWN_LOG):
        return
    lines = []
    with open(UNKNOWN_LOG) as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get("barcode") != barcode:
                    lines.append(line)
            except Exception:
                lines.append(line)
    with open(UNKNOWN_LOG, "w") as f:
        f.writelines(lines)

def load_custom():
    if not os.path.exists(CUSTOM_MAP):
        return {}
    with open(CUSTOM_MAP) as f:
        return json.load(f)

def save_custom(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CUSTOM_MAP, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_to_bring(name, description=""):
    payload = {"entity_id": HA_TODO_ENTITY, "item": name}
    if description:
        payload["description"] = description
    try:
        r = requests.post(
            f"{HA_URL}/api/services/todo/add_item",
            headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"},
            json=payload, timeout=5,
        )
        return r.status_code in (200, 201)
    except Exception:
        return False

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("unknown"))

@app.route("/unknown")
def unknown():
    return render_template("unknown.html", items=load_unknown())

@app.route("/unknown/resolve", methods=["POST"])
def resolve():
    barcode = request.form.get("barcode", "").strip()
    name    = request.form.get("name", "").strip()
    if not barcode or not name:
        flash("Barcode and name are required.", "err")
        return redirect(url_for("unknown"))
    if add_to_bring(name):
        remove_unknown(barcode)
        data = load_custom()
        data[barcode] = name
        save_custom(data)
        flash(f"'{name}' added to Bring! and saved — scanner will recognise it next time.", "ok")
    else:
        flash("Failed to reach Home Assistant.", "err")
    return redirect(url_for("unknown"))

@app.route("/unknown/dismiss", methods=["POST"])
def dismiss():
    barcode = request.form.get("barcode", "").strip()
    if barcode:
        remove_unknown(barcode)
        flash(f"Barcode {barcode} dismissed.", "ok")
    return redirect(url_for("unknown"))

@app.route("/custom")
def custom():
    data = load_custom()
    edit_barcode = request.args.get("edit", "")
    return render_template("custom.html", items=sorted(data.items()), edit_barcode=edit_barcode)

@app.route("/custom/edit", methods=["POST"])
def custom_edit():
    barcode = request.form.get("barcode", "").strip()
    name    = request.form.get("name", "").strip()
    if not barcode or not name:
        flash("Name is required.", "err")
        return redirect(url_for("custom"))
    data = load_custom()
    if barcode in data:
        data[barcode] = name
        save_custom(data)
        flash(f"'{barcode}' updated to '{name}'.", "ok")
    return redirect(url_for("custom"))

@app.route("/custom/add", methods=["POST"])
def custom_add():
    barcode = request.form.get("barcode", "").strip()
    name    = request.form.get("name", "").strip()
    if not barcode or not name:
        flash("Both fields are required.", "err")
        return redirect(url_for("custom"))
    data = load_custom()
    data[barcode] = name
    save_custom(data)
    flash(f"'{barcode}' → '{name}' saved.", "ok")
    return redirect(url_for("custom"))

@app.route("/custom/delete", methods=["POST"])
def custom_delete():
    barcode = request.form.get("barcode", "").strip()
    data = load_custom()
    if barcode in data:
        del data[barcode]
        save_custom(data)
        flash(f"Barcode {barcode} deleted.", "ok")
    return redirect(url_for("custom"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
