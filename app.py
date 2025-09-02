import os
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Dict, Optional
from transcriptor import Transcriptor
from pydantic import BaseModel
import json
from datetime import datetime

app = FastAPI(
    title="Audio Transcription API",
    description="API для транскрибации аудиофайлов с разделением по спикерам",
    version="1.0.0"
)

# Создаем папку для результатов если ее нет
os.makedirs("./results", exist_ok=True)
os.makedirs("./uploads", exist_ok=True)

class TranscriptionRequest(BaseModel):
    num_speakers: int = 4
    model_path: Optional[str] = None

class TranscriptionResponse(BaseModel):
    job_id: str
    status: str
    message: str
    result_file: Optional[str] = None

class TranscriptionResult(BaseModel):
    speaker: str
    text: str
    start: float
    end: float
    formatted_start: str
    formatted_end: str

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: str
    created_at: str
    completed_at: Optional[str] = None
    result_file: Optional[str] = None
    error: Optional[str] = None

# Глобальный словарь для хранения статусов задач
jobs = {}
transcriber = Transcriptor()

def format_time(seconds: float) -> str:
    """Форматирование времени"""
    minutes = int(seconds // 60)
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:06.3f}"

def process_transcription(job_id: str, file_path: str, num_speakers: int, model_path: Optional[str] = None):
    """Фоновая задача обработки транскрибации"""
    try:
        jobs[job_id] = {
            "status": "processing",
            "progress": "Конвертация MP3 в WAV",
            "created_at": datetime.now().isoformat(),
            "result_file": None,
            "error": None
        }
        
        # Создаем экземпляр транскрибатора
        if model_path:
            transcriber_instance = Transcriptor(model_path=model_path)
        else:
            transcriber_instance = Transcriptor()
        
        # Запуск транскрибации
        jobs[job_id]["progress"] = "Транскрибация аудио"
        transcription = transcriber_instance.transcribe_mp3_with_speakers(
            file_path, num_speakers=num_speakers
        )

        if transcription:
            jobs[job_id]["progress"] = "Сохранение результатов"
            
            # Генерируем имя файла для результата
            result_filename = f"transcription_{job_id}.txt"
            result_path = os.path.join("./results", result_filename)
            
            # Сохраняем результаты
            transcriber_instance.save_results(transcription, result_path)
            
            # Сохраняем также в JSON формате
            json_result = []
            for segment in transcription:
                json_result.append({
                    "speaker": segment['speaker'],
                    "text": segment['text'],
                    "start": segment['start'],
                    "end": segment['end'],
                    "formatted_start": format_time(segment['start']),
                    "formatted_end": format_time(segment['end'])
                })
            
            json_filename = f"transcription_{job_id}.json"
            json_path = os.path.join("./results", json_filename)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_result, f, ensure_ascii=False, indent=2)
            
            # Обновляем статус задачи
            jobs[job_id].update({
                "status": "completed",
                "progress": "Завершено",
                "completed_at": datetime.now().isoformat(),
                "result_file": result_filename,
                "json_file": json_filename
            })
            
        else:
            jobs[job_id].update({
                "status": "error",
                "progress": "Ошибка",
                "completed_at": datetime.now().isoformat(),
                "error": "Транскрибация не удалась"
            })
            
    except Exception as e:
        jobs[job_id].update({
            "status": "error",
            "progress": "Ошибка",
            "completed_at": datetime.now().isoformat(),
            "error": str(e)
        })
    finally:
        # Удаляем временный файл
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    num_speakers: int = 4,
    model_path: Optional[str] = None
):
    """Запуск транскрибации аудиофайла"""
    # Проверяем формат файла
    if not file.filename.lower().endswith('.mp3'):
        raise HTTPException(status_code=400, detail="Поддерживаются только MP3 файлы")
    
    # Генерируем ID задачи
    job_id = str(uuid.uuid4())
    
    # Сохраняем файл во временную папку
    file_path = os.path.join("./uploads", f"{job_id}_{file.filename}")
    
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {str(e)}")
    
    # Запускаем фоновую задачу
    background_tasks.add_task(
        process_transcription, job_id, file_path, num_speakers, model_path
    )
    
    # Сохраняем информацию о задаче
    jobs[job_id] = {
        "status": "queued",
        "progress": "В очереди на обработку",
        "created_at": datetime.now().isoformat(),
        "result_file": None,
        "error": None
    }
    
    return TranscriptionResponse(
        job_id=job_id,
        status="queued",
        message="Задача добавлена в очередь на обработку",
        result_file=None
    )

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Получение статуса задачи"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        result_file=job.get("result_file"),
        error=job.get("error")
    )

@app.get("/jobs/{job_id}/result")
async def get_transcription_result(job_id: str):
    """Получение результата транскрибации"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Задача еще не завершена")
    
    result_file = job.get("result_file")
    if not result_file:
        raise HTTPException(status_code=404, detail="Файл результата не найден")
    
    file_path = os.path.join("./results", result_file)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл результата не существует")
    
    return FileResponse(
        file_path,
        media_type="text/plain",
        filename=f"transcription_{job_id}.txt"
    )

@app.get("/jobs/{job_id}/result/json")
async def get_transcription_json(job_id: str):
    """Получение результата в JSON формате"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Задача еще не завершена")
    
    json_file = job.get("json_file")
    if not json_file:
        raise HTTPException(status_code=404, detail="JSON файл не найден")
    
    file_path = os.path.join("./results", json_file)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="JSON файл не существует")
    
    return FileResponse(
        file_path,
        media_type="application/json",
        filename=f"transcription_{job_id}.json"
    )

@app.get("/jobs")
async def list_jobs():
    """Получение списка всех задач"""
    return jobs

@app.get("/health")
async def health_check():
    """Проверка статуса сервиса"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Удаление задачи и связанных файлов"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Удаляем файлы результатов
    job = jobs[job_id]
    if job.get("result_file"):
        result_path = os.path.join("./results", job["result_file"])
        if os.path.exists(result_path):
            os.remove(result_path)
    
    if job.get("json_file"):
        json_path = os.path.join("./results", job["json_file"])
        if os.path.exists(json_path):
            os.remove(json_path)
    
    # Удаляем задачу из списка
    del jobs[job_id]
    
    return {"message": "Задача и файлы удалены"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)