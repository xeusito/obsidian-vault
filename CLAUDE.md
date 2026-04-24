# CLAUDE.md

Orientation for Claude working in this Obsidian vault. Read this first so you can skip re-reading `Dashboard.md` on every session.

## Purpose

Home-automation hardware projects. Stack: Home Assistant + ESPHome, ESP32, mmWave sensors, e-ink displays, solar power.

## Entry point

For **current status** of what's active / on-hold / ideas, read `Projects/Dashboard.md`. This CLAUDE.md only describes structure — Dashboard.md is the source of truth for state.

## Project structure convention

Every folder under `Projects/` follows the same triad:

- `index.md` — overview, YAML frontmatter (status, started, tags), key decisions, next steps
- `Hardware.md` — components, wiring tables, mermaid diagrams, mounting notes
- `Software.md` — code, ESPHome/HA configs, integration notes

When a user asks about a project, read its `index.md` first, then pull Hardware/Software only if the question needs them.

## Folder map

- `Projects/` — active and on-hold work. Folder names use emoji status prefix: 🟢 in-progress, 🟡 on-hold.
- `Ideas/` — flat list of concept files. Template at `Resources/templates/idea.md`.
- `Resources/` — templates, PDF manuals, reference docs.

## Conventions

- YAML frontmatter on each project `index.md`: `status`, `started`, `tags`.
- Tag vocabulary: `project, hardware, esp32, home-assistant, esphome, mmwave`.
- Emoji status prefix on project folder names (not note titles).

## Current projects (snapshot — verify against Dashboard.md if it matters)

- 🟢 Presence Detection in the Hallway (LD2450 + ESP32)
- 🟢 Solar E-Ink Door Display
- Ideas: Solar IQOS Charger, Grocery List Automation

## How to work here

- Status questions → `Projects/Dashboard.md`.
- Specific project → that project's `index.md`, then Hardware/Software as needed.
- New idea → copy `Resources/templates/idea.md` into `Ideas/`.
- HA or ESPHome automation work → trigger the `home-assistant-best-practices` skill.
