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
#  CSS — Premium Dark-Glass Design (معدّل للهواتف)
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ====== Reset & Base ====== */
#MainMenu, footer, header { visibility: hidden; }

*, *::before, *::after { box-sizing: border-box; }

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
    padding-top: 1rem !important;
    padding-bottom: 1.5rem !important;
    max-width: 680px !important;
    position: relative;
    z-index: 1;
}

/* ====== العنوان الرئيسي (مصغر) ====== */
.app-header {
    text-align: center;
    padding: 1rem 0.5rem 0.8rem;
    position: relative;
}

.app-header .brand {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.35em;
    color: #4ECBA0;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
    display: block;
}

.app-header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 28px;
    font-weight: 700;
    color: #f0f4ff;
    margin: 0 0 0.2rem 0;
    line-height: 1.2;
    letter-spacing: -0.02em;
}

.app-header h1 .accent {
    color: #4ECBA0;
    position: relative;
}

.app-header .subtitle {
    font-size: 11px;
    color: rgba(180,200,230,0.55);
    margin: 0;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 500;
}

/* ====== بطاقات الزجاج (مضغوطة) ====== */
.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 0.8rem;
    margin-bottom: 0.8rem;
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

/* ====== منطقة الميكروفون (مصغرة جداً) ====== */
.mic-zone {
    text-align: center;
    padding: 0.3rem 0;
}

.mic-icon-wrap {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 52px;          /* <-- تم التصغير من 80px */
    height: 52px;         /* <-- تم التصغير من 80px */
    border-radius: 50%;
    background: radial-gradient(circle, rgba(78,203,160,0.15) 0%, rgba(78,203,160,0.04) 70%);
    border: 1.5px solid rgba(78,203,160,0.25);
    font-size: 24px;      /* <-- تم التصغير من 36px */
    margin-bottom: 0.2rem;
    box-shadow: 0 0 20px rgba(78,203,160,0.08), inset 0 1px 0 rgba(78,203,160,0.12);
}

.mic-hint {
    font-size: 11px;
    color: rgba(180,200,230,0.5);
    margin: 0;
    font-weight: 400;
}

/* ====== Selectbox ====== */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
    color: #e8f0ff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    transition: border-color 0.2s;
    padding: 0px 8px !important;
    min-height: 32px !important;
}

.stSelectbox > div > div:hover {
    border-color: rgba(78,203,160,0.5) !important;
}

.stSelectbox > div > div:focus-within {
    border-color: #4ECBA0 !important;
    box-shadow: 0 0 0 3px rgba(78,203,160,0.12) !important;
}

.stSelectbox label {
    font-size: 10px !important;
    font-weight: 600 !important;
    color: rgba(78,203,160,0.75) !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    margin-bottom: 2px !important;
}

/* ====== الأزرار ====== */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 0.5rem 1rem !important;
    background: linear-gradient(135deg, #4ECBA0 0%, #2fa87a 100%) !important;
    color: #0a1520 !important;
    border: none !important;
    width: 100% !important;
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: 0.03em !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 16px rgba(78,203,160,0.2) !important;
    min-height: 36px !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #5ed9b0 0%, #3dbf8a 100%) !important;
    box-shadow: 0 6px 24px rgba(78,203,160,0.35) !important;
    transform: translateY(-1px) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* زر المبادلة */
.stButton:has(button[title="Swap"]) > button,
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.07) !important;
    color: rgba(200,220,255,0.8) !important;
    box-shadow: none !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    font-size: 16px !important;
    padding: 0.2rem !important;
    min-height: 32px !important;
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
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 14px !important;
    color: #e8f0ff !important;
    font-size: 14px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 10px 14px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    line-height: 1.5 !important;
    min-height: 70px !important;
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
    border-radius: 14px;
    padding: 0.8rem 1rem;
    border: 1px solid rgba(78,203,160,0.2);
    margin-top: 0.5rem;
    position: relative;
    overflow: hidden;
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
    margin-bottom: 4px;
    display: block;
}

.result-box .text {
    font-size: 15px;
    color: #e8f0ff;
    line-height: 1.6;
    font-weight: 400;
}

/* ====== سياق المجال ====== */
.context {
    background: rgba(78,203,160,0.07);
    border-radius: 10px;
    padding: 5px 10px;
    font-size: 11px;
    color: rgba(78,203,160,0.9);
    border: 1px solid rgba(78,203,160,0.15);
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}

