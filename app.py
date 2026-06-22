import streamlit as st
import requests
import os
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict

st.set_page_config(
    page_title="مترجم حسن ناصر",
    page_icon="🌐",
    layout="centered"
)

# ════════════════════════════════════════════════════════════
#  SESSION STATE
# ════════════════════════════════════════════════════════════
defaults = {
    "device_mode": "laptop",
    "source_lang": "Auto-Detect",
    "target_lang": "Arabic",
    "selected_style": "Auto-Detect",
    "prev_input": "",
    "prev_translation": "",
    "prev_target": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

IS_MOBILE = st.session_state.device_mode == "mobile"

# ════════════════════════════════════════════════════════════
#  CSS
# ════════════════════════════════════════════════════════════
if IS_MOBILE:
    MAX_W = "100%"
    H1_SIZE = "24px"
    BRAND_SIZE = "9px"
    SUB_SIZE = "10px"
    SEC_SIZE = "9px"
    AREA_H = 130
    BTN_PAD = "0.55rem 1rem"
    BTN_FS = "13px"
    CARD_PAD = "0.85rem"
    CARD_R = "14px"
    CON_PL = "0.75rem"
    CON_PR = "0.75rem"
else:
    MAX_W = "700px"
    H1_SIZE = "38px"
    BRAND_SIZE = "10px"
    SUB_SIZE = "12px"
    SEC_SIZE = "10px"
    AREA_H = 110
    BTN_PAD = "0.65rem 1.5rem"
    BTN_FS = "14px"
    CARD_PAD = "1.25rem"
    CARD_R = "18px"
    CON_PL = "1rem"
    CON_PR = "1rem"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

#MainMenu, footer, header {{ visibility: hidden; }}
*, *::before, *::after {{ box-sizing: border-box; }}

.stApp {{
    background: linear-gradient(135deg, #080812 0%, #0d1522 45%, #081018 100%) !important;
    font-family: 'Inter', sans-serif !important;
    min-height: 100vh;
}}

.stApp::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(78,203,160,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(78,203,160,0.025) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
    z-index: 0;
}}

.block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    padding-left: {CON_PL} !important;
    padding-right: {CON_PR} !important;
    max-width: {MAX_W} !important;
    position: relative;
    z-index: 1;
}}

/* ── Header ── */
.app-header {{
    text-align: center;
    padding: 1.5rem 0.5rem 1.25rem;
}}
.app-header .brand {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: {BRAND_SIZE};
    font-weight: 600;
    letter-spacing: 0.3em;
    color: rgba(78,203,160,0.6);
    text-transform: uppercase;
    display: block;
    margin-bottom: 0.5rem;
}}
.app-header h1 {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: {H1_SIZE};
    font-weight: 700;
    color: #f0f4ff;
    margin: 0 0 0.35rem;
    letter-spacing: -0.01em;
    line-height: 1.1;
}}
.app-header h1 span {{ color: #4ECBA0; }}
.app-header .sub {{
    font-size: {SUB_SIZE};
    color: rgba(160,185,230,0.45);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 500;
    margin: 0;
}}

/* ── Device toggle ── */
.dev-row {{
    display: flex;
    justify-content: flex-end;
    gap: 5px;
    margin-bottom: 0.2rem;
}}

/* ── Section heading ── */
.sh {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: {SEC_SIZE};
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(140,175,220,0.45);
    margin: 1.4rem 0 0.55rem;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.sh::before {{
    content: '';
    width: 3px; height: 12px;
    background: #4ECBA0;
    border-radius: 2px;
    flex-shrink: 0;
}}

/* ── Glass card ── */
.gc {{
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: {CARD_R};
    padding: {CARD_PAD};
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
}}
.gc::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(78,203,160,0.35), transparent);
}}

