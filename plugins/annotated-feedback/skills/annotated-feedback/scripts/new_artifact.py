#!/usr/bin/env python3
"""One-shot scaffold for an annotated-feedback artifact.

Usage:
    python3 new_artifact.py <output_dir> [--title "Some title"] [--kicker "Section · Project"] [--deck "One-sentence dek."]

Creates <output_dir>, copies template.html → index.html and server.py alongside,
and substitutes {{TITLE}} / {{KICKER}} / {{DECK}} placeholders if provided.

After this, the parent agent should:
  1. Edit <output_dir>/index.html — fill in the body, embed .af-q blocks
  2. Run:   python3 server.py --port 8765 --artifact index.html  (in background)
  3. Open:  http://127.0.0.1:8765/
  4. Wait for new files in <output_dir>/feedback/
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "template.html"
SERVER = SKILL_DIR / "assets" / "server.py"
VENDOR = SKILL_DIR / "assets" / "vendor"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("output_dir")
    ap.add_argument("--title", default="Untitled artifact")
    ap.add_argument("--kicker", default="Artifact")
    ap.add_argument("--deck", default="One-line description of what this artifact is for.")
    args = ap.parse_args()

    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "feedback").mkdir(exist_ok=True)

    if not TEMPLATE.exists():
        print(f"ERROR: template.html missing at {TEMPLATE}", file=sys.stderr)
        return 1
    if not SERVER.exists():
        print(f"ERROR: server.py missing at {SERVER}", file=sys.stderr)
        return 1

    html = TEMPLATE.read_text(encoding="utf-8")
    html = (
        html.replace("{{TITLE}}", args.title)
            .replace("{{KICKER}}", args.kicker)
            .replace("{{DECK}}", args.deck)
    )
    (out / "index.html").write_text(html, encoding="utf-8")
    shutil.copy2(SERVER, out / "server.py")

    # Copy vendored JS (perfect-freehand + mermaid) so the artifact has zero
    # network dependencies at runtime — same versions every time.
    vendor_dst = out / "vendor"
    if vendor_dst.exists():
        shutil.rmtree(vendor_dst)
    if VENDOR.exists():
        shutil.copytree(VENDOR, vendor_dst)

    print(f"scaffolded annotated-feedback artifact at: {out}")
    print(f"  - {out / 'index.html'}   (edit this, embed .af-q blocks)")
    print(f"  - {out / 'server.py'}    (run: python3 server.py --port 8765)")
    print(f"  - {out / 'vendor/'}      (vendored perfect-freehand + mermaid)")
    print(f"  - {out / 'feedback/'}    (submissions land here)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
