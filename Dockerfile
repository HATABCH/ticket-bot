# /Users/mac/projects/ticket_bot/Dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app

# Создаем директорию для базы данных
RUN mkdir -p /app/app/database/data

CMD ["python", "-m", "app.main"]
