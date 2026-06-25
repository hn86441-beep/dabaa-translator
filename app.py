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
#  تحليل المشاعر
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_emotion_classifier():
    try:
        return pipeline("text-classification", model="tabularisai/multilingual-sentiment-analysis")
    except Exception as e:
        st.warning(f"⚠️ فشل تحميل النموذج: {e}")
        return None

emotion_classifier = load_emotion_classifier()

def analyze_emotion(text):
    if not text or emotion_classifier is None:
        return "محايد"
    try:
        result = emotion_classifier(text[:512])[0]
        label = result['label'].upper()
        if "POSITIVE" in label:
            return "فرح"
        elif "NEGATIVE" in label:
            return "حزن"
        else:
            return "محايد"
    except Exception:
        return "محايد"

# ════════════════════════════════════════════════════════════
#  تحويل النص إلى صوت (TTS)
# ════════════════════════════════════════════════════════════
from gtts import gTTS

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
    except Exception as e:
        return None

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
#  CSS - ألوان فقط، بدون حركات
# ════════════════════════════════════════════════════════════
def get_css(theme):
    if theme == "light":
        return """
        .stApp { background: #f5f7fa !important; }
        .app-header { text-align: center; padding: 0.5rem 0; }
        .app-header h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: #1a1a2e;
            margin: 0;
        }
        .app-header h1 .accent { color: #2a7a60; }
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
        """
    else:
        return """
        .stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0f1728 40%, #0a1520 100%) !important; }
        .app-header { text-align: center; padding: 0.5rem 0; }
        .app-header h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: #f0f4ff;
            margin: 0;
        }
        .app-header h1 .accent { color: #4ECBA0; }
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
        """

