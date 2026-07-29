# ════════════════════════════════════════════════════════════════
#  HN Translator — Vercel Serverless Backend
#  All API endpoints in one Flask app
# ════════════════════════════════════════════════════════════════
import os, io, json, base64, re, tempfile
from flask import Flask, request, jsonify, Response
import requests as http
from deep_translator import GoogleTranslator, MyMemoryTranslator
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict

app = Flask(__name__)

# ── Secrets (set in Vercel Dashboard → Settings → Environment Variables) ──
GROQ_KEY   = os.environ.get("GROQ_API_KEY",   "")
DEEPL_KEY  = os.environ.get("DEEPL_API_KEY",  "")
COHERE_KEY = os.environ.get("COHERE_API_KEY", "")

# ── Models ────────────────────────────────────────────────────────
_M_FAST  = "llama-3.1-8b-instant"
_M_SMART = "llama-3.3-70b-versatile"
_M_VISION_PRIMARY  = "meta-llama/llama-4-scout-17b-16e-instruct"
_M_VISION_FALLBACK = "llama-3.2-11b-vision-preview"
_M_WHISPER = "whisper-large-v3-turbo"

# ── Language map ──────────────────────────────────────────────────
LANGS = {
    "Auto-Detect": {"g": "auto",  "d": None,    "w": None},
    "Arabic":      {"g": "ar",    "d": "AR",    "w": "ar"},
    "English":     {"g": "en",    "d": "EN-US", "w": "en"},
    "Russian":     {"g": "ru",    "d": "RU",    "w": "ru"},
    "Chinese":     {"g": "zh-CN", "d": "ZH",    "w": "zh"},
    "German":      {"g": "de",    "d": "DE",    "w": "de"},
    "Spanish":     {"g": "es",    "d": "ES",    "w": "es"},
    "French":      {"g": "fr",    "d": "FR",    "w": "fr"},
    "Portuguese":  {"g": "pt",    "d": "PT-PT", "w": "pt"},
    "Italian":     {"g": "it",    "d": "IT",    "w": "it"},
    "Japanese":    {"g": "ja",    "d": "JA",    "w": "ja"},
    "Korean":      {"g": "ko",    "d": "KO",    "w": "ko"},
    "Turkish":     {"g": "tr",    "d": "TR",    "w": "tr"},
    "Dutch":       {"g": "nl",    "d": "NL",    "w": "nl"},
    "Polish":      {"g": "pl",    "d": "PL",    "w": "pl"},
    "Ukrainian":   {"g": "uk",    "d": "UK",    "w": "uk"},
    "Swedish":     {"g": "sv",    "d": "SV",    "w": "sv"},
    "Danish":      {"g": "da",    "d": "DA",    "w": "da"},
    "Finnish":     {"g": "fi",    "d": "FI",    "w": "fi"},
    "Romanian":    {"g": "ro",    "d": "RO",    "w": "ro"},
    "Hungarian":   {"g": "hu",    "d": "HU",    "w": "hu"},
    "Czech":       {"g": "cs",    "d": "CS",    "w": "cs"},
    "Bulgarian":   {"g": "bg",    "d": "BG",    "w": "bg"},
    "Greek":       {"g": "el",    "d": "EL",    "w": "el"},
    "Indonesian":  {"g": "id",    "d": "ID",    "w": "id"},
    "Hindi":       {"g": "hi",    "d": None,    "w": "hi"},
    "Persian":     {"g": "fa",    "d": None,    "w": "fa"},
    "Hebrew":      {"g": "iw",    "d": None,    "w": "he"},
    "Urdu":        {"g": "ur",    "d": None,    "w": "ur"},
}

