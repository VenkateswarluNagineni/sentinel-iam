# Scoring/query service image. Streaming + ML extras are layered in later phases.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir -e ".[serve]"

# Placeholder entrypoint until the FastAPI service lands (see ROADMAP phase 9).
CMD ["python", "-c", "import sentinel; print('sentinel-iam', sentinel.__version__)"]
