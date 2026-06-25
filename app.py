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
import re

# ════════════════════════════════════════════════════════════
#  تحليل المشاعر (متعدد اللغات)
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
            return "😊 فرح"
        elif "NEGATIVE" in label:
            return "😢 حزن"
        else:
            return "😐 محايد"
    except Exception:
        return "😐 محايد"

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
        st.error(f"❌ فشل توليد الصوت: {str(e)}")
        return None

# ════════════════════════════════════════════════════════════
#  دالة نسخ النص باستخدام JavaScript آمن
# ════════════════════════════════════════════════════════════
def copy_to_clipboard(text):
    """نسخ النص إلى الحافظة باستخدام JavaScript."""
    if not text:
        return
    # استخدام st.code مع زر نسخ مدمج (أفضل حل)
    # لكننا نضيف زراً منفصلاً أيضاً
    pass

# ════════════════════════════════════════════════════════════
#  إعدادات الصفحة
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="HN TRANSLATOR",
    page_icon="🌐",
    layout="wide"
)

# ════════════════════════════════════════════════════════════
#  CSS
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

#MainMenu, footer, header { visibility: hidden; }

.stApp {
    background: linear-gradient(135deg, #0a0a1a 0%, #0f1728 40%, #0a1520 100%) !important;
    font-family: 'Inter', sans-serif !important;
    min-height: 100vh;
}

.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 1rem !important;
    max-width: 900px !important;
    position: relative;
    z-index: 1;
}

.app-header {
    text-align: center;
    padding: 0.3rem 0.5rem 0.2rem;
}
.app-header .brand {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.35em;
    color: #4ECBA0;
    text-transform: uppercase;
    display: block;
    margin-bottom: 0.1rem;
}
.app-header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #f0f4ff;
    margin: 0;
}
.app-header h1 .accent { color: #4ECBA0; }

.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 0.6rem;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

div[data-testid="stAudioInput"] {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
}
div[data-testid="stAudioInput"] > div {
    background: rgba(78,203,160,0.08) !important;
    border: 2px solid rgba(78,203,160,0.3) !important;
    border-radius: 60px !important;
    padding: 0.2rem 0.4rem !important;
    width: auto !important;
    min-width: 160px !important;
    transition: all 0.3s !important;
    backdrop-filter: blur(8px);
}
div[data-testid="stAudioInput"] > div:hover {
    border-color: #4ECBA0 !important;
    box-shadow: 0 0 30px rgba(78,203,160,0.15) !important;
}
div[data-testid="stAudioInput"] button {
    background: transparent !important;
    border: none !important;
    color: #e8f0ff !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.8rem !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
}
div[data-testid="stAudioInput"] button::before {
    content: "🎤";
    font-size: 20px;
}

div.clear-btn-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 60px;
}
button[kind="secondary"][data-testid="baseButton-secondary"] {
    background: rgba(239,68,68,0.1) !important;
    border: 1.5px solid rgba(239,68,68,0.25) !important;
    color: #f87171 !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    padding: 0 !important;
    border-radius: 50% !important;
    width: 40px !important;
    height: 40px !important;
    min-height: unset !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 0 15px rgba(239,68,68,0.05) !important;
    cursor: pointer !important;
}
button[kind="secondary"][data-testid="baseButton-secondary"]:hover {
    background: rgba(239,68,68,0.2) !important;
    border-color: #f87171 !important;
    box-shadow: 0 0 30px rgba(239,68,68,0.15) !important;
    transform: scale(1.08) !important;
}

.stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 10px !important;
    color: #e8f0ff !important;
    font-size: 13px !important;
    padding: 0px 8px !important;
    min-height: 30px !important;
}
.stSelectbox label {
    font-size: 9px !important;
    font-weight: 600 !important;
    color: rgba(78,203,160,0.75) !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    padding: 0.35rem 0.8rem !important;
    background: linear-gradient(135deg, #4ECBA0 0%, #2fa87a 100%) !important;
    color: #0a1520 !important;
    border: none !important;
    width: 100% !important;
    font-family: 'Space Grotesk', sans-serif !important;
    min-height: 32px !important;
}
.stButton:has(button[title="Swap"]) > button {
    background: rgba(255,255,255,0.07) !important;
    color: rgba(200,220,255,0.8) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    font-size: 14px !important;
    min-height: 28px !important;
}

textarea {
    background: #1a1a2e !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #f0f4ff !important;
    font-size: 14px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 8px 12px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    line-height: 1.5 !important;
    min-height: 60px !important;
}
textarea:focus {
    border-color: rgba(78,203,160,0.5) !important;
    box-shadow: 0 0 0 3px rgba(78,203,160,0.1) !important;
    outline: none !important;
}
textarea::placeholder {
    color: rgba(150,175,220,0.4) !important;
}

.result-box {
    background: rgba(78,203,160,0.06);
    border-radius: 12px;
    padding: 0.5rem 0.8rem;
    border: 1px solid rgba(78,203,160,0.2);
    margin-top: 0.4rem;
    position: relative;
}
.result-box::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, #4ECBA0, #2fa87a);
}
.result-box .label {
    font-size: 8px;
    font-weight: 700;
    text-transform: uppercase;
    color: rgba(78,203,160,0.7);
    letter-spacing: 0.15em;
    display: block;
}
.result-box .text {
    font-size: 14px;
    color: #e8f0ff;
    line-height: 1.5;
}
.result-box .emotion {
    margin-top: 4px;
    font-size: 13px;
    color: #4ECBA0;
    font-weight: 500;
}
.result-box .actions {
    margin-top: 8px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.copy-btn {
    background: rgba(78,203,160,0.1) !important;
    border: 1px solid rgba(78,203,160,0.2) !important;
    border-radius: 20px !important;
    padding: 2px 12px !important;
    font-size: 11px !important;
    color: #4ECBA0 !important;
    cursor: pointer;
    transition: 0.3s;
}
.copy-btn:hover {
    background: rgba(78,203,160,0.2) !important;
    border-color: #4ECBA0 !important;
}
.context {
    background: rgba(78,203,160,0.07);
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 10px;
    color: rgba(78,203,160,0.9);
    border: 1px solid rgba(78,203,160,0.15);
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}
.tag {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 1px 6px;
    border-radius: 12px;
    font-size: 8px;
    font-weight: 600;
}
.tag-pol  { background: rgba(230,57,70,0.2);   color: #ff6b78; border: 1px solid rgba(230,57,70,0.3); }
.tag-leg  { background: rgba(83,74,183,0.2);   color: #9d96f0; border: 1px solid rgba(83,74,183,0.3); }
.tag-eco  { background: rgba(244,162,97,0.2);  color: #f4b060; border: 1px solid rgba(244,162,97,0.3); }
.tag-med  { background: rgba(42,157,143,0.2);  color: #3dd1bd; border: 1px solid rgba(42,157,143,0.3); }
.tag-sci  { background: rgba(38,70,83,0.3);    color: #7dbfcf; border: 1px solid rgba(38,70,83,0.5); }
.tag-eng  { background: rgba(29,158,117,0.2);  color: #42d4a0; border: 1px solid rgba(29,158,117,0.3); }
.tag-mil  { background: rgba(139,0,0,0.2);     color: #ff7b7b; border: 1px solid rgba(139,0,0,0.35); }
.tag-edu  { background: rgba(244,208,63,0.15); color: #f4d24a; border: 1px solid rgba(244,208,63,0.25); }
.tag-rel  { background: rgba(108,52,131,0.2);  color: #c07fe0; border: 1px solid rgba(108,52,131,0.35); }
.tag-spt  { background: rgba(230,126,34,0.2);  color: #f0944a; border: 1px solid rgba(230,126,34,0.3); }
.tag-lit  { background: rgba(216,27,96,0.2);   color: #f06090; border: 1px solid rgba(216,27,96,0.3); }
.tag-it   { background: rgba(0,172,193,0.2);   color: #3dd4e4; border: 1px solid rgba(0,172,193,0.3); }
.tag-env  { background: rgba(67,160,71,0.2);   color: #6dd873; border: 1px solid rgba(67,160,71,0.3); }
.tag-agr  { background: rgba(121,85,72,0.2);   color: #c4a08a; border: 1px solid rgba(121,85,72,0.3); }
.tag-tour { background: rgba(0,131,143,0.2);   color: #30c8d8; border: 1px solid rgba(0,131,143,0.3); }
.tag-gen  { background: rgba(107,114,128,0.2); color: #9ca3af; border: 1px solid rgba(107,114,128,0.3); }

.stSuccess { background: rgba(78,203,160,0.08) !important; border: 1px solid rgba(78,203,160,0.25) !important; color: #a8f0d8 !important; }
.stError { background: rgba(239,68,68,0.08) !important; border: 1px solid rgba(239,68,68,0.25) !important; }
hr { margin: 0.6rem 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(78,203,160,0.2), transparent); }
.section-heading {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: rgba(150,185,230,0.5);
    margin: 0.6rem 0 0.3rem;
    display: flex;
    align-items: center;
    gap: 6px;
}
.section-heading::before {
    content: '';
    width: 2px;
    height: 10px;
    background: #4ECBA0;
}

[data-testid="stSidebar"] {
    background: rgba(10,10,26,0.95) !important;
    border-right: 1px solid rgba(78,203,160,0.1) !important;
}
[data-testid="stSidebar"] .stMarkdown {
    color: #e8f0ff !important;
}
.history-item {
    background: rgba(78,203,160,0.06);
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 6px;
    border-left: 2px solid #4ECBA0;
}
.history-item .time {
    font-size: 9px;
    color: rgba(180,200,230,0.4);
}
.history-item .text {
    font-size: 12px;
    color: #e8f0ff;
}
.history-item .lang {
    font-size: 9px;
    color: rgba(78,203,160,0.6);
}

@media (max-width: 600px) {
    .block-container { padding: 0.4rem !important; }
    .app-header h1 { font-size: 20px !important; }
    .app-header { padding: 0.2rem 0.3rem 0.1rem !important; }
    div[data-testid="stAudioInput"] > div { min-width: 140px !important; }
    div[data-testid="stAudioInput"] button { font-size: 14px !important; padding: 0.4rem 1.2rem !important; }
    .stButton > button { font-size: 11px !important; min-height: 34px !important; }
    textarea { font-size: 13px !important; min-height: 50px !important; }
    button[kind="secondary"][data-testid="baseButton-secondary"] { width: 34px !important; height: 34px !important; font-size: 17px !important; }
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  العنوان
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <span class="brand">✦ Smart Voice Translator ✦</span>
    <h1>HN <span class="accent">TRANSLATOR</span></h1>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  الشريط الجانبي: سجل الترجمات
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📜 سجل الترجمات")
    
    if "history" not in st.session_state:
        st.session_state.history = []
    
    if st.session_state.history:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"**{len(st.session_state.history)}** ترجمة")
        with col2:
            if st.button("🗑️ مسح الكل", use_container_width=True):
                st.session_state.history = []
                st.rerun()
        
        st.divider()
        
        for item in reversed(st.session_state.history[-50:]):
            st.markdown(f"""
            <div class="history-item">
                <div class="text">🔹 {item.get('original', '')[:50]}...</div>
                <div class="text" style="color: #4ECBA0;">→ {item.get('translated', '')[:50]}...</div>
                <div class="lang">
                    {item.get('source_lang', '')} → {item.get('target_lang', '')} 
                    · {item.get('emotion', '')}
                </div>
                <div class="time">{item.get('time', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("📤 تصدير السجل (JSON)", use_container_width=True):
            json_str = json.dumps(st.session_state.history, ensure_ascii=False, indent=2)
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="translation_history.json">📥 تحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.info("📭 لا توجد ترجمات محفوظة")

# ════════════════════════════════════════════════════════════
#  CONFIGURATION
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
#  TRANSLATION & SPEECH FUNCTIONS
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
#  دالة النسخ (باستخدام JavaScript آمن)
# ════════════════════════════════════════════════════════════
def copy_button(text, label="📋 نسخ"):
    """إنشاء زر نسخ يعمل باستخدام JavaScript."""
    # ترميز النص ليكون آمناً للاستخدام في JavaScript
    safe_text = json.dumps(text)
    js_code = f"""
    <button onclick="navigator.clipboard.writeText({safe_text}).then(() => {{this.textContent = '✅ تم النسخ!'; setTimeout(() => {{this.textContent = '{label}';}}, 2000);}}).catch(() => {{alert('فشل النسخ');}})" 
            style="background:rgba(78,203,160,0.1);border:1px solid rgba(78,203,160,0.2);border-radius:20px;padding:2px 12px;font-size:11px;color:#4ECBA0;cursor:pointer;transition:0.3s;"
            onmouseover="this.style.background='rgba(78,203,160,0.2)'" 
            onmouseout="this.style.background='rgba(78,203,160,0.1)'">
        {label}
    </button>
    """
    return js_code

# ════════════════════════════════════════════════════════════
#  UI
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
                    
                    # عرض الترجمة مع زر نسخ مدمج (st.code يحتوي على زر نسخ)
                    st.markdown(f"""
                    <div class="result-box">
                        <span class="label">✦ Translation</span>
                        <div class="text">{translated_text}</div>
                        <div class="emotion">{emotion}</div>
                        <div class="actions">
                            {copy_button(translated_text)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # st.code يحتوي على زر نسخ مدمج في Streamlit 1.28+
                    st.code(translated_text, language=None)
                    
                    # زر تشغيل الصوت
                    audio_bytes_tts = generate_audio(translated_text, target_lang)
                    if audio_bytes_tts:
                        st.audio(audio_bytes_tts, format="audio/mp3")
                    
                    # حفظ في السجل
                    st.session_state.history.append({
                        "original": recognized_text,
                        "translated": translated_text,
                        "emotion": emotion,
                        "source_lang": source_lang_name,
                        "target_lang": target_lang_name,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
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
                    <div class="actions">
                        {copy_button(translation_result)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.code(translation_result, language=None)
                
                audio_bytes_tts = generate_audio(translation_result, target_lang)
                if audio_bytes_tts:
                    st.audio(audio_bytes_tts, format="audio/mp3")
                
                st.session_state.history.append({
                    "original": input_text,
                    "translated": translation_result,
                    "emotion": emotion,
                    "source_lang": source_lang_name,
                    "target_lang": target_lang_name,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
            else:
                st.error(f"❌ {translation_result}")

st.markdown("""
<div style="text-align:center; padding: 1rem 0; color:rgba(100,130,170,0.3); font-size:9px; letter-spacing:0.12em; text-transform:uppercase;">
    HN TRANSLATOR · Voice Translation Suite
</div>
""", unsafe_allow_html=True)
