# Container for ML training/inference jobs.

FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY ml/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml/ ./ml
COPY data/ ./data
COPY artifacts/ ./artifacts

ENV PYTHONPATH=/app

CMD ["python", "ml/scripts/train_all.py"]
