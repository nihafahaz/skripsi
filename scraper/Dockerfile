FROM python:3.10-slim

# Install system dependencies, Chromium, ChromeDriver, and fonts
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    fonts-liberation \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium and ChromeDriver
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

# Install HANYA dependency yang dibutuhkan scraper (tanpa TensorFlow, dll)
COPY scraper/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy HANYA subdirektori yang dibutuhkan scraper dari app/
# (menghindari app/__init__.py yang import seluruh FastAPI router + ML deps)
RUN mkdir -p ./app/core ./app/utils ./app/db
COPY app/core/ ./app/core/
COPY app/utils/ ./app/utils/
# Hanya session.py dari app/db (bukan repositories/ yang ada ML imports)
COPY app/db/session.py ./app/db/session.py
# Buat __init__.py kosong agar Python mengenali package-nya
RUN touch ./app/__init__.py ./app/db/__init__.py

# Copy modul scraper/
COPY scraper/ ./scraper/

# Default: jalankan scraper sekali (untuk docker compose run --rm scraper)
CMD ["python", "scraper/main.py"]
