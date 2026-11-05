# Architect candidate A — manual TanStack Query (`enabled: false`) + view-state union

Issue: #207 · Branch: `w1-207-pond-table-explorer` · Angle: **manual query + explicit `SchemaViewState`**

---

## Problem

Pond detail (`apps/web/src/features/ponds/detail-page.tsx`, ~232 lines) must show a **Tablas** explorer fed by `GET /api/v1/ponds/{id}/schema` (OpenAPI types already in `schema.d.ts` from S5). The demo needs a **Recargar** control that refetches only on press—no polling, no SSE, no `refetchOnWindowFocus`. Existing pond hooks poll only for transient lifecycle states; there is no schema hook, no MSW `/schema` route, and the page is already near the 250-line guard. Non-running ponds raise `pond_busy` with API message `"El pond no está en ejecución"`, but `problemToMessage` maps that code to the generic catalog string `"Ese pond ya tiene una operación en curso."`—so the UI must not rely on that catalog string for the “pond not running” state. Spanish UI, existing design tokens, a11y (aria-busy on Recargar, focus retained, polite live region), no koi over tables/data, no contract edits.

## Usage (caller's view)

### README

`PondTableExplorer` is a self-contained section on pond detail. Pass the already-loaded `Pond`. It owns the schema query, view-state derivation, expand/collapse, Recargar, and all explorer states. The detail page does not call the schema API.

```tsx
// apps/web/src/features/ponds/detail-page.tsx (happy path return)
import { PondTableExplorer } from "@/features/ponds/pond-table-explorer";

// …after ConnectionCard, before PondRiskZone…
<ConnectionCard … />
<PondTableExplorer pond={pond} />
<PondRiskZone … />
```

### Call site 1 — mount on detail

```tsx
// Only prop: the pond already fetched by useGetPond.
// Explorer decides idle / loading / empty / ready / error / not-running.
<PondTableExplorer pond={pond} />
```

### Call site 2 — Recargar (inside explorer)

```tsx
const { query, reload } = usePondSchema(pond.id);

<button
  type="button"
  data-testid="schema-reload"
  aria-busy={query.isFetching || undefined}
  disabled={pond.observed_state !== "running" || query.isFetching}
  onClick={() => {
    void reload(); // query.refetch(); focus stays on this button
  }}
>
  Recargar
</button>
```

### Call site 3 — render from derived view state

```tsx
const view = deriveSchemaViewState(pond, query);

switch (view.kind) {
  case "pond_not_running":
    return <p data-testid="schema-not-running">El pond no está en ejecución…</p>;
  case "idle":
    return <p>Pulsá Recargar para listar las tablas.</p>;
  case "loading":
    return <div data-testid="schema-loading" className="…pulse…" />;
  case "empty":
    return <p data-testid="schema-empty">Esta pond aún no tiene tablas</p>;
  case "ready":
    return <SchemaTableList tables={view.tables} />;
  case "error":
    return (
      <div data-testid="schema-error">
        <p>{view.message}</p>
        <button data-testid="schema-retry" onClick={() => void reload()}>
          Reintentar
        </button>
      </div>
    );
}
```

Invariant for callers: **one** way to load schema (`usePondSchema` → `reload` / Recargar / Reintentar). Never `apiClient.GET` from a component. Never auto-fetch on mount.

## Shape

### Types (derived from usage)

