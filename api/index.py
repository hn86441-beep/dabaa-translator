import os, io, base64, json, time, urllib.parse
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict
from datetime import datetime
from PIL import Image
from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment Variables
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
DEEPL_KEY = os.environ.get("DEEPL_API_KEY", "").strip()
COHERE_KEY = os.environ.get("COHERE_API_KEY", "").strip()
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY", "").strip()
WA_PHONE = "201152582350"

# WhatsApp Alerts
def notify_whatsapp(message, err_key=None):
    if not CALLMEBOT_APIKEY or not WA_PHONE: return
    try:
        text = urllib.parse.quote(f"🚨 HN TRANSLATOR\n{message[:500]}")
        requests.get("https://api.callmebot.com/whatsapp.php", 
                     params={"phone": WA_PHONE, "text": text, "apikey": CALLMEBOT_APIKEY}, timeout=8)
    except: pass

# Languages Map
LANGS = {
    "Auto-Detect":{"g":"auto", "d":None, "tts":"en"}, "Arabic":{"g":"ar","d":"AR","tts":"ar"},
    "English":{"g":"en","d":"EN-US","tts":"en"}, "Russian":{"g":"ru","d":"RU","tts":"ru"},
    "Chinese":{"g":"zh-CN","d":"ZH","tts":"zh-cn"}, "German":{"g":"de","d":"DE","tts":"de"},
    "Spanish":{"g":"es","d":"ES","tts":"es"}, "French":{"g":"fr","d":"FR","tts":"fr"},
    "Portuguese":{"g":"pt","d":"PT-PT","tts":"pt"}, "Italian":{"g":"it","d":"IT","tts":"it"},
    "Japanese":{"g":"ja","d":"JA","tts":"ja"}, "Korean":{"g":"ko","d":"KO","tts":"ko"},
    "Turkish":{"g":"tr","d":"TR","tts":"tr"}, "Dutch":{"g":"nl","d":"NL","tts":"nl"},
    "Polish":{"g":"pl","d":"PL","tts":"pl"}, "Ukrainian":{"g":"uk","d":"UK","tts":"uk"},
    "Swedish":{"g":"sv","d":"SV","tts":"sv"}, "Danish":{"g":"da","d":"DA","tts":"da"},
    "Finnish":{"g":"fi","d":"FI","tts":"fi"}, "Romanian":{"g":"ro","d":"RO","tts":"ro"},
    "Hungarian":{"g":"hu","d":"HU","tts":"hu"}, "Czech":{"g":"cs","d":"CS","tts":"cs"},
    "Bulgarian":{"g":"bg","d":"BG","tts":"bg"}, "Greek":{"g":"el","d":"EL","tts":"el"},
    "Indonesian":{"g":"id","d":"ID","tts":"id"}, "Hindi":{"g":"hi","d":None,"tts":"hi"},
    "Persian":{"g":"fa","d":None,"tts":"fa"}, "Hebrew":{"g":"iw","d":None,"tts":"iw"},
    "Urdu":{"g":"ur","d":None,"tts":"ur"}
}

_TR_SYS = "You are an expert multilingual translator. Translate MEANING and INTENT. Return ONLY the translation."

def groq_llm(prompt, system="", max_tokens=700, fast=False):
    if not GROQ_KEY: return None
    model = "llama-3.1-8b-instant" if fast else "llama-3.3-70b-versatile"
    msgs = []
    if system: msgs.append({"role":"system","content":system})
    msgs.append({"role":"user","content":prompt})
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":model,"messages":msgs,"max_tokens":max_tokens,"temperature":0.4}, timeout=30)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"].strip()
        if r.status_code == 401: notify_whatsapp("GROQ 401", "groq_401")
    except: pass
    return None

