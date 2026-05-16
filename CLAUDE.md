# Repository rules

## Public repository — no personal data

This is a public repository. Never share personal information. Always obfuscate examples: invent names, change scenarios, swap real identifiers for plausible fictional ones. This applies to commit messages, code, docs, fixtures, and screenshots.

## Pre-push checklist

Before pushing:

1. Run `/simplify` on changed code (skip for docs-only changes).
2. Run `git diff HEAD` (and check untracked files) for data and secret leaks. Grep cues to start with: `sk-`, `ghp_`, `xoxb-`, `.internal`, `/Users/`, real corporate names, customer identifiers, real email addresses other than `mhlavac` / public handles.
3. Verify any new third-party assets have their `LICENSE` vendored alongside (see License section below).
4. Never commit `feedback/` output directories produced by the `mh:annotated-feedback` skill — they contain user-submitted artifact responses.

## License

MIT for the marketplace and the plugin in it. The root `LICENSE` file is canonical. The plugin's `plugin.json` MUST include `"license": "MIT"`.

Bundled third-party assets keep their original license — vendor the original `LICENSE` file alongside the asset (see `plugins/mh/skills/annotated-feedback/assets/vendor/LICENSES/` for the pattern) and record the upstream source URL and version.

## Repository structure

```
/.claude-plugin/marketplace.json          # marketplace manifest, one plugin: mh
/LICENSE                                  # MIT, repo-wide
/CONTRIBUTING.md                          # contribution + release rules
/CLAUDE.md                                # this file
/plugins/mh/
  .claude-plugin/plugin.json              # plugin manifest (name: mh, version, license)
  README.md                               # plugin overview + skill index
  CHANGELOG.md                            # plugin-level changelog (keep-a-changelog style)
  skills/<skill>/
    SKILL.md                              # skill frontmatter + body
    README.md                             # skill-specific docs (optional but recommended)
    {scripts,assets,references}/
```

Folder names MUST equal the `name` field in the corresponding manifest / SKILL.md frontmatter.

## Naming conventions

- **Single plugin**: `mh`. Everything ships inside it so all invocations read `mh:<skill>`.
- **kebab-case** everywhere (folders, skill names, manifest keys that are identifiers).
- **Skill name = the action/noun**, no `mh-` re-prefix (the namespace already comes from the plugin name).
- **Versioning is semver** in `plugins/mh/.claude-plugin/plugin.json` and tracked in `plugins/mh/CHANGELOG.md`. Bump the plugin version on any user-visible skill change. Skills themselves don't carry independent versions — Claude Code only versions plugins.

## Commits and PRs

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>
```

- **type**: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`
- **scope**: skill name (e.g., `annotated-feedback`), or omit for repo- / plugin-wide changes
- **subject**: imperative, lowercase, no trailing period

Examples:

```
feat(annotated-feedback): add radio-group element
fix(annotated-feedback): escape user input in envelope renderer
chore: bump marketplace description
```

Breaking changes: append `!` after the type/scope (`feat(annotated-feedback)!: …`) and include a `BREAKING CHANGE:` footer.