_TR_SYSTEM = (
    "You are an expert multilingual translator with deep cultural knowledge. "
    "CRITICAL RULES:\n"
    "1. NEVER translate word-for-word — translate MEANING and INTENT\n"
    "2. Proverbs/idioms: find the CULTURAL EQUIVALENT in target language\n"
    "3. Dialects (Arabic: مصري/خليجي/شامي/مغربي; all world dialects): understand first, then translate naturally\n"
    "4. Preserve register: formal=formal, casual=casual\n"
    "5. Return ONLY the translation. No explanations. No quotes."
)

_AI_SYSTEM = (
    "أنت مساعد ترجمة ذكي محترف. قدراتك:\n"
    "▸ ترجمة سياقية ذكية (الأمثال والعامية بمقابلها الثقافي)\n"
    "▸ تصحيح إملاء ونحو وإعراب\n"
    "▸ تلخيص وشرح مصطلحات\n"
    "▸ تغيير الأسلوب (رسمي/أدبي/تقني)\n"
    "▸ الإجابة عن أي سؤال لغوي أو ثقافي\n"
    "ردودك مباشرة وواضحة بلا مقدمات زائدة."
)


# ════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════

def _wl(code: str):
    """Normalize lang code for Whisper."""
    if not code or code == "auto": return None
    return {"zh-CN": "zh", "zh-cn": "zh", "iw": "he"}.get(code, code[:2])


def groq_chat(prompt: str, system: str = "", max_tokens: int = 700,
              model: str = None, history: list = None) -> tuple[str | None, str | None]:
    """Call Groq chat API. Returns (text, error)."""
    if not GROQ_KEY:
        return None, "GROQ_API_KEY not set"
    m = model or _M_FAST
    msgs = ([{"role": "system", "content": system}] if system else [])
    if history:
        msgs.extend(history[-8:])
    msgs.append({"role": "user", "content": prompt})
    for attempt_model in ([m, _M_FAST] if m != _M_FAST else [m]):
        try:
            r = http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}",
                         "Content-Type": "application/json"},
                json={"model": attempt_model, "messages": msgs,
                      "max_tokens": max_tokens, "temperature": 0.35},
                timeout=30)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip(), None
            if r.status_code == 429:
                if attempt_model == _M_FAST:
                    return None, "Rate limit exceeded. Please wait a moment."
                continue
            return None, f"Groq {r.status_code}"
        except Exception as e:
            return None, str(e)
    return None, "All models rate limited"


def translate_text(text: str, tgt: str, src: str = "Auto-Detect") -> tuple[str | None, str]:
    """Translate using DeepL → Groq AI → Google → MyMemory."""
    if not text or not text.strip():
        return None, "no text"

    tgt_info = LANGS.get(tgt, {})
    src_g    = LANGS.get(src, {}).get("g", "auto")
    tgt_g    = tgt_info.get("g", "en")

    # 1. DeepL (highest quality)
    if DEEPL_KEY and tgt_info.get("d"):
        ep = ("https://api-free.deepl.com/v2/translate" if DEEPL_KEY.endswith(":fx")
              else "https://api.deepl.com/v2/translate")
        try:
            r = http.post(ep,
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_KEY}"},
                data={"text": text, "target_lang": tgt_info["d"]},
                timeout=12)
            if r.status_code == 200:
                return r.json()["translations"][0]["text"], "DeepL ✦"
        except: pass

    # 2. Groq AI (contextual, handles dialects & idioms)
    if GROQ_KEY and len(text) <= 1200:
        result, _ = groq_chat(
            f"Translate from {src} to {tgt}:\n\n{text}",
            system=_TR_SYSTEM, max_tokens=600, model=_M_FAST)
        if result:
            return result, "AI ✦"

    # 3. Google Translate
    try:
        res = GoogleTranslator(source=src_g or "auto", target=tgt_g).translate(text)
        if res:
            return res, "Google"
    except: pass

    # 4. MyMemory fallback
    try:
        s = "en" if (not src_g or src_g == "auto") else src_g
        res = MyMemoryTranslator(source=s, target=tgt_g).translate(text)
        if res:
            return res, "Google"
    except: pass

    return None, "Translation failed"