```ts
// apps/web/src/api/hooks/ponds.ts  (aliases next to existing Pond / Connection)
import type { components } from "@/api/schema";

export type PondSchema = components["schemas"]["PondSchemaResponse"];
export type PondTable = components["schemas"]["PondTableOut"];
export type PondColumn = components["schemas"]["PondColumnOut"];

/** Explicit UI state. Single source of truth; do not mirror in useState. */
export type SchemaViewState =
  | { kind: "pond_not_running" }
  | { kind: "idle" } // running, never successfully fetched this session cache
  | { kind: "loading" } // fetching with no usable prior tables to show
  | { kind: "empty" } // fetched; tables.length === 0
  | { kind: "ready"; tables: PondTable[] }
  | { kind: "error"; message: string; code?: string };

export function deriveSchemaViewState(
  pond: Pick<Pond, "observed_state">,
  query: {
    isFetched: boolean;
    isFetching: boolean;
    isError: boolean;
    error: unknown;
    data: PondSchema | undefined;
  },
): SchemaViewState {
  // not implemented — pure; order below is load-bearing
  // 1. if pond.observed_state !== "running" → pond_not_running
  //    (ignore stale cache so stopped ponds never show table chrome)
  // 2. if isFetching && !data?.tables → loading
  // 3. if isError && !isFetching → error via problemToMessage + optional code
  // 4. if !isFetched → idle
  // 5. if tables.length === 0 → empty
  // 6. → ready { tables }
  throw new Error("not implemented");
}

export function usePondSchema(pondId: string | undefined) {
  // not implemented
  // useQuery({
  //   queryKey: ["ponds", pondId, "schema"],
  //   enabled: false,                    // NEVER auto-run
  //   refetchOnWindowFocus: false,       // belt; AppProviders already false
  //   refetchOnReconnect: false,
  //   refetchInterval: false,
  //   staleTime: Infinity,               // cache until explicit reload
  //   retry: false,                      // manual Reintentar owns retry UX
  //   queryFn: async () => {
  //     const { data, error } = await apiClient.GET(
  //       "/api/v1/ponds/{pond_id}/schema",
  //       { params: { path: { pond_id: pondId as string } } },
  //     );
  //     if (error || !data) throw new ApiError(error);
  //     return data; // PondSchemaResponse
  //   },
  // })
  // return { query, reload: () => query.refetch() }
  throw new Error("not implemented");
}
```

```tsx
// apps/web/src/features/ponds/pond-table-explorer.tsx
type PondTableExplorerProps = {
  pond: Pond; // domain Pond alias from hooks — not raw OpenAPI path types
};

export function PondTableExplorer({ pond }: PondTableExplorerProps): JSX.Element {
  // not implemented
  // const { query, reload } = usePondSchema(pond.id);
  // const view = deriveSchemaViewState(pond, query);
  // expand state: Set<string> of table.name (local only; not synced to URL)
  // Recargar: aria-busy while query.isFetching; keep focus on button after click
  // polite live region updates on settle (ready/empty/error)
  // no koi, no dark:, tokens from index.css only
  throw new Error("not implemented");
}

// Internal presentational helpers in the same file (or pond-table-list.tsx if
// explorer exceeds ~200 lines). Not exported from a barrel.
function SchemaTableList(props: {
  tables: PondTable[];
  expanded: ReadonlySet<string>;
  onToggle: (name: string) => void;
}): JSX.Element {
  throw new Error("not implemented");
}
```

### Data flow

```
PondDetailPage
  └─ useGetPond → pond
  └─ <PondTableExplorer pond={pond} />
        ├─ usePondSchema(pond.id)     // enabled:false; reload = refetch
        ├─ deriveSchemaViewState(...) // pure; encodes all UI branches
        ├─ Recargar / Reintentar → reload()
        └─ SchemaTableList            // expandable rows; tabular-nums rows
```

Call chain length: **page → explorer → hook** (≤3 files). Derivation is pure and colocated with the hook so tests can import it without rendering.

### Invariants encoded in types / structure

| Invariant | Encoding |
|-----------|----------|
| No auto-fetch | `enabled: false`; only `reload()` / `refetch()` |
| No focus refetch | explicit `refetchOnWindowFocus: false` on this query |
| No polling | `refetchInterval: false`; never share pond poll keys |
| Not-running UX | `SchemaViewState.pond_not_running` from `observed_state`, not from catalog `pond_busy` string |
| Empty copy | only after successful fetch with `tables.length === 0` (`kind: "empty"`) |
| One load path | sole public API: `usePondSchema` + `PondTableExplorer` |
| Wire types stay at boundary | `queryFn` returns `PondSchema`; UI consumes `SchemaViewState` / `PondTable` |
| Page line budget | explorer extracted; detail-page adds ~3 lines |

### Interface depth

