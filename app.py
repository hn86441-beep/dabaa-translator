import streamlit as st

# ════════════════════════════════════════════════════════════
#  إعدادات الصفحة — يجب أن تكون أول استدعاء لـ Streamlit
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="HN TRANSLATOR",
    page_icon="🌐",
    layout="centered"
)

import requests
import os
import json
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict
from datetime import datetime
import io
import base64
import sqlite3
from PIL import Image
import time

# ────────────────────────────────────────────────────────────
#  مكتبات اختيارية
# ────────────────────────────────────────────────────────────
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from transformers import pipeline as hf_pipeline
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS

# ════════════════════════════════════════════════════════════
#  قاموس اللغات الموسّع
#  deepl  : رمز DeepL  (None = غير مدعوم → يستخدم Google)
#  google : رمز Google / gTTS
# ════════════════════════════════════════════════════════════
ALL_LANGUAGES = {
    "Auto-Detect":   {"google": "auto",  "deepl": None,    "gtts": "en"},
    "Arabic":        {"google": "ar",    "deepl": "AR",    "gtts": "ar"},
    "English":       {"google": "en",    "deepl": "EN-US", "gtts": "en"},
    "Russian":       {"google": "ru",    "deepl": "RU",    "gtts": "ru"},
    "Chinese":       {"google": "zh-CN", "deepl": "ZH",    "gtts": "zh-cn"},
    "German":        {"google": "de",    "deepl": "DE",    "gtts": "de"},
    "Spanish":       {"google": "es",    "deepl": "ES",    "gtts": "es"},
    "French":        {"google": "fr",    "deepl": "FR",    "gtts": "fr"},
    "Portuguese":    {"google": "pt",    "deepl": "PT-PT", "gtts": "pt"},
    "Italian":       {"google": "it",    "deepl": "IT",    "gtts": "it"},
    "Japanese":      {"google": "ja",    "deepl": "JA",    "gtts": "ja"},
    "Korean":        {"google": "ko",    "deepl": "KO",    "gtts": "ko"},
    "Turkish":       {"google": "tr",    "deepl": "TR",    "gtts": "tr"},
    "Dutch":         {"google": "nl",    "deepl": "NL",    "gtts": "nl"},
    "Polish":        {"google": "pl",    "deepl": "PL",    "gtts": "pl"},
    "Ukrainian":     {"google": "uk",    "deepl": "UK",    "gtts": "uk"},
    "Swedish":       {"google": "sv",    "deepl": "SV",    "gtts": "sv"},
    "Danish":        {"google": "da",    "deepl": "DA",    "gtts": "da"},
    "Finnish":       {"google": "fi",    "deepl": "FI",    "gtts": "fi"},
    "Romanian":      {"google": "ro",    "deepl": "RO",    "gtts": "ro"},
    "Hungarian":     {"google": "hu",    "deepl": "HU",    "gtts": "hu"},
    "Czech":         {"google": "cs",    "deepl": "CS",    "gtts": "cs"},
    "Bulgarian":     {"google": "bg",    "deepl": "BG",    "gtts": "bg"},
    "Greek":         {"google": "el",    "deepl": "EL",    "gtts": "el"},
    "Indonesian":    {"google": "id",    "deepl": "ID",    "gtts": "id"},
    "Hindi":         {"google": "hi",    "deepl": None,    "gtts": "hi"},
    "Persian":       {"google": "fa",    "deepl": None,    "gtts": "fa"},
    "Hebrew":        {"google": "iw",    "deepl": None,    "gtts": "iw"},
    "Urdu":          {"google": "ur",    "deepl": None,    "gtts": "ur"},
}

# قائمة مبسّطة للـ selectbox (ما عدا Auto-Detect)
LANG_NAMES        = list(ALL_LANGUAGES.keys())
LANG_NAMES_NO_AUTO = [k for k in LANG_NAMES if k != "Auto-Detect"]

# ════════════════════════════════════════════════════════════
#  قاعدة بيانات SQLite
#  نستخدم /tmp/ لأن Streamlit Cloud يسمح بالكتابة هناك فقط
# ════════════════════════════════════════════════════════════
import tempfile as _tempfile

# مسار آمن يعمل على Streamlit Cloud وأي بيئة أخرى
DB_PATH = os.path.join(_tempfile.gettempdir(), "hn_translations.db")

def _get_conn():
    """فتح اتصال SQLite مع timeout لتجنب تعارض الكتابة."""
    return sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)

def init_db():
    try:
        conn = _get_conn()
        c = conn.cursor()
        # إنشاء الجدول بالشكل الكامل
        c.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                original    TEXT NOT NULL,
                translated  TEXT NOT NULL,
                emotion     TEXT DEFAULT '',
                source_lang TEXT DEFAULT '',
                target_lang TEXT DEFAULT '',
                engine      TEXT DEFAULT '',
                timestamp   TEXT DEFAULT ''
            )
        ''')
        # migration: أضف أي عمود ناقص في قاعدة بيانات قديمة
        existing = {row[1] for row in c.execute("PRAGMA table_info(history)")}
        for col, typ in [("engine", "TEXT DEFAULT ''"),
                         ("emotion", "TEXT DEFAULT ''"),
                         ("source_lang", "TEXT DEFAULT ''"),
                         ("target_lang", "TEXT DEFAULT ''")]:
            if col not in existing:
                c.execute(f"ALTER TABLE history ADD COLUMN {col} {typ}")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        # لا نوقف التطبيق — نستخدم الذاكرة كاحتياطي
        if "db_error" not in st.session_state:
            st.session_state["db_error"] = str(e)
        return False

def save_translation(original, translated, emotion, source_lang, target_lang, engine=""):
    # احتياطي في الذاكرة دائماً
    if "_mem_history" not in st.session_state:
        st.session_state["_mem_history"] = []
    entry = {
        "original": str(original or "")[:500],
        "translated": str(translated or "")[:500],
        "emotion": str(emotion or ""),
        "source_lang": str(source_lang or ""),
        "target_lang": str(target_lang or ""),
        "engine": str(engine or ""),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    st.session_state["_mem_history"].insert(0, entry)
    st.session_state["_mem_history"] = st.session_state["_mem_history"][:200]
    # محاولة الحفظ في SQLite أيضاً
    try:
        conn = _get_conn()
        conn.cursor().execute('''
            INSERT INTO history
                (original, translated, emotion, source_lang, target_lang, engine, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (entry["original"], entry["translated"], entry["emotion"],
              entry["source_lang"], entry["target_lang"], entry["engine"], entry["time"]))
        conn.commit()
        conn.close()
    except Exception:
        pass  # نكتفي بالذاكرة