def secs_to_srt(s: float) -> str:
    h  = int(s // 3600)
    m  = int((s % 3600) // 60)
    sc = int(s % 60)
    ms = int((s % 1) * 1000)
    return f"{h:02d}:{m:02d}:{sc:02d},{ms:03d}"


def detect_lang_script(text: str) -> str:
    """Quick script-based language detection."""
    if not text: return "en"
    ar = sum(1 for c in text if "\u0600" <= c <= "\u06FF") / max(len(text), 1)
    cy = sum(1 for c in text if "\u0400" <= c <= "\u04FF") / max(len(text), 1)
    cj = sum(1 for c in text if "\u4E00" <= c <= "\u9FFF") / max(len(text), 1)
    if ar > 0.12: return "ar"
    if cy > 0.12: return "ru"
    if cj > 0.12: return "zh"
    return "en"


# ════════════════════════════════════════════════════════════════
#  CORS preflight
# ════════════════════════════════════════════════════════════════
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return Response("", 204, {
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


# ════════════════════════════════════════════════════════════════
#  1. GET /api/langs  — language list
# ════════════════════════════════════════════════════════════════
@app.route("/api/langs", methods=["GET"])
def get_langs():
    return jsonify({"langs": list(LANGS.keys())})


# ════════════════════════════════════════════════════════════════
#  2. POST /api/translate  — text translation
#  Body: { text, src, tgt }
# ════════════════════════════════════════════════════════════════
@app.route("/api/translate", methods=["POST", "OPTIONS"])
def api_translate():
    data   = request.get_json(force=True)
    text   = (data.get("text") or "").strip()
    src    = data.get("src", "Auto-Detect")
    tgt    = data.get("tgt", "Arabic")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    result, engine = translate_text(text, tgt, src)
    if not result:
        return jsonify({"error": engine}), 500

    return jsonify({"translation": result, "engine": engine})


# ════════════════════════════════════════════════════════════════
#  3. POST /api/tts  — text to speech
#  Body: { text, lang }
# ════════════════════════════════════════════════════════════════
@app.route("/api/tts", methods=["POST", "OPTIONS"])
def api_tts():
    data  = request.get_json(force=True)
    text  = (data.get("text") or "").strip()
    lang  = data.get("lang", "en")

    if not text:
        return jsonify({"error": "No text"}), 400

    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text[:500], lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode()
        return jsonify({"audio": audio_b64, "mime": "audio/mpeg"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════════════
#  4. POST /api/voice  — speech-to-text + translate
#  Form: audio (file), src, tgt
# ════════════════════════════════════════════════════════════════
@app.route("/api/voice", methods=["POST", "OPTIONS"])
def api_voice():
    src = request.form.get("src", "Auto-Detect")
    tgt = request.form.get("tgt", "Arabic")
    af  = request.files.get("audio")
    if not af:
        return jsonify({"error": "No audio file"}), 400

    audio_bytes = af.read()
    wl = _wl(LANGS.get(src, {}).get("w") or "auto")

    # STT: Groq Whisper
    recognized = None
    if GROQ_KEY:
        try:
            files = {
                "file":            ("audio.wav", audio_bytes, af.mimetype or "audio/wav"),
                "model":           (None, _M_WHISPER),
                "response_format": (None, "json"),
            }
            if wl:
                files["language"] = (None, wl)
            r = http.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                files=files, timeout=45)
            if r.status_code == 200:
                recognized = r.json().get("text", "").strip()
        except: pass

    # Fallback: Cohere STT
    if not recognized and COHERE_KEY:
        try:
            lc  = wl or "en"
            enc = MultipartEncoder(fields=OrderedDict([
                ("language", lc), ("model", "cohere-transcribe-03-2026"),
                ("file", ("audio.wav", audio_bytes, "audio/wav")),
            ]))
            r = http.post("https://api.cohere.com/v2/audio/transcriptions",
                headers={"Authorization": f"Bearer {COHERE_KEY}",
                         "Content-Type": enc.content_type},
                data=enc, timeout=30)
            if r.status_code == 200:
                recognized = r.json().get("text", "").strip()
        except: pass

    if not recognized:
        return jsonify({"error": "Speech recognition failed. Check your Groq key."}), 500

    result, engine = translate_text(recognized, tgt, src)
    return jsonify({
        "recognized": recognized,
        "translation": result or "",
        "engine": engine,
    })


# ════════════════════════════════════════════════════════════════
#  5. POST /api/ocr  — image OCR + translate (FIXED)
#  Form: image (file), src, tgt
# ════════════════════════════════════════════════════════════════
@app.route("/api/ocr", methods=["POST", "OPTIONS"])
def api_ocr():
    src  = request.form.get("src", "Auto-Detect")
    tgt  = request.form.get("tgt", "Arabic")
    imgf = request.files.get("image")
    if not imgf:
        return jsonify({"error": "No image provided"}), 400

    if not GROQ_KEY:
        return jsonify({"error": "GROQ_API_KEY not configured in environment variables"}), 503

    img_bytes = imgf.read()

    # Detect MIME type from PIL
    try:
        from PIL import Image as PilImg
        pil = PilImg.open(io.BytesIO(img_bytes))
        fmt  = (pil.format or "JPEG").upper()
        mime = "image/jpeg" if fmt in ("JPG", "JPEG") else f"image/{fmt.lower()}"
        # Resize if too large (Groq has 20MB base64 limit)
        if len(img_bytes) > 4_000_000:
            pil.thumbnail((1920, 1920))
            buf = io.BytesIO()
            pil.save(buf, format=fmt if fmt != "JPG" else "JPEG")
            img_bytes = buf.getvalue()
    except:
        mime = imgf.mimetype or "image/jpeg"

    b64 = base64.b64encode(img_bytes).decode()

    extracted = None
    last_err  = "Groq Vision unavailable"

    for model in [_M_VISION_PRIMARY, _M_VISION_FALLBACK]:
        try:
            payload = {
                "model": model,
                "temperature": 0,
                "max_tokens": 2048,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"}
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract ALL text visible in this image exactly as written. "
                                "Preserve the original language (Arabic, English, or any other). "
                                "If multiple languages, keep each in its original script. "
                                "Return ONLY the raw extracted text — no labels, no explanations, "
                                "no quotes, no preamble. Just the text as it appears."
                            )
                        }
                    ]
                }]
            }
            r = http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}",
                         "Content-Type": "application/json"},
                json=payload, timeout=35)

            if r.status_code == 200:
                extracted = r.json()["choices"][0]["message"]["content"].strip()
                if extracted:
                    break
                last_err = "No text detected in image"
            elif r.status_code == 404:
                last_err = f"Model {model} not available"
                continue
            elif r.status_code == 400:
                err_detail = r.json().get("error", {}).get("message", "")
                last_err = f"Image format error: {err_detail[:100]}"
                break
            else:
                last_err = f"Groq Vision error {r.status_code}"
        except Exception as e:
            last_err = str(e)

    if not extracted:
        return jsonify({"error": last_err}), 500

    # Detect language of extracted text
    lang_code = detect_lang_script(extracted)
    src_name  = next((k for k, v in LANGS.items() if v.get("g") == lang_code), src)

    result, engine = translate_text(extracted, tgt, src_name)
    return jsonify({
        "extracted": extracted,
        "translation": result or "",
        "detected_lang": src_name,
        "engine": engine,
    })


