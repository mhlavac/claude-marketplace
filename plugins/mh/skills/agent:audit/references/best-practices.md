# Three-tier subagent best practices

The rules the `mh:agent:audit` lint encodes, with a one-line **why** each
matters.

## Tier 1 — Definition (`.claude/agents/<name>.md`)

1. **Has YAML frontmatter** with `name`, `description`, `model`.
   *Why:* the Claude Code harness needs this to register the agent.
2. **`name:` matches the filename.**
   *Why:* mismatched names lead to invocation failures.
3. **Description is substantive** (≥ ~100 characters).
   *Why:* the harness pattern-matches the description to decide whether to spawn.
4. **Description has positive triggers** (keywords, paths the agent responds to).
   *Why:* tells the harness when to spawn.
5. **Description has anti-triggers** (a "do NOT trigger for" or "skip when" clause).
   *Why:* prevents the agent from being spawned for adjacent-but-wrong tasks.
6. **Body has a Persona / Identity section.**
   *Why:* gives the agent a voice; "blank-slate Claude" produces inconsistent output.
7. **Body has an explicit Boot sequence** — a numbered list of files to read in order.
   *Why:* boot order matters (PRIVACY first, then identity, then state, then context).
8. **Body has a Self-curation section** — what the agent writes back at session end.
   *Why:* without a closing loop, memory never grows from real interactions.
9. **No `<!-- TODO -->` markers left.**
   *Why:* a scaffold that hasn't been customized is a "blank" agent.

## Tier 2 — Memory index (`.claude/agent-memory/<name>/MEMORY.md`)

1. **File exists.**
   *Why:* this is the auto-injected index; without it the agent boots blind.
2. **≤ 80 lines.**
   *Why:* it costs context tokens on every spawn. Pointers, not content.
3. **Boot sequence present** (numbered list).
   *Why:* mirrors the definition's boot sequence; this is the version the agent itself reads.
4. **Boot-sequence files resolve.**
   *Why:* references to missing files produce silent failures or wasted attempts.
5. **Identity one-liner present** (matches the definition).
   *Why:* the agent should know who it is in its own working memory, not just the system prompt.

## Tier 3 — Deep store (`.agents/<name>/`)

1. **`memory/PRIVACY.md` exists.**
   *Why:* privacy posture must be loadable before the agent does anything.
2. **`memory/INDEX.md` exists.**
   *Why:* the deeper pointer file the auto-injected index points into.
3. **`tasks/open-tasks.md` exists.**
   *Why:* every agent should have a place for its own backlog.
4. **`sessions/` exists.**
   *Why:* without this the agent has no place to log what it did.
5. **Recent session log within 90 days** (skip if brand new).
   *Why:* if the agent hasn't run in 90+ days, the memory is probably stale.

## Cross-tier consistency

1. **All three tiers present for `<name>`.**
   *Why:* a definition without a store, or a store without a definition, is a half-built agent.
2. **Identity one-liner consistent** between definition and index.
   *Why:* drift here is the first sign the agent's role has shifted without being re-codified.
3. **Boot sequence files in the index actually exist in the store.**
   *Why:* the most common "the agent feels lost" symptom is a boot sequence pointing at deleted/renamed files.

## What's intentionally NOT checked

- **Behavioral output quality.** Static structure only.
- **External wiring** (MCPs, slash commands, queues). Out of scope for the
  three-tier primitive.
- **Privacy content.** The audit checks that PRIVACY.md exists, not what's in it.
  Content is the user's call.
- **Tier 1 length.** Definitions can be long when the persona is rich — no budget
  enforced here.
