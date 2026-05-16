#!/usr/bin/env python3
"""annotated-feedback receiver — stdlib only, no pip deps.

Serves an HTML artifact at `/` and accepts POST `/feedback` (W3C-shaped envelope
combining form_responses + annotations). Writes one JSON file + a paste-ready
Markdown prompt next to it under `./feedback/<timestamp>__<id>.{json,prompt.md}`.

Usage:
    python3 server.py [--port 8765] [--artifact index.html] [--dir .]

Common pattern from the parent agent (Bash with run_in_background=true):

    cd "$OUT" && python3 server.py --port 8765 --artifact index.html

Then wait for new feedback to land:

    LAST_BEFORE=$(ls -1t "$OUT/feedback"/*.json 2>/dev/null | head -1)
    until LAST=$(ls -1t "$OUT/feedback"/*.json 2>/dev/null | head -1); \\
          [ -n "$LAST" ] && [ "$LAST" != "$LAST_BEFORE" ]; \\
          do sleep 2; done
    echo "GOT $LAST"
"""
from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PORT = 8765
DEFAULT_ARTIFACT = "index.html"


def render_prompt(env: dict) -> str:
    """Turn the envelope into a clean Markdown handoff for the next Claude turn."""
    title = env.get("document", {}).get("title") or "(untitled)"
    url = env.get("document", {}).get("url") or ""
    form = env.get("form_responses") or []
    annos = env.get("annotations") or []
    action = env.get("action")
    triggered_by = env.get("triggeredBy") or "submit"

    lines: list[str] = [
        f"# Feedback on **{title}**",
        f"`{url}`",
        f"Triggered by: **{triggered_by}**",
        "",
    ]

    if action:
        prompt_txt = action.get("prompt") or "Action"
        label_txt = action.get("label")
        suffix = f" ({label_txt})" if label_txt and label_txt != action.get("value") else ""
        lines += [
            "## Decision",
            f"- **{prompt_txt}** → `{action.get('value')}`{suffix}",
            "",
        ]

    # Action-type questions get rendered in the Decision section above; exclude
    # them from "answered" and "skipped" so they don't appear in two places.
    form_for_listing = [q for q in form if q.get("type") != "action"]
    answered = [q for q in form_for_listing if _is_answered(q)]
    skipped = [q for q in form_for_listing if not _is_answered(q)]

    if answered:
        lines.append("## Form responses")
        for q in answered:
            qid = q.get("id", "?")
            prompt = q.get("prompt") or qid
            val = q.get("value")
            if isinstance(val, list):
                val_str = ", ".join(map(str, val)) if val else "(empty)"
            else:
                val_str = str(val) if val is not None else "(empty)"
            lines.append(f"- **{prompt}** (`{qid}`, {q.get('type','text')}): {val_str}")
        lines.append("")

    if skipped:
        lines.append("## Skipped questions")
        for q in skipped:
            lines.append(f"- _{q.get('prompt') or q.get('id')}_ — `{q.get('id')}`")
        lines.append("")

    if annos:
        lines.append(f"## Annotations ({len(annos)})")
        for i, a in enumerate(annos, 1):
            body = ((a.get("body") or [{}])[0]).get("value", "")
            sel = (a.get("target") or {}).get("selector") or []
            kind = a.get("motivation", "commenting")
            quote = next((s for s in sel if s.get("type") == "TextQuoteSelector"), None)
            css = next((s for s in sel if s.get("type") == "CssSelector"), None)
            frag = next((s for s in sel if s.get("type") == "FragmentSelector"), None)
            svg = next((s for s in sel if s.get("type") == "SvgSelector"), None)

            if quote:
                anchor = f'text "{quote.get("exact","")[:120]}"'
            elif frag and css:
                anchor = f'pin on `{css.get("value","")}` at {frag.get("value","")}'
            elif svg:
                anchor = "free-form sketch (SVG path attached in envelope)"
            elif not sel:
                anchor = "general comment (no anchor)"
            else:
                anchor = "(unknown anchor)"

            lines.append(f"{i}. **[{kind}]** {anchor}")
            if body:
                lines.append(f"   → {body}")
            lines.append("")

    if not (action or answered or annos):
        lines += ["_(empty submission — nothing to act on)_", ""]

    lines += [
        "---",
        "Apply each form answer + comment as a concrete edit. For sketches without text, "
        "infer intent from the path location, restate what you understood, then apply. "
        "If a decision action was clicked, that's the user's authoritative call.",
    ]
    return "\n".join(lines)


def _is_answered(q: dict) -> bool:
    v = q.get("value")
    if isinstance(v, list):
        return len(v) > 0
    return v is not None and v != ""


