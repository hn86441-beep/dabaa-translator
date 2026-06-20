import streamlit as st
import requests
import os
import json
from pathlib import Path
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict

st.set_page_config(
    page_title="HASSAN NASSER | Voice Translator",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ════════════════════════════════════════════════════════════
#  CSS - واجهة مودرن (بطاقات شفافة + تدرجات)
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ====== الخطوط ====== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

#MainMenu, footer, header {
    visibility: hidden;
}

/* ====== الخلفية ====== */
.stApp {
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 900px;
}

/* ====== الهيدر ====== */
.glass-header {
    background: rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 20px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 8px 32px rgba(0,0,0,0.06);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
}

.glass-header .logo {
    display: flex;
    align-items: center;
    gap: 12px;
}

.glass-header .logo-icon {
    font-size: 32px;
    background: linear-gradient(135deg, #1a1a2e, #302b63);
    width: 50px;
    height: 50px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 22px;
}

.glass-header .logo-text {
    font-size: 22px;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.5px;
}

.glass-header .logo-text span {
    color: #5DCAA5;
}

.glass-header .logo-sub {
    font-size: 11px;
    color: #9ca3af;
    font-weight: 400;
    letter-spacing: 0.06em;
}

.glass-header .badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}

.glass-header .badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.04em;
    background: rgba(93,202,165,0.12);
    color: #5DCAA5;
    border: 1px solid rgba(93,202,165,0.15);
}

/* ====== بطاقات شفافة ====== */
.glass-card {
    background: rgba(255, 255, 255, 0.55);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-radius: 20px;
    padding: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 4px 24px rgba(0,0,0,0.04);
    transition: all 0.3s ease;
}

.glass-card:hover {
    box-shadow: 0 8px 40px rgba(0,0,0,0.08);
}

/* ====== ميكروفون أسطوري ====== */
.mic-section {
    text-align: center;
    padding: 0.5rem 0;
}

.mic-icon-wrapper {
    display: inline-block;
    position: relative;
    margin-bottom: 8px;
}

.mic-icon-wrapper .pulse-ring {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: rgba(93, 202, 165, 0.08);
    animation: pulse-ring 2.5s ease-in-out infinite;
    pointer-events: none;
}

@keyframes pulse-ring {
    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.4; }
    50% { transform: translate(-50%, -50%) scale(1.4); opacity: 0; }
}

.mic-icon-wrapper .mic-circle {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1a1a2e, #302b63);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    z-index: 1;
    box-shadow: 0 8px 32px rgba(48, 43, 99, 0.25);
    transition: all 0.3s ease;
}

.mic-icon-wrapper .mic-circle:hover {
    transform: scale(1.05);
    box-shadow: 0 12px 48px rgba(48, 43, 99, 0.35);
}

.mic-icon-wrapper .mic-circle .mic-emoji {
    font-size: 36px;
}

.mic-title {
    font-size: 18px;
    font-weight: 600;
    color: #1a1a2e;
    margin-top: 4px;
}

.mic-sub {
    font-size: 13px;
    color: #9ca3af;
}

/* ====== حقل الميكروفون ====== */
.stAudioInput {
    border-radius: 60px !important;
    border: 2px dashed rgba(209, 213, 219, 0.6) !important;
    padding: 6px 16px !important;
    background: rgba(255,255,255,0.5) !important;
    backdrop-filter: blur(8px) !important;
    transition: all 0.3s ease !important;
    max-width: 340px !important;
    margin: 0 auto !important;
}

.stAudioInput:hover {
    border-color: #5DCAA5 !important;
    box-shadow: 0 0 0 4px rgba(93,202,165,0.1) !important;
}

.stAudioInput > div {
    justify-content: center !important;
}

/* ====== الأزرار ====== */
.stButton > button {
    border-radius: 60px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 0.6rem 2rem !important;
    transition: all 0.3s ease !important;
    background: linear-gradient(135deg, #1a1a2e, #302b63) !important;
    color: white !important;
    border: none !important;
    width: auto !important;
    min-width: 140px !important;
    box-shadow: 0 4px 16px rgba(48, 43, 99, 0.2) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(48, 43, 99, 0.3) !important;
}

/* ====== حقول الإدخال ====== */
textarea {
    border-radius: 16px !important;
    border: 1px solid rgba(229, 231, 235, 0.6) !important;
    font-size: 14px !important;
    transition: all 0.3s ease !important;
    padding: 12px 16px !important;
    background: rgba(255,255,255,0.4) !important;
    backdrop-filter: blur(8px) !important;
}

textarea:focus {
    border-color: #5DCAA5 !important;
    box-shadow: 0 0 0 4px rgba(93,202,165,0.1) !important;
    background: rgba(255,255,255,0.7) !important;
}

/* ====== صناديق الاختيار ====== */
.stSelectbox > div > div {
    border-radius: 12px !important;
    border-color: rgba(229, 231, 235, 0.6) !important;
    background: rgba(255,255,255,0.4) !important;
    backdrop-filter: blur(8px) !important;
}

.stSelectbox label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #6b7280 !important;
}

