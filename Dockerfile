FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8010
ENV LIAN_PORT=8010
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "backend.server"]