class FeedbackHandler(http.server.BaseHTTPRequestHandler):
    server_version = "annotated-feedback/1.0"

    BASE_DIR: Path
    ARTIFACT: Path
    FEEDBACK_DIR: Path

    def _send(self, code: int, body: bytes, ctype: str = "text/html; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            if not self.ARTIFACT.exists():
                self._send(503, f"artifact not found: {self.ARTIFACT}".encode(), "text/plain; charset=utf-8")
                return
            self._send(200, self.ARTIFACT.read_bytes())
            return
        if self.path == "/health":
            self._send(200, b'{"ok":true}', "application/json")
            return
        if self.path == "/feedback":
            items = []
            for p in sorted(self.FEEDBACK_DIR.glob("*.json"), reverse=True)[:20]:
                try:
                    items.append({"file": p.name, "at": p.stat().st_mtime})
                except OSError:
                    pass
            self._send(200, json.dumps({"items": items}, indent=2).encode(), "application/json")
            return
        # Static fallback: serve any file under BASE_DIR (vendor/, images, etc.).
        # Block path traversal — reject any path component that is ".." or hidden.
        rel = self.path.lstrip("/")
        parts = rel.split("/") if rel else []
        if not rel or any(p in ("", "..", ".") or p.startswith(".") for p in parts):
            self._send(404, b"not found", "text/plain; charset=utf-8"); return
        candidate = self.BASE_DIR / rel
        try:
            resolved = candidate.resolve()
            if candidate.is_file() and resolved.is_relative_to(self.BASE_DIR.resolve()):
                self._send(200, candidate.read_bytes(), _ctype_for(candidate))
                return
        except (OSError, ValueError):
            pass
        self._send(404, b"not found", "text/plain; charset=utf-8")

    # ------------------------------------------------------------------
    # CSRF / DoS guards for POST /feedback
    # ------------------------------------------------------------------
    # The server binds to 127.0.0.1 — but any web page in the same browser
    # can still issue a "simple" cross-origin POST against localhost.
    # Without these checks, that page could write attacker-controlled
    # .prompt.md files that the next Claude turn reads as instructions
    # (prompt-injection via CSRF). Defenses:
    #   1. Require Content-Type: application/json (forces a CORS preflight
    #      for cross-origin POSTs, which we never answer → blocked. Simple
    #      cross-origin POSTs with text/plain are rejected here.)
    #   2. Require Origin to be null / http://127.0.0.1:<port> /
    #      http://localhost:<port> — same-origin only.
    #   3. Cap body size — runaway pages can't DoS our memory.
    MAX_BODY_BYTES = 5 * 1024 * 1024  # 5 MB

    def _allowed_origin(self) -> bool:
        origin = self.headers.get("Origin", "").strip().lower()
        if not origin or origin == "null":
            return True
        port = self.server.server_address[1]
        return origin in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def do_POST(self):
        if self.path != "/feedback":
            self._send(404, b"not found", "text/plain; charset=utf-8"); return
        ctype = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if ctype != "application/json":
            self._send(415, b"unsupported media type \xe2\x80\x94 application/json required", "text/plain; charset=utf-8"); return
        if not self._allowed_origin():
            self._send(403, b"forbidden \xe2\x80\x94 origin mismatch", "text/plain; charset=utf-8"); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, b"bad Content-Length", "text/plain; charset=utf-8"); return
        if length <= 0 or length > self.MAX_BODY_BYTES:
            self._send(413, b"payload too large or empty", "text/plain; charset=utf-8"); return
        body = self.rfile.read(length).decode("utf-8")
        try:
            env = json.loads(body)
        except json.JSONDecodeError as e:
            self._send(400, f"bad json: {e}".encode(), "text/plain; charset=utf-8"); return

        sub_id = uuid.uuid4().hex[:12]
        ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
        title = (env.get("document", {}).get("title") or "feedback").strip()
        slug = "".join(c if c.isalnum() else "_" for c in title)[:50] or "feedback"
        json_path = self.FEEDBACK_DIR / f"{ts}__{slug}__{sub_id}.json"
        prompt_path = json_path.with_suffix(".prompt.md")

        payload = {"_received_at": datetime.now(timezone.utc).isoformat(), "_id": sub_id, **env}
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        prompt_path.write_text(render_prompt(env), encoding="utf-8")

        sys.stderr.write(f"[feedback] {sub_id} → {json_path.name}\n")
        sys.stderr.flush()

        self._send(
            200,
            json.dumps({
                "id": sub_id,
                "path": str(json_path),
                "prompt_path": str(prompt_path),
                "form_answered": sum(1 for q in env.get("form_responses", []) if _is_answered(q)),
                "annotations": len(env.get("annotations") or []),
                "action": env.get("action"),
            }, indent=2).encode(),
            "application/json",
        )

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")


def _ctype_for(p: Path) -> str:
    ext = p.suffix.lower()
    return {
        ".html": "text/html; charset=utf-8",
        ".css":  "text/css; charset=utf-8",
        ".js":   "application/javascript; charset=utf-8",
        ".mjs":  "application/javascript; charset=utf-8",
        ".json": "application/json",
        ".svg":  "image/svg+xml",
        ".png":  "image/png",
        ".jpg":  "image/jpeg", ".jpeg": "image/jpeg",
        ".gif":  "image/gif",
        ".txt":  "text/plain; charset=utf-8",
        ".md":   "text/markdown; charset=utf-8",
    }.get(ext, "application/octet-stream")


def main() -> int:
    ap = argparse.ArgumentParser(description="annotated-feedback HTTP server")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--artifact", default=DEFAULT_ARTIFACT, help="HTML file served at /")
    ap.add_argument("--dir", default=".", help="working directory (defaults to script dir)")
    args = ap.parse_args()

    base = Path(args.dir).resolve()
    artifact = (base / args.artifact).resolve()
    feedback_dir = base / "feedback"
    feedback_dir.mkdir(exist_ok=True)

    FeedbackHandler.BASE_DIR = base
    FeedbackHandler.ARTIFACT = artifact
    FeedbackHandler.FEEDBACK_DIR = feedback_dir

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True  # avoid "Address already in use" on quick restarts

    with ReusableTCPServer(("127.0.0.1", args.port), FeedbackHandler) as httpd:
        print(f"serving {artifact} on http://127.0.0.1:{args.port}/")
        print(f"feedback lands in {feedback_dir}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nbye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