.tag {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 2px 8px;
    border-radius: 16px;
    font-size: 9px;
    font-weight: 600;
    margin-right: 4px;
    letter-spacing: 0.03em;
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
.stSuccess {
    background: rgba(78,203,160,0.08) !important;
    border: 1px solid rgba(78,203,160,0.25) !important;
    border-radius: 12px !important;
    color: #a8f0d8 !important;
    padding: 6px 12px !important;
    font-size: 13px !important;
}

.stError, [data-baseweb="notification"][kind="negative"] {
    background: rgba(239,68,68,0.08) !important;
    border: 1px solid rgba(239,68,68,0.25) !important;
    border-radius: 12px !important;
    padding: 6px 12px !important;
    font-size: 13px !important;
}

.stWarning {
    background: rgba(245,158,11,0.08) !important;
    border: 1px solid rgba(245,158,11,0.2) !important;
    border-radius: 12px !important;
    padding: 6px 12px !important;
    font-size: 13px !important;
}

.stCode, code, pre {
    background: rgba(0,0,0,0.35) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    color: #a8f0d8 !important;
    font-size: 12px !important;
    padding: 6px 10px !important;
}

hr {
    margin: 0.8rem 0 !important;
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(78,203,160,0.2), transparent) !important;
}

.stSpinner > div {
    border-color: #4ECBA0 !important;
}

.stTextInput input {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    color: #e8f0ff !important;
    font-family: 'Inter', sans-serif !important;
    padding: 6px 10px !important;
    font-size: 13px !important;
}

.stTextInput input:focus {
    border-color: rgba(78,203,160,0.5) !important;
    box-shadow: 0 0 0 3px rgba(78,203,160,0.1) !important;
}