/* ── Mic strip ── */
.mic-strip {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0.65rem 1rem;
    background: rgba(78,203,160,0.05);
    border: 1px solid rgba(78,203,160,0.18);
    border-radius: 12px;
    margin-bottom: 0.6rem;
}}
.mic-dot {{
    width: 36px; height: 36px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(78,203,160,0.2), rgba(78,203,160,0.04));
    border: 1px solid rgba(78,203,160,0.3);
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    box-shadow: 0 0 10px rgba(78,203,160,0.12);
}}
.mic-label {{
    font-size: 12px;
    font-weight: 600;
    color: rgba(220,235,255,0.8);
    letter-spacing: 0.01em;
}}
.mic-sub {{
    font-size: 10px;
    color: rgba(78,203,160,0.55);
    margin-top: 1px;
    letter-spacing: 0.03em;
}}

/* ── Selectbox ── */
.stSelectbox > div > div {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    color: #e8f0ff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    transition: border-color 0.2s;
}}
.stSelectbox > div > div:hover {{ border-color: rgba(78,203,160,0.4) !important; }}
.stSelectbox label {{
    font-size: 10px !important;
    font-weight: 600 !important;
    color: rgba(78,203,160,0.65) !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}}

/* ── Buttons ── */
.stButton > button {{
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: {BTN_FS} !important;
    padding: {BTN_PAD} !important;
    background: linear-gradient(135deg, #4ECBA0, #28a074) !important;
    color: #071512 !important;
    border: none !important;
    width: 100% !important;
    font-family: 'Space Grotesk', sans-serif !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 3px 16px rgba(78,203,160,0.28) !important;
    letter-spacing: 0.02em !important;
}}
.stButton > button:hover {{
    background: linear-gradient(135deg, #5ddbb0, #35b886) !important;
    box-shadow: 0 5px 22px rgba(78,203,160,0.42) !important;
    transform: translateY(-1px) !important;
}}

/* ── Textarea ── */
textarea {{
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 14px !important;
    color: #dce8ff !important;
    font-size: 15px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 13px 15px !important;
    line-height: 1.65 !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}}
textarea:focus {{
    border-color: rgba(78,203,160,0.45) !important;
    box-shadow: 0 0 0 3px rgba(78,203,160,0.09) !important;
    outline: none !important;
}}
textarea::placeholder {{ color: rgba(140,165,210,0.28) !important; }}

/* ── Result box ── */
.rb {{
    background: rgba(78,203,160,0.055);
    border: 1px solid rgba(78,203,160,0.18);
    border-radius: 14px;
    padding: 1rem 1.25rem 1rem 1.5rem;
    margin-top: 0.75rem;
    position: relative;
}}
.rb::before {{
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, #4ECBA0, #239e6a);
    border-radius: 3px 0 0 3px;
}}
.rb-label {{
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    color: rgba(78,203,160,0.6);
    letter-spacing: 0.14em;
    display: block;
    margin-bottom: 5px;
}}
.rb-text {{
    font-size: 15px;
    color: #dce8ff;
    line-height: 1.7;
}}

/* ── Live badge ── */
.live-badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 10px;
    font-weight: 600;
    color: rgba(78,203,160,0.65);
    letter-spacing: 0.07em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}}
.pdot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #4ECBA0;
    animation: pdot 1.4s ease-in-out infinite;
    display: inline-block;
}}
@keyframes pdot {{
    0%,100% {{ opacity:1; transform:scale(1); }}
    50% {{ opacity:0.3; transform:scale(0.6); }}
}}

