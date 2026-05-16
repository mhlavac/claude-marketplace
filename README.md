# mhlavac-marketplace

A small [Claude Code](https://claude.com/code) plugin marketplace by
[@mhlavac](https://github.com/mhlavac). Ships a single plugin, `mh`, that
bundles personal skills — reusable primitives for collaborating with Claude on
rich artifacts and multi-turn iteration loops.

## Plugin

| Plugin | Skills | What it does |
|---|---|---|
| [`mh`](plugins/mh) | `mh:annotated-feedback` | Personal skill bundle — see the [plugin README](plugins/mh/README.md) for the current skill list. |

## Install

### From GitHub

```
/plugin marketplace add mhlavac/claude-marketplace
/plugin install mh@mhlavac-marketplace
```

### From a local clone

```
/plugin marketplace add /path/to/your/clone/claude-marketplace
/plugin install mh@mhlavac-marketplace
```

### Update after changes

```
/plugin marketplace update mhlavac-marketplace
```

## Use after install

All skills live under the `mh` plugin and are invoked as `mh:<skill-name>` —
e.g. `mh:annotated-feedback`. Skills also auto-trigger based on their
description when the agent decides they fit.

See each skill's `SKILL.md` and `README.md` for details:

- [`mh:annotated-feedback`](plugins/mh/skills/annotated-feedback/README.md)

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
│   └── mh/
│       ├── .claude-plugin/
│       │   └── plugin.json        ← plugin manifest (name: mh)
│       ├── README.md              ← plugin overview + skill index
│       ├── CHANGELOG.md           ← plugin-level changelog
│       └── skills/
│           └── annotated-feedback/
│               ├── SKILL.md       ← the skill itself
│               ├── README.md      ← skill-specific docs
│               ├── assets/        ← template.html, server.py, vendor/
│               ├── scripts/       ← new_artifact.py
│               └── references/    ← form-elements.md, envelope-and-prompt.md
├── CLAUDE.md                       ← repo rules (license, naming, commits)
├── CONTRIBUTING.md                 ← contribution guide
├── LICENSE                         ← MIT
└── README.md                       ← this file
```

## Uninstall

```
/plugin uninstall mh@mhlavac-marketplace
/plugin marketplace remove mhlavac-marketplace
```

## Issues & contributions

[github.com/mhlavac/claude-marketplace/issues](https://github.com/mhlavac/claude-marketplace/issues) — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) — fork, copy, adapt freely.
