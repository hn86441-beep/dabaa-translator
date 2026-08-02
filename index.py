# HN Translator – Backend (Vercel Serverless)
import os, json, base64, re, io
from flask import Flask, request, jsonify, send_file
import requests

app = Flask(__name__)

# ── Keys (Vercel Dashboard → Settings → Environment Variables) ─────
GROQ_KEY   = os.environ.get("GROQ_API_KEY",  "").strip()
DEEPL_KEY  = os.environ.get("DEEPL_API_KEY", "").strip()
COHERE_KEY = os.environ.get("COHERE_API_KEY","").strip()

M_FAST, M_SMART = "llama-3.1-8b-instant", "llama-3.3-70b-versatile"

LANGS = {
    "Auto-Detect":"auto","Arabic":"ar","English":"en","Russian":"ru",
    "Chinese":"zh-CN","German":"de","Spanish":"es","French":"fr",
    "Portuguese":"pt","Italian":"it","Japanese":"ja","Korean":"ko",
    "Turkish":"tr","Dutch":"nl","Polish":"pl","Ukrainian":"uk",
    "Swedish":"sv","Danish":"da","Finnish":"fi","Romanian":"ro",
    "Hungarian":"hu","Czech":"cs","Bulgarian":"bg","Greek":"el",
    "Indonesian":"id","Hindi":"hi","Persian":"fa","Hebrew":"iw","Urdu":"ur",
}
DEEPL_CODES = {
    "Arabic":"AR","English":"EN-US","Russian":"RU","Chinese":"ZH","German":"DE",
    "Spanish":"ES","French":"FR","Portuguese":"PT-PT","Italian":"IT","Japanese":"JA",
    "Korean":"KO","Turkish":"TR","Dutch":"NL","Polish":"PL","Ukrainian":"UK",
    "Swedish":"SV","Danish":"DA","Finnish":"FI","Romanian":"RO","Hungarian":"HU",
    "Czech":"CS","Bulgarian":"BG","Greek":"EL","Indonesian":"ID",
}
GTTS_CODES = {
    "Arabic":"ar","English":"en","Russian":"ru","Chinese":"zh-cn","German":"de",
    "Spanish":"es","French":"fr","Portuguese":"pt","Italian":"it","Japanese":"ja",
    "Korean":"ko","Turkish":"tr","Dutch":"nl","Polish":"pl","Ukrainian":"uk",
    "Swedish":"sv","Danish":"da","Finnish":"fi","Romanian":"ro","Hungarian":"hu",
    "Czech":"cs","Bulgarian":"bg","Greek":"el","Indonesian":"id","Hindi":"hi",
    "Persian":"fa","Hebrew":"iw","Urdu":"ur","Auto-Detect":"en",
}

# ── CORS ──────────────────────────────────────────────────────────
@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

@app.route("/api/<path:p>", methods=["OPTIONS"])
def opts(p): return jsonify({"ok": True})

# ── helpers ───────────────────────────────────────────────────────
def _wl(c):
    if not c or c in ("auto","Auto-Detect"): return None
    return {"zh-CN":"zh","zh-cn":"zh","iw":"he"}.get(c, c[:2])

def _mime(fn):
    ext = (fn or "").rsplit(".",1)[-1].lower()
    return {"wav":"audio/wav","mp3":"audio/mpeg","mp4":"video/mp4",
            "m4a":"audio/mp4","ogg":"audio/ogg","webm":"audio/webm",
            "mov":"video/quicktime"}.get(ext, "audio/webm")

def _do_translate(text, target, source="Auto-Detect"):
    tgt_g = LANGS.get(target, "en")
    src_g = LANGS.get(source, "auto")
    if DEEPL_KEY and target in DEEPL_CODES:
        ep = ("https://api-free.deepl.com/v2/translate" if DEEPL_KEY.endswith(":fx")
              else "https://api.deepl.com/v2/translate")
        try:
            r = requests.post(ep,
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_KEY}"},
                data={"text": text, "target_lang": DEEPL_CODES[target]}, timeout=10)
            if r.status_code == 200:
                return r.json()["translations"][0]["text"], "DeepL ✦"
        except: pass
    try:
        from deep_translator import GoogleTranslator
        t = GoogleTranslator(source=src_g, target=tgt_g).translate(text)
        if t: return t, "Google"
    except: pass
    try:
        from deep_translator import MyMemoryTranslator
        s = "en" if src_g == "auto" else src_g
        t = MyMemoryTranslator(source=s, target=tgt_g).translate(text)
        if t: return t, "MyMemory"
    except: pass
    return None, "failed"

