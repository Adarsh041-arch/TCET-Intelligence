FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser for PDF generation
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium && \
    rm -rf /var/lib/apt/lists/*

# Copy application source code
COPY app ./app
COPY config.json .

EXPOSE 8000

# Launch uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
