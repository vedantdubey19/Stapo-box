FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and data
COPY . .

# Ensure start script is executable
RUN chmod +x /app/start.sh

# Expose ports
EXPOSE 8501 8000

ENV BACKEND_HOST="127.0.0.1"
ENV BACKEND_PORT="8000"
ENV BACKEND_URL="http://127.0.0.1:8000"

ENTRYPOINT ["/app/start.sh"]
