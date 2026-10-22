FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN mkdir -p backend/data
RUN pip install --no-cache-dir fastapi uvicorn python-multipart tzdata
ENV LIAN_PORT=8000
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["python", "run.py"]
