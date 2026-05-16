#!/usr/bin/env python3
"""Prepare a dream pass — snapshot the deep store + emit an inventory JSON.

For a given agent:
  1. Copies the current memory/ + log.md to .agents/<name>/cache/snapshots/dream-<stamp>/
  2. Scans each append-only log file, parses entries by `## <slug>` headings,
     extracts YAML frontmatter (importance, captured, tags, etc.)
  3. Identifies candidate duplicate pairs (slug token-overlap >= 0.5)
  4. Prints JSON to stdout — fed to the next Claude turn for per-entry decisions
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

ENTRY_HEAD = re.compile(r"^##\s+(.+)$", re.MULTILINE)
YAML_BLOCK = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def kebab_tokens(slug: str) -> set[str]:
    return {t for t in re.split(r"[-_\s]+", slug.lower()) if len(t) >= 3}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def parse_entries(text: str) -> list[dict]:
    """Split a log file into entries keyed by `## slug` headings."""
    # Strip comment blocks AND fenced code blocks — example entries inside
    # those should not be counted as real entries.
    active = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    active = re.sub(r"^```.*?^```", "", active, flags=re.DOTALL | re.MULTILINE)
    lines = active.splitlines(keepends=True)
    entries: list[dict] = []
    current: dict | None = None
    buf: list[str] = []
    for line in lines:
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and not m.group(1).startswith("[20"):  # don't grab `## [YYYY-MM-DD]`
            if current is not None:
                current["body"] = "".join(buf).strip()
                entries.append(current)
            current = {"slug": m.group(1).strip(), "yaml": {}, "body": ""}
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        current["body"] = "".join(buf).strip()
        entries.append(current)

    for e in entries:
        ym = YAML_BLOCK.search(e["body"])
        if ym:
            for raw in ym.group(1).splitlines():
                if ":" in raw:
                    k, _, v = raw.partition(":")
                    e["yaml"][k.strip()] = v.strip()
    return entries


def importance_int(yaml: dict) -> int | None:
    v = yaml.get("importance")
    if not v:
        return None
    try:
        return int(re.search(r"\d+", v).group(0))
    except (AttributeError, ValueError):
        return None


def captured_date(yaml: dict) -> str | None:
    v = yaml.get("captured")
    if not v:
        return None
    m = re.search(r"\d{4}-\d{2}-\d{2}", v)
    return m.group(0) if m else None


def find_logs(store: Path) -> list[Path]:
    """All append-only logs: memory/<file>.md + memory/<subject>/<file>.md."""
    out: list[Path] = []
    memory = store / "memory"
    if not memory.exists():
        return out
    targets = ("what-works.md", "what-doesnt.md", "decisions.md", "failures.md")
    for t in targets:
        p = memory / t
        if p.exists():
            out.append(p)
    for sub in memory.iterdir():
        if sub.is_dir() and sub.name not in ("_shared",):
            for t in targets:
                p = sub / t
                if p.exists():
                    out.append(p)
    return out


def snapshot(store: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    snap = store / "cache" / "snapshots" / f"dream-{stamp}"
    snap.mkdir(parents=True, exist_ok=True)
    memory = store / "memory"
    if memory.exists():
        shutil.copytree(memory, snap / "memory")
    log = store / "log.md"
    if log.exists():
        shutil.copy2(log, snap / "log.md")
    return snap


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Prepare an agent dream-pass inventory.")
    p.add_argument("--name", required=True, help="agent name")
    p.add_argument("--target", default=".", help="vault root (contains .agents/)")
    p.add_argument("--no-snapshot", action="store_true",
                   help="skip snapshot creation (for dry-run inventory)")
    args = p.parse_args(argv)

    target = Path(args.target).expanduser().resolve()
    store = target / ".agents" / args.name
    if not store.exists():
        print(f"error: no store at {store}", file=sys.stderr)
        return 1

    snap = None if args.no_snapshot else snapshot(store)

    files: list[dict] = []
    all_entries: list[dict] = []
    for f in find_logs(store):
        text = f.read_text(encoding="utf-8", errors="replace")
        entries = parse_entries(text)
        for e in entries:
            e["file"] = str(f.relative_to(target))
        # importance histogram
        scores = [importance_int(e["yaml"]) for e in entries]
        scored = [s for s in scores if s is not None]
        hist: dict[int, int] = {}
        for s in scored:
            hist[s] = hist.get(s, 0) + 1
        files.append({
            "file": str(f.relative_to(target)),
            "entries": len(entries),
            "scored": len(scored),
            "unscored": len(entries) - len(scored),
            "importance_histogram": hist,
            "lines": text.count("\n"),
            "words": len(re.findall(r"\S+", text)),
            "mtime": f.stat().st_mtime,
        })
        all_entries.extend(entries)

    # Duplicate candidates — across all entries, by slug token overlap
    dupes: list[dict] = []
    for i in range(len(all_entries)):
        a = all_entries[i]
        ta = kebab_tokens(a["slug"])
        for j in range(i + 1, len(all_entries)):
            b = all_entries[j]
            tb = kebab_tokens(b["slug"])
            score = jaccard(ta, tb)
            if score >= 0.5:
                dupes.append({
                    "a": {"file": a["file"], "slug": a["slug"]},
                    "b": {"file": b["file"], "slug": b["slug"]},
                    "slug_overlap": round(score, 2),
                })

    payload = {
        "agent": args.name,
        "target": str(target),
        "snapshot": str(snap) if snap else None,
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "files": files,
        "totals": {
            "files": len(files),
            "entries": sum(f["entries"] for f in files),
            "scored": sum(f["scored"] for f in files),
            "duplicate_candidates": len(dupes),
        },
        "duplicate_candidates": dupes,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
