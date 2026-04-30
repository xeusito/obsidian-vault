---
pm-task: true
projectId: "da2026048001e780"
parentId:
id: "da202604800001a4"
title: "Build laptop agent (Python FastAPI)"
type: "task"
status: "todo"
priority: "high"
start: "2026-05-03"
due: "2026-05-12"
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: ["da202604800001a3"]
collapsed: false
createdAt: "2026-04-28T00:00:00.000Z"
updatedAt: "2026-04-28T00:00:00.000Z"
---

Project: [[Downloads Assistant v2.0|Downloads Assistant v2.0]]

Build `tools/downloads-assistant/laptop-agent/` in the repo.

**Endpoints:**
- `GET /health` — liveness
- `POST /scan` — scan Downloads via SSE stream; caches result in memory
- `GET /files` — return cached scan results
- `POST /actions` — execute batch `[{path, action: "recycle"|"move", dest?}]`
- `GET /file-info?path=` — extended metadata for one file

**Key implementation notes:**
- Port `01-Inventory.ps1` logic to Python `os.walk`
- Port `03-MoveByType.ps1` extension map to a Python dict
- Port `04-DuplicatesReport.ps1` SHA256 duplicate logic with `hashlib`
- Age threshold 180 days constant (from `05-OldFilesReport.ps1`)
- Recycle Bin: call `Common.psm1` → `Send-PathToRecycleBin` via `subprocess.run(['powershell', '-File', ...])`
- MSI metadata: call `07-InteractiveInstallers.ps1` Get-MsiPropertyFields via subprocess

`requirements.txt`: `fastapi`, `uvicorn`, `pywin32`

Started via `start_agent.ps1` — called from LXC 226 over SSH on web app open.
