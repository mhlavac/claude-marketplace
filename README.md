# mhlavac-marketplace

Personal [Claude Code](https://claude.com/code) plugin marketplace by Martin Hlavac.

Reusable primitives for collaborating with Claude on rich artifacts, periodic
notes, and family flows — extracted from a working personal vault, kept
small enough to be droppable into someone else's setup.

## Plugins

| Plugin | What it does |
|---|---|
| [`annotated-feedback`](plugins/annotated-feedback) | Turn any HTML artifact into a structured-feedback surface — inline form elements (textareas, radios, checkboxes, action buttons) keyed by stable IDs, plus a freeform annotation overlay (text highlights, diagram pins, sketches, general comments). One Submit produces a paste-ready Markdown prompt for the next Claude turn. Mermaid + perfect-freehand vendored, zero CDN deps. |

## Install

### From GitHub (once pushed)

```
/plugin marketplace add martinhlavac/claude-marketplace
/plugin install annotated-feedback@mhlavac-marketplace
```

Replace `martinhlavac` with the actual GitHub owner once the repo is public.

### From a local clone (development / pre-publish)

```
/plugin marketplace add ~/Personal/Workspace/claude-marketplace
/plugin install annotated-feedback@mhlavac-marketplace
```

### Update after changes

```
/plugin marketplace update mhlavac-marketplace
```

## Use after install

Each plugin's skills become callable as `<plugin-name>:<skill-name>` — e.g.
the `annotated-feedback` plugin's skill is invoked via `annotated-feedback:annotated-feedback`,
or auto-triggers based on its description when the agent decides it fits the task.

See each plugin's own README / SKILL.md for usage details:

- [`annotated-feedback` skill docs](plugins/annotated-feedback/skills/annotated-feedback/SKILL.md)

## Structure

```
.
├── .claude-plugin/
│   └── marketplace.json           ← marketplace manifest
├── plugins/
│   └── annotated-feedback/
│       ├── .claude-plugin/
│       │   └── plugin.json        ← plugin manifest
│       └── skills/
│           └── annotated-feedback/
│               ├── SKILL.md       ← the skill itself
│               ├── assets/        ← template.html, server.py, vendor/
│               ├── scripts/       ← new_artifact.py
│               └── references/    ← form-elements.md, envelope-and-prompt.md
└── README.md                       ← this file
```

## License

[MIT](LICENSE) — fork, copy, adapt freely.

## Contact

baldur.e@gmail.com
