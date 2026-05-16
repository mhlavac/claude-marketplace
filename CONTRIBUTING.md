# Contributing

Thanks for the interest. This is a personal marketplace, but PRs and issues are welcome.

## License

By contributing, you agree your contribution is licensed under the [MIT License](./LICENSE) — the same terms as the rest of the repository. Don't add code under a different license without flagging it explicitly in the PR. See [CLAUDE.md → License](./CLAUDE.md#license) for the vendoring rules on third-party assets.

## Repo conventions

See [CLAUDE.md](./CLAUDE.md) for structure, naming (single `mh` plugin; skills invoked as `mh:<skill>`), and commit conventions. The short version:

- kebab-case folder and skill names
- skill folder name = the `name` in its `SKILL.md` frontmatter
- semver in `plugins/mh/.claude-plugin/plugin.json` and `plugins/mh/CHANGELOG.md`
- [Conventional Commits](https://www.conventionalcommits.org/) for commit messages and PR titles, scoped by skill name

## Adding a new skill

1. Create `plugins/mh/skills/<skill-name>/` with `SKILL.md` (frontmatter + body) and a `README.md`.
2. Add `scripts/`, `assets/`, `references/` as needed.
3. Add a row to the skill table in `plugins/mh/README.md`.
4. Bump `plugins/mh/.claude-plugin/plugin.json` version (minor for new skill).
5. Add an entry to `plugins/mh/CHANGELOG.md`.
6. Test locally before opening the PR — see [README → From a local clone](./README.md#from-a-local-clone).

## Modifying an existing skill

- Bump `plugins/mh/.claude-plugin/plugin.json` per semver (patch for fixes, minor for additive behavior, major for breaking changes).
- Add an entry to `plugins/mh/CHANGELOG.md` scoped to the skill.
- Update the skill's `README.md` and `SKILL.md` if behavior changes.

## Pre-push checklist

See [CLAUDE.md → Pre-push checklist](./CLAUDE.md#pre-push-checklist) — single source of truth for what to run and what to grep for before pushing to this public repo.

## Reporting issues

Open a GitHub issue with: skill name + plugin version, what you did, what you expected, what happened. Include a minimal repro if you can.
