# Gate checklist

## job polling error doesn't leave the UI stuck in a non-terminal state

A failed `GET /api/v1/ponds/{pond_id}/jobs/{job_id}` must not leave the backups screen showing `queued` or `running` after polling has stopped.

The live test is `job polling error doesn't leave the UI stuck in a non-terminal state` in `apps/web/src/features/ponds/__tests__/backups.test.tsx`.

Template test:

```ts
expect(await screen.findByTestId("restore-job-error")).toHaveTextContent(
  "No pudimos leer el estado de la restauración.",
);
expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
expect(screen.queryByTestId("restore-job-status")).not.toBeInTheDocument();
const readsAtError = jobReads;
await new Promise((resolve) => setTimeout(resolve, 1500));
expect(jobReads).toBe(readsAtError);
```

## user SQL errors return a 4xx, never a 500

A query the user wrote that Postgres rejects, such as bad syntax or a missing table, returns a 4xx. It does not become `internal_error` with status 500. The message is fixed Spanish and does not include the driver text.

The live test is `test_user_sql_error_is_4xx` in `apps/api/tests/test_sql_real_pond.py`. The console shows that failure in `shows a safe message for a user SQL error` in `apps/web/src/features/sql-console/sql-console.test.tsx`.

Template test:

```python
def test_user_sql_error_is_4xx(client, headers, pond_id):
    response = client.post(
        f"/api/v1/ponds/{pond_id}/sql",
        headers=headers,
        json={"query": "SELECT * FROM table_that_is_not_there", "mode": "read"},
    )
    assert 400 <= response.status_code < 500
```

## list endpoints have a default limit and a working cursor

`GET /api/v1/admin/users` returns 50 rows unless `limit` is set. `limit` above 200 is 422. `next_cursor` is an opaque keyset on `(created_at desc, id desc)` and is null on the last page. Plans for the page come from that same query.

The live test is `test_admin_list_users_returns_three_pages_for_120_users` in `apps/api/app/modules/admin/tests/test_admin_users_api.py`. The screen appends the next page in `appends the next page when Cargar más is used` in `apps/web/src/features/admin/admin-users-live-client.test.tsx`.

Template test:

```python
def test_admin_users_page_has_a_limit_and_a_cursor(client, headers):
    first = client.get("/api/v1/admin/users", headers=headers)
    assert first.status_code == 200
    assert len(first.json()["users"]) <= 50
    cursor = first.json()["next_cursor"]
    if cursor is not None:
        second = client.get("/api/v1/admin/users", headers=headers, params={"cursor": cursor})
        assert second.status_code == 200
        first_ids = {user["id"] for user in first.json()["users"]}
        assert first_ids.isdisjoint({user["id"] for user in second.json()["users"]})
    over = client.get("/api/v1/admin/users", headers=headers, params={"limit": 201})
    assert over.status_code == 422
```

## focus stays on Cargar más while the next page loads

Pressing **Cargar más** must not move focus to the document body. The button stays enabled and sets `aria-busy` while the next page is in flight. After that page arrives, and another page remains, focus is still on **Cargar más**.

The live test is `keeps focus on Cargar más while the next page loads` in `apps/web/src/features/admin/admin-users-live-client.test.tsx`. The same name in `e2e/journey/tests/admin-users.spec.ts` checks it in Chromium.

Template test:

```ts
const busy = await screen.findByRole("button", { name: "Cargando…" });
expect(busy).toHaveFocus();
expect(busy).toBeEnabled();
expect(busy).toHaveAttribute("aria-busy", "true");
```

## a failed next page shows an inline error and retries

A failed `GET /api/v1/admin/users` for a cursor must keep the rows already loaded. The screen shows an inline alert, **No pudimos cargar más usuarios.**, and **Reintentar**. **Reintentar** loads that same page. The full-page error is only for a failure that returns no rows.

The live test is `shows an inline error and retries the next page without dropping loaded rows` in `apps/web/src/features/admin/admin-users-live-client.test.tsx`. The same name in `e2e/journey/tests/admin-users.spec.ts` checks it in Chromium.

Template test:

```ts
const alert = await within(page).findByRole("alert");
expect(alert).toHaveTextContent(/No pudimos cargar más usuarios\./);
expect(screen.getByText("QA Uno")).toBeInTheDocument();
await user.click(within(alert).getByRole("button", { name: "Reintentar" }));
expect(await screen.findByText("Cuenta Demo")).toBeInTheDocument();
expect(screen.getByText("QA Uno")).toBeInTheDocument();
```
