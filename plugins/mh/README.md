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

## Compatibility

- **Python 3.10+** for any bundled server scripts (stdlib only).
- **Modern Chromium / Firefox / Safari** (mid-2024+) for artifact-side JS.
- **Claude Code** with plugin support.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](../../LICENSE)