/* ── Domain tags ── */
.ctx {{
    background: rgba(78,203,160,0.06);
    border: 1px solid rgba(78,203,160,0.13);
    border-radius: 10px;
    padding: 6px 12px;
    font-size: 11px;
    color: rgba(78,203,160,0.85);
    margin-bottom: 0.6rem;
}}
.tag {{
    display: inline-flex; align-items: center; gap: 3px;
    padding: 2px 9px; border-radius: 20px;
    font-size: 10px; font-weight: 600; margin-right: 4px;
}}
.tag-pol  {{ background:rgba(230,57,70,.18);  color:#ff6b78; border:1px solid rgba(230,57,70,.28); }}
.tag-leg  {{ background:rgba(83,74,183,.18);  color:#9d96f0; border:1px solid rgba(83,74,183,.28); }}
.tag-eco  {{ background:rgba(244,162,97,.18); color:#f4b060; border:1px solid rgba(244,162,97,.28); }}
.tag-med  {{ background:rgba(42,157,143,.18); color:#3dd1bd; border:1px solid rgba(42,157,143,.28); }}
.tag-sci  {{ background:rgba(38,70,83,.28);   color:#7dbfcf; border:1px solid rgba(38,70,83,.45); }}
.tag-eng  {{ background:rgba(29,158,117,.18); color:#42d4a0; border:1px solid rgba(29,158,117,.28); }}
.tag-mil  {{ background:rgba(139,0,0,.18);    color:#ff7b7b; border:1px solid rgba(139,0,0,.3); }}
.tag-edu  {{ background:rgba(244,208,63,.12); color:#f4d24a; border:1px solid rgba(244,208,63,.22); }}
.tag-rel  {{ background:rgba(108,52,131,.18); color:#c07fe0; border:1px solid rgba(108,52,131,.3); }}
.tag-spt  {{ background:rgba(230,126,34,.18); color:#f0944a; border:1px solid rgba(230,126,34,.28); }}
.tag-lit  {{ background:rgba(216,27,96,.18);  color:#f06090; border:1px solid rgba(216,27,96,.28); }}
.tag-it   {{ background:rgba(0,172,193,.18);  color:#3dd4e4; border:1px solid rgba(0,172,193,.28); }}
.tag-env  {{ background:rgba(67,160,71,.18);  color:#6dd873; border:1px solid rgba(67,160,71,.28); }}
.tag-agr  {{ background:rgba(121,85,72,.18);  color:#c4a08a; border:1px solid rgba(121,85,72,.28); }}
.tag-tour {{ background:rgba(0,131,143,.18);  color:#30c8d8; border:1px solid rgba(0,131,143,.28); }}
.tag-gen  {{ background:rgba(107,114,128,.18);color:#9ca3af; border:1px solid rgba(107,114,128,.28); }}

/* ── Alerts ── */
.stSuccess {{ background:rgba(78,203,160,0.07)!important; border:1px solid rgba(78,203,160,0.22)!important; border-radius:12px!important; }}
.stError   {{ background:rgba(239,68,68,0.07)!important;  border:1px solid rgba(239,68,68,0.22)!important;  border-radius:12px!important; }}
.stWarning {{ background:rgba(245,158,11,0.07)!important; border:1px solid rgba(245,158,11,0.18)!important; border-radius:12px!important; }}

.stCode, code, pre {{
    background:rgba(0,0,0,0.32)!important;
    border:1px solid rgba(255,255,255,0.07)!important;
    border-radius:10px!important;
    color:#a8f0d8!important;
    font-size:13px!important;
}}

hr {{
    margin:1.25rem 0!important; border:none!important; height:1px!important;
    background:linear-gradient(90deg,transparent,rgba(78,203,160,0.18),transparent)!important;
}}

.stTextInput input {{
    background:rgba(255,255,255,0.045)!important;
    border:1px solid rgba(255,255,255,0.09)!important;
    border-radius:10px!important;
    color:#e8f0ff!important;
    font-family:'Inter',sans-serif!important;
}}
.stTextInput input:focus {{
    border-color:rgba(78,203,160,0.45)!important;
    box-shadow:0 0 0 3px rgba(78,203,160,0.09)!important;
}}
.stTextInput label {{
    color:rgba(78,203,160,0.7)!important; font-size:10px!important;
    font-weight:600!important; letter-spacing:0.1em!important; text-transform:uppercase!important;
}}

.stCaption {{ color:rgba(140,170,220,0.4)!important; font-size:10px!important; }}
[data-testid="column"] {{ padding: 0 4px !important; }}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  DEVICE TOGGLE
# ════════════════════════════════════════════════════════════
dcol1, dcol2, dcol3 = st.columns([4, 1, 1])
with dcol2:
    if st.button("💻", key="dev_lap", use_container_width=True,
                 help="وضع اللابتوب"):
        st.session_state.device_mode = "laptop"
        st.rerun()
with dcol3:
    if st.button("📱", key="dev_mob", use_container_width=True,
                 help="وضع الهاتف"):
        st.session_state.device_mode = "mobile"
        st.rerun()

# Show active mode indicator
mode_label = "📱 وضع الهاتف" if IS_MOBILE else "💻 وضع اللابتوب"
st.markdown(f"""
<div style="text-align:right; font-size:10px; color:rgba(78,203,160,0.5);
            font-weight:600; letter-spacing:0.06em; margin-top:-0.5rem; margin-bottom:0.25rem;">
    {mode_label}
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <span class="brand">✦ مترجم متخصص ✦</span>
    <h1>حسن <span>ناصر</span></h1>
    <p class="sub">مترجم صوتي · ٨ لغات</p>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════════════
languages_dict = {
    "Auto-Detect": "auto", "Arabic": "ar", "English": "en",
    "Russian": "ru", "Chinese": "zh", "German": "de",
    "Spanish": "es", "Portuguese": "pt", "Korean": "ko"
}
DOMAINS = {
    "political":    {"emoji":"🏛️","name_en":"Political"},
    "legal":        {"emoji":"⚖️","name_en":"Legal"},
    "economic":     {"emoji":"📈","name_en":"Economic"},
    "medical":      {"emoji":"🏥","name_en":"Medical"},
    "scientific":   {"emoji":"🔬","name_en":"Scientific"},
    "engineering":  {"emoji":"🏗️","name_en":"Engineering"},
    "military":     {"emoji":"🎖️","name_en":"Military"},
    "educational":  {"emoji":"📚","name_en":"Educational"},
    "religious":    {"emoji":"🕌","name_en":"Religious"},
    "sports":       {"emoji":"⚽","name_en":"Sports"},
    "literary":     {"emoji":"📖","name_en":"Literary"},
    "it":           {"emoji":"💻","name_en":"IT / Tech"},
    "environmental":{"emoji":"🌿","name_en":"Environmental"},
    "agricultural": {"emoji":"🌾","name_en":"Agricultural"},
    "media":        {"emoji":"📺","name_en":"Media"},
    "tourism":      {"emoji":"✈️","name_en":"Tourism"},
    "general":      {"emoji":"💬","name_en":"General"},
}
STYLE_OPTIONS = {
    "Auto-Detect": None,
    "🏛️ Political":"political","⚖️ Legal":"legal","📈 Economic":"economic",
    "🏥 Medical":"medical","🔬 Scientific":"scientific","🏗️ Engineering":"engineering",
    "🎖️ Military":"military","📚 Educational":"educational","🕌 Religious":"religious",
    "⚽ Sports":"sports","📖 Literary":"literary","💻 IT / Tech":"it",
    "🌿 Environmental":"environmental","🌾 Agricultural":"agricultural",
    "📺 Media":"media","✈️ Tourism":"tourism","💬 General":"general",
}
DOMAIN_KEYWORDS = {
    "political":["minister","government","parliament","political","diplomatic","treaty","election","policy","president","وزير","حكومة","برلمان","سياسة","دبلوماسي","معاهدة","انتخابات","رئيس"],
    "legal":["contract","agreement","clause","legal","court","judgment","law","عقد","اتفاق","قانون","محكمة","حكم"],
    "economic":["economic","financial","investment","cost","budget","revenue","profit","loss","اقتصاد","مالية","استثمار","تكلفة","ميزانية","ربح"],
    "medical":["doctor","hospital","treatment","disease","diagnosis","surgery","patient","طبيب","مستشفى","علاج","مرض","تشخيص","عملية","مريض"],
    "scientific":["research","study","experiment","theory","scientific","technology","data","بحث","دراسة","تجربة","نظرية","علمي","تقنية","بيانات"],
    "engineering":["engineering","structural","civil","electrical","mechanical","concrete","construction","هندسة","إنشائي","مدني","كهرباء","ميكانيك","خرسانة","بناء"],
    "military":["military","army","defense","war","weapon","base","جيش","عسكري","دفاع","حرب","سلاح","قاعدة"],
    "educational":["school","university","education","teacher","student","exam","مدرسة","جامعة","تعليم","معلم","طالب","امتحان"],
    "religious":["mosque","church","prayer","Quran","Bible","religion","faith","مسجد","كنيسة","صلاة","قرآن","إنجيل","دين"],
    "sports":["sports","football","basketball","tennis","stadium","team","player","رياضة","كرة القدم","كرة السلة","تنس","ملعب","فريق"],
    "literary":["literature","story","novel","poetry","writer","author","text","أدب","قصة","رواية","شعر","كاتب","نص"],
    "it":["programming","computer","network","software","application","website","database","برمجة","حاسوب","شبكة","برنامج","موقع","قاعدة بيانات"],
    "environmental":["environment","pollution","climate","renewable","solar","wind","بيئة","تلوث","مناخ","متجددة","شمسية","رياح"],
    "agricultural":["agriculture","farm","crop","wheat","rice","trees","irrigation","زراعة","مزرعة","محصول","قمح","أرز","أشجار"],
    "media":["media","journalism","television","radio","news","report","إعلام","صحافة","تلفزيون","إذاعة","خبر","تقرير"],
    "tourism":["tourism","hotel","travel","airport","passport","visa","tour","سياحة","فندق","سفر","مطار","جواز","تأشيرة"],
}

def detect_domains(text):
    tl = text.lower()
    scores = {}
    for d, kws in DOMAIN_KEYWORDS.items():
        s = sum(tl.count(k.lower()) for k in kws)
        if s > 0:
            scores[d] = s
    return sorted(scores, key=scores.get, reverse=True) if scores else []

# ════════════════════════════════════════════════════════════
#  API KEYS
# ════════════════════════════════════════════════════════════
try:    deepl_secret = st.secrets.get("DEEPL_API_KEY", "")
except: deepl_secret = ""
try:    cohere_secret = st.secrets.get("COHERE_API_KEY", "")
except: cohere_secret = ""

if "deepl_api_key" not in st.session_state:
    st.session_state.deepl_api_key = deepl_secret
if "cohere_api_key" not in st.session_state:
    st.session_state.cohere_api_key = cohere_secret

if not st.session_state.deepl_api_key or not st.session_state.cohere_api_key:
    st.markdown("""
    <div class="gc" style="text-align:center; padding:2rem;">
        <div style="font-size:32px; margin-bottom:0.75rem;">🔐</div>
        <div style="font-family:'Space Grotesk',sans-serif; font-size:18px; font-weight:700;
                    color:#e8f0ff; margin-bottom:0.3rem;">أدخل مفاتيح API</div>
        <div style="font-size:11px; color:rgba(140,175,220,0.45);">
            تُحفظ في الجلسة فقط ولا تُرسل لأي جهة
        </div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if not st.session_state.deepl_api_key:
            v = st.text_input("DeepL API Key", type="password", placeholder="xxxx:fx")
            if v:
                st.session_state.deepl_api_key = v
                st.rerun()
        else:
            st.success("✅ DeepL")
    with c2:
        if not st.session_state.cohere_api_key:
            v = st.text_input("Cohere API Key", type="password", placeholder="xxxx-xxxx")
            if v:
                st.session_state.cohere_api_key = v
                st.rerun()
        else:
            st.success("✅ Cohere")
    st.stop()

# ════════════════════════════════════════════════════════════
#  TRANSLATION
# ════════════════════════════════════════════════════════════
def translate_deepl(text, target_lang):
    tl = target_lang.upper()
    ep = "https://api-free.deepl.com/v2/translate" if st.session_state.deepl_api_key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    try:
        r = requests.post(ep,
            headers={"Authorization": f"DeepL-Auth-Key {st.session_state.deepl_api_key}"},
            data={"text": text, "target_lang": tl}, timeout=15)
        if r.status_code == 200:
            return r.json()["translations"][0]["text"], None
        return None, f"خطأ {r.status_code}"
    except Exception as e:
        return None, str(e)

def do_translate(text, target_lang):
    result, err = translate_deepl(text, target_lang)
    return (result, None) if result else (None, err)

# ════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT
# ════════════════════════════════════════════════════════════
def stt_cohere(audio_bytes, lang="auto"):
    if not st.session_state.cohere_api_key:
        return None, "مفتاح Cohere غير موجود"
    try:
        fields = OrderedDict()
        fields['language'] = "en" if lang in ("auto", None) else lang
        fields['model'] = 'cohere-transcribe-03-2026'
        fields['file'] = ('audio.wav', audio_bytes, 'audio/wav')
        enc = MultipartEncoder(fields=fields)
        r = requests.post("https://api.cohere.com/v2/audio/transcriptions",
            headers={"Authorization": f"Bearer {st.session_state.cohere_api_key}", "Content-Type": enc.content_type},
            data=enc, timeout=30)
        if r.status_code == 200:
            t = r.json().get("text", "").strip()
            return (t, None) if t else (None, "لم يتم التعرف على كلام")
        return None, f"خطأ {r.status_code}"
    except Exception as e:
        return None, str(e)

@st.cache_resource
def load_whisper():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("small", device="cpu", compute_type="int8")
    except:
        return None

def stt_whisper(audio_bytes):
    model = load_whisper()
    if not model:
        return None, "نموذج Whisper غير متاح"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes); tmp = f.name
        segs, _ = model.transcribe(tmp, language="ru", beam_size=5, temperature=0.0, vad_filter=True)
        t = " ".join(s.text for s in segs).strip()
        return (t, None) if t else (None, "لم يتم التعرف على كلام")
    except Exception as e:
        return None, str(e)
    finally:
        try:
            if tmp and os.path.exists(tmp): os.unlink(tmp)
        except: pass

def stt(audio_bytes, lang="auto"):
    if lang == "ru":
        return stt_whisper(audio_bytes)
    return stt_cohere(audio_bytes, lang)

# ════════════════════════════════════════════════════════════
#  LANGUAGE SELECTORS
# ════════════════════════════════════════════════════════════
lang_list  = list(languages_dict.keys())
style_list = list(STYLE_OPTIONS.keys())

if st.session_state.target_lang == st.session_state.source_lang:
    for l in lang_list:
        if l != st.session_state.source_lang:
            st.session_state.target_lang = l; break

src_idx  = lang_list.index(st.session_state.source_lang) if st.session_state.source_lang in lang_list else 0
tgt_opts = [k for k in lang_list if k != st.session_state.source_lang and k != "Auto-Detect"]
tgt_idx  = tgt_opts.index(st.session_state.target_lang) if st.session_state.target_lang in tgt_opts else 0
sty_idx  = style_list.index(st.session_state.selected_style) if st.session_state.selected_style in style_list else 0

def swap_langs():
    s, t = st.session_state.source_lang, st.session_state.target_lang
    st.session_state.source_lang, st.session_state.target_lang = t, s

st.markdown('<div class="sh">اتجاه الترجمة</div>', unsafe_allow_html=True)
cl, cm, cr = st.columns([1, 0.18, 1])
with cl:
    src_name = st.selectbox("من", lang_list, index=src_idx)
with cm:
    st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
    if st.button("⇄", use_container_width=True):
        swap_langs()
with cr:
    tgt_name = st.selectbox("إلى", tgt_opts, index=tgt_idx)

st.session_state.source_lang = src_name
st.session_state.target_lang = tgt_name
src_lang = languages_dict[src_name]
tgt_lang = languages_dict[tgt_name]

st.markdown('<div class="sh">المجال</div>', unsafe_allow_html=True)
sel_style = st.selectbox("المجال", style_list, index=sty_idx, label_visibility="collapsed")
sel_domain = STYLE_OPTIONS[sel_style]
st.session_state.selected_style = sel_style

# ════════════════════════════════════════════════════════════
#  VOICE INPUT — صغيرة ومدمجة
# ════════════════════════════════════════════════════════════
st.markdown("---")

lang_hint = {"ru": "روسي (Whisper)", "auto": "كشف تلقائي", "ar": "عربي", "en": "إنجليزي",
             "zh": "صيني", "de": "ألماني", "es": "إسباني", "pt": "برتغالي", "ko": "كوري"}
hint = lang_hint.get(src_lang, src_name)

st.markdown(f"""
<div class="mic-strip">
    <div class="mic-dot">🎙️</div>
    <div>
        <div class="mic-label">تسجيل صوتي</div>
        <div class="mic-sub">{hint} · ترجمة فورية بعد التسجيل</div>
    </div>
</div>
""", unsafe_allow_html=True)

audio_value = st.audio_input("", label_visibility="collapsed")

if audio_value:
    with st.spinner("جارٍ التعرف على الكلام..."):
        recognized, err = stt(audio_value.getvalue(), src_lang)
    if recognized:
        st.success(f"✅ {recognized}")
        with st.spinner("جارٍ الترجمة..."):
            result, terr = do_translate(recognized, tgt_lang)
        if result:
            st.markdown('<div class="sh">نتيجة الترجمة الصوتية</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rb"><span class="rb-label">✦ ترجمة</span><div class="rb-text">{result}</div></div>', unsafe_allow_html=True)
            st.code(result, language=None)
        else:
            st.error(f"❌ {terr}")
    else:
        st.error(f"❌ {err}")

# ════════════════════════════════════════════════════════════
#  TEXT INPUT — ترجمة فورية عند الكتابة
# ════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<div class="sh">النص المكتوب</div>', unsafe_allow_html=True)

st.markdown("""
<div class="live-badge">
    <span class="pdot"></span>
    ترجمة فورية عند الكتابة
</div>
""", unsafe_allow_html=True)

input_text = st.text_area(
    "", height=AREA_H,
    placeholder="اكتب النص هنا... / Type here...",
    key="live_input"
)

# ── كشف المجال ──
detected = []
if input_text.strip():
    detected = detect_domains(input_text)
    if detected:
        badges = "".join(
            f'<span class="tag tag-{d}">{DOMAINS[d]["emoji"]} {DOMAINS[d]["name_en"]}</span>'
            for d in detected[:3]
        )
        st.markdown(f'<div class="ctx">🔍 {badges}</div>', unsafe_allow_html=True)

# ── الترجمة الفورية ──
# المنطق: إذا تغير النص أو تغيرت لغة الهدف → نترجم
current_text = input_text.strip()
current_target = tgt_lang

needs_translation = (
    current_text
    and len(current_text) >= 3
    and (
        current_text != st.session_state.prev_input
        or current_target != st.session_state.prev_target
    )
)

if needs_translation:
    with st.spinner("⚡ جارٍ الترجمة..."):
        live_result, live_err = do_translate(current_text, current_target)

    if live_result:
        st.session_state.prev_input = current_text
        st.session_state.prev_target = current_target
        st.session_state.prev_translation = live_result

        active = sel_domain or (detected[0] if detected else "general")
        d_emoji = DOMAINS.get(active, {}).get("emoji", "💬")
        d_name  = DOMAINS.get(active, {}).get("name_en", "General")

        st.markdown('<div class="sh">الترجمة</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="rb"><span class="rb-label">✦ {d_emoji} {d_name}</span>'
            f'<div class="rb-text">{live_result}</div></div>',
            unsafe_allow_html=True
        )
        st.code(live_result, language=None)

    elif len(current_text) >= 10:
        st.error(f"❌ {live_err}")

elif (
    st.session_state.prev_translation
    and current_text == st.session_state.prev_input
    and current_target == st.session_state.prev_target
):
    # عرض آخر ترجمة إذا لم يتغير النص
    active = sel_domain or (detected[0] if detected else "general")
    d_emoji = DOMAINS.get(active, {}).get("emoji", "💬")
    d_name  = DOMAINS.get(active, {}).get("name_en", "General")
    st.markdown('<div class="sh">الترجمة</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="rb"><span class="rb-label">✦ {d_emoji} {d_name}</span>'
        f'<div class="rb-text">{st.session_state.prev_translation}</div></div>',
        unsafe_allow_html=True
    )
    st.code(st.session_state.prev_translation, language=None)

elif not current_text:
    st.session_state.prev_input = ""
    st.session_state.prev_translation = ""
    st.session_state.prev_target = ""