def get_history(limit=100):
    # حاول قراءة SQLite
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute('''
            SELECT original, translated, emotion, source_lang, target_lang, engine, timestamp
            FROM history ORDER BY id DESC LIMIT ?
        ''', (limit,))
        rows = c.fetchall()
        conn.close()
        if rows:
            return [{"original": r[0], "translated": r[1], "emotion": r[2] or "",
                     "source_lang": r[3] or "", "target_lang": r[4] or "",
                     "engine": r[5] or "", "time": r[6] or ""}
                    for r in rows]
    except Exception:
        pass
    # احتياطي: اعرض من الذاكرة
    return st.session_state.get("_mem_history", [])[:limit]

def clear_history():
    st.session_state["_mem_history"] = []
    try:
        conn = _get_conn()
        conn.cursor().execute('DELETE FROM history')
        conn.commit()
        conn.close()
    except Exception:
        pass

def export_history_json():
    return json.dumps(get_history(limit=1000), ensure_ascii=False, indent=2)

init_db()

# ════════════════════════════════════════════════════════════
#  تحليل المشاعر
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_emotion_classifier():
    if not HF_AVAILABLE:
        return None
    try:
        return hf_pipeline("text-classification",
                           model="tabularisai/multilingual-sentiment-analysis")
    except Exception:
        return None

emotion_classifier = load_emotion_classifier()

def analyze_emotion(text):
    if not text or emotion_classifier is None:
        return "محايد"
    try:
        label = emotion_classifier(text[:512])[0]['label'].upper()
        if "POSITIVE" in label:
            return "😊 فرح"
        elif "NEGATIVE" in label:
            return "😔 حزن"
        return "😐 محايد"
    except Exception:
        return "😐 محايد"

# ════════════════════════════════════════════════════════════
#  دوال الترجمة
# ════════════════════════════════════════════════════════════

def translate_deepl(text: str, deepl_target: str, api_key: str) -> tuple[str | None, str | None]:
    """ترجمة باستخدام DeepL API (مجاني أو مدفوع)."""
    if not api_key or not deepl_target:
        return None, "No DeepL key or unsupported language"
    endpoint = (
        "https://api-free.deepl.com/v2/translate"
        if api_key.endswith(":fx")
        else "https://api.deepl.com/v2/translate"
    )
    try:
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            data={"text": text, "target_lang": deepl_target},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"], None
        return None, f"DeepL {resp.status_code}: {resp.text[:120]}"
    except Exception as e:
        return None, str(e)


def translate_google(text: str, google_target: str, google_source: str = "auto") -> tuple[str | None, str | None]:
    """ترجمة مجانية عبر Google Translate."""
    try:
        src = google_source if google_source else "auto"
        result = GoogleTranslator(source=src, target=google_target).translate(text)
        return result, None
    except Exception as e:
        # احتياطي: MyMemory
        try:
            src2 = "en" if (src == "auto" or not src) else src
            result = MyMemoryTranslator(source=src2, target=google_target).translate(text)
            return result, None
        except Exception as e2:
            return None, f"Google: {e} | MyMemory: {e2}"


def fetch_best_translation(text: str, lang_name: str,
                           source_name: str = "Auto-Detect") -> tuple[str | None, str]:
    """
    يحاول DeepL أولاً (إن كانت اللغة مدعومة والمفتاح موجود).
    يعود إلى Google تلقائياً عند الفشل.
    يُعيد (نص_مترجم, اسم_المحرك).
    """
    info        = ALL_LANGUAGES.get(lang_name, {})
    deepl_code  = info.get("deepl")
    google_code = info.get("google", "en")
    api_key     = st.session_state.get("deepl_api_key", "")

    # 1️⃣ DeepL
    if api_key and deepl_code:
        result, err = translate_deepl(text, deepl_code, api_key)
        if result:
            return result, "DeepL ✦"

    # 2️⃣ Google / MyMemory
    src_google = ALL_LANGUAGES.get(source_name, {}).get("google", "auto")
    result, err = translate_google(text, google_code, src_google)
    if result:
        return result, "Google"

    return None, err or "Translation failed"


def translate_to_multiple(text: str, target_names: list[str],
                          source_name: str = "Auto-Detect") -> dict:
    """ترجمة نص واحد لعدة لغات دفعةً واحدة."""
    results = {}
    for lang in target_names:
        translated, engine = fetch_best_translation(text, lang, source_name)
        results[lang] = {
            "text":   translated,
            "engine": engine,
            "gtts":   ALL_LANGUAGES.get(lang, {}).get("gtts", "en"),
        }
    return results

# ════════════════════════════════════════════════════════════
#  تحويل النص إلى صوت (gTTS)
# ════════════════════════════════════════════════════════════

def generate_audio(text: str, gtts_lang: str = "en") -> io.BytesIO | None:
    if not text or not text.strip():
        return None
    try:
        buf = io.BytesIO()
        gTTS(text=text, lang=gtts_lang, slow=False).write_to_fp(buf)
        buf.seek(0)
        return buf
    except Exception:
        return None

