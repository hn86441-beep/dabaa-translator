"""
HN Translator – Vercel Serverless Backend  (complete)
Routes: /translate /ocr /stt /subtitle /chat /spell /tts /langs /health
"""
import os, json, base64, re, io
from flask import Flask, request, jsonify, send_file
import requests

app = Flask(__name__)

# ── Keys (set in Vercel Dashboard → Settings → Environment Variables) ──
GROQ_KEY  = os.environ.get("GROQ_API_KEY",  "").strip()
DEEPL_KEY = os.environ.get("DEEPL_API_KEY", "").strip()

_M_FAST  = "llama-3.1-8b-instant"
_M_SMART = "llama-3.3-70b-versatile"

LANGS = {
    "Auto-Detect":{"g":"auto","d":None,   "gtts":"en"},
    "Arabic":     {"g":"ar",  "d":"AR",   "gtts":"ar"},
    "English":    {"g":"en",  "d":"EN-US","gtts":"en"},
    "Russian":    {"g":"ru",  "d":"RU",   "gtts":"ru"},
    "Chinese":    {"g":"zh-CN","d":"ZH",  "gtts":"zh-cn"},
    "German":     {"g":"de",  "d":"DE",   "gtts":"de"},
    "Spanish":    {"g":"es",  "d":"ES",   "gtts":"es"},
    "French":     {"g":"fr",  "d":"FR",   "gtts":"fr"},
    "Portuguese": {"g":"pt",  "d":"PT-PT","gtts":"pt"},
    "Italian":    {"g":"it",  "d":"IT",   "gtts":"it"},
    "Japanese":   {"g":"ja",  "d":"JA",   "gtts":"ja"},
    "Korean":     {"g":"ko",  "d":"KO",   "gtts":"ko"},
    "Turkish":    {"g":"tr",  "d":"TR",   "gtts":"tr"},
    "Dutch":      {"g":"nl",  "d":"NL",   "gtts":"nl"},
    "Polish":     {"g":"pl",  "d":"PL",   "gtts":"pl"},
    "Ukrainian":  {"g":"uk",  "d":"UK",   "gtts":"uk"},
    "Swedish":    {"g":"sv",  "d":"SV",   "gtts":"sv"},
    "Danish":     {"g":"da",  "d":"DA",   "gtts":"da"},
    "Finnish":    {"g":"fi",  "d":"FI",   "gtts":"fi"},
    "Romanian":   {"g":"ro",  "d":"RO",   "gtts":"ro"},
    "Hungarian":  {"g":"hu",  "d":"HU",   "gtts":"hu"},
    "Czech":      {"g":"cs",  "d":"CS",   "gtts":"cs"},
    "Bulgarian":  {"g":"bg",  "d":"BG",   "gtts":"bg"},
    "Greek":      {"g":"el",  "d":"EL",   "gtts":"el"},
    "Indonesian": {"g":"id",  "d":"ID",   "gtts":"id"},
    "Hindi":      {"g":"hi",  "d":None,   "gtts":"hi"},
    "Persian":    {"g":"fa",  "d":None,   "gtts":"fa"},
    "Hebrew":     {"g":"iw",  "d":None,   "gtts":"iw"},
    "Urdu":       {"g":"ur",  "d":None,   "gtts":"ur"},
}

# ════════════════════════════════════════════════════════
#  CORS preflight
# ════════════════════════════════════════════════════════
@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return r

@app.route("/api/<path:p>", methods=["OPTIONS"])
def preflight(p): return jsonify({"ok":True}), 200

# ════════════════════════════════════════════════════════
#  helpers
# ════════════════════════════════════════════════════════
def _wl(c):
    if not c or c in ("auto","Auto-Detect"): return None
    return {"zh-CN":"zh","zh-cn":"zh","iw":"he"}.get(c, c[:2])

def _amime(fn):
    ext = fn.rsplit(".",1)[-1].lower()
    return {"wav":"audio/wav","mp3":"audio/mpeg","mp4":"video/mp4",
            "m4a":"audio/mp4","ogg":"audio/ogg","webm":"audio/webm",
            "mov":"video/quicktime"}.get(ext,"audio/wav")

