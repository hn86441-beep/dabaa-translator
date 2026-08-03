import os, io, base64, urllib.parse
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import OrderedDict
from PIL import Image
from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS
import pdfplumber, docx, openpyxl, requests

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
DEEPL_KEY = os.environ.get("DEEPL_API_KEY", "").strip()
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY", "").strip()
WA_PHONE = "201152582350"

def notify_whatsapp(message):
    if not CALLMEBOT_APIKEY: return
    try:
        text = urllib.parse.quote(f"🚨 HN TRANSLATOR\n{message[:500]}")
        requests.get("https://api.callmebot.com/whatsapp.php", params={"phone": WA_PHONE, "text": text, "apikey": CALLMEBOT_APIKEY}, timeout=8)
    except: pass

LANGS = {
    "Auto-Detect":{"g":"auto","d":None,"tts":"en"}, "Arabic":{"g":"ar","d":"AR","tts":"ar"},
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

def groq_llm(prompt, system="", fast=False):
    if not GROQ_KEY: return None
    model = "llama-3.1-8b-instant" if fast else "llama-3.3-70b-versatile"
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}],"max_tokens":800,"temperature":0.4}, timeout=30)
        if r.status_code == 200: return r.json()["choices"][0]["message"]["content"].strip()
        if r.status_code == 401: notify_whatsapp("GROQ 401")
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
        sys = "You are an expert multilingual translator. Translate MEANING. Return ONLY the translation."
        r = groq_llm(f"Translate from {src} to {tgt}:\n\n{text}", system=sys, fast=len(text)<300)
        if r: return r, "AI Contextual"
    try:
        res = GoogleTranslator(source=LANGS.get(src,{}).get("g","auto"), target=LANGS.get(tgt,{}).get("g","en")).translate(text)
        if res: return res, "Google"
    except: pass
    return None, "فشلت الترجمة"

def groq_stt(audio_bytes, lang="auto", verbose=False):
    if not GROQ_KEY: return None, "No Groq key"
    lc = lang if lang and lang != "auto" else None
    files={"file":("audio.webm",audio_bytes,"audio/webm"), "model":(None,"whisper-large-v3-turbo"), "response_format":(None,"verbose_json" if verbose else "json")}
    if lc: files["language"]=(None,lc)
    try:
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers={"Authorization":f"Bearer {GROQ_KEY}"}, files=files, timeout=60)
        if r.status_code == 200: return r.json(), None
        return None, f"Groq STT {r.status_code}"
    except Exception as e: return None, str(e)

@app.post("/translate")
async def api_translate(req: Request):
    data = await req.json()
    trans, eng = smart_translate(data.get("text",""), data.get("tgt","Arabic"), data.get("src","Auto-Detect"))
    return {"trans": trans, "eng": eng}

@app.post("/chat")
async def api_chat(req: Request):
    data = await req.json()
    sys = "أنت ذكاء اصطناعي متخصص في اللغات والترجمة. ردودك مباشرة. إذا طُلبت ترجمة أعطها فوراً."
    res = groq_llm(data.get("msg",""), system=sys)
    return {"ans": res}

@app.post("/tts")
async def api_tts(req: Request):
    data = await req.json()
    try:
        buf = io.BytesIO(); gTTS(text=data.get("text","")[:500], lang=data.get("lang","en"), slow=False).write_to_fp(buf)
        buf.seek(0); return JSONResponse({"audio": base64.b64encode(buf.read()).decode()})
    except: return JSONResponse({"audio": None})

@app.post("/ocr")
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

@app.post("/stt")
async def api_stt(file: UploadFile = File(...), lang: str = Form("auto")):
    audio = await file.read()
    data, err = groq_stt(audio, lang, verbose=False)
    if data: return JSONResponse({"txt": data.get("text","").strip(), "err": None})
    return JSONResponse({"txt": None, "err": err})

@app.post("/srt")
async def api_srt(file: UploadFile = File(...), tgt: str = Form("Arabic")):
    audio = await file.read()
    data, err = groq_stt(audio, lang="auto", verbose=True)
    if not data: return JSONResponse({"blocks": None, "err": err})
    blocks = []
    for i, s in enumerate(data.get("segments", []), 1):
        txt = s.get("text","").strip()
        tr, _ = smart_translate(txt, tgt)
        blocks.append({"num": i, "start": s.get("start",0), "end": s.get("end",0), "trans": tr or txt})
    return JSONResponse({"blocks": blocks, "err": None})

@app.post("/group")
async def api_group(file: UploadFile = File(...), tgt: str = Form("Arabic")):
    audio = await file.read()
    data, err = groq_stt(audio, lang="auto", verbose=True)
    if not data: return JSONResponse({"results": None, "err": err})
    results = []
    for s in data.get("segments", []):
        txt = s.get("text","").strip()
        if not txt: continue
        tr, eng = smart_translate(txt, tgt, "Auto-Detect")
        results.append({"orig": txt, "trans": tr, "t0": s.get("start",0), "t1": s.get("end",0), "eng": eng})
    return JSONResponse({"results": results, "err": None})

@app.post("/extract")
async def api_extract(file: UploadFile = File(...)):
    fb = await file.read(); fn = file.filename; ext = os.path.splitext(fn)[1].lower()
    try:
        if ext == ".pdf":
            txt = ""
            with pdfplumber.open(io.BytesIO(fb)) as pdf:
                for pg in pdf.pages:
                    t = pg.extract_text()
                    if t: txt += t + "\n"
            return {"txt": txt.strip(), "err": None}
        elif ext == ".docx":
            d = docx.Document(io.BytesIO(fb)); txt = "\n".join(p.text for p in d.paragraphs)
            return {"txt": txt.strip(), "err": None}
        elif ext in (".xlsx",".xls"):
            wb = openpyxl.load_workbook(io.BytesIO(fb), data_only=True)
            parts = [str(c.value) for sh in wb.worksheets for row in sh.iter_rows() for c in row if c.value is not None]
            return {"txt": "\n".join(parts).strip(), "err": None}
        elif ext == ".txt":
            return {"txt": fb.decode("utf-8", errors="ignore").strip(), "err": None}
        else: return {"txt": None, "err": "Unsupported file"}
    except Exception as e: return {"txt": None, "err": str(e)}
