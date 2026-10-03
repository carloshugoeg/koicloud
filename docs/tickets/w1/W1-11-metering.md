---
id: W1-11
workstream: W1
persona: Carlos
estado: abierto
rama: w1-metering
epica: "E7-01, E7-02, E7-03, E7-04"
sprint: S3
pr:
depends_on:
---

# [W1-11] Muestreo y agregación de consumo

## Qué se ve

El node-agent sube muestras de tamaño de pond. Un worker agrega `usage_daily`.
`GET /usage` deja de devolver solo el example: muestra instance_hours / storage reales
(o ceros honestos) para el mes pedido. Dashboard y CLI pueden dejar de pintar `—` cuando
haya filas.

## Entradas ya decididas (no se cambian)

- Endpoint interno de samples ya en OpenAPI (`/internal/v1/...` samples).
- Tablas `pond_samples` / `usage_daily` según `data-model.md` (crear ORM si falta).
- `commands.usage.get_usage` firma congelada; Web/CLI/MCP solo leen.
- Sin inventar KPIs: si no hay samples, devolver ceros o lista vacía del contrato, no
  números inventados.

## Criterios de aceptación

1. El agent (mock o docker) puede persistir al menos una sample por pond activo.
2. Agregación diaria escribe `usage_daily` idempotente para un día dado.
3. `GET /api/v1/usage` (y query `month` si aplica) lee agregados reales del usuario.
4. Prueba API: tras insertar samples + agregar, el mes refleja storage/instance_hours > 0
   o el shape vacío documentado.
5. `make check-api` verde.

## No tocar

OpenAPI a mano. UI W2 (solo consume el endpoint). Billing/subscribe. Sin VPS.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

`docs/architecture/feature-breakdown.md` E7 y `docs/architecture/interconnections.md` medición.
