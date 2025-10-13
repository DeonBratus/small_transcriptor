from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.background import BackgroundTasks
import os
import tempfile
from transcriptor import Transcriptor
from models import TranscriptionRequest, TranscriptionResponse, TranscriptionSegment
from typing import Optional

app = FastAPI(
    title="Audio Transcription API",
    description="API для транскрибации аудио с разделением по спикерам с поддержкой многопоточности",
    version="2.0.0"
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
        transcriptor = Transcriptor(is_advanced_segmentation=False)
        print("Транскрибатор успешно инициализирован")
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
    use_multithreading: bool = True,
    chunk_duration: float = 30.0,
    max_workers: Optional[int] = None
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
        
        # Настраиваем количество потоков если указано
        if max_workers is not None:
            transcriptor.max_workers = max_workers
        
        # Транскрибация
        import time
        start_time = time.time()
        
        result = transcriptor.transcribe_mp3_with_speakers(
            temp_file.name, 
            num_speakers=num_speakers,
            use_multithreading=use_multithreading,
            chunk_duration=chunk_duration
        )
        
        processing_time = time.time() - start_time
        
        # Очищаем временный файл
        os.unlink(temp_file.name)
        
        if not result:
            raise HTTPException(status_code=500, detail="Ошибка транскрибации")
        
        return {
            "segments": result,
            "processing_time": round(processing_time, 2),
            "multithreading_used": use_multithreading,
            "threads_count": transcriptor.max_workers
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
    use_multithreading: bool = True,
    chunk_duration: float = 30.0,
    max_workers: Optional[int] = None
):
    result = await transcribe_audio(file, num_speakers, use_multithreading, chunk_duration, max_workers)
    
    # Сохраняем во временный файл
    temp_result = tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8')
    
    with open(temp_result.name, 'w', encoding='utf-8') as f:
        f.write(f"Результаты транскрибации\n")
        f.write(f"Файл: {file.filename}\n")
        f.write(f"Время обработки: {result['processing_time']} сек\n")
        f.write(f"Многопоточность: {'Да' if result['multithreading_used'] else 'Нет'}\n")
        f.write(f"Количество потоков: {result['threads_count']}\n")
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