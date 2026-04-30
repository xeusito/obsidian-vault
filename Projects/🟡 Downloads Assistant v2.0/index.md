---
status: todo
priority: medium
startDate: 2026-04-28
dueDate: 2026-05-31
tags: [project, proxmox, python, react, featherless-ai, powershell, home-lab]
---

# Downloads Assistant v2.0

A browser-based assistant that keeps the Windows Downloads folder organised. It replaces the manual PowerShell scripts (v1.0) with a web UI: AI chat on the left, categorised file panels on the right. All file operations still happen on the laptop; the web app lives on Proxmox.

## Subpages
- [[Architecture]] — system diagram, component breakdown, data flows
- [[API Reference]] — laptop agent + backend endpoints

## Background

### Why
The existing PowerShell toolkit (v1.0 in the `home_it_infrastructure` repo) works, but requires opening a terminal and navigating a text menu. The goal is a persistent web app reachable from any device on the LAN that makes cleanup feel effortless: scan automatically on open, present files by category, let AI answer questions and execute commands in natural language.

### Constraints
- File operations must stay on the Windows laptop — the hypervisor cannot directly write to the local filesystem
- All deletes go to the Recycle Bin (never permanent wipe)
- The web app must self-start the laptop agent via SSH — no manual pre-step required
- AI descriptions are lazy (on-demand per file) to keep API costs low

## Architecture

```
Browser
  └─► LXC 226 (Ubuntu 22.04) — pve / NVMe-pve
        ├── Nginx  →  serves React build on :80
        └── FastAPI backend on :8000
              ├── Featherless.ai API (OpenAI-compat) ← chat / describe / recs
              ├── SSH to 192.168.0.159              ← agent bootstrap on demand
              └── HTTP to Laptop Agent :7878
                    └── Windows laptop (192.168.0.159)
                          ├── Python FastAPI agent
                          └── Existing PS scripts (Common.psm1, etc.)
```

## Status

| Item | State |
|---|---|
| Plan drafted | ✅ done |
| GitHub docs updated (v2.0 section) | ⬜ pending |
| LXC 226 created | ⬜ pending |
| SSH key setup (LXC 226 → Laptop) | ⬜ pending |
| Laptop agent built | ⬜ pending |
| Proxmox backend built | ⬜ pending |
| React frontend built | ⬜ pending |
| Deployed on LXC 226 | ⬜ pending |
| End-to-end verified | ⬜ pending |

## Next Steps
- [ ] Enable OpenSSH Server on laptop (installing as of 2026-04-28) and confirm it auto-starts
- [ ] Update `tools/downloads-cleanup/README.md` in `xeusito/home_it_infrastructure` with v2.0 section
- [ ] Create LXC 226 on Proxmox: Ubuntu 22.04, 2 vCPU, 2 GB RAM, NVMe-pve storage
- [ ] Generate SSH key on LXC 226, add public key to `C:\Users\offic\.ssh\authorized_keys` on laptop
- [ ] Test: `ssh -i ~/.ssh/downloads_agent offic@192.168.0.159 "powershell -Command echo ok"`

## Key Decisions

- **Small agent on laptop, not SMB share** — avoids network share config; agent exposes a clean REST API the backend can call without knowing about Windows paths
- **Featherless.ai (OpenAI-compat) instead of Claude API** — testing open-source models; the `openai` Python library points at `https://api.featherless.ai/v1`; model is configurable via `FEATHERLESS_MODEL` env var (default: `meta-llama/Llama-3.3-70B-Instruct`)
- **Lazy AI descriptions** — clicking "✨ Describe" per file generates the description on demand; no batch call on scan
- **Batch Apply, not immediate** — tick all actions → Review & Apply modal → confirm once → all actions execute
- **Reuse existing PS scripts** — `Common.psm1` Send-PathToRecycleBin, extension map from `03-MoveByType.ps1`, duplicate logic from `04-DuplicatesReport.ps1`, age threshold from `05-OldFilesReport.ps1`
- **LXC 226 on NVMe-pve** — matches existing numbering; app footprint < 500 MB, well within available space

## File Layout (repo)

```
tools/downloads-assistant/
├── laptop-agent/
│   ├── main.py              # FastAPI agent
│   ├── scanner.py           # scan + categorise (ports PS logic)
│   ├── actions.py           # Recycle Bin + Move via PS subprocess
│   ├── start_agent.ps1      # bootstrap (called via SSH from LXC 226)
│   └── requirements.txt
├── server/
│   ├── main.py              # FastAPI backend
│   ├── ai.py                # Featherless.ai: chat, describe, recs
│   ├── agent_client.py      # HTTP client + SSH bootstrap
│   ├── models.py
│   ├── .env.example
│   └── requirements.txt
├── client/                  # React + Vite
│   └── src/components/
│       ├── ChatPanel.tsx
│       ├── FileTable.tsx
│       ├── ScanStatus.tsx
│       ├── ActionBar.tsx
│       └── ApplyModal.tsx
├── nginx.conf
└── docker-compose.yml
```

## .env (LXC 226)

```
FEATHERLESS_API_KEY=...
FEATHERLESS_MODEL=meta-llama/Llama-3.3-70B-Instruct
LAPTOP_HOST=192.168.0.159
LAPTOP_AGENT_PORT=7878
LAPTOP_SSH_USER=offic
LAPTOP_SSH_KEY=/root/.ssh/downloads_agent
DOWNLOADS_PATH=C:\Users\offic\Downloads
```

## Verification Checklist

- [ ] `ssh -i ~/.ssh/downloads_agent offic@192.168.0.159 "powershell -Command echo ok"` → `ok`
- [ ] Browser opens `http://lxc-226-ip` → "Starting laptop agent…" spinner appears
- [ ] Spinner resolves → scan progress bar increments live
- [ ] Documents tab populates; Old Files tab shows files > 6 months
- [ ] Click "✨ Describe" → description appears inline within ~3 s
- [ ] Mark 2 files Delete → Apply → modal lists them → confirm → Recycle Bin on laptop
- [ ] Chat: *"What are my 5 largest files?"* → accurate answer from scan data
- [ ] Chat: *"Delete all .torrent files"* → AI explains → user confirms → executes
- [ ] Swap `FEATHERLESS_MODEL` in `.env` → restart → chat still works with new model

## Plan File
Full implementation plan: `C:\Users\offic\.claude\plans\i-would-like-to-unified-comet.md`

## References
- Existing scripts: [xeusito/home_it_infrastructure — tools/downloads-cleanup](https://github.com/xeusito/home_it_infrastructure/tree/main/tools/downloads-cleanup)
- Featherless.ai docs: https://featherless.ai
- Proxmox node: `pve` — LXC 226 target on NVMe-pve
