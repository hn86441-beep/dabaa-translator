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
    import easyocr;        EASYOCR_OK = True
except ImportError:        EASYOCR_OK = False

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
    from langdetect import detect as langdetect_detect; LANGDETECT_OK = True
except ImportError:        LANGDETECT_OK = False

from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS

# ══════════════════════════════════════════════════════════════════
#  جدول اللغات
#  google  → رمز Google Translate / gTTS
#  deepl   → رمز DeepL (None = غير مدعوم)
#  whisper → رمز ISO-639-1 لـ Whisper / Groq
#  ocr     → قائمة لغات EasyOCR
# ══════════════════════════════════════════════════════════════════
ALL_LANGUAGES = {
    "Auto-Detect": {"google":"auto",  "deepl":None,    "gtts":"en",    "whisper":None, "ocr":["en","ar"]},
    "Arabic":      {"google":"ar",    "deepl":"AR",    "gtts":"ar",    "whisper":"ar", "ocr":["ar","en"]},
    "English":     {"google":"en",    "deepl":"EN-US", "gtts":"en",    "whisper":"en", "ocr":["en"]},
    "Russian":     {"google":"ru",    "deepl":"RU",    "gtts":"ru",    "whisper":"ru", "ocr":["ru","en"]},
    "Chinese":     {"google":"zh-CN", "deepl":"ZH",    "gtts":"zh-cn", "whisper":"zh", "ocr":["ch_sim","en"]},
    "German":      {"google":"de",    "deepl":"DE",    "gtts":"de",    "whisper":"de", "ocr":["de","en"]},
    "Spanish":     {"google":"es",    "deepl":"ES",    "gtts":"es",    "whisper":"es", "ocr":["es","en"]},
    "French":      {"google":"fr",    "deepl":"FR",    "gtts":"fr",    "whisper":"fr", "ocr":["fr","en"]},
    "Portuguese":  {"google":"pt",    "deepl":"PT-PT", "gtts":"pt",    "whisper":"pt", "ocr":["pt","en"]},
    "Italian":     {"google":"it",    "deepl":"IT",    "gtts":"it",    "whisper":"it", "ocr":["it","en"]},
    "Japanese":    {"google":"ja",    "deepl":"JA",    "gtts":"ja",    "whisper":"ja", "ocr":["ja","en"]},
    "Korean":      {"google":"ko",    "deepl":"KO",    "gtts":"ko",    "whisper":"ko", "ocr":["ko","en"]},
    "Turkish":     {"google":"tr",    "deepl":"TR",    "gtts":"tr",    "whisper":"tr", "ocr":["tr","en"]},
    "Dutch":       {"google":"nl",    "deepl":"NL",    "gtts":"nl",    "whisper":"nl", "ocr":["nl","en"]},
    "Polish":      {"google":"pl",    "deepl":"PL",    "gtts":"pl",    "whisper":"pl", "ocr":["pl","en"]},
    "Ukrainian":   {"google":"uk",    "deepl":"UK",    "gtts":"uk",    "whisper":"uk", "ocr":["uk","en"]},
    "Swedish":     {"google":"sv",    "deepl":"SV",    "gtts":"sv",    "whisper":"sv", "ocr":["sv","en"]},
    "Danish":      {"google":"da",    "deepl":"DA",    "gtts":"da",    "whisper":"da", "ocr":["da","en"]},
    "Finnish":     {"google":"fi",    "deepl":"FI",    "gtts":"fi",    "whisper":"fi", "ocr":["fi","en"]},
    "Romanian":    {"google":"ro",    "deepl":"RO",    "gtts":"ro",    "whisper":"ro", "ocr":["ro","en"]},
    "Hungarian":   {"google":"hu",    "deepl":"HU",    "gtts":"hu",    "whisper":"hu", "ocr":["hu","en"]},
    "Czech":       {"google":"cs",    "deepl":"CS",    "gtts":"cs",    "whisper":"cs", "ocr":["cs","en"]},
    "Bulgarian":   {"google":"bg",    "deepl":"BG",    "gtts":"bg",    "whisper":"bg", "ocr":["bg","en"]},
    "Greek":       {"google":"el",    "deepl":"EL",    "gtts":"el",    "whisper":"el", "ocr":["el","en"]},
    "Indonesian":  {"google":"id",    "deepl":"ID",    "gtts":"id",    "whisper":"id", "ocr":["id","en"]},
    "Hindi":       {"google":"hi",    "deepl":None,    "gtts":"hi",    "whisper":"hi", "ocr":["hi","en"]},
    "Persian":     {"google":"fa",    "deepl":None,    "gtts":"fa",    "whisper":"fa", "ocr":["fa","en"]},
    "Hebrew":      {"google":"iw",    "deepl":None,    "gtts":"iw",    "whisper":"he", "ocr":["he","en"]},
    "Urdu":        {"google":"ur",    "deepl":None,    "gtts":"ur",    "whisper":"ur", "ocr":["ur","en"]},
}

LANG_NAMES        = list(ALL_LANGUAGES.keys())
LANG_NAMES_NO_AUTO = [k for k in LANG_NAMES if k != "Auto-Detect"]

# تحويل رمز langdetect → اسم اللغة في التطبيق
DETECT_CODE_TO_NAME = {
    "ar":"Arabic","en":"English","ru":"Russian","zh-cn":"Chinese","zh-tw":"Chinese",
    "de":"German","es":"Spanish","fr":"French","pt":"Portuguese","it":"Italian",
    "ja":"Japanese","ko":"Korean","tr":"Turkish","nl":"Dutch","pl":"Polish",
    "uk":"Ukrainian","sv":"Swedish","da":"Danish","fi":"Finnish","ro":"Romanian",
    "hu":"Hungarian","cs":"Czech","bg":"Bulgarian","el":"Greek","id":"Indonesian",
    "hi":"Hindi","fa":"Persian","he":"Hebrew","ur":"Urdu",
}

