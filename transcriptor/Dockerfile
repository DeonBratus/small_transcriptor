FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочих директорий
RUN mkdir -p /app/models /app/data/recordings /app/data/transcripts /app/logs

WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка PyTorch с поддержкой CUDA
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

RUN pip install triton==2.1.0
# Копирование исходного кода
COPY app.py .
COPY transcriptor.py .
COPY models.py .

# Создание volume точек
VOLUME ["/app/models", "/app/data"]

# Открытие порта
EXPOSE 8002

# Запуск приложения
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]