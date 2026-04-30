---
pm-task: true
projectId: "da2026048001e780"
parentId:
id: "da202604800001a2"
title: "Create LXC 226 on Proxmox (pve / NVMe-pve)"
type: "task"
status: "todo"
priority: "high"
start: "2026-04-28"
due: "2026-05-03"
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: []
collapsed: false
createdAt: "2026-04-28T00:00:00.000Z"
updatedAt: "2026-04-28T00:00:00.000Z"
---

Project: [[Downloads Assistant v2.0|Downloads Assistant v2.0]]

Create LXC container 226 on node `pve`:
- Template: Ubuntu 22.04 LTS
- Storage: NVMe-pve
- CPU: 2 vCPU
- RAM: 2048 MB
- Disk: 10 GB
- Network: vmbr0, DHCP (or static on 192.168.0.x)

Install Docker + Docker Compose after creation.
