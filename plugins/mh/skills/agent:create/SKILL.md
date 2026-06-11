---
name: agent:create
description: |
  Scaffold a new Claude Code subagent using a **three-tier memory architecture**:
  (1) a definition file the harness reads to spawn the agent, (2) an auto-injected
  memory index loaded into the agent's context on every spawn, and (3) a deep
  on-disk memory store the agent reads on demand and writes back to (sessions,
  per-topic profiles, what-works, what-doesn't, an own backlog, a privacy file).

  Use this skill when the user wants to **create a new persona / subagent**,
  set up the **memory scaffolding** for an existing one, or "give my new agent
  the same shape as my other agents." Triggers include: "scaffold a subagent",
  "create a new persona", "set up a new agent for X", "give me an agent skeleton",
  "wire up the memory for an agent", "new Claude Code agent", "agent boilerplate",
  "I want an agent that does Y."

  The skill is intentionally generic — it scaffolds the architecture only. It
  does **not** prescribe a cadence (daily/weekly/monthly), does not wire the
  agent into any external system (MCPs, slash-commands, queues, calendars),
  and does not invent a persona for the user. The user fills in voice, anchor
  phrase, triggers, and tool boundaries after the scaffold lands.

  Skip when: the user already has a working agent and just wants tweaks (edit
  files directly), or when the request is for a one-off slash-command rather
  than a stateful persona with durable memory.
---

# agent:create

Scaffold a Claude Code subagent that has **durable memory** — not just a system
prompt, but a small filesystem the agent reads at boot and writes back to at
the end of each session.

The skill creates three things in one shot:

| Tier | What | Where | Read by |
|---|---|---|---|
| 1 | **Definition** (system prompt + YAML frontmatter) | `.claude/agents/<name>.md` | The Claude Code harness, at spawn |
| 2 | **Memory index** (boot sequence, ≤80 lines) | `.claude/agent-memory/<name>/MEMORY.md` | The subagent itself, auto-injected on every spawn |
| 3 | **Deep memory store** (PRIVACY, profiles, sessions, tasks, cache) | `.agents/<name>/` | The subagent, on demand per the boot sequence |

Files are templates. They include placeholders, hints, and a few sensible
defaults (e.g. PRIVACY.md as the first boot step, a self-curation block in the
definition, a `tasks/open-tasks.md` skeleton). The user customizes after the
scaffold runs.

## When this earns its place

Use it when the user is about to create — or wishes they had created — an
agent that should:

- Have a **persistent identity** across sessions, not a one-shot prompt
- Remember decisions, preferences, and "what works" without being told each time
- Carry **per-topic state** (per-person profiles, per-project notes, etc.)
- Curate its own memory after each session (append to what-works.md, log a session, mark a task done)

Skip it for:

- One-off slash commands (those go in `commands/`, not `agents/`)
- Skills that wrap a tool — those don't need their own memory store
- "Just give me a system prompt" — that's a one-file edit, not three-tier scaffolding

## The flow

### 1. Collect the minimum input

Before running the scaffolder, confirm with the user:

1. **Name** — kebab-case, used in all three tiers (e.g. `code-reviewer`, `release-notes-writer`, `data-scout`).
   The agent file will be `<name>.md`; the deep store will live at `.agents/<name>/`.
2. **Role / one-line purpose** — a single sentence the user would say if asked
   "what does this agent do for me?" Used in the description-trigger and in the
   identity blocks of all three tiers.
3. **Target directory** — where the three tiers should be created. Default is
   the current working directory. For a vault-style setup, pass the vault root
   (the scaffolder will create `.claude/agents/`, `.claude/agent-memory/`, and
   `.agents/` under it).

Optional fields (the scaffolder accepts but leaves blank if not provided):

- `--anchor` — a short anchor phrase the agent returns to (`"Boring is the feature."`, `"Signal, not noise."`)
- `--voice` — one line of voice notes (`"calm, dry, no exclamations, no emojis"`)
- `--triggers` — comma-separated keywords for the description (`"X, Y, Z"`)
- `--anti-triggers` — comma-separated "do NOT trigger for" topics
- `--force` — overwrite existing files (default: refuse if any of the three tiers already exists)

### 2. Run the scaffolder

```bash
# $CLAUDE_PLUGIN_ROOT is set by Claude Code when the plugin is installed
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:create/scripts/create_agent.py" \
  --name <agent-name> \
  --role "<one-line purpose>" \
  --target <vault-or-project-root> \
  [--anchor "<phrase>"] \
  [--voice "<one line>"] \
  [--triggers "kw1, kw2, kw3"] \
  [--anti-triggers "topic1, topic2"]
```

The script prints the absolute paths of every file it created and exits 0 on
success, non-zero with a clear message if a tier already exists (use `--force`
to overwrite, or pick a different name).

### 3. Seed with researched context (encouraged)

Templates give shape; **seeding gives the agent a working first session.**
If research preceded the scaffold (vault/repo exploration, an intake
conversation, prior agent handoffs), replace the placeholders with that
material instead of leaving TODOs for later:

- `memory/critical_facts.md` — seed with dated, researched facts. Add a
  one-line provenance note ("Seeded YYYY-MM-DD by <who> from <where> at
  creation. I own this file now.") so the agent knows the baseline is
  inherited, owned, and editable.
- Per-topic profile files — quote the user's own words **with dates**; for a
  coach/planner persona those quotes are worth more than any framework.
- `tasks/open-tasks.md` — seed with a timely first session if one exists
  (an upcoming ritual date, a live situation in the agent's lane).

Seeded facts are a snapshot: date everything, and let the agent's own
self-curation take over from the first real session.

### 4. Review and customize

After the scaffold lands, walk the user through the three files that matter
most:

1. `**.claude/agents/<name>.md**` — fill in persona, boundaries, output formats.
   The template ships with section headings and `<!-- TODO -->` markers so it's
   obvious what's missing.
2. `**.claude/agent-memory/<name>/MEMORY.md**` — sanity-check the boot sequence.
   Add or remove file pointers based on what `memory/` actually contains.
3. `**.agents/<name>/memory/PRIVACY.md**` — set the privacy posture before the
   agent is ever invoked. The template has prompts for what to redact, what to
   keep in buckets, and what to point-to-vault rather than duplicate.

### 5. Run a first audit

After customization, the user can run `mh:agent:audit` (the sister skill in
this plugin) against the new agent to check that:

- All boot-sequence files referenced in MEMORY.md actually exist
- The description has both positive triggers and "do NOT trigger" rules
- PRIVACY.md, tasks/, and sessions/ are present
- Cross-tier consistency holds (name, identity one-liner)

This closes the loop: scaffold → customize → audit → iterate.

## What the scaffolder creates

```
<target>/
├── .claude/
│   ├── agents/
│   │   └── <name>.md                 ← Tier 1 — definition + system prompt
│   └── agent-memory/
│       └── <name>/
│           └── MEMORY.md             ← Tier 2 — auto-injected boot index
└── .agents/
    └── <name>/
        ├── memory/
        │   ├── PRIVACY.md            ← always read first by the agent
        │   ├── INDEX.md              ← pointers into the deep store
        │   └── _shared/.gitkeep      ← framework / pattern files (load on demand)
        ├── tasks/
        │   └── open-tasks.md         ← agent's own backlog (Markdown checkboxes)
        ├── sessions/
        │   └── .gitkeep              ← session logs land here per ritual
        ├── cache/
        │   └── .gitkeep              ← ephemeral cache (rates, RSS poll state, …)
        └── output/
            └── .gitkeep              ← draft outputs before publish
```

Templates live at `templates/` inside this skill. They are deliberately short:
they give shape, not content.

## Conventions baked into the templates

- **PRIVACY.md is step 1 of every boot sequence.** Always.
- **MEMORY.md kept ≤80 lines.** It pays its cost on every spawn — keep it lean.
  Detail goes to `memory/INDEX.md` and topic files.
- **Boot sequence is a numbered list.** No "read these files" prose — the order
  matters and should be explicit.
- **Self-curation block in the definition.** Every agent writes back at session
  end: what-works, decisions, tasks closed, MEMORY.md trim check.
- **`Subagents do NOT inherit the CLAUDE.md cascade`** is called out in the
  template — boot sequence should explicitly list any CLAUDE.md the agent
  depends on.
- **Context gaps — elicit, don't assume.** The Tier-1 template has a section
  naming the domains the memory store systematically under-represents (a
  personal vault under-represents work life; a work repo under-represents
  personal constraints). The agent asks 1–2 targeted questions when a session
  depends on a gap, and writes the answers back the same session so the gap
  shrinks over time. An agent that treats its store as complete gives
  confidently stale advice.

## What the skill does NOT do

By design, this skill stays out of the user's domain decisions:

- **No cadence integration** — no daily/weekly/monthly assumptions, no embedding
  the agent in any periodic-routine flow. If the user wants that, they wire it after.
- **No external-system handoffs** — no MCP wiring, no queue conventions, no
  cron/scheduling. The scaffolded agent is fully self-contained.
- **No persona invention** — anchor phrase, voice, triggers, and tool boundaries
  are user input. Templates have placeholders, not opinions.
- **No vault opinions** — the scaffolder writes the three tiers wherever you
  point it. It does not touch existing CLAUDE.md, README, or git config.

## Inputs / outputs

**Inputs:** name, role, target dir, optional anchor / voice / triggers / anti-triggers.
**Outputs:** three tiers of files described above, absolute-path-listed on stdout.
**Exit codes:** 0 on success; non-zero with a clear message on collision or
invalid input.

## See also

- `mh:agent:audit` — sister skill, checks the structure for completeness and
  cross-tier consistency.
- The plugin README at `plugins/mh/README.md`.
