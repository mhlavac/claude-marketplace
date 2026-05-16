#!/usr/bin/env python3
"""Static lint for three-tier Claude Code subagents.

Walks a target directory's `.claude/agents/`, `.claude/agent-memory/`, and
`.agents/` trees and reports on the structure of each agent. Reports PASS,
WARN, FAIL, or INFO per check, with a short reason and where useful a one-line
suggested fix.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"
SEVERITY_RANK = {FAIL: 0, WARN: 1, INFO: 2, PASS: 3}

# v1.2.0 expected file manifest — used by drift/apply modes.
# Each tuple: (dest path relative to target/ for an agent named X,
#              template filename under agent:create/templates/, "required"|"recommended")
# `{name}` is substituted with the agent name at runtime.
TEMPLATE_MANIFEST: list[tuple[str, str, str]] = [
    (".agents/{name}/memory/PRIVACY.md",         "tier3_privacy.md.tmpl",         "required"),
    (".agents/{name}/memory/critical_facts.md",  "tier3_critical_facts.md.tmpl",  "required"),
    (".agents/{name}/memory/INDEX.md",           "tier3_index.md.tmpl",           "required"),
    (".agents/{name}/memory/what-works.md",      "tier3_what_works.md.tmpl",      "recommended"),
    (".agents/{name}/memory/failures.md",        "tier3_failures.md.tmpl",        "recommended"),
    (".agents/{name}/memory/decisions.md",       "tier3_decisions.md.tmpl",       "recommended"),
    (".agents/{name}/memory/DREAMS.md",          "tier3_dreams.md.tmpl",          "recommended"),
    (".agents/{name}/tasks/open-tasks.md",       "tier3_open_tasks.md.tmpl",      "recommended"),
    (".agents/{name}/log.md",                    "tier3_log.md.tmpl",             "recommended"),
]


@dataclass
class Check:
    tier: str
    name: str
    result: str
    detail: str = ""
    fix: str = ""


@dataclass
class AgentReport:
    name: str
    checks: list[Check] = field(default_factory=list)

    def add(self, *args, **kwargs) -> None:
        self.checks.append(Check(*args, **kwargs))

    @property
    def worst(self) -> str:
        return min((c.result for c in self.checks),
                   key=lambda r: SEVERITY_RANK.get(r, 99), default=PASS)

    def count(self, result: str) -> int:
        return sum(1 for c in self.checks if c.result == result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

YAML_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
BOOT_LINE_RE = re.compile(r"^\s*\d+\.\s+(?:`([^`]+)`|([^\s].*))", re.MULTILINE)
TODO_RE = re.compile(r"<!--\s*TODO", re.IGNORECASE)
BOOT_HEADING_RE = re.compile(r"^#{1,6}\s+(.*boot.*)$",
                             re.IGNORECASE | re.MULTILINE)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Tiny YAML subset parser — flat key: value pairs only."""
    m = YAML_FRONTMATTER_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    out: dict[str, str] = {}
    current_key: str | None = None
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            out[current_key] = (out[current_key] + "\n" + line.strip()).strip()
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            current_key = key.strip()
            out[current_key] = value.strip().strip("|>").strip()
    return out


