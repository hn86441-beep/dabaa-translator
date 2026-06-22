import streamlit as st
import requests
import os
import json
from pathlib import Path
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict

st.set_page_config(
    page_title="HN TRANSLATOR",
    page_icon="🌐",
    layout="centered"
)

# ════════════════════════════════════════════════════════════
#  CSS — تصميم أنيق (النسخة الأصلية) مع تعديلات طفيفة للهواتف
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

.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(100,220,180,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(100,220,180,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}

.block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 0.6rem !important;
    padding-left: 0.6rem !important;
    padding-right: 0.6rem !important;
    max-width: 720px !important;   /* أوسع قليلاً للهواتف */
    position: relative;
    z-index: 1;
}

/* ====== العنوان ====== */
.app-header {
    text-align: center;
    padding: 0.4rem 0.5rem 0.3rem;
    position: relative;
}
.app-header .brand {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.35em;
    color: #4ECBA0;
    text-transform: uppercase;
    display: block;
}
.app-header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 22px;   /* قلّصت قليلاً */
    font-weight: 700;
    color: #f0f4ff;
    margin: 0 0 0.1rem 0;
    line-height: 1.2;
}
.app-header h1 .accent { color: #4ECBA0; }
.app-header .subtitle {
    font-size: 10px;
    color: rgba(180,200,230,0.55);
    margin: 0;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 500;
}

/* ====== بطاقات ====== */
.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 0.5rem;    /* قلّصت قليلاً */
    margin-bottom: 0.5rem;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06);
    position: relative;
    overflow: hidden;
}
.glass-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(78,203,160,0.4), transparent);
}

/* ====== زر الميكروفون (بنفس التصميم السابق) ====== */
div[data-testid="stAudioInput"] {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
    margin: 0.2rem 0 !important;
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
    font-size: 15px !important;
    font-weight: 600 !important;
    padding: 0.4rem 1.5rem !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px !important;
}
div[data-testid="stAudioInput"] button::before {
    content: "🎤";
    font-size: 18px;
}

/* ====== Selectbox ====== */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 10px !important;
    color: #e8f0ff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;  /* قلّصت قليلاً */
    transition: border-color 0.2s;
    padding: 0px 8px !important;
    min-height: 28px !important;  /* قلّصت قليلاً */
}
.stSelectbox > div > div:hover {
    border-color: rgba(78,203,160,0.5) !important;
}
.stSelectbox > div > div:focus-within {
    border-color: #4ECBA0 !important;
    box-shadow: 0 0 0 3px rgba(78,203,160,0.12) !important;
}
.stSelectbox label {
    font-size: 8px !important;   /* قلّصت قليلاً */
    font-weight: 600 !important;
    color: rgba(78,203,160,0.75) !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    margin-bottom: 1px !important;
}

/* ====== الأزرار ====== */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 11px !important;  /* قلّصت قليلاً */
    padding: 0.3rem 0.6rem !important;
    background: linear-gradient(135deg, #4ECBA0 0%, #2fa87a 100%) !important;
    color: #0a1520 !important;
    border: none !important;
    width: 100% !important;
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: 0.03em !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 16px rgba(78,203,160,0.15) !important;
    min-height: 30px !important;  /* قلّصت قليلاً */
}
.stButton > button:hover {
    background: linear-gradient(135deg, #5ed9b0 0%, #3dbf8a 100%) !important;
    box-shadow: 0 6px 24px rgba(78,203,160,0.3) !important;
    transform: translateY(-1px) !important;
}
.stButton:has(button[title="Swap"]) > button {
    background: rgba(255,255,255,0.07) !important;
    color: rgba(200,220,255,0.8) !important;
    box-shadow: none !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    font-size: 13px !important;
    padding: 0.1rem !important;
    min-height: 26px !important;
}
.stButton:has(button[title="Swap"]) > button:hover {
    background: rgba(78,203,160,0.12) !important;
    border-color: rgba(78,203,160,0.3) !important;
    box-shadow: none !important;
    transform: none !important;
    color: #4ECBA0 !important;
}

/* ====== Textarea ====== */
textarea {
    background: #1a1a2e !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
    color: #f0f4ff !important;
    font-size: 13px !important;   /* قلّصت قليلاً */
    font-family: 'Inter', sans-serif !important;
    padding: 8px 12px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    line-height: 1.5 !important;
    min-height: 60px !important;  /* قلّصت قليلاً */
}
textarea:focus {
    border-color: rgba(78,203,160,0.5) !important;
    box-shadow: 0 0 0 3px rgba(78,203,160,0.1) !important;
    outline: none !important;
}
textarea::placeholder {
    color: rgba(150,175,220,0.3) !important;
}

/* ====== صندوق النتيجة ====== */
.result-box {
    background: rgba(78,203,160,0.06);
    border-radius: 12px;
    padding: 0.4rem 0.6rem;
    border: 1px solid rgba(78,203,160,0.2);
    margin-top: 0.3rem;
    position: relative;
}
.result-box::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, #4ECBA0, #2fa87a);
    border-radius: 3px 0 0 3px;
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
    font-weight: 400;
}

