import streamlit as st
import requests
import os
import json
from pathlib import Path
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict

# ════════════════════════════════════════════════════════════
#  إعدادات الصفحة
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="HASSAN NASSER | Voice Translator",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ════════════════════════════════════════════════════════════
#  CSS - واجهة محسنة مع ميكروفون أسطوري
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ====== الخطوط والأساسيات ====== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ====== إخفاء العناصر الافتراضية ====== */
#MainMenu, footer, header {
    visibility: hidden;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* ====== الهيدر ====== */
.hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 20px;
    padding: 2.5rem 2.5rem 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    position: relative;
    overflow: hidden;
}

.hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -30%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(93,202,165,0.15) 0%, transparent 70%);
    border-radius: 50%;
}

.hero-name {
    font-size: 34px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
    position: relative;
    z-index: 1;
}

.hero-name span {
    color: #5DCAA5;
    background: rgba(93,202,165,0.15);
    padding: 2px 12px;
    border-radius: 8px;
}

.hero-sub {
    font-size: 14px;
    color: rgba(255,255,255,0.5);
    margin-top: 6px;
    letter-spacing: 0.06em;
    font-weight: 400;
    position: relative;
    z-index: 1;
}

.hero-pills {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 14px;
    position: relative;
    z-index: 1;
}

.pill {
    display: inline-block;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    transition: all 0.3s ease;
}

.pill-active {
    background: #5DCAA5;
    color: #04342C;
}

.pill-muted {
    background: rgba(255,255,255,0.07);
    border: 0.5px solid rgba(255,255,255,0.12);
    color: rgba(255,255,255,0.5);
}

.lang-bar {
    display: flex;
    gap: 6px;
    margin-top: 16px;
    align-items: center;
    position: relative;
    z-index: 1;
}

.ldot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #5DCAA5;
    display: inline-block;
    animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.8); }
}

.lang-bar-txt {
    font-size: 11px;
    color: rgba(255,255,255,0.3);
    margin-left: 4px;
}

/* ====== البطاقات ====== */
.rcard {
    border-radius: 16px;
    padding: 1.3rem 1.5rem;
    border: 0.5px solid rgba(229, 231, 235, 0.6);
    background: #ffffff;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.rcard:hover {
    box-shadow: 0 8px 30px rgba(0,0,0,0.08);
    transform: translateY(-2px);
}