# ════════════════════════════════════════════════════════════════
#  6. POST /api/subtitle  — audio/video → SRT (FIXED)
#  Form: audio (file), tgt
# ════════════════════════════════════════════════════════════════
@app.route("/api/subtitle", methods=["POST", "OPTIONS"])
def api_subtitle():
    tgt = request.form.get("tgt", "Arabic")
    af  = request.files.get("audio")
    if not af:
        return jsonify({"error": "No audio/video file"}), 400
    if not GROQ_KEY:
        return jsonify({"error": "GROQ_API_KEY not configured"}), 503

    audio_bytes = af.read()
    filename    = af.filename or "audio.wav"
    mime        = af.mimetype or "audio/wav"

    # Groq Whisper with verbose_json for timestamps
    try:
        files = {
            "file":                         (filename, audio_bytes, mime),
            "model":                        (None, _M_WHISPER),
            "response_format":              (None, "verbose_json"),
            "timestamp_granularities[]":    (None, "segment"),
        }
        r = http.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            files=files, timeout=90)

        if r.status_code != 200:
            return jsonify({"error": f"Groq STT error {r.status_code}: {r.text[:120]}"}), 500

        data = r.json()
    except Exception as e:
        return jsonify({"error": f"STT request failed: {str(e)}"}), 500

    segs = data.get("segments", [])
    if not segs:
        # No segments — use full text as single block
        full_text = data.get("text", "").strip()
        if not full_text:
            return jsonify({"error": "No speech detected in the audio"}), 400
        segs = [{"start": 0, "end": 5, "text": full_text}]

    orig_lines  = []
    trans_lines = []
    preview     = []

    for i, seg in enumerate(segs, 1):
        text  = seg.get("text", "").strip()
        t0    = seg.get("start", 0)
        t1    = seg.get("end",   t0 + 2)
        if not text: continue

        t_start = secs_to_srt(t0)
        t_end   = secs_to_srt(t1)

        orig_lines.append(f"{i}\n{t_start} --> {t_end}\n{text}")

        tr, _ = translate_text(text, tgt)
        tr_text = tr or text
        trans_lines.append(f"{i}\n{t_start} --> {t_end}\n{tr_text}")

        if i <= 20:
            preview.append({"num": i, "start": t_start[:8], "orig": text, "trans": tr_text})

    orig_srt  = "\n\n".join(orig_lines)
    trans_srt = "\n\n".join(trans_lines)

    # Bilingual SRT
    bilingual_lines = []
    for i, (o, t) in enumerate(zip(orig_lines, trans_lines), 1):
        # Extract just the text parts
        o_txt = "\n".join(o.split("\n")[2:])
        t_txt = "\n".join(t.split("\n")[2:])
        timing = o.split("\n")[1]
        bilingual_lines.append(f"{i}\n{timing}\n{o_txt}\n{t_txt}")
    bilingual_srt = "\n\n".join(bilingual_lines)

    return jsonify({
        "count":     len(orig_lines),
        "preview":   preview,
        "original":  base64.b64encode(orig_srt.encode()).decode(),
        "translated": base64.b64encode(trans_srt.encode()).decode(),
        "bilingual": base64.b64encode(bilingual_srt.encode()).decode(),
    })