def smart_translate(text, tgt, src="Auto-Detect"):
    if not text or not text.strip(): return None, "no text"
    if DEEPL_KEY:
        info = LANGS.get(tgt, {})
        if info.get("d"):
            ep = "https://api-free.deepl.com/v2/translate" if DEEPL_KEY.endswith(":fx") else "https://api.deepl.com/v2/translate"
            try:
                r = requests.post(ep, headers={"Authorization":f"DeepL-Auth-Key {DEEPL_KEY}"}, data={"text":text,"target_lang":info["d"]}, timeout=15)
                if r.status_code == 200: return r.json()["translations"][0]["text"], "DeepL"
            except: pass
    if GROQ_KEY and len(text) <= 1500:
        r = groq_llm(f"Translate from {src} to {tgt}:\n\n{text}", system=_TR_SYS, max_tokens=800, fast=len(text)<300)
        if r: return r, "AI Contextual"
    src_g = LANGS.get(src, {}).get("g","auto"); tgt_g = LANGS.get(tgt, {}).get("g","en")
    try:
        res = GoogleTranslator(source=src_g or "auto", target=tgt_g).translate(text)
        if res: return res, "Google"
    except: pass
    return None, "فشلت الترجمة"

def groq_stt(audio_bytes, lang="auto", verbose=False):
    if not GROQ_KEY: return None, "No Groq key"
    lc = lang if lang and lang != "auto" else None
    files={"file":("audio.wav",audio_bytes,"audio/wav"), "model":(None,"whisper-large-v3-turbo"), "response_format":(None,"verbose_json" if verbose else "json")}
    if lc: files["language"]=(None,lc)
    try:
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization":f"Bearer {GROQ_KEY}"}, files=files, timeout=60)
        if r.status_code == 200: return r.json(), None
        return None, f"Groq STT {r.status_code}"
    except Exception as e: return None, str(e)

@app.post("/api/translate")
async def api_translate(req: Request):
    data = await req.json()
    text, tgt, src = data.get("text",""), data.get("tgt","Arabic"), data.get("src","Auto-Detect")
    trans, eng = smart_translate(text, tgt, src)
    return {"trans": trans, "eng": eng}

@app.post("/api/chat")
async def api_chat(req: Request):
    data = await req.json()
    # Logic for AI Chat simplified for API
    res = groq_llm(data.get("msg",""), system="You are a helpful translation assistant.")
    return {"ans": res}

@app.post("/api/tts")
async def api_tts(req: Request):
    data = await req.json()
    text, lang = data.get("text",""), data.get("lang","en")
    try:
        buf = io.BytesIO()
        gTTS(text=text[:500], lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        return JSONResponse({"audio": base64.b64encode(buf.read()).decode()})
    except: return JSONResponse({"audio": None})

@app.post("/api/ocr")
async def api_ocr(file: UploadFile = File(...)):
    img = await file.read()
    if not GROQ_KEY: return JSONResponse({"txt": None, "err": "No Groq Key"})
    try:
        b64 = base64.b64encode(img).decode()
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":"meta-llama/llama-4-scout-17b-16e-instruct","temperature":0,"max_tokens":2048,
                  "messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}, {"type":"text","text":"Extract ALL text. Return raw text only."}]}]}, timeout=30)
        if r.status_code == 200: return JSONResponse({"txt": r.json()["choices"][0]["message"]["content"].strip(), "err": None})
        return JSONResponse({"txt": None, "err": "Vision unavailable"})
    except Exception as e: return JSONResponse({"txt": None, "err": str(e)})

@app.post("/api/stt")
async def api_stt(file: UploadFile = File(...), lang: str = Form("auto")):
    audio = await file.read()
    data, err = groq_stt(audio, lang, verbose=False)
    if data: return JSONResponse({"txt": data.get("text","").strip(), "err": None})
    return JSONResponse({"txt": None, "err": err})

@app.post("/api/group")
async def api_group(file: UploadFile = File(...), tgt: str = Form("Arabic")):
    audio = await file.read()
    data, err = groq_stt(audio, lang="auto", verbose=True)
    if not data: return JSONResponse({"results": None, "err": err})
    segs = data.get("segments", [])
    results = []
    for s in segs:
        txt = s.get("text","").strip()
        if not txt: continue
        tr, eng = smart_translate(txt, tgt, "Auto-Detect")
        results.append({"orig": txt, "trans": tr, "t0": s.get("start",0), "t1": s.get("end",0), "eng": eng})
    return JSONResponse({"results": results, "err": None})
