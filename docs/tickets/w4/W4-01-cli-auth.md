---
id: W4-01
workstream: W4
persona: Diego
estado: en-revision
rama: w4-cli-auth
epica: "E9-01"
sprint: S2
pr:
depends_on:
---

# [W4-01] CLI `login`, `logout`, `whoami`

## Qué se ve

Comandos básicos de sesión de la CLI. El resultado visible es un archivo de sesión en `~/.config/koicloud/config.json`, `whoami` funcional y logout que borra la sesión.

## Entradas ya decididas (no se cambian)

- Comandos: `koicloud login`, `koicloud logout`, `koicloud whoami`.
- API: `POST /auth/login`, `POST /auth/logout`, `GET /me`.
- La sesión se guarda en `~/.config/koicloud/config.json` con permisos `0600`.
- Se reutiliza `apps/cli/koicloud_cli/client.py` y el ejemplo `MockTransport` que deja W1.
  No necesitás `email_tokens`. Login pega a `POST /auth/login`.
- Sin sesión, cualquier comando sale con código `1` y el mensaje “Primero corré `koicloud login`” (`api-surface.md` §5). El `2` de la matriz de inputs no aplica.

## Criterios de aceptación

1. `login` guarda la sesión con permisos `0600`.
2. `whoami` imprime el usuario actual usando el contrato de `GET /me`.
3. `logout` limpia el archivo o las credenciales guardadas.
4. Hay pruebas con `CliRunner` y `respx`/`MockTransport` para login, whoami y logout.
5. Un comando autenticado sin sesión (p.ej. `whoami`) termina con exit `1` y el mensaje de §5.

## No tocar

- `apps/cli/koicloud_cli/client.py` y `config.py` salvo la API pública ya congelada por W1.
- `apps/api/app/commands/**`.
- `apps/node-agent/**`.
- `apps/api/app/mcp/{server.py,gate.py,prompt.py}` y cualquier tool mutante.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.
