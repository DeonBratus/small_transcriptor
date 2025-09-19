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
    vision_model: str = Form("llava"),
    eval_model: str = Form("llama3.2"),
    ollama_base_url: str = Form("http://212.8.228.176:9000")
):
    try:
        with TemporaryDirectory() as temp_dir:
            # Сохраняем DOCX файл
            docx_path = os.path.join(temp_dir, f"{uuid.uuid4()}.docx")
            with open(docx_path, "wb") as f:
                shutil.copyfileobj(docx_file.file, f)

            # Сохраняем PPTX файл
            pptx_path = os.path.join(temp_dir, f"{uuid.uuid4()}.pptx")
            with open(pptx_path, "wb") as f:
                shutil.copyfileobj(pptx_file.file, f)

            # Создаем evaluator
            evaluator = PresentationEvaluator(
                vision_model=vision_model,
                eval_model=eval_model,
                ollama_base_url=ollama_base_url,
            )

            # Функция для генерации стрима
            async def generate():
                try:
                    for chunk in evaluator.evaluate_stream(
                        doc_path=docx_path,
                        presentation_path=pptx_path
                    ):
                        yield f"data: {chunk}\n\n"
                        await asyncio.sleep(0.01)  # Небольшая задержка
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    yield f"data: ERROR: {str(e)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/models/")
async def get_available_models():
    """Получить список доступных моделей Ollama"""
    try:
        import requests
        response = requests.get("http://212.8.228.176:9000/api/tags")
        models = response.json().get("models", [])
        return {"models": [model["name"] for model in models]}
    except Exception as e:
        return {"models": ["llama3.2", "llava", "mistral", "phi3"]}

@app.get("/health/")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        import requests
        response = requests.get("http://212.8.228.176:9000/api/tags", timeout=5)
        return {"status": "healthy", "ollama_connected": response.status_code == 200}
    except:
        return {"status": "healthy", "ollama_connected": False}