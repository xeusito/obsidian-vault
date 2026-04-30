---
pm-task: true
projectId: "da2026048001e780"
parentId:
id: "da202604800001a7"
title: "Deploy with Docker Compose on LXC 226"
type: "task"
status: "todo"
priority: "medium"
start: "2026-05-15"
due: "2026-05-20"
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: ["da202604800001a6"]
collapsed: false
createdAt: "2026-04-28T00:00:00.000Z"
updatedAt: "2026-04-28T00:00:00.000Z"
---

Project: [[Downloads Assistant v2.0|Downloads Assistant v2.0]]

Deploy on LXC 226 via Docker Compose. Nginx serves the React build on `:80`, proxies `/api/*` to FastAPI on `:8000`.

```bash
apt update && apt install -y docker.io docker-compose git
git clone https://github.com/xeusito/home_it_infrastructure.git
cd home_it_infrastructure/tools/downloads-assistant
cp server/.env.example server/.env   # fill FEATHERLESS_API_KEY + laptop details
docker-compose up -d
```

Laptop agent (`laptop-agent/`) runs directly on Windows — started on demand via SSH from the backend, not containerised.
