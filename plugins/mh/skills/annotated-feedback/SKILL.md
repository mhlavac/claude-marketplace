---
name: annotated-feedback
description: |
  Ship any HTML artifact (architecture doc, design proposal, decision card,
  periodic-note conversation page, code-review summary) wired to receive **two
  complementary channels of user feedback in a single envelope**: (1) explicit
  form elements that you embed inline — textareas, radio groups, checkboxes,
  action buttons — keyed by stable question IDs so you can ask the user specific
  things; and (2) a freeform annotation overlay — highlight-then-comment on any
  text, drop pinned notes on diagrams/tables/callouts, free-form sketch on top
  of anything, plus un-anchored "general" comments. Both channels surface live
  in a single right-side panel and submit together. A small stdlib Python server
  receives the envelope and writes a paste-ready Markdown prompt you can hand
  straight to the next Claude turn.

  **Use this skill when the agent is producing a non-trivial HTML artifact the
  user will want to react to** — architecture docs, multi-option decisions,
  design reviews, daily/weekly conversation pages, research synthesis, proposed
  plans, code-review write-ups, anything where "what do you think?" is the
  right next move. Also trigger when the user says "ask me", "build a form
  for", "let me annotate", "let me sketch on this", "make it interactive",
  "wire it to a server", "iterate with me", or "give me a v2 after I look at it".

  Skip for plain prose answers, simple file edits, terminal-only tasks, or
  anything where a Markdown reply is enough.
---

# annotated-feedback

A reusable loop for turning any HTML artifact into a structured-feedback surface.
The user reads, **answers explicit questions you embedded**, **annotates freely**
(highlight, pin, sketch, general comment), hits one Submit button. The server writes
a paste-ready prompt the next agent turn consumes.

## When this earns its place

You are about to hand the user an artifact and you genuinely want their reaction —
not their thumbs-up. Use this skill if any of these are true:

- The artifact has open decisions ("which approach do you prefer?") that need a typed answer
- The artifact has loose ends ("did I capture the constraint correctly?") that the
  user can only flag by pointing at the exact spot
- You'd otherwise be guessing what to change in v2 — better to ask once and iterate fast
- The agent is part of a periodic-note flow (daily, weekly, monthly) where the user
  is going to read a card and reply

## The four-step flow

### 1. Create a working folder for the artifact

Pick a folder where the artifact + its feedback audit trail should live —
typically a project subfolder (`~/projects/my-thing/feedback-round-1/`),
a periodic-note folder, or a scratch dir. The submissions land next to the
artifact, so put it where you want the audit trail.

The recommended way is the helper script — it copies template + server +
vendored JS in one shot:

```bash
# $CLAUDE_PLUGIN_ROOT is set by Claude Code when invoking a plugin's skill
SKILL="$CLAUDE_PLUGIN_ROOT/skills/annotated-feedback"
OUT="<absolute path to your artifact folder>"
python3 "$SKILL/scripts/new_artifact.py" "$OUT" --title "..." --kicker "..." --deck "..."
```

If `$CLAUDE_PLUGIN_ROOT` isn't set (running outside the plugin runtime), point
`$SKILL` at wherever this skill's directory lives on your machine — see the
file tree at the bottom of this doc.

