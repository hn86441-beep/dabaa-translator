import streamlit as st
import requests
import os
import json
from pathlib import Path
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict
from transformers import pipeline
from datetime import datetime
import io
import base64
import sqlite3
from PIL import Image
import time
import numpy as np

# ════════════════════════════════════════════════════════════
#  استيراد EasyOCR للصور (للملفات فقط)
# ════════════════════════════════════════════════════════════
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# ════════════════════════════════════════════════════════════
#  استيراد مكتبات الملفات (PDF, DOCX, Excel)
# ════════════════════════════════════════════════════════════
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

# ════════════════════════════════════════════════════════════
#  استيراد أدوات الترجمة والصوت
# ════════════════════════════════════════════════════════════
from deep_translator import GoogleTranslator
from gtts import gTTS

# ════════════════════════════════════════════════════════════
#  قاعدة بيانات SQLite
# ════════════════════════════════════════════════════════════
DB_PATH = "translations.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original TEXT NOT NULL,
            translated TEXT NOT NULL,
            emotion TEXT,
            source_lang TEXT,
            target_lang TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_translation(original, translated, emotion, source_lang, target_lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO history (original, translated, emotion, source_lang, target_lang, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (original, translated, emotion, source_lang, target_lang, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_history(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT original, translated, emotion, source_lang, target_lang, timestamp
        FROM history
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "original": row[0],
            "translated": row[1],
            "emotion": row[2],
            "source_lang": row[3],
            "target_lang": row[4],
            "time": row[5]
        }
        for row in rows
    ]

def clear_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM history')
    conn.commit()
    conn.close()

def export_history_json():
    history = get_history(limit=1000)
    return json.dumps(history, ensure_ascii=False, indent=2)

init_db()

# ════════════════════════════════════════════════════════════
#  تحليل المشاعر (دالة أصلية 100%، لم تُمس)
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_emotion_classifier():
    try:
        return pipeline("text-classification", model="nlptown/bert-base-multilingual-uncased-sentiment")
    except Exception as e:
        st.warning(f"⚠️ فشل تحميل النموذج: {e}")
        return None

emotion_classifier = load_emotion_classifier()

def analyze_emotion(text):
    if not text or emotion_classifier is None:
        return "محايد"
    try:
        result = emotion_classifier(text[:512])[0]
        label = int(result['label'].split()[0])
        if label >= 4:
            return "فرح"
        elif label <= 2:
            return "حزن"
        else:
            return "محايد"
    except Exception:
        return "محايد"

# ════════════════════════════════════════════════════════════
#  تحويل النص إلى صوت (gTTS)
# ════════════════════════════════════════════════════════════
def get_tts_lang(lang_code):
    lang_map = {
        "ar": "ar", "en": "en", "ru": "ru", "zh": "zh-cn",
        "de": "de", "es": "es", "pt": "pt", "ko": "ko",
    }
    return lang_map.get(lang_code, "en")

def generate_audio(text, lang_code="en"):
    if not text or not text.strip():
        return None
    try:
        tts_lang = get_tts_lang(lang_code)
        tts = gTTS(text=text, lang=tts_lang, slow=False)
        audio_bytes = io.BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        return audio_bytes
    except Exception:
        return None

# ════════════════════════════════════════════════════════════
#  استخراج النص من الملفات
# ════════════════════════════════════════════════════════════
def extract_text_from_file(file_bytes, filename):
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == '.pdf':
        if not PDFPLUMBER_AVAILABLE:
            return None, "مكتبة pdfplumber غير مثبتة"
        try:
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text.strip(), None
            return None, "لم يتم العثور على نص في ملف PDF"
        except Exception as e:
            return None, str(e)
    
    elif ext == '.docx':
        if not DOCX_AVAILABLE:
            return None, "مكتبة python-docx غير مثبتة"
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            if text.strip():
                return text.strip(), None
            return None, "لم يتم العثور على نص في ملف DOCX"
        except Exception as e:
            return None, str(e)
    
    elif ext in ['.xlsx', '.xls']:
        if not EXCEL_AVAILABLE:
            return None, "مكتبة openpyxl غير مثبتة"
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            all_text = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value is not None:
                            all_text.append(str(cell.value))
            text = "\n".join(all_text)
            if text.strip():
                return text.strip(), None
            return None, "لم يتم العثور على نص في ملف Excel"
        except Exception as e:
            return None, str(e)
    
    elif ext == '.txt':
        try:
            text = file_bytes.decode('utf-8')
            if text.strip():
                return text.strip(), None
            return None, "الملف فارغ"
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode('windows-1256')
                if text.strip():
                    return text.strip(), None
            except:
                pass
            return None, "تعذر قراءة الملف، تأكد من أنه نص عادي"
    
    else:
        return None, f"نوع الملف غير مدعوم: {ext}"

# ════════════════════════════════════════════════════════════
#  دوال الترجمة (DeepL أساسي + Google احتياطي)
# ════════════════════════════════════════════════════════════
def translate_deepl(text, target_lang):
    """استدعاء DeepL للترجمة. تُرجع (الترجمة, None) أو (None, رسالة خطأ)."""
    if not st.session_state.get("deepl_api_key"):
        return None, "No API key"
    tl = target_lang.upper()
    endpoint = "https://api-free.deepl.com/v2/translate" if st.session_state.deepl_api_key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    try:
        resp = requests.post(endpoint, headers={"Authorization": f"DeepL-Auth-Key {st.session_state.deepl_api_key}"}, data={"text": text, "target_lang": tl}, timeout=15)
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"], None
        return None, f"DeepL error {resp.status_code}"
    except Exception as e:
        return None, f"Error: {str(e)}"

def translate_text(text, target_lang):
    """
    الترجمة الذكية:
    1. DeepL (إن وُجد المفتاح).
       إذا فشل، ننتقل تلقائياً إلى Google.
    2. Google Translator (يدعم العربية وجميع اللغات).
    3. LibreTranslate (احتياطي إن وُجد رابطه).
    """
    # 1. محاولة DeepL أولاً
    if st.session_state.get("deepl_api_key"):
        tr, err = translate_deepl(text, target_lang)
        if tr:
            return tr, None
    # 2. Google Translator
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text), None
    except Exception as e1:
        # 3. LibreTranslate احتياطي
        libre_url = os.environ.get("LIBRETRANSLATE_URL", st.secrets.get("LIBRETRANSLATE_URL", ""))
        if libre_url:
            try:
                resp = requests.post(f"{libre_url}/translate",
                                     json={"q": text, "source": "auto", "target": target_lang}, timeout=10)
                if resp.status_code == 200:
                    return resp.json()["translatedText"], None
                else:
                    return None, f"Google: {e1} | LibreTranslate: {resp.status_code}"
            except Exception as e2:
                return None, f"Google: {e1} | LibreTranslate: {e2}"
        return None, f"Google Translator error: {e1}"

# ════════════════════════════════════════════════════════════
#  دوال التعرف على الصوت (Cohere أساسي)
# ════════════════════════════════════════════════════════════
def speech_to_text_cohere(audio_bytes, language_code="auto"):
    """تحويل الصوت إلى نص باستخدام Cohere."""
    if not st.session_state.get("cohere_api_key"):
        return None, "API key missing"
    try:
        fields = OrderedDict()
        lang = "en" if language_code == "auto" or language_code is None else language_code
        fields['language'] = lang
        fields['model'] = 'cohere-transcribe-03-2026'
        fields['file'] = ('audio.wav', audio_bytes, 'audio/wav')
        encoder = MultipartEncoder(fields=fields)
        response = requests.post(
            "https://api.cohere.com/v2/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {st.session_state.cohere_api_key}",
                "Content-Type": encoder.content_type
            },
            data=encoder,
            timeout=30
        )
        if response.status_code == 200:
            text = response.json().get("text", "").strip()
            if text:
                return text, "Cohere"
            else:
                return None, "No speech detected"
        return None, f"Cohere error {response.status_code}"
    except Exception as e:
        return None, f"Error: {str(e)}"