def _detect_lang(text):
    ar = sum(1 for c in text if "\u0600"<=c<="\u06FF") / max(len(text),1)
    cy = sum(1 for c in text if "\u0400"<=c<="\u04FF") / max(len(text),1)
    if ar > 0.12: return "ar", "Arabic"
    if cy > 0.12: return "ru", "Russian"
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 42
        code = detect(text)
        names = {"en":"English","ar":"Arabic","fr":"French","de":"German",
                 "es":"Spanish","ru":"Russian","zh":"Chinese","ja":"Japanese",
                 "ko":"Korean","tr":"Turkish","it":"Italian","pt":"Portuguese"}
        return code, names.get(code, code.capitalize())
    except: return "en", "English"

# ── /api/translate ─────────────────────────────────────────────────
@app.route("/api/translate", methods=["POST"])
def translate():
    d = request.get_json(force=True) or {}
    text = (d.get("text") or "").strip()
    if not text: return jsonify({"error": "no text"}), 400
    res, eng = _do_translate(text, d.get("target","Arabic"), d.get("source","Auto-Detect"))
    if res: return jsonify({"translated": res, "engine": eng})
    return jsonify({"error": "فشلت جميع محركات الترجمة"}), 502

# ── /api/stt — Groq Whisper → Cohere fallback ─────────────────────
def _groq_stt(audio_bytes, fn, lang, verbose=False):
    if not GROQ_KEY: return None, "GROQ_API_KEY غير مضبوط"
    lc = _wl(lang)
    # Vercel has body size limit — check audio size
    if len(audio_bytes) > 24 * 1024 * 1024:
        return None, "الملف الصوتي كبير جداً (الحد 24MB)"
    files = {
        "file": (fn, audio_bytes, _mime(fn)),
        "model": (None, "whisper-large-v3-turbo"),
        "response_format": (None, "verbose_json" if verbose else "json"),
    }
    if verbose: files["timestamp_granularities[]"] = (None, "segment")
    if lc: files["language"] = (None, lc)
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            files=files, timeout=55)
        if r.status_code == 200:
            d = r.json()
            if verbose: return d, None
            t = d.get("text","").strip()
            return (t, None) if t else (None, "لم يُكتشف كلام")
        err = r.json().get("error",{}).get("message","") if r.headers.get("content-type","").startswith("application/json") else r.text[:100]
        return None, f"خطأ في التعرف على الصوت: {err}"
    except requests.exceptions.Timeout:
        return None, "انتهت مهلة الاتصال — الملف طويل جداً"
    except Exception as e:
        return None, str(e)

def _cohere_stt(audio_bytes, fn, lang):
    if not COHERE_KEY: return None, "COHERE_API_KEY غير مضبوط"
    lc = _wl(lang) or "en"
    try:
        from requests_toolbelt import MultipartEncoder
        fields = {"language": lc, "model": "cohere-transcribe-03-2026",
                  "file": (fn, audio_bytes, _mime(fn))}
        enc = MultipartEncoder(fields=fields)
        r = requests.post("https://api.cohere.com/v2/audio/transcriptions",
            headers={"Authorization": f"Bearer {COHERE_KEY}",
                     "Content-Type": enc.content_type},
            data=enc, timeout=55)
        if r.status_code == 200:
            t = r.json().get("text","").strip()
            return (t, None) if t else (None, "لم يُكتشف كلام")
        return None, f"Cohere {r.status_code}"
    except ImportError:
        # fallback without MultipartEncoder
        files = {"file": (fn, audio_bytes, _mime(fn)),
                 "language": (None, lc),
                 "model": (None, "cohere-transcribe-03-2026")}
        try:
            r = requests.post("https://api.cohere.com/v2/audio/transcriptions",
                headers={"Authorization": f"Bearer {COHERE_KEY}"},
                files=files, timeout=55)
            if r.status_code == 200:
                t = r.json().get("text","").strip()
                return (t, None) if t else (None, "لم يُكتشف كلام")
        except Exception as e: return None, str(e)
    except Exception as e:
        return None, str(e)

