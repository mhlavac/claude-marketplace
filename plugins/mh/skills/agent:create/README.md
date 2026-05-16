# agent:create

A skill in the [`mh`](../../README.md) Claude Code plugin that scaffolds a new
**stateful subagent** using a three-tier memory architecture.

## What it generates

Three tiers, one shot:

1. **`.claude/agents/<name>.md`** — the definition the Claude Code harness reads
   to spawn the agent (YAML frontmatter + system prompt body).
2. **`.claude/agent-memory/<name>/MEMORY.md`** — a small index file (≤80 lines)
   auto-injected into the agent's context on every spawn. Contains the boot
   sequence — an ordered list of deeper files to read before doing real work.
3. **`.agents/<name>/`** — the deep memory store. `memory/` (with `PRIVACY.md`,
   `INDEX.md`, `_shared/`), `tasks/open-tasks.md`, `sessions/`, `cache/`,
   `output/`.

## Install

```
/plugin marketplace add mhlavac/claude-marketplace
/plugin install mh@mhlavac-marketplace
```

Invoke as `mh:agent:create`, or let the agent auto-trigger it from the SKILL.md
description ("scaffold a subagent", "new persona", "create an agent for…").

## 30-second quickstart

```bash
# After install, $CLAUDE_PLUGIN_ROOT points at plugins/mh
python3 "$CLAUDE_PLUGIN_ROOT/skills/agent:create/scripts/create_agent.py" \
  --name code-reviewer \
  --role "Reviews pull requests for correctness, security, and style" \
  --target ~/projects/my-vault
```

Result:

```
~/projects/my-vault/.claude/agents/code-reviewer.md
~/projects/my-vault/.claude/agent-memory/code-reviewer/MEMORY.md
~/projects/my-vault/.agents/code-reviewer/memory/PRIVACY.md
~/projects/my-vault/.agents/code-reviewer/memory/INDEX.md
~/projects/my-vault/.agents/code-reviewer/tasks/open-tasks.md
~/projects/my-vault/.agents/code-reviewer/{sessions,cache,output,_shared}/...
```

Open the three TODO-marked files, fill in the persona / triggers / boundaries,
and the agent is ready to invoke.

## What's inside

| Piece | Where |
|---|---|
| **Skill body** | [`SKILL.md`](SKILL.md) — what the agent reads when triggered |
| **Scaffolder** | `scripts/create_agent.py` — stdlib Python, no pip deps |
| **Templates** | `templates/` — the three tiers, with placeholders |

## Why three tiers?

Single-file system prompts work for one-off agents. They break down when:

- You need the agent to **remember decisions** across sessions
- You want **per-topic state** (per-person, per-project) without bloating the
  prompt
- You want the agent to **curate its own memory** (append what-works, log a
  session, close a task)

The three-tier split makes the cost/value of each file explicit:

- **Tier 1** loads at *spawn cost* — keep it tight, persona-defining.
- **Tier 2** loads at *every-spawn cost* — keep it ≤80 lines, an index only.
- **Tier 3** loads at *on-demand cost* — go deep, the agent fetches what it needs.

## What this skill deliberately leaves out

- No cadence (no daily/weekly/monthly assumptions)
- No external-system handoffs (no MCPs, queues, cron)
- No persona invention (anchor / voice / triggers are user input)
- No opinions about the host vault/project

Pair with `mh:agent:audit` to validate the scaffolded agent stays healthy as
it accrues memory.