def transcribe_audio_single(audio_bytes, language=None):
    """نسخ سريع لمقطع صوتي باستخدام Cohere."""
    lang_param = "en" if language == "auto" or language is None else language
    return speech_to_text_cohere(audio_bytes, lang_param)

# ════════════════════════════════════════════════════════════
#  إعدادات الصفحة
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="HN TRANSLATOR",
    page_icon="🌐",
    layout="centered"
)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# ════════════════════════════════════════════════════════════
#  CSS (مختصر لكن كامل)
# ════════════════════════════════════════════════════════════
def get_css(theme):
    if theme == "light":
        return """
        .stApp { background: #f5f7fa !important; }
        .app-header { text-align: center; padding: 0.8rem 0 0.5rem 0; position: relative; }
        .app-header .brand { font-family: 'Space Grotesk', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.3em; color: #2a7a60; text-transform: uppercase; display: block; margin-bottom: 0.2rem; opacity: 0.8; }
        .app-header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 32px; font-weight: 700; color: #1a1a2e; margin: 0; letter-spacing: -0.02em; }
        .app-header h1 .accent { color: #2a7a60; }
        .app-header .divider { width: 60px; height: 3px; background: linear-gradient(90deg, #2a7a60, transparent); margin: 0.3rem auto 0; border-radius: 2px; }
        .stButton > button { background: #2a7a60 !important; color: white !important; }
        .stButton > button:hover { background: #1a5a48 !important; }
        textarea { background: white !important; color: #1a1a2e !important; border: 1px solid #ccc !important; }
        .result-box { background: rgba(42,122,96,0.06); border: 1px solid rgba(42,122,96,0.2); border-radius: 12px; padding: 0.5rem 0.8rem; margin-top: 0.4rem; }
        .result-box .label { font-size: 8px; font-weight: 700; text-transform: uppercase; color: rgba(42,122,96,0.7); letter-spacing: 0.15em; }
        .result-box .text { font-size: 14px; color: #1a1a2e; }
        .result-box .emotion { font-size: 13px; color: #2a7a60; font-weight: 500; margin-top: 4px; }
        .stSelectbox > div > div { background: white !important; color: #1a1a2e !important; border-color: #ccc !important; }
        .stSelectbox label { color: #2a7a60 !important; }
        [data-testid="stSidebar"] { background: rgba(255,255,255,0.98) !important; border-right: 1px solid #ddd !important; }
        .history-item { padding: 6px 10px; margin-bottom: 4px; border-bottom: 1px solid rgba(0,0,0,0.05); }
        .history-item .original { font-size: 12px; color: #1a1a2e; }
        .history-item .translated { font-size: 12px; color: #2a7a60; }
        div[data-testid="stAudioInput"] > div { background: rgba(42,122,96,0.08); border: 2px solid rgba(42,122,96,0.3); border-radius: 60px; }
        div[data-testid="stAudioInput"] button { color: #1a1a2e !important; }
        .stCode, code, pre { background: #f0f0f0 !important; color: #1a1a2e !important; border: 1px solid #ddd !important; border-radius: 8px !important; }
        .section-heading { font-size: 9px; font-weight: 700; text-transform: uppercase; color: #2a7a60; margin: 0.6rem 0 0.3rem; }
        hr { margin: 0.5rem 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(42,122,96,0.2), transparent); }
        .chat-bubble {
            margin: 10px 0;
            border-radius: 15px;
            padding: 12px;
            background: rgba(42,122,96,0.05);
            border-left: 5px solid #2a7a60;
        }
        .chat-bubble .speaker {
            font-weight: bold;
            margin-bottom: 5px;
            color: #2a7a60;
        }
        .chat-bubble .original { color: #333; font-size: 14px; }
        .chat-bubble .translated { color: #1a5a48; font-size: 14px; margin-top: 5px; }
        """
    else:
        return """
        .stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0f1728 40%, #0a1520 100%) !important; }
        .app-header { text-align: center; padding: 0.8rem 0 0.5rem 0; position: relative; }
        .app-header .brand { font-family: 'Space Grotesk', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.3em; color: #4ECBA0; text-transform: uppercase; display: block; margin-bottom: 0.2rem; opacity: 0.8; }
        .app-header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 32px; font-weight: 700; color: #f0f4ff; margin: 0; letter-spacing: -0.02em; }
        .app-header h1 .accent { color: #4ECBA0; }
        .app-header .divider { width: 60px; height: 3px; background: linear-gradient(90deg, #4ECBA0, transparent); margin: 0.3rem auto 0; border-radius: 2px; }
        .stButton > button { background: linear-gradient(135deg, #4ECBA0 0%, #2fa87a 100%) !important; color: #0a1520 !important; }
        .stButton > button:hover { background: linear-gradient(135deg, #5ed9b0 0%, #3dbf8a 100%) !important; }
        textarea { background: #1a1a2e !important; color: #f0f4ff !important; border: 1px solid rgba(255,255,255,0.15) !important; }
        .result-box { background: rgba(78,203,160,0.06); border: 1px solid rgba(78,203,160,0.2); border-radius: 12px; padding: 0.5rem 0.8rem; margin-top: 0.4rem; }
        .result-box .label { font-size: 8px; font-weight: 700; text-transform: uppercase; color: rgba(78,203,160,0.7); letter-spacing: 0.15em; }
        .result-box .text { font-size: 14px; color: #e8f0ff; }
        .result-box .emotion { font-size: 13px; color: #4ECBA0; font-weight: 500; margin-top: 4px; }
        .stSelectbox > div > div { background: rgba(255,255,255,0.05) !important; color: #e8f0ff !important; border-color: rgba(255,255,255,0.12) !important; }
        .stSelectbox label { color: rgba(78,203,160,0.75) !important; }
        [data-testid="stSidebar"] { background: rgba(10,10,26,0.98) !important; border-right: 1px solid rgba(78,203,160,0.1) !important; }
        .history-item { padding: 6px 10px; margin-bottom: 4px; border-bottom: 1px solid rgba(78,203,160,0.1); }
        .history-item .original { font-size: 12px; color: #e8f0ff; }
        .history-item .translated { font-size: 12px; color: #4ECBA0; }
        div[data-testid="stAudioInput"] > div { background: rgba(78,203,160,0.08); border: 2px solid rgba(78,203,160,0.3); border-radius: 60px; }
        div[data-testid="stAudioInput"] button { color: #e8f0ff !important; }
        .stCode, code, pre { background: rgba(0,0,0,0.35) !important; color: #a8f0d8 !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 8px !important; }
        .section-heading { font-size: 9px; font-weight: 700; text-transform: uppercase; color: rgba(150,185,230,0.5); margin: 0.6rem 0 0.3rem; }
        hr { margin: 0.5rem 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(78,203,160,0.2), transparent); }
        .chat-bubble {
            margin: 10px 0;
            border-radius: 15px;
            padding: 12px;
            background: rgba(255,255,255,0.05);
            border-left: 5px solid #4ECBA0;
        }
        .chat-bubble .speaker {
            font-weight: bold;
            margin-bottom: 5px;
            color: #4ECBA0;
        }
        .chat-bubble .original { color: #ccc; font-size: 14px; }
        .chat-bubble .translated { color: #a8f0d8; font-size: 14px; margin-top: 5px; }
        """

