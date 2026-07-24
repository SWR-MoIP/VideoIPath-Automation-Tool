---
description: Agent rules directory layout and symlink conventions
alwaysApply: false
globs: .agents/rules/**,.claude/rules/**,.cursor/rules/**
paths:
  - ".agents/rules/**/*.md"
  - ".claude/rules/**/*.md"
  - ".cursor/rules/**/*.mdc"
---

# Agent rules layout

This repo stores path-scoped agent rules in a tool-agnostic location and bridges them into Claude Code and Cursor via symlinks.

## Canonical source

- **Edit rules here:** `.agents/rules/*.md`
- **Do not** put rule content directly in `.claude/rules/` or `.cursor/rules/` — those files are symlinks.

## Tool bridges

Claude Code reads `.claude/rules/*.md`. Cursor requires `.cursor/rules/*.mdc`. Each bridge entry is a symlink to the matching canonical `.md`:

```text
.agents/rules/my-rule.md          ← canonical (commit this)
.claude/rules/my-rule.md          ← symlink → ../../.agents/rules/my-rule.md
.cursor/rules/my-rule.mdc         ← symlink → ../../.agents/rules/my-rule.md
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

1. Create `.agents/rules/<name>.md` with dual frontmatter and content.
2. Add the Claude and Cursor symlinks:

```bash
ln -s ../../.agents/rules/<name>.md .claude/rules/<name>.md
ln -s ../../.agents/rules/<name>.md .cursor/rules/<name>.mdc
```

3. List the new rule in the **Agent rules** section of `AGENTS.md`.

## Removing a rule

1. Delete `.agents/rules/<name>.md`.
2. Delete `.claude/rules/<name>.md` and `.cursor/rules/<name>.mdc` (the symlinks, not separate copies).
3. Remove its entry from `AGENTS.md`.

## Do not

- Symlink an entire bridge directory to another (extension mismatch: `.mdc` vs `.md`).
- Duplicate rule content across directories.
- Commit real files under `.claude/rules/` or `.cursor/rules/` — only symlinks belong there.
