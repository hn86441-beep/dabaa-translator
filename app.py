import streamlit as st
import requests
import os
import json
from pathlib import Path
import tempfile
from faster_whisper import WhisperModel

st.set_page_config(page_title="HASSAN NASSER | Voice Translator", page_icon="🎤", layout="wide")

# ════════════════════════════════════════════════════════════
#  CSS
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1100px; }
.hero {
    background: #1a1a2e;
    border-radius: 14px;
    padding: 2rem 2rem 1.5rem;
    margin-bottom: 1.5rem;
}
.hero-name { font-size: 30px; font-weight: 600; color: #ffffff; letter-spacing: -0.5px; }
.hero-name span { color: #5DCAA5; }
.hero-sub { font-size: 13px; color: rgba(255,255,255,0.45); margin-top: 6px; letter-spacing: 0.04em; }
.hero-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.pill { display: inline-block; border-radius: 20px; padding: 4px 12px; font-size: 11px; font-weight: 500; letter-spacing: 0.04em; }
.pill-active { background: #5DCAA5; color: #04342C; }
.pill-muted { background: rgba(255,255,255,0.07); border: 0.5px solid rgba(255,255,255,0.12); color: rgba(255,255,255,0.5); }
.lang-bar { display: flex; gap: 6px; margin-top: 14px; align-items: center; }
.ldot { width: 8px; height: 8px; border-radius: 50%; background: #5DCAA5; display: inline-block; }
.lang-bar-txt { font-size: 11px; color: rgba(255,255,255,0.35); margin-left: 4px; }
.rcard { border-radius: 12px; padding: 1.1rem 1.3rem; border: 0.5px solid #e5e7eb; background: #fff; transition: all 0.2s; }
.rcard-pol { border-top: 3px solid #E63946; }
.rcard-leg { border-top: 3px solid #534AB7; }
.rcard-eco { border-top: 3px solid #F4A261; }
.rcard-med { border-top: 3px solid #2A9D8F; }
.rcard-sci { border-top: 3px solid #264653; }
.rcard-eng { border-top: 3px solid #1D9E75; }
.rcard-mil { border-top: 3px solid #8B0000; }
.rcard-edu { border-top: 3px solid #F4D03F; }
.rcard-rel { border-top: 3px solid #6C3483; }
.rcard-spt { border-top: 3px solid #E67E22; }
.rcard-lit { border-top: 3px solid #D81B60; }
.rcard-it  { border-top: 3px solid #00ACC1; }
.rcard-env { border-top: 3px solid #43A047; }
.rcard-agr { border-top: 3px solid #795548; }
.rcard-med2 { border-top: 3px solid #5E35B1; }
.rcard-tour { border-top: 3px solid #00838F; }
.rcard-gen { border-top: 3px solid #6B7280; }
.rlabel { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; margin-bottom: 8px; }
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
.rtext { font-size: 14px; line-height: 1.75; color: #1f2937; direction: auto; }
.detected-box { background: #E6F4F1; border-left: 3px solid #5DCAA5; border-radius: 0 8px 8px 0; padding: 10px 14px; font-size: 13px; color: #04342C; margin-bottom: 1rem; }
.api-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; letter-spacing: 0.04em; margin-right: 4px; }
.api-deepl { background: #0F2B46; color: #8ECAE6; }
.domain-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: 0.04em; margin-right: 6px; margin-bottom: 4px; }
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
.priority-badge { display: inline-block; background: #5DCAA5; color: white; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-left: 6px; }
.error-box { background: #fee2e2; border-left: 3px solid #ef4444; border-radius: 0 8px 8px 0; padding: 12px 16px; font-size: 14px; color: #991b1b; margin-bottom: 1rem; }
textarea { border-radius: 8px !important; border: 0.5px solid #d1d5db !important; font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="hero-name">HASSAN <span>NASSER</span></div>
    <div class="hero-sub">VOICE & MULTI-DOMAIN SMART TRANSLATOR — 15+ SPECIALIZED FIELDS</div>
    <div class="hero-pills">
        <span class="pill pill-active">🎤 Voice Input</span>
        <span class="pill pill-active">Auto-Domain Detect</span>
        <span class="pill pill-muted">DeepL Precision</span>
        <span class="pill pill-muted">Smart Swap</span>
        <span class="pill pill-muted">Style Selector</span>
    </div>
    <div class="lang-bar">
        <span class="ldot"></span><span class="ldot"></span><span class="ldot"></span>
        <span class="ldot"></span><span class="ldot"></span><span class="ldot"></span>
        <span class="ldot"></span><span class="ldot"></span>
        <span class="lang-bar-txt">8 languages — Chrome & Safari supported</span>
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
#  DEEPL API KEY
# ════════════════════════════════════════════════════════════
try:
    secrets_key = st.secrets.get("DEEPL_API_KEY", "")
except:
    secrets_key = ""

if not secrets_key:
    secrets_key = os.environ.get("DEEPL_API_KEY", "")

if "deepl_api_key" not in st.session_state:
    st.session_state.deepl_api_key = secrets_key

# ════════════════════════════════════════════════════════════
#  TRANSLATION ENGINE
# ════════════════════════════════════════════════════════════
def translate_deepl(text, target_lang_code):
    if not st.session_state.deepl_api_key:
        return None, "No API key configured"
    tl = target_lang_code.upper()
    endpoint = "https://api-free.deepl.com/v2/translate" if st.session_state.deepl_api_key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    try:
        resp = requests.post(endpoint, headers={"Authorization": f"DeepL-Auth-Key {st.session_state.deepl_api_key}"}, data={"text": text, "target_lang": tl}, timeout=15)
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"], None
        else:
            return None, f"DeepL error {resp.status_code}: {resp.text}"
    except Exception as e:
        return None, f"Request error: {str(e)}"

def fetch_ai_translation(text, target_lang_code):
    result, error = translate_deepl(text, target_lang_code)
    if result:
        return result, "DeepL"
    return None, error

# ════════════════════════════════════════════════════════════
#  تحميل نموذج Faster-Whisper (OpenAI Whisper المحسّن)
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_whisper_model():
    """
    تحميل نموذج Faster-Whisper (مرة واحدة فقط)
    - "base" = توازن بين السرعة والدقة (ممتاز)
    - "small" = دقة أعلى، أبطأ قليلاً
    - "medium" = دقة عالية جداً
    - "large" = أعلى دقة، أبطأ
    """
    return WhisperModel("base", device="cpu", compute_type="int8")

def speech_to_text_whisper(audio_bytes, language_code="auto"):
    """
    تحويل الصوت إلى نص باستخدام Faster-Whisper.
    language_code: "auto" للكشف التلقائي، أو رمز اللغة مثل "ar", "en", إلخ.
    """
    tmp_path = None
    try:
        # حفظ الصوت في ملف مؤقت
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
            tmp_audio.write(audio_bytes)
            tmp_path = tmp_audio.name

        # تحميل النموذج
        model = load_whisper_model()
        
        # تحديد اللغة
        lang = None if language_code == "auto" else language_code
        
        # تشغيل التعرف مع إعدادات محسّنة
        segments, info = model.transcribe(
            tmp_path,
            language=lang,
            beam_size=5,              # تحسين الدقة
            temperature=0.0,          # جعل النموذج أكثر حزماً
            vad_filter=True,          # تصفية الصمت لتحسين الدقة
            condition_on_previous_text=False
        )
        
        # تجميع النص من جميع المقاطع
        text = " ".join(segment.text for segment in segments).strip()
        
        # تحديد النموذج المستخدم
        model_name = f"Faster-Whisper (base)"
        if lang:
            model_name += f" - لغة: {language_code}"
        else:
            model_name += " - كشف تلقائي"
        
        return text, model_name
        
    except Exception as e:
        return None, f"خطأ في التعرف: {str(e)}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

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

left, mid, right = st.columns([1, 0.12, 1])
with left:
    source_lang_name = st.selectbox("From Language", lang_list, index=src_idx)
with mid:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    st.button("⇄", on_click=swap_languages, help="Swap languages", use_container_width=True)
with right:
    target_lang_name = st.selectbox("To Language", tgt_options, index=tgt_idx)

st.session_state.source_lang = source_lang_name
st.session_state.target_lang = target_lang_name

source_lang_code = languages_dict[source_lang_name]
target_lang_code = languages_dict[target_lang_name]

style_col1, style_col2 = st.columns([1, 2])
with style_col1:
    selected_style_label = st.selectbox("Translation Style / Domain", style_list, index=style_idx)
with style_col2:
    selected_domain = STYLE_OPTIONS[selected_style_label]
    if selected_domain and selected_domain != "general":
        dinfo = DOMAINS[selected_domain]
        st.markdown(f"<div style='margin-top: 28px; font-size: 13px; color: {dinfo['color']}; font-weight: 600;'>{dinfo['emoji']} Priority: {dinfo['name_en']}</div>", unsafe_allow_html=True)
    elif selected_domain == "general":
        st.markdown("<div style='margin-top: 28px; font-size: 13px; color: #6B7280;'>💬 General</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='margin-top: 28px; font-size: 13px; color: #6B7280;'>🔍 Auto-detecting</div>", unsafe_allow_html=True)

st.session_state.selected_style = selected_style_label

# ════════════════════════════════════════════════════════════
#  VOICE INPUT (باستخدام Faster-Whisper)
# ════════════════════════════════════════════════════════════
if st.session_state.deepl_api_key:
    if source_lang_code == "auto":
        lang_mode = "🔄 كشف تلقائي للغة"
        model_info = "سيستخدم Faster-Whisper للكشف عن اللغة تلقائياً."
    else:
        lang_mode = f"🎯 لغة محددة: {source_lang_name} ({source_lang_code})"
        model_info = f"سيستخدم Faster-Whisper مع تحديد اللغة {source_lang_name}."

    st.markdown(f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1rem;margin-bottom:1rem;">
        <div style="font-size:14px;font-weight:700;color:#1a1a2e;margin-bottom:4px;">🎤 إدخال صوتي - OpenAI Whisper</div>
        <div style="font-size:12px;color:#6b7280;">
            {lang_mode}<br>
            {model_info}<br>
            <span style="color:#16a34a;">⚡ يستخدم Faster-Whisper (أسرع 4 مرات من Whisper الأصلي)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    audio_value = st.audio_input("🎙️ سجل رسالة صوتية")
    
    if audio_value:
        st.audio(audio_value)
        with st.spinner("جاري التعرف على الصوت باستخدام Whisper..."):
            recognized_text, model_used = speech_to_text_whisper(
                audio_value.getvalue(),
                language_code=source_lang_code
            )
            if recognized_text:
                st.success(f"✅ تم التعرف ({model_used}): {recognized_text}")
                st.session_state.input_text = recognized_text
                # الترجمة التلقائية
                with st.spinner("جاري الترجمة..."):
                    translation_result, source_engine = fetch_ai_translation(recognized_text, target_lang_code)
                    if translation_result:
                        st.session_state.translated_text = translation_result
                        st.markdown("### الترجمة")
                        st.markdown(f">>> {translation_result}")
                    else:
                        st.error(f"فشلت الترجمة: {translation_result}")
            else:
                st.error(f"فشل التعرف على الصوت: {model_used}")
else:
    st.warning("⚠️ يرجى إدخال مفتاح DeepL API أولاً من الشريط الجانبي.")

# ════════════════════════════════════════════════════════════
#  TEXT INPUT
# ════════════════════════════════════════════════════════════
input_text = st.text_area("أدخل النص للترجمة (أو عدّله)", height=140, placeholder="اكتب أو الصق النص هنا...", value=st.session_state.input_text, key="input_text_area")
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
        st.markdown(f'<div class="detected-box">🔍 <b>السياق المكتشف:</b><br><div style="margin-top:6px;">{badges}</div></div>', unsafe_allow_html=True)
    else:
        if selected_style_label == "Auto-Detect":
            st.markdown('<div class="detected-box" style="border-left-color: #6B7280; background: #F3F4F6; color: #4B5563;">💬 <b>السياق:</b> عام</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  زر الترجمة
# ════════════════════════════════════════════════════════════
if st.button("ترجم 🚀", type="primary", use_container_width=True):
    if not st.session_state.deepl_api_key:
        st.error("❌ مفتاح DeepL API مفقود.")
    elif not input_text.strip():
        st.warning("الرجاء إدخال نص للترجمة.")
    else:
        with st.spinner("جاري الترجمة..."):
            translation_result, source_engine = fetch_ai_translation(input_text, target_lang_code)
            if translation_result:
                st.session_state.translated_text = translation_result
                st.markdown("### نتيجة الترجمة")
                st.markdown(f">>> {translation_result}")
            else:
                st.error(f"فشلت الترجمة: {translation_result}")

# ════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔑 مفتاح DeepL API")
    if st.session_state.deepl_api_key:
        masked = st.session_state.deepl_api_key[:6] + "..." + st.session_state.deepl_api_key[-4:] if len(st.session_state.deepl_api_key) > 10 else "***"
        st.markdown(f"<div style='font-size:12px;color:#16a34a;font-weight:600;'>✅ مفعّل</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:10px;color:#6b7280;'>{masked}</div>", unsafe_allow_html=True)
        if st.button("🔄 تغيير المفتاح", use_container_width=True):
            st.session_state.deepl_api_key = ""
            st.rerun()
    else:
        st.markdown("<div style='font-size:12px;color:#ef4444;'>⚠️ غير مضبوط</div>", unsafe_allow_html=True)
        new_key = st.text_input("أدخل مفتاح DeepL API", type="password", placeholder="مثل: abc...xyz:fx")
        if new_key:
            st.session_state.deepl_api_key = new_key
            st.success("✅ تم حفظ المفتاح!")
            st.rerun()
        st.caption("احصل على مفتاح مجاني من [DeepL](https://www.deepl.com/pro-api)")