st.markdown(f"<style>{get_css(st.session_state.theme)}</style>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  العنوان
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <span class="brand">✦ Smart Voice Translator ✦</span>
    <h1>HN <span class="accent">TRANSLATOR</span></h1>
    <div class="divider"></div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  الشريط الجانبي
# ════════════════════════════════════════════════════════════
with st.sidebar:
    if st.button("🌓", help="تبديل المظهر", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()
    
    st.divider()
    
    history = get_history(limit=100)
    if history:
        if st.button("🗑️", help="مسح الكل", use_container_width=True):
            clear_history()
            st.rerun()
        for item in history:
            st.markdown(f"""
            <div class="history-item">
                <div class="original">{item.get('original', '')}</div>
                <div class="translated">{item.get('translated', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("📤", help="تصدير السجل (JSON)", use_container_width=True):
            json_str = export_history_json()
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="translation_history.json">📥 تحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; color: rgba(150,175,220,0.3); font-size: 30px;'>📭</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  الإعدادات الأساسية
# ════════════════════════════════════════════════════════════
languages_dict = {
    "Auto-Detect": "auto",
    "Arabic": "ar",
    "English": "en",
    "Russian": "ru",
    "Chinese": "zh",
    "German": "de",
    "Spanish": "es",
    "Portuguese": "pt",
    "Korean": "ko"
}

DOMAINS = {
    "political":  {"emoji": "🏛️", "name_en": "Political"},
    "legal":      {"emoji": "⚖️", "name_en": "Legal"},
    "economic":   {"emoji": "📈", "name_en": "Economic"},
    "medical":    {"emoji": "🏥", "name_en": "Medical"},
    "scientific": {"emoji": "🔬", "name_en": "Scientific"},
    "engineering":{"emoji": "🏗️", "name_en": "Engineering"},
    "military":   {"emoji": "🎖️", "name_en": "Military"},
    "educational":{"emoji": "📚", "name_en": "Educational"},
    "religious":  {"emoji": "🕌", "name_en": "Religious"},
    "sports":     {"emoji": "⚽", "name_en": "Sports"},
    "literary":   {"emoji": "📖", "name_en": "Literary"},
    "it":         {"emoji": "💻", "name_en": "IT / Tech"},
    "environmental":{"emoji": "🌿", "name_en": "Environmental"},
    "agricultural":{"emoji": "🌾", "name_en": "Agricultural"},
    "media":      {"emoji": "📺", "name_en": "Media"},
    "tourism":    {"emoji": "✈️", "name_en": "Tourism"},
    "general":    {"emoji": "💬", "name_en": "General"},
}

STYLE_OPTIONS = {
    "Auto-Detect": None,
    "🏛️ Political": "political",
    "⚖️ Legal": "legal",
    "📈 Economic": "economic",
    "🏥 Medical": "medical",
    "🔬 Scientific": "scientific",
    "🏗️ Engineering": "engineering",
    "🎖️ Military": "military",
    "📚 Educational": "educational",
    "🕌 Religious": "religious",
    "⚽ Sports": "sports",
    "📖 Literary": "literary",
    "💻 IT / Tech": "it",
    "🌿 Environmental": "environmental",
    "🌾 Agricultural": "agricultural",
    "📺 Media": "media",
    "✈️ Tourism": "tourism",
    "💬 General": "general",
}

DOMAIN_KEYWORDS = {
    "political": ["minister", "government", "parliament", "political", "president", "وزير", "حكومة", "برلمان", "سياسة", "رئيس"],
    "legal": ["contract", "agreement", "legal", "court", "law", "عقد", "اتفاق", "قانون", "محكمة"],
    "economic": ["economic", "financial", "investment", "cost", "budget", "ربح", "اقتصاد", "مالية", "استثمار", "تكلفة"],
    "medical": ["doctor", "hospital", "treatment", "disease", "patient", "طبيب", "مستشفى", "علاج", "مرض", "مريض"],
    "scientific": ["research", "study", "experiment", "theory", "data", "بحث", "دراسة", "تجربة", "نظرية", "بيانات"],
    "engineering": ["engineering", "structural", "construction", "هندسة", "إنشائي", "بناء"],
    "military": ["military", "army", "defense", "war", "weapon", "جيش", "عسكري", "دفاع", "حرب", "سلاح"],
    "educational": ["school", "university", "education", "teacher", "student", "مدرسة", "جامعة", "تعليم", "معلم", "طالب"],
    "religious": ["mosque", "church", "prayer", "Quran", "religion", "مسجد", "كنيسة", "صلاة", "قرآن", "دين"],
    "sports": ["sports", "football", "stadium", "team", "player", "رياضة", "كرة القدم", "ملعب", "فريق"],
    "literary": ["literature", "story", "novel", "poetry", "writer", "أدب", "قصة", "رواية", "شعر", "كاتب"],
    "it": ["programming", "computer", "software", "website", "برمجة", "حاسوب", "برنامج", "موقع"],
    "environmental": ["environment", "pollution", "climate", "solar", "wind", "بيئة", "تلوث", "مناخ", "شمسية", "رياح"],
    "agricultural": ["agriculture", "farm", "crop", "wheat", "rice", "زراعة", "مزرعة", "محصول", "قمح", "أرز"],
    "media": ["media", "journalism", "television", "news", "report", "إعلام", "صحافة", "تلفزيون", "خبر", "تقرير"],
    "tourism": ["tourism", "hotel", "travel", "airport", "visa", "سياحة", "فندق", "سفر", "مطار", "تأشيرة"],
}

def detect_domains(text):
    text_lower = text.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(text_lower.count(kw.lower()) for kw in keywords)
        if score > 0:
            scores[domain] = score
    return sorted(scores, key=scores.get, reverse=True) if scores else []

# ════════════════════════════════════════════════════════════
#  API KEYS
# ════════════════════════════════════════════════════════════
try:
    deepl_from_secrets = st.secrets.get("DEEPL_API_KEY", "")
except:
    deepl_from_secrets = ""
try:
    cohere_from_secrets = st.secrets.get("COHERE_API_KEY", "")
except:
    cohere_from_secrets = ""

if "deepl_api_key" not in st.session_state:
    st.session_state.deepl_api_key = deepl_from_secrets
if "cohere_api_key" not in st.session_state:
    st.session_state.cohere_api_key = cohere_from_secrets

# ════════════════════════════════════════════════════════════
#  SESSION STATE
# ════════════════════════════════════════════════════════════
if "source_lang" not in st.session_state:
    st.session_state.source_lang = "Auto-Detect"
if "target_lang" not in st.session_state:
    st.session_state.target_lang = "Arabic"
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "selected_style" not in st.session_state:
    st.session_state.selected_style = "Auto-Detect"
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""
if "group_chat_messages" not in st.session_state:
    st.session_state.group_chat_messages = []
if "audio_key_counter" not in st.session_state:
    st.session_state.audio_key_counter = 0

def swap_languages():
    old_source = st.session_state.source_lang
    old_target = st.session_state.target_lang
    st.session_state.source_lang = old_target
    st.session_state.target_lang = old_source
    if st.session_state.source_lang == "Auto-Detect":
        st.session_state.source_lang = "English"
        if st.session_state.target_lang == "English":
            st.session_state.target_lang =
