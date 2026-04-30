# Projects Dashboard

> [!tip] Plugin views
> Open the **Project Manager** panel for interactive Gantt, Kanban, and Table views → click the `chart-gantt` icon in the ribbon, or run **Project Manager: Open projects** from the command palette.

## Timeline

```dataviewjs
// ── Helpers ──────────────────────────────────────────────────────────────────
const toStr = d => {
    if (!d) return null
    if (d?.toISODate) return d.toISODate()          // Luxon DateTime (Dataview)
    if (typeof d === "string") return d
    return new Date(d).toISOString().slice(0, 10)
}
const toMs  = d => new Date(toStr(d) + "T00:00:00").getTime()
const addDay = s => { const d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + 1); return d.toISOString().slice(0, 10) }

// ── Data ─────────────────────────────────────────────────────────────────────
const projMap = {}
for (const p of dv.pages('"Projects"').where(p => p["pm-project"] === true))
    projMap[p.id] = { title: p.title, icon: p.icon ?? "", color: p.color ?? "#8a94a0" }

const allTasks = dv.pages('"Projects"')
    .where(t => t["pm-task"] === true && t.start && t.due)
    .sort(t => t.start, "asc")
    .array()

const byProject = {}
for (const t of allTasks) {
    if (!byProject[t.projectId]) byProject[t.projectId] = []
    byProject[t.projectId].push(t)
}
const sortedPids = Object.keys(byProject).sort((a, b) =>
    toMs(byProject[a][0].start) - toMs(byProject[b][0].start))

// ── Date range ────────────────────────────────────────────────────────────────
const allMs  = allTasks.flatMap(t => [toMs(t.start), toMs(t.due)])
const rangeStart = new Date(Math.min(...allMs)); rangeStart.setDate(rangeStart.getDate() - 5)
const rangeEnd   = new Date(Math.max(...allMs)); rangeEnd.setDate(rangeEnd.getDate() + 10)
const totalMs    = rangeEnd - rangeStart

const pct     = d => ((toMs(d) - rangeStart) / totalMs * 100).toFixed(3) + "%"
const widthPct = (s, e) => Math.max((toMs(e) - toMs(s)) / totalMs * 100, 0.8).toFixed(3) + "%"
const todayPct = ((Date.now() - rangeStart) / totalMs * 100).toFixed(3) + "%"

// ── Month markers ─────────────────────────────────────────────────────────────
const months = []
const cur = new Date(rangeStart.getFullYear(), rangeStart.getMonth(), 1)
while (cur <= rangeEnd) {
    const p = ((cur - rangeStart) / totalMs * 100)
    if (p >= 0) months.push({ label: cur.toLocaleString("default", { month: "short", year: "2-digit" }), pct: p.toFixed(3) })
    cur.setMonth(cur.getMonth() + 1)
}

// ── Status colours ────────────────────────────────────────────────────────────
const COLOR = { done: "#79b58d", "in-progress": "#8b72be", blocked: "#c47070", todo: "#8a94a0" }

// ── Styles ───────────────────────────────────────────────────────────────────
const wrap = this.container.createDiv()
wrap.createEl("style").textContent = `
.pmg { width:100%; border-spacing:0; border-collapse:collapse; font-size:12px; font-family:var(--font-interface); }
.pmg td, .pmg th { padding:0; margin:0; }
.pmg-label { width:190px; min-width:190px; max-width:190px; padding:2px 10px 2px 4px;
             white-space:nowrap; overflow:hidden; text-overflow:ellipsis; vertical-align:middle;
             color:var(--text-muted); border-right:1px solid var(--background-modifier-border); }
.pmg-section .pmg-label { color:var(--text-normal); font-weight:600; font-size:11px;
                           background:var(--background-secondary); text-transform:uppercase;
                           letter-spacing:.04em; padding-top:8px; }
.pmg-tl { position:relative; }
.pmg-bar { position:absolute; height:16px; border-radius:3px; top:4px;
           display:flex; align-items:center; padding:0 5px; overflow:hidden;
           white-space:nowrap; font-size:10px; color:#fff; box-sizing:border-box;
           min-width:4px; cursor:default; }
.pmg-today { position:absolute; top:0; bottom:0; width:2px;
             background:var(--color-red); opacity:.6; pointer-events:none; }
.pmg-grid  { position:absolute; top:0; bottom:0; width:1px;
             background:var(--background-modifier-border); opacity:.6; }
.pmg-month { position:absolute; top:3px; font-size:10px; color:var(--text-muted);
             white-space:nowrap; padding-left:3px; }