def extract_boot_paths(text: str) -> list[str]:
    """Extract path-looking entries from the numbered list under a Boot heading.

    Looks for a heading matching /boot/i (e.g. `## Boot sequence`) and captures
    numbered list items until the next heading. Falls back to the first
    numbered list if no boot heading is found.
    """
    headings = list(BOOT_HEADING_RE.finditer(text))
    if headings:
        start = headings[0].end()
        next_heading = re.search(r"^#{1,6}\s+", text[start:], re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(text)
        scope = text[start:end]
    else:
        scope = text

    paths: list[str] = []
    for m in BOOT_LINE_RE.finditer(scope):
        candidate = (m.group(1) or m.group(2) or "").strip()
        if not candidate:
            continue
        candidate = candidate.split(" — ", 1)[0].strip().rstrip(".").strip("`'\"")
        if "/" in candidate or candidate.endswith(".md"):
            paths.append(candidate)
    return paths


def has_section(text: str, *patterns: str) -> bool:
    body = text.lower()
    return any(p.lower() in body for p in patterns)


def file_line_count(p: Path) -> int:
    try:
        return sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def audit_tier1(rep: AgentReport, definition: Path) -> dict[str, str]:
    """Returns the parsed frontmatter for downstream cross-tier checks."""
    if not definition.exists():
        rep.add("tier1", "definition_file", FAIL,
                f"Missing definition file {definition}",
                "Run `mh:agent:create` or create the file by hand.")
        return {}

    text = definition.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)

    if not fm:
        rep.add("tier1", "yaml_frontmatter", FAIL,
                "No YAML frontmatter found",
                "Wrap the header with `---` lines and add `name`, `description`, `model`.")
        return fm

    rep.add("tier1", "yaml_frontmatter", PASS)

    expected_name = definition.stem
    if fm.get("name") == expected_name:
        rep.add("tier1", "name_matches_filename", PASS)
    else:
        rep.add("tier1", "name_matches_filename", FAIL,
                f"name={fm.get('name')!r} but file is {expected_name}.md",
                f"Set `name: {expected_name}` or rename the file.")

    desc = fm.get("description", "")
    if len(desc) >= 100:
        rep.add("tier1", "description_length", PASS, f"{len(desc)} chars")
    else:
        rep.add("tier1", "description_length", WARN,
                f"description is only {len(desc)} chars",
                "Expand the description — the harness matches on it.")

    desc_l = desc.lower()
    if any(t in desc_l for t in ("trigger", "use when", "use this", "when the user", "auto-trigger")):
        rep.add("tier1", "positive_triggers", PASS)
    else:
        rep.add("tier1", "positive_triggers", WARN,
                "no explicit trigger keywords / 'use when' clauses found",
                "Add a 'Use when …' / 'Triggers on …' sentence to the description.")

    if any(t in desc_l for t in ("do not trigger", "skip when", "skip for", "not for", "avoid for")):
        rep.add("tier1", "anti_triggers", PASS)
    else:
        rep.add("tier1", "anti_triggers", WARN,
                "no 'do NOT trigger for' / 'skip when' clause found",
                "Add an anti-trigger clause to prevent over-spawning.")

    if has_section(text, "## persona", "## identity", "## voice"):
        rep.add("tier1", "persona_section", PASS)
    else:
        rep.add("tier1", "persona_section", WARN,
                "no '## Persona' / '## Identity' / '## Voice' heading",
                "Add a Persona section with the agent's voice + anchor.")

    boot_paths = extract_boot_paths(text)
    if boot_paths:
        rep.add("tier1", "boot_sequence", PASS,
                f"{len(boot_paths)} entries")
    else:
        rep.add("tier1", "boot_sequence", FAIL,
                "no numbered boot sequence found",
                "Add `## Boot sequence` with a numbered list of files to read in order.")

    if has_section(text, "self-curation", "before i sign off", "what-works"):
        rep.add("tier1", "self_curation", PASS)
    else:
        rep.add("tier1", "self_curation", WARN,
                "no self-curation section found",
                "Add a 'Self-curation — every session before I sign off' section.")

    if TODO_RE.search(text):
        rep.add("tier1", "todo_markers", WARN,
                "definition still contains `<!-- TODO -->` markers",
                "Fill in the placeholders from the scaffold.")
    else:
        rep.add("tier1", "todo_markers", PASS)

    return fm


