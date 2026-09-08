FROM python:3.11-slim

# Tesseract OCR engine + OpenCV runtime libs are required at runtime (not pip-installable)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY samples ./samples
COPY streamlit_app.py .

RUN mkdir -p data/uploads data/results

# Streamlit UI is the primary demo surface (used for Hugging Face Docker Spaces / Render).
# To run the FastAPI service instead, override the CMD:
#   docker run -p 8000:8000 <image> uvicorn app.main:app --host 0.0.0.0 --port 8000
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
