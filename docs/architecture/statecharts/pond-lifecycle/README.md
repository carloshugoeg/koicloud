# Pond lifecycle statechart (Wave B1)

Agreed behavior for stop, start, and delete-with-pre_delete-backup.

| File | Role |
|------|------|
| `pond-lifecycle.mmd` | Hand chart (regions desire × observed) |
| `PondLifecycle.tla` | Guarded TLA+ model (source of truth for rules) |
| `PondLifecycle.cfg` | Invariants |
| `PondLifecycle.map.mjs` | Reader labels |
| `summary.json` | Last TLC run counts |

Readable diagram for reviewers:

- Mermaid: `docs/architecture/diagrams/20-pond-lifecycle-stop-start-delete.mmd`
- PNG: `docs/architecture/diagrams/20-pond-lifecycle-stop-start-delete.png`

Regenerate (needs `mise` + network once for TLC):

```bash
export PATH="$HOME/.local/bin:$PATH"
node <statechart-skill>/scripts/statechart.mjs from-chart pond-lifecycle.mmd --png
cp PondLifecycle-statechart/chart.mmd ../../diagrams/20-pond-lifecycle-stop-start-delete.mmd
cp PondLifecycle-statechart/chart.png ../../diagrams/20-pond-lifecycle-stop-start-delete.png
```

Invariants that must stay green: `GoneWhileWantedOn`, `GoneWhileWantedOff`,
`OnlineAfterYouRemovedIt`, `OfflineAfterYouRemovedIt`, `GoneOnlyWhenRemoved`.
