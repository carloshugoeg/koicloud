# Merge lanes

Each pull request carries one label, `lane:low` or `lane:high`.

A pull request that touches any high-risk path is high-risk.

A path that matches no glob is high-risk.

## Authors

`@Jasgu097`, `@Josh-JM`, and `@diegojoachin07` do not auto-merge on either lane.

The agent markers are `<!-- CURSOR_AGENT_PR_BODY_BEGIN -->` and `<!-- CURSOR_AGENT_PR_BODY_END -->`.

A pull request from `@carloshugoeg` is an agent pull request when the body contains both markers. Lane rules apply to that pull request.

A pull request from `@carloshugoeg` that lacks either marker is Carlos's own pull request. It does not auto-merge.

## How a path gets a lane

The first rule that matches wins.

1. A path that matches a test glob or a style glob is low-risk.
2. A path that matches a high-risk glob is high-risk.
3. A dependency path is high-risk when the change is not a patch bump.
4. A path that matches another low-risk glob is low-risk.
5. Any other path is high-risk.

The pull request is `lane:high` when any changed path is high-risk. The pull request is `lane:low` only when every changed path is low-risk.

Rule 1 is the only reason a path inside a high-risk directory stays low-risk. A test file under `apps/api/app/modules/auth/` is low-risk. The same pull request becomes high-risk if it also changes `apps/api/app/modules/auth/service.py`.

## Low-risk lane

The label is `lane:low`.

A low-risk pull request auto-merges only when CI is green, Bugbot is clean, and gate, the QA bot, passes. That auto-merge runs only for an author the Authors section allows.

| Area | Paths |
| --- | --- |
| Copy | None. The tree has no `i18n`, `locale`, or copy directory. UI strings live in feature modules. Those files keep that module's lane. |
| Styles | `apps/web/src/index.css`, `apps/web/src/styles/**`, `apps/web/tailwind.config.ts`, `apps/web/postcss.config.js`, `apps/web/src/features/sql-console/sql-editor-theme.ts` |
| Tests | `**/*.test.ts`, `**/*.test.tsx`, `**/tests/**`, `**/__tests__/**`, `scripts/test_*.py`, `apps/web/src/test/**` |
| Patch-level dependency updates | `apps/web/package.json`, `apps/web/pnpm-lock.yaml`, `apps/api/pyproject.toml`, `apps/api/uv.lock`, `apps/cli/pyproject.toml`, `apps/cli/uv.lock`, `apps/node-agent/pyproject.toml`, `apps/node-agent/uv.lock` |
| Internal tools | `scripts/**`, `apps/api/app/tooling/**`, `apps/web/scripts/**`, `load/**`, `Makefile` |

A dependency path from that row stays low-risk only when every version change is a patch bump. A patch bump changes only the last number in a version, as in 1.2.3 to 1.2.4. A minor bump, a major bump, an added dependency, or a removed dependency makes that path high-risk. Rule 3 records that exception.

`scripts/migrate-dev.sh` matches the internal-tool glob and the data-migration glob. Rule 2 wins, so that file is high-risk.

## High-risk lane

The label is `lane:high`.

A high-risk pull request does not auto-merge. Carlos approves it at 9:00 or at 16:00 in `America/Guatemala`. Grok Bot batches high-risk pull requests for that window.

| Area | Paths |
| --- | --- |
| Auth | `apps/api/app/modules/auth/**`, `apps/api/app/commands/auth.py`, `apps/api/app/core/auth.py`, `apps/api/app/core/security.py`, `apps/api/app/core/crypto.py`, `apps/api/app/core/deps.py`, `apps/web/src/features/auth/**`, `apps/web/src/lib/auth-store.ts`, `apps/web/src/api/hooks/auth.ts`, `apps/web/src/app/guards.tsx`, `apps/web/src/app/session-boot-gate.tsx`, `apps/cli/koicloud_cli/commands/auth.py` |
| Payments | `apps/api/app/modules/billing/**`, `apps/api/app/commands/billing.py`, `apps/api/app/workers/daily_renewal.py`, `apps/web/src/features/plans/**`, `apps/web/src/api/hooks/plans.ts`, `apps/web/src/api/hooks/invoices.ts`, `apps/cli/koicloud_cli/commands/subscription.py` |
| Data migrations | `apps/api/alembic/**`, `apps/api/alembic.ini`, `scripts/migrate-dev.sh` |
| Production environment | `.env.example`, `apps/api/app/core/config.py`, `apps/node-agent/agent/config.py`, `docker-compose.yml`, `docker-compose.docker-agent.yml`, `docker-compose.vm-hostnet.yml`, `infra/**`, `apps/web/vercel.json`, `.github/workflows/**`, `.github/scripts/**` |
| Client sites at launch | `apps/web/index.html`, `apps/web/src/main.tsx`, `apps/web/src/app/**`, `apps/web/src/components/**`, `apps/web/src/features/landing/**`, `apps/web/src/features/ponds/**`, `apps/web/src/features/uso/**`, `apps/web/src/features/sql-console/**`, `apps/web/src/features/pages.tsx`, `apps/web/src/api/client.ts`, `apps/web/src/api/hooks/ponds.ts`, `apps/web/src/api/hooks/sql-console.ts`, `apps/web/public/**` |

## Paths with no glob

A path in neither table is high-risk. These trees are examples, not a full list.

- `apps/web/src/features/admin/**`
- `apps/web/src/features/agent-access/**`
- `apps/api/app/modules/ponds/**`
- `apps/api/app/commands/ponds.py`
- `apps/node-agent/**`, other than `apps/node-agent/agent/config.py` and test paths
- `apps/cli/**`, other than the auth command, the subscription command, and test paths
- `packages/contracts/**`
- `docs/**`
- `LANES.md`
