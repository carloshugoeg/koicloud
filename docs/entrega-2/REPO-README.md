# KoiCloud — Entrega 2 (requisitos y diseño preliminar)

**Curso:** Ingeniería de Software I · Universidad Rafael Landívar · 2026  
**Categoría:** Base de Datos como Servicio (DBaaS) · PostgreSQL  
**Equipo KoiCloud:** Hugo Escobar · Jason Gutiérrez · Jousé Menendez · Diego Joachin

Paquete de handoff para ingeniería: alcance sellado, documento de entrega, diagramas UML/ER, mockups y propuesta alineada.

Los mockups fijan la **arquitectura de información** de cada pantalla (campos de entrada, campos de salida, tablas y pasos), no la apariencia final del producto: su tema visual es preliminar y la piel definitiva se define aparte, en la guía visual del equipo.

## Compromiso (resumen)

Web + CLI + MCP como clientes delgados sobre la misma API de control plane; ponds PostgreSQL reales en Docker; doble confirmación en mutaciones CLI/MCP; auth mínima de agente para demo de aula; guion de demo con fallback. Seguridad completa de agentes y auto-curación como producto quedan fuera (V2 / fuera de semestre).

Detalle: [`alcance.md`](./alcance.md) · documento: [`ENTREGA-2.md`](./ENTREGA-2.md) · PDF: [`ENTREGA-2.pdf`](./ENTREGA-2.pdf)

## Contenido

```
.
├── README.md                 ← este archivo
├── alcance.md
├── ENTREGA-2.md / .html / .pdf
├── diagramas/                ← fuentes Mermaid
├── renders/                  ← SVG/PNG
├── mockups/                  ← pantallas HTML
└── propuesta/                ← propuesta-koicloud.md / .html / .pdf
```

## Autoría

Entregable del **Equipo KoiCloud**. Los commits del repositorio se firman como equipo (sin trailers de herramientas de IA).