Manual copy (only if the helper doesn't fit):

```bash
mkdir -p "$OUT/feedback" "$OUT/vendor"
cp    "$SKILL/assets/template.html" "$OUT/index.html"
cp    "$SKILL/assets/server.py"     "$OUT/server.py"
cp -R "$SKILL/assets/vendor/"*      "$OUT/vendor/"
```

### 2. Fill in content + embed form questions

Open `index.html`. Inside `<main id="af-content">`, write the artifact body in
whatever editorial style fits. Wherever you want a typed answer, drop a
`<div class="af-q">` block — see `references/form-elements.md` for the full
question-type spec (text, textarea, radio, checkbox, action button).

Keep question IDs **stable and human-readable** (`headline_tone`, `phase_1_decision`,
`risks_to_flag`) — they show up verbatim in the prompt the next Claude turn reads.

For full details on the form-element markup, **read
[references/form-elements.md](references/form-elements.md)** the first time you
use this skill or whenever you need a question type you haven't tried.

**Mermaid diagrams are supported out of the box.** Drop a fenced block in the
content area:

```html
<div class="mermaid">
flowchart LR
  A[Idea] --> B{Decision}
  B -->|yes| C[Ship]
  B -->|no|  D[Iterate]
</div>
```

It renders to inline SVG via the vendored Mermaid (`assets/vendor/mermaid.min.js`,
pinned to 11.4.1) with the doc's editorial palette. **The annotation overlay
pins anchor to specific nodes/edges inside the rendered SVG** (CSS-path
selectors target `.mermaid g.node` / `g.edge` / `g.cluster`), so the reviewer
can point at the *exact arrow that should move* rather than at the diagram as
a whole. Supported diagram types: flowchart, sequence, class, state, ER,
gantt, pie, mindmap, timeline — see the
[Mermaid docs](https://mermaid.js.org/intro/syntax-reference.html) for syntax.

### 3. Start the server in the background

```bash
cd "$OUT" && python3 server.py --port 8765 --artifact index.html
```

Use `run_in_background: true`. Stdlib only — no pip, no uv, no FastAPI. Health-check
once and then leave it:

```bash
sleep 1 && curl -sf -o /dev/null http://127.0.0.1:8765/health && echo "server up"
```

### 4. Arm the Monitor BEFORE you open the browser

**Order matters.** If you open the page first and only set up the wait-loop afterwards,
you can miss a submission that lands during the gap, and worse — you'll look careless
to the user, who'll watch you sit silently after they hit Submit.

The right primitive is `Monitor` (one notification per new submission, lifetime of
the loop). A one-shot Bash `until` loop catches only the first submit; users routinely
submit multiple times per session (smoke-test, then real input, then iterate). So use:

```bash
mkdir -p $OUT/feedback
touch $OUT/.seen-feedback
# Seed seen-set with any files that already exist
for f in $OUT/feedback/*.json; do
  [ -f "$f" ] && echo "$f" >> $OUT/.seen-feedback
done
while true; do
  for f in $OUT/feedback/*.json; do
    [ -f "$f" ] || continue
    if ! grep -qxF -- "$f" $OUT/.seen-feedback 2>/dev/null; then
      echo "NEW $f"
      echo "$f" >> $OUT/.seen-feedback
    fi
  done
  sleep 2
done
```

Run that via the `Monitor` tool with a generous `timeout_ms` (e.g. 1_800_000 = 30
min). Each `NEW <path>` line that hits stdout becomes a notification you'll receive
while doing other work — including while waiting for the user's text reply. Treat
every notification as: read the matching `.prompt.md`, acknowledge what the user
said, react.

### 5. Open the browser

Only now:

```bash
open http://127.0.0.1:8765/
```

The user starts using the page; the Monitor is already armed.

### 6. React to each submission

Every notification fires for a new `.json`. Read the sibling `.prompt.md` (paste-
ready Markdown rendering of the envelope) and act:

- **Acknowledge what they submitted** — quote the form answers and annotations back
  briefly so they know you saw it. Silence after Submit feels broken.
- **Iterate the artifact** — edit `index.html` in place (the server reads from disk
  each request — a browser refresh shows v2) or create a new file if you're
  versioning.
- **Keep going** — the Monitor stays armed; further submissions arrive as more
  notifications.

### 7. Close the loop

When the user signals they're done (or hits an action button and you've applied the
decision), kill the server and stop the Monitor:

```bash
pkill -f "server.py.*--port 8765" 2>/dev/null
# Monitor stops on TaskStop or when the timeout hits
```

## The envelope, in one paragraph

What the page POSTs is a single JSON document with two main channels: `form_responses`
(an array of `{id, type, prompt, value, label}` keyed by your question IDs) and
`annotations` (an array of W3C Web Annotation-shaped objects — text-quote anchored
comments, CSS+fragment pin anchors, SVG-path sketches, or un-anchored general
comments). Plus a `document` block (URL, title, submitted_at) and an `action`
field if the user clicked an action-typed button. The server writes both the raw
envelope and a `.prompt.md` rendering — that's what the next Claude turn reads.

Full schema and rendering rules in **[references/envelope-and-prompt.md](references/envelope-and-prompt.md)**.

## Composing with multi-agent flows

If multiple agents need to ask their own questions on the same page (e.g. a
daily-note conversation page where several subagents each contribute one
fragment), namespace question IDs as `<agent>__<field>` (double underscore):

```
planner__phase_1_decision
researcher__items_to_keep
reviewer__open_concerns
```

The orchestrating agent can then split `form_responses` by ID prefix and route
each slice to the right subagent (e.g. via `SendMessage`). See the envelope
reference for the dispatch pattern.

## What the user sees

A right-side panel labeled **Inputs** with two collapsible sections — **Questions**
(your embedded form elements, live-updating as they type) and **Annotations** (their
comments and sketches). A floating top-right toolbar with mode buttons (Select,
Comment text, Pin spot, Sketch) and a **Submit →** button. Clicking an action button
inside the doc auto-submits with that action recorded. All inputs persist in
`localStorage` per artifact URL, so a refresh doesn't lose work.

## Anti-patterns

- **Don't ask 15 questions.** Three or four well-placed prompts beat a checklist.
- **Don't reinvent the markup.** Use the `af-q` shape from
  `references/form-elements.md` so the page JS picks it up automatically.
- **Don't make all questions required.** Empty form responses are valid — the user
  may only want to annotate.
- **Don't forget action buttons** when a clear decision is needed. They short-circuit
  the loop — one click and you're done, no Submit ceremony.
- **Don't run the server long after the loop closes.** Kill it; the artifact +
  envelope JSON are the durable record.

## Files in this skill

```
<plugin-root>/skills/annotated-feedback/
├── SKILL.md                              ← you are here
├── assets/
│   ├── template.html                     ← copy this to make a new artifact
│   ├── server.py                         ← stdlib HTTP server (Python 3.10+)
│   └── vendor/
│       ├── mermaid.min.js                ← diagram rendering (MIT, v11.4.1)
│       ├── perfect-freehand.mjs          ← stroke smoothing (MIT, v1.2.2)
│       └── LICENSES/                     ← third-party attribution
├── scripts/
│   └── new_artifact.py                   ← one-shot scaffolder
└── references/
    ├── form-elements.md                  ← the af-q markup spec (read first time)
    └── envelope-and-prompt.md            ← envelope schema + prompt rendering rules
```

## Compatibility

- **Python**: 3.10+ (uses `match`-style guards, `is_relative_to`, modern stdlib).
- **Browser**: any current Chromium/Firefox/Safari released after mid-2024
  (uses CSS Custom Highlight API for text annotations, `<dialog>` for the
  comment popup, ES module imports for `perfect-freehand`).
- **Server**: binds to `127.0.0.1` only. No auth — this is a single-user
  local tool. Submission is CSRF-guarded (Origin check + JSON-only).
