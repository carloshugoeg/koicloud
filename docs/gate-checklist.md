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

## restore leaves the backup row count

A backup of a table with 7 rows, restored 3 times, still has those 7 rows. A restore that fails after the load has started leaves the rows the pond had before that attempt, and the job ends `failed`.

The live tests are `test_restore_three_times_leaves_seven_rows` and `test_restore_failure_keeps_previous_rows` in `apps/node-agent/tests/test_restore_replaces.py`.

Template test:

```python
def test_restore_three_times_leaves_seven_rows(tmp_path):
    rows = ["1", "2", "3", "4", "5", "6", "7"]
    cluster, driver = pond_with_items(tmp_path, rows)
    driver.dump("inventario-demo", "bak7")
    for index in range(3):
        report = run_restore(driver, f"job_restore_{index}", "bak7")
        assert report.status == "succeeded"
        assert item_rows(cluster) == rows
```

## restore replaces every non-system schema

A pond with schema `inv` and tables in both `public` and `inv`, restored 3 times, keeps those row counts. The job does not fail because the schema already exists.

The live test is `test_restore_replaces_every_non_system_schema` in `apps/node-agent/tests/test_restore_replaces.py`.

Template test:

```python
def test_restore_replaces_every_non_system_schema(tmp_path):
    rows = ["1", "2", "3", "4", "5", "6", "7"]
    cluster, driver = pond_with_items(tmp_path, rows)
    add_schema(cluster, "inv", "stock", rows)
    driver.dump("inventario-demo", "bak-inv")
    for index in range(3):
        report = run_restore(driver, f"job_inv_{index}", "bak-inv")
        assert report.status == "succeeded"
        assert item_rows(cluster) == rows
        assert schema_rows(cluster, "inv", "stock") == rows
```

## restore grants no CREATE on public

After a restore, a role that is not the owner cannot CREATE in `public`.

The live test is `test_restore_denies_create_in_public_to_non_owner` in `apps/node-agent/tests/test_restore_replaces.py`.

Template test:

```python
def test_restore_denies_create_in_public_to_non_owner(tmp_path):
    cluster, driver = pond_with_items(tmp_path, ["1"])
    driver.dump("inventario-demo", "bak-acl")
    report = run_restore(driver, "job_acl", "bak-acl")
    assert report.status == "succeeded"
    assert create_as(cluster, "stranger", "public", "probe") is not None
```

## restored objects belong to the pond owner role

After a restore, the restored tables and schemas are owned by `koi_console`, the non-superuser role W1-191 uses, not by `postgres`.

The live test is `test_restored_tables_and_schemas_owned_by_koi_console` in `apps/node-agent/tests/test_restore_replaces.py`.

Template test:

```python
def test_restored_tables_and_schemas_owned_by_koi_console(tmp_path):
    cluster, driver = pond_with_items(tmp_path, ["1"])
    add_schema(cluster, "inv", "stock", ["1", "2"])
    driver.dump("inventario-demo", "bak-own")
    report = run_restore(driver, "job_own", "bak-own")
    assert report.status == "succeeded"
    assert schema_owner(cluster, "public") == "koi_console"
    assert schema_owner(cluster, "inv") == "koi_console"
    assert table_owner(cluster, "public", "items") == "koi_console"
    assert table_owner(cluster, "inv", "stock") == "koi_console"
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
