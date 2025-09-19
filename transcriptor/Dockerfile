FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочих директорий
RUN mkdir -p /app/models /app/data/recordings /app/data/transcripts

WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu118

# Копирование исходного кода
COPY app.py .
COPY transcriptor.py .
COPY models.py .


# Создание volume точек
VOLUME ["/app/models", "/app/data"]

# Открытие порта
EXPOSE 8000

# Запуск приложения
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]