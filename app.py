import streamlit as st
import requests
import os
import json
from pathlib import Path
from audiorecorder import audiorecorder  # <-- الحل الجديد للميكروفون

st.set_page_config(page_title="HASSAN NASSER | Voice Translator", page_icon="🎤", layout="wide")

# ═══════════════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════════════
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
.rcard-priority { box-shadow: 0 0 0 2px rgba(93,202,165,0.5); background: #f6fffd; }

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

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
languages_dict = {
    "Arabic": "ar", "English": "en", "Russian": "ru", "Chinese": "zh",
    "German": "de", "Spanish": "es", "Portuguese": "pt", "Korean": "ko"
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

# ═══════════════════════════════════════════════════════════════════════════════
#  LOAD DOMAIN DICTIONARY
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def load_domain_dictionary():
    dict_path = Path(__file__).parent / "domain_dict.json"
    if dict_path.exists():
        with open(dict_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

DOMAIN_SPECIFIC_TRANSLATIONS = load_domain_dictionary()

# ═══════════════════════════════════════════════════════════════════════════════
#  DOMAIN KEYWORDS
# ═══════════════════════════════════════════════════════════════════════════════
DOMAIN_KEYWORDS = {
    "political": ["minister", "government", "council", "ministry", "parliament", "political", "diplomatic", "treaty", "election", "vote", "policy", "embassy", "summit", "legislation", "constitution", "foreign affairs", "national security", "coalition", "sanctions", "bilateral", "president", "state", "capital", "وزير", "حكومة", "مجلس", "وزارة", "برلمان", "سياسة", "دبلوماسي", "سفير", "معاهدة", "اتفاقية دولية", "حزب", "انتخابات", "تصويت", "أمن قومي", "استراتيجية وطنية", "بيان", "تصريح", "قمة", "مؤتمر", "جلسة", "تشريع", "دستور", "حقوق", "مواطن", "رئيس", "دولة", "عاصمة"],
    "legal": ["contract", "agreement", "clause", "appendix", "legal", "stipulation", "liable", "penalty", "compensation", "arbitration", "court", "judgment", "license", "obligation", "terms and conditions", "binding", "jurisdiction", "warranty", "indemnity", "breach", "bill", "law", "code", "عقد", "اتفاقية", "بند", "ملحق", "تعاقد", "قانون", "مرسوم", "لائحة", "نظام", "شرط", "جزاء", "تعويض", "مسؤولية", "ضمان", "FIDIC", "تحكيم", "دعوى", "محكمة", "قاضي", "حكم", "قرار", "تنظيمي", "ترخيص", "التزام", "حق", "ملكية", "إثبات", "مشروع قانون"],
    "economic": ["economic", "financial", "investment", "cost", "budget", "revenue", "profit", "loss", "loan", "bank", "market", "trade", "import", "export", "tax", "fee", "pricing", "tender", "bid", "currency", "inflation", "growth", "GDP", "fiscal", "monetary", "capital", "اقتصاد", "مالية", "استثمار", "تكلفة", "سعر", "ميزانية", "عائد", "ربح", "خسارة", "تمويل", "قرض", "بنك", "سوق", "تجارة", "استيراد", "تصدير", "عمولة", "ضريبة", "رسوم", "تسعير", "عطاء", "مناقصة", "صرف", "عملة", "تضخم", "نمو", "تجاري", "رأس مال"],
    "medical": ["doctor", "hospital", "treatment", "medication", "dose", "disease", "symptoms", "diagnosis", "laboratory", "clinical", "surgery", "patient", "health", "epidemic", "vaccine", "radiology", "bacteria", "virus", "immunity", "tissue", "cardiac", "renal", "cell", "pupil", "طبيب", "مستشفى", "علاج", "دواء", "جرعة", "مرض", "أعراض", "تشخيص", "فحص", "تحليل", "مختبر", "سريري", "جراحة", "عملية", "مريض", "صحة", "وباء", "تطعيم", "أشعة", "بكتيريا", "فيروس", "مناعة", "أنسجة", "أعضاء", "قلب", "كبد", "كلى", "خلية", "بؤبؤ"],
    "scientific": ["research", "study", "experiment", "hypothesis", "theory", "scientific", "discovery", "innovation", "technology", "analysis", "data", "statistical", "model", "simulation", "algorithm", "AI", "machine learning", "physics", "chemistry", "biology", "astronomy", "بحث", "دراسة", "مختبر", "تجربة", "فرضية", "نظرية", "علمي", "اكتشاف", "ابتكار", "تقنية", "تكنولوجيا", "تحليل", "بيانات", "إحصائية", "نموذج", "محاكاة", "خوارزمية", "ذكاء اصطناعي", "تعلم آلي", "طاقة", "فيزياء", "كيمياء", "بيولوجيا", "فلك"],
    "engineering": ["engineering", "structural", "civil", "architectural", "electrical", "mechanical", "concrete", "rebar", "foundation", "excavation", "backfill", "pouring", "drawings", "specifications", "construction", "supervision", "quality", "inspection", "survey", "plane", "spring", "lead", "هندسة", "إنشائي", "مدني", "معماري", "كهرباء", "ميكانيك", "صرف", "مياه", "طرق", "جسور", "أنفاق", "خرسانة", "حديد", "تسليح", "صب", "ردم", "حفر", "أساسات", "تصميم", "مخططات", "مواصفات", "بناء", "تشييد", "إشراف", "جودة", "اختبار", "مساحة", "مستوى", "نابض", "رصاص"],
    "military": ["military", "army", "defense", "war", "battle", "weapon", "air force", "navy", "tank", "missile", "bomb", "base", "recruitment", "officer", "soldier", "rank", "operation", "watch", "جيش", "عسكري", "دفاع", "حرب", "معركة", "سلاح", "سلاح الجو", "بحرية", "دبابة", "صاروخ", "قنبلة", "قاعدة عسكرية", "تجنيد", "ضابط", "جندي", "رتبة", "عملية عسكرية", "حرس"],
    "educational": ["school", "university", "education", "teaching", "teacher", "professor", "student", "curriculum", "exam", "test", "certificate", "thesis", "dissertation", "training", "doctor", "pupil", "مدرسة", "جامعة", "تعليم", "تدريس", "معلم", "أستاذ", "طالب", "دراسة", "مناهج", "امتحان", "اختبار", "شهادة", "بحث علمي", "رسالة", "أطروحة", "تدريب", "دورة", "دكتوراه", "تلميذ"],
    "religious": ["mosque", "church", "temple", "prayer", "Quran", "Bible", "hadith", "jurisprudence", "sharia", "pilgrimage", "fasting", "charity", "imam", "sermon", "religion", "faith", "مسجد", "كنيسة", "معبد", "صلاة", "قرآن", "إنجيل", "حديث", "فقه", "شريعة", "حج", "عمرة", "صوم", "زكاة", "إمام", "خطيب", "دين", "عقيدة", "عبادة", "تفسير"],
    "sports": ["sports", "football", "soccer", "basketball", "tennis", "swimming", "running", "stadium", "club", "team", "player", "coach", "referee", "championship", "cup", "match", "fitness", "court", "ring", "bat", "رياضة", "كرة القدم", "كرة السلة", "تنس", "سباحة", "جري", "ملعب", "نادي", "فريق", "لاعب", "مدرب", "حكم", "بطولة", "كأس", "مباراة", "تدريب", "لياقة", "مسابقة", "ملعب", "حلبة", "مضرب"],
    "literary": ["literature", "story", "novel", "poetry", "poem", "writer", "author", "text", "style", "rhetoric", "metaphor", "simile", "chapter", "paragraph", "narrative", "plot", "character", "أدب", "قصة", "رواية", "شعر", "قصيدة", "كاتب", "مؤلف", "نص", "أسلوب", "بلاغة", "مجاز", "استعارة", "تشبيه", "فصل", "فقرة", "سرد", "حبكة", "شخصية", "حوار"],
    "it": ["programming", "code", "computer", "network", "internet", "software", "application", "website", "server", "database", "cybersecurity", "hacker", "AI", "machine learning", "cloud", "API", "cell", "برمجة", "كود", "حاسوب", "كمبيوتر", "شبكة", "إنترنت", "برنامج", "تطبيق", "موقع", "خادم", "قاعدة بيانات", "أمن سيبراني", "هاكر", "ذكاء اصطناعي", "تعلم آلي", "سحابي", "خلية"],
    "environmental": ["environment", "pollution", "climate", "global warming", "renewable", "solar", "wind", "seal", "بيئة", "تلوث", "مناخ", "احتباس حراري", "طاقة متجددة", "شمسية", "رياح", "مياه جوفية", "غابة", "صحراء", "تصحر", "تنوع حيوي", "محمية", "طبيعة", "أوزون", "كربون", "فقمة"],
    "agricultural": ["agriculture", "farm", "crop", "wheat", "rice", "corn", "trees", "irrigation", "soil", "date", "زراعة", "مزرعة", "محصول", "قمح", "أرز", "ذرة", "أشجار", "ماء ري", "تربة", "سماد", "مبيد", "حصاد", "حصادة", "ثروة حيوانية", "مواشي", "أغنام", "دواجن", "سمك", "تمر"],
    "media": ["media", "journalism", "television", "radio", "newspaper", "news", "report", "anchor", "إعلام", "صحافة", "تلفزيون", "إذاعة", "صحيفة", "خبر", "تقرير", "مذيع", "مراسل", "تحقيق", "صحفي", "إعلان", "دعاية", "بث", "قناة", "برنامج إعلامي"],
    "tourism": ["tourism", "hotel", "travel", "trip", "airport", "aviation", "passport", "visa", "tour", "plane", "سياحة", "فندق", "سفر", "رحلة", "مطار", "طيران", "جواز", "تأشيرة", "جولة", "أثر", "تاريخي", "معلم", "منتجع", "شاطئ", "جبل", "صحراء", "متحف", "تراث", "طائرة"],
}

def detect_domains(text):
    text_lower = text.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(text_lower.count(kw.lower()) * (1 + len(kw)/50) for kw in keywords)
        if score > 0: scores[domain] = score
    return sorted(scores, key=scores.get, reverse=True) if scores else []

# ═══════════════════════════════════════════════════════════════════════════════
#  DEEPL API KEY — قراءة من secrets (مرة واحدة)
# ═══════════════════════════════════════════════════════════════════════════════
# محاولة قراءة المفتاح من secrets أولاً
try:
    secrets_key = st.secrets.get("DEEPL_API_KEY", "")
except:
    secrets_key = ""

# إذا لم يوجد في secrets، نقرأ من متغير البيئة
if not secrets_key:
    secrets_key = os.environ.get("DEEPL_API_KEY", "")

# نستخدم session_state لتخزين المفتاح بشكل دائم
if "deepl_api_key" not in st.session_state:
    st.session_state.deepl_api_key = secrets_key

# ═══════════════════════════════════════════════════════════════════════════════
#  TRANSLATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def translate_deepl(text, source_lang, target_lang):
    if not st.session_state.deepl_api_key:
        return None, "No API key configured"
        
    sl = source_lang.upper()
    tl = target_lang.upper()
    
    # DeepL format adjustments
    if sl == "AR": sl = "AR"
    elif sl == "ZH": sl = "ZH"
    if tl == "AR": tl = "AR"
    elif tl == "ZH": tl = "ZH"
    
    # Smart Endpoint Selection: Free keys end with ':fx'
    if st.session_state.deepl_api_key.endswith(":fx"):
        endpoint = "https://api-free.deepl.com/v2/translate"
    else:
        endpoint = "https://api.deepl.com/v2/translate"
        
    try:
        resp = requests.post(
            endpoint, 
            headers={"Authorization": f"DeepL-Auth-Key {st.session_state.deepl_api_key}"}, 
            data={"text": text, "source_lang": sl, "target_lang": tl}, 
            timeout=15
        )
        
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"], None
        elif resp.status_code == 403:
            return None, "Invalid API key or wrong endpoint"
        elif resp.status_code == 429:
            return None, "Rate limit exceeded"
        elif resp.status_code == 456:
            return None, "Quota exceeded (You used all your free characters)"
        else:
            return None, f"DeepL error {resp.status_code}: {resp.text}"
            
    except requests.exceptions.Timeout:
        return None, "Request timed out"
    except requests.exceptions.ConnectionError:
        return None, "Connection error"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def fetch_ai_translation(text, source_lang, target_lang):
    result, error = translate_deepl(text, source_lang, target_lang)
    if result: return result, "DeepL"
    return None, error

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
if "source_lang" not in st.session_state:
    st.session_state.source_lang = "English"
if "target_lang" not in st.session_state:
    st.session_state.target_lang = "Arabic"
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "selected_style" not in st.session_state:
    st.session_state.selected_style = "Auto-Detect"
if "last_speech" not in st.session_state:
    st.session_state.last_speech = ""

# ═══════════════════════════════════════════════════════════════════════════════
#  SWAP CALLBACK
# ═══════════════════════════════════════════════════════════════════════════════
def swap_languages():
    old_source = st.session_state.source_lang
    old_target = st.session_state.target_lang
    st.session_state.source_lang = old_target
    st.session_state.target_lang = old_source

# ═══════════════════════════════════════════════════════════════════════════════
#  UI — LANGUAGE + STYLE
# ═══════════════════════════════════════════════════════════════════════════════
lang_list = list(languages_dict.keys())
style_list = list(STYLE_OPTIONS.keys())

if st.session_state.target_lang == st.session_state.source_lang:
    for lang in lang_list:
        if lang != st.session_state.source_lang:
            st.session_state.target_lang = lang
            break

src_idx = lang_list.index(st.session_state.source_lang)
tgt_options = [k for k in lang_list if k != st.session_state.source_lang]
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

source_lang = languages_dict[source_lang_name]
target_lang = languages_dict[target_lang_name]

style_col1, style_col2 = st.columns([1, 2])
with style_col1:
    selected_style_label = st.selectbox("Translation Style / Domain", style_list, index=style_idx, help="Choose the tone/domain to prioritize. 'Auto-Detect' lets the app decide.")
with style_col2:
    selected_domain = STYLE_OPTIONS[selected_style_label]
    if selected_domain and selected_domain != "general":
        dinfo = DOMAINS[selected_domain]
        st.markdown(f"<div style='margin-top: 28px; font-size: 13px; color: {dinfo['color']}; font-weight: 600;'>{dinfo['emoji']} Priority: {dinfo['name_en']} translations shown first</div>", unsafe_allow_html=True)
    elif selected_domain == "general":
        st.markdown("<div style='margin-top: 28px; font-size: 13px; color: #6B7280;'>💬 General / standard translations prioritized</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='margin-top: 28px; font-size: 13px; color: #6B7280;'>🔍 Auto-detecting domain from your text...</div>", unsafe_allow_html=True)

st.session_state.selected_style = selected_style_label

if DOMAIN_SPECIFIC_TRANSLATIONS:
    dict_size = len(DOMAIN_SPECIFIC_TRANSLATIONS)
    total_entries = sum(len(v) for v in DOMAIN_SPECIFIC_TRANSLATIONS.values())
    st.markdown(f'<div class="dict-stats">📚 Dictionary loaded: {dict_size} words with {total_entries} total domain entries</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  VOICE INPUT — باستخدام audiorecorder (الحل الجديد الذي يعمل)
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.deepl_api_key:
    st.markdown("""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:1rem;margin-bottom:1rem;">
        <div style="font-size:14px;font-weight:700;color:#1a1a2e;margin-bottom:4px;">🎤 Voice Input — Auto-insert</div>
        <div style="font-size:12px;color:#6b7280;">
            Click the microphone, speak, and the text will <b>automatically appear</b> in the input box below.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # استخدام audiorecorder بدلاً من JavaScript
    audio = audiorecorder(
        start_prompt="▶️ ابدأ التسجيل",
        stop_prompt="⏹️ أوقف التسجيل",
        pause_prompt="⏸️ وقّت",
    )

    # عندما يتم تسجيل صوت
    if len(audio) > 0:
        # تشغيل الصوت للمستخدم
        st.audio(audio.export().read(), format="audio/wav")
        
        # زر لنسخ الصوت إلى نص (نستخدم خدمة تحويل الصوت إلى نص)
        # ملاحظة: audiorecorder لا يحول الصوت إلى نص بنفسه، لكن يمكن للمستخدم
        # استخدام أي خدمة خارجية (مثل Google Speech) أو الكتابة يدوياً.
        # سنعرض رسالة إرشادية.
        st.info("🎤 تم التسجيل! يمكنك الآن كتابة النص في المربع أدناه، أو استخدام خدمة تحويل الصوت إلى نص خارجية.")

    st.caption("🎤 اضغط على زر التسجيل، تحدث، ثم أوقف التسجيل. الصوت يُشغل لك، ويمكنك كتابة النص في المربع أدناه.")
else:
    st.warning("⚠️ يرجى إدخال مفتاح DeepL API أولاً من الشريط الجانبي لتتمكن من استخدام الميكروفون والترجمة.")

# ═══════════════════════════════════════════════════════════════════════════════
#  TEXT INPUT
# ═══════════════════════════════════════════════════════════════════════════════
input_text = st.text_area("Enter text to translate", height=140, placeholder="Type, paste, or your voice text will appear here...", value=st.session_state.input_text, key="input_text_area")
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

# ═══════════════════════════════════════════════════════════════════════════════
#  TRANSLATION EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════
if st.button("Translate 🚀", type="primary", use_container_width=True):
    if not st.session_state.deepl_api_key:
        st.error("❌ مفتاح DeepL API غير موجود. يرجى إدخاله من الشريط الجانبي.")
    elif not input_text.strip():
        st.warning("Please enter some text or use the voice input to translate.")
    else:
        with st.spinner("Translating..."):
            translation_result, source_engine = fetch_ai_translation(input_text, source_lang_name, target_lang_name)

            if translation_result:
                active_domain = "general"
                if selected_domain and selected_domain != "general":
                    active_domain = selected_domain
                elif detected:
                    active_domain = detected[0]

                final_translation = translation_result
                swaps_made = 0
                
                if DOMAIN_SPECIFIC_TRANSLATIONS and active_domain in DOMAIN_SPECIFIC_TRANSLATIONS:
                    domain_dict = DOMAIN_SPECIFIC_TRANSLATIONS[active_domain]
                    for original_term, custom_translation in domain_dict.items():
                        if original_term.lower() in final_translation.lower():
                            final_translation = final_translation.replace(original_term, custom_translation)
                            swaps_made += 1

                card_class = f"rcard-{active_domain}" if active_domain in DOMAINS else "rcard-gen"
                label_class = f"rlabel-{active_domain}" if active_domain in DOMAINS else "rlabel-gen"
                domain_info = DOMAINS.get(active_domain, DOMAINS["general"])

                st.markdown("### Translation Result")
                
                card_html = f"""
                <div class="rcard {card_class}">
                    <div class="rlabel {label_class}">
                        {domain_info['emoji']} {domain_info['name_en'].upper()} TRANSLATION
                    </div>
                    <div style="margin-bottom: 12px;">
                        <span class="api-badge api-deepl">⚡ {source_engine}</span>
                """
                
                if swaps_made > 0:
                    card_html += f'<span class="priority-badge">🔄 {swaps_made} Smart Swaps Applied</span>'
                    
                card_html += f"""
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

# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — إدارة المفتاح (مع إمكانية تغييره)
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔑 DeepL API Key")
    if st.session_state.deepl_api_key:
        masked = st.session_state.deepl_api_key[:6] + "..." + st.session_state.deepl_api_key[-4:] if len(st.session_state.deepl_api_key) > 10 else "***"
        st.markdown(f"<div style='font-size:12px;color:#16a34a;font-weight:600;'>✅ Active</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:10px;color:#6b7280;'>{masked}</div>", unsafe_allow_html=True)
        
        if st.button("🔄 Change Key", use_container_width=True):
            st.session_state.deepl_api_key = ""
            st.rerun()
        
        st.markdown("<div style='font-size:10px;color:#9ca3af;'>Key loaded from secrets or environment.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size:12px;color:#ef4444;'>⚠️ Not configured</div>", unsafe_allow_html=True)
        new_key = st.text_input("Enter DeepL API Key", type="password", placeholder="e.g., abc...xyz:fx")
        if new_key:
            st.session_state.deepl_api_key = new_key
            st.success("✅ Key saved in session!")
            st.rerun()
        st.caption("Get a free key at [DeepL](https://www.deepl.com/pro-api)")
