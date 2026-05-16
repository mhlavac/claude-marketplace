# annotated-feedback

A skill in the [`mh`](../../README.md) Claude Code plugin that turns any HTML
artifact into a structured-feedback surface.

The user reads, answers explicit form questions you embedded, annotates freely
(highlight text, pin diagrams, sketch, leave general notes), hits one Submit
button. A small local server writes both the raw envelope (W3C Web
Annotation-shaped JSON) and a paste-ready Markdown prompt for the next Claude
turn.

## Install

```
/plugin marketplace add mhlavac/claude-marketplace
/plugin install mh@mhlavac-marketplace
```

Invoke as `mh:annotated-feedback`, or let the agent auto-trigger it from the
skill description.

## What's inside

| Piece | Where |
|---|---|
| **Skill** | [`SKILL.md`](SKILL.md) — the skill body the agent reads |
| **Template** | `assets/template.html` — single-file HTML with the annotation overlay, form discovery, sidebar, vendored Mermaid + perfect-freehand |
| **Server** | `assets/server.py` — stdlib HTTP server, ~270 lines, no pip deps |
| **Helper** | `scripts/new_artifact.py` — one-shot scaffolder |
| **Refs** | `references/form-elements.md` (markup spec), `references/envelope-and-prompt.md` (envelope schema + prompt rendering) |

## 30-second quickstart

```bash
# Scaffold a new artifact folder (after install, $CLAUDE_PLUGIN_ROOT points to plugins/mh)
python3 "$CLAUDE_PLUGIN_ROOT/skills/annotated-feedback/scripts/new_artifact.py" \
  ~/my-artifact --title "My Decision" --kicker "Design review"

# Start the server
cd ~/my-artifact && python3 server.py --port 8765

# Open it
open http://127.0.0.1:8765/
```

Edit `~/my-artifact/index.html` to fill in content and drop `<div class="af-q">`
question blocks where you want answers. The page hot-reads from disk on every
request, so a browser refresh shows v2.

Submitted envelopes land in `~/my-artifact/feedback/<timestamp>__<id>.json`
plus a paste-ready `<same>.prompt.md` next to each one.

## Feature highlights

- **Text annotation** — select any text in the doc, popup asks for a comment, highlight stays via CSS Custom Highlight API
- **Pin annotation** — click on diagrams / tables / code blocks / callouts to drop a numbered pin with a note
- **Free-form sketch** — drag to draw with [`perfect-freehand`](https://github.com/steveruizok/perfect-freehand) (variable thickness, simulated pressure, ink-like strokes)
- **Mermaid diagrams** — drop `<div class="mermaid">flowchart …</div>` blocks; render to SVG with pin anchors on individual nodes/edges
- **General comments** — un-anchored notes via a sidebar button
- **Form elements** — `text`, `textarea`, `radio`, `checkbox`, `action` (auto-submit) — all discovered automatically by `.af-q` class
- **Live sidebar** — every input visible as you type
- **localStorage persistence** — refresh doesn't lose work
- **Action buttons** — short-circuit submission with a decision recorded
- **W3C Web Annotation envelope** — text-quote selectors, CSS+fragment pins, SVG strokes

## Security posture

- Server binds to `127.0.0.1` only — single-user local tool, no remote exposure
- `POST /feedback` requires `Content-Type: application/json` and a same-origin `Origin` header (CSRF-guarded to prevent malicious pages from writing prompt-injection content)
- 5 MB body cap (DoS guard)
- Mermaid initialised with `securityLevel: 'strict'` (HTML in diagram labels is sanitised)
- Path-traversal blocked in the static-file fallback
- No subprocess, no eval, no shell — pure stdlib Python

## Compatibility

- **Python 3.10+** (stdlib only)
- **Modern Chromium / Firefox / Safari** released after mid-2024 (uses CSS Custom Highlight API, `<dialog>`, ES module imports)

## Third-party assets

This plugin vendors:

- **[mermaid](https://github.com/mermaid-js/mermaid) 11.4.1** — MIT, +transitive deps under MIT / BSD / ISC / Apache-2.0 / MPL-2.0
- **[perfect-freehand](https://github.com/steveruizok/perfect-freehand) 1.2.2** — MIT

Full license texts: [`assets/vendor/LICENSES/`](assets/vendor/LICENSES/).

## Changelog

See the plugin-level [CHANGELOG.md](../../CHANGELOG.md).

## License

[MIT](../../../../LICENSE)