# رموز اللغات للاستخدام في Whisper/Groq
WHISPER_MAP = {v["google"]: v["whisper"] for v in ALL_LANGUAGES.values() if v.get("whisper")}

# ══════════════════════════════════════════════════════════════════
#  قاعدة البيانات — /tmp/ للتوافق مع Streamlit Cloud
# ══════════════════════════════════════════════════════════════════
DB_PATH = os.path.join(tempfile.gettempdir(), "hn_translations.db")

def _db():
    return sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)

def init_db():
    try:
        conn = _db()
        conn.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original TEXT NOT NULL DEFAULT '',
            translated TEXT NOT NULL DEFAULT '',
            emotion TEXT DEFAULT '',
            source_lang TEXT DEFAULT '',
            target_lang TEXT DEFAULT '',
            engine TEXT DEFAULT '',
            timestamp TEXT DEFAULT ''
        )''')
        existing = {r[1] for r in conn.execute("PRAGMA table_info(history)")}
        for col, typ in [("engine","TEXT DEFAULT ''"),("emotion","TEXT DEFAULT ''"),
                         ("source_lang","TEXT DEFAULT ''"),("target_lang","TEXT DEFAULT ''")]:
            if col not in existing:
                conn.execute(f"ALTER TABLE history ADD COLUMN {col} {typ}")
        conn.commit(); conn.close()
    except Exception as e:
        if "db_init_err" not in st.session_state:
            st.session_state["db_init_err"] = str(e)

def _mem_save(entry):
    if "_mem" not in st.session_state: st.session_state["_mem"] = []
    st.session_state["_mem"].insert(0, entry)
    st.session_state["_mem"] = st.session_state["_mem"][:300]

def save_translation(orig, trans, emotion, src, tgt, engine=""):
    entry = {"original":str(orig or "")[:500],"translated":str(trans or "")[:500],
             "emotion":str(emotion or ""),"source_lang":str(src or ""),
             "target_lang":str(tgt or ""),"engine":str(engine or ""),
             "time":datetime.now().strftime("%Y-%m-%d %H:%M")}
    _mem_save(entry)
    try:
        conn = _db()
        conn.execute('''INSERT INTO history (original,translated,emotion,source_lang,target_lang,engine,timestamp)
                        VALUES (?,?,?,?,?,?,?)''',
                     tuple(entry[k] for k in ["original","translated","emotion","source_lang","target_lang","engine","time"]))
        conn.commit(); conn.close()
    except Exception: pass

def get_history(limit=100):
    try:
        conn = _db()
        rows = conn.execute('''SELECT original,translated,emotion,source_lang,target_lang,engine,timestamp
                               FROM history ORDER BY id DESC LIMIT ?''',(limit,)).fetchall()
        conn.close()
        if rows:
            return [{"original":r[0],"translated":r[1],"emotion":r[2] or "",
                     "source_lang":r[3] or "","target_lang":r[4] or "",
                     "engine":r[5] or "","time":r[6] or ""} for r in rows]
    except Exception: pass
    return st.session_state.get("_mem",[])[:limit]

def clear_history():
    st.session_state["_mem"] = []
    try:
        conn = _db(); conn.execute("DELETE FROM history"); conn.commit(); conn.close()
    except Exception: pass

init_db()

# ══════════════════════════════════════════════════════════════════
#  تحليل المشاعر — transformers أولاً، ثم كلمات مفتاحية
# ══════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def _load_emotion_model():
    if not HF_OK: return None
    try:
        return hf_pipeline(
            "text-classification",
            model="tabularisai/multilingual-sentiment-analysis",
            top_k=1,
        )
    except Exception:
        return None

_EMOTION_MODEL = _load_emotion_model()

_POS_WORDS = [
    "شكر","ممتاز","جيد","رائع","سعيد","فرح","أحب","يسعدني","حلو","عظيم",
    "مبهج","مثير","جميل","يعجبني","موافق","نعم","صحيح","صواب","ممتاز","بارع",
    "happy","good","great","excellent","love","wonderful","amazing","joy",
    "nice","beautiful","perfect","awesome","fantastic","enjoy","pleasure",
    "glad","delighted","positive","agree","correct","right","super",
]
_NEG_WORDS = [
    "حزين","سيء","كره","مشكلة","غضب","ألم","صعب","خطأ","فشل","مزعج",
    "لا","رفض","خطير","مرفوض","ممنوع","مخيف","قلق","توتر","عنيف",
    "sad","bad","hate","problem","angry","pain","difficult","error","fail",
    "no","reject","dangerous","refused","banned","scary","anxious","tense",
    "terrible","horrible","awful","wrong","disaster","violence","threat",
]

def analyze_emotion(text: str) -> str:
    if not text or not text.strip():
        return "😐 محايد"
    # 1️⃣ transformers
    if _EMOTION_MODEL is not None:
        try:
            label = _EMOTION_MODEL(text[:512])[0][0]["label"].upper()
            score = _EMOTION_MODEL(text[:512])[0][0].get("score", 0)
            if score >= 0.55:
                if any(x in label for x in ("POSITIVE","POS","HAPPY","JOY")):
                    return "😊 إيجابي"
                if any(x in label for x in ("NEGATIVE","NEG","SAD","ANGER")):
                    return "😔 سلبي"
                if "NEUTRAL" in label:
                    return "😐 محايد"
        except Exception:
            pass
    # 2️⃣ كلمات مفتاحية
    tl = text.lower()
    pos = sum(1 for w in _POS_WORDS if w in tl)
    neg = sum(1 for w in _NEG_WORDS if w in tl)
    if pos > neg:   return "😊 إيجابي"
    if neg > pos:   return "😔 سلبي"
    return "😐 محايد"

# ══════════════════════════════════════════════════════════════════
#  كشف اللغة بالنص (langdetect + احتياطي يدوي)
# ══════════════════════════════════════════════════════════════════
def detect_text_language(text: str) -> tuple[str, str]:
    """
    يُعيد (رمز_اللغة, اسم_اللغة).
    """
    if not text: return "en", "English"
    # فحص الخط العربي
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    if arabic / max(len(text.strip()), 1) > 0.25:
        return "ar", "Arabic"
    # فحص الأحرف الروسية (سيريلية)
    cyrillic = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
    if cyrillic / max(len(text.strip()), 1) > 0.25:
        return "ru", "Russian"
    # langdetect
    if LANGDETECT_OK:
        try:
            code = langdetect_detect(text)
            name = DETECT_CODE_TO_NAME.get(code, code.capitalize())
            return code, name
        except Exception:
            pass
    return "en", "English"

# ══════════════════════════════════════════════════════════════════
#  الترجمة — DeepL → Google → MyMemory
# ══════════════════════════════════════════════════════════════════
def _deepl_translate(text: str, deepl_target: str, api_key: str):
    endpoint = ("https://api-free.deepl.com/v2/translate"
                if api_key.endswith(":fx") else "https://api.deepl.com/v2/translate")
    try:
        r = requests.post(endpoint,
                          headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                          data={"text": text, "target_lang": deepl_target}, timeout=15)
        if r.status_code == 200:
            return r.json()["translations"][0]["text"], None
        return None, f"DeepL {r.status_code}"
    except Exception as e: return None, str(e)

def _google_translate(text: str, tgt: str, src: str = "auto"):
    try:
        return GoogleTranslator(source=src or "auto", target=tgt).translate(text), None
    except Exception as e1:
        try:
            s = "en" if (not src or src == "auto") else src
            return MyMemoryTranslator(source=s, target=tgt).translate(text), None
        except Exception as e2:
            return None, f"{e1} | {e2}"

def translate_text(text: str, tgt_lang_name: str, src_lang_name: str = "Auto-Detect") -> tuple[str|None, str]:
    """
    يُعيد (نص_مترجم, اسم_المحرك).
    DeepL → Google.
    """
    if not text or not text.strip(): return None, "no text"
    info = ALL_LANGUAGES.get(tgt_lang_name, {})
    deepl_code  = info.get("deepl")
    google_code = info.get("google", "en")
    src_google  = ALL_LANGUAGES.get(src_lang_name, {}).get("google", "auto")
    ak = st.session_state.get("deepl_api_key", "")
    if ak and deepl_code:
        r, _ = _deepl_translate(text, deepl_code, ak)
        if r: return r, "DeepL ✦"
    r, err = _google_translate(text, google_code, src_google)
    return (r, "Google") if r else (None, err or "failed")

def translate_many(text: str, tgt_names: list[str], src_name: str = "Auto-Detect") -> dict:
    """ترجمة نص لعدة لغات دفعةً واحدة."""
    return {lng: {"text": t, "engine": e,
                  "gtts": ALL_LANGUAGES.get(lng, {}).get("gtts","en")}
            for lng in tgt_names for t, e in [translate_text(text, lng, src_name)]}

# ══════════════════════════════════════════════════════════════════
#  TTS — gTTS
# ══════════════════════════════════════════════════════════════════
def tts(text: str, gtts_lang: str = "en") -> io.BytesIO | None:
    if not text or not text.strip(): return None
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=gtts_lang, slow=False).write_to_fp(buf)
        buf.seek(0); return buf
    except Exception: return None

# ══════════════════════════════════════════════════════════════════
#  استخراج النص من الملفات
# ══════════════════════════════════════════════════════════════════
def extract_file_text(file_bytes: bytes, filename: str) -> tuple[str|None, str|None]:
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
#  EasyOCR — استخراج النص من الصور
# ══════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def _load_ocr(langs_tuple: tuple):
    if not EASYOCR_OK: return None
    try:
        return easyocr.Reader(list(langs_tuple), gpu=False, verbose=False)
    except Exception: return None

def extract_image_text(img_bytes: bytes, ocr_langs: list[str]) -> tuple[str|None, str|None]:
    if not EASYOCR_OK: return None, "EasyOCR غير مثبت"
    try:
        import numpy as np
        reader = _load_ocr(tuple(ocr_langs))
        if reader is None: return None, "تعذر تحميل EasyOCR"
        img_np = np.array(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
        results = reader.readtext(img_np, detail=0, paragraph=True)
        txt = " ".join(results).strip()
        return (txt, None) if txt else (None, "لم يُعثر على نص في الصورة")
    except Exception as e: return None, str(e)

# ══════════════════════════════════════════════════════════════════
#  التعرف على الصوت
#  الأولوية: Groq (whisper-large-v3-turbo) → Cohere → Whisper محلي
# ══════════════════════════════════════════════════════════════════
def _norm_whisper(code: str) -> str | None:
    if not code or code == "auto": return None
    table = {"zh-CN":"zh","zh-cn":"zh","iw":"he","auto":None}
    return table.get(code, code[:2])

# ── Groq ──────────────────────────────────────────────────────────
def _groq_transcribe(audio_bytes: bytes, lang_code: str = "auto",
                     verbose: bool = False) -> tuple[dict|str|None, str|None]:
    """
    verbose=True  → يُعيد dict كامل (segments, language, duration, text)
    verbose=False → يُعيد النص فقط
    """
    ak = st.session_state.get("groq_api_key","")
    if not ak: return None, "مفتاح Groq غير موجود"
    lang = _norm_whisper(lang_code)
    files = {
        "file": ("audio.wav", audio_bytes, "audio/wav"),
        "model": (None, "whisper-large-v3-turbo"),
        "response_format": (None, "verbose_json" if verbose else "json"),
    }
    if verbose:
        files["timestamp_granularities[]"] = (None, "segment")
    if lang:
        files["language"] = (None, lang)
    try:
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                          headers={"Authorization": f"Bearer {ak}"},
                          files=files, timeout=60)
        if r.status_code == 200:
            data = r.json()
            if verbose: return data, None
            txt = data.get("text","").strip()
            return (txt, None) if txt else (None, "لم يُكتشف كلام")
        return None, f"Groq {r.status_code}: {r.text[:120]}"
    except Exception as e: return None, str(e)

# ── Cohere ────────────────────────────────────────────────────────
def _cohere_transcribe(audio_bytes: bytes, lang_code: str = "en") -> tuple[str|None, str|None]:
    ak = st.session_state.get("cohere_api_key","")
    if not ak: return None, "مفتاح Cohere غير موجود"
    lang = _norm_whisper(lang_code) or "en"
    try:
        fields = OrderedDict([("language",lang),("model","cohere-transcribe-03-2026"),
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

# ── Whisper محلي ──────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _load_local_whisper():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("small", device="cpu", compute_type="int8")
    except Exception: return None

def _local_whisper(audio_bytes: bytes, lang: str|None = None) -> tuple[str|None, str|None]:
    m = _load_local_whisper()
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

# ── الدالة الموحّدة ───────────────────────────────────────────────
def speech_to_text(audio_bytes: bytes, lang_code: str = "auto") -> tuple[str|None, str|None]:
    wl = _norm_whisper(lang_code)
    if st.session_state.get("groq_api_key"):
        r, e = _groq_transcribe(audio_bytes, lang_code)
        if r: return r, None
    if st.session_state.get("cohere_api_key"):
        r, e = _cohere_transcribe(audio_bytes, lang_code)
        if r: return r, None
    return _local_whisper(audio_bytes, lang=wl)

# ══════════════════════════════════════════════════════════════════
#  محادثة جماعية متعددة اللغات
#  الخطوات:
#   1. نُرسل الصوت لـ Groq بـ verbose_json لأخذ segments مع توقيتات
#   2. نجمّع segments بفواصل صمت (>0.7 ثانية)
#   3. نكتشف لغة كل مجموعة بـ detect_text_language
#   4. نُعيّن رقم متحدث لكل لغة جديدة
#   5. نترجم كل نص إلى اللغة الهدف
# ══════════════════════════════════════════════════════════════════
SPEAKER_ICONS = ["🧑","👤","🙍","👱","🧔","👩","🧕","👲"]

def _group_segments(segments: list, gap: float = 0.7) -> list[list]:
    if not segments: return []
    groups, cur = [], [segments[0]]
    for i in range(1, len(segments)):
        if segments[i].get("start",0) - segments[i-1].get("end",0) >= gap:
            groups.append(cur); cur = []
        cur.append(segments[i])
    if cur: groups.append(cur)
    return groups

def group_chat_transcribe(audio_bytes: bytes, tgt_lang_name: str) -> tuple[list|None, str|None]:
    """
    يُعيد قائمة من:
    {
      speaker_num  : int,
      speaker_icon : str,
      lang_code    : str,
      lang_name    : str,
      original     : str,
      translated   : str,
      engine       : str,
      gtts_lang    : str,
      start        : float,
      end          : float,
    }
    """
    # ── خطوة 1: Groq verbose ──────────────────────────────────────
    data, err = _groq_transcribe(audio_bytes, lang_code="auto", verbose=True)
    if data is None:
        # احتياطي: Cohere / Whisper محلي (يُعيد نصاً واحداً)
        txt, err2 = (None, err)
        if st.session_state.get("cohere_api_key"):
            txt, err2 = _cohere_transcribe(audio_bytes)
        if not txt:
            txt, err2 = _local_whisper(audio_bytes)
        if not txt:
            return None, (err2 or err or "تعذر التعرف على الكلام")
        # نص واحد بدون segments
        lc, ln = detect_text_language(txt)
        trans, eng = translate_text(txt, tgt_lang_name,
                                    DETECT_CODE_TO_NAME.get(lc, "Auto-Detect"))
        return [{
            "speaker_num":1, "speaker_icon":SPEAKER_ICONS[0],
            "lang_code":lc, "lang_name":ln,
            "original":txt, "translated":trans or "",
            "engine":eng,
            "gtts_lang": ALL_LANGUAGES.get(
                DETECT_CODE_TO_NAME.get(lc,"English"),{}).get("gtts","en"),
            "start":0, "end":0,
        }], None

    segments = data.get("segments", [])
    if not segments:
        txt = data.get("text","").strip()
        if not txt: return None, "لم يُكتشف كلام"
        lc, ln = detect_text_language(txt)
        trans, eng = translate_text(txt, tgt_lang_name,
                                    DETECT_CODE_TO_NAME.get(lc,"Auto-Detect"))
        return [{
            "speaker_num":1,"speaker_icon":SPEAKER_ICONS[0],
            "lang_code":lc,"lang_name":ln,
            "original":txt,"translated":trans or "","engine":eng,
            "gtts_lang":ALL_LANGUAGES.get(
                DETECT_CODE_TO_NAME.get(lc,"English"),{}).get("gtts","en"),
            "start":0,"end":0,
        }], None

    # ── خطوة 2: تجميع بفواصل الصمت ────────────────────────────────
    groups = _group_segments(segments, gap=0.7)

    # ── خطوات 3-5 ──────────────────────────────────────────────────
    results       = []
    lang_to_spk   = {}   # lang_code → speaker_num
    spk_counter   = 1

    for grp in groups:
        txt = " ".join(s.get("text","").strip() for s in grp).strip()
        if not txt: continue

        lc, ln = detect_text_language(txt)

        # رقم المتحدث: نفس اللغة = نفس المتحدث (إلا إذا تخلل بينهما لغة أخرى)
        if lc not in lang_to_spk:
            lang_to_spk[lc] = spk_counter
            spk_counter += 1
        spk_num  = lang_to_spk[lc]
        spk_icon = SPEAKER_ICONS[min(spk_num - 1, len(SPEAKER_ICONS)-1)]

        src_name = DETECT_CODE_TO_NAME.get(lc, "Auto-Detect")
        trans, eng = translate_text(txt, tgt_lang_name, src_name)

        gtts_lang = ALL_LANGUAGES.get(
            DETECT_CODE_TO_NAME.get(lc,"English"), {}).get("gtts","en")

        results.append({
            "speaker_num":spk_num, "speaker_icon":spk_icon,
            "lang_code":lc, "lang_name":ln,
            "original":txt, "translated":trans or "",
            "engine":eng, "gtts_lang":gtts_lang,
            "start":grp[0].get("start",0), "end":grp[-1].get("end",0),
        })

    return (results if results else None), (None if results else "لم يُكتشف كلام")

# ══════════════════════════════════════════════════════════════════
#  كشف مجال النص
# ══════════════════════════════════════════════════════════════════
DOMAINS = {
    "political":    {"emoji":"🏛️","name":"Political"},
    "legal":        {"emoji":"⚖️","name":"Legal"},
    "economic":     {"emoji":"📈","name":"Economic"},
    "medical":      {"emoji":"🏥","name":"Medical"},
    "scientific":   {"emoji":"🔬","name":"Scientific"},
    "military":     {"emoji":"🎖️","name":"Military"},
    "educational":  {"emoji":"📚","name":"Educational"},
    "religious":    {"emoji":"🕌","name":"Religious"},
    "sports":       {"emoji":"⚽","name":"Sports"},
    "it":           {"emoji":"💻","name":"IT/Tech"},
    "tourism":      {"emoji":"✈️","name":"Tourism"},
    "general":      {"emoji":"💬","name":"General"},
}
_DKW = {
    "political":  ["minister","government","president","وزير","حكومة","رئيس","سياسة"],
    "legal":      ["contract","agreement","court","law","عقد","قانون","محكمة"],
    "economic":   ["economic","investment","budget","اقتصاد","استثمار","ميزانية"],
    "medical":    ["doctor","hospital","treatment","طبيب","مستشفى","علاج","مرض"],
    "scientific": ["research","experiment","theory","بحث","تجربة","نظرية"],
    "military":   ["military","army","weapon","جيش","عسكري","سلاح","حرب"],
    "educational":["school","university","teacher","مدرسة","جامعة","معلم"],
    "religious":  ["mosque","prayer","Quran","مسجد","صلاة","قرآن","دين"],
    "sports":     ["football","stadium","team","كرة","ملعب","فريق"],
    "it":         ["programming","software","website","برمجة","موقع","تطبيق"],
    "tourism":    ["hotel","travel","airport","فندق","سفر","مطار"],
}
def detect_domains(text: str) -> list:
    tl = text.lower()
    return sorted((d for d,kws in _DKW.items()
                   if any(k in tl for k in kws)), key=lambda d: -sum(tl.count(k) for k in _DKW[d]))[:3]

# ══════════════════════════════════════════════════════════════════
#  Secrets & Session State
# ══════════════════════════════════════════════════════════════════
def _sec(k, default=""):
    try: return st.secrets.get(k, default) or default
    except Exception: return default

_defs = {
    "theme":         "dark",
    "groq_api_key":  _sec("GROQ_API_KEY"),
    "deepl_api_key": _sec("DEEPL_API_KEY"),
    "cohere_api_key":_sec("COHERE_API_KEY"),
    "source_lang":   "Auto-Detect",
    "target_lang":   "Arabic",
    "input_text":    "",
}
for k, v in _defs.items():
    if k not in st.session_state: st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════
def _css(theme):
    if theme == "light":
        ac,bg,card,brd,txt,sub,sbg = (
            "#2a7a60","#f5f7fa","rgba(42,122,96,.06)","rgba(42,122,96,.2)",
            "#1a1a2e","rgba(42,122,96,.7)","rgba(255,255,255,.98)")
    else:
        ac,bg,card,brd,txt,sub,sbg = (
            "#4ECBA0","linear-gradient(135deg,#0a0a1a,#0f1728 40%,#0a1520)",
            "rgba(78,203,160,.06)","rgba(78,203,160,.2)","#e8f0ff",
            "rgba(78,203,160,.7)","rgba(10,10,26,.98)")
    inp_bg = "white" if theme=="light" else "rgba(255,255,255,.04)"
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
.stApp{{background:{bg} !important}}
.hdr{{text-align:center;padding:.8rem 0 .4rem}}
.hdr .brand{{font-size:10px;font-weight:700;letter-spacing:.3em;color:{ac};text-transform:uppercase;opacity:.8}}
.hdr h1{{font-family:'Space Grotesk',sans-serif;font-size:30px;font-weight:700;color:{txt};margin:0}}
.hdr h1 span{{color:{ac}}}
.hdr .div{{width:60px;height:3px;background:linear-gradient(90deg,{ac},transparent);margin:.3rem auto 0;border-radius:2px}}
.stButton>button{{background:linear-gradient(135deg,{ac},#2fa87a) !important;color:#0a1520 !important;
  font-weight:700 !important;border:none !important;border-radius:8px !important}}
.stButton>button:hover{{filter:brightness(1.1) !important}}
textarea{{background:{inp_bg} !important;color:{txt} !important;border:1px solid {brd} !important;border-radius:8px !important}}
.card{{background:{card};border:1px solid {brd};border-radius:12px;padding:.8rem 1rem;margin:.4rem 0}}
.card .lbl{{font-size:9px;font-weight:700;text-transform:uppercase;color:{sub};letter-spacing:.15em}}
.card .body{{font-size:15px;color:{txt};margin-top:.3rem;line-height:1.6}}
.card .eng{{font-size:9px;color:{sub};margin-top:4px;opacity:.7}}
.sh{{font-size:9px;font-weight:700;text-transform:uppercase;color:{sub};margin:.5rem 0 .25rem;letter-spacing:.1em}}
[data-testid="stSidebar"]{{background:{sbg} !important;border-right:1px solid {brd} !important}}
.hist{{padding:5px 8px;border-bottom:1px solid {brd};font-size:12px}}
.hist .o{{color:{txt}}} .hist .t{{color:{ac}}} .hist .m{{font-size:9px;color:{sub};opacity:.6}}
div[data-testid="stAudioInput"]>div{{background:{card};border:2px solid {brd};border-radius:60px}}
/* chat bubble ─ group */
.chat-bubble{{border-radius:16px;padding:.9rem 1.1rem;margin-bottom:.7rem;border:1px solid {brd};background:{card}}}
.chat-bubble .cb-header{{display:flex;align-items:center;gap:8px;margin-bottom:.5rem}}
.chat-bubble .cb-icon{{font-size:22px}}
.chat-bubble .cb-info{{display:flex;flex-direction:column}}
.chat-bubble .cb-spk{{font-size:13px;font-weight:700;color:{ac}}}
.chat-bubble .cb-lang{{font-size:10px;color:{sub};opacity:.8}}
.chat-bubble .cb-orig{{font-size:13px;color:{sub};font-style:italic;margin-bottom:.3rem;opacity:.85}}
.chat-bubble .cb-trans{{font-size:16px;color:{txt};font-weight:600;line-height:1.6}}
.chat-bubble .cb-eng{{font-size:9px;color:{sub};opacity:.6;margin-top:4px}}
.chat-bubble .cb-time{{font-size:9px;color:{sub};opacity:.5;float:right}}
.stSelectbox label,.stMultiSelect label{{color:{sub} !important}}
.stSelectbox>div>div,.stMultiSelect>div>div{{background:{inp_bg} !important;color:{txt} !important;border-color:{brd} !important}}
button[data-baseweb="tab"]{{font-family:'Space Grotesk',sans-serif !important;font-size:12px !important;
  font-weight:600 !important;color:{"#1a1a2e" if theme=="light" else "#b0c4de"} !important;
  background:transparent !important;border:none !important;border-radius:8px 8px 0 0 !important}}
button[data-baseweb="tab"][aria-selected="true"]{{background:{card} !important;color:{ac} !important;
  border-bottom:2px solid {ac} !important}}
div[data-baseweb="tab-list"]{{gap:4px !important;border-bottom:1px solid {brd} !important}}
hr{{margin:.4rem 0;border:none;height:1px;background:linear-gradient(90deg,transparent,{brd},transparent)}}
"""

st.markdown(f"<style>{_css(st.session_state.theme)}</style>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  Header
# ══════════════════════════════════════════════════════════════════
st.markdown("""<div class="hdr">
<span class="brand">✦ Smart Voice Translator ✦</span>
<h1>HN <span>TRANSLATOR</span></h1>
<div class="div"></div></div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  Sidebar
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    if st.button("🌓 تبديل المظهر", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme=="dark" else "dark"
        st.rerun()
    st.divider()

    with st.expander("🔑 مفاتيح API", expanded=False):
        for key, label, hint in [
            ("groq_api_key",   "🎤 Groq (STT — أفضل جودة)",  "console.groq.com — مجاني"),
            ("deepl_api_key",  "🌐 DeepL (ترجمة)",           "500,000 حرف/شهر مجاناً"),
            ("cohere_api_key", "🔄 Cohere (STT احتياطي)",    ""),
        ]:
            new_val = st.text_input(label, type="password",
                                    value=st.session_state[key],
                                    help=hint, key=f"_inp_{key}")
            if new_val != st.session_state[key]:
                st.session_state[key] = new_val
        st.divider()
        st.success("🎤 Groq نشط") if st.session_state.groq_api_key else st.warning("⚠️ Groq غير نشط — أضف مفتاحاً من console.groq.com")
        st.success("🌐 DeepL نشط") if st.session_state.deepl_api_key else st.info("ℹ️ DeepL غير نشط — Google مجاناً")

    st.divider()
    history = get_history(limit=80)
    if history:
        c1,c2 = st.columns(2)
        with c1:
            if st.button("🗑️ مسح",use_container_width=True): clear_history(); st.rerun()
        with c2:
            b64 = base64.b64encode(json.dumps(history,ensure_ascii=False,indent=2).encode()).decode()
            st.markdown(f'<a href="data:application/json;base64,{b64}" download="history.json">📥 تصدير</a>',
                        unsafe_allow_html=True)
        for item in history:
            st.markdown(f"""<div class="hist">
              <div class="o">{item.get('original','')[:55]}</div>
              <div class="t">{item.get('translated','')[:55]}</div>
              <div class="m">{item.get('engine','')} · {item.get('target_lang','')} · {item.get('time','')}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center;opacity:.3;font-size:28px'>📭</div>",
                    unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  اختيار اللغات (مشترك)
# ══════════════════════════════════════════════════════════════════
st.markdown('<div class="sh">Translation Direction</div>', unsafe_allow_html=True)
c1,c2,c3 = st.columns([1,.18,1])
with c1:
    src_name = st.selectbox("From", LANG_NAMES,
                            index=LANG_NAMES.index(st.session_state.source_lang)
                            if st.session_state.source_lang in LANG_NAMES else 0,
                            key="_src")
with c2:
    st.markdown("<div style='height:22px'></div>",unsafe_allow_html=True)
    if st.button("⇄", use_container_width=True):
        s,t = st.session_state.source_lang, st.session_state.target_lang
        if s == "Auto-Detect": s = "English"
        st.session_state.source_lang, st.session_state.target_lang = t, s
        st.rerun()
with c3:
    tgt_opts = [k for k in LANG_NAMES if k not in ("Auto-Detect", src_name)]
    if st.session_state.target_lang not in tgt_opts:
        st.session_state.target_lang = tgt_opts[0]
    tgt_name = st.selectbox("To", tgt_opts,
                            index=tgt_opts.index(st.session_state.target_lang),
                            key="_tgt")

st.session_state.source_lang = src_name
st.session_state.target_lang = tgt_name

src_google = ALL_LANGUAGES.get(src_name,{}).get("google","auto")
tgt_gtts   = ALL_LANGUAGES.get(tgt_name,{}).get("gtts","en")
src_lang_code = ALL_LANGUAGES.get(src_name,{}).get("google","auto")

# ══════════════════════════════════════════════════════════════════
#  تبويبات
# ══════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🎤 Voice","📝 Text","📄 File","📷 Camera","👥 Group Chat"]
)

# ─────────────────────────── Tab 1: Voice ─────────────────────────
with tab1:
    st.markdown("---")
    audio_in = st.audio_input("🎤 سجّل رسالتك", key="voice_mic")
    if audio_in:
        with st.spinner("⏳ التعرف على الكلام..."):
            recognized, err = speech_to_text(audio_in.getvalue(), src_lang_code)
        if recognized:
            st.success(f"✅ {recognized}")
            with st.spinner("⏳ الترجمة..."):
                translated, engine = translate_text(recognized, tgt_name, src_name)
            if translated:
                emotion = analyze_emotion(recognized)
                st.markdown(f"""<div class="card">
                  <span class="lbl">✦ الترجمة</span>
                  <div class="body">{translated}</div>
                  <div class="eng">{engine} &nbsp;·&nbsp; {emotion}</div>
                </div>""", unsafe_allow_html=True)
                st.code(translated, language=None)
                aud = tts(translated, tgt_gtts)
                if aud: st.audio(aud, format="audio/mp3")
                save_translation(recognized, translated, emotion, src_name, tgt_name, engine)
            else:
                st.error(f"❌ فشلت الترجمة: {engine}")
        else:
            st.error(f"❌ فشل التعرف: {err}")

# ─────────────────────────── Tab 2: Text ──────────────────────────
with tab2:
    st.markdown("---")
    input_text = st.text_area("اكتب النص هنا", height=110,
                              placeholder="اكتب أو الصق النص...",
                              value=st.session_state.input_text, key="_text_area")
    st.session_state.input_text = input_text

    if input_text.strip():
        doms = detect_domains(input_text)
        if doms:
            badges = "".join(
                f'<span style="background:rgba(78,203,160,.15);border:1px solid rgba(78,203,160,.3);'
                f'border-radius:20px;padding:2px 8px;font-size:11px;margin-right:4px;">'
                f'{DOMAINS[d]["emoji"]} {DOMAINS[d]["name"]}</span>' for d in doms)
            st.markdown(f"<div style='margin-bottom:.4rem'>🔍 {badges}</div>", unsafe_allow_html=True)

    if st.button("Translate ✦", use_container_width=True, key="_txt_btn"):
        if not input_text.strip():
            st.warning("أدخل نصاً أولاً.")
        else:
            with st.spinner("جاري الترجمة..."):
                translated, engine = translate_text(input_text, tgt_name, src_name)
            if translated:
                emotion = analyze_emotion(input_text)
                st.markdown(f"""<div class="card">
                  <span class="lbl">✦ الترجمة</span>
                  <div class="body">{translated}</div>
                  <div class="eng">{engine} &nbsp;·&nbsp; {emotion}</div>
                </div>""", unsafe_allow_html=True)
                st.code(translated, language=None)
                aud = tts(translated, tgt_gtts)
                if aud: st.audio(aud, format="audio/mp3")
                save_translation(input_text, translated, emotion, src_name, tgt_name, engine)
            else:
                st.error(f"❌ {engine}")

# ─────────────────────────── Tab 3: File ──────────────────────────
with tab3:
    st.markdown("---")
    st.caption("PDF · DOCX · XLSX · TXT")
    up = st.file_uploader("اختر ملفاً", key="_file_up")
    if up:
        st.success(f"✅ {up.name}  ({len(up.getvalue())//1024} KB)")
        if st.button("🔍 استخراج وترجمة", key="_file_btn"):
            with st.spinner("استخراج النص..."):
                extracted, err = extract_file_text(up.getvalue(), up.name)
            if extracted:
                st.code(extracted[:2000] + ("…" if len(extracted)>2000 else ""), language=None)
                st.caption(f"الكلمات: {len(extracted.split())}")
                with st.spinner("الترجمة..."):
                    translated, engine = translate_text(extracted, tgt_name, src_name)
                if translated:
                    emotion = analyze_emotion(extracted[:500])
                    st.markdown(f"""<div class="card">
                      <span class="lbl">✦ الترجمة</span>
                      <div class="body">{translated[:2000]}</div>
                      <div class="eng">{engine}</div>
                    </div>""", unsafe_allow_html=True)
                    save_translation(extracted[:300], translated, emotion, "File", tgt_name, engine)
                    st.download_button("📥 تحميل الترجمة",
                                       data=translated, file_name="translation.txt",
                                       mime="text/plain")
                else:
                    st.error(f"❌ {engine}")
            else:
                st.error(f"❌ {err}")

# ─────────────────────────── Tab 4: Camera ────────────────────────
with tab4:
    st.markdown("---")
    st.caption("ارفع صورة ← يُستخرج النص تلقائياً ← يُترجَم")

    ocr_lang_name = st.selectbox(
        "🔤 لغة النص في الصورة",
        options=LANG_NAMES_NO_AUTO,
        index=LANG_NAMES_NO_AUTO.index("Arabic") if "Arabic" in LANG_NAMES_NO_AUTO else 0,
        key="_ocr_lang",
        help="اختر لغة النص داخل الصورة لتحسين دقة OCR"
    )
    ocr_codes = ALL_LANGUAGES.get(ocr_lang_name, {}).get("ocr", ["en"])

    cam_file = st.file_uploader("اختر صورة", type=["png","jpg","jpeg","webp","bmp"],
                                key="_cam_up")
    if cam_file:
        img_bytes = cam_file.getvalue()
        try:
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            st.image(pil_img, caption=cam_file.name, use_container_width=True)
        except Exception as e:
            st.warning(f"تعذر عرض الصورة: {e}")

        if st.button("🔍 استخراج وترجمة", key="_cam_btn"):
            with st.spinner(f"جاري OCR بلغة {ocr_lang_name}..."):
                extracted, err = extract_image_text(img_bytes, ocr_codes)
            if extracted:
                st.markdown('<div class="sh">النص المستخرج</div>', unsafe_allow_html=True)
                st.code(extracted, language=None)
                st.caption(f"الكلمات: {len(extracted.split())}")
                with st.spinner("الترجمة..."):
                    translated, engine = translate_text(extracted, tgt_name, ocr_lang_name)
                if translated:
                    emotion = analyze_emotion(extracted[:500])
                    st.markdown(f"""<div class="card">
                      <span class="lbl">✦ الترجمة</span>
                      <div class="body">{translated}</div>
                      <div class="eng">{engine} &nbsp;·&nbsp; {emotion}</div>
                    </div>""", unsafe_allow_html=True)
                    save_translation(extracted, translated, emotion,
                                     ocr_lang_name, tgt_name, engine)
                    c1,c2 = st.columns(2)
                    with c1:
                        st.download_button("📥 تحميل النص الأصلي",
                                           data=extracted, file_name="extracted.txt", mime="text/plain")
                    with c2:
                        st.download_button("📥 تحميل الترجمة",
                                           data=translated, file_name="translated.txt", mime="text/plain")
                    aud = tts(translated, tgt_gtts)
                    if aud: st.audio(aud, format="audio/mp3")
                else:
                    st.error(f"❌ الترجمة فشلت: {engine}")
            else:
                st.error(f"❌ OCR فشل: {err}")
                st.info("💡 تلميح: تأكد من وضوح الصورة وصحة اختيار لغة النص")

# ─────────────────────── Tab 5: Group Chat ───────────────────────
with tab5:
    st.markdown("---")
    st.markdown("""
    <div style='background:rgba(78,203,160,.08);border:1px solid rgba(78,203,160,.2);
         border-radius:12px;padding:.8rem 1rem;margin-bottom:.8rem;font-size:13px'>
    <b>كيف يعمل؟</b><br>
    سجّل صوت محادثة بين أشخاص يتحدثون بلغات مختلفة ←
    يكتشف التطبيق <b>تلقائياً</b> لغة كل متحدث ←
    يترجم كل شخص على حدة إلى اللغة الهدف ←
    يعرض كل متحدث في فقاعة محادثة مستقلة مع صوت الترجمة.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sh">🎯 اللغة الهدف للترجمة</div>', unsafe_allow_html=True)
    grp_tgt = st.selectbox("اللغة الهدف",
                           options=LANG_NAMES_NO_AUTO,
                           index=LANG_NAMES_NO_AUTO.index(tgt_name)
                           if tgt_name in LANG_NAMES_NO_AUTO else 0,
                           key="_grp_tgt")

    st.markdown("---")
    st.markdown('<div class="sh">🎤 سجّل المحادثة</div>', unsafe_allow_html=True)
    st.caption("يمكن أن يتحدث أكثر من شخص بأكثر من لغة في نفس التسجيل")

    grp_audio = st.audio_input("ابدأ التسجيل", key="_grp_mic", label_visibility="collapsed")

    if grp_audio:
        if st.button("🚀 تحليل وترجمة المحادثة", use_container_width=True, key="_grp_btn"):
            progress = st.progress(0, text="⏳ جاري التعرف على الكلام وفصل المتحدثين...")
            results, err = group_chat_transcribe(grp_audio.getvalue(), grp_tgt)
            progress.progress(70, text="⏳ الترجمة...")

            if not results:
                progress.empty()
                st.error(f"❌ {err or 'تعذر تحليل الصوت'}")
            else:
                progress.progress(100, text="✅ اكتمل!")
                time.sleep(0.4); progress.empty()

                grp_tgt_gtts = ALL_LANGUAGES.get(grp_tgt,{}).get("gtts","en")
                n = len(results)

                st.markdown(f"""
                <div style='text-align:center;margin:.5rem 0 1rem;font-size:13px;opacity:.7'>
                تم اكتشاف <b>{n}</b> جزء كلامي
                </div>""", unsafe_allow_html=True)

                # ── عرض كل متحدث في فقاعة ─────────────────────────────
                full_transcript = []
                for item in results:
                    spk  = item["speaker_num"]
                    icon = item["speaker_icon"]
                    lang = item["lang_name"]
                    orig = item["original"]
                    trans= item["translated"] or "—"
                    eng  = item["engine"]
                    t0   = item["start"]
                    t1   = item["end"]

                    time_str = f"{t0:.1f}s – {t1:.1f}s" if t1 > 0 else ""

                    st.markdown(f"""
                    <div class="chat-bubble">
                      <div class="cb-header">
                        <span class="cb-icon">{icon}</span>
                        <div class="cb-info">
                          <span class="cb-spk">المتحدث {spk}</span>
                          <span class="cb-lang">{lang} &nbsp;·&nbsp; {time_str}</span>
                        </div>
                      </div>
                      <div class="cb-orig">"{orig}"</div>
                      <div class="cb-trans">{trans}</div>
                      <div class="cb-eng">{eng}</div>
                    </div>""", unsafe_allow_html=True)

                    # صوت الترجمة
                    aud = tts(trans, grp_tgt_gtts)
                    if aud:
                        st.audio(aud, format="audio/mp3")

                    # حفظ في السجل
                    emotion = analyze_emotion(orig)
                    save_translation(orig, trans, emotion,
                                     f"Group/{lang}", grp_tgt, eng)

                    full_transcript.append(
                        f"المتحدث {spk} ({lang}):\n  الأصلي  : {orig}\n  الترجمة : {trans}\n")

                # ── تحميل النص الكامل ──────────────────────────────────
                st.markdown("---")
                full_text = "\n".join(full_transcript)
                st.download_button("📥 تحميل محضر المحادثة",
                                   data=full_text,
                                   file_name="group_chat_transcript.txt",
                                   mime="text/plain",
                                   use_container_width=True,
                                   key="_grp_dl")

# ══════════════════════════════════════════════════════════════════
#  Footer
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div style='text-align:center;padding:1.2rem 0 .5rem;color:rgba(100,130,170,.3);
    font-size:9px;letter-spacing:.12em;text-transform:uppercase'>
HN TRANSLATOR · Groq Whisper + DeepL + Google · Multi-Language Voice Suite
</div>""", unsafe_allow_html=True)
