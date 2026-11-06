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

## job errors never echo raw command output

A failed job returns only a closed code and a fixed Spanish message in `last_error`. Raw psql or command output, dump rows and passwords never reach the jobs API. The server log keeps only `pg_dump:` / `psql:` ERROR lines (no DETAIL/CONTEXT/COPY rows), capped at 500 characters. Sentry gets only the code plus job id (and pond id). Old rows are sanitized on read.

The live tests are in `apps/api/tests/test_job_error_sanitize.py`.

Template test:

```python
def test_failed_job_hides_command_output(client, headers, pond_id, failed_job_id):
    body = client.get(f"/api/v1/ponds/{pond_id}/jobs/{failed_job_id}", headers=headers).json()
    assert "ROWVALUE" not in body["last_error"]
    assert "postgresql://" not in body["last_error"]
```
