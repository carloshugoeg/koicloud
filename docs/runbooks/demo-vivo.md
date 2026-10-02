# Demo en vivo (puntero)

Guion versionado: **`scripts/demo-vivo.sh`** desde la raíz del repo.

```bash
bash scripts/demo-vivo.sh preflight
bash scripts/demo-vivo.sh a          # pond fijo :15432
bash scripts/demo-vivo.sh b          # control plane + DockerDriver
bash scripts/demo-vivo.sh all        # reset → A → B
```

Detalle de producto / hostnet: [`local-pond.md`](./local-pond.md).
Onboarding de agentes (Mac quirks): [`../agent-onboarding.md`](../agent-onboarding.md) §9.

No inventar VPS. Mac Docker Desktop usa el compose default; el overlay hostnet es escape
hatch de cloud VM.