# ════════════════════════════════════════════════════════════
#  استخراج النص من الملفات
# ════════════════════════════════════════════════════════════

def extract_text_from_file(file_bytes: bytes, filename: str) -> tuple[str | None, str | None]:
    ext = os.path.splitext(filename)[1].lower()

    if ext == '.pdf':
        if not PDFPLUMBER_AVAILABLE:
            return None, "مكتبة pdfplumber غير مثبتة"
        try:
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
            return (text.strip(), None) if text.strip() else (None, "لم يتم العثور على نص في ملف PDF")
        except Exception as e:
            return None, str(e)

    elif ext == '.docx':
        if not DOCX_AVAILABLE:
            return None, "مكتبة python-docx غير مثبتة"
        try:
            d = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in d.paragraphs)
            return (text.strip(), None) if text.strip() else (None, "لم يتم العثور على نص في DOCX")
        except Exception as e:
            return None, str(e)

    elif ext in ['.xlsx', '.xls']:
        if not EXCEL_AVAILABLE:
            return None, "مكتبة openpyxl غير مثبتة"
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            parts = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value is not None:
                            parts.append(str(cell.value))
            text = "\n".join(parts)
            return (text.strip(), None) if text.strip() else (None, "لم يتم العثور على نص في Excel")
        except Exception as e:
            return None, str(e)

    elif ext == '.txt':
        for enc in ['utf-8', 'windows-1256', 'latin-1']:
            try:
                text = file_bytes.decode(enc)
                if text.strip():
                    return text.strip(), None
            except Exception:
                continue
        return None, "تعذر قراءة الملف"

    return None, f"نوع الملف غير مدعوم: {ext}"

# ════════════════════════════════════════════════════════════
#  EasyOCR — استخراج النص من الصور
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_easyocr_reader():
    if EASYOCR_AVAILABLE:
        try:
            return easyocr.Reader(['ar', 'en', 'ru'], gpu=False)
        except Exception:
            return None
    return None

easyocr_reader = load_easyocr_reader()

def extract_text_from_image(image_bytes: bytes) -> tuple[str | None, str | None]:
    if easyocr_reader is None:
        return None, "EasyOCR غير متاح"
    try:
        import numpy as np
        img_np = np.array(Image.open(io.BytesIO(image_bytes)))
        result = easyocr_reader.readtext(img_np)
        text = " ".join(item[1] for item in result)
        return (text.strip(), None) if text.strip() else (None, "لم يتم العثور على نص في الصورة")
    except Exception as e:
        return None, str(e)

# ════════════════════════════════════════════════════════════
#  التعرف على الصوت
#  الأولوية:  1 Groq whisper-large-v3-turbo (أفضل جودة، مجاني، 99 لغة)
#             2 Cohere (احتياطي)
#             3 faster-whisper محلي (احتياطي أخير)
# ════════════════════════════════════════════════════════════

_WHISPER_LANG = {
    "auto": None, "ar": "ar", "en": "en", "ru": "ru",
    "zh-CN": "zh", "zh-cn": "zh", "de": "de", "es": "es",
    "fr": "fr", "pt": "pt", "it": "it", "ja": "ja",
    "ko": "ko", "tr": "tr", "nl": "nl", "pl": "pl",
    "uk": "uk", "sv": "sv", "da": "da", "fi": "fi",
    "ro": "ro", "hu": "hu", "cs": "cs", "bg": "bg",
    "el": "el", "id": "id", "hi": "hi", "fa": "fa",
    "iw": "he", "ur": "ur",
}

def _whisper_lang(code):
    if not code or code == "auto":
        return None
    return _WHISPER_LANG.get(code, code[:2])


def speech_to_text_groq(audio_bytes, language_code="auto"):
    """Groq Whisper Large V3 Turbo — مجاني 7200 ثانية/يوم، 99 لغة."""
    api_key = st.session_state.get("groq_api_key", "")
    if not api_key:
        return None, "مفتاح Groq غير موجود"
    try:
        lang = _whisper_lang(language_code)
        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
            "model": (None, "whisper-large-v3-turbo"),
            "response_format": (None, "json"),
        }
        if lang:
            files["language"] = (None, lang)
        resp = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            timeout=30,
        )
        if resp.status_code == 200:
            text = resp.json().get("text", "").strip()
            return (text, None) if text else (None, "لم يُكتشف كلام")
        return None, f"Groq {resp.status_code}: {resp.text[:120]}"
    except Exception as e:
        return None, str(e)


def speech_to_text_cohere(audio_bytes, language_code="en"):
    api_key = st.session_state.get("cohere_api_key", "")
    if not api_key:
        return None, "مفتاح Cohere غير موجود"
    try:
        lang = _whisper_lang(language_code) or "en"
        fields = OrderedDict()
        fields["language"] = lang
        fields["model"]    = "cohere-transcribe-03-2026"
        fields["file"]     = ("audio.wav", audio_bytes, "audio/wav")
        enc = MultipartEncoder(fields=fields)
        resp = requests.post(
            "https://api.cohere.com/v2/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": enc.content_type},
            data=enc,
            timeout=30,
        )
        if resp.status_code == 200:
            text = resp.json().get("text", "").strip()
            return (text, None) if text else (None, "لم يُكتشف كلام")
        return None, f"Cohere {resp.status_code}"
    except Exception as e:
        return None, str(e)


@st.cache_resource(show_spinner=False)
def load_whisper_model():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("small", device="cpu", compute_type="int8")
    except Exception:
        return None

