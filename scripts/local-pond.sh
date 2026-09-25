#!/usr/bin/env bash
# Start the Compose pond-demo and print a psql URI.
# Does not need the VPS. Needs a local Docker daemon.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está en este entorno. El driver real está en apps/node-agent"
  echo "y el servicio Compose es pond-demo (profile ponds)."
  echo "En una máquina con Docker:"
  echo "  make pond-demo"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "El daemon de Docker no responde. Arrancalo y reintentá \`make pond-demo\`."
  exit 1
fi

docker compose --profile ponds up -d pond-demo

echo "Esperando healthcheck de pond-demo…"
for _ in $(seq 1 40); do
  status="$(docker inspect --format '{{.State.Health.Status}}' koicloud-inventario-demo 2>/dev/null || true)"
  if [ "$status" = "healthy" ]; then
    break
  fi
  sleep 1
done

if [ "${status:-}" != "healthy" ]; then
  echo "pond-demo no quedó healthy. \`docker compose --profile ponds logs pond-demo\`"
  exit 1
fi

URI="postgresql://postgres:local-pond-dev-only@127.0.0.1:15432/inventario_demo"
echo
echo "Pond local listo (sin VPS)."
echo "  psql \"$URI\""
echo
echo "Para el driver docker del node-agent (jobs create_pond reales):"
echo "  AGENT_MODE=docker docker compose -f docker-compose.yml -f docker-compose.docker-agent.yml up"
echo
echo "El E2E register → Micro → POST /ponds sigue pidiendo persistencia W3/W1 y un VPS."
echo "Este servicio solo adelanta el hito de \`psql\` contra un postgres:16-alpine real."
