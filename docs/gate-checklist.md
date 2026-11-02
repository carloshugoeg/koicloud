# Gate checklist

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