.stTextInput label {
    color: rgba(78,203,160,0.75) !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

.stCheckbox label {
    color: rgba(180,200,230,0.8) !important;
    font-size: 13px !important;
}

.stAudioInput {
    border-radius: 40px !important;
}

.stCaption {
    color: rgba(150,175,220,0.45) !important;
    font-size: 10px !important;
}

[data-testid="column"] {
    padding: 0 4px !important;
}

.section-heading {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: rgba(150,185,230,0.5);
    margin: 0.8rem 0 0.4rem;
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

/* ====== تحسينات إضافية للهواتف ====== */
@media (max-width: 600px) {
    .block-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    .app-header h1 {
        font-size: 22px !important;
    }
    .app-header .subtitle {
        font-size: 9px !important;
    }
    .mic-icon-wrap {
        width: 44px !important;
        height: 44px !important;
        font-size: 20px !important;
    }
    .glass-card {
        padding: 0.6rem !important;
    }
    .result-box .text {
        font-size: 14px !important;
    }
    .section-heading {
        font-size: 8px !important;
    }
    .stSelectbox > div > div {
        font-size: 12px !important;
        min-height: 28px !important;
    }
    .stButton > button {
        font-size: 12px !important;
        padding: 0.4rem 0.8rem !important;
        min-height: 32px !important;
    }
    textarea {
        font-size: 13px !important;
        min-height: 60px !important;
        padding: 8px 10px !important;
    }
    .mic-hint {
        font-size: 10px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  العنوان الرئيسي
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
    <div class="glass-card" style="text-align:center; padding: 1.5rem 1rem;">
        <div style="font-size:28px; margin-bottom:0.5rem;">🔐</div>
        <div style="font-family:'Space Grotesk',sans-serif; font-size:16px; font-weight:700;
                    color:#e8f0ff; margin-bottom:0.2rem;">Connect API Keys</div>
        <div style="font-size:10px; color:rgba(150,185,230,0.5); letter-spacing:0.04em;">
            Stored in your browser session only
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.deepl_api_key:
            deepl_input = st.text_input("DeepL Key", type="password", placeholder="abc...xyz:fx")
            if deepl_input:
                st.session_state.deepl_api_key = deepl_input
                st.success("✅ Connected")
                st.rerun()
        else:
            st.success("✅ DeepL Active")
    
    with col2:
        if not st.session_state.cohere_api_key:
            cohere_input = st.text_input("Cohere Key", type="password", placeholder="abcd-1234-efgh-5678")
            if cohere_input:
                st.session_state.cohere_api_key = cohere_input
                st.success("✅ Connected")
                st.rerun()
        else:
            st.success("✅ Cohere Active")
    
    st.caption("💡 Keys are never stored on any server — session only.")
    st.stop()

# ════════════════════════════════════════════════════════════
#  TRANSLATION ENGINE
# ════════════════════════════════════════════════════════════
def translate_deepl(text, target_lang):
    if not st.session_state.deepl_api_key:
        return None, "No API key configured"
    tl = target_lang.upper()
    endpoint = "https://api-free.deepl.com/v2/translate" if st.session_state.deepl_api_key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    try:
        resp = requests.post(endpoint, headers={"Authorization": f"DeepL-Auth-Key {st.session_state.deepl_api_key}"}, data={"text": text, "target_lang": tl}, timeout=15)
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"], None
        else:
            return None, f"DeepL error {resp.status_code}: {resp.text}"
    except Exception as e:
        return None, f"Request error: {str(e)}"

def fetch_ai_translation(text, target_lang):
    result, error = translate_deepl(text, target_lang)
    if result:
        return result, "Translator"
    return None, error

# ════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT (Cohere)
# ════════════════════════════════════════════════════════════
def speech_to_text_cohere(audio_bytes, language_code="auto"):
    if not st.session_state.cohere_api_key:
        return None, "مفتاح API غير موجود."

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
                "Content-Type": encoder.content_type,
            },
            data=encoder,
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            text = result.get("text", "").strip()
            if text:
                return text, "Speech Recognition"
            else:
                return None, "لم يتم التعرف على أي كلام"
        else:
            return None, f"Cohere error {response.status_code}: {response.text}"
    except Exception as e:
        return None, f"خطأ: {str(e)}"

# ════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT (Faster-Whisper للروسية)
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_whisper_model():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("small", device="cpu", compute_type="int8")
    except ImportError:
        return None
    except Exception:
        return None

def speech_to_text_whisper(audio_bytes):
    model = load_whisper_model()
    if not model:
        return None, "⚠️ نموذج التعرف غير متاح"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        segments, info = model.transcribe(tmp_path, language="ru", beam_size=5, temperature=0.0, vad_filter=True)
        text = " ".join(segment.text for segment in segments).strip()
        if text:
            return text, "Speech Recognition"
        else:
            return None, "لم يتم التعرف على أي كلام"
    except Exception as e:
        return None, f"خطأ: {str(e)}"
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except:
            pass

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
#  UI - بسيط وجذاب (مع تصغير الميكروفون)
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

st.session_state.source_lang = source_lang_name
st.session_state.target_lang = target_lang_name

source_lang = languages_dict[source_lang_name]
target_lang = languages_dict[target_lang_name]

# ====== النمط ======
st.markdown('<div class="section-heading">Domain Style</div>', unsafe_allow_html=True)
selected_style_label = st.selectbox("Style", style_list, index=style_idx, label_visibility="collapsed")
selected_domain = STYLE_OPTIONS[selected_style_label]
st.session_state.selected_style = selected_style_label

# ====== الميكروفون (مصغر) ======
st.markdown("---")
st.markdown('<div class="section-heading">Voice Input</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="glass-card mic-zone" style="padding: 0.5rem 0.8rem;">
    <div class="mic-icon-wrap">🎤</div>
    <div style="font-size:13px; font-weight:600; color:#e8f0ff; margin-bottom:1px;">
        Record
    </div>
    <div class="mic-hint">Click to speak</div>
</div>
""", unsafe_allow_html=True)

audio_value = st.audio_input("")

if audio_value:
    with st.spinner("⏳ جاري التعرف..."):
        audio_bytes = audio_value.getvalue()
        recognized_text, engine_used = speech_to_text(audio_bytes, source_lang)
        if recognized_text:
            st.success(f"✅ {recognized_text}")
            st.session_state.input_text = recognized_text
            if st.button("Translate ✦", use_container_width=True):
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

# ====== نص مكتوب ======
st.markdown("---")
st.markdown('<div class="section-heading">Text Input</div>', unsafe_allow_html=True)

input_text = st.text_area(
    "",
    height=80,
    placeholder="اكتب أو الصق النص هنا...",
    value=st.session_state.input_text,
    key="input_text_area"
)

if input_text != st.session_state.input_text:
    st.session_state.input_text = input_text

# ====== سياق ======
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

# ====== زر الترجمة ======
if st.button("Translate ✦", use_container_width=True, key="translate_btn"):
    if not st.session_state.deepl_api_key:
        st.error("❌ API key missing.")
    elif not input_text.strip():
        st.warning("الرجاء إدخال نص للترجمة.")
    else:
        with st.spinner("جاري الترجمة..."):
            translation_result, source_engine = fetch_ai_translation(input_text, target_lang)

            if translation_result:
                active_domain = "general"
                if selected_domain and selected_domain != "general":
                    active_domain = selected_domain
                elif detected:
                    active_domain = detected[0]

                final_translation = translation_result

                st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="result-box">
                    <span class="label">✦ Translation</span>
                    <div class="text">{final_translation}</div>
                </div>
                """, unsafe_allow_html=True)
                st.code(final_translation, language=None)
            else:
                st.error(f"❌ {translation_result}")

# ====== Footer ======
st.markdown("""
<div style="text-align:center; padding: 1.5rem 0 0.5rem; color:rgba(100,130,170,0.3); font-size:10px;
            letter-spacing:0.12em; font-family:Inter,sans-serif; text-transform:uppercase;">
    HN TRANSLATOR &nbsp;·&nbsp; Voice Translation Suite
</div>
""", unsafe_allow_html=True)
