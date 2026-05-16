# Form-element markup (`.af-q`)

The annotation layer's JS scans the DOM at load time for elements with class
`.af-q`. Each one becomes a **question** the user can answer; the answer surfaces
in the panel sidebar (live, as the user types) and ships in the submit envelope's
`form_responses` array. The agent reads those back in the prompt.md output.

## Common attributes

Every `.af-q` block carries:

| attribute | required | meaning |
|---|---|---|
| `data-q-id` | **yes** | Stable identifier. Use snake_case. Surfaces verbatim in the prompt and JSON, so keep it human-readable (`headline_tone`, `phase_1_decision`, `risks_to_flag`). |
| `data-q-type` | optional | `text`, `textarea`, `radio`, `checkbox`, or `action`. Inferred from the input children if omitted. |
| `data-q-prompt` | optional | What you're asking. If omitted, the `.af-q-label` or `<legend>` text is used. Set it explicitly for prompts that contain markup. |

Inside the block, include an optional `.af-q-label`, an optional `.af-q-help`
italic hint, and one or more inputs. The label text becomes the human-readable
prompt in the prompt.md output.

---

## Type: `text` — single-line input

```html
<div class="af-q" data-q-id="headline_tone" data-q-type="text"
     data-q-prompt="One-word tone for the headline">
  <label class="af-q-label">One-word tone for the headline</label>
  <p class="af-q-help">e.g. "playful", "sober", "punchy"</p>
  <input type="text" name="headline_tone" placeholder="One word">
</div>
```

## Type: `textarea` — multi-line free text

```html
<div class="af-q" data-q-id="open_concerns" data-q-type="textarea"
     data-q-prompt="What's missing or wrong?">
  <label class="af-q-label">What's missing or wrong?</label>
  <textarea name="open_concerns" rows="4"
            placeholder="Anything you'd push back on, anything I should have asked but didn't…"></textarea>
</div>
```

## Type: `radio` — pick exactly one

Use when the choices are mutually exclusive. Wrap the options in a
`<fieldset>` with `<legend class="af-q-label">`, or just use `.af-q-label`
above the options.

```html
<div class="af-q" data-q-id="phase_1_decision" data-q-type="radio"
     data-q-prompt="Phase 1 — go, hold, or reshape?">
  <fieldset>
    <legend class="af-q-label">Phase 1 — go, hold, or reshape?</legend>
    <div class="af-q-options">
      <label><input type="radio" name="phase_1_decision" value="go">       Go as proposed</label>
      <label><input type="radio" name="phase_1_decision" value="hold">     Hold for now</label>
      <label><input type="radio" name="phase_1_decision" value="reshape">  Reshape (use comments below)</label>
    </div>
  </fieldset>
</div>
```

## Type: `checkbox` — pick any (zero or more)

```html
<div class="af-q" data-q-id="risks_to_flag" data-q-type="checkbox"
     data-q-prompt="Which risks should v2 address?">
  <fieldset>
    <legend class="af-q-label">Which risks should v2 address? (pick any)</legend>
    <div class="af-q-options">
      <label><input type="checkbox" name="risks" value="latency">  Latency</label>
      <label><input type="checkbox" name="risks" value="cost">     Cost</label>
      <label><input type="checkbox" name="risks" value="privacy">  Privacy</label>
      <label><input type="checkbox" name="risks" value="ux_kids">  Kid-UX edge cases</label>
    </div>
  </fieldset>
</div>
```

## Type: `action` — buttons that auto-submit

Action buttons are the **decision short-circuit**. Clicking one immediately
submits the whole envelope (form + annotations) with the action recorded under
`action: {id, value, label}`. Use these when you want a single click to close
the loop — "Approve and proceed", "Send back for v2", "Defer to next quarter".

```html
<div class="af-q" data-q-id="proposal_decision" data-q-type="action"
     data-q-prompt="What's your call on this proposal?">
  <label class="af-q-label">What's your call on this proposal?</label>
  <div class="af-q-actions">
    <button type="button" class="af-action" data-value="approve" data-label="Approve and proceed">Approve →</button>
    <button type="button" class="af-action af-action-secondary" data-value="revise" data-label="Send back for v2">Send back for v2</button>
    <button type="button" class="af-action af-action-defer" data-value="defer" data-label="Defer">Defer</button>
  </div>
</div>
```

When the user clicks one, all currently-typed form values + all annotations are
included in the envelope. The agent's prompt.md gets a `## Decision` section at
the top showing what they chose.

---

## Anti-patterns

- **Don't include a `<form>` element** around `.af-q` blocks. The annotation
  layer doesn't submit through HTML form semantics — there's one global Submit
  button in the toolbar and one global submit handler. Stray forms can intercept
  Enter keypresses inside textareas.
- **Don't repeat `data-q-id` values.** Each ID is the key into `form_responses` —
  duplicates clobber.
- **Don't make every question required-looking.** Empty answers are valid;
  the user may only want to annotate.
- **Don't put a question inside a `.af-q` inside a `.af-q`.** Flat is fine.
- **Don't omit `data-q-id`.** The discovery loop skips blocks without it and logs
  a warning to the console.

## Tips

- **Three or four well-placed prompts** beat a checklist of ten. Let the
  annotation overlay handle the long-tail of comments.
- **Match the prompt's verb to the answer type.** "What…" → textarea.
  "Which…" → radio/checkbox. "Should we…" → action or radio with `yes/no/defer`.
- **Pre-fill text inputs** where you can — set the textarea's contents to a
  reasonable default so the user can edit instead of starting from blank.
- **Use action buttons sparingly.** They short-circuit the loop; if the user
  needs to also leave comments, they'd lose the "comments first, then decision"
  ergonomics. Pair an action question with an optional textarea above it when
  in doubt.
