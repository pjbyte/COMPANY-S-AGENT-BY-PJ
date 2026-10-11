FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY data ./data

# models + chroma + sqlite live here; mount a volume in production
ENV SENTENCE_TRANSFORMERS_HOME=/data/hf
ENV STORAGE_DIR=/data/storage
VOLUME ["/data"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
