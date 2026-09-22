FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
COPY agent ./agent
COPY tests ./tests
RUN uv sync --group dev
CMD ["uv", "run", "python", "-m", "agent.main"]