def _stt(audio_bytes, fn, lang, verbose=False):
    if GROQ_KEY:
        result, err = _groq_stt(audio_bytes, fn, lang, verbose)
        if result is not None: return result, None
        # Try Cohere only if Groq failed (not for verbose/subtitle mode)
        if not verbose and COHERE_KEY:
            result2, err2 = _cohere_stt(audio_bytes, fn, lang)
            if result2: return result2, None
        return None, err
    if COHERE_KEY:
        return _cohere_stt(audio_bytes, fn, lang)
    return None, "لم يتم ضبط أي مفتاح API للتعرف على الصوت"

@app.route("/api/stt",   methods=["POST"])
@app.route("/api/voice", methods=["POST"])
def stt():
    f = request.files.get("audio")
    if f:
        ab, fn = f.read(), f.filename or "audio.webm"
    else:
        d = request.get_json(force=True, silent=True) or {}
        b64 = d.get("audio_b64","")
        if not b64: return jsonify({"error": "لا يوجد ملف صوتي"}), 400
        ab, fn = base64.b64decode(b64), "audio.wav"
    lang = request.form.get("lang","auto") or "auto"
    verbose = request.form.get("verbose","false") == "true"
    result, err = _stt(ab, fn, lang, verbose)
    if result is None: return jsonify({"error": err}), 502
    if isinstance(result, dict): return jsonify(result)
    return jsonify({"text": result})

# ── /api/ocr — Groq Vision ─────────────────────────────────────────
@app.route("/api/ocr", methods=["POST"])
def ocr():
    if not GROQ_KEY:
        return jsonify({"error": "GROQ_API_KEY غير مضبوط في Vercel"}), 503
    d = request.get_json(force=True) or {}
    img = d.get("image","")
    mime = "image/jpeg"
    if "," in img:
        hdr, img = img.split(",",1)
        if ":" in hdr: mime = hdr.split(":")[1].split(";")[0]
    if not img: return jsonify({"error": "لا توجد صورة"}), 400
    # Try models in order of capability
    for model in [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.2-90b-vision-preview",
        "llama-3.2-11b-vision-preview",
    ]:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}",
                         "Content-Type": "application/json"},
                json={"model": model, "temperature": 0, "max_tokens": 2048,
                      "messages":[{"role":"user","content":[
                          {"type":"image_url",
                           "image_url":{"url":f"data:{mime};base64,{img}","detail":"high"}},
                          {"type":"text","text":
                           "Extract ALL text from this image exactly as written. "
                           "Keep original language and formatting. "
                           "Return ONLY the extracted text, nothing else."}
                      ]}]},
                timeout=30)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                if txt: return jsonify({"text": txt, "model": model})
                continue
            if r.status_code in (404, 400, 422): continue
            if r.status_code == 429:
                return jsonify({"error": "تم تجاوز حد الاستخدام — حاول بعد قليل"}), 429
        except: continue
    return jsonify({"error": "خدمة قراءة الصور غير متاحة حالياً"}), 502

