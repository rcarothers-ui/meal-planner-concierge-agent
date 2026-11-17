FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY meal_planner_agent/ ./meal_planner_agent/
COPY evals/ ./evals/
COPY pyproject.toml README.md ./

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["adk", "api_server", "meal_planner_agent", "--port", "8080", "--host", "0.0.0.0"]
