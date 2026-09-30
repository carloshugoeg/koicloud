FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
COPY agent ./agent
COPY tests ./tests
RUN uv sync --frozen
CMD ["uv", "run", "python", "-m", "agent.main"]
