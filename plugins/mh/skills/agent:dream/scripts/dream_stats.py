#!/usr/bin/env python3
"""Stats report for an agent dream pass — diffs a snapshot vs the current state.

Run AFTER the consolidation mutations. Compares the snapshot directory created
by `dream_prep.py` to the now-mutated `.agents/<name>/memory/`. Reports:
  - entry counts before/after per file (total, dropped, merged, added)
  - line counts and avg importance
  - top changes by importance delta

Output is paste-ready markdown by default; `--format json` for piping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

# Re-use the parser from the prep script via duplication (keep scripts independent).
ENTRY_HEAD = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
YAML_BLOCK = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def parse_entries(text: str) -> dict[str, dict]:
    """Return {slug: {yaml, body}} for entries with `## slug` (skip dated `## [20…]`)."""
    active = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    active = re.sub(r"^```.*?^```", "", active, flags=re.DOTALL | re.MULTILINE)
    lines = active.splitlines(keepends=True)
    out: dict[str, dict] = {}
    slug: str | None = None
    buf: list[str] = []
    for line in lines:
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and not m.group(1).startswith("[20"):
            if slug is not None:
                out[slug] = _entry("".join(buf))
            slug = m.group(1).strip()
            buf = []
        elif slug is not None:
            buf.append(line)
    if slug is not None:
        out[slug] = _entry("".join(buf))
    return out


def _entry(body: str) -> dict:
    yaml: dict[str, str] = {}
    ym = YAML_BLOCK.search(body)
    if ym:
        for raw in ym.group(1).splitlines():
            if ":" in raw:
                k, _, v = raw.partition(":")
                yaml[k.strip()] = v.strip()
    return {"yaml": yaml, "body": body.strip()}


def importance_int(yaml: dict) -> int | None:
    v = yaml.get("importance")
    if not v:
        return None
    try:
        return int(re.search(r"\d+", v).group(0))
    except (AttributeError, ValueError):
        return None


def file_summary(text: str) -> dict:
    entries = parse_entries(text)
    scored = [importance_int(e["yaml"]) for e in entries.values()]
    scored = [s for s in scored if s is not None]
    return {
        "entries": len(entries),
        "lines": text.count("\n"),
        "words": len(re.findall(r"\S+", text)),
        "scored": len(scored),
        "avg_importance": round(sum(scored) / len(scored), 2) if scored else None,
        "slugs": list(entries.keys()),
        "by_slug": entries,
    }


def find_pair(target: Path, snap: Path, name: str) -> list[tuple[Path, Path]]:
    """For each memory log file present in either side, return (before, after)."""
    store = target / ".agents" / name
    memory = store / "memory"
    snap_memory = snap / "memory"
    pairs: list[tuple[Path, Path]] = []
    seen: set[str] = set()
    targets = ("what-works.md", "what-doesnt.md", "decisions.md", "failures.md")
    for root in (memory, snap_memory):
        if not root.exists():
            continue
        for t in targets:
            for p in root.rglob(t):
                rel = p.relative_to(root)
                if str(rel) in seen:
                    continue
                seen.add(str(rel))
                pairs.append((snap_memory / rel, memory / rel))
    return pairs


def diff_pair(before: Path, after: Path) -> dict:
    b = file_summary(before.read_text(encoding="utf-8", errors="replace")) \
        if before.exists() else file_summary("")
    a = file_summary(after.read_text(encoding="utf-8", errors="replace")) \
        if after.exists() else file_summary("")
    bset = set(b["slugs"])
    aset = set(a["slugs"])
    dropped = sorted(bset - aset)
    added = sorted(aset - bset)
    kept = sorted(bset & aset)
    rescored: list[dict] = []
    for slug in kept:
        bi = importance_int(b["by_slug"][slug]["yaml"])
        ai = importance_int(a["by_slug"][slug]["yaml"])
        if bi != ai and bi is not None and ai is not None:
            rescored.append({"slug": slug, "before": bi, "after": ai, "delta": ai - bi})
    rescored.sort(key=lambda r: abs(r["delta"]), reverse=True)
    return {
        "file": str(after),
        "before": {k: v for k, v in b.items() if k not in ("slugs", "by_slug")},
        "after":  {k: v for k, v in a.items() if k not in ("slugs", "by_slug")},
        "dropped": dropped,
        "added": added,
        "rescored": rescored,
    }


def render_markdown(name: str, diffs: list[dict]) -> str:
    out = [f"# Dream stats — `{name}`",
           f"_{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}_", ""]
    total_b = sum(d["before"]["entries"] for d in diffs)
    total_a = sum(d["after"]["entries"]  for d in diffs)
    drops = sum(len(d["dropped"]) for d in diffs)
    adds  = sum(len(d["added"]) for d in diffs)
    rescore_count = sum(len(d["rescored"]) for d in diffs)
    out.append(f"**Summary:** {total_b} → {total_a} entries "
               f"({total_a - total_b:+d}). Dropped {drops}, added {adds}, "
               f"rescored {rescore_count}.")
    out.append("")
    for d in diffs:
        rel = Path(d["file"]).name
        bi = d["before"]; ai = d["after"]
        out.append(f"## `{rel}`")
        out.append("")
        out.append(f"- entries: {bi['entries']} → {ai['entries']} ({ai['entries'] - bi['entries']:+d})")
        out.append(f"- lines: {bi['lines']} → {ai['lines']} ({ai['lines'] - bi['lines']:+d})")
        if bi.get("avg_importance") is not None and ai.get("avg_importance") is not None:
            delta = round(ai["avg_importance"] - bi["avg_importance"], 2)
            out.append(f"- avg importance: {bi['avg_importance']} → {ai['avg_importance']} ({delta:+.2f})")
        if d["dropped"]:
            out.append("- **dropped:**")
            for s in d["dropped"]:
                out.append(f"  - `{s}`")
        if d["added"]:
            out.append("- **added / merged-into:**")
            for s in d["added"]:
                out.append(f"  - `{s}`")
        if d["rescored"]:
            out.append("- **rescored:**")
            for r in d["rescored"][:10]:
                out.append(f"  - `{r['slug']}` — {r['before']} → {r['after']} ({r['delta']:+d})")
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Dream pass stats — before vs after.")
    p.add_argument("--name", required=True, help="agent name")
    p.add_argument("--target", default=".", help="vault root")
    p.add_argument("--snapshot", required=True,
                   help="snapshot dir from dream_prep.py (.agents/<name>/cache/snapshots/dream-<stamp>)")
    p.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = p.parse_args(argv)

    target = Path(args.target).expanduser().resolve()
    snap = Path(args.snapshot).expanduser().resolve()
    if not snap.exists():
        print(f"error: snapshot {snap} does not exist", file=sys.stderr)
        return 2

    pairs = find_pair(target, snap, args.name)
    diffs = [diff_pair(b, a) for b, a in pairs]

    if args.format == "json":
        print(json.dumps({"agent": args.name, "diffs": diffs}, indent=2))
    else:
        print(render_markdown(args.name, diffs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