.rcard-pol { border-top: 4px solid #E63946; }
.rcard-leg { border-top: 4px solid #534AB7; }
.rcard-eco { border-top: 4px solid #F4A261; }
.rcard-med { border-top: 4px solid #2A9D8F; }
.rcard-sci { border-top: 4px solid #264653; }
.rcard-eng { border-top: 4px solid #1D9E75; }
.rcard-mil { border-top: 4px solid #8B0000; }
.rcard-edu { border-top: 4px solid #F4D03F; }
.rcard-rel { border-top: 4px solid #6C3483; }
.rcard-spt { border-top: 4px solid #E67E22; }
.rcard-lit { border-top: 4px solid #D81B60; }
.rcard-it  { border-top: 4px solid #00ACC1; }
.rcard-env { border-top: 4px solid #43A047; }
.rcard-agr { border-top: 4px solid #795548; }
.rcard-med2 { border-top: 4px solid #5E35B1; }
.rcard-tour { border-top: 4px solid #00838F; }
.rcard-gen { border-top: 4px solid #6B7280; }
.rcard-priority {
    box-shadow: 0 0 0 2px rgba(93,202,165,0.4);
    background: #f6fffd;
}

.rlabel {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.rlabel-pol { color: #9B2226; }
.rlabel-leg { color: #3C3489; }
.rlabel-eco { color: #9C6644; }
.rlabel-med { color: #1B6B5E; }
.rlabel-sci { color: #1D3A4C; }
.rlabel-eng { color: #085041; }
.rlabel-mil { color: #8B0000; }
.rlabel-edu { color: #9A7D0A; }
.rlabel-rel { color: #6C3483; }
.rlabel-spt { color: #A04000; }
.rlabel-lit { color: #AD1457; }
.rlabel-it  { color: #006064; }
.rlabel-env { color: #1B5E20; }
.rlabel-agr { color: #4E342E; }
.rlabel-med2 { color: #4527A0; }
.rlabel-tour { color: #006064; }
.rlabel-gen { color: #4B5563; }

.rtext {
    font-size: 15px;
    line-height: 1.8;
    color: #1f2937;
    direction: auto;
}

/* ====== الصناديق ====== */
.detected-box {
    background: #E6F4F1;
    border-left: 4px solid #5DCAA5;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    font-size: 13px;
    color: #04342C;
    margin-bottom: 1.2rem;
}

/* ====== الشارات ====== */
.api-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin-right: 4px;
}
.api-deepl { background: #0F2B46; color: #8ECAE6; }
.api-cohere { background: #1a1a2e; color: #8ECAE6; }
.api-whisper { background: #4a90d9; color: #ffffff; }

/* ====== أوسمة المجالات ====== */
.domain-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin-right: 6px;
    margin-bottom: 4px;
}
.db-pol { background: #E63946; color: white; }
.db-leg { background: #534AB7; color: white; }
.db-eco { background: #F4A261; color: #3E2723; }
.db-med { background: #2A9D8F; color: white; }
.db-sci { background: #264653; color: white; }
.db-eng { background: #1D9E75; color: white; }
.db-mil { background: #8B0000; color: white; }
.db-edu { background: #F4D03F; color: #3E2723; }
.db-rel { background: #6C3483; color: white; }
.db-spt { background: #E67E22; color: white; }
.db-lit { background: #D81B60; color: white; }
.db-it  { background: #00ACC1; color: white; }
.db-env { background: #43A047; color: white; }
.db-agr { background: #795548; color: white; }
.db-med2 { background: #5E35B1; color: white; }
.db-tour { background: #00838F; color: white; }
.db-gen { background: #6B7280; color: white; }

.priority-badge {
    display: inline-block;
    background: #5DCAA5;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    margin-left: 6px;
}

/* ====== أخطاء ====== */
.error-box {
    background: #fee2e2;
    border-left: 4px solid #ef4444;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    font-size: 14px;
    color: #991b1b;
    margin-bottom: 1rem;
}

/* ====== حقول الإدخال ====== */
textarea {
    border-radius: 12px !important;
    border: 0.5px solid #d1d5db !important;
    font-size: 14px !important;
    transition: border-color 0.3s ease;
}

textarea:focus {
    border-color: #5DCAA5 !important;
    box-shadow: 0 0 0 3px rgba(93,202,165,0.2) !important;
}

/* ====== الأزرار ====== */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    background: linear-gradient(135deg, #0f0c29, #302b63) !important;
    color: white !important;
    border: none !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(48, 43, 99, 0.4) !important;
}

/* ============================================================
   🎙️ ميكروفون أسطوري
   ============================================================ */

/* إخفاء النص الافتراضي لـ st.audio_input */
div[data-testid="stAudioInput"] label {
    display: none !important;
}

/* إعادة تنسيق الحاوية */
div[data-testid="stAudioInput"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* زر الميكروفون الأساسي */
div[data-testid="stAudioInput"] > div > div {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    min-height: 80px;
}

/* تخصيص زر الميكروفون نفسه */
div[data-testid="stAudioInput"] button {
    width: 80px !important;
    height: 80px !important;
    border-radius: 50% !important;
    background: linear-gradient(145deg, #1a1a3e, #2d2b6e) !important;
    border: 2px solid rgba(93, 202, 165, 0.5) !important;
    box-shadow: 
        0 0 20px rgba(93, 202, 165, 0.2),
        inset 0 0 30px rgba(93, 202, 165, 0.05) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer;
    position: relative;
    z-index: 1;
}

/* تأثير الهالة الخلفية للميكروفون */
div[data-testid="stAudioInput"] button::before {
    content: '';
    position: absolute;
    inset: -8px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(93, 202, 165, 0.15), transparent 70%);
    opacity: 0;
    transition: opacity 0.5s ease;
}

div[data-testid="stAudioInput"] button:hover::before {
    opacity: 1;
}

/* عند التمرير على الميكروفون */
div[data-testid="stAudioInput"] button:hover {
    transform: scale(1.08) !important;
    border-color: #5DCAA5 !important;
    box-shadow: 
        0 0 40px rgba(93, 202, 165, 0.4),
        inset 0 0 40px rgba(93, 202, 165, 0.1) !important;
}

/* أيقونة الميكروفون (تعديل الأيقونة الافتراضية) */
div[data-testid="stAudioInput"] button svg {
    width: 36px !important;
    height: 36px !important;
    fill: #5DCAA5 !important;
    stroke: #5DCAA5 !important;
    transition: transform 0.3s ease !important;
}

div[data-testid="stAudioInput"] button:hover svg {
    transform: scale(1.1) !important;
}

/* حالة التسجيل (عندما يكون الميكروفون نشطاً) */
div[data-testid="stAudioInput"] button[aria-pressed="true"] {
    background: linear-gradient(145deg, #5DCAA5, #2d7d46) !important;
    border-color: #5DCAA5 !important;
    animation: mic-pulse 1.5s infinite !important;
    box-shadow: 0 0 50px rgba(93, 202, 165, 0.6) !important;
}

div[data-testid="stAudioInput"] button[aria-pressed="true"] svg {
    fill: #ffffff !important;
    stroke: #ffffff !important;
}

@keyframes mic-pulse {
    0%, 100% {
        box-shadow: 0 0 30px rgba(93, 202, 165, 0.4);
    }
    50% {
        box-shadow: 0 0 70px rgba(93, 202, 165, 0.8);
    }
}

/* إخفاء النص الداخلي لـ st.audio_input */
div[data-testid="stAudioInput"] button span {
    font-size: 0 !important;
}

/* إظهار أيقونة الميكروفون فقط */
div[data-testid="stAudioInput"] button svg {
    font-size: 32px !important;
}

/* ============================================================
   نهاية تخصيص الميكروفون
   ============================================================ */

/* ====== صناديق الاختيار ====== */
.stSelectbox {
    border-radius: 12px !important;
}

/* ====== التباعد ====== */
.spacer {
    height: 0.5rem;
}

/* ====== نص التحميل ====== */
.stSpinner > div {
    color: #5DCAA5 !important;
}

/* ====== شريط التقدم ====== */
.stProgress > div > div {
    background: linear-gradient(90deg, #5DCAA5, #302b63) !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  الهيدر
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
    <div class="hero-name">HASSAN <span>NASSER</span></div>
    <div class="hero-sub">VOICE &amp; MULTI-DOMAIN SMART TRANSLATOR — 15+ SPECIALIZED FIELDS</div>
    <div class="hero-pills">
        <span class="pill pill-active">🎤 Voice Input</span>
        <span class="pill pill-active">Auto-Domain Detect</span>
        <span class="pill pill-muted">DeepL Precision</span>
        <span class="pill pill-muted">Cohere Transcribe</span>
        <span class="pill pill-muted">Faster-Whisper (Русский)</span>
    </div>
    <div class="lang-bar">
        <span class="ldot"></span><span class="ldot"></span><span class="ldot"></span>
        <span class="ldot"></span><span class="ldot"></span><span class="ldot"></span>
        <span class="ldot"></span><span class="ldot"></span>
        <span class="lang-bar-txt">8 languages — Chrome &amp; Safari supported</span>
    </div>
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
    "political":  {"emoji": "🏛️", "name_en": "Political",     "color": "#E63946"},
    "legal":      {"emoji": "⚖️", "name_en": "Legal",         "color": "#534AB7"},
    "economic":   {"emoji": "📈", "name_en": "Economic",      "color": "#F4A261"},
    "medical":    {"emoji": "🏥", "name_en": "Medical",       "color": "#2A9D8F"},
    "scientific": {"emoji": "🔬", "name_en": "Scientific",    "color": "#264653"},
    "engineering":{"emoji": "🏗️", "name_en": "Engineering",   "color": "#1D9E75"},
    "military":   {"emoji": "🎖️", "name_en": "Military",      "color": "#8B0000"},
    "educational":{"emoji": "📚", "name_en": "Educational",   "color": "#F4D03F"},
    "religious":  {"emoji": "🕌", "name_en": "Religious",     "color": "#6C3483"},
    "sports":     {"emoji": "⚽", "name_en": "Sports",        "color": "#E67E22"},
    "literary":   {"emoji": "📖", "name_en": "Literary",      "color": "#D81B60"},
    "it":         {"emoji": "💻", "name_en": "IT / Tech",     "color": "#00ACC1"},
    "environmental":{"emoji": "🌿", "name_en": "Environmental", "color": "#43A047"},
    "agricultural":{"emoji": "🌾", "name_en": "Agricultural",  "color": "#795548"},
    "media":      {"emoji": "📺", "name_en": "Media",         "color": "#5E35B1"},
    "tourism":    {"emoji": "✈️", "name_en": "Tourism",       "color": "#00838F"},
    "general":    {"emoji": "💬", "name_en": "General",       "color": "#6B7280"},
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

# ════════════════════════════════════════════════════════════
#  DOMAIN KEYWORDS
# ════════════════════════════════════════════════════════════
DOMAIN_KEYWORDS = {
    "political": ["minister", "government", "parliament", "political", "diplomatic", "treaty", "election", "policy", "president", "وزير", "حكومة", "برلمان", "سياسة", "دبلوماسي", "معاهدة", "انتخابات", "رئيس"],
    "legal": ["contract", "agreement", "clause", "legal", "court", "judgment", "law", "عقد", "اتفاق", "قانون", "محكمة", "حكم"],
    "economic": ["economic", "financial", "investment", "cost", "budget", "revenue", "profit", "loss", "اقتصاد", "مالية", "استثمار", "تكلفة", "ميزانية", "ربح"],
    "medical": ["doctor", "hospital", "treatment", "disease", "diagnosis", "surgery", "patient", "طبيب", "مستشفى", "علاج", "مرض", "تشخيص", "عملية", "مريض"],
    "scientific": ["research", "study", "experiment", "theory", "scientific", "technology", "data", "بحث", "دراسة", "تجربة", "نظرية", "علمي", "تقنية", "بيانات"],
    "engineering": ["engineering", "structural", "civil", "electrical", "mechanical", "concrete", "construction", "هندسة", "إنشائي", "مدني", "كهرباء", "ميكانيك", "خرسانة", "بناء"],
    "military": ["military", "army", "defense", "war", "weapon", "base", "جيش", "عسكري", "دفاع", "حرب", "سلاح", "قاعدة"],
    "educational": ["school", "university", "education", "teacher", "student", "exam", "مدرسة", "جامعة", "تعليم", "معلم", "طالب", "امتحان"],
    "religious": ["mosque", "church", "prayer", "Quran", "Bible", "religion", "faith", "مسجد", "كنيسة", "صلاة", "قرآن", "إنجيل", "دين"],
    "sports": ["sports", "football", "basketball", "tennis", "stadium", "team", "player", "رياضة", "كرة القدم", "كرة السلة", "تنس", "ملعب", "فريق"],
    "literary": ["literature", "story", "novel", "poetry", "writer", "author", "text", "أدب", "قصة", "رواية", "شعر", "كاتب", "نص"],
    "it": ["programming", "computer", "network", "software", "application", "website", "database", "برمجة", "حاسوب", "شبكة", "برنامج", "موقع", "قاعدة بيانات"],
    "environmental": ["environment", "pollution", "climate", "renewable", "solar", "wind", "بيئة", "تلوث", "مناخ", "متجددة", "شمسية", "رياح"],
    "agricultural": ["agriculture", "farm", "crop", "wheat", "rice", "trees", "irrigation", "زراعة", "مزرعة", "محصول", "قمح", "أرز", "أشجار"],
    "media": ["media", "journalism", "television", "radio", "news", "report", "إعلام", "صحافة", "تلفزيون", "إذاعة", "خبر", "تقرير"],
    "tourism": ["tourism", "hotel", "travel", "airport", "passport", "visa", "tour", "سياحة", "فندق", "سفر", "مطار", "جواز", "تأشيرة"],
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
#  إدارة المفاتيح
# ════════════════════════════════════════════════════════════
if not st.session_state.deepl_api_key or not st.session_state.cohere_api_key:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f0c29, #302b63); border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem; text-align: center;">
        <div style="font-size: 24px; font-weight: 700; color: #ffffff; margin-bottom: 8px;">🔑 API Keys Required</div>
        <div style="font-size: 14px; color: rgba(255,255,255,0.6); margin-bottom: 20px;">
            Please enter your API keys below. They will be saved for this session only.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.deepl_api_key:
            deepl_input = st.text_input("🔐 DeepL API Key", type="password", placeholder="e.g., abc...xyz:fx")
            if deepl_input:
                st.session_state.deepl_api_key = deepl_input
                st.success("✅ DeepL key saved!")
                st.rerun()
        else:
            st.success("✅ DeepL API Key: OK")
    
    with col2:
        if not st.session_state.cohere_api_key:
            cohere_input = st.text_input("🔐 Cohere API Key", type="password", placeholder="e.g., abcd-1234-efgh-5678")
            if cohere_input:
                st.session_state.cohere_api_key = cohere_input
                st.success("✅ Cohere key saved!")
                st.rerun()
        else:
            st.success("✅ Cohere API Key: OK")
    
    st.info("💡 Your keys are stored only in your browser session.")
    st.stop()

# ════════════════════════════════════════════════════════════
#  TRANSLATION ENGINE (DeepL)
# ════════════════════════════════════════════════════════════
def translate_deepl(text, target_lang):
    if not st.session_state.deepl_api_key:
        return None, "No DeepL API key configured"
        
    tl = target_lang.upper()
    
    if st.session_state.deepl_api_key.endswith(":fx"):
        endpoint = "https://api-free.deepl.com/v2/translate"
    else:
        endpoint = "https://api.deepl.com/v2/translate"
        
    try:
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"DeepL-Auth-Key {st.session_state.deepl_api_key}"},
            data={"text": text, "target_lang": tl},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"], None
        else:
            return None, f"DeepL error {resp.status_code}: {resp.text}"
    except Exception as e:
        return None, f"Request error: {str(e)}"

def fetch_ai_translation(text, target_lang):
    result, error = translate_deepl(text, target_lang)
    if result:
        return result, "DeepL"
    return None, error

# ════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT (Cohere Transcribe)
# ════════════════════════════════════════════════════════════
def speech_to_text_cohere(audio_bytes, language_code="auto"):
    if not st.session_state.cohere_api_key:
        return None, "مفتاح Cohere API غير موجود."

    try:
        fields = OrderedDict()
        
        if language_code == "auto" or language_code is None:
            lang = "en"
        else:
            lang = language_code
        
        fields['language'] = lang
        fields['model'] = 'cohere-transcribe-03-2026'
        fields['file'] = ('audio.wav', audio_bytes, 'audio/wav')

        encoder = MultipartEncoder(fields=fields)

        response = requests.post(
            "https://api.cohere.com/v2/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {st.session_state.cohere_api_key}",
                "Content-Type": encoder.content_type,
            },
            data=encoder,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            text = result.get("text", "").strip()
            if text:
                return text, "Cohere Transcribe"
            else:
                return None, "لم يتم التعرف على أي كلام"
        else:
            return None, f"Cohere error {response.status_code}: {response.text}"

    except Exception as e:
        return None, f"خطأ في Cohere: {str(e)}"

# ════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT (Faster-Whisper Medium للروسية)
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_whisper_model():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("medium", device="cpu", compute_type="int8")
    except ImportError:
        st.error("⚠️ Faster-Whisper غير مثبت. قم بتشغيل: pip install faster-whisper")
        return None
    except Exception as e:
        st.error(f"⚠️ فشل تحميل نموذج Faster-Whisper: {str(e)}")
        return None

def speech_to_text_whisper(audio_bytes):
    model = load_whisper_model()
    if not model:
        return None, "⚠️ فشل تحميل نموذج التعرف على الصوت"
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        segments, info = model.transcribe(
            tmp_path,
            language="ru",
            beam_size=5,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False
        )
        
        text = " ".join(segment.text for segment in segments).strip()
        
        if text:
            return text, "Faster-Whisper Medium (Русский)"
        else:
            return None, "لم يتم التعرف على أي كلام بالروسية"
    except Exception as e:
        return None, f"خطأ في التعرف: {str(e)}"
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except:
            pass

# ════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT (المحرك الذكي)
# ════════════════════════════════════════════════════════════
def speech_to_text(audio_bytes, language_code="auto"):
    if language_code == "ru":
        return speech_to_text_whisper(audio_bytes)
    else:
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

# ====== اختيار اللغات ======
st.markdown("### 🌐 Language Selection")

col_left, col_mid, col_right = st.columns([1, 0.15, 1])

with col_left:
    source_lang_name = st.selectbox("From Language", lang_list, index=src_idx, key="src_lang")

with col_mid:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("⇄", help="Swap languages", use_container_width=True):
        swap_languages()

with col_right:
    target_lang_name = st.selectbox("To Language", tgt_options, index=tgt_idx, key="tgt_lang")

st.session_state.source_lang = source_lang_name
st.session_state.target_lang = target_lang_name

source_lang = languages_dict[source_lang_name]
target_lang = languages_dict[target_lang_name]

# ====== اختيار النمط ======
st.markdown("### 🎯 Translation Style / Domain")
col_style1, col_style2 = st.columns([1, 2])

with col_style1:
    selected_style_label = st.selectbox("Style / Domain", style_list, index=style_idx, key="style_sel")

with col_style2:
    selected_domain = STYLE_OPTIONS[selected_style_label]
    if selected_domain and selected_domain != "general":
        dinfo = DOMAINS[selected_domain]
        st.markdown(f"""
        <div style='margin-top: 26px; font-size: 14px; color: {dinfo['color']}; font-weight: 600;'>
            {dinfo['emoji']} Priority: {dinfo['name_en']}
        </div>
        """, unsafe_allow_html=True)
    elif selected_domain == "general":
        st.markdown("<div style='margin-top: 26px; font-size: 14px; color: #6B7280;'>💬 General / Standard</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='margin-top: 26px; font-size: 14px; color: #6B7280;'>🔍 Auto-detecting domain...</div>", unsafe_allow_html=True)

st.session_state.selected_style = selected_style_label

# ====== تقسيم ======
st.markdown("---")

# ====== VOICE INPUT (مع ميكروفون أسطوري) ======
if source_lang == "ru":
    engine_info = "⚡ يستخدم **Faster-Whisper Medium** (دقة عالية جداً للروسية)"
elif source_lang == "auto":
    engine_info = "⚡ يستخدم **Cohere Transcribe** (كشف تلقائي للغة)"
else:
    engine_info = f"⚡ يستخدم **Cohere Transcribe** (لغة محددة: {source_lang_name})"

st.markdown(f"""
<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.2rem; margin-bottom: 1.2rem;">
    <div style="font-size: 15px; font-weight: 700; color: #1a1a2e; margin-bottom: 4px;">🎤 Voice Input</div>
    <div style="font-size: 13px; color: #6b7280;">
        اضغط على زر الميكروفون الأسطوري 🎙️، تحدث، وسيتم التعرف على صوتك تلقائياً.
        <br>{engine_info}
    </div>
</div>
""", unsafe_allow_html=True)

# هذا هو الميكروفون الأسطوري
audio_value = st.audio_input("🎙️ سجل رسالة صوتية", key="audio_input")

if audio_value:
    with st.spinner("⏳ جاري التعرف على الصوت..."):
        audio_bytes = audio_value.getvalue()
        recognized_text, engine_used = speech_to_text(audio_bytes, source_lang)
        
        if recognized_text:
            st.success(f"✅ تم التعرف ({engine_used}): {recognized_text}")
            st.session_state.input_text = recognized_text
            
            if st.button("ترجم الآن 🚀", type="primary", use_container_width=True):
                with st.spinner("⏳ جاري الترجمة..."):
                    translated_text, engine = fetch_ai_translation(recognized_text, target_lang)
                    if translated_text:
                        st.session_state.translated_text = translated_text
                        st.markdown("### 📝 الترجمة")
                        st.markdown(f">>> {translated_text}")
                    else:
                        st.error(f"فشلت الترجمة: {engine}")
        else:
            st.error(f"فشل التعرف على الصوت: {engine_used}")

# ====== TEXT INPUT ======
st.markdown("### ✍️ Text Input")

input_text = st.text_area(
    "Enter text to translate",
    height=120,
    placeholder="Type, paste, or your voice text will appear here...",
    value=st.session_state.input_text,
    key="input_text_area"
)

if input_text != st.session_state.input_text:
    st.session_state.input_text = input_text

if input_text.strip():
    detected = detect_domains(input_text)
    if detected:
        badges = ""
        for d in detected[:3]:
            dn = DOMAINS[d]["name_en"]
            emoji = DOMAINS[d]["emoji"]
            css_class = f"db-{d}" if d in DOMAINS else "db-gen"
            badges += f'<span class="domain-badge {css_class}">{emoji} {dn}</span>'
        st.markdown(f'<div class="detected-box">🔍 <b>Auto-Detected Context:</b><br><div style="margin-top:6px;">{badges}</div></div>', unsafe_allow_html=True)
    else:
        if selected_style_label == "Auto-Detect":
            st.markdown('<div class="detected-box" style="border-left-color: #6B7280; background: #F3F4F6; color: #4B5563;">💬 <b>Context:</b> General / Standard</div>', unsafe_allow_html=True)

# ====== زر الترجمة اليدوي ======
if st.button("Translate 🚀", type="primary", use_container_width=True):
    if not st.session_state.deepl_api_key:
        st.error("❌ DeepL API key missing.")
    elif not input_text.strip():
        st.warning("Please enter some text to translate.")
    else:
        with st.spinner("Translating..."):
            translation_result, source_engine = fetch_ai_translation(input_text, target_lang)

            if translation_result:
                active_domain = "general"
                if selected_domain and selected_domain != "general":
                    active_domain = selected_domain
                elif detected:
                    active_domain = detected[0]

                final_translation = translation_result

                card_class = f"rcard-{active_domain}" if active_domain in DOMAINS else "rcard-gen"
                label_class = f"rlabel-{active_domain}" if active_domain in DOMAINS else "rlabel-gen"
                domain_info = DOMAINS.get(active_domain, DOMAINS["general"])

                st.markdown("### 📝 Translation Result")
                
                card_html = f"""
                <div class="rcard {card_class}">
                    <div class="rlabel {label_class}">
                        {domain_info['emoji']} {domain_info['name_en'].upper()} TRANSLATION
                    </div>
                    <div style="margin-bottom: 12px;">
                        <span class="api-badge api-deepl">⚡ {source_engine}</span>
                        <span class="api-badge api-cohere">🎤 Cohere Transcribe</span>
                        <span class="api-badge api-whisper">🎙️ Faster-Whisper</span>
                    </div>
                    <div class="rtext">{final_translation}</div>
                </div>
                """
                
                st.markdown(card_html, unsafe_allow_html=True)
                st.code(final_translation, language=None)
            else:
                st.markdown(f"""
                <div class="error-box">
                    <b>Translation Failed:</b> {source_engine}
                    <br><span style="font-size:12px;">Please check your DeepL API key and internet connection.</span>
                </div>
                """, unsafe_allow_html=True)
