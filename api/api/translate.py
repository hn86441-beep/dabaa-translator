import os
import json
import base64
import srt
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import deepl
from groq import Groq
import io

app = FastAPI()

# تهيئة المفاتيح من متغيرات البيئة في Vercel
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# تهيئة العملاء
translator = deepl.Translator(DEEPL_API_KEY) if DEEPL_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

class TranslationRequest(BaseModel):
    text: str
    source: str
    target: str

class VisionRequest(BaseModel):
    image: str  # Base64 encoded image

@app.post("/api/translate")
async def translate_text(request: TranslationRequest):
    if not translator:
        return {"translated_text": "خطأ: مفتاح DeepL غير متوفر."}
    
    try:
        source_lang = None if request.source == "auto" else request.source
        result = translator.translate_text(
            request.text, 
            source_lang=source_lang,
            target_lang=request.target if request.target != "EN" else "EN-US"
        )
        return {"translated_text": result.text}
    except Exception as e:
        return {"translated_text": f"حدث خطأ: {str(e)}"}

@app.post("/api/vision")
async def vision_ocr(request: VisionRequest):
    if not groq_client:
        return {"text": "خطأ: مفتاح Groq غير متوفر."}
    
    try:
        # تنظيف بيانات base64
        base64_image = request.image.split(",")[1] if "," in request.image else request.image
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this image and provide it as plain text. Do not add any explanation."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="llama-3.2-11b-vision-preview",
        )
        return {"text": chat_completion.choices[0].message.content}
    except Exception as e:
        return {"text": f"فشل التعرف على النص: {str(e)}"}

@app.post("/api/translate-srt")
async def translate_srt(file: UploadFile = File(...), target: str = Form(...)):
    if not translator:
        raise HTTPException(status_code=500, detail="DeepL API Key missing")
    
    try:
        content = await file.read()
        srt_content = content.decode("utf-8")
        subtitles = list(srt.parse(srt_content))
        
        # تجميع النصوص لترجمتها دفعة واحدة (أسرع وأوفر)
        texts_to_translate = [sub.content for sub in subtitles]
        
        # ترجمة النصوص
        results = translator.translate_text(
            texts_to_translate, 
            target_lang=target if target != "EN" else "EN-US"
        )
        
        # تحديث محتوى الترجمة
        for i, sub in enumerate(subtitles):
            sub.content = results[i].text
            
        translated_srt = srt.compose(subtitles)
        
        return StreamingResponse(
            io.BytesIO(translated_srt.encode("utf-8")),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=translated_{file.filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# لمعالجة المسارات في Vercel
@app.get("/")
async def root():
    return {"message": "Dabaa Translator API is running"}
