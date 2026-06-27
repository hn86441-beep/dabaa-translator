import streamlit as st
st.set_page_config(page_title="HN TRANSLATOR", page_icon="🌐", layout="centered")

# ══════════════════════════════════════════════════════════════════
#  مكتبات
# ══════════════════════════════════════════════════════════════════
import requests, os, json, tempfile, io, base64, sqlite3, time
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict
from datetime import datetime
from PIL import Image

try:
    import pdfplumber;     PDF_OK = True
except ImportError:        PDF_OK = False
try:
    import docx;           DOCX_OK = True
except ImportError:        DOCX_OK = False
try:
    import openpyxl;       EXCEL_OK = True
except ImportError:        EXCEL_OK = False
try:
    from transformers import pipeline as hf_pipeline; HF_OK = True
except ImportError:        HF_OK = False
try:
    from langdetect import detect as _ld_detect, DetectorFactory
    DetectorFactory.seed = 42
    LANGDETECT_OK = True
except ImportError:        LANGDETECT_OK = False
try:
    import easyocr;        EASYOCR_OK = True
except ImportError:        EASYOCR_OK = False

from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS

# ══════════════════════════════════════════════════════════════════
#  جدول اللغات
# ══════════════════════════════════════════════════════════════════
ALL_LANGUAGES = {
    "Auto-Detect": {"google":"auto",  "deepl":None,    "gtts":"en",    "whisper":None,  "ocr":["en","ar"]},
    "Arabic":      {"google":"ar",    "deepl":"AR",    "gtts":"ar",    "whisper":"ar",  "ocr":["ar","en"]},
    "English":     {"google":"en",    "deepl":"EN-US", "gtts":"en",    "whisper":"en",  "ocr":["en"]},
    "Russian":     {"google":"ru",    "deepl":"RU",    "gtts":"ru",    "whisper":"ru",  "ocr":["ru","en"]},
    "Chinese":     {"google":"zh-CN", "deepl":"ZH",    "gtts":"zh-cn", "whisper":"zh",  "ocr":["ch_sim","en"]},
    "German":      {"google":"de",    "deepl":"DE",    "gtts":"de",    "whisper":"de",  "ocr":["de","en"]},
    "Spanish":     {"google":"es",    "deepl":"ES",    "gtts":"es",    "whisper":"es",  "ocr":["es","en"]},
    "French":      {"google":"fr",    "deepl":"FR",    "gtts":"fr",    "whisper":"fr",  "ocr":["fr","en"]},
    "Portuguese":  {"google":"pt",    "deepl":"PT-PT", "gtts":"pt",    "whisper":"pt",  "ocr":["pt","en"]},
    "Italian":     {"google":"it",    "deepl":"IT",    "gtts":"it",    "whisper":"it",  "ocr":["it","en"]},
    "Japanese":    {"google":"ja",    "deepl":"JA",    "gtts":"ja",    "whisper":"ja",  "ocr":["ja","en"]},
    "Korean":      {"google":"ko",    "deepl":"KO",    "gtts":"ko",    "whisper":"ko",  "ocr":["ko","en"]},
    "Turkish":     {"google":"tr",    "deepl":"TR",    "gtts":"tr",    "whisper":"tr",  "ocr":["tr","en"]},
    "Dutch":       {"google":"nl",    "deepl":"NL",    "gtts":"nl",    "whisper":"nl",  "ocr":["nl","en"]},
    "Polish":      {"google":"pl",    "deepl":"PL",    "gtts":"pl",    "whisper":"pl",  "ocr":["pl","en"]},
    "Ukrainian":   {"google":"uk",    "deepl":"UK",    "gtts":"uk",    "whisper":"uk",  "ocr":["uk","en"]},
    "Swedish":     {"google":"sv",    "deepl":"SV",    "gtts":"sv",    "whisper":"sv",  "ocr":["sv","en"]},
    "Danish":      {"google":"da",    "deepl":"DA",    "gtts":"da",    "whisper":"da",  "ocr":["da","en"]},
    "Finnish":     {"google":"fi",    "deepl":"FI",    "gtts":"fi",    "whisper":"fi",  "ocr":["fi","en"]},
    "Romanian":    {"google":"ro",    "deepl":"RO",    "gtts":"ro",    "whisper":"ro",  "ocr":["ro","en"]},
    "Hungarian":   {"google":"hu",    "deepl":"HU",    "gtts":"hu",    "whisper":"hu",  "ocr":["hu","en"]},
    "Czech":       {"google":"cs",    "deepl":"CS",    "gtts":"cs",    "whisper":"cs",  "ocr":["cs","en"]},
    "Bulgarian":   {"google":"bg",    "deepl":"BG",    "gtts":"bg",    "whisper":"bg",  "ocr":["bg","en"]},
    "Greek":       {"google":"el",    "deepl":"EL",    "gtts":"el",    "whisper":"el",  "ocr":["el","en"]},
    "Indonesian":  {"google":"id",    "deepl":"ID",    "gtts":"id",    "whisper":"id",  "ocr":["id","en"]},
    "Hindi":       {"google":"hi",    "deepl":None,    "gtts":"hi",    "whisper":"hi",  "ocr":["hi","en"]},
    "Persian":     {"google":"fa",    "deepl":None,    "gtts":"fa",    "whisper":"fa",  "ocr":["fa","en"]},
    "Hebrew":      {"google":"iw",    "deepl":None,    "gtts":"iw",    "whisper":"he",  "ocr":["he","en"]},
    "Urdu":        {"google":"ur",    "deepl":None,    "gtts":"ur",    "whisper":"ur",  "ocr":["ur","en"]},
}
LANG_NAMES         = list(ALL_LANGUAGES.keys())
LANG_NAMES_NO_AUTO = [k for k in LANG_NAMES if k != "Auto-Detect"]

# رمز langdetect → اسم اللغة في التطبيق
_LC2NAME = {
    "ar":"Arabic","en":"English","ru":"Russian","zh-cn":"Chinese","zh-tw":"Chinese",
    "de":"German","es":"Spanish","fr":"French","pt":"Portuguese","it":"Italian",
    "ja":"Japanese","ko":"Korean","tr":"Turkish","nl":"Dutch","pl":"Polish",
    "uk":"Ukrainian","sv":"Swedish","da":"Danish","fi":"Finnish","ro":"Romanian",
    "hu":"Hungarian","cs":"Czech","bg":"Bulgarian","el":"Greek","id":"Indonesian",
    "hi":"Hindi","fa":"Persian","he":"Hebrew","ur":"Urdu","zh":"Chinese",
}

