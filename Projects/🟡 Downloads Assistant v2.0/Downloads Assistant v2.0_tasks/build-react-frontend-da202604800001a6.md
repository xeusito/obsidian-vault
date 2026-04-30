---
pm-task: true
projectId: "da2026048001e780"
parentId:
id: "da202604800001a6"
title: "Build React frontend"
type: "task"
status: "todo"
priority: "medium"
start: "2026-05-07"
due: "2026-05-17"
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: ["da202604800001a5"]
collapsed: false
createdAt: "2026-04-28T00:00:00.000Z"
updatedAt: "2026-04-28T00:00:00.000Z"
---

Project: [[Downloads Assistant v2.0|Downloads Assistant v2.0]]

Build `tools/downloads-assistant/client/` — React + Vite.

**Layout:** Two-column. Chat panel left (~35%), file panels right (~65%).

**Components:**
- `ScanStatus.tsx` — animated progress bar + "Scanning… N files found" counter (SSE hook)
- `ChatPanel.tsx` — streaming chat + proactive recommendation card on scan complete
- `FileTable.tsx` — sortable/filterable table with tabs: Documents | Media & Exe | Old Files | Duplicates
- `ActionBar.tsx` — pending count badge + "Review & Apply" button
- `ApplyModal.tsx` — pre-flight action summary → confirm → per-file progress toasts

**Boot UX:**
1. Load → backend checks agent health → if down: "Starting laptop agent…" spinner
2. Agent up → scan auto-starts → SSE progress bar
3. Scan done → panels populate + proactive recs card in chat

**File table columns:** Filename · Size · Last Modified · `✨ Describe` button (lazy) · Action radio (Leave / Keep / Delete / Move to Docs)

**File tabs:**

| Tab | Types |
|---|---|
| Documents | PDF, Word, Excel, PPT, TXT, MD, CSV, code files |
| Media & Exe | Images, EXE/MSI, archives (ZIP/7Z/RAR), ISO/IMG |
| Old Files | Any file > 6 months, sorted oldest-first |
| Duplicates | Grouped by SHA256; mark which copy to keep |
