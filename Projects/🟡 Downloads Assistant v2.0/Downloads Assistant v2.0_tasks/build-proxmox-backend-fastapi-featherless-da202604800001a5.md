---
pm-task: true
projectId: "da2026048001e780"
parentId:
id: "da202604800001a5"
title: "Build Proxmox backend (FastAPI + Featherless.ai)"
type: "task"
status: "todo"
priority: "high"
start: "2026-05-03"
due: "2026-05-14"
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: ["da202604800001a4"]
collapsed: false
createdAt: "2026-04-28T00:00:00.000Z"
updatedAt: "2026-04-28T00:00:00.000Z"
---

Project: [[Downloads Assistant v2.0|Downloads Assistant v2.0]]

Build `tools/downloads-assistant/server/` in the repo.

**Endpoints:**
- `GET /status` — agent liveness + last scan timestamp
- `POST /scan/start` — proxies SSE scan stream from laptop agent to browser
- `GET /files` — categorised file list (Documents / Media & Exe / Old Files / Duplicates)
- `POST /describe` — on-demand: Featherless LLM describes one file from metadata
- `POST /chat` — streaming LLM chat with full file list as system context
- `POST /apply` — sends batch to laptop agent; SSE-streams per-file results
- `GET /recommendations` — after scan: LLM generates top-5 prioritised cleanup summary

**AI integration:**
- Library: `openai` Python package
- Endpoint: `https://api.featherless.ai/v1`
- Model: configurable via `FEATHERLESS_MODEL` env var
- Streaming: `stream=True` on chat completions
- File list sent as system message context on every chat turn

**SSH bootstrap:**
- `paramiko` SSHClient: on `/status` if laptop agent `/health` fails → SSH to 192.168.0.159 → run `start_agent.ps1` → poll until healthy

`requirements.txt`: `fastapi`, `uvicorn`, `openai`, `paramiko`, `httpx`
