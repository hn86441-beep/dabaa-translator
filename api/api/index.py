import os
import srt
import io
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import deepl
from groq import Groq

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# تهيئة العملاء
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

translator = deepl.Translator(DEEPL_API_KEY) if DEEPL_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

class TranslationRequest(BaseModel):
    text: str
    source: str
    target: str

class VisionRequest(BaseModel):
    image: str

# مسارات شاملة لضمان الوصول
@app.post("/api/translate")
@app.post("/translate")
async def translate_text(request: TranslationRequest):
    if not translator:
        raise HTTPException(status_code=500, detail="DeepL API Key missing")
    try:
        target = "EN-US" if request.target == "EN" else request.target
        source = None if request.source == "auto" else request.source
        result = translator.translate_text(request.text, source_lang=source, target_lang=target)
        return {"translated_text": result.text}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision")
@app.post("/vision")
async def vision_ocr(request: VisionRequest):
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq API Key missing")
    try:
        encoded = request.image.split(",", 1)[1] if "," in request.image else request.image
        completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": "Extract text from image."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}]}],
            model="llama-3.2-11b-vision-preview",
        )
        return {"text": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
@app.get("/health")
async def health():
    return {"status": "ok", "deepl": translator is not None, "groq": groq_client is not None}