/* ====== سياق المجال ====== */
.context {
    background: rgba(78,203,160,0.07);
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 10px;
    color: rgba(78,203,160,0.9);
    border: 1px solid rgba(78,203,160,0.15);
    margin-bottom: 0.3rem;
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
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

/* ====== رسائل ====== */
.stSuccess { background: rgba(78,203,160,0.08) !important; border: 1px solid rgba(78,203,160,0.25) !important; color: #a8f0d8 !important; padding: 4px 10px !important; font-size: 11px !important; border-radius: 10px !important; }
.stError { background: rgba(239,68,68,0.08) !important; border: 1px solid rgba(239,68,68,0.25) !important; padding: 4px 10px !important; font-size: 11px !important; border-radius: 10px !important; }
.stWarning { background: rgba(245,158,11,0.08) !important; border: 1px solid rgba(245,158,11,0.2) !important; padding: 4px 10px !important; font-size: 11px !important; border-radius: 10px !important; }
.stCode, code, pre {
    background: rgba(0,0,0,0.35) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #a8f0d8 !important;
    font-size: 11px !important;
    padding: 4px 8px !important;
}
hr {
    margin: 0.5rem 0 !important;
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(78,203,160,0.2), transparent) !important;
}
.stSpinner > div {
    border-color: #4ECBA0 !important;
}
.stCheckbox label {
    color: rgba(180,200,230,0.8) !important;
    font-size: 11px !important;
}
.stCaption {
    color: rgba(150,175,220,0.45) !important;
    font-size: 9px !important;
}
[data-testid="column"] {
    padding: 0 4px !important;
}
.section-heading {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: rgba(150,185,230,0.5);
    margin: 0.5rem 0 0.25rem;
    display: flex;
    align-items: center;
    gap: 6px;
}
.section-heading::before {
    content: '';
    width: 2px;
    height: 10px;
    background: #4ECBA0;
    border-radius: 2px;
    flex-shrink: 0;
}

/* ====== تحسينات للهواتف (معتدلة) ====== */
@media (max-width: 600px) {
    .block-container {
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
        padding-top: 0.4rem !important;
        padding-bottom: 0.4rem !important;
    }
    .app-header h1 {
        font-size: 20px !important;
    }
    .app-header .brand { font-size: 8px !important; }
    .app-header .subtitle { font-size: 9px !important; }
    div[data-testid="stAudioInput"] > div { min-width: 140px !important; }
    div[data-testid="stAudioInput"] button { font-size: 13px !important; padding: 0.3rem 1rem !important; }
    .stSelectbox > div > div { font-size: 11px !important; min-height: 26px !important; }
    .stButton > button { font-size: 10px !important; min-height: 28px !important; }
    textarea { font-size: 12px !important; min-height: 55px !important; padding: 6px 10px !important; }
    .result-box .text { font-size: 13px !important; }
    .section-heading { font-size: 7px !important; }
    .glass-card { padding: 0.4rem !important; }
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
    <p class="subtitle">Voice &amp; Text Translation · 8 Languages</p>
</div>
""", unsafe_allow_html=True)

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
    st.markdown('<div class="glass-card" style="text-align:center; padding:0.8rem;">🔐 Connect API Keys</div>', unsafe_allow_html=True)
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
    st.caption("💡 Keys are never stored on any server — session only.")
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
tgt_idx = tgt_options.index(st.session_state.target_lang) if st.session_state.target_lang in tgt_options else 0
style_idx = style_list.index(st.session_state.selected_style) if st.session_state.selected_style in style_list else 0

# اللغات
st.markdown('<div class="section-heading">Translation Direction</div>', unsafe_allow_html=True)
col_left, col_mid, col_right = st.columns([1, 0.18, 1])
with col_left:
    source_lang_name = st.selectbox("From", lang_list, index=src_idx)
with col_mid:
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    if st.button("⇄", help="Swap", use_container_width=True):
        swap_languages()
with col_right:
    target_lang_name = st.selectbox("To", tgt_options, index=tgt_idx)

st.session_state.source_lang = source_lang_name
st.session_state.target_lang = target_lang_name
source_lang = languages_dict[source_lang_name]
target_lang = languages_dict[target_lang_name]

# النمط
st.markdown('<div class="section-heading">Domain Style</div>', unsafe_allow_html=True)
selected_style_label = st.selectbox("Style", style_list, index=style_idx, label_visibility="collapsed")
selected_domain = STYLE_OPTIONS[selected_style_label]
st.session_state.selected_style = selected_style_label

# ====== الميكروفون ======
st.markdown("---")
st.markdown('<div class="section-heading">🎤 Voice Input</div>', unsafe_allow_html=True)

audio_value = st.audio_input("", key="mic_audio_main", label_visibility="collapsed")

if audio_value:
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
                    st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="result-box">
                        <span class="label">✦ Translation</span>
                        <div class="text">{translated_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.code(translated_text, language=None)
                else:
                    st.error(f"❌ {engine}")
        else:
            st.error(f"❌ {engine_used}")

# ====== النص المكتوب ======
st.markdown("---")
st.markdown('<div class="section-heading">Text Input</div>', unsafe_allow_html=True)
input_text = st.text_area("", height=60, placeholder="اكتب أو الصق النص هنا...", value=st.session_state.input_text, key="input_text_area")
if input_text != st.session_state.input_text:
    st.session_state.input_text = input_text

# السياق
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

# زر الترجمة الرئيسي
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
                st.markdown(f"""
                <div class="result-box">
                    <span class="label">✦ Translation</span>
                    <div class="text">{translation_result}</div>
                </div>
                """, unsafe_allow_html=True)
                st.code(translation_result, language=None)
            else:
                st.error(f"❌ {translation_result}")

st.markdown("""
<div style="text-align:center; padding: 0.6rem 0 0.2rem; color:rgba(100,130,170,0.3); font-size:9px;
            letter-spacing:0.12em; font-family:Inter,sans-serif; text-transform:uppercase;">
    HN TRANSLATOR &nbsp;·&nbsp; Voice Translation Suite
</div>
""", unsafe_allow_html=True)
