# Host VPS + sslip.io (host académico)

## Status

Accepted (amended). W1-13; host fact update W1-52.

## Context

La entrega académica (ENTREGA-2 §6.3) pide un solo nodo con Docker, Caddy y ponds
reales. El equipo no tiene dominio de pago. ADR 003 ya eligió Docker en un VPS
frente a Kubernetes. Quedaba elegir el host y el nombre DNS.

Render y Neon alojan bien la API y Postgres, pero **no exponen el socket Docker**.
Sin socket no hay `AGENT_MODE=docker` ni ponds reales (solo mock). Eso incumple
el hito de provisioning.

La decisión original (W1-13) apuntaba a **Oracle Cloud Always Free** (Ampere ARM)
como host a **$0**. En la práctica el despliegue de demo corre en un **Hostinger
KVM 1** (VPS x86_64). El hostname sigue sin dominio de pago.

## Decision

Desplegar en **una** VM: **Hostinger KVM 1** (Ubuntu). Hostname vía la variable
de repositorio **`KOICLOUD_DOMAIN`**, hoy un host **sslip.io** (o nip.io)
`<ip-pública>.sslip.io` sin dominio de pago. Caddy hace TLS automático (ACME).
Compose + unit systemd del node-agent reutilizan ADR 003 (SSH + Docker + Caddy).

Alternativas rechazadas: Render/Neon (sin Docker socket → sin ponds reales).
Oracle Always Free queda como alternativa histórica de costo $0, no como host
de producción actual.

## Consequences

- Imágenes con bases multi-arch (`*-alpine`, `python:3.12-slim`) sin pin
  `linux/amd64` ni `linux/arm64` en el compose de producción.
- Puertos 80/443 y el rango de ponds `15000-15999` se abren en el firewall del VPS.
- El valor concreto de `KOICLOUD_DOMAIN` vive en las variables del repo de GitHub;
  este ADR no inventa IP.
- El nombre de archivo `014-oracle-always-free-sslip.md` se conserva para no
  romper enlaces; el título y el cuerpo reflejan el host real.
