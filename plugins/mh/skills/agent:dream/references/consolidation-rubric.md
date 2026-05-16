# Consolidation rubric

The per-entry decision rule used inside `mh:agent:dream`. Apply consistently.

## Decision tree

For each `## <slug>` entry in `what-works.md` / `decisions.md` / `failures.md`:

1. **Read the entry's frontmatter.** Note `importance`, `captured`, `tags`,
   `superseded_by` (if any).
2. **Compute its age.** Days since `captured`.
3. **Search the rest of the file** for entries that overlap on tags or slug
   tokens. The `dream_prep.py` inventory pre-computed a candidate list — use it
   as a starting point, but also do a fresh skim, the heuristic misses semantic
   overlap.
4. **Classify:**

   | Signal | Classification | Action |
   |---|---|---|
   | `superseded_by` already set | **drop** | Move to "dropped" list. The new entry has the truth. |
   | Importance ≥ 7, ≤ 90 days, no contradictions | **keep** | No action. |
   | Importance ≤ 3, > 90 days, no cross-links pointing in | **drop** | List with reason "low-importance + stale". |
   | Importance 4–6 + overlapping entry exists | **merge** | Combine into the older slug; set `superseded_by` on the dropped. |
   | Three or more entries share a tag / `attribution` | **promote** | Extract the shared pattern into `_shared/<topic>.md`. Leave originals with a pointer. |
   | Body still true but importance feels wrong | **enhance / rescore** | Edit the YAML; explain delta in DREAMS rationale. |
   | Body now feels wrong but originally was load-bearing | **enhance** | Rewrite the body; do not change `captured`; add `revised: YYYY-MM-DD` to YAML. |

## Importance scoring guide

The agent rates 1–10 at moment of capture. The dream pass can rescore based on
how the entry has aged:

- **10** — load-bearing identity / value statement. Drops here = identity drift.
- **8–9** — major decision or pattern, multiple sessions have leaned on it.
- **6–7** — useful insight, has come up at least once since capture.
- **4–5** — observation worth keeping, no specific recurrence yet.
- **2–3** — minor note. Candidate for drop after 90 days.
- **1** — captured as a fleeting observation. Default drop after 30 days.

## Promotion to `_shared/`

Promote when you see **three or more** entries sharing a tag or `attribution`
value. Examples:

- 3+ `attribution: timing` failures → `_shared/timing-patterns.md`
- 3+ entries with `tags: [caching]` that worked → `_shared/caching-patterns.md`
- 3+ decisions tagged `cost-vs-latency` → `_shared/perf-tradeoffs.md`

The promoted file should:

- Start with a one-paragraph synthesis of the pattern
- List the originating entries (with file pointers) so the audit trail is intact
- Be loaded on demand via the agent's boot sequence `_shared/<topic>` line

## What the dream MUST NOT do

- **Delete entries without listing them** in the DREAMS.md entry.
- **Silently change importance** without explaining the rescore in rationale.
- **Touch `PRIVACY.md` or `critical_facts.md`** before the entry-level work is
  done. `critical_facts.md` is re-distilled in step 3 of the SKILL flow, after
  the deeper logs settle.
- **Run without a snapshot.** Always snapshot first.

## Rationale field

The "rationale" in the DREAMS.md entry should be 2–3 sentences. Answer:

- What was the *theme* of this consolidation? (drift, contradiction, importance drift, promotion of a pattern, etc.)
- What surprised you, if anything?
- What changed about the agent's working model as a result?

If you have nothing surprising to say, the dream probably wasn't necessary.
That's also a valid signal — capture it as "dream-too-soon" in the next
session's `failures.md`.