def audit_tier2(rep: AgentReport, mem_index: Path, target: Path) -> list[str]:
    """Returns the boot-sequence paths the index references (for cross-tier checks)."""
    if not mem_index.exists():
        rep.add("tier2", "memory_index_file", FAIL,
                f"Missing memory index {mem_index}",
                "Create the auto-injected MEMORY.md (see `mh:agent:create`).")
        return []

    rep.add("tier2", "memory_index_file", PASS)

    lines = file_line_count(mem_index)
    if lines <= 80:
        rep.add("tier2", "memory_index_size", PASS, f"{lines} lines")
    else:
        rep.add("tier2", "memory_index_size", WARN,
                f"{lines} lines — over the 80-line budget",
                "Move detail into `memory/INDEX.md` and topic files.")

    text = mem_index.read_text(encoding="utf-8", errors="replace")
    boot_paths = extract_boot_paths(text)
    if boot_paths:
        rep.add("tier2", "boot_sequence_present", PASS,
                f"{len(boot_paths)} entries")
    else:
        rep.add("tier2", "boot_sequence_present", WARN,
                "no numbered boot sequence found",
                "Add a numbered boot sequence to the index.")

    missing: list[str] = []
    for p in boot_paths:
        if p.startswith("<!--") or "TODO" in p or "<" in p or "*" in p:
            continue  # template placeholder or glob, not a literal path
        full = (target / p) if not Path(p).is_absolute() else Path(p)
        if not full.exists():
            missing.append(p)
    if boot_paths:
        if missing:
            rep.add("tier2", "boot_paths_resolve", WARN,
                    f"{len(missing)} boot path(s) missing on disk: " + ", ".join(missing[:3]) + ("…" if len(missing) > 3 else ""),
                    "Update the boot sequence or create the referenced files.")
        else:
            rep.add("tier2", "boot_paths_resolve", PASS)

    if re.search(r"^I'm \*\*", text, re.MULTILINE) or re.search(r"^I am \*\*", text, re.MULTILINE):
        rep.add("tier2", "identity_one_liner", PASS)
    else:
        rep.add("tier2", "identity_one_liner", WARN,
                "no `I'm **X** — …` identity opener found",
                "Add a one-line identity statement at the top of MEMORY.md.")

    return boot_paths


def audit_tier3(rep: AgentReport, store: Path) -> None:
    if not store.exists():
        rep.add("tier3", "store_dir", FAIL,
                f"Missing deep store {store}",
                "Run `mh:agent:create` or create `.agents/<name>/` by hand.")
        return

    rep.add("tier3", "store_dir", PASS)

    privacy = store / "memory" / "PRIVACY.md"
    if privacy.exists():
        rep.add("tier3", "privacy_md", PASS)
    else:
        rep.add("tier3", "privacy_md", FAIL,
                "memory/PRIVACY.md is missing",
                "Create memory/PRIVACY.md — privacy posture must be loadable.")

    index = store / "memory" / "INDEX.md"
    rep.add("tier3", "memory_index_md", PASS if index.exists() else WARN,
            "" if index.exists() else "memory/INDEX.md is missing",
            "" if index.exists() else "Create memory/INDEX.md as a pointer file.")

    tasks = store / "tasks" / "open-tasks.md"
    rep.add("tier3", "open_tasks", PASS if tasks.exists() else WARN,
            "" if tasks.exists() else "tasks/open-tasks.md is missing",
            "" if tasks.exists() else "Create tasks/open-tasks.md for the agent's own backlog.")

    sessions = store / "sessions"
    if sessions.exists() and sessions.is_dir():
        rep.add("tier3", "sessions_dir", PASS)
        logs = sorted(p for p in sessions.glob("*.md")
                      if p.name not in (".gitkeep",))
        if not logs:
            rep.add("tier3", "recent_session_log", INFO,
                    "no session logs yet (new agent?)",
                    "")
        else:
            newest_mtime = max(p.stat().st_mtime for p in logs)
            age_days = (dt.datetime.now().timestamp() - newest_mtime) / 86400
            if age_days <= 90:
                rep.add("tier3", "recent_session_log", PASS,
                        f"newest log is {int(age_days)} days old")
            else:
                rep.add("tier3", "recent_session_log", INFO,
                        f"newest session log is {int(age_days)} days old",
                        "Consider whether this agent is still in use.")
    else:
        rep.add("tier3", "sessions_dir", WARN,
                "sessions/ is missing",
                "Create sessions/ for session logs.")

    for sub in ("cache", "output"):
        d = store / sub
        rep.add("tier3", f"{sub}_dir", PASS if d.exists() else INFO,
                "" if d.exists() else f"{sub}/ not present",
                "")