st.markdown(f"<style>{get_css(st.session_state.theme)}</style>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  العنوان في المنتصف
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <h1>HN <span class="accent">TRANSLATOR</span></h1>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  الشريط الجانبي - زر تبديل المظهر + السجل المبسط
# ════════════════════════════════════════════════════════════
with st.sidebar:
    # زر تبديل المظهر (أيقونة فقط)
    if st.button("🌓", help="تبديل المظهر", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()
    
    st.divider()
    
    # السجل - بدون أي كلمات إضافية
    history = get_history(limit=100)
    
    if history:
        # زر مسح السجل (أيقونة فقط)
        if st.button("🗑️", help="مسح الكل", use_container_width=True):
            clear_history()
            st.rerun()
        
        # عرض الترجمات بشكل مبسط جداً
        for item in history:
            st.markdown(f"""
            <div class="history-item">
                <div class="original">{item.get('original', '')}</div>
                <div class="translated">{item.get('translated', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # زر تصدير السجل (أيقونة فقط)
        if st.button("📤", help="تصدير السجل (JSON)", use_container_width=True):
            json_str = export_history_json()
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="translation_history.json">📥 تحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        # أيقونة فقط عند عدم وجود ترجمات
        st.markdown("<div style='text-align:center; color: rgba(150,175,220,0.3); font-size: 30px;'>📭</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  باقي الكود (الإعدادات، الترجمة، الصوت، إلخ)
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

if not st.session_state.deepl_api_key or not st.session_state.cohere_api_key:
    st.markdown('<div class="glass-card" style="text-align:center;">🔐 Connect API Keys</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.deepl_api_key:
            deepl_input = st.text_input("DeepL Key", type="password", placeholder="abc...xyz:fx")
            if deepl_input:
                st.session_state.deepl_api_key = deepl_input
                st.rerun()
        else:
            st.success("✅ DeepL Active")
    with col2:
        if not st.session_state.cohere_api_key:
            cohere_input = st.text_input("Cohere Key", type="password", placeholder="abcd-1234-efgh-5678")
            if cohere_input:
                st.session_state.cohere_api_key = cohere_input
                st.rerun()
        else:
            st.success("✅ Cohere Active")
    st.stop()

# ════════════════════════════════════════════════════════════
#  دوال الترجمة والتعرف على الصوت
# ════════════════════════════════════════════════════════════
def translate_deepl(text, target_lang):
    if not st.session_state.deepl_api_key:
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

def fetch_ai_translation(text, target_lang):
    return translate_deepl(text, target_lang)

def speech_to_text_cohere(audio_bytes, language_code="auto"):
    if not st.session_state.cohere_api_key:
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
            headers={"Authorization": f"Bearer {st.session_state.cohere_api_key}", "Content-Type": encoder.content_type},
            data=encoder,
            timeout=30
        )
        if response.status_code == 200:
            text = response.json().get("text", "").strip()
            if text:
                return text, "Speech Recognition"
            else:
                return None, "No speech detected"
        return None, f"Cohere error {response.status_code}"
    except Exception as e:
        return None, f"Error: {str(e)}"

@st.cache_resource
def load_whisper_model():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("small", device="cpu", compute_type="int8")
    except:
        return None

def speech_to_text_whisper(audio_bytes):
    model = load_whisper_model()
    if not model:
        return None, "Whisper unavailable"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        segments, info = model.transcribe(tmp_path, language="ru", beam_size=5, vad_filter=True)
        text = " ".join(segment.text for segment in segments).strip()
        if text:
            return text, "Speech Recognition"
        else:
            return None, "No speech detected"
    except Exception as e:
        return None, f"Error: {str(e)}"
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except:
            pass

def speech_to_text(audio_bytes, language_code="auto"):
    if language_code == "ru":
        return speech_to_text_whisper(audio_bytes)
    return speech_to_text_cohere(audio_bytes, language_code)

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

def swap_languages():
    old_source = st.session_state.source_lang
    old_target = st.session_state.target_lang
    st.session_state.source_lang = old_target
    st.session_state.target_lang = old_source
    if st.session_state.source_lang == "Auto-Detect":
        st.session_state.source_lang = "English"
        if st.session_state.target_lang == "English":
            st.session_state.target_lang = "Arabic"
    if st.session_state.source_lang == st.session_state.target_lang:
        for lang in languages_dict.keys():
            if lang != st.session_state.source_lang and lang != "Auto-Detect":
                st.session_state.target_lang = lang
                break
    st.rerun()

def clear_audio():
    if "mic_audio_main" in st.session_state:
        del st.session_state.mic_audio_main
    st.session_state.input_text = ""
    st.session_state.translated_text = ""
    st.rerun()

# ════════════════════════════════════════════════════════════
#  الواجهة الرئيسية (UI)
# ════════════════════════════════════════════════════════════
lang_list = list(languages_dict.keys())
style_list = list(STYLE_OPTIONS.keys())

if st.session_state.target_lang == st.session_state.source_lang:
    for lang in lang_list:
        if lang != st.session_state.source_lang:
            st.session_state.target_lang = lang
            break

src_idx = lang_list.index(st.session_state.source_lang) if st.session_state.source_lang in lang_list else 0
tgt_options = [k for k in lang_list if k != st.session_state.source_lang and k != "Auto-Detect"]
if st.session_state.target_lang not in tgt_options:
    st.session_state.target_lang = tgt_options[0] if tgt_options else "English"
tgt_idx = tgt_options.index(st.session_state.target_lang) if st.session_state.target_lang in tgt_options else 0
style_idx = style_list.index(st.session_state.selected_style) if st.session_state.selected_style in style_list else 0

# ====== اللغات ======
st.markdown('<div class="section-heading">Translation Direction</div>', unsafe_allow_html=True)
col_left, col_mid, col_right = st.columns([1, 0.18, 1])
with col_left:
    source_lang_name = st.selectbox("From", lang_list, index=src_idx)
with col_mid:
    st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)
    if st.button("⇄", help="Swap", use_container_width=True):
        swap_languages()
with col_right:
    target_lang_name = st.selectbox("To", tgt_options, index=tgt_idx)

if source_lang_name != st.session_state.source_lang:
    st.session_state.source_lang = source_lang_name
if target_lang_name != st.session_state.target_lang:
    st.session_state.target_lang = target_lang_name

source_lang = languages_dict[st.session_state.source_lang]
target_lang = languages_dict[st.session_state.target_lang]

# ====== النمط ======
st.markdown('<div class="section-heading">Domain Style</div>', unsafe_allow_html=True)
selected_style_label = st.selectbox("Style", style_list, index=style_idx, label_visibility="collapsed")
selected_domain = STYLE_OPTIONS[selected_style_label]
st.session_state.selected_style = selected_style_label

# ====== الميكروفون ======
st.markdown("---")
st.markdown('<div class="section-heading">🎤 Voice Input</div>', unsafe_allow_html=True)

col_mic, col_clear = st.columns([5, 1])
with col_mic:
    audio_value = st.audio_input("", key="mic_audio_main", label_visibility="collapsed")
with col_clear:
    if "mic_audio_main" in st.session_state and st.session_state.mic_audio_main is not None:
        st.markdown('<div class="clear-btn-wrapper">', unsafe_allow_html=True)
        if st.button("✖", key="clear_btn", help="حذف التسجيل", type="secondary"):
            clear_audio()
        st.markdown('</div>', unsafe_allow_html=True)

if audio_value is not None:
    with st.spinner("⏳ جاري التعرف..."):
        audio_bytes = audio_value.getvalue()
        recognized_text, engine_used = speech_to_text(audio_bytes, source_lang)
        if recognized_text:
            st.success(f"✅ {recognized_text}")
            st.session_state.input_text = recognized_text
            with st.spinner("⏳ جاري الترجمة..."):
                translated_text, engine = fetch_ai_translation(recognized_text, target_lang)
                if translated_text:
                    st.session_state.translated_text = translated_text
                    emotion = analyze_emotion(recognized_text)
                    
                    st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="result-box">
                        <span class="label">✦ Translation</span>
                        <div class="text">{translated_text}</div>
                        <div class="emotion">{emotion}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.code(translated_text, language=None)
                    
                    audio_bytes_tts = generate_audio(translated_text, target_lang)
                    if audio_bytes_tts:
                        st.audio(audio_bytes_tts, format="audio/mp3")
                    
                    save_translation(recognized_text, translated_text, emotion, source_lang_name, target_lang_name)
                else:
                    st.error(f"❌ {engine}")
        else:
            st.error(f"❌ {engine_used}")

# ====== النص المكتوب ======
st.markdown("---")
st.markdown('<div class="section-heading">Text Input</div>', unsafe_allow_html=True)
input_text = st.text_area("", height=70, placeholder="اكتب أو الصق النص هنا...", value=st.session_state.input_text, key="input_text_area")
if input_text != st.session_state.input_text:
    st.session_state.input_text = input_text

if input_text.strip():
    detected = detect_domains(input_text)
    if detected:
        badges = ""
        for d in detected[:3]:
            dn = DOMAINS[d]["name_en"]
            emoji = DOMAINS[d]["emoji"]
            css_class = f"tag-{d}" if d in DOMAINS else "tag-gen"
            badges += f'<span class="tag {css_class}">{emoji} {dn}</span>'
        st.markdown(f'<div class="context">🔍 {badges}</div>', unsafe_allow_html=True)

if st.button("Translate ✦", use_container_width=True, key="translate_btn"):
    if not st.session_state.deepl_api_key:
        st.error("❌ API key missing.")
    elif not input_text.strip():
        st.warning("الرجاء إدخال نص للترجمة.")
    else:
        with st.spinner("جاري الترجمة..."):
            translation_result, source_engine = fetch_ai_translation(input_text, target_lang)
            if translation_result:
                st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                emotion = analyze_emotion(input_text)
                
                st.markdown(f"""
                <div class="result-box">
                    <span class="label">✦ Translation</span>
                    <div class="text">{translation_result}</div>
                    <div class="emotion">{emotion}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.code(translation_result, language=None)
                
                audio_bytes_tts = generate_audio(translation_result, target_lang)
                if audio_bytes_tts:
                    st.audio(audio_bytes_tts, format="audio/mp3")
                
                save_translation(input_text, translation_result, emotion, source_lang_name, target_lang_name)
            else:
                st.error(f"❌ {translation_result}")

st.markdown("""
<div style="text-align:center; padding: 1rem 0; color:rgba(100,130,170,0.3); font-size:9px; letter-spacing:0.12em; text-transform:uppercase;">
    HN TRANSLATOR · Voice Translation Suite
</div>
""", unsafe_allow_html=True)
