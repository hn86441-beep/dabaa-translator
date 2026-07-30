import os
import json
import base64
import srt
import io
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import deepl
from groq import Groq

# إعداد السجلات للمساعدة في التصحيح في Vercel Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# إضافة CORS للسماح بالطلبات من الواجهة الأمامية
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# تهيئة المفاتيح
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# تهيئة العملاء مع التحقق من وجود المفاتيح
try:
    translator = deepl.Translator(DEEPL_API_KEY) if DEEPL_API_KEY else None
    if not translator:
        logger.warning("DeepL API Key is missing!")
except Exception as e:
    logger.error(f"Failed to initialize DeepL: {e}")
    translator = None

try:
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
    if not groq_client:
        logger.warning("Groq API Key is missing!")
except Exception as e:
    logger.error(f"Failed to initialize Groq: {e}")
    groq_client = None

class TranslationRequest(BaseModel):
    text: str
    source: str
    target: str

class VisionRequest(BaseModel):
    image: str

@app.post("/api/translate")
async def translate_text(request: TranslationRequest):
    if not translator:
        raise HTTPException(status_code=500, detail="DeepL API Key is not configured in Vercel environment variables.")
    
    try:
        # تحويل كود اللغة للإنجليزية ليتوافق مع DeepL (EN-US أو EN-GB)
        target = request.target
        if target == "EN":
            target = "EN-US"
        
        source = None if request.source == "auto" else request.source
        
        result = translator.translate_text(
            request.text,
            source_lang=source,
            target_lang=target
        )
        return {"translated_text": result.text, "detected_source": result.detected_source_language}
    except deepl.DeepLException as e:
        logger.error(f"DeepL Error: {e}")
        raise HTTPException(status_code=400, detail=f"DeepL API Error: {str(e)}")
    except Exception as e:
        logger.error(f"General Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision")
async def vision_ocr(request: VisionRequest):
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq API Key is not configured.")
    
    try:
        # تنظيف بيانات base64
        header, encoded = request.image.split(",", 1) if "," in request.image else (None, request.image)
        
        completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this image accurately. Return only the extracted text without any conversational filler."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded}",
                            },
                        },
                    ],
                }
            ],
            model="llama-3.2-11b-vision-preview",
            temperature=0.1,
        )
        return {"text": completion.choices[0].message.content}
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        raise HTTPException(status_code=500, detail=f"Vision API Error: {str(e)}")

@app.post("/api/translate-srt")
async def translate_srt(file: UploadFile = File(...), target: str = Form(...)):
    if not translator:
        raise HTTPException(status_code=500, detail="DeepL API Key missing")
    
    try:
        content = await file.read()
        try:
            srt_content = content.decode("utf-8")
        except UnicodeDecodeError:
            srt_content = content.decode("latin-1")
            
        subtitles = list(srt.parse(srt_content))
        
        # ترجمة النصوص بشكل دفعات (لتحسين الأداء)
        texts = [sub.content for sub in subtitles]
        
        target_lang = target if target != "EN" else "EN-US"
        
        # تقسيم النصوص لمجموعات إذا كانت كبيرة جداً
        translated_results = []
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            results = translator.translate_text(batch, target_lang=target_lang)
            translated_results.extend([r.text for r in results])
        
        for i, sub in enumerate(subtitles):
            sub.content = translated_results[i]
            
        final_srt = srt.compose(subtitles)
        
        return StreamingResponse(
            io.BytesIO(final_srt.encode("utf-8")),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=translated_{file.filename}"}
        )
    except Exception as e:
        logger.error(f"SRT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# مسار للتحقق من الحالة
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "deepl_ready": translator is not None,
        "groq_ready": groq_client is not None
    }
