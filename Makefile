.PHONY: sync-rules contracts check-api check-web check-cli check-node-agent check-infra check migrate seed up pond-demo

sync-rules:
	python3 scripts/sync-rules.py

contracts:
	cd apps/api && uv run python -m app.tooling.export_openapi
	cd apps/web && pnpm gen:api

check-api:
	cd apps/api && uv run ruff check . && uv run pytest -q

check-web:
	cd apps/web && pnpm lint && pnpm typecheck && pnpm test && pnpm build

check-cli:
	cd apps/cli && uv run ruff check . && uv run pytest -q

check-node-agent:
	cd apps/node-agent && uv run ruff check . && uv run pytest -q

check-infra:
	bash infra/scripts/check-prod-compose.sh

check: check-api check-web check-cli check-node-agent check-infra

migrate:
	bash scripts/migrate-dev.sh

seed:
	bash scripts/seed-dev.sh

up:
	docker compose up --build

pond-demo:
	bash scripts/local-pond.sh
