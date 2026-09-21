# Branch naming

Work branches are explicit task names, not `cursor/<random>` slugs.

## Pattern

`<area>-<short-task>` in kebab-case. No `cursor/` prefix. No random or run-id suffix.

| Area | Meaning | Use for |
|------|---------|---------|
| `w1` | core | API, data model, jobs, reconciler |
| `w2` | web | web app |
| `w3` | accounts | auth, billing, accounts |
| `w4` | surfaces | CLI, MCP, operator surfaces |
| `docs` | proposal / entrega only | not product code |

Examples: `w1-openapi-freeze`, `w2-pond-detail`, `w3-auth-routers`, `w4-cli-ponds`, `docs-entrega-1`.

## What actually controls the name

**Rule only. No setting was changed.**

Checked and cannot set this from an agent:

- This Project’s cloud environment (`e0d7cf56-ae48-11f1-bf4b-42ffb4d10ea7`, personal, no repo `environment.json`) has no branch-name field. Cloud environment tools cannot write one.
- `.cursor/environment.json` is machine setup (install, snapshot, network). It does not name branches.
- Cursor’s real control is a **single static** “Branch prefix” under [Cloud Agents → My Settings](https://cursor.com/dashboard/cloud-agents#my-defaults) (also Team Settings, and the editor’s Cloud Agent defaults). Default is `cursor/`. An empty value falls back to `cursor/`. It is applied before the agent runs, so `preferences.md` and `AGENTS.md` do not replace it. One prefix also cannot express `w1` / `w2` / `w3` / `w4` / `docs`.

Agents still receive an injected template like `cursor/<descriptive-name>-<id>`. Ignore it.

## What agents must do

1. Pick the name before the first commit (`w2-pond-detail`, not `cursor/pond-detail-8735`).
2. Create that branch from the base branch: `git checkout -b w2-pond-detail`.
3. When opening the PR, pass the branch-prefix override: `skip_branch_prefix_check: true`, with `branch_name` set to that exact name. This Project’s preferences are the explicit request to override the prefix.
4. If a `cursor/…` branch was already pushed for the same work, delete it after the PR is on the named branch.

## What still needs Carlos in the Cursor UI

Nothing required for this convention. Do not clear Branch prefix — empty becomes `cursor/` again. Do not set a custom prefix hoping it will vary by area; it will not. Leave the dashboard prefix as-is unless you want a different static label on branches the agent fails to rename.
