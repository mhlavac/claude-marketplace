---
name: agent:audit
description: |
  Audit a Claude Code subagent against the **three-tier memory architecture**
  best practices: definition completeness, memory-index health, deep-store
  scaffolding, self-curation evidence, and cross-tier consistency. Emits a
  PASS / WARN / FAIL report per check.

  Use this skill when the user wants to **check the health of an existing
  agent** — has the agent's memory index drifted past its budget, is the boot
  sequence still pointing at real files, has the agent been writing back what
  it learns. Triggers include: "audit my agent", "check the X agent",
  "is my subagent following best practices", "lint agent", "agent health
  check", "how is my agent doing", "is X still wired up correctly", "run an
  audit on the new agent."

  Pairs with `mh:agent:create`: scaffold → customize → audit → iterate.

  Skip when: the user is just looking at a single file (`Read` it), or when
  they want behavioral testing of the agent's output quality (this skill
  checks structure, not output).
---

# agent:audit

Static-analysis lint for Claude Code subagents that use the three-tier memory
architecture (definition · memory index · deep store).

The skill walks a target agent (or all agents in a target directory) and runs
a fixed set of checks. Each check emits PASS, WARN, or FAIL with a short
reason and — where useful — a one-line suggested fix.

## What gets checked

### Tier 1 — Definition (`.claude/agents/<name>.md`)

| Check | Severity | What it looks for |
|---|---|---|
| YAML frontmatter present | FAIL | Opens with `---`, has a parseable `name:` / `description:` block |
| `name` field matches filename | FAIL | `name: foo` ⇔ `foo.md` |
| `description` non-trivial | WARN | At least ~100 characters; otherwise the harness can't match well |
| Positive triggers present | WARN | Description mentions specific keywords or paths |
| Anti-triggers present | WARN | Description has a "do NOT trigger for" / "skip when" clause |
| Body has a Persona section | WARN | `## Persona`, `## Identity`, or similar |
| Body has a Boot sequence | FAIL | Numbered list pointing at memory files |
| Body has a Self-curation section | WARN | "every session before I sign off" / "self-curation" / "what-works" |
| `<!-- TODO -->` markers absent | WARN | If still present, the scaffold hasn't been customized |

### Tier 2 — Memory index (`.claude/agent-memory/<name>/MEMORY.md`)

| Check | Severity | What it looks for |
|---|---|---|
| File exists | FAIL | The auto-injected index must be present |
| Size ≤ 80 lines | WARN | The index costs context on every spawn — trim |
| Boot sequence present | WARN | Numbered list of files to read in order |
| Boot-sequence files exist | WARN | Each referenced path resolves on disk |
| Identity one-liner | WARN | "I'm **X** — …" or similar opening |

### Tier 3 — Deep store (`.agents/<name>/`)

| Check | Severity | What it looks for |
|---|---|---|
| `memory/PRIVACY.md` exists | FAIL | Privacy posture must be set before the agent runs |
| `memory/INDEX.md` exists | WARN | Pointer file into the deep store |
| `tasks/open-tasks.md` exists | WARN | Agent has a place for its own backlog |
| `sessions/` exists | WARN | Place for session logs |
| `cache/` exists | INFO | Optional but expected |
| `output/` exists | INFO | Optional but expected |
| Recent session log | INFO | A log within the last 90 days (skip if the agent is brand new) |

### Cross-tier consistency

| Check | Severity | What it looks for |
|---|---|---|
| All three tiers present for `<name>` | FAIL | Definition + index + store must all exist |
| Identity one-liner consistent | WARN | Same role phrasing in Tier 1 and Tier 2 |
| Boot-sequence resolves | WARN | Every path in the index actually exists in Tier 3 |

## The flow

### 1. Pick the audit target

The audit runs against either a single named agent or every agent it
discovers under a target directory. Defaults are sensible:

```bash
# Audit one agent
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:audit/scripts/audit_agent.py" \
  --name code-reviewer \
  --target ~/projects/my-vault

# Audit every agent under .claude/agents/ in the target
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:audit/scripts/audit_agent.py" \
  --target ~/projects/my-vault
```

The `--target` flag is the directory that contains `.claude/agents/` —
typically a vault or project root.

### 2. Read the report

The script prints a Markdown report to stdout by default. Severity counts
appear at the top, then a per-agent section with one line per check:

```
# Agent Audit — 2026-05-16

**Summary:** 2 agents, 38 checks, 0 FAIL, 4 WARN, 1 INFO.

## ✅ code-reviewer

| Check | Result | Detail |
|---|---|---|
| Tier1: frontmatter | PASS | |
| Tier1: anti-triggers in description | WARN | No `do NOT trigger for` clause found |
| …                            | …  | … |

## ⚠️ data-scout

| Check | Result | Detail |
| Tier2: boot sequence files exist | WARN | `.agents/data-scout/memory/profile.md` missing |
```

`--format json` emits a structured JSON report instead, suitable for piping
into other tools.

### 3. Act on findings

The report ranks issues so the user can fix the most-impactful items first:

1. **FAIL** — the agent likely doesn't spawn correctly or has missing privacy /
   boot files. Fix before next invocation.
2. **WARN** — the agent works, but is drifting from best practices. Schedule
   a cleanup pass.
3. **INFO** — observation only. No action required.

For each WARN/FAIL, the report includes a one-line **Suggested fix** when
the script can be specific (e.g. "Add a 'do NOT trigger for' clause", "Trim
MEMORY.md from 134 to ≤80 lines", "Create `memory/PRIVACY.md` or copy from
the agent:create skill's template").

## When this skill earns its place

- After running `mh:agent:create` and customizing — confirm the scaffold is
  internally consistent.
- Periodically (quarterly?) against your existing agents — memory indexes
  drift, boot sequences get out of date, what-works.md stops getting
  appended to. The audit surfaces drift.
- After a non-trivial refactor of the agent's memory layout — re-check that
  the boot sequence still resolves.

## What the audit deliberately does NOT do

- **No behavioral testing.** This is a static check. It tells you if the
  scaffolding is correct, not whether the agent gives good answers.
- **No fixes applied.** The audit reports; the user (or a follow-up Claude
  turn) decides what to fix. This keeps the skill safe to run on any
  repository.
- **No external-system checks.** The audit doesn't verify MCP wiring, cron
  jobs, or queue conventions — those are out of scope for the three-tier
  primitive.

## Inputs / outputs

**Inputs:** `--target <dir>`, optional `--name <agent>`, optional
`--format {markdown,json}` (default markdown).
**Output:** report on stdout.
**Exit codes:** 0 if no FAIL; 1 if any FAIL; 2 on invocation error.

## See also

- `mh:agent:create` — the sister skill that scaffolds the three tiers.
- The plugin README at `plugins/mh/README.md`.
