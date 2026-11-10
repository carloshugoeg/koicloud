FROM python:3.12-slim
WORKDIR /src
RUN pip install --no-cache-dir uv
COPY packages/job_sanitize ./packages/job_sanitize
COPY apps/node-agent/pyproject.toml apps/node-agent/uv.lock ./apps/node-agent/
COPY apps/node-agent/agent ./apps/node-agent/agent
COPY apps/node-agent/tests ./apps/node-agent/tests
WORKDIR /src/apps/node-agent
RUN uv sync --frozen
CMD ["uv", "run", "python", "-m", "agent.main"]
