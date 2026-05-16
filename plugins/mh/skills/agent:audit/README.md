# agent:audit

A skill in the [`mh`](../../README.md) Claude Code plugin that **lints**
Claude Code subagents using the three-tier memory architecture (definition +
auto-injected memory index + deep store).

It is the static-analysis sister of [`mh:agent:create`](../agent:create/).
Scaffold → customize → audit → iterate.

## What it checks

Three tiers, plus cross-tier consistency:

| Tier | What it covers |
|---|---|
| **Definition** (`.claude/agents/<name>.md`) | YAML frontmatter, description quality (positive triggers + anti-triggers), boot sequence present, self-curation section, `<!-- TODO -->` leftovers |
| **Memory index** (`.claude/agent-memory/<name>/MEMORY.md`) | File exists, ≤80 lines, boot sequence resolves, identity one-liner |
| **Deep store** (`.agents/<name>/`) | `memory/PRIVACY.md` exists, `memory/INDEX.md`, `tasks/open-tasks.md`, `sessions/`, recent session log |
| **Cross-tier** | All three tiers present, identity one-liner consistent, boot-sequence files actually exist |

Each check emits **PASS**, **WARN**, **FAIL**, or **INFO** with a short
detail and — where possible — a one-line suggested fix.

## Install

```
/plugin marketplace add mhlavac/claude-marketplace
/plugin install mh@mhlavac-marketplace
```

Invoke as `mh:agent:audit`, or let the agent auto-trigger it from the SKILL.md
description ("audit my agent", "lint subagent", "is X following best practices").

## 30-second quickstart

```bash
# Audit one agent
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:audit/scripts/audit_agent.py" \
  --name code-reviewer \
  --target ~/projects/my-vault

# Audit every agent under .claude/agents/ in the target
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:audit/scripts/audit_agent.py" \
  --target ~/projects/my-vault
```

Output is a Markdown report on stdout. Pass `--format json` for structured
output, e.g. for piping into another tool.

## Exit codes

- `0` — all checks PASS or only WARN/INFO
- `1` — at least one FAIL
- `2` — invocation error (bad flags, missing target)

## What's inside

| Piece | Where |
|---|---|
| **Skill body** | [`SKILL.md`](SKILL.md) |
| **Auditor** | `scripts/audit_agent.py` — stdlib Python, no pip deps |
| **Reference** | `references/best-practices.md` — the rules the auditor encodes |

## What this skill deliberately does NOT do

- **No behavioral testing** — structure only, not output quality.
- **No fixes applied** — the audit reports; the user / a follow-up turn decides.
- **No external-system checks** — MCPs, queues, cron are out of scope.

Pair with `mh:agent:create` to scaffold new agents that pass these checks out
of the box.
