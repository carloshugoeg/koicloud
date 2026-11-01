# L2 · SQL query run

What the reader sees after clicking Ejecutar. The pond row does not change when read mode rejects a write. A successful read leaves the query in history.

TLC on `sql-query/SqlQuery.cfg` reached 12 states. These rules hold: `ReadOnlyKeepsTheRow`, `SuccessRemembersTheQuery`, `RejectedDidNotWrite`, `NoDeadlock`.

```mermaid
---
title: "Consulta SQL"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: ok
    lg1: bad
    lg2: busy
    lg3: wait
  }
  class lg0 teal
  class lg1 orange
  class lg2 yellow
  class lg3 tan
  s0: Idle
  s1: Running
  s2: Error
  s3: Read-only rejected
  s4: Success
  [*] --> s0
  s0 --> s1: you click Ejecutar
  s1 --> s2: the pond reports an error
  s1 --> s3: read mode rejects the write
  s1 --> s4: the pond returns the rows
  s2 --> s1: you click Ejecutar
  s3 --> s1: you click Ejecutar
  s4 --> s1: you click Ejecutar
  class s0 tan
  class s1 yellow
  class s2 orange
  class s3 orange
  class s4 teal
```

Regenerate from the repo root, with `TLA2TOOLS` pointing at `tla2tools.jar` and `JAVA` at a Java 11+ binary:

```
docs/statechart/level2/sql-query is the spec
statechart SqlQuery.tla --config SqlQuery.cfg --view view.ts --out out
```

The chart hides no steps. It does not model `pond_not_running`. That code is not in the error catalog.
