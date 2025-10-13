import os
import shutil
import uuid
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from tempfile import TemporaryDirectory
from typing import Optional
import asyncio

from app.evaluator import PresentationEvaluator
from app.utils import setup_logging, log_error, log_info

# Настройка логирования
logger = setup_logging()

app = FastAPI(title="Thesis & Presentation Evaluator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/evaluate/")
async def evaluate_thesis_and_presentation(
    docx_file: UploadFile = File(...),
    pptx_file: UploadFile = File(...),
    vision_model: str = Form("gemma3:4b"),
    eval_model: str = Form("gemma3:4b"),
    ollama_base_url: str = Form("http://212.8.228.176:9000")
):
    log_info(logger, f"Starting evaluation with models: {eval_model}, {vision_model}")
    
    # Создаем директорию для файлов в общем volume
    data_dir = "/app/data/evaluation_files"
    os.makedirs(data_dir, exist_ok=True)
    
    # Генерируем уникальные имена файлов
    docx_filename = f"{uuid.uuid4()}.docx"
    pptx_filename = f"{uuid.uuid4()}.pptx"
    docx_path = os.path.join(data_dir, docx_filename)
    pptx_path = os.path.join(data_dir, pptx_filename)
    
    try:
        # Сохраняем DOCX файл
        with open(docx_path, "wb") as f:
            shutil.copyfileobj(docx_file.file, f)
        log_info(logger, f"Saved DOCX file: {docx_file.filename} -> {docx_path}")

        # Сохраняем PPTX файл
        with open(pptx_path, "wb") as f:
            shutil.copyfileobj(pptx_file.file, f)
        log_info(logger, f"Saved PPTX file: {pptx_file.filename} -> {pptx_path}")

        # Создаем evaluator
        evaluator = PresentationEvaluator(
            vision_model=vision_model,
            eval_model=eval_model,
            ollama_base_url=ollama_base_url,
        )
        log_info(logger, "Created PresentationEvaluator instance")

        # Функция для генерации стрима
        async def generate():
            try:
                log_info(logger, "Starting stream evaluation")
                for chunk in evaluator.evaluate_stream(
                    doc_path=docx_path,
                    presentation_path=pptx_path
                ):
                    yield f"data: {chunk}\n\n"
                    await asyncio.sleep(0.01)  # Небольшая задержка
                yield "data: [DONE]\n\n"
                log_info(logger, "Stream evaluation completed")
            except Exception as e:
                log_error(logger, e, "Stream evaluation")
                yield f"data: ERROR: {str(e)}\n\n"
            finally:
                # Очищаем файлы после обработки
                try:
                    if os.path.exists(docx_path):
                        os.unlink(docx_path)
                        log_info(logger, f"Cleaned up DOCX file: {docx_path}")
                    if os.path.exists(pptx_path):
                        os.unlink(pptx_path)
                        log_info(logger, f"Cleaned up PPTX file: {pptx_path}")
                except Exception as cleanup_error:
                    log_error(logger, cleanup_error, "File cleanup")

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except Exception as e:
        log_error(logger, e, "evaluate_thesis_and_presentation")
        # Очищаем файлы в случае ошибки
        try:
            if os.path.exists(docx_path):
                os.unlink(docx_path)
            if os.path.exists(pptx_path):
                os.unlink(pptx_path)
        except:
            pass
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/models/")
async def get_available_models():
    """Получить список доступных моделей Ollama"""
    try:
        import requests
        response = requests.get("http://212.8.228.176:9000/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return {"models": [model["name"] for model in models]}
        else:
            return {"models": ["llama3.2", "llava", "mistral", "phi3"], "error": "Could not fetch models"}
    except Exception as e:
        return {"models": ["llama3.2", "llava", "mistral", "phi3"], "error": str(e)}

@app.get("/health/")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        import requests
        response = requests.get("http://212.8.228.176:9000/api/tags", timeout=5)
        return {
            "status": "healthy", 
            "ollama_connected": response.status_code == 200,
            "ollama_url": "http://212.8.228.176:9000"
        }
    except Exception as e:
        return {
            "status": "healthy", 
            "ollama_connected": False,
            "error": str(e)
        }