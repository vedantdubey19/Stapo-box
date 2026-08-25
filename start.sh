#!/usr/bin/env bash
set -e

echo "🚀 Starting StapuBox FastAPI Backend on port 8000..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

echo "⏳ Waiting for Backend health check..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy!"
    break
  fi
  sleep 0.5
done

# Set FRONTEND_PORT (supports cloud environments like Render/HuggingFace/Railway which set $PORT)
FRONTEND_PORT=${PORT:-8501}

echo "🎨 Starting Streamlit Story Studio on port ${FRONTEND_PORT}..."
exec streamlit run frontend/app.py \
  --server.port "${FRONTEND_PORT}" \
  --server.address 0.0.0.0 \
  --server.headless true
