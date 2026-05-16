#!/usr/bin/env python3
"""Scaffold a three-tier Claude Code subagent.

Creates:
    <target>/.claude/agents/<name>.md
    <target>/.claude/agent-memory/<name>/MEMORY.md
    <target>/.agents/<name>/memory/{PRIVACY,INDEX}.md
    <target>/.agents/<name>/memory/_shared/.gitkeep
    <target>/.agents/<name>/tasks/open-tasks.md
    <target>/.agents/<name>/{sessions,cache,output}/.gitkeep

Templates live under `../templates/` relative to this script.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Mapping

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SCRIPT_DIR.parent / "templates"

KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def kebab_to_title(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def render(template_name: str, vars: Mapping[str, str]) -> str:
    body = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    for key, value in vars.items():
        body = body.replace("{{" + key + "}}", value)
    return body


def build_description(role: str, triggers: str, anti_triggers: str) -> str:
    parts = [role.rstrip(".") + "."]
    if triggers:
        kws = ", ".join(t.strip() for t in triggers.split(",") if t.strip())
        if kws:
            parts.append(f"Triggers on: {kws}.")
    if anti_triggers:
        anti = ", ".join(t.strip() for t in anti_triggers.split(",") if t.strip())
        if anti:
            parts.append(f"Do NOT trigger for: {anti}.")
    return " ".join(parts)


def write_file(path: Path, body: str, force: bool) -> str:
    if path.exists() and not force:
        return f"EXISTS  {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return f"WROTE   {path}"


def write_keep(directory: Path, force: bool) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    keep = directory / ".gitkeep"
    if keep.exists() and not force:
        return f"EXISTS  {keep}"
    keep.write_text("", encoding="utf-8")
    return f"WROTE   {keep}"


def install_hooks(target: Path, name: str, vars: Mapping[str, str],
                  force: bool) -> list[str]:
    """Install hook scripts + merge entries into .claude/settings.json."""
    results: list[str] = []
    hook_dir = target / ".claude" / "hooks" / name
    hook_dir.mkdir(parents=True, exist_ok=True)

    for tmpl, mode_exec in (
        ("snapshot-memory.sh.tmpl", True),
        ("curate-memory.sh.tmpl",  True),
        ("load-curated.sh.tmpl",   True),
    ):
        out_name = tmpl.replace(".tmpl", "")
        out = hook_dir / out_name
        if out.exists() and not force:
            results.append(f"EXISTS  {out}")
            continue
        body = render(f"hooks/{tmpl}", vars)
        out.write_text(body, encoding="utf-8")
        if mode_exec:
            out.chmod(0o755)
        results.append(f"WROTE   {out}")

    # Merge entries into .claude/settings.json. Keep additive — never delete
    # existing hooks the user already set up.
    settings_path = target / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) \
        if settings_path.exists() else {}
    hooks = settings.setdefault("hooks", {})

    def hook_entry(matcher: str, script: str) -> dict:
        cmd = str((hook_dir / script).resolve())
        entry = {"hooks": [{"type": "command", "command": cmd}]}
        if matcher:
            entry["matcher"] = matcher
        return entry

    def merge_hook(event: str, matcher: str, script: str) -> bool:
        cmd_str = str((hook_dir / script).resolve())
        existing = hooks.setdefault(event, [])
        for e in existing:
            for h in e.get("hooks", []):
                if h.get("command") == cmd_str:
                    return False  # already registered
        existing.append(hook_entry(matcher, script))
        return True

    added = []
    if merge_hook("PreCompact",   "auto|manual",          "snapshot-memory.sh"):
        added.append("PreCompact")
    if merge_hook("SessionEnd",   "",                     "curate-memory.sh"):
        added.append("SessionEnd")
    if merge_hook("SessionStart", "startup|resume|compact", "load-curated.sh"):
        added.append("SessionStart")

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n",
                             encoding="utf-8")
    if added:
        results.append(f"MERGED  {settings_path}  (+{', '.join(added)})")
    else:
        results.append(f"NOOP    {settings_path}  (hooks already registered)")
    return results


def existing_tiers(target: Path, name: str) -> list[Path]:
    candidates = [
        target / ".claude" / "agents" / f"{name}.md",
        target / ".claude" / "agent-memory" / name / "MEMORY.md",
        target / ".agents" / name,
    ]
    return [c for c in candidates if c.exists()]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Scaffold a three-tier Claude Code subagent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  create_agent.py --name code-reviewer \\\n"
            "    --role 'Reviews PRs for correctness, security, and style' \\\n"
            "    --target ~/projects/my-vault"
        ),
    )
    p.add_argument("--name", required=True,
                   help="kebab-case agent name (used in all three tiers)")
    p.add_argument("--role", required=True,
                   help="one-line purpose; goes into the description and identity blocks")
    p.add_argument("--target", default=".",
                   help="directory under which .claude/ and .agents/ will be created (default: cwd)")
    p.add_argument("--anchor", default="",
                   help="optional anchor phrase (e.g. 'Signal, not noise.')")
    p.add_argument("--voice", default="",
                   help="optional one-line voice notes (e.g. 'calm, dry, no emojis')")
    p.add_argument("--triggers", default="",
                   help="comma-separated trigger keywords for the description")
    p.add_argument("--anti-triggers", dest="anti_triggers", default="",
                   help="comma-separated 'do NOT trigger for' topics")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing files (default: refuse if any tier exists)")
    p.add_argument("--with-hooks", action="store_true",
                   help="also install PreCompact/SessionEnd/SessionStart hook scripts "
                        "+ merge into .claude/settings.json under the target dir")
    args = p.parse_args(argv)

    if not KEBAB_RE.match(args.name):
        print(f"error: --name must be kebab-case (got {args.name!r}). "
              f"Use lowercase letters, digits, and hyphens; start with a letter.",
              file=sys.stderr)
        return 2

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        print(f"error: --target {target} does not exist", file=sys.stderr)
        return 2

    collisions = existing_tiers(target, args.name)
    if collisions and not args.force:
        print(f"error: refusing to overwrite existing tier(s) for "
              f"{args.name!r}:", file=sys.stderr)
        for c in collisions:
            print(f"  - {c}", file=sys.stderr)
        print("re-run with --force to overwrite, or pick a different --name.",
              file=sys.stderr)
        return 1

    vars: Mapping[str, str] = {
        "NAME": args.name,
        "NAME_TITLE": kebab_to_title(args.name),
        "ROLE": args.role.strip(),
        "DESCRIPTION": build_description(args.role, args.triggers, args.anti_triggers),
        "ANCHOR": args.anchor.strip() or "TODO — add an anchor phrase",
        "VOICE": args.voice.strip() or "TODO — define the agent's voice in one line",
    }

    results: list[str] = []

    # Tier 1
    tier1 = target / ".claude" / "agents" / f"{args.name}.md"
    results.append(write_file(tier1, render("tier1_definition.md.tmpl", vars), args.force))

    # Tier 2
    tier2 = target / ".claude" / "agent-memory" / args.name / "MEMORY.md"
    results.append(write_file(tier2, render("tier2_memory_index.md.tmpl", vars), args.force))

    # Tier 3 — memory
    base3 = target / ".agents" / args.name
    results.append(write_file(base3 / "memory" / "PRIVACY.md",
                              render("tier3_privacy.md.tmpl", vars), args.force))
    results.append(write_file(base3 / "memory" / "critical_facts.md",
                              render("tier3_critical_facts.md.tmpl", vars), args.force))
    results.append(write_file(base3 / "memory" / "INDEX.md",
                              render("tier3_index.md.tmpl", vars), args.force))
    results.append(write_file(base3 / "memory" / "what-works.md",
                              render("tier3_what_works.md.tmpl", vars), args.force))
    results.append(write_file(base3 / "memory" / "failures.md",
                              render("tier3_failures.md.tmpl", vars), args.force))
    results.append(write_file(base3 / "memory" / "decisions.md",
                              render("tier3_decisions.md.tmpl", vars), args.force))
    results.append(write_file(base3 / "memory" / "DREAMS.md",
                              render("tier3_dreams.md.tmpl", vars), args.force))
    results.append(write_keep(base3 / "memory" / "_shared", args.force))

    # Tier 3 — tasks + log + dirs
    results.append(write_file(base3 / "tasks" / "open-tasks.md",
                              render("tier3_open_tasks.md.tmpl", vars), args.force))
    results.append(write_file(base3 / "log.md",
                              render("tier3_log.md.tmpl", vars), args.force))
    for sub in ("sessions", "cache", "output"):
        results.append(write_keep(base3 / sub, args.force))

    # Optional hooks
    if args.with_hooks:
        results.extend(install_hooks(target, args.name, vars, args.force))

    for line in results:
        print(line)

    print()
    print(f"Scaffolded agent {args.name!r} at {target}.")
    print("Next steps:")
    print(f"  1. Edit {tier1.relative_to(target)} — persona, triggers, boundaries.")
    print(f"  2. Edit {tier2.relative_to(target)} — sanity-check boot sequence + named blocks.")
    print(f"  3. Edit {(base3 / 'memory' / 'PRIVACY.md').relative_to(target)} — set posture.")
    print(f"  4. Edit {(base3 / 'memory' / 'critical_facts.md').relative_to(target)} — ≤200-tok distillation.")
    print(f"  5. Run `mh:agent:audit` against {args.name!r} once customized.")
    print(f"  6. Run `mh:agent:dream --name {args.name}` periodically (weekly is a reasonable default) to consolidate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
