# Envelope shape + prompt rendering

## What POSTs to `/feedback`

```json
{
  "document": {
    "url": "http://127.0.0.1:8765/",
    "title": "<page title>",
    "submittedAt": "2026-05-16T09:00:00.000Z",
    "userAgent": "Mozilla/5.0 …"
  },
  "form_responses": [
    {
      "id": "headline_tone",
      "type": "text",
      "prompt": "One-word tone for the headline",
      "value": "playful"
    },
    {
      "id": "phase_1_decision",
      "type": "radio",
      "prompt": "Phase 1 — go, hold, or reshape?",
      "value": "reshape"
    },
    {
      "id": "risks_to_flag",
      "type": "checkbox",
      "prompt": "Which risks should v2 address?",
      "value": ["cost", "ux_kids"]
    },
    {
      "id": "open_concerns",
      "type": "textarea",
      "prompt": "What's missing or wrong?",
      "value": ""
    }
  ],
  "action": {
    "id": "proposal_decision",
    "value": "approve",
    "label": "Approve and proceed",
    "prompt": "What's your call on this proposal?"
  },
  "annotations": [
    {
      "id": "a-mfu1m4w-k3a7q",
      "type": "Annotation",
      "motivation": "commenting",
      "created": "2026-05-16T09:00:00.000Z",
      "body": [{ "type": "TextualBody", "value": "Disagree — this overstates the case.",
                  "format": "text/plain", "purpose": "commenting" }],
      "target": {
        "source": "http://127.0.0.1:8765/",
        "selector": [
          { "type": "TextQuoteSelector",
            "exact": "The right answer is always local.",
            "prefix": "…and so ", "suffix": " That's not …" }
        ]
      }
    },
    {
      "id": "a-mfu1m4w-aaa11",
      "type": "Annotation",
      "motivation": "commenting",
      "created": "2026-05-16T09:00:05.000Z",
      "body": [{ "type": "TextualBody", "value": "Move this arrow to FastAPI",
                  "format": "text/plain", "purpose": "commenting" }],
      "target": {
        "source": "http://127.0.0.1:8765/",
        "selector": [
          { "type": "CssSelector", "value": "main>section:nth-of-type(3)>.diagram" },
          { "type": "FragmentSelector",
            "conformsTo": "http://www.w3.org/TR/media-frags/",
            "value": "xywh=percent:62.40,38.10,0,0" }
        ]
      }
    },
    {
      "id": "a-mfu1m4w-bbb22",
      "type": "Annotation",
      "motivation": "sketching",
      "created": "2026-05-16T09:00:10.000Z",
      "body": [{ "type": "TextualBody", "value": "this region needs work", "format": "text/plain" }],
      "target": {
        "source": "http://127.0.0.1:8765/",
        "selector": [{ "type": "SvgSelector", "value": "<svg …><path d=\"M …\"/></svg>" }]
      },
      "_bbox": { "x": 480, "y": 1200, "w": 240, "h": 180 }
    },
    {
      "id": "a-mfu1m4w-ccc33",
      "type": "Annotation",
      "motivation": "commenting",
      "created": "2026-05-16T09:00:15.000Z",
      "body": [{ "type": "TextualBody", "value": "Overall: the structure is right. Tone could be punchier.",
                  "format": "text/plain", "purpose": "commenting" }],
      "target": { "source": "http://127.0.0.1:8765/" }
    }
  ],
  "submittedAt": "2026-05-16T09:00:20.000Z",
  "triggeredBy": "action"
}
```

### Field reference

| Field | Notes |
|---|---|
| `document.url` | Browser URL — useful as the anchor `source` for selectors. |
| `document.title` | `<title>` of the page. Becomes the H1 in the prompt.md. |
| `form_responses[]` | One entry per discovered `.af-q` block, **including unanswered ones** (so the agent sees what was skipped). |
| `form_responses[].type` | `text` / `textarea` / `radio` / `checkbox`. |
| `form_responses[].value` | String (text/radio), array of strings (checkbox), or empty string / empty array. |
| `action` | Present **only** when an `.af-action` button was clicked. Otherwise `null`. |
| `annotations[]` | W3C Web Annotation-shaped. See selector types below. |
| `triggeredBy` | `"submit"` for the toolbar button, `"action"` for an action-button click. |

### Annotation selector types

| Selector | Used for | Re-resolution strategy |
|---|---|---|
| `TextQuoteSelector` | Text highlights | Search `<main id="af-content">` text for `prefix+exact`, then `exact`. |
| `CssSelector` + `FragmentSelector` | Pin on a specific element at `xywh=percent:x,y,0,0` | `document.querySelector(css)` then position via percent inside that element. |
| `SvgSelector` | Free-form sketch | The inline SVG fragment contains a `<path d="…">` in document coordinates. `_bbox` (non-standard) helps render position. |
| _no selector_ | General comment | No DOM anchor — pure prose feedback. |

Unanchored sketches and general comments still count as feedback; the prompt
will list them under the annotations section without a specific target.

---

## What the server writes

For each submission, two files land in `./feedback/`:

```
2026-05-16T07-53-04.806481+00-00__Some_Title__7bd70539ffe9.json
2026-05-16T07-53-04.806481+00-00__Some_Title__7bd70539ffe9.prompt.md
```

The `.json` is the raw envelope plus `_received_at` and `_id`.
The `.prompt.md` is the agent's primary read — designed to paste straight into
the next Claude turn.

### Prompt.md template

```markdown
# Feedback on **<title>**
`<url>`
Triggered by: **<submit | action>**

## Decision           (only if an action button was clicked)
- **<prompt>** → `<value>` (<label>)

## Form responses     (only if 1+ questions were answered)
- **<prompt>** (`<id>`, <type>): <value>
- ...

## Skipped questions  (only if 1+ questions were left blank)
- _<prompt>_ — `<id>`

## Annotations (N)
1. **[<motivation>]** <anchor description>
   → <comment body>

---
Apply each form answer + comment as a concrete edit. For sketches without text,
infer intent from the path location, restate what you understood, then apply.
If a decision action was clicked, that's the user's authoritative call.
```

## Consuming the envelope in the next turn

The simplest pattern: the orchestrating agent reads the latest
`feedback/*.prompt.md` and treats it as the user's reply for the v2 iteration.
That file is human-readable and rich enough to drive substantive edits.

For agents that want structured access (route specific form fields to specific
subagents — e.g. a multi-agent conversation page where several subagents each
contribute one fragment), read the corresponding `.json` and dispatch by `id`
namespace:

```python
import json, pathlib, sys
env = json.loads(pathlib.Path(sys.argv[1]).read_text())
for q in env["form_responses"]:
    agent_id, _, sub_field = q["id"].partition("__")  # e.g. "planner__phase_1_decision"
    ...  # route to that agent via SendMessage
```

A simple naming convention like `<agent>__<field>` for question IDs is the
recommended bridge to multi-agent flows. It keeps the same UI primitive
serving both "ask the user one question" and "ask N agents their own questions
in one page."