def _locate_logs(store: Path, filename: str) -> list[Path]:
    """Find an append-only log either at `memory/<filename>` or one level deeper
    at `memory/<subject>/<filename>` (per-subject pattern, e.g. memory/<subject>/...).
    Returns all matches.
    """
    memory = store / "memory"
    if not memory.exists():
        return []
    hits = []
    direct = memory / filename
    if direct.exists():
        hits.append(direct)
    for sub in memory.iterdir():
        if sub.is_dir() and sub.name not in ("_shared",):
            candidate = sub / filename
            if candidate.exists():
                hits.append(candidate)
    return hits


def audit_v2_patterns(rep: AgentReport, store: Path, target: Path,
                      definition: Path, mem_index: Path) -> None:
    """v1.2.0 patterns: critical_facts, log, DREAMS, failures, importance
    scoring on append-only files, named blocks in Tier 2, hooks installed."""
    if not store.exists():
        return

    # --- Tier 3 — new files ----------------------------------------------
    crit = store / "memory" / "critical_facts.md"
    if crit.exists():
        body = crit.read_text(encoding="utf-8", errors="replace")
        word_count = sum(1 for _ in re.finditer(r"\S+", body))
        # ~200 tokens — rule-of-thumb for an always-loaded distillation:
        # small enough that loading it across many agents doesn't dominate context.
        budget = 140
        if word_count <= budget:
            rep.add("v2", "critical_facts", PASS, f"{word_count} words (≤{budget})")
        else:
            rep.add("v2", "critical_facts", WARN,
                    f"critical_facts.md is {word_count} words — over ~{budget}-word budget",
                    "Distill harder — this file loads on every spawn.")
    else:
        rep.add("v2", "critical_facts", WARN,
                "memory/critical_facts.md missing (boot step 2)",
                "Add critical_facts.md — ≤200-token always-loaded distillation.")

    log = store / "log.md"
    if log.exists():
        try:
            age_days = (dt.datetime.now().timestamp() - log.stat().st_mtime) / 86400
            if age_days <= 30:
                rep.add("v2", "log_md", PASS, f"updated {int(age_days)}d ago")
            else:
                rep.add("v2", "log_md", INFO,
                        f"log.md last touched {int(age_days)}d ago",
                        "Agent may be idle; consider whether it's still in use.")
        except OSError:
            rep.add("v2", "log_md", PASS, "present")
    else:
        rep.add("v2", "log_md", WARN,
                "log.md missing (append-only chronology pattern)",
                "Create log.md for `## [YYYY-MM-DD HH:MM] kind | title` lines.")

    dreams = store / "memory" / "DREAMS.md"
    if dreams.exists():
        body = dreams.read_text(encoding="utf-8", errors="replace")
        # Find latest YYYY-MM-DD headed entry; if none, dreams was never run.
        dates = re.findall(r"^##\s+(\d{4}-\d{2}-\d{2})", body, re.MULTILINE)
        if not dates:
            rep.add("v2", "dreams", INFO,
                    "DREAMS.md exists but has no consolidation entries yet",
                    "Run `mh:agent:dream` weekly.")
        else:
            try:
                latest = max(dt.date.fromisoformat(d) for d in dates)
                age_days = (dt.date.today() - latest).days
                if age_days <= 14:
                    rep.add("v2", "dreams", PASS, f"last dream {age_days}d ago")
                elif age_days <= 30:
                    rep.add("v2", "dreams", INFO, f"last dream {age_days}d ago")
                else:
                    rep.add("v2", "dreams", WARN,
                            f"last dream {age_days}d ago — consolidation overdue",
                            "Run `mh:agent:dream --name <agent>`.")
            except ValueError:
                rep.add("v2", "dreams", INFO, "DREAMS.md present, dates unparseable")
    else:
        rep.add("v2", "dreams", WARN,
                "memory/DREAMS.md missing — no consolidation history",
                "Create DREAMS.md (or run `mh:agent:dream` which writes it).")

    # `failures.md` accepts either `memory/failures.md` or `memory/*/failures.md`
    failures_files = _locate_logs(store, "failures.md")
    rep.add("v2", "failures_md",
            PASS if failures_files else WARN,
            "" if failures_files else "no failures.md found (Reflexion pattern)",
            "" if failures_files else "Create memory/failures.md for failure attribution.")

    # --- Importance scoring on append-only files -------------------------
    for fname in ("what-works.md", "decisions.md", "failures.md"):
        files = _locate_logs(store, fname)
        if not files:
            continue
        body = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in files)
        # Skip templates that only contain examples in comment blocks AND
        # fenced code blocks (the "Format per entry" examples).
        active = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
        active = re.sub(r"^```.*?^```", "", active, flags=re.DOTALL | re.MULTILINE)
        # Count headings (entries) outside of comments + code blocks
        headings = re.findall(r"^##\s+(?!\d{4}-)", active, re.MULTILINE)
        importance_count = len(re.findall(r"^\s*importance\s*:\s*\d", active, re.MULTILINE))
        if not headings:
            rep.add("v2", f"importance_in_{fname}", INFO,
                    "no entries yet", "")
        elif importance_count == 0:
            rep.add("v2", f"importance_in_{fname}", WARN,
                    f"{len(headings)} entries, none with `importance:` YAML",
                    "Add `importance: 1-10` frontmatter at moment of capture.")
        elif importance_count < len(headings) * 0.5:
            rep.add("v2", f"importance_in_{fname}", WARN,
                    f"{importance_count}/{len(headings)} entries have importance",
                    "Backfill importance scores during next dream pass.")
        else:
            rep.add("v2", f"importance_in_{fname}", PASS,
                    f"{importance_count}/{len(headings)} entries scored")

    # --- Tier 2 named blocks (labelled-blocks-edited-via-tools pattern) ----
    if mem_index.exists():
        idx_body = mem_index.read_text(encoding="utf-8", errors="replace")
        expected_blocks = ["<persona>", "<critical_facts>", "<active_threads>",
                           "<open_questions>", "<recent_decisions>"]
        found = [b for b in expected_blocks if b in idx_body]
        if len(found) >= 3:
            rep.add("v2", "named_blocks", PASS,
                    f"{len(found)}/{len(expected_blocks)} blocks present")
        elif found:
            rep.add("v2", "named_blocks", INFO,
                    f"{len(found)}/{len(expected_blocks)} named blocks found",
                    "Add the missing blocks to MEMORY.md (persona, critical_facts, "
                    "active_threads, open_questions, recent_decisions).")
        else:
            rep.add("v2", "named_blocks", INFO,
                    "no Letta-pattern named blocks in MEMORY.md (flat index still works)",
                    "Optional: switch to named blocks for targeted Edit-based curation.")

    # --- Tier 1 — memory protocol + frozen snapshot ---------------------
    if definition.exists():
        def_body = definition.read_text(encoding="utf-8", errors="replace").lower()
        if "memory protocol" in def_body or "always view your memory" in def_body:
            rep.add("v2", "memory_protocol_in_def", PASS)
        else:
            # Note: the "always view your memory" boot string is documented in
            # platform.claude.com — checked here as a recommended cue.
            rep.add("v2", "memory_protocol_in_def", INFO,
                    "no 'Memory protocol' / 'ALWAYS VIEW YOUR MEMORY' clause in definition",
                    "Add a memory-protocol boot clause (recommended).")
        if "frozen-snapshot" in def_body or "session-start snapshot" in def_body:
            rep.add("v2", "frozen_snapshot_in_def", PASS)
        else:
            rep.add("v2", "frozen_snapshot_in_def", INFO,
                    "no frozen-snapshot discipline note in definition",
                    "Add a note that mid-session writes are only visible next spawn.")

    # --- Hooks installed -------------------------------------------------
    settings = target / ".claude" / "settings.json"
    if settings.exists():
        try:
            s = json.loads(settings.read_text(encoding="utf-8"))
            hooks = s.get("hooks", {}) or {}
            present = [e for e in ("PreCompact", "SessionEnd", "SessionStart") if e in hooks]
            if len(present) == 3:
                rep.add("v2", "hooks_installed", PASS,
                        "PreCompact + SessionEnd + SessionStart registered")
            elif present:
                rep.add("v2", "hooks_installed", INFO,
                        f"only {len(present)}/3 lifecycle hooks: {', '.join(present)}",
                        "Run `mh:agent:create --with-hooks --force` or wire manually.")
            else:
                rep.add("v2", "hooks_installed", INFO,
                        "no PreCompact/SessionEnd/SessionStart hooks",
                        "Add hooks via `mh:agent:create --with-hooks`.")
        except json.JSONDecodeError:
            rep.add("v2", "hooks_installed", INFO,
                    "settings.json is not valid JSON",
                    "Fix settings.json before adding hooks.")
    else:
        rep.add("v2", "hooks_installed", INFO,
                ".claude/settings.json absent (no lifecycle hooks)",
                "Add hooks via `mh:agent:create --with-hooks`.")


