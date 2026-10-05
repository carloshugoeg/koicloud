# Reiniciar el node-agent

El agente **no** va en `docker-compose.prod.yml`. Corre con systemd para usar
`/var/run/docker.sock` y hablar con la API por loopback
(`http://127.0.0.1:8000/internal/v1`). Caddy bloquea `/internal/*` desde fuera.

Unit versionada: `infra/koicloud-agent.service`.

```bash
sudo cp /srv/koicloud/infra/koicloud-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now koicloud-agent
sudo systemctl restart koicloud-agent
sudo systemctl status koicloud-agent --no-pager
```

Requiere `infra/env/prod.env` en el host (`NODE_ID`, `NODE_TOKEN`, `AGENT_MODE=docker`).
Sin host provisionado no hay máquina que arrancar: ver [`deploy.md`](./deploy.md).