# ── /api/subtitle ─────────────────────────────────────────────────
def _srt_t(s):
    h=int(s//3600); m=int((s%3600)//60); sc=int(s%60); ms=int((s%1)*1000)
    return f"{h:02d}:{m:02d}:{sc:02d},{ms:03d}"

@app.route("/api/subtitle", methods=["POST"])
def subtitle():
    f = request.files.get("audio")
    if not f: return jsonify({"error": "لا يوجد ملف"}), 400
    ab = f.read(); fn = f.filename or "audio.webm"
    tgt = request.form.get("target_lang","Arabic")
    data, err = _stt(ab, fn, "auto", verbose=True)
    if data is None: return jsonify({"error": err}), 502
    segs = data.get("segments",[])
    if not segs:
        txt = data.get("text","").strip()
        if not txt: return jsonify({"error": "لم يُكتشف كلام في الملف"}), 400
        segs = [{"start":0,"end":0,"text":txt}]
    orig_b=[]; trans_b=[]
    for i,seg in enumerate(segs,1):
        t = seg.get("text","").strip()
        b = {"n":str(i),"s":_srt_t(seg.get("start",0)),
             "e":_srt_t(seg.get("end",0)),"t":t}
        orig_b.append(b)
        tr,_ = _do_translate(t, tgt)
        trans_b.append({**b,"t":tr or t})
    to_srt = lambda bl: "\n\n".join(
        f"{b['n']}\n{b['s']} --> {b['e']}\n{b['t']}" for b in bl)
    bi = "\n\n".join(
        f"{o['n']}\n{o['s']} --> {o['e']}\n{o['t']}\n{t['t']}"
        for o,t in zip(orig_b,trans_b))
    return jsonify({
        "original_srt": to_srt(orig_b),
        "translated_srt": to_srt(trans_b),
        "bilingual_srt": bi,
        "count": len(orig_b),
        "segments": trans_b,
    })

# ── /api/file ─────────────────────────────────────────────────────
@app.route("/api/file", methods=["POST"])
def file_tr():
    f = request.files.get("file")
    if not f: return jsonify({"error": "لا يوجد ملف"}), 400
    tgt = request.form.get("target_lang","Arabic")
    src = request.form.get("source_lang","Auto-Detect")
    fb = f.read(); fn = f.filename or "file.txt"
    ext = fn.rsplit(".",1)[-1].lower()
    extracted = ""
    if ext == "txt":
        for enc in ("utf-8","windows-1256","latin-1"):
            try: extracted = fb.decode(enc); break
            except: pass
    elif ext == "pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(fb)) as pdf:
                extracted = "\n".join(p.extract_text() or "" for p in pdf.pages)
        except Exception as e: return jsonify({"error":f"خطأ في قراءة PDF: {e}"}),500
    elif ext == "docx":
        try:
            import docx as _d
            doc = _d.Document(io.BytesIO(fb))
            extracted = "\n".join(p.text for p in doc.paragraphs)
        except Exception as e: return jsonify({"error":f"خطأ في قراءة DOCX: {e}"}),500
    elif ext in ("xlsx","xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(fb), data_only=True)
            extracted = "\n".join(
                str(c.value) for sh in wb.worksheets
                for row in sh.iter_rows() for c in row if c.value)
        except Exception as e: return jsonify({"error":f"خطأ في قراءة Excel: {e}"}),500
    if not extracted.strip():
        return jsonify({"error":"لم يُعثر على نص في الملف"}), 400
    chunks = [extracted[i:i+1400] for i in range(0,len(extracted),1400)]
    parts = []
    for ch in chunks:
        tr,_ = _do_translate(ch, tgt, src)
        parts.append(tr or ch)
    return jsonify({
        "original": extracted[:3000],
        "translated": "\n".join(parts),
        "chars": len(extracted)
    })

# ── /api/group ─────────────────────────────────────────────────────
ICONS = ["🧑","👤","👩","👱","🧔","🧕","👲","🧑‍💼","👩‍💼","🙍"]

@app.route("/api/group", methods=["POST"])
def group():
    f = request.files.get("audio")
    if not f: return jsonify({"error":"لا يوجد ملف صوتي"}), 400
    ab = f.read(); fn = f.filename or "audio.webm"
    tgt = request.form.get("target_lang","Arabic")
    data, err = _stt(ab, fn, "auto", verbose=True)
    if data is None: return jsonify({"error": err}), 502
    segs = data.get("segments",[]); full = data.get("text","").strip()
    if not segs:
        if not full: return jsonify({"error":"لم يُكتشف كلام"}), 400
        lc, ln = _detect_lang(full); tr,eng = _do_translate(full, tgt, ln)
        return jsonify({"results":[{"spk":1,"icon":ICONS[0],"lang":ln,
                        "orig":full,"trans":tr or "","eng":eng,"t0":0,"t1":0}]})
    groups=[]; cur=[segs[0]]
    for i in range(1,len(segs)):
        if segs[i].get("start",0)-segs[i-1].get("end",0) >= 0.6:
            groups.append(cur); cur=[]
        cur.append(segs[i])
    if cur: groups.append(cur)
    results=[]; l2s={}; spk_n=1
    for grp in groups:
        txt = " ".join(s.get("text","").strip() for s in grp).strip()
        if not txt: continue
        lc, ln = _detect_lang(txt)
        if lc not in l2s: l2s[lc] = spk_n; spk_n+=1
        spk = l2s[lc]
        tr, eng = _do_translate(txt, tgt, ln)
        results.append({"spk":spk,"icon":ICONS[min(spk-1,9)],"lang":ln,
                        "orig":txt,"trans":tr or "","eng":eng,
                        "t0":grp[0].get("start",0),"t1":grp[-1].get("end",0)})
    return jsonify({"results":results}) if results else (jsonify({"error":"لم يُكتشف كلام"}), 400)

# ── /api/chat ─────────────────────────────────────────────────────
_SYS = """أنت مساعد ترجمة ذكي محترف.
قدراتك: ترجمة بالمعنى والسياق لا بالحرف — الأمثال بمقابلها الثقافي — اللهجات العربية وعاميات العالم — تصحيح إملاء ونحو — تلخيص وشرح المصطلحات.
قاعدة: افهم القصد دائماً — ردودك مباشرة وواضحة."""

@app.route("/api/chat", methods=["POST"])
def chat():
    if not GROQ_KEY: return jsonify({"error":"GROQ_API_KEY غير مضبوط"}), 503
    d = request.get_json(force=True) or {}
    msg = (d.get("message") or "").strip()
    if not msg: return jsonify({"error":"لا توجد رسالة"}), 400
    ctx = (f"النص الأصلي: {d.get('source_text','')[:400]}\n"
           f"الترجمة: {d.get('current_translation','')[:300]}\n"
           f"الاتجاه: {d.get('source_lang','?')} → {d.get('target_lang','?')}\n"
           f"طلب: {msg}")
    msgs = [{"role":"system","content":_SYS}]
    for h in d.get("history",[])[-6:]:
        if h.get("role") in ("user","assistant"): msgs.append(h)
    msgs.append({"role":"user","content":ctx})
    for model in [M_SMART, M_FAST]:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}",
                         "Content-Type":"application/json"},
                json={"model":model,"messages":msgs,
                      "max_tokens":900,"temperature":0.35},
                timeout=30)
            if r.status_code == 200:
                return jsonify({"reply":r.json()["choices"][0]["message"]["content"].strip()})
            if r.status_code == 429: continue
        except: pass
    return jsonify({"error":"تجاوزت الحد — أعد المحاولة بعد قليل"}), 429

