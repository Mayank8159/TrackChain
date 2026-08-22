# =============================================================================
# Production Cloud / HF Spaces backend image.
# Optimized for ONNX inference (no PyTorch/Ultralytics) to reduce size.
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.cloud.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO
ENV ONNX_MODE=true

EXPOSE 7860

# Single worker for SSE / WebSocket consistency. Timeout increased for long-running inferences.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--timeout-keep-alive", "120"]
