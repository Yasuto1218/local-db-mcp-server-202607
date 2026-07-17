FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY main.py README.md ./

EXPOSE 8000

CMD ["uv", "run", "python", "main.py"]