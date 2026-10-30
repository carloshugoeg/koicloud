# Oracle Always Free + sslip.io (costo $0)

## Status

Accepted. W1-13.

## Context

La entrega académica (ENTREGA-2 §6.3) pide un solo nodo con Docker, Caddy y ponds
reales. El equipo no tiene dominio de pago. ADR 003 ya eligió Docker en un VPS
frente a Kubernetes. Quedaba elegir el host y el nombre DNS.

Render y Neon alojan bien la API y Postgres, pero **no exponen el socket Docker**.
Sin socket no hay `AGENT_MODE=docker` ni ponds reales (solo mock). Eso incumple
el hito de provisioning.

## Decision

Desplegar en **una** VM Oracle Cloud Always Free (Ampere ARM, Ubuntu). Hostname
vía **sslip.io** o **nip.io** (`<ip-pública>.sslip.io`) sin dominio de pago. Caddy
hace TLS automático (ACME). Compose + unit systemd del node-agent reutilizan
ADR 003 (SSH + Docker + Caddy). Costo del host y del DNS: **$0**.

## Consequences

- Imágenes deben construir en `linux/arm64` (bases multi-arch, sin pin amd64).
- Puertos 80/443 y el rango de ponds `15000-15999` se abren en la VCN y en iptables.
- El cableado real sigue fuera del repo hasta que exista la VM. Este ADR no inventa IP.
- Alternativas rechazadas: Render/Neon (sin Docker socket → sin ponds reales).
