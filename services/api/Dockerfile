FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin poppler-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY atlas ./atlas
RUN useradd --create-home atlas
USER atlas
CMD ["sh", "-c", "uvicorn atlas.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
