FROM python:3.12-slim
WORKDIR /src
RUN pip install --no-cache-dir uv
COPY packages/job_sanitize ./packages/job_sanitize
COPY apps/api/pyproject.toml apps/api/README.md apps/api/uv.lock ./apps/api/
COPY apps/api/app ./apps/api/app
COPY apps/api/alembic.ini ./apps/api/
COPY apps/api/alembic ./apps/api/alembic
COPY apps/api/tests ./apps/api/tests
WORKDIR /src/apps/api
RUN uv sync --frozen
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
