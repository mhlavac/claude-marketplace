# Changelog

All notable changes to the `mh` plugin.
This project follows [Semantic Versioning](https://semver.org/).

## [1.2.0] — 2026-06-11

Lessons from the first real-world persona built after this toolkit shipped
(a management coach in the MyNotes vault).

### Changed — `mh:agent:create`

- **New Tier-1 template section: "Context gaps — elicit, don't assume."**
  Every memory store has blind spots (a personal vault under-represents work
  life; a work repo under-represents personal constraints). The scaffolded
  agent now names its known gaps, asks 1–2 targeted questions when a session
  depends on one, and writes the answers back the same session so the gap
  shrinks over time.
- **New flow step: "Seed with researched context (encouraged)."** Templates
  give shape; seeding gives the agent a working first session. When research
  preceded the scaffold, replace placeholders with dated facts + a provenance
  line ("Seeded YYYY-MM-DD by <who> from <where>. I own this file now.")
  instead of leaving TODOs. User quotes with dates beat frameworks.
- `tier3_critical_facts.md.tmpl` — example line for a known context gap.

## [1.1.0] — 2026-05-16

Adds a three-skill subagent toolkit on top of the agent-memory architecture
described in the academic literature (MemGPT, Generative Agents, Reflexion,
A-MEM, Sleep-time Compute) and the documented Claude Code hook lifecycle.

### Added — new skills

- **`mh:agent:create`** — scaffold a three-tier Claude Code subagent: definition file (`.claude/agents/<name>.md`), auto-injected memory index (`.claude/agent-memory/<name>/MEMORY.md`), and deep memory store (`.agents/<name>/{memory,tasks,sessions,cache,output,log.md}`). Stdlib Python script with templated files for each tier. Optional `--with-hooks` flag installs lifecycle hook scripts and merges them into `.claude/settings.json` non-destructively.
- **`mh:agent:audit`** — static lint for three-tier subagents. Tier-1 checks (frontmatter, triggers, persona, boot sequence, self-curation), Tier-2 checks (≤80-line budget, boot-sequence resolves, named blocks present), Tier-3 checks (PRIVACY.md, critical_facts.md within token budget, log.md recency, DREAMS.md consolidation cadence, failures.md presence, importance scoring on append-only files), and cross-tier consistency. Markdown or JSON output. Non-zero exit on FAIL. `--mode drift` shows what's missing vs the latest templates; `--mode apply` writes missing files non-destructively. Per-subject log awareness (accepts `memory/<file>.md` or `memory/<subject>/<file>.md`).
- **`mh:agent:dream`** — periodic memory-consolidation pass implementing the Sleep-time Compute pattern (Letta 2025: async memory rewrite between user turns). Snapshot via `dream_prep.py`, mutation guided by `references/consolidation-rubric.md`, before/after stats via `dream_stats.py`. Five entry classifications: keep / drop / merge / promote (episodic→semantic) / enhance. Structured audit trail appended to `memory/DREAMS.md`.

### Patterns built into the templates

- **`memory/critical_facts.md`** — ≤200-token always-loaded distillation (boot step 2, after PRIVACY).
- **`log.md`** — append-only chronology, one `## [YYYY-MM-DD HH:MM] kind | title` line per session.
- **`memory/DREAMS.md`** — consolidation history scaffold.
- **`memory/failures.md`** — failure attribution with explicit *why* (Reflexion, Shinn et al. 2023).
- **`memory/what-works.md` / `decisions.md` / `failures.md`** ship with `importance: 1-10` YAML frontmatter format documented inline (Generative Agents, Park et al. 2023).
- **Tier 2 `MEMORY.md` named blocks** — `<persona>`, `<critical_facts>`, `<active_threads>`, `<open_questions>`, `<recent_decisions>` — each with a one-line maintenance hint, edited via targeted `Edit` calls rather than full rewrites.
- **Tier 1 definition** includes: memory-protocol boot clause, frozen-snapshot-discipline note (mid-session writes only visible next spawn), cross-link-on-write rule (A-MEM, Xu et al. 2025), Two-Output Rule (every Q→A also mutates a durable doc), Reflexion failure-attribution requirement.

### Hooks (optional)

- `snapshot-memory.sh` on `PreCompact` — copies durable memory files to a timestamped snapshot dir before compaction loses any not re-injected.
- `curate-memory.sh` on `SessionEnd` — appends a chronology line; fallback when in-session self-curation didn't run.
- `load-curated.sh` on `SessionStart` — emits `additionalContext` JSON so curated files re-inject on every entry path including post-`/compact` resume.

## [1.0.0] — 2026-05-16

Initial public release.

### Features

- Skill `mh:annotated-feedback` with auto-trigger description and slash invocation
- HTML template with annotation overlay (text-highlight, pin, sketch, general comment) and `.af-q` form-element discovery (text, textarea, radio, checkbox, action)
- Live right-side sidebar showing every form answer + annotation as the user types
- Stdlib Python receiver server (`server.py`) — writes W3C-shaped JSON envelopes and paste-ready Markdown prompts to `feedback/`
- One-shot scaffolder script (`scripts/new_artifact.py`)
- Vendored Mermaid 11.4.1 + perfect-freehand 1.2.2 — zero CDN deps at runtime
- Mermaid diagram support with pin anchors on individual nodes/edges
- localStorage persistence per artifact URL
- W3C Web Annotation Data Model envelope (TextQuoteSelector / CssSelector + FragmentSelector / SvgSelector)

### Security

- POST `/feedback` requires `Content-Type: application/json` and same-origin `Origin` header — CSRF-guarded
- 5 MB body cap on submissions
- Mermaid initialised with `securityLevel: 'strict'`
- Path-traversal blocked in static-file fallback
- Server binds to `127.0.0.1` only

