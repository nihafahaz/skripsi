FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements or directly install
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    mysql-connector-python \
    pymysql \
    sqlalchemy \
    pandas \
    openpyxl \
    tensorflow \
    numpy \
    reportlab \
    joblib \
    python-dotenv

# Copy application files
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
