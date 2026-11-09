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

## SQL console role is not a superuser

The console connects as the pond role `koi_console`. That role is not a superuser, owns schema `app`, and is not a member of `pg_read_server_files`, `pg_write_server_files`, or `pg_execute_server_program`. `COPY … PROGRAM` returns 400 `sql_error` with the fixed Spanish message and does not run the program. Read mode still rejects writes. The 1000-row cap and the statement timeout stay as they are.

The live test is `test_copy_program_returns_sql_error_and_runs_nothing` in `apps/api/tests/test_sql_real_pond.py`. The session check is `test_console_session_is_not_superuser_and_not_a_server_file_role`. App-schema reads, writes, and `CREATE TABLE` are `test_console_reads_and_writes_app_data_and_can_create_a_table`.

Template test:

```python
def test_copy_program_is_rejected(client, headers, pond_id):
    response = client.post(
        f"/api/v1/ponds/{pond_id}/sql",
        headers=headers,
        json={
            "query": "COPY (SELECT 1) TO PROGRAM 'touch /tmp/koicloud-copy-program-marker'",
            "mode": "write",
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "sql_error"
```

## concurrent console queries succeed

Ten console queries sent together against one pond all return 200. None of them comes back as `internal_error`, and Postgres does not report `tuple concurrently updated`. The role setup runs once for that pond, or again only when the console password changes, and concurrent callers take the same advisory lock.

The live test is `test_ten_parallel_console_queries_all_succeed` in `apps/api/tests/test_sql_console_role_lifecycle.py`. The unchanged-password check is `test_console_setup_does_not_rerun_when_the_password_is_unchanged`.

Template test:

```python
async def test_ten_parallel_console_queries_all_succeed(pond_id, headers):
    responses = await asyncio.gather(
        *[
            client.post(
                f"/api/v1/ponds/{pond_id}/sql",
                headers=headers,
                json={"query": "SELECT 1 AS n", "mode": "read"},
            )
            for _ in range(10)
        ]
    )
    assert [response.status_code for response in responses] == [200] * 10
```

## no secrets in logs

The console password and the pond password never appear in the Postgres log or in a captured error. The role password is stored as a SCRAM-SHA-256 verifier, so the plaintext is not SQL text.

The live test is `test_console_password_never_reaches_the_log_or_captured_errors` in `apps/api/tests/test_sql_console_role_lifecycle.py`.

Template test:

```python
def test_console_password_is_absent_from_logs(log_text, captured_errors, console_password):
    assert console_password not in log_text
    assert console_password not in captured_errors
```

## console on serial ponds

A pond that already has `SERIAL` or `IDENTITY` columns must accept first-create and a console query. Setup must not run `ALTER SEQUENCE ... OWNER TO koi_console` on a sequence linked to a table column (PG 16 returns `0A000`). Tables and views are re-owned first so ownership cascades.

The live tests are `test_console_setup_succeeds_on_serial_and_identity_pond` and `test_console_query_succeeds_on_pond_with_serial_and_identity` in `apps/api/tests/test_sql_console_role_lifecycle.py`, and `test_first_create_succeeds_on_pond_with_serial_and_identity` in `apps/node-agent/tests/test_console_role_contract.py`.

Template test:

```python
def test_console_setup_succeeds_on_serial_and_identity_pond():
    prepare_fresh_serial_identity_database(database)
    result = run_setup_sql_via_peer_psql(database)
    assert result.returncode == 0, result.stderr
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

## focus never lands on body when a control unmounts

When **Cargar más** leaves the screen because the last page arrived, or the error alert leaves after **Reintentar** loads rows, focus moves to the first newly loaded row. It does not move to the document body. While a page is still loading, focus stays on **Cargar más**.

The live tests are `moves focus to the first new row when the last page loads` and `moves focus to the first new row after Reintentar loads the page` in `apps/web/src/features/admin/admin-users-live-client.test.tsx`. The same names in `e2e/journey/tests/admin-users-focus.spec.ts` check both at 375, 768, and 1440.

## no flaky alert tests: the error-state test passes 20 of 20 runs

The inline error test uses a QueryClient with `retry: false`, so one click shows the alert after exactly one failed request. A failing next page must not sit through several automatic retries before the alert.

The live test is `shows an inline error and retries the next page without dropping loaded rows` in `apps/web/src/features/admin/admin-users-live-client.test.tsx`. `makes exactly one request before the alert when the next page fails` in the same file counts the requests.
