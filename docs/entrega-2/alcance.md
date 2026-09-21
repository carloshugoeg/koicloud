# Alcance comprometido — KoiCloud

**Categoría:** Base de Datos como Servicio (DBaaS) · PostgreSQL  
**Superficies:** Web + CLI + MCP (adaptadores delgados sobre la misma API de control plane)  
**Equipo:** Equipo KoiCloud — Hugo Escobar, Jason Gutiérrez, Jousé Menendez, Diego Joachin

No hay división en núcleo / deseable / ambicioso. Lo que aparece abajo es el compromiso completo del semestre. Lo que no aparece está en *Fuera de alcance*.

## Compromiso

1. **Cuentas:** registro, verificación de correo, recuperación de contraseña, inicio de sesión con JWT + refresh; roles Cliente y Administrador.
2. **Suscripciones:** catálogo Sandbox / Micro / Pro (nombre, descripción, precio, vigencia); contratación con pago simulado; historial; renovación y cancelación.
3. **Catálogo DBaaS:** crear, consultar estado, obtener cadena de conexión y eliminar instancias PostgreSQL 16 en contenedores Docker reales.
4. **Configuración básica al crear:** nombre del pond, versión del motor (16), plan asociado a la suscripción.
5. **Consola SQL en el navegador:** modo lectura por defecto, timeout y límite de filas; modo escritura con confirmación.
6. **Respaldos:** copia diaria automática y restauración bajo demanda (`pg_dump` / `pg_restore`).
7. **Uso:** horas de instancia y almacenamiento estimados a partir de muestras del agente; vista mensual simple.
8. **Administración:** el Administrador consulta usuarios, suscripciones e instancias.
9. **Arquitectura:** monolito modular FastAPI (control plane) + node-agent (data plane) + PostgreSQL interno; cola de trabajos en la misma base; un solo nodo VPS.
10. **Tres superficies, una API:** interfaz web, CLI (`koicloud`) y servidor MCP como clientes delgados que invocan los mismos endpoints/comandos del control plane — sin lógica de negocio duplicada.
11. **Doble confirmación** en acciones mutantes/destructivas desde CLI y MCP: el cliente propone la operación; el sistema exige un segundo paso con token de confirmación antes de ejecutar (crear/eliminar pond, SQL write, etc.).
12. **Auth mínima de agente (demo de aula):** URL de acceso al endpoint MCP/agente protegida por contraseña o secreto compartido simple (gate básico). Suficiente para demostrar el flujo; **no** es un producto de seguridad.
13. **Demo MCP fiable:** guion happy-path (lenguaje natural en Claude/Cursor → listar/crear/eliminar ponds, ops SQL) más respaldo si el LLM en vivo falla (script/replay determinista).

## Fuera de alcance

- Infraestructura declarativa (`cloud.yaml` / `koicloud apply`) como producto.
- Seguridad completa de agentes = **V2 fuera de semestre:** OAuth 2.1, llaves API con scopes finos, tope de gasto por agente, auditoría forense, 2FA.
- Auto-curación como garantía de producto o demostración de caos (recuperación automática ante `docker kill`).
- Validación empírica de hipótesis de precio o de factura local con NIT (requiere usuarios reales pagando).
- Otros motores (MySQL, MongoDB), branching, réplicas, connection pooler, extensiones.
- Organizaciones / equipos / invitaciones.
- Cobro real, pasarelas de pago, facturación electrónica ante la SAT, SLA.
- Alta disponibilidad, multi-nodo, migración de instancias.
- Roles Soporte técnico y Operador de infraestructura; página pública de estado; panel de flota.
- Sandbox sin registro (puede explorarse si sobra tiempo; no forma parte del compromiso).

## Problemas que el proyecto sí aborda

| Problema | Cómo se verifica |
|---|---|
| Poner en marcha Postgres exige operación que el cliente no quiere hacer | Tiempo desde “crear pond” hasta URI utilizable |
| El estado del servicio es opaco | El panel (y CLI/MCP) muestran estado y health del contenedor |
| No hay cliente SQL a mano | Consola web / tool MCP ejecutan `SELECT` y muestran filas |
| Hay que demostrar suscripción/pago académicos | Flujo simulado con historial e factura PDF simple |
| Un agente o CLI debe operar sin reinventar la API | Misma API; doble confirmación en mutaciones; demo con guion |

## Hipótesis de negocio (no comprometidas)

El posicionamiento comercial (hueco de precio ~USD 5 vs. ~USD 25; factura con NIT) orienta el catálogo, pero **no** se evalúa ni se promete como resultado del semestre.

## Tono hacia el catedrático

Showcase de capacidad técnica: tres fachadas delgadas sobre un control plane. **No** se presenta como “plataforma agéntica” ni como producto de seguridad para agentes.
