---
pm-task: true
projectId: "da2026048001e780"
parentId:
id: "da202604800001a3"
title: "OpenSSH key setup — LXC 226 → Laptop 192.168.0.159"
type: "task"
status: "todo"
priority: "high"
start: "2026-04-28"
due: "2026-05-05"
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: ["da202604800001a2"]
collapsed: false
createdAt: "2026-04-28T00:00:00.000Z"
updatedAt: "2026-04-28T00:00:00.000Z"
---

Project: [[Downloads Assistant v2.0|Downloads Assistant v2.0]]

**On LXC 226:**
```bash
ssh-keygen -t ed25519 -f ~/.ssh/downloads_agent -N ""
cat ~/.ssh/downloads_agent.pub
```

**On laptop (192.168.0.159) — PowerShell:**
```powershell
# Ensure OpenSSH Server is running and set to auto-start
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd

# Add the public key from LXC 226
Add-Content -Path "$env:USERPROFILE\.ssh\authorized_keys" -Value "<paste pub key here>"
```

**Verify from LXC 226:**
```bash
ssh -i ~/.ssh/downloads_agent -o StrictHostKeyChecking=no offic@192.168.0.159 "powershell -Command \"echo ok\""
# Expected: ok
```