/* ====== نتيجة الترجمة ====== */
.result-glass {
    background: rgba(255, 255, 255, 0.5);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-radius: 16px;
    padding: 1rem 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-left: 4px solid #5DCAA5;
    margin-top: 0.5rem;
}

.result-glass .rlabel {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #9ca3af;
    margin-bottom: 4px;
}

.result-glass .rtext {
    font-size: 15px;
    color: #1f2937;
    line-height: 1.7;
}

/* ====== سياق ====== */
.context-glass {
    background: rgba(240, 253, 244, 0.5);
    backdrop-filter: blur(8px);
    border-radius: 12px;
    padding: 8px 14px;
    font-size: 12px;
    color: #065f46;
    margin-bottom: 0.8rem;
    border-left: 3px solid #5DCAA5;
}

/* ====== شارات ====== */
.badge-sm {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 600;
    margin-right: 4px;
}
.badge-deepl { background: #0F2B46; color: #8ECAE6; }
.badge-cohere { background: #1a1a2e; color: #8ECAE6; }
.badge-whisper { background: #4a90d9; color: #fff; }

/* ====== أوسمة ====== */
.tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 600;
    margin-right: 4px;
    margin-bottom: 3px;
}
.tag-pol { background: #E63946; color: white; }
.tag-leg { background: #534AB7; color: white; }
.tag-eco { background: #F4A261; color: #3E2723; }
.tag-med { background: #2A9D8F; color: white; }
.tag-sci { background: #264653; color: white; }
.tag-eng { background: #1D9E75; color: white; }
.tag-mil { background: #8B0000; color: white; }
.tag-edu { background: #F4D03F; color: #3E2723; }
.tag-rel { background: #6C3483; color: white; }
.tag-spt { background: #E67E22; color: white; }
.tag-lit { background: #D81B60; color: white; }
.tag-it  { background: #00ACC1; color: white; }
.tag-env { background: #43A047; color: white; }
.tag-agr { background: #795548; color: white; }
.tag-tour { background: #00838F; color: white; }
.tag-gen { background: #6B7280; color: white; }

/* ====== خطأ ====== */
.error-glass {
    background: rgba(254, 226, 226, 0.5);
    backdrop-filter: blur(8px);
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 13px;
    color: #991b1b;
    border-left: 3px solid #ef4444;
}

/* ====== فواصل ====== */
hr {
    margin: 1.2rem 0 !important;
    opacity: 0.2 !important;
    border-color: #d1d5db !important;
}

/* ====== رسائل النجاح ====== */
.stSuccess {
    background: rgba(240, 253, 244, 0.5) !important;
    backdrop-filter: blur(8px) !important;
    border-radius: 12px !important;
    border-left: 3px solid #5DCAA5 !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  الهيدر
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="glass-header">
    <div class="logo">
        <div class="logo-icon">🎤</div>
        <div>
            <div class="logo-text">HASSAN <span>NASSER</span></div>
            <div class="logo-sub">VOICE &amp; MULTI-DOMAIN TRANSLATOR</div>
        </div>
    </div>
    <div class="badges">
        <span class="badge">🎤 Voice</span>
        <span class="badge">🤖 AI</span>
        <span class="badge">🌍 8 Languages</span>
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
    <div style="text-align:center;padding:2rem 0;">
        <h3 style="font-weight:600;color:#1a1a2e;">🔑 API Keys Required</h3>
        <p style="color:#6b7280;font-size:13px;">Enter your keys below. They will be saved for this session.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.deepl_api_key:
            deepl_input = st.text_input("DeepL API Key", type="password", placeholder="abc...xyz:fx")
            if deepl_input:
                st.session_state.deepl_api_key = deepl_input
                st.success("✅ Saved!")
                st.rerun()
        else:
            st.success("✅ DeepL: OK")
    
    with col2:
        if not st.session_state.cohere_api_key:
            cohere_input = st.text_input("Cohere API Key", type="password", placeholder="abcd-1234-efgh-5678")
            if cohere_input:
                st.session_state.cohere_api_key = cohere_input
                st.success("✅ Saved!")
                st.rerun()
        else:
            st.success("✅ Cohere: OK")
    
    st.caption("💡 Keys are stored only in your browser session.")
    st.stop()

# ════════════════════════════════════════════════════════════
#  TRANSLATION ENGINE
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
#  SPEECH-TO-TEXT (Cohere)
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
        
        segments, info = model.transcribe(
            tmp_path,
            language="ru",
            beam_size=5,
            temperature=0.0,
            vad_filter=True
        )
        
        text = " ".join(segment.text for segment in segments).strip()
        
        if text:
            return text, "Faster-Whisper"
        else:
            return None, "لم يتم التعرف على أي كلام بالروسية"
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
#  UI - مودرن
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
st.markdown("### 🌐 Languages")

col_left, col_mid, col_right = st.columns([1, 0.15, 1])

with col_left:
    source_lang_name = st.selectbox("From", lang_list, index=src_idx)

with col_mid:
    st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
    if st.button("⇄", help="Swap", use_container_width=True):
        swap_languages()

with col_right:
    target_lang_name = st.selectbox("To", tgt_options, index=tgt_idx)

st.session_state.source_lang = source_lang_name
st.session_state.target_lang = target_lang_name

source_lang = languages_dict[source_lang_name]
target_lang = languages_dict[target_lang_name]

# ====== النمط ======
selected_style_label = st.selectbox("Style", style_list, index=style_idx)
selected_domain = STYLE_OPTIONS[selected_style_label]
st.session_state.selected_style = selected_style_label

# ====== بطاقة الميكروفون ======
st.markdown("---")

if source_lang == "ru":
    engine_info = "⚡ Faster-Whisper (دقة عالية للروسية)"
elif source_lang == "auto":
    engine_info = "⚡ Cohere (كشف تلقائي)"
else:
    engine_info = f"⚡ Cohere ({source_lang_name})"

st.markdown(f"""
<div class="glass-card">
    <div class="mic-section">
        <div class="mic-icon-wrapper">
            <div class="pulse-ring"></div>
            <div class="mic-circle">
                <span class="mic-emoji">🎤</span>
            </div>
        </div>
        <div class="mic-title">سجل رسالتك الصوتية</div>
        <div class="mic-sub">{engine_info}</div>
    </div>
</div>
""", unsafe_allow_html=True)

audio_value = st.audio_input("")

if audio_value:
    with st.spinner("⏳ جاري التعرف..."):
        audio_bytes = audio_value.getvalue()
        recognized_text, engine_used = speech_to_text(audio_bytes, source_lang)
        
        if recognized_text:
            st.success(f"✅ {engine_used}: {recognized_text}")
            st.session_state.input_text = recognized_text
            
            if st.button("ترجم 🚀", use_container_width=True):
                with st.spinner("⏳ جاري الترجمة..."):
                    translated_text, engine = fetch_ai_translation(recognized_text, target_lang)
                    if translated_text:
                        st.session_state.translated_text = translated_text
                        st.markdown("### 📝 الترجمة")
                        st.markdown(f"""
                        <div class="result-glass">
                            <div class="rlabel">🎯 نتيجة الترجمة</div>
                            <div class="rtext">{translated_text}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.code(translated_text, language=None)
                    else:
                        st.error(f"❌ {engine}")
        else:
            st.error(f"❌ {engine_used}")

# ====== نص مكتوب ======
st.markdown("---")
st.markdown("### ✍️ أو اكتب النص")

input_text = st.text_area(
    "",
    height=100,
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
        st.markdown(f'<div class="context-glass">🔍 {badges}</div>', unsafe_allow_html=True)

# ====== زر الترجمة ======
if st.button("ترجم 🚀", use_container_width=True, key="translate_btn"):
    if not st.session_state.deepl_api_key:
        st.error("❌ DeepL API key missing.")
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

                st.markdown("### 📝 النتيجة")
                st.markdown(f"""
                <div class="result-glass">
                    <div class="rlabel">🎯 نتيجة الترجمة</div>
                    <div class="rtext">{final_translation}</div>
                </div>
                """, unsafe_allow_html=True)
                st.code(final_translation, language=None)
            else:
                st.error(f"❌ {translation_result}")
