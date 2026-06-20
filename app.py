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
    layout="centered"
)

# ════════════════════════════════════════════════════════════
#  CSS - بسيط وجذاب
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ====== إخفاء العناصر ====== */
#MainMenu, footer, header {
    visibility: hidden;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
    max-width: 650px;
}

/* ====== العنوان ====== */
.title {
    text-align: center;
    padding: 0.5rem 0 1rem 0;
}

.title h1 {
    font-size: 28px;
    font-weight: 700;
    color: #1a1a2e;
    margin: 0;
}

.title h1 span {
    color: #5DCAA5;
}

.title p {
    font-size: 13px;
    color: #9ca3af;
    margin: 4px 0 0 0;
}

/* ====== أيقونة الميكروفون الكبيرة ====== */
.mic-big {
    text-align: center;
    font-size: 48px;
    padding: 0.2rem 0;
}

/* ====== حقل الميكروفون ====== */
.stAudioInput {
    border-radius: 40px !important;
    border: 2px solid #e5e7eb !important;
    padding: 4px 12px !important;
    max-width: 280px !important;
    margin: 0 auto !important;
}

.stAudioInput:hover {
    border-color: #5DCAA5 !important;
}

/* ====== الأزرار ====== */
.stButton > button {
    border-radius: 40px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 0.5rem 1.5rem !important;
    background: #1a1a2e !important;
    color: white !important;
    border: none !important;
    width: 100% !important;
}

.stButton > button:hover {
    background: #302b63 !important;
}

/* ====== حقول الإدخال ====== */
textarea {
    border-radius: 16px !important;
    border: 2px solid #e5e7eb !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
}

textarea:focus {
    border-color: #5DCAA5 !important;
    outline: none !important;
}

/* ====== صناديق الاختيار ====== */
.stSelectbox label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #6b7280 !important;
}

/* ====== النتيجة ====== */
.result-box {
    background: #f8fafc;
    border-radius: 16px;
    padding: 0.8rem 1.2rem;
    border-left: 4px solid #5DCAA5;
    margin-top: 0.5rem;
}

.result-box .label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    color: #9ca3af;
    letter-spacing: 0.05em;
}

.result-box .text {
    font-size: 15px;
    color: #1f2937;
    margin-top: 2px;
}

/* ====== سياق ====== */
.context {
    background: #f0fdf4;
    border-radius: 12px;
    padding: 6px 12px;
    font-size: 12px;
    color: #065f46;
    border-left: 3px solid #5DCAA5;
    margin-bottom: 0.5rem;
}

/* ====== شارات ====== */
.tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: 600;
    margin-right: 4px;
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
.error {
    background: #fee2e2;
    border-radius: 12px;
    padding: 8px 14px;
    font-size: 13px;
    color: #991b1b;
    border-left: 3px solid #ef4444;
}

hr {
    margin: 1rem 0 !important;
    opacity: 0.2 !important;
}

/* ====== رسائل ====== */
.stSuccess {
    border-radius: 12px !important;
    border-left: 3px solid #5DCAA5 !important;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  العنوان
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="title">
    <h1>🎤 HASSAN <span>NASSER</span></h1>
    <p>VOICE TRANSLATOR — 8 LANGUAGES</p>
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
        <h3 style="font-weight:600;">🔑 API Keys</h3>
        <p style="color:#6b7280;font-size:13px;">Enter your keys below.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.deepl_api_key:
            deepl_input = st.text_input("DeepL Key", type="password", placeholder="abc...xyz:fx")
            if deepl_input:
                st.session_state.deepl_api_key = deepl_input
                st.success("✅ Saved!")
                st.rerun()
        else:
            st.success("✅ DeepL")
    
    with col2:
        if not st.session_state.cohere_api_key:
            cohere_input = st.text_input("Cohere Key", type="password", placeholder="abcd-1234-efgh-5678")
            if cohere_input:
                st.session_state.cohere_api_key = cohere_input
                st.success("✅ Saved!")
                st.rerun()
        else:
            st.success("✅ Cohere")
    
    st.caption("💡 Stored only in your browser session.")
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
#  UI - بسيط وجذاب
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
col_left, col_mid, col_right = st.columns([1, 0.15, 1])

with col_left:
    source_lang_name = st.selectbox("From", lang_list, index=src_idx)

with col_mid:
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
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

# ====== الميكروفون ======
st.markdown("---")

if source_lang == "ru":
    engine_info = "Faster-Whisper (دقة عالية للروسية)"
elif source_lang == "auto":
    engine_info = "Cohere (كشف تلقائي)"
else:
    engine_info = f"Cohere ({source_lang_name})"

st.markdown(f"""
<div style="text-align:center;padding:0.5rem 0;">
    <div style="font-size:52px;">🎤</div>
    <div style="font-size:14px;font-weight:500;color:#1a1a2e;">سجل رسالتك الصوتية</div>
    <div style="font-size:11px;color:#9ca3af;">{engine_info}</div>
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
            
            if st.button("ترجم 🚀", use_container_width=True):
                with st.spinner("⏳ جاري الترجمة..."):
                    translated_text, engine = fetch_ai_translation(recognized_text, target_lang)
                    if translated_text:
                        st.session_state.translated_text = translated_text
                        st.markdown("### 📝 الترجمة")
                        st.markdown(f"""
                        <div class="result-box">
                            <div class="label">🎯 نتيجة الترجمة</div>
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
        st.markdown(f'<div class="context">🔍 {badges}</div>', unsafe_allow_html=True)

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
                <div class="result-box">
                    <div class="label">🎯 نتيجة الترجمة</div>
                    <div class="text">{final_translation}</div>
                </div>
                """, unsafe_allow_html=True)
                st.code(final_translation, language=None)
            else:
                st.error(f"❌ {translation_result}")
