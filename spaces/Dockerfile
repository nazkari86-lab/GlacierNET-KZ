# Gradio demo — build from repo root:
#   docker build -f spaces/Dockerfile -t glacierkz-demo .

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt spaces/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r spaces/requirements.txt

ENV PYTHONPATH=/app
ENV GRADIO_ROOT_PATH=/demo
ENV DEMO_PORT=7860

COPY src/ /app/src/
COPY spaces/app.py /app/spaces/app.py
RUN mkdir -p /app/models

WORKDIR /app/spaces

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:7860/demo/ || curl -sf http://localhost:7860/ || exit 1

CMD ["python", "app.py"]
