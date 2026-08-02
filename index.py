import os, json, base64, re, io
from flask import Flask, request, jsonify, send_file
import requests

app = Flask(__name__)

# ── Keys ──────────────────────────────────────────────────────
GROQ_KEY  = os.environ.get("GROQ_API_KEY","").strip()
DEEPL_KEY = os.environ.get("DEEPL_API_KEY","").strip()
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
    "Persian":"fa","Hebrew":"iw","Urdu":"ur",
}

# ── CORS ────────────────────────────────────────────────────────
@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return r

@app.route("/api/<path:p>", methods=["OPTIONS"])
def opts(p): return jsonify({"ok":True})

# ── Translation helper ──────────────────────────────────────────
def do_translate(text, target, source="Auto-Detect"):
    tgt_g = LANGS.get(target,"en"); src_g = LANGS.get(source,"auto")
    # DeepL
    if DEEPL_KEY and target in DEEPL_CODES:
        ep = ("https://api-free.deepl.com/v2/translate" if DEEPL_KEY.endswith(":fx")
              else "https://api.deepl.com/v2/translate")
        try:
            r = requests.post(ep,
                headers={"Authorization":f"DeepL-Auth-Key {DEEPL_KEY}"},
                data={"text":text,"target_lang":DEEPL_CODES[target]}, timeout=10)
            if r.status_code == 200:
                return r.json()["translations"][0]["text"], "DeepL ✦"
        except: pass
    # Google
    try:
        from deep_translator import GoogleTranslator
        t = GoogleTranslator(source=src_g,target=tgt_g).translate(text)
        if t: return t, "Google"
    except: pass
    # MyMemory
    try:
        from deep_translator import MyMemoryTranslator
        s = "en" if src_g in ("auto",) else src_g
        t = MyMemoryTranslator(source=s,target=tgt_g).translate(text)
        if t: return t, "MyMemory"
    except: pass
    return None, "failed"

# ── /api/translate ──────────────────────────────────────────────
@app.route("/api/translate", methods=["POST"])
def translate():
    d = request.get_json(force=True) or {}
    text = (d.get("text") or "").strip()
    if not text: return jsonify({"error":"no text"}), 400
    res, eng = do_translate(text, d.get("target","Arabic"), d.get("source","Auto-Detect"))
    if res: return jsonify({"translated":res,"engine":eng})
    return jsonify({"error":"Translation failed"}), 502

# ── /api/ocr ─────────────────────────────────────────────────────
@app.route("/api/ocr", methods=["POST"])
def ocr():
    if not GROQ_KEY: return jsonify({"error":"GROQ_API_KEY not set"}), 503
    d = request.get_json(force=True) or {}
    img = d.get("image","")
    mime = "image/jpeg"
    if "," in img:
        hdr, img = img.split(",",1)
        if ":" in hdr: mime = hdr.split(":")[1].split(";")[0]
    if not img: return jsonify({"error":"no image"}), 400
    for model in ["meta-llama/llama-4-scout-17b-16e-instruct",
                  "llama-3.2-90b-vision-preview",
                  "llama-3.2-11b-vision-preview"]:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":model,"temperature":0,"max_tokens":2048,
                      "messages":[{"role":"user","content":[
                          {"type":"image_url","image_url":{"url":f"data:{mime};base64,{img}"}},
                          {"type":"text","text":"Extract ALL text from this image. Return ONLY the raw text."}
                      ]}]}, timeout=30)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                if txt: return jsonify({"text":txt,"model":model})
            if r.status_code in (404,400): continue
        except: continue
    return jsonify({"error":"OCR unavailable"}), 502

# ── /api/stt ─────────────────────────────────────────────────────
def _wl(c):
    if not c or c in ("auto","Auto-Detect"): return None
    return {"zh-CN":"zh","iw":"he"}.get(c, c[:2])

def _stt(audio_bytes, fn, lang, verbose=False):
    if not GROQ_KEY: return None, "no key"
    lc = _wl(lang)
    ext = fn.rsplit(".",1)[-1].lower()
    mime = {"wav":"audio/wav","mp3":"audio/mpeg","mp4":"video/mp4",
            "m4a":"audio/mp4","ogg":"audio/ogg","webm":"audio/webm"}.get(ext,"audio/webm")
    files = {"file":(fn, audio_bytes, mime),
             "model":(None,"whisper-large-v3-turbo"),
             "response_format":(None,"verbose_json" if verbose else "json")}
    if verbose: files["timestamp_granularities[]"] = (None,"segment")
    if lc: files["language"] = (None, lc)
    try:
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization":f"Bearer {GROQ_KEY}"},files=files,timeout=90)
        if r.status_code == 200:
            d = r.json()
            if verbose: return d, None
            t = d.get("text","").strip()
            return (t, None) if t else (None,"No speech")
        return None, f"STT {r.status_code}"
    except Exception as e: return None, str(e)