# ---------------------------------------------------------------------------

def audit_cross_tier(rep: AgentReport, fm: dict[str, str],
                     mem_index: Path, definition: Path) -> None:
    """Identity-line consistency between Tier 1 and Tier 2."""
    if not (mem_index.exists() and definition.exists()):
        return
    role_def = definition.read_text(encoding="utf-8", errors="replace")
    role_idx = mem_index.read_text(encoding="utf-8", errors="replace")

    def first_identity_line(text: str) -> str:
        for line in text.splitlines():
            if line.lstrip().startswith(("I'm **", "I am **")):
                return line.strip()
        return ""

    a, b = first_identity_line(role_def), first_identity_line(role_idx)
    if a and b:
        # rough match: same bolded name?
        name_a = re.search(r"\*\*([^*]+)\*\*", a)
        name_b = re.search(r"\*\*([^*]+)\*\*", b)
        if name_a and name_b and name_a.group(1).strip().lower() == name_b.group(1).strip().lower():
            rep.add("cross", "identity_consistent", PASS)
        else:
            rep.add("cross", "identity_consistent", WARN,
                    f"identity line bold name differs: {name_a and name_a.group(1)} vs {name_b and name_b.group(1)}",
                    "Align the identity one-liner across Tier 1 and Tier 2.")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_agents(target: Path) -> list[str]:
    agents_dir = target / ".claude" / "agents"
    if not agents_dir.exists():
        return []
    return sorted(p.stem for p in agents_dir.glob("*.md") if not p.name.startswith("_"))