# ══════════════════════════════════════════════════════════════════
#  قاعدة البيانات — /tmp/ للتوافق مع Streamlit Cloud
# ══════════════════════════════════════════════════════════════════
_DB = os.path.join(tempfile.gettempdir(), "hn_translations.db")

def _db():
    return sqlite3.connect(_DB, timeout=10, check_same_thread=False)

def init_db():
    try:
        c = _db()
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original TEXT NOT NULL DEFAULT '',
            translated TEXT NOT NULL DEFAULT '',
            emotion TEXT DEFAULT '',
            source_lang TEXT DEFAULT '',
            target_lang TEXT DEFAULT '',
            engine TEXT DEFAULT '',
            timestamp TEXT DEFAULT '')''')
        existing = {r[1] for r in c.execute("PRAGMA table_info(history)")}
        for col, typ in [("engine","TEXT DEFAULT ''"),("emotion","TEXT DEFAULT ''"),
                         ("source_lang","TEXT DEFAULT ''"),("target_lang","TEXT DEFAULT ''")]:
            if col not in existing:
                c.execute(f"ALTER TABLE history ADD COLUMN {col} {typ}")
        c.commit(); c.close()
    except Exception: pass

def _mem_push(entry):
    if "_mem" not in st.session_state: st.session_state["_mem"] = []
    st.session_state["_mem"].insert(0, entry)
    st.session_state["_mem"] = st.session_state["_mem"][:300]

def save_translation(orig, trans, emotion, src, tgt, engine=""):
    entry = {"original":str(orig or "")[:500],"translated":str(trans or "")[:500],
             "emotion":str(emotion or ""),"source_lang":str(src or ""),
             "target_lang":str(tgt or ""),"engine":str(engine or ""),
             "time":datetime.now().strftime("%Y-%m-%d %H:%M")}
    _mem_push(entry)
    try:
        c = _db()
        c.execute('''INSERT INTO history (original,translated,emotion,source_lang,target_lang,engine,timestamp)
                     VALUES (?,?,?,?,?,?,?)''',
                  tuple(entry[k] for k in ["original","translated","emotion",
                                           "source_lang","target_lang","engine","time"]))
        c.commit(); c.close()
    except Exception: pass

def get_history(limit=100):
    try:
        c = _db()
        rows = c.execute('''SELECT original,translated,emotion,source_lang,target_lang,engine,timestamp
                            FROM history ORDER BY id DESC LIMIT ?''',(limit,)).fetchall()
        c.close()
        if rows:
            return [{"original":r[0],"translated":r[1],"emotion":r[2] or "",
                     "source_lang":r[3] or "","target_lang":r[4] or "",
                     "engine":r[5] or "","time":r[6] or ""} for r in rows]
    except Exception: pass
    return st.session_state.get("_mem",[])[:limit]

def clear_history():
    st.session_state["_mem"] = []
    try:
        c = _db(); c.execute("DELETE FROM history"); c.commit(); c.close()
    except Exception: pass

init_db()

# ══════════════════════════════════════════════════════════════════
#  تحليل المشاعر  ✅ مُصلح
# ══════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def _load_emotion():
    if not HF_OK: return None
    try:
        return hf_pipeline(
            "text-classification",
            model="tabularisai/multilingual-sentiment-analysis",
            top_k=None,          # يُعيد كل التصنيفات مرتّبة
            truncation=True,
            max_length=512,
        )
    except Exception:
        return None

_EMOTION_MODEL = _load_emotion()

_POS = ["شكر","ممتاز","رائع","سعيد","فرح","أحب","حلو","عظيم","جميل","موافق","صحيح",
        "happy","good","great","excellent","love","wonderful","amazing","nice","joy",
        "perfect","awesome","fantastic","enjoy","pleasure","glad","positive","super"]
_NEG = ["حزين","سيء","كره","غضب","ألم","صعب","خطأ","فشل","مزعج","لا","خطير","مرفوض",
        "قلق","توتر","sad","bad","hate","angry","pain","error","fail","no","dangerous",
        "terrible","horrible","awful","wrong","disaster","violence","threat","anxious"]

def analyze_emotion(text: str) -> str:
    """
    ✅ مُصلح:
    - استدعاء النموذج مرة واحدة فقط
    - أخذ أعلى score من النتائج
    - fallback بالكلمات المفتاحية
    """
    if not text or not text.strip():
        return "😐 محايد"

    # 1️⃣ Transformers — top_k=None يُعيد list[{"label","score"}]
    if _EMOTION_MODEL is not None:
        try:
            preds = _EMOTION_MODEL(text[:512])
            # النتيجة: [[{"label":..,"score":..}, ...]]
            if preds and isinstance(preds, list):
                items = preds[0] if isinstance(preds[0], list) else preds
                best  = max(items, key=lambda x: x.get("score", 0))
                label = best.get("label", "").upper()
                score = best.get("score", 0)
                if score >= 0.50:
                    if any(x in label for x in ("POSITIVE","POS","HAPPY","JOY","VERY_POSITIVE")):
                        return "😊 إيجابي"
                    if any(x in label for x in ("NEGATIVE","NEG","SAD","ANGER","VERY_NEGATIVE")):
                        return "😔 سلبي"
                    if "NEUTRAL" in label:
                        return "😐 محايد"
        except Exception:
            pass

    # 2️⃣ كلمات مفتاحية كاحتياطي
    tl = text.lower()
    pos = sum(1 for w in _POS if w in tl)
    neg = sum(1 for w in _NEG if w in tl)
    if pos > neg: return "😊 إيجابي"
    if neg > pos: return "😔 سلبي"
    return "😐 محايد"

# ══════════════════════════════════════════════════════════════════
#  كشف لغة النص  ✅ مُصلح (استخدام langdetect بشكل صحيح)
# ══════════════════════════════════════════════════════════════════
def detect_text_lang(text: str) -> tuple[str, str]:
    """يُعيد (lang_code, lang_name)"""
    if not text or not text.strip():
        return "en", "English"

    # فحص الخط مباشرةً (أسرع وأدق للعربية/السيريلية)
    ar_ratio  = sum(1 for c in text if "\u0600" <= c <= "\u06FF") / max(len(text), 1)
    cyr_ratio = sum(1 for c in text if "\u0400" <= c <= "\u04FF") / max(len(text), 1)
    cjk_ratio = sum(1 for c in text if "\u4E00" <= c <= "\u9FFF") / max(len(text), 1)

    if ar_ratio  > 0.15: return "ar", "Arabic"
    if cyr_ratio > 0.15: return "ru", "Russian"
    if cjk_ratio > 0.15: return "zh", "Chinese"

    # langdetect
    if LANGDETECT_OK and len(text.strip()) >= 5:
        try:
            code = _ld_detect(text)
            name = _LC2NAME.get(code, code.capitalize())
            return code, name
        except Exception:
            pass

    return "en", "English"

# ══════════════════════════════════════════════════════════════════
#  الترجمة  DeepL → Google → MyMemory
# ══════════════════════════════════════════════════════════════════
def _deepl(text, tgt_code, ak):
    ep = ("https://api-free.deepl.com/v2/translate" if ak.endswith(":fx")
          else "https://api.deepl.com/v2/translate")
    try:
        r = requests.post(ep, headers={"Authorization": f"DeepL-Auth-Key {ak}"},
                          data={"text": text, "target_lang": tgt_code}, timeout=15)
        if r.status_code == 200:
            return r.json()["translations"][0]["text"], None
        return None, f"DeepL {r.status_code}"
    except Exception as e: return None, str(e)

def _google(text, tgt, src="auto"):
    try:
        return GoogleTranslator(source=src or "auto", target=tgt).translate(text), None
    except Exception as e1:
        try:
            s = "en" if (not src or src == "auto") else src
            return MyMemoryTranslator(source=s, target=tgt).translate(text), None
        except Exception as e2:
            return None, f"{e1}|{e2}"

def translate_text(text: str, tgt_name: str, src_name: str = "Auto-Detect") -> tuple:
    """يُعيد (نص_مترجم, اسم_المحرك)"""
    if not text or not text.strip(): return None, "no text"
    info       = ALL_LANGUAGES.get(tgt_name, {})
    deepl_code = info.get("deepl")
    google_tgt = info.get("google", "en")
    src_google = ALL_LANGUAGES.get(src_name, {}).get("google", "auto")
    ak = st.session_state.get("deepl_api_key", "")
    if ak and deepl_code:
        r, _ = _deepl(text, deepl_code, ak)
        if r: return r, "DeepL ✦"
    r, err = _google(text, google_tgt, src_google)
    return (r, "Google") if r else (None, err or "فشلت الترجمة")

# ══════════════════════════════════════════════════════════════════
#  TTS
# ══════════════════════════════════════════════════════════════════
def tts(text: str, lang: str = "en") -> io.BytesIO | None:
    if not text or not text.strip(): return None
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0); return buf
    except Exception: return None

# ══════════════════════════════════════════════════════════════════
#  استخراج النص من الملفات
# ══════════════════════════════════════════════════════════════════
def extract_file_text(file_bytes: bytes, filename: str) -> tuple:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        if not PDF_OK: return None, "pdfplumber غير مثبت"
        try:
            txt = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for pg in pdf.pages:
                    t = pg.extract_text()
                    if t: txt += t + "\n"
            return (txt.strip(), None) if txt.strip() else (None, "لا نص في PDF")
        except Exception as e: return None, str(e)
    if ext == ".docx":
        if not DOCX_OK: return None, "python-docx غير مثبت"
        try:
            d = docx.Document(io.BytesIO(file_bytes))
            txt = "\n".join(p.text for p in d.paragraphs)
            return (txt.strip(), None) if txt.strip() else (None, "لا نص في DOCX")
        except Exception as e: return None, str(e)
    if ext in (".xlsx", ".xls"):
        if not EXCEL_OK: return None, "openpyxl غير مثبت"
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            parts = [str(c.value) for sh in wb.worksheets
                     for row in sh.iter_rows() for c in row if c.value is not None]
            txt = "\n".join(parts)
            return (txt.strip(), None) if txt.strip() else (None, "لا نص في Excel")
        except Exception as e: return None, str(e)
    if ext == ".txt":
        for enc in ("utf-8","windows-1256","latin-1"):
            try:
                txt = file_bytes.decode(enc)
                if txt.strip(): return txt.strip(), None
            except Exception: pass
        return None, "تعذر قراءة الملف"
    return None, f"نوع غير مدعوم: {ext}"

# ══════════════════════════════════════════════════════════════════
#  OCR من الصور  ✅ مُصلح: Groq Vision أولاً (أدق)، EasyOCR احتياطي
# ══════════════════════════════════════════════════════════════════
def _img_mime(img_bytes: bytes) -> str:
    try:
        fmt = Image.open(io.BytesIO(img_bytes)).format or "JPEG"
        return f"image/{'jpeg' if fmt.upper() in ('JPG','JPEG') else fmt.lower()}"
    except Exception: return "image/jpeg"

def extract_image_text_groq(img_bytes: bytes) -> tuple:
    """
    ✅ مُصلح: Groq Vision (llama-4-scout) — مجاني، يدعم العربية بشكل ممتاز
    """
    ak = st.session_state.get("groq_api_key", "")
    if not ak: return None, "مفتاح Groq غير موجود"
    try:
        mime   = _img_mime(img_bytes)
        b64    = base64.b64encode(img_bytes).decode()
        # تجربة نموذجين (scout أولاً، ثم llama-3.2-vision احتياطياً)
        for model in ["meta-llama/llama-4-scout-17b-16e-instruct",
                      "llama-3.2-11b-vision-preview"]:
            payload = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text",
                         "text": (
                            "Extract ALL text from this image exactly as written. "
                            "Preserve the original language (Arabic, English, or any other). "
                            "Return ONLY the extracted text with no explanation, no labels, "
                            "no quotes — just the raw text as it appears in the image."
                         )},
                    ]
                }],
                "max_tokens": 2048,
                "temperature": 0,
            }
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {ak}", "Content-Type": "application/json"},
                json=payload, timeout=30,
            )
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                return (txt, None) if txt else (None, "لم يُعثر على نص")
            if r.status_code == 404:
                continue   # جرّب النموذج التالي
            return None, f"Groq Vision {r.status_code}: {r.text[:100]}"
        return None, "النماذج غير متاحة"
    except Exception as e: return None, str(e)

@st.cache_resource(show_spinner=False)
def _load_easyocr(langs_t: tuple):
    if not EASYOCR_OK: return None
    try:
        return easyocr.Reader(list(langs_t), gpu=False, verbose=False)
    except Exception: return None

def extract_image_text_easyocr(img_bytes: bytes, ocr_langs: list) -> tuple:
    """EasyOCR — احتياطي عند غياب Groq"""
    if not EASYOCR_OK: return None, "EasyOCR غير مثبت"
    try:
        import numpy as np
        reader = _load_easyocr(tuple(ocr_langs))
        if reader is None: return None, "تعذر تحميل EasyOCR"
        arr = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
        result = reader.readtext(arr, detail=0, paragraph=True)
        txt = " ".join(result).strip()
        return (txt, None) if txt else (None, "لم يُعثر على نص")
    except Exception as e: return None, str(e)

def extract_image_text(img_bytes: bytes, ocr_langs: list) -> tuple:
    """Groq Vision → EasyOCR"""
    if st.session_state.get("groq_api_key"):
        txt, err = extract_image_text_groq(img_bytes)
        if txt: return txt, None
    return extract_image_text_easyocr(img_bytes, ocr_langs)

# ══════════════════════════════════════════════════════════════════
#  التعرف على الصوت  Groq → Cohere → Whisper محلي
# ══════════════════════════════════════════════════════════════════
def _wlang(code: str):
    if not code or code == "auto": return None
    return {"zh-CN":"zh","zh-cn":"zh","iw":"he"}.get(code, code[:2])

def _groq_stt(audio_bytes: bytes, lang="auto", verbose=False) -> tuple:
    ak = st.session_state.get("groq_api_key", "")
    if not ak: return None, "مفتاح Groq غير موجود"
    lc = _wlang(lang)
    files = {
        "file": ("audio.wav", audio_bytes, "audio/wav"),
        "model": (None, "whisper-large-v3-turbo"),
        "response_format": (None, "verbose_json" if verbose else "json"),
    }
    if verbose: files["timestamp_granularities[]"] = (None, "segment")
    if lc:     files["language"] = (None, lc)
    try:
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                          headers={"Authorization": f"Bearer {ak}"},
                          files=files, timeout=60)
        if r.status_code == 200:
            data = r.json()
            if verbose: return data, None
            txt = data.get("text","").strip()
            return (txt, None) if txt else (None, "لم يُكتشف كلام")
        return None, f"Groq {r.status_code}: {r.text[:100]}"
    except Exception as e: return None, str(e)

def _cohere_stt(audio_bytes: bytes, lang="en") -> tuple:
    ak = st.session_state.get("cohere_api_key","")
    if not ak: return None, "مفتاح Cohere غير موجود"
    lc = _wlang(lang) or "en"
    try:
        fields = OrderedDict([("language",lc),("model","cohere-transcribe-03-2026"),
                               ("file",("audio.wav",audio_bytes,"audio/wav"))])
        enc = MultipartEncoder(fields=fields)
        r = requests.post("https://api.cohere.com/v2/audio/transcriptions",
                          headers={"Authorization":f"Bearer {ak}","Content-Type":enc.content_type},
                          data=enc, timeout=30)
        if r.status_code == 200:
            txt = r.json().get("text","").strip()
            return (txt, None) if txt else (None, "لم يُكتشف كلام")
        return None, f"Cohere {r.status_code}"
    except Exception as e: return None, str(e)

@st.cache_resource(show_spinner=False)
def _load_whisper_local():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("small", device="cpu", compute_type="int8")
    except Exception: return None

def _local_stt(audio_bytes: bytes, lang=None) -> tuple:
    m = _load_whisper_local()
    if not m: return None, "Whisper المحلي غير متاح"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes); tmp = f.name
        segs, _ = m.transcribe(tmp, language=lang, beam_size=5, vad_filter=True)
        txt = " ".join(s.text for s in segs).strip()
        return (txt, None) if txt else (None, "لم يُكتشف كلام")
    except Exception as e: return None, str(e)
    finally:
        if tmp and os.path.exists(tmp): os.unlink(tmp)

def speech_to_text(audio_bytes: bytes, lang_code: str = "auto") -> tuple:
    wl = _wlang(lang_code)
    if st.session_state.get("groq_api_key"):
        r, e = _groq_stt(audio_bytes, lang_code)
        if r: return r, None
    if st.session_state.get("cohere_api_key"):
        r, e = _cohere_stt(audio_bytes, lang_code)
        if r: return r, None
    return _local_stt(audio_bytes, lang=wl)

# ══════════════════════════════════════════════════════════════════
#  محادثة جماعية — تحليل متعدد المتحدثين  ✅
#
#  الخوارزمية:
#  1. Groq verbose_json → segments مع توقيتات
#  2. تجميع segments بفواصل صمت > 0.6 ثانية
#  3. كشف لغة كل مجموعة (detect_text_lang)
#  4. تعيين رقم متحدث: كل لغة جديدة = متحدث جديد
#     (نفس اللغة تعود لنفس المتحدث إلا إذا تخلّلتها لغة أخرى)
#  5. ترجمة كل مقطع إلى اللغة الهدف
# ══════════════════════════════════════════════════════════════════
_SPK_ICONS = ["🧑","👤","🙍","👱","🧔","👩","🧕","👲","🧑‍💼","👨‍💼"]

def _group_segs(segs: list, gap=0.6) -> list:
    if not segs: return []
    groups, cur = [], [segs[0]]
    for i in range(1, len(segs)):
        pause = segs[i].get("start", 0) - segs[i-1].get("end", 0)
        if pause >= gap:
            groups.append(cur); cur = []
        cur.append(segs[i])
    if cur: groups.append(cur)
    return groups

def group_chat_analyze(audio_bytes: bytes, tgt_lang: str) -> tuple:
    """
    يُعيد (list[dict] | None, error_str | None)

    كل dict:
    {speaker_num, speaker_icon, lang_code, lang_name,
     original, translated, engine, gtts_lang, start, end}
    """
    tgt_gtts = ALL_LANGUAGES.get(tgt_lang, {}).get("gtts", "en")

    def _single_result(txt, lc, ln, start=0.0, end=0.0):
        src_name = _LC2NAME.get(lc, "Auto-Detect")
        trans, eng = translate_text(txt, tgt_lang, src_name)
        return [{
            "speaker_num": 1, "speaker_icon": _SPK_ICONS[0],
            "lang_code": lc,  "lang_name": ln,
            "original": txt,  "translated": trans or "",
            "engine": eng,    "gtts_lang": tgt_gtts,
            "start": start,   "end": end,
        }]

    # ── 1. Groq verbose ─────────────────────────────────────────
    data, err = _groq_stt(audio_bytes, lang="auto", verbose=True)

    if data is None:
        # احتياطي بدون segments
        txt = None
        if st.session_state.get("cohere_api_key"):
            txt, _ = _cohere_stt(audio_bytes)
        if not txt:
            txt, err2 = _local_stt(audio_bytes)
        if not txt:
            return None, err2 if 'err2' in dir() else (err or "تعذر التعرف على الصوت")
        lc, ln = detect_text_lang(txt)
        return _single_result(txt, lc, ln), None

    segs = data.get("segments", [])
    full_txt = data.get("text", "").strip()

    if not segs:
        if not full_txt: return None, "لم يُكتشف كلام"
        lc, ln = detect_text_lang(full_txt)
        return _single_result(full_txt, lc, ln), None

    # ── 2. تجميع segments بالصمت ──────────────────────────────
    groups = _group_segs(segs, gap=0.6)

    results     = []
    lang_to_spk = {}   # lc → speaker_num
    prev_lang   = None
    spk_counter = 1

    for grp in groups:
        txt = " ".join(s.get("text","").strip() for s in grp).strip()
        if not txt: continue

        lc, ln = detect_text_lang(txt)

        # منطق تعيين المتحدث:
        # نفس اللغة متتالياً → نفس المتحدث
        # لغة جديدة → متحدث جديد دائماً
        if lc not in lang_to_spk or (prev_lang and lc != prev_lang
                                      and lc in lang_to_spk):
            if lc not in lang_to_spk:
                lang_to_spk[lc] = spk_counter
                spk_counter += 1
        spk  = lang_to_spk[lc]
        icon = _SPK_ICONS[min(spk - 1, len(_SPK_ICONS) - 1)]
        prev_lang = lc

        src_name = _LC2NAME.get(lc, "Auto-Detect")
        trans, eng = translate_text(txt, tgt_lang, src_name)

        results.append({
            "speaker_num":  spk,
            "speaker_icon": icon,
            "lang_code":    lc,
            "lang_name":    ln,
            "original":     txt,
            "translated":   trans or "",
            "engine":       eng,
            "gtts_lang":    tgt_gtts,
            "start":        grp[0].get("start", 0),
            "end":          grp[-1].get("end", 0),
        })

    return (results, None) if results else (None, "لم يُكتشف كلام")

# ══════════════════════════════════════════════════════════════════
#  كشف مجال النص
# ══════════════════════════════════════════════════════════════════
_DOMAINS = {
    "political":  {"e":"🏛️","n":"Political",  "kw":["minister","government","president","وزير","حكومة","رئيس"]},
    "legal":      {"e":"⚖️","n":"Legal",       "kw":["contract","court","law","عقد","قانون","محكمة"]},
    "economic":   {"e":"📈","n":"Economic",    "kw":["economic","investment","اقتصاد","استثمار","ميزانية"]},
    "medical":    {"e":"🏥","n":"Medical",     "kw":["doctor","hospital","treatment","طبيب","مستشفى","علاج"]},
    "scientific": {"e":"🔬","n":"Scientific",  "kw":["research","experiment","بحث","تجربة","نظرية"]},
    "military":   {"e":"🎖️","n":"Military",   "kw":["military","army","weapon","جيش","عسكري","سلاح"]},
    "educational":{"e":"📚","n":"Educational","kw":["school","university","teacher","مدرسة","جامعة","معلم"]},
    "religious":  {"e":"🕌","n":"Religious",   "kw":["mosque","prayer","Quran","مسجد","صلاة","قرآن"]},
    "sports":     {"e":"⚽","n":"Sports",      "kw":["football","stadium","team","كرة","ملعب","فريق"]},
    "it":         {"e":"💻","n":"IT/Tech",     "kw":["programming","software","website","برمجة","موقع","تطبيق"]},
    "tourism":    {"e":"✈️","n":"Tourism",     "kw":["hotel","travel","airport","فندق","سفر","مطار"]},
}
def detect_domains(text: str) -> list:
    tl = text.lower()
    return sorted(
        (d for d, v in _DOMAINS.items() if any(k in tl for k in v["kw"])),
        key=lambda d: -sum(tl.count(k) for k in _DOMAINS[d]["kw"])
    )[:3]

# ══════════════════════════════════════════════════════════════════
#  Secrets & Session State
# ══════════════════════════════════════════════════════════════════
def _sec(k, d=""):
    try: return st.secrets.get(k, d) or d
    except Exception: return d

for k, v in {
    "theme":         "dark",
    "groq_api_key":  _sec("GROQ_API_KEY"),
    "deepl_api_key": _sec("DEEPL_API_KEY"),
    "cohere_api_key":_sec("COHERE_API_KEY"),
    "source_lang":   "Auto-Detect",
    "target_lang":   "Arabic",
    "input_text":    "",
}.items():
    if k not in st.session_state: st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════
def _css(t):
    if t == "light":
        ac,bg,card,brd,txt,sub,sbg = (
            "#2a7a60","#f5f7fa","rgba(42,122,96,.07)","rgba(42,122,96,.22)",
            "#1a1a2e","rgba(42,122,96,.75)","rgba(255,255,255,.98)")
    else:
        ac,bg,card,brd,txt,sub,sbg = (
            "#4ECBA0","linear-gradient(135deg,#0a0a1a,#0f1728 40%,#0a1520)",
            "rgba(78,203,160,.07)","rgba(78,203,160,.22)","#e8f0ff",
            "rgba(78,203,160,.75)","rgba(10,10,26,.98)")
    ib = "white" if t=="light" else "rgba(255,255,255,.04)"
    tl = "#1a1a2e" if t=="light" else "#b0c4de"
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
.stApp{{background:{bg} !important}}
.hdr{{text-align:center;padding:.8rem 0 .4rem}}
.hdr .br{{font-size:10px;font-weight:700;letter-spacing:.3em;color:{ac};text-transform:uppercase;opacity:.8}}
.hdr h1{{font-family:'Space Grotesk',sans-serif;font-size:30px;font-weight:700;color:{txt};margin:0}}
.hdr h1 span{{color:{ac}}}
.hdr .dv{{width:60px;height:3px;background:linear-gradient(90deg,{ac},transparent);margin:.3rem auto 0;border-radius:2px}}
.stButton>button{{background:linear-gradient(135deg,{ac},#2fa87a) !important;color:#0a1520 !important;
  font-weight:700 !important;border:none !important;border-radius:8px !important;transition:all .2s}}
.stButton>button:hover{{filter:brightness(1.12) !important;transform:translateY(-1px)}}
textarea{{background:{ib} !important;color:{txt} !important;border:1px solid {brd} !important;border-radius:8px !important}}
.card{{background:{card};border:1px solid {brd};border-radius:12px;padding:.8rem 1rem;margin:.4rem 0}}
.card .lbl{{font-size:9px;font-weight:700;text-transform:uppercase;color:{sub};letter-spacing:.15em}}
.card .body{{font-size:15px;color:{txt};margin-top:.3rem;line-height:1.7}}
.card .meta{{font-size:10px;color:{sub};margin-top:5px;opacity:.75}}
.sh{{font-size:9px;font-weight:700;text-transform:uppercase;color:{sub};margin:.55rem 0 .25rem;letter-spacing:.1em}}
[data-testid="stSidebar"]{{background:{sbg} !important;border-right:1px solid {brd} !important}}
.hist{{padding:5px 8px;border-bottom:1px solid {brd};font-size:12px}}
.hist .o{{color:{txt}}} .hist .tr{{color:{ac}}} .hist .m{{font-size:9px;color:{sub};opacity:.6}}
div[data-testid="stAudioInput"]>div{{background:{card};border:2px solid {brd};border-radius:60px}}
/* chat bubble */
.cb{{border-radius:14px;padding:.85rem 1.1rem;margin-bottom:.75rem;
     border:1px solid {brd};background:{card};transition:box-shadow .2s}}
.cb:hover{{box-shadow:0 4px 20px {brd}}}
.cb-hd{{display:flex;align-items:center;gap:10px;margin-bottom:.45rem}}
.cb-ic{{font-size:24px;line-height:1}}
.cb-nfo{{display:flex;flex-direction:column;gap:2px}}
.cb-spk{{font-size:14px;font-weight:700;color:{ac}}}
.cb-lang{{font-size:10px;color:{sub};opacity:.85}}
.cb-ts{{font-size:9px;color:{sub};opacity:.5;margin-top:2px}}
.cb-orig{{font-size:13px;color:{sub};font-style:italic;margin-bottom:.35rem;
          border-left:3px solid {brd};padding-left:8px;opacity:.85}}
.cb-trans{{font-size:16px;color:{txt};font-weight:600;line-height:1.65}}
.cb-eng{{font-size:9px;color:{sub};opacity:.55;margin-top:5px}}
.stSelectbox label,.stMultiSelect label{{color:{sub} !important}}
.stSelectbox>div>div,.stMultiSelect>div>div{{background:{ib} !important;color:{txt} !important;border-color:{brd} !important}}
button[data-baseweb="tab"]{{font-family:'Space Grotesk',sans-serif !important;font-size:12px !important;
  font-weight:600 !important;color:{tl} !important;background:transparent !important;
  border:none !important;border-radius:8px 8px 0 0 !important;transition:all .2s}}
button[data-baseweb="tab"][aria-selected="true"]{{background:{card} !important;color:{ac} !important;
  border-bottom:2px solid {ac} !important}}
div[data-baseweb="tab-list"]{{gap:4px !important;border-bottom:1px solid {brd} !important}}
hr{{margin:.4rem 0;border:none;height:1px;background:linear-gradient(90deg,transparent,{brd},transparent)}}
.info-box{{background:{card};border:1px solid {brd};border-radius:10px;padding:.75rem 1rem;
           font-size:13px;color:{txt};margin-bottom:.7rem;line-height:1.6}}
"""

st.markdown(f"<style>{_css(st.session_state.theme)}</style>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  Header
# ══════════════════════════════════════════════════════════════════
st.markdown("""<div class="hdr">
<span class="br">✦ Smart Voice Translator ✦</span>
<h1>HN <span>TRANSLATOR</span></h1>
<div class="dv"></div></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  Sidebar
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    if st.button("🌓 تبديل المظهر", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()
    st.divider()

    with st.expander("🔑 مفاتيح API", expanded=False):
        for key, label, hint in [
            ("groq_api_key",   "🎤 Groq  (STT + رؤية الصور)", "احصل على مفتاح مجاني من console.groq.com"),
            ("deepl_api_key",  "🌐 DeepL (ترجمة عالية الجودة)","500 ألف حرف/شهر مجاناً"),
            ("cohere_api_key", "🔄 Cohere (STT احتياطي)",      ""),
        ]:
            nv = st.text_input(label, type="password",
                               value=st.session_state[key], help=hint, key=f"_i_{key}")
            if nv != st.session_state[key]: st.session_state[key] = nv

        st.divider()
        if st.session_state.groq_api_key:
            st.success("🎤 Groq نشط — STT + رؤية الصور")
        else:
            st.warning("⚠️ Groq غير نشط\nاحصل على مفتاح مجاني:\nconsole.groq.com")
        if st.session_state.deepl_api_key:
            st.success("🌐 DeepL نشط")
        else:
            st.info("ℹ️ DeepL غير نشط — Google مجاناً")

    st.divider()
    history = get_history(80)
    if history:
        ca, cb = st.columns(2)
        with ca:
            if st.button("🗑️ مسح", use_container_width=True):
                clear_history(); st.rerun()
        with cb:
            b64h = base64.b64encode(json.dumps(history, ensure_ascii=False, indent=2).encode()).decode()
            st.markdown(f'<a href="data:application/json;base64,{b64h}" download="history.json">📥 تصدير</a>',
                        unsafe_allow_html=True)
        for it in history:
            st.markdown(f"""<div class="hist">
<div class="o">{it.get('original','')[:55]}</div>
<div class="tr">{it.get('translated','')[:55]}</div>
<div class="m">{it.get('engine','')} · {it.get('target_lang','')} · {it.get('time','')}</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center;font-size:28px;opacity:.25;padding:1rem'>📭</div>",
                    unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  اختيار اللغات (مشترك بين التبويبات 1–4)
# ══════════════════════════════════════════════════════════════════
st.markdown('<div class="sh">Translation Direction</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([1, .18, 1])
with c1:
    src_name = st.selectbox("From", LANG_NAMES,
                            index=LANG_NAMES.index(st.session_state.source_lang)
                            if st.session_state.source_lang in LANG_NAMES else 0,
                            key="_src")
with c2:
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    if st.button("⇄", use_container_width=True, key="_swap"):
        s = st.session_state.source_lang
        t = st.session_state.target_lang
        st.session_state.source_lang = t if t != "Auto-Detect" else "English"
        st.session_state.target_lang = s if s != "Auto-Detect" else "Arabic"
        st.rerun()
with c3:
    tgt_opts = [k for k in LANG_NAMES if k not in (src_name, "Auto-Detect")]
    if st.session_state.target_lang not in tgt_opts:
        st.session_state.target_lang = tgt_opts[0]
    tgt_name = st.selectbox("To", tgt_opts,
                            index=tgt_opts.index(st.session_state.target_lang),
                            key="_tgt")

st.session_state.source_lang = src_name
st.session_state.target_lang = tgt_name
src_google = ALL_LANGUAGES.get(src_name, {}).get("google", "auto")
tgt_gtts   = ALL_LANGUAGES.get(tgt_name, {}).get("gtts", "en")

# ══════════════════════════════════════════════════════════════════
#  التبويبات
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🎤 Voice", "📝 Text", "📄 File", "📷 Camera", "👥 Group Chat"]
)

# ─────────────────────── Tab 1: Voice ───────────────────────────
with tab1:
    st.markdown("---")
    audio_val = st.audio_input("🎤 سجّل صوتك", key="_mic1", label_visibility="visible")

    if audio_val:
        with st.spinner("⏳ التعرف على الكلام..."):
            recognized, _ = speech_to_text(audio_val.getvalue(), src_google)

        if recognized:
            st.success(f"✅ {recognized}")
            with st.spinner("⏳ الترجمة..."):
                translated, engine = translate_text(recognized, tgt_name, src_name)
            if translated:
                emotion = analyze_emotion(recognized)
                domains = detect_domains(recognized)
                d_badges = " ".join(f'{_DOMAINS[d]["e"]} {_DOMAINS[d]["n"]}' for d in domains)
                st.markdown(f"""<div class="card">
<span class="lbl">✦ الترجمة</span>
<div class="body">{translated}</div>
<div class="meta">{emotion} &nbsp;·&nbsp; {engine} {("&nbsp;·&nbsp; "+d_badges) if d_badges else ""}</div>
</div>""", unsafe_allow_html=True)
                st.code(translated, language=None)
                aud = tts(translated, tgt_gtts)
                if aud: st.audio(aud, format="audio/mp3")
                save_translation(recognized, translated, emotion, src_name, tgt_name, engine)
            else:
                st.error(f"❌ الترجمة فشلت: {engine}")
        else:
            st.error("❌ تعذر التعرف على الكلام — تأكد من وضوح الصوت")

# ─────────────────────── Tab 2: Text ────────────────────────────
with tab2:
    st.markdown("---")
    input_text = st.text_area("📝 أدخل النص", height=110,
                              placeholder="اكتب أو الصق النص هنا...",
                              value=st.session_state.input_text, key="_txt")
    st.session_state.input_text = input_text

    if input_text.strip():
        domains = detect_domains(input_text)
        if domains:
            badges = " ".join(f'<span style="background:rgba(78,203,160,.15);'
                              f'border:1px solid rgba(78,203,160,.3);border-radius:20px;'
                              f'padding:2px 9px;font-size:11px;margin-right:4px">'
                              f'{_DOMAINS[d]["e"]} {_DOMAINS[d]["n"]}</span>' for d in domains)
            st.markdown(f'<div style="margin-bottom:.5rem">🔍 {badges}</div>',
                        unsafe_allow_html=True)

    if st.button("Translate ✦", use_container_width=True, key="_txt_btn"):
        if not input_text.strip():
            st.warning("الرجاء إدخال نص.")
        else:
            with st.spinner("جاري الترجمة..."):
                translated, engine = translate_text(input_text, tgt_name, src_name)
            if translated:
                emotion = analyze_emotion(input_text)
                st.markdown(f"""<div class="card">
<span class="lbl">✦ الترجمة</span>
<div class="body">{translated}</div>
<div class="meta">{emotion} &nbsp;·&nbsp; {engine}</div>
</div>""", unsafe_allow_html=True)
                st.code(translated, language=None)
                aud = tts(translated, tgt_gtts)
                if aud: st.audio(aud, format="audio/mp3")
                save_translation(input_text, translated, emotion, src_name, tgt_name, engine)
            else:
                st.error(f"❌ {engine}")

# ─────────────────────── Tab 3: File ────────────────────────────
with tab3:
    st.markdown("---")
    uploaded = st.file_uploader("اختر ملفاً (PDF · DOCX · XLSX · TXT)", key="_file_up")
    if uploaded:
        st.caption(f"📎 {uploaded.name} — {len(uploaded.getvalue())//1024} KB")
        if st.button("🔍 استخراج وترجمة", key="_file_btn"):
            with st.spinner("استخراج النص..."):
                extracted, err = extract_file_text(uploaded.getvalue(), uploaded.name)
            if extracted:
                st.markdown('<div class="sh">النص المستخرج</div>', unsafe_allow_html=True)
                st.code(extracted[:2500] + ("…" if len(extracted) > 2500 else ""), language=None)
                st.caption(f"الكلمات: {len(extracted.split())}")
                with st.spinner("الترجمة..."):
                    translated, engine = translate_text(extracted, tgt_name, src_name)
                if translated:
                    emotion = analyze_emotion(extracted[:500])
                    st.markdown(f"""<div class="card">
<span class="lbl">✦ الترجمة</span>
<div class="body">{translated}</div>
<div class="meta">{engine}</div>
</div>""", unsafe_allow_html=True)
                    ca, cb = st.columns(2)
                    with ca:
                        st.download_button("📥 النص الأصلي", data=extracted,
                                           file_name="original.txt", mime="text/plain")
                    with cb:
                        st.download_button("📥 الترجمة", data=translated,
                                           file_name="translated.txt", mime="text/plain")
                    aud = tts(translated, tgt_gtts)
                    if aud: st.audio(aud, format="audio/mp3")
                    save_translation(extracted[:300], translated, emotion, "File", tgt_name, engine)
                else:
                    st.error(f"❌ الترجمة فشلت: {engine}")
            else:
                st.error(f"❌ الاستخراج فشل: {err}")

# ─────────────────────── Tab 4: Camera ──────────────────────────
with tab4:
    st.markdown("---")
    st.markdown("""<div class="info-box">
📷 <b>OCR الصور</b> — يستخدم <b>Groq Vision</b> (ذكاء اصطناعي) لاستخراج النص من الصور
بدقة عالية، يدعم العربية والإنجليزية وجميع اللغات.
<br>💡 تأكد من إضافة مفتاح Groq في الإعدادات.
</div>""", unsafe_allow_html=True)

    cam_file = st.file_uploader("اختر صورة", type=["png","jpg","jpeg","webp","bmp"], key="_cam")
    if cam_file:
        img_bytes = cam_file.getvalue()
        try:
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            st.image(pil_img, caption=cam_file.name, use_container_width=True)
        except Exception as e:
            st.warning(f"تعذر عرض الصورة: {e}")

        if st.button("🔍 استخراج النص وترجمته", key="_cam_btn"):
            # ── OCR ─────────────────────────────────────────────
            ocr_spinner = "جاري استخراج النص بـ Groq Vision..." if st.session_state.groq_api_key \
                          else "جاري استخراج النص..."
            with st.spinner(ocr_spinner):
                ocr_langs = ALL_LANGUAGES.get(src_name, {}).get("ocr", ["en"])
                extracted, err = extract_image_text(img_bytes, ocr_langs)

            if not extracted:
                st.error(f"❌ OCR فشل: {err}")
                if not st.session_state.groq_api_key:
                    st.info("💡 أضف مفتاح Groq من console.groq.com للحصول على أفضل نتائج OCR")
            else:
                # اكتشف لغة النص تلقائياً
                lc, ln = detect_text_lang(extracted)
                src_for_trans = _LC2NAME.get(lc, src_name)

                st.markdown('<div class="sh">النص المستخرج</div>', unsafe_allow_html=True)
                st.code(extracted, language=None)
                st.caption(f"اللغة المكتشفة: {ln} · الكلمات: {len(extracted.split())}")

                with st.spinner("الترجمة..."):
                    translated, engine = translate_text(extracted, tgt_name, src_for_trans)

                if translated:
                    emotion = analyze_emotion(extracted[:500])
                    st.markdown(f"""<div class="card">
<span class="lbl">✦ الترجمة ({src_for_trans} → {tgt_name})</span>
<div class="body">{translated}</div>
<div class="meta">{emotion} &nbsp;·&nbsp; {engine}</div>
</div>""", unsafe_allow_html=True)
                    st.code(translated, language=None)
                    ca, cb = st.columns(2)
                    with ca:
                        st.download_button("📥 النص الأصلي", data=extracted,
                                           file_name="ocr_text.txt", mime="text/plain")
                    with cb:
                        st.download_button("📥 الترجمة", data=translated,
                                           file_name="ocr_translated.txt", mime="text/plain")
                    aud = tts(translated, tgt_gtts)
                    if aud: st.audio(aud, format="audio/mp3")
                    save_translation(extracted, translated, emotion,
                                     f"Camera/{ln}", tgt_name, engine)
                else:
                    st.error(f"❌ الترجمة فشلت: {engine}")

# ─────────────────────── Tab 5: Group Chat ──────────────────────
with tab5:
    st.markdown("---")
    st.markdown("""<div class="info-box">
👥 <b>كيف يعمل Group Chat؟</b><br>
① سجّل محادثة بين أشخاص يتحدثون بلغات مختلفة في وقت واحد<br>
② التطبيق يكتشف <b>تلقائياً</b> لغة كل متحدث ويحدد هويته<br>
③ يُترجم كل مقطع إلى اللغة الهدف مع الاحتفاظ بهوية كل متحدث<br>
④ يعرض النتيجة كفقاعات محادثة: المتحدث ١ (عربي)، المتحدث ٢ (إنجليزي)...
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="sh">🎯 اللغة الهدف للترجمة</div>', unsafe_allow_html=True)
    grp_tgt = st.selectbox("اللغة الهدف",
                           options=LANG_NAMES_NO_AUTO,
                           index=LANG_NAMES_NO_AUTO.index(tgt_name)
                           if tgt_name in LANG_NAMES_NO_AUTO else 0,
                           key="_g_tgt")
    grp_tgt_gtts = ALL_LANGUAGES.get(grp_tgt, {}).get("gtts", "en")

    st.markdown("---")
    st.markdown('<div class="sh">🎤 سجّل المحادثة</div>', unsafe_allow_html=True)
    st.caption("يمكن أن يتحدث أكثر من شخص بأكثر من لغة في نفس التسجيل")

    grp_audio = st.audio_input("ابدأ التسجيل", key="_g_mic", label_visibility="collapsed")

    if grp_audio:
        if st.button("🚀 تحليل وترجمة المحادثة", use_container_width=True, key="_g_btn"):

            if not st.session_state.groq_api_key:
                st.warning("⚠️ هذه الميزة تعتمد على Groq لكشف المتحدثين. أضف مفتاح Groq من console.groq.com")

            bar = st.progress(0, text="⏳ جاري التعرف على الكلام وتمييز المتحدثين...")
            results, err = group_chat_analyze(grp_audio.getvalue(), grp_tgt)
            bar.progress(80, text="⏳ الترجمة...")

            if not results:
                bar.empty()
                st.error(f"❌ {err or 'تعذر تحليل الصوت'}")
            else:
                bar.progress(100, text="✅ اكتمل!")
                time.sleep(0.3); bar.empty()

                speakers = sorted({r["speaker_num"] for r in results})
                st.markdown(f"""
<div style='text-align:center;margin:.5rem 0 1rem;font-size:13px;opacity:.7'>
تم اكتشاف <b>{len(results)}</b> مقطع كلامي ·
<b>{len(speakers)}</b> متحدث{'ون' if len(speakers)>1 else ''}
</div>""", unsafe_allow_html=True)

                full_log = []

                for item in results:
                    spk   = item["speaker_num"]
                    icon  = item["speaker_icon"]
                    lang  = item["lang_name"]
                    lc    = item["lang_code"]
                    orig  = item["original"]
                    trans = item["translated"] or "—"
                    eng   = item["engine"]
                    t0, t1 = item["start"], item["end"]
                    ts    = f"{t0:.1f}s – {t1:.1f}s" if t1 > 0 else ""

                    # لون مختلف لكل متحدث
                    hue = (spk * 47) % 360
                    spk_color = f"hsl({hue},60%,60%)"

                    st.markdown(f"""<div class="cb">
  <div class="cb-hd">
    <span class="cb-ic">{icon}</span>
    <div class="cb-nfo">
      <span class="cb-spk" style="color:{spk_color}">المتحدث {spk}</span>
      <span class="cb-lang">🌐 {lang}</span>
      {'<span class="cb-ts">⏱ '+ts+'</span>' if ts else ''}
    </div>
  </div>
  <div class="cb-orig">"{orig}"</div>
  <div class="cb-trans">{trans}</div>
  <div class="cb-eng">{eng}</div>
</div>""", unsafe_allow_html=True)

                    aud = tts(trans, grp_tgt_gtts)
                    if aud: st.audio(aud, format="audio/mp3")

                    emotion = analyze_emotion(orig)
                    save_translation(orig, trans, emotion, f"Group/{lang}", grp_tgt, eng)
                    full_log.append(
                        f"المتحدث {spk} ({lang}) [{ts}]\n"
                        f"  الأصلي  : {orig}\n"
                        f"  الترجمة : {trans}\n"
                        f"  المشاعر : {emotion}\n"
                    )

                st.markdown("---")
                st.download_button(
                    "📥 تحميل محضر المحادثة الكامل",
                    data="\n".join(full_log),
                    file_name="group_transcript.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="_g_dl"
                )

# ══════════════════════════════════════════════════════════════════
#  Footer
# ══════════════════════════════════════════════════════════════════
st.markdown("""<div style='text-align:center;padding:1.2rem 0 .4rem;
color:rgba(100,130,170,.28);font-size:9px;letter-spacing:.12em;text-transform:uppercase'>
HN TRANSLATOR · Groq Whisper + DeepL + Google · Multi-Language Voice Suite
</div>""", unsafe_allow_html=True)