@app.route("/api/stt",   methods=["POST"])
@app.route("/api/voice", methods=["POST"])
def stt():
    f = request.files.get("audio")
    if f: ab, fn = f.read(), f.filename or "audio.webm"
    else:
        ab = base64.b64decode((request.get_json(force=True,silent=True) or {}).get("audio_b64",""))
        fn = "audio.wav"
    if not ab: return jsonify({"error":"no audio"}), 400
    lang = request.form.get("lang","auto") or "auto"
    verbose = request.form.get("verbose","false") == "true"
    result, err = _stt(ab, fn, lang, verbose)
    if result is None: return jsonify({"error":err}), 502
    if isinstance(result, dict): return jsonify(result)
    return jsonify({"text": result})

# ── /api/subtitle ─────────────────────────────────────────────────
def _s2t(s):
    h=int(s//3600);m=int((s%3600)//60);sc=int(s%60);ms=int((s%1)*1000)
    return f"{h:02d}:{m:02d}:{sc:02d},{ms:03d}"

@app.route("/api/subtitle", methods=["POST"])
def subtitle():
    f = request.files.get("audio")
    if not f: return jsonify({"error":"no audio"}), 400
    ab = f.read(); fn = f.filename or "audio.webm"
    tgt = request.form.get("target_lang","Arabic")
    data, err = _stt(ab, fn, "auto", verbose=True)
    if data is None: return jsonify({"error":err}), 502
    segs = data.get("segments",[])
    if not segs:
        txt = data.get("text","").strip()
        if not txt: return jsonify({"error":"No speech"}), 400
        segs = [{"start":0,"end":0,"text":txt}]
    orig_b=[]; trans_b=[]
    for i,seg in enumerate(segs,1):
        t = seg.get("text","").strip()
        b = {"n":str(i),"s":_s2t(seg.get("start",0)),"e":_s2t(seg.get("end",0)),"t":t}
        orig_b.append(b)
        tr,_ = do_translate(t, tgt)
        trans_b.append({**b,"t":tr or t})
    to_srt = lambda bl: "\n\n".join(f"{b['n']}\n{b['s']} --> {b['e']}\n{b['t']}" for b in bl)
    bi = "\n\n".join(f"{o['n']}\n{o['s']} --> {o['e']}\n{o['t']}\n{t['t']}" for o,t in zip(orig_b,trans_b))
    return jsonify({"original_srt":to_srt(orig_b),"translated_srt":to_srt(trans_b),
                    "bilingual_srt":bi,"count":len(orig_b),"segments":trans_b})

# ── /api/chat ─────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    if not GROQ_KEY: return jsonify({"error":"no key"}), 503
    d = request.get_json(force=True) or {}
    msg = (d.get("message") or "").strip()
    if not msg: return jsonify({"error":"no message"}), 400
    sys_msg = """أنت مساعد ترجمة ذكي في HN Translator.
قدراتك: ترجمة بالمعنى لا بالحرف — الأمثال بمقابلها الثقافي — اللهجات العربية وعاميات العالم — تصحيح إملاء ونحو — تلخيص وشرح مصطلحات.
ردودك مباشرة بلا مقدمات."""
    ctx = (f"النص الأصلي: {d.get('source_text','')[:400]}\n"
           f"الترجمة الحالية: {d.get('current_translation','')[:300]}\n"
           f"الاتجاه: {d.get('source_lang','?')} → {d.get('target_lang','?')}\n"
           f"طلب: {msg}")
    msgs = [{"role":"system","content":sys_msg}]
    for h in d.get("history",[])[-6:]:
        if h.get("role") in ("user","assistant"): msgs.append(h)
    msgs.append({"role":"user","content":ctx})
    for model in [M_SMART, M_FAST]:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":model,"messages":msgs,"max_tokens":900,"temperature":0.35},
                timeout=30)
            if r.status_code == 200:
                return jsonify({"reply":r.json()["choices"][0]["message"]["content"].strip(),"model":model})
            if r.status_code == 429: continue
        except: pass
    return jsonify({"error":"try again"}), 429