def audit_agent(name: str, target: Path) -> AgentReport:
    rep = AgentReport(name=name)
    definition = target / ".claude" / "agents" / f"{name}.md"
    mem_index = target / ".claude" / "agent-memory" / name / "MEMORY.md"
    store = target / ".agents" / name

    # Cross-tier presence
    have_def = definition.exists()
    have_idx = mem_index.exists()
    have_store = store.exists()
    if have_def and have_idx and have_store:
        rep.add("cross", "all_three_tiers_present", PASS)
    else:
        missing = []
        if not have_def: missing.append("definition")
        if not have_idx: missing.append("memory-index")
        if not have_store: missing.append("deep-store")
        rep.add("cross", "all_three_tiers_present", FAIL,
                f"missing tier(s): {', '.join(missing)}",
                "Run `mh:agent:create` with the same name to scaffold the gaps.")

    fm = audit_tier1(rep, definition)
    audit_tier2(rep, mem_index, target)
    audit_tier3(rep, store)
    audit_v2_patterns(rep, store, target, definition, mem_index)
    audit_cross_tier(rep, fm, mem_index, definition)
    return rep


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

SEV_ICON = {PASS: "✅", WARN: "⚠️ ", FAIL: "❌", INFO: "ℹ️ "}


# ---------------------------------------------------------------------------
# Drift / apply
# ---------------------------------------------------------------------------

