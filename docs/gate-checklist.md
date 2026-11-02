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
