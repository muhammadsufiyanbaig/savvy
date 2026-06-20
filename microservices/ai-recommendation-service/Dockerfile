FROM python:3.11-slim

WORKDIR /app

# build-essential needed for chromadb (hnswlib C++ extension)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 -M -s /bin/false appuser

COPY shared /app/shared
COPY ai-recommendation-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai-recommendation-service/app /app/app

RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8005

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