def _deepl(text, tgt_code):
    if not DEEPL_KEY or not tgt_code: return None
    ep = ("https://api-free.deepl.com/v2/translate" if DEEPL_KEY.endswith(":fx")
          else "https://api.deepl.com/v2/translate")
    try:
        r = requests.post(ep, headers={"Authorization":f"DeepL-Auth-Key {DEEPL_KEY}"},
                          data={"text":text,"target_lang":tgt_code}, timeout=12)
        if r.status_code == 200:
            return r.json()["translations"][0]["text"]
    except Exception: pass
    return None

def _google(text, tgt_g, src_g="auto"):
    try:
        from deep_translator import GoogleTranslator
        res = GoogleTranslator(source=src_g or "auto", target=tgt_g).translate(text)
        if res: return res
    except Exception: pass
    try:
        from deep_translator import MyMemoryTranslator
        s = "en" if (not src_g or src_g=="auto") else src_g
        res = MyMemoryTranslator(source=s, target=tgt_g).translate(text)
        if res: return res
    except Exception: pass
    return None

def _translate_text(text, target, source="Auto-Detect"):
    info   = LANGS.get(target, {})
    src_g  = LANGS.get(source, {}).get("g","auto")
    # DeepL first
    r = _deepl(text, info.get("d"))
    if r: return r, "DeepL ✦"
    # Google / MyMemory
    r = _google(text, info.get("g","en"), src_g)
    if r: return r, "Google"
    return None, "failed"

def _groq_chat(msgs, model=_M_SMART, max_tokens=900):
    if not GROQ_KEY: return None, "no key"
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":model,"messages":msgs,"max_tokens":max_tokens,"temperature":0.35},
            timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip(), None
        if r.status_code == 429:
            return None, "rate_limit"
        return None, f"{r.status_code}"
    except Exception as e: return None, str(e)

# ════════════════════════════════════════════════════════
#  /api/translate
# ════════════════════════════════════════════════════════
@app.route("/api/translate", methods=["POST"])
def translate():
    d = request.get_json(force=True) or {}
    text   = (d.get("text") or "").strip()
    target = d.get("target","Arabic")
    source = d.get("source","Auto-Detect")
    if not text: return jsonify({"error":"no text"}), 400
    res, eng = _translate_text(text, target, source)
    if res: return jsonify({"translated":res,"engine":eng})
    return jsonify({"error":"All translation engines failed"}), 502

# ════════════════════════════════════════════════════════
#  /api/ocr — Groq Vision (FIXED — 4 models)
# ════════════════════════════════════════════════════════
@app.route("/api/ocr", methods=["POST"])
def ocr():
    if not GROQ_KEY: return jsonify({"error":"GROQ_API_KEY not configured"}), 503

    # Accept both JSON (base64) and multipart form
    img_b64 = ""; mime = "image/jpeg"
    if request.content_type and "multipart" in request.content_type:
        f = request.files.get("image")
        if f:
            img_b64 = base64.b64encode(f.read()).decode()
            mime = f.mimetype or "image/jpeg"
    else:
        d = request.get_json(force=True) or {}
        img_b64 = d.get("image","")
        if "," in img_b64:
            hdr, img_b64 = img_b64.split(",",1)
            if ":" in hdr: mime = hdr.split(":")[1].split(";")[0]

    if not img_b64: return jsonify({"error":"no image"}), 400

    prompt = ("Extract ALL text from this image exactly as written. "
              "Preserve the original language. Return ONLY the raw text, no explanation.")
    models = [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
    ]
    for model in models:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":model,"temperature":0,"max_tokens":2048,
                      "messages":[{"role":"user","content":[
                          {"type":"image_url","image_url":{"url":f"data:{mime};base64,{img_b64}","detail":"high"}},
                          {"type":"text","text":prompt}]}]},
                timeout=30)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                if txt: return jsonify({"text":txt,"model":model})
                continue
            if r.status_code in (404,400,422): continue
            return jsonify({"error":f"Groq {r.status_code}: {r.text[:120]}"}), 502
        except Exception: continue
    return jsonify({"error":"No Groq Vision model available"}), 502

# ════════════════════════════════════════════════════════
#  /api/stt — Groq Whisper (also handles /api/voice)
# ════════════════════════════════════════════════════════
def _do_stt(audio_bytes, fn, lang, verbose=False):
    if not GROQ_KEY: return None, "GROQ_API_KEY not configured"
    lc = _wl(lang)
    files = {
        "file":(fn,audio_bytes,_amime(fn)),
        "model":(None,"whisper-large-v3-turbo"),
        "response_format":(None,"verbose_json" if verbose else "json"),
    }
    if verbose: files["timestamp_granularities[]"] = (None,"segment")
    if lc: files["language"] = (None,lc)
    try:
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                          headers={"Authorization":f"Bearer {GROQ_KEY}"},
                          files=files, timeout=90)
        if r.status_code == 200:
            d = r.json()
            if verbose: return d, None
            txt = d.get("text","").strip()
            return (txt, None) if txt else (None, "No speech detected")
        return None, f"Groq STT {r.status_code}: {r.text[:120]}"
    except Exception as e: return None, str(e)