def _resolve_create_templates() -> Path:
    """Locate the sibling agent:create skill's templates dir.

    Walks up from this script: skills/agent:audit/scripts/ → skills/agent:create/templates/
    """
    here = Path(__file__).resolve()
    candidate = here.parent.parent.parent / "agent:create" / "templates"
    if candidate.exists():
        return candidate
    # Fallback for installed plugins where layout could differ
    raise FileNotFoundError(
        f"could not find sibling agent:create templates at {candidate}"
    )


def _kebab_to_title(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def _render(template_dir: Path, template_name: str, name: str) -> str:
    body = (template_dir / template_name).read_text(encoding="utf-8")
    vars_ = {
        "NAME": name,
        "NAME_TITLE": _kebab_to_title(name),
        "ROLE": "(role placeholder — fill in via mh:agent:create)",
        "DESCRIPTION": "(description placeholder)",
        "ANCHOR": "TODO — add an anchor phrase",
        "VOICE": "TODO — define the agent's voice",
    }
    for k, v in vars_.items():
        body = body.replace("{{" + k + "}}", v)
    return body


_SUBJECTLOG_FILES = {"what-works.md", "decisions.md", "failures.md", "DREAMS.md"}


def drift_report(name: str, target: Path) -> list[dict]:
    """For each entry in TEMPLATE_MANIFEST, decide PRESENT / MISSING.

    For per-subject log files (what-works, decisions, failures, DREAMS), accept
    either the direct path or a subject-subfolder match (memory/<subject>/<file>).
    """
    try:
        _resolve_create_templates()
    except FileNotFoundError as e:
        return [{"path": str(e), "template": "", "status": "ERROR", "level": "ERROR"}]
    store = target / ".agents" / name
    rows: list[dict] = []
    for rel, tmpl, level in TEMPLATE_MANIFEST:
        rel_resolved = rel.format(name=name)
        direct = target / rel_resolved
        present = direct.exists()
        detail = ""
        if not present and direct.name in _SUBJECTLOG_FILES:
            # accept memory/<subject>/<file>.md
            hits = _locate_logs(store, direct.name)
            if hits:
                present = True
                detail = "found at " + ", ".join(str(h.relative_to(target)) for h in hits)
        rows.append({
            "path": rel_resolved,
            "template": tmpl,
            "status": "PRESENT" if present else "MISSING",
            "level": level,
            "detail": detail,
        })
    return rows


def apply_missing(name: str, target: Path, drifts: list[dict]) -> list[str]:
    """For each MISSING row, copy the template (rendered) into place. Never overwrites."""
    tdir = _resolve_create_templates()
    results: list[str] = []
    for row in drifts:
        if row["status"] != "MISSING" or row["level"] == "ERROR":
            continue
        dest = target / row["path"]
        if dest.exists():  # belt-and-braces
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = _render(tdir, row["template"], name)
        dest.write_text(body, encoding="utf-8")
        results.append(f"WROTE   {dest}")
    return results


def render_drift_markdown(name: str, rows: list[dict]) -> str:
    out = [f"# Drift report — `{name}`", ""]
    miss_req = sum(1 for r in rows if r["status"] == "MISSING" and r["level"] == "required")
    miss_rec = sum(1 for r in rows if r["status"] == "MISSING" and r["level"] == "recommended")
    out.append(f"**Summary:** {miss_req} required + {miss_rec} recommended files missing.")
    out.append("")
    out.append("| Status | Level | Path | Template | Detail |")
    out.append("|---|---|---|---|---|")
    for r in rows:
        icon = "✅" if r["status"] == "PRESENT" else ("❌" if r["level"] == "required" else "⚠️ ")
        det = r.get("detail", "")
        out.append(f"| {icon} {r['status']} | {r['level']} | `{r['path']}` | `{r['template']}` | {det} |")
    out.append("")
    if miss_req + miss_rec > 0:
        out.append("Run `audit_agent.py --name <agent> --target <dir> --mode apply` "
                   "to write the missing files from templates (never overwrites).")
    return "\n".join(out)


def render_markdown(reports: list[AgentReport]) -> str:
    today = dt.date.today().isoformat()
    total = sum(len(r.checks) for r in reports)
    fails = sum(r.count(FAIL) for r in reports)
    warns = sum(r.count(WARN) for r in reports)
    infos = sum(r.count(INFO) for r in reports)

    lines = [f"# Agent Audit — {today}", ""]
    lines.append(
        f"**Summary:** {len(reports)} agent(s), {total} checks, "
        f"**{fails} FAIL**, {warns} WARN, {infos} INFO."
    )
    lines.append("")

    for r in reports:
        icon = SEV_ICON.get(r.worst, "")
        lines.append(f"## {icon} `{r.name}`")
        lines.append("")
        lines.append("| Tier | Check | Result | Detail | Fix |")
        lines.append("|---|---|---|---|---|")
        for c in r.checks:
            detail = c.detail.replace("|", "\\|")
            fix = c.fix.replace("|", "\\|")
            lines.append(f"| {c.tier} | {c.name} | {c.result} | {detail} | {fix} |")
        lines.append("")
    return "\n".join(lines)


def render_json(reports: list[AgentReport]) -> str:
    payload = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "agents": [
            {
                "name": r.name,
                "worst": r.worst,
                "counts": {sev: r.count(sev) for sev in (FAIL, WARN, PASS, INFO)},
                "checks": [asdict(c) for c in r.checks],
            }
            for r in reports
        ],
    }
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Lint Claude Code three-tier subagents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--target", default=".",
                   help="directory containing .claude/agents (default: cwd)")
    p.add_argument("--name", default=None,
                   help="audit only this agent (default: every agent under .claude/agents/)")
    p.add_argument("--format", choices=("markdown", "json"), default="markdown",
                   help="output format (default: markdown)")
    p.add_argument("--mode", choices=("audit", "drift", "apply"), default="audit",
                   help="audit: full check (default); drift: diff vs latest templates; "
                        "apply: write only the files that are missing (never overwrite)")
    args = p.parse_args(argv)

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        print(f"error: --target {target} does not exist", file=sys.stderr)
        return 2

    if args.name:
        names = [args.name]
    else:
        names = discover_agents(target)
        if not names:
            print(f"error: no agents found under {target / '.claude/agents'}",
                  file=sys.stderr)
            return 2

    # Mode: drift — show what's missing vs latest templates, never write
    if args.mode == "drift":
        if args.format == "json":
            payload = {"target": str(target),
                       "agents": [{"name": n, "drift": drift_report(n, target)} for n in names]}
            print(json.dumps(payload, indent=2))
        else:
            for n in names:
                print(render_drift_markdown(n, drift_report(n, target)))
                print()
        return 0

    # Mode: apply — write missing files from templates, then run audit
    if args.mode == "apply":
        any_written = False
        for n in names:
            drifts = drift_report(n, target)
            written = apply_missing(n, target, drifts)
            for line in written:
                print(line)
            if written:
                any_written = True
        if not any_written:
            print("nothing to write — all template files already present.")
        return 0

    # Mode: audit (default)
    reports = [audit_agent(n, target) for n in names]

    if args.format == "json":
        print(render_json(reports))
    else:
        print(render_markdown(reports))

    return 1 if any(r.count(FAIL) > 0 for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
