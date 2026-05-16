---
name: agent:dream
description: |
  Run a **memory-consolidation pass** ("dream") for a Claude Code subagent that
  uses the three-tier memory architecture. The agent re-reads its own
  `.agents/<name>/memory/` files, decides per-entry to keep/drop/merge/promote/
  enhance, applies the changes, and appends a structured stats entry to
  `memory/DREAMS.md` covering counts before/after, what was dropped and why,
  what was merged, what was promoted episodic→semantic, and what was rescored.

  Implements the **Sleep-time Compute** pattern (Letta, 2025) — the academic
  finding that ~5× compute reduction + 13% accuracy improvement comes from a
  periodic async rewrite of agent memory. Without consolidation, Tier 3 grows
  monotonically and importance scoring loses its eviction value.

  Trigger when: the user says "consolidate <agent>", "run dream on <agent>",
  "<agent> memory cleanup", "dream pass", "run the dream", "weekly
  consolidation", or when `mh:agent:audit` reports DREAMS.md is stale
  (>30 days). Recommended cadence: weekly, or after every N (~5) substantive
  sessions.

  Skip when: the agent has fewer than ~10 entries across all logs (not enough
  to consolidate), or has run `dream` within the last 7 days (the bookkeeping
  needs less consolidation than that).
---

# agent:dream

Weekly memory consolidation pass for a three-tier subagent.

The skill walks Claude through a deliberate re-read + rewrite of an agent's
own `memory/` files, then leaves a paste-trail in `DREAMS.md` so the audit log
of "what got dropped and why" is durable.

## When this earns its place

- `mh:agent:audit` reports `dreams: WARN` (no consolidation in 30+ days)
- The agent's `memory/what-works.md` / `decisions.md` / `failures.md` have
  grown past ~30 entries each
- Multiple entries in those files **contradict** each other — bidirectional
  link-on-write was skipped during the sessions that wrote them
- Importance scores cluster at the same value (no signal) — agent has been
  rating everything 5

Skip when: <10 entries total, <7 days since last dream, or the agent is brand
new (let it accumulate first).

## The flow

### 1. Inventory the deep store

```bash
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:dream/scripts/dream_prep.py" \
  --name <agent-name> \
  --target <vault-root>
```

Output (JSON): per-file line/word counts, latest-mtime, importance
histogram, candidate duplicate-entry pairs (slug-overlap heuristic), and a
snapshot directory under `.agents/<name>/cache/snapshots/dream-<stamp>/`
that captures the pre-dream state.

Snapshot first, mutate second. If the dream goes badly the user can
`rsync -a` back from the snapshot.

### 2. Read every entry the agent appended since the last dream

For each of `memory/what-works.md`, `memory/decisions.md`, `memory/failures.md`
(plus any per-subject variants like `memory/<subject>/what-works.md`):

1. Read the file.
2. For each entry under a `## <slug>` heading, classify into one of:
   - **keep** — still true, still useful, importance still right
   - **drop** — stale, obsolete, low importance, or duplicated by a newer entry
   - **merge** — overlaps with another entry; combine them into the older
     slug, set `superseded_by: <kept-slug>` on the dropped one's frontmatter
   - **promote** — recurring pattern that should move from episodic
     (per-session) to semantic (a `_shared/<framework>.md` file). Examples:
     three failures with the same `attribution: timing` → promote to
     `_shared/timing-patterns.md`
   - **enhance** — keep but rewrite for clarity, add cross-links, refine
     importance score based on how many times it's been load-bearing since
     write
3. Apply the changes via `Edit` and `Write`. **Never delete entries silently
   — they must end up listed in the DREAMS.md entry.**

### 3. Re-distill `critical_facts.md`

After the per-entry consolidation, re-read `memory/critical_facts.md` and
ask: given what changed in the deeper logs, does the ≤200-token distillation
still represent the truth? Edit if needed.

### 4. Write the DREAMS.md entry

Append a structured entry to `.agents/<name>/memory/DREAMS.md` using the
template at `templates/dreams_entry.md.tmpl` — counts before/after,
explicit lists per category, 2–3 sentences of rationale.

### 5. Print the stats report

```bash
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:dream/scripts/dream_stats.py" \
  --name <agent-name> \
  --target <vault-root> \
  --snapshot <snapshot-dir-from-step-1>
```

Output (markdown by default, `--format json` available): a single-page
report showing entry counts, line counts, average importance, top
contradictions resolved, and any patterns promoted to `_shared/`.

### 6. Log the dream session

Append one line to `.agents/<name>/log.md`:

```
## [YYYY-MM-DD HH:MM] dream | consolidated N entries → M, K promoted, J dropped
```

## What this skill does NOT do

- **No autonomous deletion without a DREAMS.md entry.** Every dropped item
  must be listed by slug + reason. The audit trail is the point.
- **No cross-agent consolidation.** A dream on `code-reviewer` never touches
  `data-scout`'s store. Cross-subagent memory is an open problem; this skill
  doesn't try.
- **No external-system writes.** Vault / project files outside `.agents/<name>/`
  are left alone; the dream operates strictly inside the agent's own store.
- **No vector-DB rebuild.** This is a markdown-only rewrite pass.

## Conventions baked in

- **Snapshot before mutate.** Always. Lives at `cache/snapshots/dream-<stamp>/`.
- **Importance-protect.** Entries with `importance: ≥7` are presumed-keep
  unless explicitly superseded. The dream can rescore but should justify
  every change in the rationale.
- **Two-bucket eviction.** Low importance (1–3) + old (>90 days) + no
  cross-links → strong drop candidate. Mid (4–6) + old → merge candidate.
- **Promotion threshold.** Three or more entries sharing a tag or
  `attribution` value → promote to `_shared/<topic>.md` as a pattern.

## Inputs / outputs

**Inputs:** `--name <agent>`, `--target <dir>`.
**Outputs:** mutated memory files, new entry in DREAMS.md, log.md line,
stats report on stdout.
**Exit codes:** 0 on success; 1 on snapshot failure or invocation error.

## See also

- `mh:agent:create` — scaffold a new agent with all the right files in place
  for `dream` to operate on.
- `mh:agent:audit` — surfaces "dream overdue" via the `dreams` check.
- `references/consolidation-rubric.md` — the per-entry decision rubric in
  more detail.