# ── /api/spell ────────────────────────────────────────────────────
@app.route("/api/spell", methods=["POST"])
def spell():
    if not GROQ_KEY: return jsonify({"suggestions":[]})
    d = request.get_json(force=True) or {}
    text = (d.get("text") or "").strip()
    if len(text) < 4: return jsonify({"suggestions":[]})
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}",
                     "Content-Type":"application/json"},
            json={"model":M_FAST,"max_tokens":200,"temperature":0.1,
                  "messages":[{"role":"user","content":
                    f'Find spelling/grammar errors in: "{text[:350]}"\n'
                    'Return JSON array only (no markdown): [{"wrong":"","correct":"","reason":""}]\n'
                    'Max 3 items. If no errors: []'}]},
            timeout=12)
        if r.status_code == 200:
            raw = re.sub(r"```\w*|```","",
                         r.json()["choices"][0]["message"]["content"]).strip()
            items = json.loads(raw)
            return jsonify({"suggestions":[x for x in items
                if isinstance(x,dict) and x.get("wrong") != x.get("correct")][:3]})
    except: pass
    return jsonify({"suggestions":[]})

# ── /api/tts ─────────────────────────────────────────────────────
@app.route("/api/tts", methods=["POST"])
def tts():
    d = request.get_json(force=True) or {}
    text = (d.get("text") or "").strip()[:500]
    lang = d.get("lang","en")
    if not text: return jsonify({"error":"لا يوجد نص"}), 400
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg", download_name="tts.mp3")
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── /api/health ──────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "groq": bool(GROQ_KEY),
        "deepl": bool(DEEPL_KEY),
        "cohere": bool(COHERE_KEY),
    })

handler = app
ENDOFPY
echo "✅ api/index.py: $(wc -l < /mnt/user-data/outputs/hn_vercel/api/index.py) lines"
