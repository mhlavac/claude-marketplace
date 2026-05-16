# Changelog

All notable changes to the `annotated-feedback` plugin.
This project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-05-16

Initial public release.

### Features

- Skill `annotated-feedback` with auto-trigger description and slash invocation
- HTML template with annotation overlay (text-highlight, pin, sketch, general comment) and `.af-q` form-element discovery (text, textarea, radio, checkbox, action)
- Live right-side sidebar showing every form answer + annotation as the user types
- Stdlib Python receiver server (`server.py`) — writes W3C-shaped JSON envelopes and paste-ready Markdown prompts to `feedback/`
- One-shot scaffolder script (`scripts/new_artifact.py`)
- Vendored Mermaid 11.4.1 + perfect-freehand 1.2.2 — zero CDN deps at runtime
- Mermaid diagram support with pin anchors on individual nodes/edges
- localStorage persistence per artifact URL
- W3C Web Annotation Data Model envelope (TextQuoteSelector / CssSelector + FragmentSelector / SvgSelector)

### Security

- POST `/feedback` requires `Content-Type: application/json` and same-origin `Origin` header — CSRF-guarded
- 5 MB body cap on submissions
- Mermaid initialised with `securityLevel: 'strict'`
- Path-traversal blocked in static-file fallback
- Server binds to `127.0.0.1` only

### Known gaps (deferred to future releases)

- No screenshot / GIF in the README — coming once the project has its first real public demo
- No example artifact under `examples/` — the `new_artifact.py` scaffolder produces one in seconds, but a pre-built one would shorten the first-look loop further