def speech_to_text_whisper_local(audio_bytes, lang=None):
    model = load_whisper_model()
    if not model:
        return None, "Whisper المحلي غير متاح"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            tmp = f.name
        segs, _ = model.transcribe(tmp, language=lang, beam_size=5, vad_filter=True)
        text = " ".join(s.text for s in segs).strip()
        return (text, None) if text else (None, "لم يُكتشف كلام")
    except Exception as e:
        return None, str(e)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def speech_to_text(audio_bytes, language_code="auto"):
    """يجرّب: Groq -> Cohere -> Whisper محلي"""
    wlang  = _whisper_lang(language_code)
    errors = []
    if st.session_state.get("groq_api_key"):
        r, e = speech_to_text_groq(audio_bytes, language_code)
        if r:
            return r, None
        errors.append(f"Groq: {e}")
    if st.session_state.get("cohere_api_key"):
        r, e = speech_to_text_cohere(audio_bytes, language_code)
        if r:
            return r, None
        errors.append(f"Cohere: {e}")
    r, e = speech_to_text_whisper_local(audio_bytes, lang=wlang)
    if r:
        return r, None
    errors.append(f"Whisper: {e}")
    return None, " | ".join(errors)

# ════════════════════════════════════════════════════════════
#  أنماط المجال
# ════════════════════════════════════════════════════════════
DOMAINS = {
    "political":    {"emoji": "🏛️", "name": "Political"},
    "legal":        {"emoji": "⚖️", "name": "Legal"},
    "economic":     {"emoji": "📈", "name": "Economic"},
    "medical":      {"emoji": "🏥", "name": "Medical"},
    "scientific":   {"emoji": "🔬", "name": "Scientific"},
    "engineering":  {"emoji": "🏗️", "name": "Engineering"},
    "military":     {"emoji": "🎖️", "name": "Military"},
    "educational":  {"emoji": "📚", "name": "Educational"},
    "religious":    {"emoji": "🕌", "name": "Religious"},
    "sports":       {"emoji": "⚽", "name": "Sports"},
    "literary":     {"emoji": "📖", "name": "Literary"},
    "it":           {"emoji": "💻", "name": "IT/Tech"},
    "environmental":{"emoji": "🌿", "name": "Environmental"},
    "agricultural": {"emoji": "🌾", "name": "Agricultural"},
    "media":        {"emoji": "📺", "name": "Media"},
    "tourism":      {"emoji": "✈️", "name": "Tourism"},
    "general":      {"emoji": "💬", "name": "General"},
}

DOMAIN_KEYWORDS = {
    "political":    ["minister","government","parliament","political","president","وزير","حكومة","برلمان","سياسة","رئيس"],
    "legal":        ["contract","agreement","legal","court","law","عقد","اتفاق","قانون","محكمة"],
    "economic":     ["economic","financial","investment","cost","budget","اقتصاد","مالية","استثمار","تكلفة","ربح"],
    "medical":      ["doctor","hospital","treatment","disease","patient","طبيب","مستشفى","علاج","مرض","مريض"],
    "scientific":   ["research","study","experiment","theory","data","بحث","دراسة","تجربة","نظرية","بيانات"],
    "engineering":  ["engineering","structural","construction","هندسة","إنشائي","بناء"],
    "military":     ["military","army","defense","war","weapon","جيش","عسكري","دفاع","حرب","سلاح"],
    "educational":  ["school","university","education","teacher","student","مدرسة","جامعة","تعليم","معلم","طالب"],
    "religious":    ["mosque","church","prayer","Quran","religion","مسجد","كنيسة","صلاة","قرآن","دين"],
    "sports":       ["sports","football","stadium","team","player","رياضة","كرة القدم","ملعب","فريق"],
    "literary":     ["literature","story","novel","poetry","writer","أدب","قصة","رواية","شعر","كاتب"],
    "it":           ["programming","computer","software","website","برمجة","حاسوب","برنامج","موقع"],
    "environmental":["environment","pollution","climate","solar","بيئة","تلوث","مناخ","شمسية"],
    "agricultural": ["agriculture","farm","crop","wheat","rice","زراعة","مزرعة","محصول","قمح","أرز"],
    "media":        ["media","journalism","television","news","report","إعلام","صحافة","تلفزيون","خبر"],
    "tourism":      ["tourism","hotel","travel","airport","visa","سياحة","فندق","سفر","مطار","تأشيرة"],
}

def detect_domains(text: str) -> list:
    tl = text.lower()
    scores = {d: sum(tl.count(kw.lower()) for kw in kws)
              for d, kws in DOMAIN_KEYWORDS.items()}
    return sorted((d for d, s in scores.items() if s > 0), key=scores.get, reverse=True)

STYLE_OPTIONS = {
    "Auto-Detect": None,
    **{f"{v['emoji']} {v['name']}": k for k, v in DOMAINS.items()}
}

# ════════════════════════════════════════════════════════════
#  قراءة المفاتيح من Secrets
# ════════════════════════════════════════════════════════════
def _secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default) or default
    except Exception:
        return default

