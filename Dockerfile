FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir fastapi uvicorn python-multipart
RUN mkdir -p backend/data
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]