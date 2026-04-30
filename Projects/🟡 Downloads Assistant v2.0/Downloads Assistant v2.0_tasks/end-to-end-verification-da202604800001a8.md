---
pm-task: true
projectId: "da2026048001e780"
parentId:
id: "da202604800001a8"
title: "End-to-end verification"
type: "task"
status: "todo"
priority: "medium"
start: "2026-05-18"
due: "2026-05-25"
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: ["da202604800001a7"]
collapsed: false
createdAt: "2026-04-28T00:00:00.000Z"
updatedAt: "2026-04-28T00:00:00.000Z"
---

Project: [[Downloads Assistant v2.0|Downloads Assistant v2.0]]

Run all checklist items end-to-end:

- [ ] `ssh -i ~/.ssh/downloads_agent offic@192.168.0.159 "powershell -Command echo ok"` → `ok`
- [ ] Browser opens `http://lxc-226-ip` → "Starting laptop agent…" spinner appears
- [ ] Spinner resolves → scan progress bar increments live
- [ ] Documents tab populates; Old Files tab shows files > 6 months
- [ ] Click "✨ Describe" → inline description appears within ~3 s
- [ ] Mark 2 files Delete → Apply → modal lists them → confirm → Recycle Bin on laptop ✓
- [ ] Chat: *"What are my 5 largest files?"* → accurate answer from scan data
- [ ] Chat: *"Delete all .torrent files"* → AI explains → user confirms → executes
- [ ] Swap `FEATHERLESS_MODEL` in `.env` → restart → chat still works with new model