# ════════════════════════════════════════════════════════════
#  Session State
# ════════════════════════════════════════════════════════════
_defaults = {
    "theme":          "dark",
    "deepl_api_key":  _secret("DEEPL_API_KEY"),
    "cohere_api_key": _secret("COHERE_API_KEY"),
    "groq_api_key":   _secret("GROQ_API_KEY"),
    "source_lang":    "Auto-Detect",
    "target_lang":    "Arabic",
    "input_text":     "",
    "translated_text":"",
    "selected_style": "Auto-Detect",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ════════════════════════════════════════════════════════════
#  CSS
# ════════════════════════════════════════════════════════════
def get_css(theme: str) -> str:
    if theme == "light":
        accent = "#2a7a60"
        bg     = "#f5f7fa"
        card   = "rgba(42,122,96,0.06)"
        border = "rgba(42,122,96,0.2)"
        text   = "#1a1a2e"
        sub    = "rgba(42,122,96,0.7)"
        sidebar_bg = "rgba(255,255,255,0.98)"
    else:
        accent = "#4ECBA0"
        bg     = "linear-gradient(135deg,#0a0a1a 0%,#0f1728 40%,#0a1520 100%)"
        card   = "rgba(78,203,160,0.06)"
        border = "rgba(78,203,160,0.2)"
        text   = "#e8f0ff"
        sub    = "rgba(78,203,160,0.7)"
        sidebar_bg = "rgba(10,10,26,0.98)"

    bg_css = f"background:{bg} !important;" if "gradient" not in bg else f"background:{bg} !important;"

    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
    .stApp {{ {bg_css} }}
    .app-header {{ text-align:center; padding:0.8rem 0 0.5rem; }}
    .app-header .brand {{ font-family:'Space Grotesk',sans-serif; font-size:11px; font-weight:600;
        letter-spacing:.3em; color:{accent}; text-transform:uppercase; display:block; margin-bottom:.2rem; opacity:.8; }}
    .app-header h1 {{ font-family:'Space Grotesk',sans-serif; font-size:32px; font-weight:700;
        color:{text}; margin:0; letter-spacing:-.02em; }}
    .app-header h1 .accent {{ color:{accent}; }}
    .app-header .divider {{ width:60px; height:3px;
        background:linear-gradient(90deg,{accent},transparent); margin:.3rem auto 0; border-radius:2px; }}
    .stButton > button {{ background:linear-gradient(135deg,{accent},#2fa87a) !important;
        color:#0a1520 !important; font-weight:600 !important; border:none !important; border-radius:8px !important; }}
    .stButton > button:hover {{ filter:brightness(1.1) !important; }}
    textarea {{ background:{'white' if theme=='light' else '#1a1a2e'} !important;
        color:{text} !important; border:1px solid {border} !important; border-radius:8px !important; }}
    .result-box {{ background:{card}; border:1px solid {border}; border-radius:12px;
        padding:.7rem 1rem; margin-top:.5rem; }}
    .result-box .label {{ font-size:9px; font-weight:700; text-transform:uppercase;
        color:{sub}; letter-spacing:.15em; }}
    .result-box .text {{ font-size:15px; color:{text}; margin-top:.3rem; line-height:1.6; }}
    .result-box .emotion {{ font-size:13px; color:{accent}; font-weight:500; margin-top:6px; }}
    .result-box .engine {{ font-size:9px; color:{sub}; margin-top:4px; opacity:.7; }}
    .section-heading {{ font-size:9px; font-weight:700; text-transform:uppercase;
        color:{sub}; margin:.6rem 0 .3rem; letter-spacing:.1em; }}
    .stSelectbox label {{ color:{sub} !important; }}
    .stSelectbox > div > div {{ background:{'white' if theme=='light' else 'rgba(255,255,255,0.05)'} !important;
        color:{text} !important; border-color:{border} !important; }}
    [data-testid="stSidebar"] {{ background:{sidebar_bg} !important;
        border-right:1px solid {border} !important; }}
    .history-item {{ padding:6px 10px; margin-bottom:4px; border-bottom:1px solid {border}; }}
    .history-item .orig {{ font-size:12px; color:{text}; }}
    .history-item .trans {{ font-size:12px; color:{accent}; }}
    .history-item .eng {{ font-size:9px; color:{sub}; opacity:.6; }}
    div[data-testid="stAudioInput"] > div {{ background:{card}; border:2px solid {border}; border-radius:60px; }}
    div[data-testid="stAudioInput"] button {{ color:{text} !important; }}
    .stCode, code, pre {{ background:{'#f0f0f0' if theme=='light' else 'rgba(0,0,0,0.35)'} !important;
        color:{'#1a1a2e' if theme=='light' else '#a8f0d8'} !important;
        border:1px solid {border} !important; border-radius:8px !important; }}
    hr {{ margin:.5rem 0; border:none; height:1px;
        background:linear-gradient(90deg,transparent,{border},transparent); }}
    .multi-card {{ background:{card}; border:1px solid {border}; border-radius:12px;
        padding:.8rem 1rem; margin-bottom:.6rem; }}
    .multi-card .lang-title {{ font-size:13px; font-weight:700; color:{accent};
        margin-bottom:.4rem; }}
    .multi-card .trans-text {{ font-size:14px; color:{text}; line-height:1.6; }}
    .multi-card .eng-badge {{ display:inline-block; font-size:8px; background:{border};
        color:{sub}; padding:2px 6px; border-radius:10px; margin-top:6px; }}
    button[data-baseweb="tab"] {{
        font-family:'Space Grotesk',sans-serif !important; font-size:13px !important;
        font-weight:600 !important; color:{'#1a1a2e' if theme=='light' else '#b0c4de'} !important;
        background:transparent !important; border:none !important;
        padding:.5rem 1.2rem !important; border-radius:8px 8px 0 0 !important;
        transition:all .3s !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background:{card} !important; color:{accent} !important;
        border-bottom:2px solid {accent} !important;
    }}
    div[data-baseweb="tab-list"] {{
        gap:4px !important; border-bottom:1px solid {border} !important; padding-bottom:0 !important;
    }}
    """

st.markdown(f"<style>{get_css(st.session_state.theme)}</style>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  Header
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <span class="brand">✦ Smart Voice Translator ✦</span>
    <h1>HN <span class="accent">TRANSLATOR</span></h1>
    <div class="divider"></div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  Sidebar — السجل وإعدادات المفاتيح
# ════════════════════════════════════════════════════════════
with st.sidebar:
    if st.button("🌓", help="تبديل المظهر", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

    st.divider()

    with st.expander("🔑 مفاتيح API", expanded=False):
        # ── Groq (STT) ──
        gk = st.text_input(
            "🎤 Groq API Key (للتعرف على الصوت)",
            type="password",
            value=st.session_state.groq_api_key,
            key="groq_input",
            help="احصل على مفتاح مجاني من console.groq.com — أفضل دقة لجميع اللغات",
        )
        if gk != st.session_state.groq_api_key:
            st.session_state.groq_api_key = gk

        # ── DeepL (ترجمة) ──
        dk = st.text_input(
            "🌐 DeepL API Key (للترجمة)",
            type="password",
            value=st.session_state.deepl_api_key,
            key="deepl_input",
        )
        if dk != st.session_state.deepl_api_key:
            st.session_state.deepl_api_key = dk

        # ── Cohere (STT احتياطي) ──
        ck = st.text_input(
            "🔄 Cohere API Key (احتياطي STT)",
            type="password",
            value=st.session_state.cohere_api_key,
            key="cohere_input",
        )
        if ck != st.session_state.cohere_api_key:
            st.session_state.cohere_api_key = ck

        st.divider()
        # حالة المحركات
        if st.session_state.groq_api_key:
            st.success("🎤 Groq نشط — جودة عالية، 99 لغة")
        else:
            st.warning("⚠️ Groq غير نشط — أضف مفتاحاً مجانياً من console.groq.com")
        if st.session_state.deepl_api_key:
            st.success("🌐 DeepL نشط — جودة ترجمة عالية")
        else:
            st.info("ℹ️ DeepL غير نشط — يُستخدم Google مجاناً")

    st.divider()

    history = get_history(limit=100)
    if history:
        col_clr, col_exp = st.columns(2)
        with col_clr:
            if st.button("🗑️ مسح", use_container_width=True):
                clear_history()
                st.rerun()
        with col_exp:
            if st.button("📤 تصدير", use_container_width=True):
                b64 = base64.b64encode(export_history_json().encode()).decode()
                st.markdown(
                    f'<a href="data:application/json;base64,{b64}" download="history.json">📥 تحميل JSON</a>',
                    unsafe_allow_html=True
                )
        for item in history:
            st.markdown(f"""
            <div class="history-item">
                <div class="orig">{item.get('original','')[:60]}</div>
                <div class="trans">{item.get('translated','')[:60]}</div>
                <div class="eng">{item.get('engine','')} · {item.get('target_lang','')} · {item.get('time','')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center;font-size:28px;opacity:.3'>📭</div>",
                    unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  اختيار اللغات والنمط — مشترك بين جميع التبويبات
# ════════════════════════════════════════════════════════════
def swap_languages():
    s, t = st.session_state.source_lang, st.session_state.target_lang
    if s == "Auto-Detect":
        s = "English"
    st.session_state.source_lang = t
    st.session_state.target_lang = s
    st.rerun()

st.markdown('<div class="section-heading">Translation Direction</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([1, 0.18, 1])
with c1:
    src_name = st.selectbox("From", LANG_NAMES,
                            index=LANG_NAMES.index(st.session_state.source_lang)
                            if st.session_state.source_lang in LANG_NAMES else 0,
                            key="src_select")
with c2:
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    if st.button("⇄", use_container_width=True):
        swap_languages()
with c3:
    tgt_opts = [k for k in LANG_NAMES if k != src_name and k != "Auto-Detect"]
    if st.session_state.target_lang not in tgt_opts:
        st.session_state.target_lang = tgt_opts[0]
    tgt_name = st.selectbox("To", tgt_opts,
                            index=tgt_opts.index(st.session_state.target_lang)
                            if st.session_state.target_lang in tgt_opts else 0,
                            key="tgt_select")

st.session_state.source_lang = src_name
st.session_state.target_lang = tgt_name

src_google = ALL_LANGUAGES.get(src_name, {}).get("google", "auto")
tgt_gtts   = ALL_LANGUAGES.get(tgt_name, {}).get("gtts", "en")

st.markdown('<div class="section-heading">Domain Style</div>', unsafe_allow_html=True)
style_list  = list(STYLE_OPTIONS.keys())
style_label = st.selectbox("Style", style_list,
                           index=style_list.index(st.session_state.selected_style)
                           if st.session_state.selected_style in style_list else 0,
                           label_visibility="collapsed", key="style_select")
st.session_state.selected_style = style_label

# ════════════════════════════════════════════════════════════
#  التبويبات
# ════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎤 Voice", "📝 Text", "📄 File", "📷 Camera", "👥 Group"
])

# ──────────────────────────────────────────────────────────
#  Tab 1 — Voice
# ──────────────────────────────────────────────────────────
with tab1:
    st.markdown("---")
    st.markdown('<div class="section-heading">🎤 Voice Input</div>', unsafe_allow_html=True)

    col_mic, col_clr = st.columns([5, 1])
    with col_mic:
        audio_val = st.audio_input("", key="mic_main", label_visibility="collapsed")
    with col_clr:
        if st.session_state.get("mic_main") is not None:
            if st.button("✖", key="clr_main", type="secondary"):
                del st.session_state["mic_main"]
                st.session_state.input_text = ""
                st.rerun()

    if audio_val is not None:
        with st.spinner("⏳ جاري التعرف على الكلام..."):
            recognized, err = speech_to_text(audio_val.getvalue(), src_google)

        if recognized:
            st.success(f"✅ {recognized}")
            with st.spinner("⏳ جاري الترجمة..."):
                translated, engine = fetch_best_translation(recognized, tgt_name, src_name)

            if translated:
                emotion = analyze_emotion(recognized)
                st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="result-box">
                    <span class="label">✦ Translation</span>
                    <div class="text">{translated}</div>
                    <div class="emotion">{emotion}</div>
                    <div class="engine">{engine}</div>
                </div>""", unsafe_allow_html=True)
                st.code(translated, language=None)
                audio_out = generate_audio(translated, tgt_gtts)
                if audio_out:
                    st.audio(audio_out, format="audio/mp3")
                save_translation(recognized, translated, emotion, src_name, tgt_name, engine)
            else:
                st.error(f"❌ الترجمة فشلت: {engine}")
        else:
            st.error(f"❌ التعرف فشل: {err}")

# ──────────────────────────────────────────────────────────
#  Tab 2 — Text
# ──────────────────────────────────────────────────────────
with tab2:
    st.markdown("---")
    st.markdown('<div class="section-heading">📝 Text Input</div>', unsafe_allow_html=True)

    input_text = st.text_area("", height=100,
                              placeholder="اكتب أو الصق النص هنا...",
                              value=st.session_state.input_text,
                              key="text_input_area")
    st.session_state.input_text = input_text

    if input_text.strip():
        detected = detect_domains(input_text)
        if detected:
            badges = "".join(
                f'<span style="background:rgba(78,203,160,0.15);border:1px solid rgba(78,203,160,0.3);'
                f'border-radius:20px;padding:2px 8px;font-size:11px;margin-right:4px;">'
                f'{DOMAINS[d]["emoji"]} {DOMAINS[d]["name"]}</span>'
                for d in detected[:3]
            )
            st.markdown(f'<div style="margin-bottom:.5rem">🔍 {badges}</div>',
                        unsafe_allow_html=True)

    if st.button("Translate ✦", use_container_width=True, key="translate_btn"):
        if not input_text.strip():
            st.warning("الرجاء إدخال نص للترجمة.")
        else:
            with st.spinner("جاري الترجمة..."):
                translated, engine = fetch_best_translation(input_text, tgt_name, src_name)
            if translated:
                emotion = analyze_emotion(input_text)
                st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="result-box">
                    <span class="label">✦ Translation</span>
                    <div class="text">{translated}</div>
                    <div class="emotion">{emotion}</div>
                    <div class="engine">{engine}</div>
                </div>""", unsafe_allow_html=True)
                st.code(translated, language=None)
                audio_out = generate_audio(translated, tgt_gtts)
                if audio_out:
                    st.audio(audio_out, format="audio/mp3")
                save_translation(input_text, translated, emotion, src_name, tgt_name, engine)
            else:
                st.error(f"❌ {engine}")

# ──────────────────────────────────────────────────────────
#  Tab 3 — File
# ──────────────────────────────────────────────────────────
with tab3:
    st.markdown("---")
    st.markdown('<div class="section-heading">📄 File Translation</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("اختر ملف (PDF, DOCX, XLSX, TXT)", key="file_uploader")

    if uploaded_file:
        st.success(f"✅ {uploaded_file.name} ({len(uploaded_file.getvalue())//1024} KB)")
        if st.button("🔍 استخراج النص وترجمته", key="file_btn"):
            with st.spinner("جاري استخراج النص..."):
                extracted, err = extract_text_from_file(uploaded_file.getvalue(), uploaded_file.name)
            if extracted:
                st.markdown('<div class="section-heading">Extracted Text</div>', unsafe_allow_html=True)
                st.code(extracted[:2000] + ("..." if len(extracted) > 2000 else ""), language=None)
                st.caption(f"عدد الكلمات: {len(extracted.split())}")
                with st.spinner("جاري الترجمة..."):
                    translated, engine = fetch_best_translation(extracted, tgt_name, src_name)
                if translated:
                    emotion = analyze_emotion(extracted)
                    st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="result-box">
                        <span class="label">✦ Translation</span>
                        <div class="text">{translated}</div>
                        <div class="engine">{engine}</div>
                    </div>""", unsafe_allow_html=True)
                    save_translation(extracted[:300], translated, emotion, "File", tgt_name, engine)
                    st.download_button("📥 تحميل الترجمة (TXT)", data=translated,
                                       file_name="translation.txt", mime="text/plain")
                else:
                    st.error(f"❌ فشلت الترجمة: {engine}")
            else:
                st.error(f"❌ فشل الاستخراج: {err}")

# ──────────────────────────────────────────────────────────
#  Tab 4 — Camera / Image OCR
# ──────────────────────────────────────────────────────────
with tab4:
    st.markdown("---")
    st.markdown('<div class="section-heading">📷 Camera / Image Translation</div>', unsafe_allow_html=True)
    st.caption("ارفع صورة وسيتم استخراج النص وترجمته")

    uploaded_img = st.file_uploader("اختر صورة", type=["png","jpg","jpeg","webp"], key="cam_uploader")
    if uploaded_img:
        img_bytes = uploaded_img.getvalue()
        st.image(Image.open(io.BytesIO(img_bytes)), caption="الصورة المرفوعة", use_container_width=True)
        if st.button("🔍 استخراج وترجمة", key="cam_btn"):
            with st.spinner("جاري استخراج النص..."):
                extracted, err = extract_text_from_image(img_bytes)
            if extracted:
                st.code(extracted, language=None)
                with st.spinner("جاري الترجمة..."):
                    translated, engine = fetch_best_translation(extracted, tgt_name, src_name)
                if translated:
                    emotion = analyze_emotion(extracted)
                    st.markdown(f"""
                    <div class="result-box">
                        <span class="label">✦ Translation</span>
                        <div class="text">{translated}</div>
                        <div class="engine">{engine}</div>
                    </div>""", unsafe_allow_html=True)
                    save_translation(extracted, translated, emotion, "Camera", tgt_name, engine)
                    st.download_button("📥 تحميل الترجمة", data=translated,
                                       file_name="img_translation.txt", mime="text/plain")
            else:
                st.error(f"❌ {err}")

# ──────────────────────────────────────────────────────────
#  Tab 5 — Group Chat (Multi-Language Live)
# ──────────────────────────────────────────────────────────
with tab5:
    st.markdown("---")
    st.markdown('<div class="section-heading">👥 محادثة جماعية — ترجمة متعددة اللغات في وقت واحد</div>',
                unsafe_allow_html=True)
    st.caption(
        "سجّل مرة واحدة ← يُحوَّل الكلام إلى نص ← يُترجَم لجميع اللغات التي تختارها دفعةً واحدة"
    )

    # ── اختيار لغة المتحدث ──
    grp_src = st.selectbox(
        "🗣️ لغة المتحدث (المصدر)",
        ["Auto-Detect"] + LANG_NAMES_NO_AUTO,
        key="grp_src_lang"
    )

    # ── اختيار اللغات الهدف (متعدد) ──
    st.markdown('<div class="section-heading">🌍 اللغات الهدف (اختر أكثر من لغة)</div>',
                unsafe_allow_html=True)

    # أزرار سريعة لاختيار مجموعات شائعة
    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1:
        if st.button("🌏 آسيا", key="q_asia", use_container_width=True):
            st.session_state["grp_targets_state"] = ["Arabic","Chinese","Japanese","Korean"]
    with qc2:
        if st.button("🌍 أوروبا", key="q_euro", use_container_width=True):
            st.session_state["grp_targets_state"] = ["English","French","German","Spanish","Italian"]
    with qc3:
        if st.button("🌐 العالمية", key="q_world", use_container_width=True):
            st.session_state["grp_targets_state"] = ["Arabic","English","Russian","Chinese","French","Spanish"]
    with qc4:
        if st.button("🔄 مسح", key="q_clear", use_container_width=True):
            st.session_state["grp_targets_state"] = []

    if "grp_targets_state" not in st.session_state:
        st.session_state["grp_targets_state"] = ["Arabic", "English"]

    grp_targets = st.multiselect(
        "اختر اللغات الهدف",
        options=LANG_NAMES_NO_AUTO,
        default=st.session_state["grp_targets_state"],
        key="grp_targets_multi",
        label_visibility="collapsed"
    )
    # مزامنة الحالة
    st.session_state["grp_targets_state"] = grp_targets

    if not grp_targets:
        st.info("👆 اختر لغة هدف واحدة على الأقل.")
    else:
        st.markdown(
            f'<div style="font-size:12px;opacity:.6;margin-bottom:.5rem">'
            f'سيتم الترجمة إلى {len(grp_targets)} لغة: '
            f'{" · ".join(grp_targets)}</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ── تسجيل الصوت ──
    grp_audio = st.audio_input("🎤 اضغط لتبدأ التسجيل", key="grp_audio_input",
                               label_visibility="visible")

    if grp_audio and grp_targets:
        if st.button("🚀 ترجمة لجميع اللغات المختارة", use_container_width=True, key="grp_translate_btn"):

            audio_bytes_grp = grp_audio.getvalue()
            src_g = ALL_LANGUAGES.get(grp_src, {}).get("google", "auto")

            with st.spinner("⏳ جاري التعرف على الكلام..."):
                recognized, stt_err = speech_to_text(audio_bytes_grp, src_g)

            if not recognized:
                st.error(f"❌ فشل التعرف على الكلام: {stt_err}")
            else:
                st.success(f"✅ النص المعرَّف: **{recognized}**")
                emotion = analyze_emotion(recognized)
                st.markdown(f"**المشاعر:** {emotion}")
                st.markdown("---")
                st.markdown('<div class="section-heading">🌍 الترجمات</div>', unsafe_allow_html=True)

                # ── ترجمة موازية لجميع اللغات ──
                with st.spinner("⏳ جاري الترجمة لجميع اللغات..."):
                    all_results = translate_to_multiple(recognized, grp_targets, grp_src)

                # عرض النتائج في شبكة (3 أعمدة كحد أقصى)
                n_cols = min(len(grp_targets), 3)
                cols   = st.columns(n_cols)

                for i, lang_name in enumerate(grp_targets):
                    info      = all_results[lang_name]
                    trans_txt = info["text"]
                    engine    = info["engine"]
                    gtts_lc   = info["gtts"]

                    with cols[i % n_cols]:
                        if trans_txt:
                            st.markdown(f"""
                            <div class="multi-card">
                                <div class="lang-title">🌐 {lang_name}</div>
                                <div class="trans-text">{trans_txt}</div>
                                <span class="eng-badge">{engine}</span>
                            </div>""", unsafe_allow_html=True)

                            # نسخ النص
                            st.code(trans_txt, language=None)

                            # صوت لكل لغة
                            aud = generate_audio(trans_txt, gtts_lc)
                            if aud:
                                st.audio(aud, format="audio/mp3")

                            # حفظ في السجل
                            save_translation(recognized, trans_txt, emotion,
                                             grp_src, lang_name, engine)
                        else:
                            st.error(f"❌ {lang_name}: {engine}")

                # ── زر تحميل كل الترجمات ──
                all_text = f"النص الأصلي ({grp_src}):\n{recognized}\n\n"
                all_text += "\n\n".join(
                    f"{'='*40}\n{lang} [{all_results[lang]['engine']}]:\n{all_results[lang]['text'] or 'فشلت'}"
                    for lang in grp_targets
                )
                st.download_button(
                    "📥 تحميل جميع الترجمات (TXT)",
                    data=all_text,
                    file_name="group_translations.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="grp_download"
                )

    elif grp_audio and not grp_targets:
        st.warning("⚠️ اختر لغة هدف واحدة على الأقل قبل الترجمة.")

# ════════════════════════════════════════════════════════════
#  Footer
# ════════════════════════════════════════════════════════════
st.markdown("""
<div style="text-align:center;padding:1rem 0;color:rgba(100,130,170,0.3);
    font-size:9px;letter-spacing:.12em;text-transform:uppercase;">
    HN TRANSLATOR · DeepL + Google · Voice Translation Suite
</div>
""", unsafe_allow_html=True)
