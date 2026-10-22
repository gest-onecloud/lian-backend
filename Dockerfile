FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN mkdir -p backend/data
ENV LIAN_PORT=8000
EXPOSE 8000
CMD ["python", "backend/server.py"]