# agent:dream

A skill in the [`mh`](../../README.md) Claude Code plugin that runs a weekly
**memory-consolidation pass** on a three-tier subagent.

Implements the **Sleep-time Compute** pattern (Letta, 2025) — academic finding
of ~5× compute reduction + 13% accuracy from periodic async memory rewrite.

## What it does

For a named subagent:

1. **Snapshots** the deep store at `.agents/<name>/cache/snapshots/dream-<stamp>/`
2. **Inventories** every entry across `memory/what-works.md`, `memory/decisions.md`,
   `memory/failures.md` (plus per-subject variants)
3. **Classifies** each entry: keep · drop · merge · promote · enhance
4. **Applies** changes via Edit/Write — never silently deletes
5. **Re-distills** `memory/critical_facts.md` if downstream truths changed
6. **Appends** a structured entry to `memory/DREAMS.md` (counts before/after,
   per-category lists, rationale)
7. **Logs** one line to `log.md`
8. **Prints** a stats report

## Install

```
/plugin marketplace add mhlavac/claude-marketplace
/plugin install mh@mhlavac-marketplace
```

Invoke as `mh:agent:dream`, or let the agent auto-trigger when the user says
"consolidate <agent>", "run the dream", "weekly cleanup", etc.

## 30-second quickstart

```bash
# Inventory + snapshot (run by Claude, output JSON for the next step)
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:dream/scripts/dream_prep.py" \
  --name code-reviewer --target ~/projects/my-vault

# ... Claude reads, classifies, applies via Edit/Write ...

# After mutation: stats report (before vs after)
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:dream/scripts/dream_stats.py" \
  --name code-reviewer --target ~/projects/my-vault \
  --snapshot .agents/code-reviewer/cache/snapshots/dream-2026-05-16-2200
```

## What's inside

| Piece | Where |
|---|---|
| **Skill body** | [`SKILL.md`](SKILL.md) |
| **Prep / inventory** | `scripts/dream_prep.py` — snapshot, line/word counts, importance histogram, duplicate candidates |
| **Stats** | `scripts/dream_stats.py` — before/after diff: entries, lines, avg importance, drops, merges, promotions |
| **Templates** | `templates/dreams_entry.md.tmpl` — structured DREAMS.md entry format |
| **Rubric** | `references/consolidation-rubric.md` — per-entry decision rubric |

## What this skill does NOT do

- **No autonomous deletes without an audit-trail entry** — every drop is
  named in DREAMS.md with a reason.
- **No cross-agent consolidation** — dream operates strictly inside one
  agent's deep store.
- **No external-system writes** — files outside `.agents/<name>/` are not touched.
- **No vector-DB rebuild** — markdown only, by design.

Pair with `mh:agent:create` (which scaffolds the files the dream operates on)
and `mh:agent:audit` (which warns when a dream is overdue).
