from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.background import BackgroundTasks
import os
import tempfile
from transcriptor import Transcriptor
import torch
from models import TranscriptionRequest, TranscriptionResponse, TranscriptionSegment

app = FastAPI(
    title="Audio Transcription API",
    description="API для транскрибации аудио с разделением по спикерам с использованием GPU",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


transcriptor = None

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    global transcriptor
    try:
        transcriptor = Transcriptor(use_gpu=True, is_advanced_segmentation=False)
        print("Транскрибатор успешно инициализирован")
        if torch.cuda.is_available():
            print(f"GPU доступен: {torch.cuda.get_device_name(0)}")
        else:
            print("GPU не доступен, используется CPU")
    except Exception as e:
        print(f"Ошибка инициализации: {e}")
        raise

@app.get("/")
async def root():
    return {"message": "Audio Transcription API", "status": "running"}

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    num_speakers: int = 4,
    use_gpu: bool = True
):
    if not transcriptor:
        raise HTTPException(status_code=503, detail="Транскрибатор не инициализирован")
    
    # Проверяем формат файла
    if not file.filename.lower().endswith(('.mp3', '.wav', '.ogg')):
        raise HTTPException(status_code=400, detail="Поддерживаются только MP3, WAV и OGG файлы")
    
    try:
        # Сохраняем временный файл
        file_extension = os.path.splitext(file.filename)[1]
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        
        # Читаем и сохраняем файл
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Устанавливаем использование GPU
        transcriptor.set_use_gpu(use_gpu)
        
        # Транскрибация
        import time
        start_time = time.time()
        
        result = transcriptor.transcribe_mp3_with_speakers(
            temp_file.name, 
            num_speakers=num_speakers
        )
        
        processing_time = time.time() - start_time
        
        # Очищаем временный файл
        os.unlink(temp_file.name)
        
        if not result:
            raise HTTPException(status_code=500, detail="Ошибка транскрибации")
        
        return {
            "segments": result,
            "processing_time": round(processing_time, 2),
            "gpu_used": use_gpu and torch.cuda.is_available()
        }
        
    except Exception as e:
        if 'temp_file' in locals() and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")

@app.post("/transcribe/download")
async def transcribe_and_download(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    num_speakers: int = 4,
    use_gpu: bool = True
):
    result = await transcribe_audio(file, num_speakers, use_gpu)
    
    # Сохраняем во временный файл
    temp_result = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8')
    
    with open(temp_result.name, 'w', encoding='utf-8') as f:
        f.write(f"Результаты транскрибации\n")
        f.write(f"Файл: {file.filename}\n")
        f.write(f"Время обработки: {result['processing_time']} сек\n")
        f.write(f"Использовался GPU: {'Да' if result['gpu_used'] else 'Нет'}\n")
        f.write("=" * 60 + "\n\n")
        
        for segment in result['segments']:
            f.write(f"[{segment['speaker']}] ")
            f.write(f"{transcriptor.format_time(segment['start'])}-{transcriptor.format_time(segment['end'])}\n")
            f.write(f"{segment['text']}\n")
            f.write("-" * 50 + "\n\n")
    
    # Добавляем задачу очистки в background
    background_tasks.add_task(lambda: os.unlink(temp_result.name))
    
    return FileResponse(
        temp_result.name,
        media_type='text/plain',
        filename=f"transcription_{file.filename}.txt"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)