Public surface is **two exports** (`usePondSchema`, `PondTableExplorer`) plus one pure helper (`deriveSchemaViewState`) for tests. Callers pass a `Pond` and get Recargar semantics, all six UI states, a11y, and expand behavior. Complexity pulled into the callee: query flags, message mapping, expand set, live region text. Detail page does not learn query status flags.

Deliberately **does not**: poll; SSE; prefetch on mount; put schema in URL; show koi; edit contracts; invent tab “Tablas” (stays on Resumen section of detail); fix global `pond_busy` catalog (open question).

### Module map

| Path | Role |
|------|------|
| `apps/web/src/api/hooks/ponds.ts` | Add `PondSchema` / `PondTable` / `PondColumn` aliases, `SchemaViewState`, `deriveSchemaViewState`, `usePondSchema` |
| `apps/web/src/features/ponds/pond-table-explorer.tsx` | Section UI: header “Tablas”, Recargar, live region, state branches, expandable list |
| `apps/web/src/features/ponds/detail-page.tsx` | Mount `<PondTableExplorer pond={pond} />` after `ConnectionCard` |
| `apps/web/src/mocks/fixtures.ts` | `schema: PondSchema` fixture from OpenAPI example (`public.orders`, …) |
| `apps/web/src/mocks/handlers.ts` | `GET ${API_ROOT}/ponds/:pondId/schema` → fixture; optional 409 `pond_busy` override in tests |
| `apps/web/src/features/ponds/__tests__/detail.test.tsx` | Integration: Recargar fires GET once; empty; error+Reintentar; not-running; no second GET without click |
| `apps/web/src/features/ponds/__tests__/pond-table-explorer.test.tsx` *(optional split)* | Focus retention, aria-busy, live region, expand columns |
| `apps/web/src/api/hooks/__tests__/derive-schema-view-state.test.ts` *(optional)* | Pure union cases |
| e2e stubs (`e2e/journey`, `e2e/pond-lifecycle`) | Stub `/schema` if those journeys hit detail; keep widths 375/768/1440 |

**Do not touch:** `packages/contracts/**`, `schema.d.ts` (already has types), `apps/api/**` (unless fixing catalog later under separate decision).

### Concrete test IDs

| `data-testid` | Element |
|---------------|---------|
| `pond-table-explorer` | Section root |
| `schema-reload` | Recargar button |
| `schema-live` | `aria-live="polite"` region |
| `schema-idle` | Pre-fetch prompt |
| `schema-loading` | Loading skeleton (first fetch, no prior data) |
| `schema-empty` | “Esta pond aún no tiene tablas” |
| `schema-error` | Error panel |
| `schema-retry` | Reintentar |
| `schema-not-running` | Not-running copy |
| `schema-table-list` | List/table container when ready |
| `schema-table` | Per-row; also `data-table-name={table.name}` |
| `schema-estimated-rows` | Row estimate cell |
| `schema-columns` | Expanded column table for a row |
| `schema-column` | Column row (`data-column-name`) |

### UI copy (Spanish)

- Heading: **Tablas**
- Support: “Esquema del pond. Actualizá con Recargar después de crear tablas.”
- Button: **Recargar** / busy: keep label Recargar + `aria-busy="true"` (no spinner page)
- Idle: “Pulsá Recargar para listar las tablas.”
- Empty: “Esta pond aún no tiene tablas”
- Not running: “El pond no está en ejecución. Arrancalo para explorar el esquema.”
- Error + **Reintentar**
- Columns headers: Nombre · Tipo · Nulo (`Sí` / `No`)
- Estimated rows: “filas (est.)” with `tabular-nums` right-aligned
- Live region examples: “2 tablas cargadas.” / “Sin tablas.” / error message

### Expand pattern

Prefer native `<details>` / `<summary>` per table row (name + estimated rows on summary; column grid inside). No cards. Hairline `border-line`, header `bone-sunk`, row height ~40 px — match `BackupsTable` density. One expand set owned by the explorer; toggling does not refetch.

### A11y checklist for implementer

