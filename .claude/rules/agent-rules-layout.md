---
description: Agent rules directory layout and symlink conventions
alwaysApply: false
globs: .claude/rules/**,.cursor/rules/**
paths:
  - ".claude/rules/**/*.md"
  - ".cursor/rules/**/*.mdc"
---

# Agent rules layout

This repo shares agent rules between **Claude Code** and **Cursor** via symlinks.

## Canonical source

- **Edit rules here:** `.claude/rules/*.md`
- **Do not** put rule content directly in `.cursor/rules/` — those files are symlinks.

## Cursor bridge

Cursor requires `.mdc` files in `.cursor/rules/`. Each `.mdc` is a symlink to the matching `.md`:

```text
.claude/rules/my-rule.md          ← canonical (commit this)
.cursor/rules/my-rule.mdc         ← symlink → ../.claude/rules/my-rule.md
```

## Dual frontmatter

Every rule file needs frontmatter for both tools:

```yaml
---
description: Short summary for Cursor rule picker
alwaysApply: false
globs: path/to/match/**
paths:
  - "path/to/match/**"
---
```

- **Cursor** uses `globs`, `alwaysApply`, and `description`.
- **Claude Code** uses `paths`; omit `paths` for always-on rules.
- Each tool ignores the other's keys.

## Adding a rule

1. Create `.claude/rules/<name>.md` with dual frontmatter and content.
2. Add the Cursor symlink:

```bash
ln -s ../.claude/rules/<name>.md .cursor/rules/<name>.mdc
```

3. List the new rule in the **Agent rules** section of `AGENTS.md`.

## Removing a rule

1. Delete `.claude/rules/<name>.md`.
2. Delete `.cursor/rules/<name>.mdc` (the symlink, not a separate file).
3. Remove its entry from `AGENTS.md`.

## Do not

- Symlink the entire `.cursor/rules` directory to `.claude/rules` (extension mismatch: `.mdc` vs `.md`).
- Duplicate rule content in both directories.
- Commit real files under `.cursor/rules/` — only symlinks belong there.