# ════════════════════════════════════════════════════════════════
#  7. POST /api/chat  — AI assistant
#  Body: { message, source_text, current_trans, src, tgt, history }
# ════════════════════════════════════════════════════════════════
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    data = request.get_json(force=True)
    msg      = (data.get("message")       or "").strip()
    src_txt  = (data.get("source_text")   or "")[:500]
    cur_tr   = (data.get("current_trans") or "")[:400]
    src      = data.get("src", "Auto-Detect")
    tgt      = data.get("tgt", "Arabic")
    history  = data.get("history", [])

    if not msg:
        return jsonify({"error": "No message"}), 400
    if not GROQ_KEY:
        return jsonify({"error": "GROQ_API_KEY not configured"}), 503

    ctx = (
        f"Current context:\n"
        f"- Original text ({src}): {src_txt or 'none'}\n"
        f"- Current translation ({tgt}): {cur_tr or 'none'}\n"
        f"- Direction: {src} → {tgt}\n\n"
        f"User request: {msg}"
    )

    # Try smart model first, fallback to fast
    reply = None
    for model in [_M_SMART, _M_FAST]:
        reply, err = groq_chat(ctx, system=_AI_SYSTEM, max_tokens=900,
                               model=model, history=history)
        if reply:
            break
        if err and "429" not in str(err):
            break

    if not reply:
        return jsonify({"error": err or "AI unavailable"}), 500

    return jsonify({"reply": reply})