def _get_audio_from_request():
    f = request.files.get("audio")
    if f: return f.read(), f.filename or "audio.wav"
    # JSON base64
    d = request.get_json(force=True, silent=True) or {}
    b64 = d.get("audio_b64","")
    if b64: return base64.b64decode(b64), "audio.wav"
    return None, None

@app.route("/api/stt", methods=["POST"])
@app.route("/api/voice", methods=["POST"])
def stt():
    audio_bytes, fn = _get_audio_from_request()
    if not audio_bytes: return jsonify({"error":"no audio"}), 400
    lang = request.form.get("lang","auto") or (request.get_json(force=True,silent=True) or {}).get("lang","auto")
    verbose = (request.form.get("verbose","") or "").lower()=="true"
    result, err = _do_stt(audio_bytes, fn, lang, verbose)
    if result is None: return jsonify({"error": err}), 502
    if isinstance(result, dict): return jsonify(result)
    return jsonify({"text": result})

# ════════════════════════════════════════════════════════
#  /api/subtitle — Audio → timestamped SRT (FIXED)
# ════════════════════════════════════════════════════════
def _srt_time(s):
    h=int(s//3600); m=int((s%3600)//60); sc=int(s%60); ms=int((s%1)*1000)
    return f"{h:02d}:{m:02d}:{sc:02d},{ms:03d}"
def _to_srt(blocks): return "\n\n".join(f"{b['n']}\n{b['s']} --> {b['e']}\n{b['t']}" for b in blocks)
def _to_bilingual(o,t): return "\n\n".join(
    f"{a['n']}\n{a['s']} --> {a['e']}\n{a['t']}\n{b['t']}" for a,b in zip(o,t))

@app.route("/api/subtitle", methods=["POST"])
def subtitle():
    audio_bytes, fn = _get_audio_from_request()
    if not audio_bytes: return jsonify({"error":"no audio file"}), 400
    target_lang = request.form.get("target_lang","Arabic")
    source_lang = request.form.get("source_lang","Auto-Detect")

    # STT with segments
    data, err = _do_stt(audio_bytes, fn, "auto", verbose=True)
    if data is None: return jsonify({"error": err or "STT failed"}), 502

    segments = data.get("segments", [])
    if not segments:
        # Fallback: treat whole text as one segment
        txt = data.get("text","").strip()
        if not txt: return jsonify({"error":"No speech found"}), 400
        segments = [{"start":0,"end":0,"text":txt}]

    info = LANGS.get(target_lang, {}); src_g = LANGS.get(source_lang,{}).get("g","auto")
    orig_b=[]; trans_b=[]
    for i,seg in enumerate(segments,1):
        txt = seg.get("text","").strip()
        b = {"n":str(i),"s":_srt_time(seg.get("start",0)),"e":_srt_time(seg.get("end",0)),"t":txt}
        orig_b.append(b)
        # translate
        tr, _ = _translate_text(txt, target_lang, source_lang)
        trans_b.append({**b, "t": tr or txt})

    return jsonify({
        "original_srt":   _to_srt(orig_b),
        "translated_srt": _to_srt(trans_b),
        "bilingual_srt":  _to_bilingual(orig_b,trans_b),
        "count": len(orig_b), "segments": trans_b,
    })

# ════════════════════════════════════════════════════════
#  /api/file — extract text from PDF/DOCX/TXT then translate
# ════════════════════════════════════════════════════════
@app.route("/api/file", methods=["POST"])
def file_translate():
    f = request.files.get("file")
    if not f: return jsonify({"error":"no file"}), 400
    target_lang = request.form.get("target_lang","Arabic")
    source_lang = request.form.get("source_lang","Auto-Detect")
    fb = f.read(); fn = f.filename or "file.txt"
    ext = fn.rsplit(".",1)[-1].lower()
    extracted = ""; err = ""

    if ext == "txt":
        for enc in ("utf-8","windows-1256","latin-1"):
            try: extracted = fb.decode(enc); break
            except: pass
    elif ext == "pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(fb)) as pdf:
                extracted = "\n".join(p.extract_text() or "" for p in pdf.pages)
        except Exception as e: err = str(e)
    elif ext == "docx":
        try:
            import docx as _docx
            d = _docx.Document(io.BytesIO(fb))
            extracted = "\n".join(p.text for p in d.paragraphs)
        except Exception as e: err = str(e)
    elif ext in ("xlsx","xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(fb), data_only=True)
            cells = [str(c.value) for sh in wb.worksheets
                     for row in sh.iter_rows() for c in row if c.value]
            extracted = "\n".join(cells)
        except Exception as e: err = str(e)

    if not extracted.strip():
        return jsonify({"error": f"Could not extract text: {err or 'empty file'}"}), 400

    # Translate in chunks (1400 chars each)
    chunks = [extracted[i:i+1400] for i in range(0,len(extracted),1400)]
    parts = []
    for ch in chunks:
        tr, _ = _translate_text(ch, target_lang, source_lang)
        parts.append(tr or ch)
    return jsonify({"original": extracted[:3000], "translated": "\n".join(parts), "chars": len(extracted)})

# ════════════════════════════════════════════════════════
#  /api/group — multi-speaker STT + translate
# ════════════════════════════════════════════════════════
_ICONS = ["🧑","👤","👩","👱","🧔","🧕","👲","🧑‍💼","👩‍💼","🙍"]

def _detect_lang_code(text):
    ar = sum(1 for c in text if "\u0600"<=c<="\u06FF")/max(len(text),1)
    cy = sum(1 for c in text if "\u0400"<=c<="\u04FF")/max(len(text),1)
    cj = sum(1 for c in text if "\u4E00"<=c<="\u9FFF")/max(len(text),1)
    if ar>0.12: return "ar","Arabic"
    if cy>0.12: return "ru","Russian"
    if cj>0.12: return "zh","Chinese"
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed=42
        code=detect(text)
        names={"en":"English","fr":"French","de":"German","es":"Spanish","it":"Italian",
               "pt":"Portuguese","ja":"Japanese","ko":"Korean","tr":"Turkish","ar":"Arabic",
               "ru":"Russian","zh":"Chinese","nl":"Dutch","pl":"Polish","uk":"Ukrainian"}
        return code, names.get(code, code.capitalize())
    except Exception: pass
    return "en","English"

def _group_segments(segs, gap=0.6):
    if not segs: return []
    groups=[]; cur=[segs[0]]
    for i in range(1,len(segs)):
        if segs[i].get("start",0)-segs[i-1].get("end",0)>=gap:
            groups.append(cur); cur=[]
        cur.append(segs[i])
    if cur: groups.append(cur)
    return groups

@app.route("/api/group", methods=["POST"])
def group():
    audio_bytes, fn = _get_audio_from_request()
    if not audio_bytes: return jsonify({"error":"no audio"}), 400
    target_lang = request.form.get("target_lang","Arabic") or \
                  (request.get_json(force=True,silent=True) or {}).get("target_lang","Arabic")

    data, err = _do_stt(audio_bytes, fn, "auto", verbose=True)
    if data is None: return jsonify({"error": err}), 502

    segs = data.get("segments",[])
    full = data.get("text","").strip()
    results = []

    if not segs:
        if not full: return jsonify({"error":"No speech"}), 400
        lc,ln = _detect_lang_code(full)
        tr,eng = _translate_text(full, target_lang, ln)
        return jsonify({"results":[{"spk":1,"icon":_ICONS[0],"lang":ln,
                        "orig":full,"trans":tr or "","eng":eng,"t0":0,"t1":0}]})

    groups = _group_segments(segs)
    lang_to_spk={}; spk_n=1
    for grp in groups:
        txt=" ".join(s.get("text","").strip() for s in grp).strip()
        if not txt: continue
        lc,ln = _detect_lang_code(txt)
        if lc not in lang_to_spk: lang_to_spk[lc]=spk_n; spk_n+=1
        spk=lang_to_spk[lc]; icon=_ICONS[min(spk-1,len(_ICONS)-1)]
        tr,eng = _translate_text(txt, target_lang, ln)
        results.append({"spk":spk,"icon":icon,"lang":ln,
                        "orig":txt,"trans":tr or "","eng":eng,
                        "t0":grp[0].get("start",0),"t1":grp[-1].get("end",0)})

    return jsonify({"results": results}) if results else jsonify({"error":"No speech"}), 400

# ════════════════════════════════════════════════════════
#  /api/tts — Text-to-Speech (gTTS)
# ════════════════════════════════════════════════════════
@app.route("/api/tts", methods=["POST"])
def tts():
    d = request.get_json(force=True) or {}
    text = (d.get("text") or "").strip()[:600]
    lang = d.get("lang","en")
    if not text: return jsonify({"error":"no text"}), 400
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg", download_name="tts.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ════════════════════════════════════════════════════════
#  /api/chat — AI Chat
# ════════════════════════════════════════════════════════
_AI_SYS="""أنت مساعد ترجمة ذكي محترف في HN Translator.
قدراتك الكاملة:
▸ ترجمة ذكية: المعنى والسياق لا الكلمات — الأمثال بمقابلها الثقافي الحقيقي
▸ اللهجات والعامية: مصري خليجي شامي مغربي عراقي يمني وكل عاميات العالم
▸ تصحيح إملاء ونحو وإعراب مع شرح التغييرات
▸ تلخيص وشرح مصطلحات وتحليل لغوي وتحويل الأسلوب
▸ الإجابة عن أي سؤال لغوي أو ثقافي
القاعدة: افهم القصد دائماً — ردودك مباشرة وواضحة بلا مقدمات زائدة."""

@app.route("/api/chat", methods=["POST"])
def chat():
    if not GROQ_KEY: return jsonify({"error":"GROQ_API_KEY not configured"}), 503
    d=request.get_json(force=True) or {}
    msg=(d.get("message") or "").strip()
    if not msg: return jsonify({"error":"no message"}), 400
    src=d.get("source_text","")[:600]; cur=d.get("current_translation","")[:400]
    sl=d.get("source_lang","Auto-Detect"); tl=d.get("target_lang","Arabic")
    hist=d.get("history",[])[-8:]
    ctx=(f"السياق:\n- النص الأصلي ({sl}): {src or 'لا يوجد'}\n"
         f"- الترجمة ({tl}): {cur or 'لا يوجد'}\n- الاتجاه: {sl}→{tl}\n\nطلب: {msg}")
    msgs=[{"role":"system","content":_AI_SYS}]
    for h in hist:
        if h.get("role") in ("user","assistant") and h.get("content"):
            msgs.append({"role":h["role"],"content":h["content"]})
    msgs.append({"role":"user","content":ctx})
    for model in [_M_SMART,_M_FAST]:
        reply,err=_groq_chat(msgs,model=model)
        if reply: return jsonify({"reply":reply,"model":model})
        if err=="rate_limit": continue
        return jsonify({"error":f"Groq error: {err}"}),502
    return jsonify({"error":"Rate limit — try again in a moment"}),429

# ════════════════════════════════════════════════════════
#  /api/spell — Spell check
# ════════════════════════════════════════════════════════
@app.route("/api/spell", methods=["POST"])
def spell():
    if not GROQ_KEY: return jsonify({"suggestions":[]}), 200
    d=request.get_json(force=True) or {}
    text=(d.get("text") or "").strip(); lang=d.get("lang","Auto-Detect")
    if len(text)<4: return jsonify({"suggestions":[]})
    prompt=(f'Check this {lang} text for errors: "{text[:400]}"\n'
            'Return JSON array only: [{"wrong":"...","correct":"...","reason":"..."}] Max 3. If no errors: []')
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":_M_FAST,"messages":[{"role":"user","content":prompt}],"max_tokens":200,"temperature":0.1},
            timeout=12)
        if r.status_code==200:
            raw=re.sub(r"```json|```","",r.json()["choices"][0]["message"]["content"].strip()).strip()
            items=json.loads(raw)
            return jsonify({"suggestions":[x for x in items
                if isinstance(x,dict) and x.get("wrong")!=x.get("correct")][:3]})
    except Exception: pass
    return jsonify({"suggestions":[]})

# ════════════════════════════════════════════════════════
#  /api/langs  /api/health
# ════════════════════════════════════════════════════════
@app.route("/api/langs", methods=["GET"])
def get_langs(): return jsonify({"languages":list(LANGS.keys())})

@app.route("/api/health", methods=["GET"])
def health(): return jsonify({"status":"ok","groq":bool(GROQ_KEY),"deepl":bool(DEEPL_KEY)})

# ── Vercel WSGI ──────────────────────────────────────────
handler = app