# ── /api/spell ────────────────────────────────────────────────────
@app.route("/api/spell", methods=["POST"])
def spell():
    if not GROQ_KEY: return jsonify({"suggestions":[]})
    d = request.get_json(force=True) or {}
    text = (d.get("text") or "").strip()
    if len(text) < 4: return jsonify({"suggestions":[]})
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
            json={"model":M_FAST,"max_tokens":200,"temperature":0.1,
                  "messages":[{"role":"user","content":
                    f'Check for errors: "{text[:300]}"\nReturn JSON array only: [{{"wrong":"","correct":"","reason":""}}] or []'}]},
            timeout=12)
        if r.status_code == 200:
            raw = re.sub(r"```\w*|```","",r.json()["choices"][0]["message"]["content"]).strip()
            items = json.loads(raw)
            return jsonify({"suggestions":[x for x in items if x.get("wrong")!=x.get("correct")][:3]})
    except: pass
    return jsonify({"suggestions":[]})

# ── /api/tts ─────────────────────────────────────────────────────
@app.route("/api/tts", methods=["POST"])
def tts():
    d = request.get_json(force=True) or {}
    text = (d.get("text") or "").strip()[:500]
    lang = d.get("lang","en")
    if not text: return jsonify({"error":"no text"}), 400
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg", download_name="tts.mp3")
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── /api/group ────────────────────────────────────────────────────
@app.route("/api/group", methods=["POST"])
def group():
    f = request.files.get("audio")
    if not f: return jsonify({"error":"no audio"}), 400
    ab = f.read(); fn = f.filename or "audio.webm"
    tgt = request.form.get("target_lang","Arabic")
    data, err = _stt(ab, fn, "auto", verbose=True)
    if data is None: return jsonify({"error":err}), 502
    segs = data.get("segments",[]); full = data.get("text","").strip()
    icons = ["🧑","👤","👩","👱","🧔","🧕","👲","🧑‍💼","👩‍💼","🙍"]
    def dlang(text):
        ar = sum(1 for c in text if "\u0600"<=c<="\u06FF")/max(len(text),1)
        if ar>0.12: return "ar","Arabic"
        try:
            from langdetect import detect, DetectorFactory; DetectorFactory.seed=42
            code=detect(text)
            n={"en":"English","ar":"Arabic","fr":"French","de":"German","es":"Spanish",
               "ru":"Russian","zh":"Chinese","ja":"Japanese","ko":"Korean","tr":"Turkish"}
            return code,n.get(code,code.capitalize())
        except: return "en","English"
    if not segs:
        lc,ln=dlang(full or ""); tr,eng=do_translate(full,tgt,ln)
        return jsonify({"results":[{"spk":1,"icon":icons[0],"lang":ln,"orig":full,"trans":tr or "","eng":eng,"t0":0,"t1":0}]})
    groups=[]; cur=[segs[0]]
    for i in range(1,len(segs)):
        if segs[i].get("start",0)-segs[i-1].get("end",0)>=0.6: groups.append(cur); cur=[]
        cur.append(segs[i])
    if cur: groups.append(cur)
    results=[]; l2s={}; spk_n=1
    for grp in groups:
        txt=" ".join(s.get("text","").strip() for s in grp).strip()
        if not txt: continue
        lc,ln=dlang(txt)
        if lc not in l2s: l2s[lc]=spk_n; spk_n+=1
        spk=l2s[lc]
        tr,eng=do_translate(txt,tgt,ln)
        results.append({"spk":spk,"icon":icons[min(spk-1,9)],"lang":ln,
                        "orig":txt,"trans":tr or "","eng":eng,
                        "t0":grp[0].get("start",0),"t1":grp[-1].get("end",0)})
    return jsonify({"results":results}) if results else jsonify({"error":"No speech"}),400

# ── /api/health ───────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok":True,"groq":bool(GROQ_KEY),"deepl":bool(DEEPL_KEY)})

handler = app
ENDOFPY
python3 -c "import ast;src=open('/mnt/user-data/outputs/hn_vercel/api/index.py').read();ast.parse(src);print('✅ Syntax OK',src.count(chr(10)),'lines')"