1. Recargar: `aria-busy={isFetching || undefined}`; after click, `button.focus()` if blur occurred (normally stays).
2. Recargar disabled when `observed_state !== "running"` or while fetching.
3. `aria-live="polite"` region (`schema-live`) announces settle outcomes only (not every keystroke).
4. Expanded row: if not using `<details>`, toggle needs `aria-expanded` + `aria-controls`.
5. Errors: text + glyph/border, not color alone.
6. No koi in this section (detail page may still show provisioning koi strip elsewhere).

### Red-flag screen (candidate A)

| Flag | Status |
|------|--------|
| Shallow module | Pass — one prop in; six states + fetch policy hidden |
| Information leakage | Pass — wire `paths` not on props; aliases from `components["schemas"]` |
| Temporal decomposition | Pass — derive + render owned together; no load/validate/save modules |
| Pass-through method | Pass — `reload` is a named policy alias over `refetch`, not a second API |
| Split ownership | Pass — query cache owned by TanStack; expand Set owned by explorer; view state derived |
| Two ways to do one task | Pass — forbid component-level `apiClient` for schema |
| Importable internals | Pass — list helpers file-private; only hook + explorer + derive exported |
| Hand-synced list | Pass — empty string / view kinds listed once in `deriveSchemaViewState` |

## Synthesis decision

Pending parent synthesis. This is **candidate A** (manual `enabled: false` + `SchemaViewState` union). Not the arena base until compared with candidate B (`fetchQuery` / imperative angle).

## Tradeoffs accepted

- We accept **no schema until first Recargar** in exchange for a hard guarantee that GET `/schema` never fires from mount, focus, or reconnect.
- We accept **client-side `observed_state` gating** for not-running copy in exchange for not depending on the mismatched `pond_busy` catalog string for the primary UX.
- We accept **`staleTime: Infinity`** on schema cache in exchange for stable UI between manual reloads (stale tables remain until Recargar).
- We accept **native `<details>`** in exchange for less custom a11y code vs a fully controlled expand button pattern.
- We accept **leaving `problemToMessage` / CATALOG unchanged** in this ticket in exchange for not widening scope into global error-copy CCR; race errors may still show the generic busy string until a follow-up.
- We accept mounting the explorer on **Resumen** (not a new tab) in exchange for matching issue #207 scope and avoiding `PondTabs` contract churn.

## Alternatives considered

1. **`enabled: pond.observed_state === "running"` with auto-fetch on mount** — hides “press Recargar to load” but violates “refetch on press only” / demo narrative that Recargar is the refresh gesture; exposes automatic network policy to every detail visit. Lost on policy fit.
2. **Imperative `queryClient.fetchQuery` only (no `useQuery`)** — smaller subscription surface, but callers must reimplement loading/error/cache observation; shallower module, more state in the component. Lost on interface depth (candidate B explores this shape).
3. **Pass raw `UseQueryResult` into a dumb presentational list** — page coordinates flags + empty + error; large interface, temporal split across page and child. Lost as shallow + split ownership.
4. **New “Tablas” route/tab** — clearer IA long-term, but out of issue scope and touches `PondTabs` + router; more files for the same GET. Lost on scope.

## Open questions and risks

1. Should the first paint auto-load once when `observed_state === "running"`, with Recargar only for subsequent refresh, or is **press-only including first load** the accepted demo script?
2. When a mid-flight stop yields `pond_busy`, should the explorer special-case that code to show `"El pond no está en ejecución"` (API message) instead of the catalog busy string—without changing `lib/errors.ts` globally?
3. After stop→start, should Recargar clear the previous schema cache (`removeQueries`) before refetch so a failed reload cannot flash old tables under a new running pond?
4. Do Playwright journeys that open pond detail need a `/schema` route stub immediately, or only Vitest/MSW for this ticket?
5. Is expandable column `default` (present on `PondColumnOut`) in scope for the grid, or name/type/nullable only per issue text?

## Next implementation step

Add `usePondSchema` + `deriveSchemaViewState` in `apps/web/src/api/hooks/ponds.ts` with `enabled: false` and a Vitest table over the six `SchemaViewState` cases, then mount a stub `PondTableExplorer` on the detail page so Recargar asserts a single MSW `/schema` hit.
