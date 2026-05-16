# mhlavac-marketplace

A small [Claude Code](https://claude.com/code) plugin marketplace by
[@mhlavac](https://github.com/mhlavac). Reusable primitives for collaborating
with Claude on rich artifacts and multi-turn iteration loops, kept small
enough to be droppable into someone else's setup.

## Plugins

| Plugin | What it does |
|---|---|
| [`annotated-feedback`](plugins/annotated-feedback) | Turn any HTML artifact into a structured-feedback surface — inline form elements (textareas, radios, checkboxes, action buttons) keyed by stable IDs, plus a freeform annotation overlay (text highlights, diagram pins, sketches, general comments). One Submit produces a paste-ready Markdown prompt for the next Claude turn. Mermaid + perfect-freehand vendored, zero CDN deps. |

## Install

### From GitHub

```
/plugin marketplace add mhlavac/claude-marketplace
/plugin install annotated-feedback@mhlavac-marketplace
```

### From a local clone

```
/plugin marketplace add /path/to/your/clone/claude-marketplace
/plugin install annotated-feedback@mhlavac-marketplace
```

### Update after changes

```
/plugin marketplace update mhlavac-marketplace
```

## Use after install

Each plugin's skills are callable as `<plugin-name>:<skill-name>` — e.g. the
`annotated-feedback` plugin's skill is invoked via
`annotated-feedback:annotated-feedback` (plugin name + skill name; the skill
happens to share the plugin's name here). It also auto-triggers based on its
description when the agent decides it fits the task.

See each plugin's own README + SKILL.md for usage details:

- [`annotated-feedback` plugin README](plugins/annotated-feedback/README.md)
- [`annotated-feedback` skill docs](plugins/annotated-feedback/skills/annotated-feedback/SKILL.md)

## Compatibility

- **Python 3.10+** for the bundled server scripts (stdlib only — no pip/uv).
- **Modern Chromium/Firefox/Safari** (released mid-2024 or later) for the
  artifact-side JS (uses CSS Custom Highlight API, native `<dialog>`, ES
  modules).
- **Claude Code** with plugin support.

## Structure

```
.
├── .claude-plugin/
│   └── marketplace.json           ← marketplace manifest
├── plugins/
│   └── annotated-feedback/
│       ├── .claude-plugin/
│       │   └── plugin.json        ← plugin manifest
│       ├── README.md              ← plugin overview + quickstart
│       └── skills/
│           └── annotated-feedback/
│               ├── SKILL.md       ← the skill itself
│               ├── assets/        ← template.html, server.py, vendor/
│               ├── scripts/       ← new_artifact.py
│               └── references/    ← form-elements.md, envelope-and-prompt.md
└── README.md                       ← this file
```

## Uninstall

```
/plugin uninstall annotated-feedback@mhlavac-marketplace
/plugin marketplace remove mhlavac-marketplace
```

## Issues & contributions

[github.com/mhlavac/claude-marketplace/issues](https://github.com/mhlavac/claude-marketplace/issues)

## License

[MIT](LICENSE) — fork, copy, adapt freely.
