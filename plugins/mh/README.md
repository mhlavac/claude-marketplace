# mh

Personal Claude Code skill bundle by [@mhlavac](https://github.com/mhlavac).
Reusable primitives for collaborating with Claude on rich artifacts and
multi-turn iteration loops.

## Install

```
/plugin marketplace add mhlavac/claude-marketplace
/plugin install mh@mhlavac-marketplace
```

All skills in this plugin are invoked as `mh:<skill-name>`, or auto-trigger
based on their `SKILL.md` description.

## Skills

| Skill | Invoke as | What it does |
|---|---|---|
| [`annotated-feedback`](skills/annotated-feedback/README.md) | `mh:annotated-feedback` | Turn any HTML artifact into a structured-feedback surface — inline form elements + freeform annotation overlay (highlights, pins, sketches). One Submit produces a paste-ready Markdown prompt for the next Claude turn. |
| [`agent:create`](skills/agent:create/README.md) | `mh:agent:create` | Scaffold a three-tier Claude Code subagent — definition + auto-injected memory index + deep memory store. Builds in patterns from the academic literature: importance-at-capture (Generative Agents), cross-link on write (A-MEM), failure attribution (Reflexion), append-only chronology + Two-Output Rule, named blocks in the auto-injected index. Optional `--with-hooks` wires `PreCompact` / `SessionEnd` / `SessionStart`. |
| [`agent:audit`](skills/agent:audit/README.md) | `mh:agent:audit` | Lint a three-tier subagent: frontmatter + triggers, persona, boot sequence, ≤80-line memory index, `critical_facts.md` budget, `log.md` recency, `DREAMS.md` cadence, importance scoring on append-only files, named blocks, lifecycle hooks installed, cross-tier consistency. `--mode drift` shows what's missing vs latest templates (subject-folder aware); `--mode apply` writes missing files non-destructively. |
| [`agent:dream`](skills/agent:dream/README.md) | `mh:agent:dream` | Periodic memory-consolidation pass — Sleep-time Compute (Letta 2025) on file-based memory. Snapshot → inventory → classify each entry (keep / drop / merge / promote episodic→semantic / enhance) → apply → append structured stats to `DREAMS.md` → log. |

## Compatibility

- **Python 3.10+** for any bundled server scripts (stdlib only).
- **Modern Chromium / Firefox / Safari** (mid-2024+) for artifact-side JS.
- **Claude Code** with plugin support.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](../../LICENSE)
