FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 -M -s /bin/false appuser

COPY shared /app/shared
COPY notification-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY notification-service/app /app/app
COPY notification-service/alembic /app/alembic
COPY notification-service/alembic.ini /app/alembic.ini

RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8006

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
