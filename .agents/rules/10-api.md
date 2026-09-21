---
trigger: glob
globs: apps/api/**
description: Convenciones del backend FastAPI (apps/api)
---

- **Layout de módulo:** `router.py` (fino, sin lógica ni SQL, funciones ≤ 30 líneas) ·
  `schemas.py` (Pydantic v2, cada modelo con `example`) · `models.py` (SQLAlchemy 2.0,
  solo tablas del módulo) · `service.py` (reglas; recibe `AsyncSession`; no conoce HTTP) ·
  `repository.py` (opcional) · `tasks.py` (opcional) · `tests/`.
  Sin `utils.py` ni `helpers.py` genéricos.
- **Grafo de imports** (lo fuerza `import-linter`): `router → service → repository/models`.
  `service` puede usar `core/*` y llamar a `commands/*`, nunca al revés. Un módulo solo
  importa de otro a través de su `__init__.py`.
- **Toda operación sobre ponds pasa por `app/commands/`.** Las firmas de los comandos son
  contrato congelado: no se cambian sin CCR, aunque el cuerpo sea `NotImplementedError`.
- **Errores:** solo `AppError` con un `code` del catálogo de
  `docs/architecture/api-surface.md` §7. Nada de `HTTPException` suelta ni mensajes crudos.
- **SQL** solo con SQLAlchemy parametrizado. Única excepción: `commands/sql.py`, que ejecuta
  SQL del usuario contra **su** pond, en transacción de solo lectura con `statement_timeout`.
- **Sin estado en memoria entre requests.** Nada de cachés globales ni singletons con datos.
- **Migraciones: solo W1.** Una sola cabeza de Alembic; las migraciones fusionadas no se
  editan. Si tu ticket necesita una columna que no existe: `BLOQUEADO`, abre CCR.
- **Pruebas obligatorias:** `tests/test_api.py` (caso feliz + al menos un error del catálogo,
  con `httpx.AsyncClient`) y `tests/test_service.py` (unitaria, DB real en transacción
  revertida) por cada endpoint o regla nueva.
- Antes del PR: `make check-api` y pega la salida real.