# ════════════════════════════════════════════════════════════════
#  8. POST /api/spell  — spell check suggestions
#  Body: { text, lang }
# ════════════════════════════════════════════════════════════════
@app.route("/api/spell", methods=["POST", "OPTIONS"])
def api_spell():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    lang = data.get("lang", "Auto-Detect")

    if not text or len(text) < 4 or not GROQ_KEY:
        return jsonify({"suggestions": []})

    result, _ = groq_chat(
        f'Check spelling and grammar in this {lang} text: "{text[:400]}"\n'
        'Return a JSON array only (no markdown, no explanation). '
        'Format: [{"wrong":"incorrect_word","correct":"correct_word"}] '
        'Max 3 corrections. If no errors: []',
        max_tokens=150, model=_M_FAST)

    if not result:
        return jsonify({"suggestions": []})

    try:
        clean = re.sub(r"```json|```", "", result).strip()
        items = json.loads(clean)
        sug   = [(x["wrong"], x["correct"]) for x in items
                 if isinstance(x, dict) and x.get("wrong") and x.get("correct")
                 and x["wrong"] != x["correct"]][:3]
        return jsonify({"suggestions": [{"wrong": w, "correct": c} for w, c in sug]})
    except:
        return jsonify({"suggestions": []})


# ════════════════════════════════════════════════════════════════
#  9. POST /api/file  — extract + translate text from file
#  Form: file (file), src, tgt
# ════════════════════════════════════════════════════════════════
@app.route("/api/file", methods=["POST", "OPTIONS"])
def api_file():
    src = request.form.get("src", "Auto-Detect")
    tgt = request.form.get("tgt", "Arabic")
    f   = request.files.get("file")
    if not f:
        return jsonify({"error": "No file"}), 400

    filename = f.filename.lower()
    content  = f.read()
    text     = None

    if filename.endswith(".txt"):
        for enc in ("utf-8", "windows-1256", "latin-1"):
            try:
                text = content.decode(enc)
                break
            except: pass

    elif filename.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join(pg.extract_text() or "" for pg in pdf.pages).strip()
        except ImportError:
            return jsonify({"error": "PDF support requires pdfplumber — add it to requirements.txt"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif filename.endswith(".docx"):
        try:
            import docx
            d = docx.Document(io.BytesIO(content))
            text = "\n".join(p.text for p in d.paragraphs).strip()
        except ImportError:
            return jsonify({"error": "DOCX support requires python-docx — add it to requirements.txt"}), 400

    if not text or not text.strip():
        return jsonify({"error": "No text extracted from file"}), 400

    # Translate in chunks (DeepL has a 1MB limit)
    chunks  = [text[i:i+1400] for i in range(0, len(text), 1400)]
    parts   = []
    engine  = "Google"
    for chunk in chunks[:20]:  # max 20 chunks
        r, eng = translate_text(chunk, tgt, src)
        parts.append(r or chunk)
        engine = eng

    return jsonify({
        "original":    text[:3000],
        "translation": "\n".join(parts),
        "engine":      engine,
        "word_count":  len(text.split()),
    })


# ════════════════════════════════════════════════════════════════
#  Vercel entry point
# ════════════════════════════════════════════════════════════════
handler = app

if __name__ == "__main__":
    app.run(debug=True, port=5000)