`

// ── Table ─────────────────────────────────────────────────────────────────────
const tbl = wrap.createEl("table", { cls: "pmg" })

// Header row (date axis)
const hrow = tbl.createEl("thead").createEl("tr")
hrow.createEl("th", { cls: "pmg-label" })
const htl = hrow.createEl("th", { cls: "pmg-tl" })
htl.style.cssText = "height:22px;"
for (const m of months) {
    const g = htl.createDiv({ cls: "pmg-grid" }); g.style.left = m.pct + "%"
    const l = htl.createDiv({ cls: "pmg-month" }); l.style.left = m.pct + "%"; l.textContent = m.label
}
const todayH = htl.createDiv({ cls: "pmg-today" }); todayH.style.left = todayPct

// Body rows
const tbody = tbl.createEl("tbody")
for (const pid of sortedPids) {
    const proj = projMap[pid]

    // Section header
    const srow = tbody.createEl("tr", { cls: "pmg-section" })
    srow.createEl("td", { cls: "pmg-label", text: proj ? `${proj.icon}  ${proj.title}` : pid })
    const stl = srow.createEl("td", { cls: "pmg-tl" }); stl.style.height = "20px"
    for (const m of months) { const g = stl.createDiv({ cls: "pmg-grid" }); g.style.left = m.pct + "%" }
    stl.createDiv({ cls: "pmg-today" }).style.left = todayPct

    // Task rows
    for (const t of byProject[pid]) {
        const startStr = toStr(t.start)
        const dueStr   = toStr(t.start) === toStr(t.due) ? addDay(toStr(t.due)) : toStr(t.due)
        const color    = COLOR[t.status] ?? COLOR.todo

        const row  = tbody.createEl("tr")
        const lbl  = row.createEl("td", { cls: "pmg-label", text: t.title })
        lbl.title  = t.title
        const cell = row.createEl("td", { cls: "pmg-tl" }); cell.style.height = "24px"

        for (const m of months) { const g = cell.createDiv({ cls: "pmg-grid" }); g.style.left = m.pct + "%" }
        cell.createDiv({ cls: "pmg-today" }).style.left = todayPct

        const bar = cell.createDiv({ cls: "pmg-bar" })
        bar.style.cssText = `left:${pct(startStr)}; width:${widthPct(startStr, dueStr)}; background:${color};`
        bar.title = `${t.title}  ${startStr} → ${toStr(t.due)}  [${t.status}]`
    }
}

// ── Legend ────────────────────────────────────────────────────────────────────
const leg = wrap.createDiv()
leg.style.cssText = "margin-top:8px; display:flex; gap:14px; font-size:11px; color:var(--text-muted);"
for (const [label, color] of [["Done","#79b58d"],["In Progress","#8b72be"],["Blocked","#c47070"],["To Do","#8a94a0"]]) {
    const item = leg.createDiv(); item.style.cssText = "display:flex; align-items:center; gap:4px;"
    const dot = item.createDiv(); dot.style.cssText = `width:10px; height:10px; border-radius:2px; background:${color};`
    item.createSpan({ text: label })
}
```

---

## 🟢 In Progress

> [!note] Presence Detection in the Hallway
> **Due:** 2026-05-17 · **Priority:** High
>
> Detect presence in the hallway and switch ceiling or soft glow light based on time of day. Hardware is live and streaming to HA.
>
> **Remaining:** mount sensor → recalibrate zones → build HA automation → HDMI CEC display control
>
> → [[🟢 Presence Detection in the Hallway/index|Open project]]

---

## 🔴 Blocked

> [!warning] Solar E-Ink Door Display
> **Due:** 2026-07-15 · **Priority:** Medium · **Blocker:** Kiwi Electronics parcel (ESP32C6, MAX17048, cables)
>
> Solar-powered e-ink display behind the front door — calendar events, trash schedule, HA alerts.
>
> **Next after parts arrive:** ESPHome config → breadboard prototype → 3D enclosure
>
> → [[🟡 Solar E-Ink Door Display/index|Open project]]

---

## ⬜ To Do

> [!todo] Downloads Assistant v2.0
> **Due:** 2026-05-31 · **Priority:** Medium
>
> Browser-based Downloads folder assistant — AI chat + categorised file panels. Python agent on laptop, FastAPI + React on Proxmox LXC 226, Featherless.ai LLM.
>
> **Next:** enable OpenSSH on laptop → create LXC 226 → SSH key setup
>
> → [[🟡 Downloads Assistant v2.0/index|Open project]]

---

---

## ✅ Done

> [!success] Grocery List Automation — v1.0
> **Completed:** 2026-04-30
>
> Kitchen-counter Raspberry Pi barcode scanner — scan → OpenFoodFacts → Bring! via HA. Honeywell 7580 + BTT TFT50 touchscreen + Pi camera with Gemini 2.5 Flash AI fallback. CPU thermal monitoring with two-threshold HA alerts. SKADIS-mounted 3D-printed enclosure.
>
> → [[✅ Grocery List Automation/index|Open project]]

> [!success] LAFVIN Endless Runner
> **Completed:** 2026-04-25
>
> One-button Chrome-dino clone on the ESP32-C6 kit. LCD, RGB LED, microSD high-score persistence, 30 fps stable.
>
> → [[✅ LAFVIN Endless Runner/index|Open project]]

---

## 💡 Ideas

- [[../Ideas/solar-iqos-charger|Solar IQOS Charger]]
- [[../Ideas/grocery-list-automation|Grocery List Automation]] ← promoted to project
