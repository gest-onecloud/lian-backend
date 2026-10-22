FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN mkdir -p backend/data
RUN echo '{}' > backend/data/public_priors.json || true
RUN pip install --no-cache-dir requests fastapi uvicorn python-multipart tzdata
ENV LIAN_PORT=8000
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["python", "run.py"]
