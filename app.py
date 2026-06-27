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
from PIL import Image
import time
import numpy as np

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

from deep_translator import GoogleTranslator
from gtts import gTTS

DB_PATH = "translations.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, original TEXT NOT NULL, translated TEXT NOT NULL, emotion TEXT, source_lang TEXT, target_lang TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

def save_translation(original, translated, emotion, source_lang, target_lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO history (original, translated, emotion, source_lang, target_lang, timestamp) VALUES (?, ?, ?, ?, ?, ?)''', (original, translated, emotion, source_lang, target_lang, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_history(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT original, translated, emotion, source_lang, target_lang, timestamp FROM history ORDER BY id DESC LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"original": row[0], "translated": row[1], "emotion": row[2], "source_lang": row[3], "target_lang": row[4], "time": row[5]} for row in rows]

def clear_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM history')
    conn.commit()
    conn.close()

def export_history_json():
    return json.dumps(get_history(limit=1000), ensure_ascii=False, indent=2)

init_db()

@st.cache_resource
def load_emotion_classifier():
    try:
        return pipeline("text-classification", model="nlptown/bert-base-multilingual-uncased-sentiment")
    except Exception as e:
        st.warning(f"فشل تحميل النموذج: {e}")
        return None

emotion_classifier = load_emotion_classifier()

def analyze_emotion(text):
    if not text or emotion_classifier is None:
        return "محايد"
    try:
        result = emotion_classifier(text[:512])[0]
        label = int(result['label'].split()[0])
        if label >= 4:
            return "فرح"
        elif label <= 2:
            return "حزن"
        else:
            return "محايد"
    except Exception:
        return "محايد"

def get_tts_lang(lang_code):
    lang_map = {"ar": "ar", "en": "en", "ru": "ru", "zh": "zh-cn", "de": "de", "es": "es", "pt": "pt", "ko": "ko"}
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
    except Exception:
        return None

def extract_text_from_file(file_bytes, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        if not PDFPLUMBER_AVAILABLE:
            return None, "مكتبة pdfplumber غير مثبتة"
        try:
            text = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return (text.strip(), None) if text.strip() else (None, "لا يوجد نص")
        except Exception as e:
            return None, str(e)
    elif ext == '.docx':
        if not DOCX_AVAILABLE:
            return None, "مكتبة python-docx غير مثبتة"
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            return (text.strip(), None) if text.strip() else (None, "لا يوجد نص")
        except Exception as e:
            return None, str(e)
    elif ext in ['.xlsx', '.xls']:
        if not EXCEL_AVAILABLE:
            return None, "مكتبة openpyxl غير مثبتة"
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            all_text = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value is not None:
                            all_text.append(str(cell.value))
            text = "\n".join(all_text)
            return (text.strip(), None) if text.strip() else (None, "لا يوجد نص")
        except Exception as e:
            return None, str(e)
    elif ext == '.txt':
        try:
            text = file_bytes.decode('utf-8')
            return (text.strip(), None) if text.strip() else (None, "ملف فارغ")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode('windows-1256')
                return (text.strip(), None) if text.strip() else (None, "ملف فارغ")
            except:
                return None, "تعذر قراءة الملف"
    else:
        return None, f"نوع الملف غير مدعوم: {ext}"

def translate_deepl(text, target_lang):
    if not st.session_state.get("deepl_api_key"):
        return None, "No API key"
    tl = target_lang.upper()
    endpoint = "https://api-free.deepl.com/v2/translate" if st.session_state.deepl_api_key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    try:
        resp = requests.post(endpoint, headers={"Authorization": f"DeepL-Auth-Key {st.session_state.deepl_api_key}"}, data={"text": text, "target_lang": tl}, timeout=15)
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"], None
        return None, f"DeepL error {resp.status_code}"
    except Exception as e:
        return None, str(e)

def translate_text(text, target_lang):
    if st.session_state.get("deepl_api_key"):
        tr, err = translate_deepl(text, target_lang)
        if tr:
            return tr, None
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text), None
    except Exception as e1:
        libre_url = os.environ.get("LIBRETRANSLATE_URL", st.secrets.get("LIBRETRANSLATE_URL", ""))
        if libre_url:
            try:
                resp = requests.post(f"{libre_url}/translate", json={"q": text, "source": "auto", "target": target_lang}, timeout=10)
                if resp.status_code == 200:
                    return resp.json()["translatedText"], None
                return None, f"Google: {e1} | LibreTranslate: {resp.status_code}"
            except Exception as e2:
                return None, f"Google: {e1} | LibreTranslate: {e2}"
        return None, f"Google error: {e1}"

# ════════════════════════════════════════════════════════════
#  دالة التعرف على الصوت Cohere مع معالجة 429 وإعادة المحاولة
# ════════════════════════════════════════════════════════════
def speech_to_text_cohere(audio_bytes, language_code="auto"):
    if not st.session_state.get("cohere_api_key"):
        return None, "API key missing"

    max_retries = 3
    retry_delays = [1, 2, 4]  # ثواني

    for attempt in range(max_retries):
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
                    "Content-Type": encoder.content_type
                },
                data=encoder,
                timeout=30
            )
            if response.status_code == 200:
                text = response.json().get("text", "").strip()
                return (text, "Cohere") if text else (None, "No speech detected")
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    continue
                else:
                    return None, "Cohere: تجاوزت الحد اليومي، حاول لاحقاً"
            else:
                return None, f"Cohere error {response.status_code}"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])
                continue
            return None, f"Error: {str(e)}"
    return None, "Cohere: فشل بعد عدة محاولات"

st.set_page_config(page_title="HN TRANSLATOR", page_icon="🌐", layout="centered")

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def get_css(theme):
    if theme == "light":
        return """<style>.stApp { background: #f5f7fa !important; } .app-header { text-align: center; padding: 0.8rem 0 0.5rem 0; } .app-header .brand { font-size: 11px; font-weight: 600; letter-spacing: 0.3em; color: #2a7a60; text-transform: uppercase; display: block; margin-bottom: 0.2rem; opacity: 0.8; } .app-header h1 { font-size: 32px; font-weight: 700; color: #1a1a2e; margin: 0; } .app-header h1 .accent { color: #2a7a60; } .app-header .divider { width: 60px; height: 3px; background: linear-gradient(90deg, #2a7a60, transparent); margin: 0.3rem auto 0; border-radius: 2px; } .stButton > button { background: #2a7a60 !important; color: white !important; } .chat-bubble { margin: 10px 0; border-radius: 15px; padding: 12px; background: rgba(42,122,96,0.05); border-left: 5px solid #2a7a60; } .chat-bubble .speaker { font-weight: bold; margin-bottom: 5px; color: #2a7a60; } .chat-bubble .original { color: #333; font-size: 14px; } .chat-bubble .translated { color: #1a5a48; font-size: 14px; margin-top: 5px; }</style>"""
    else:
        return """<style>.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0f1728 40%, #0a1520 100%) !important; } .app-header { text-align: center; padding: 0.8rem 0 0.5rem 0; } .app-header .brand { font-size: 11px; font-weight: 600; letter-spacing: 0.3em; color: #4ECBA0; text-transform: uppercase; display: block; margin-bottom: 0.2rem; opacity: 0.8; } .app-header h1 { font-size: 32px; font-weight: 700; color: #f0f4ff; margin: 0; } .app-header h1 .accent { color: #4ECBA0; } .app-header .divider { width: 60px; height: 3px; background: linear-gradient(90deg, #4ECBA0, transparent); margin: 0.3rem auto 0; border-radius: 2px; } .stButton > button { background: linear-gradient(135deg, #4ECBA0 0%, #2fa87a 100%) !important; color: #0a1520 !important; } .chat-bubble { margin: 10px 0; border-radius: 15px; padding: 12px; background: rgba(255,255,255,0.05); border-left: 5px solid #4ECBA0; } .chat-bubble .speaker { font-weight: bold; margin-bottom: 5px; color: #4ECBA0; } .chat-bubble .original { color: #ccc; font-size: 14px; } .chat-bubble .translated { color: #a8f0d8; font-size: 14px; margin-top: 5px; }</style>"""

st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

st.markdown("""<div class="app-header"><span class="brand">✦ Smart Voice Translator ✦</span><h1>HN <span class="accent">TRANSLATOR</span></h1><div class="divider"></div></div>""", unsafe_allow_html=True)

with st.sidebar:
    if st.button("🌓", help="تبديل المظهر", use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()
    st.divider()
    history = get_history(limit=100)
    if history:
        if st.button("🗑️", help="مسح الكل", use_container_width=True):
            clear_history()
            st.rerun()
        for item in history:
            st.markdown(f"""<div class="history-item"><div class="original">{item.get('original', '')}</div><div class="translated">{item.get('translated', '')}</div></div>""", unsafe_allow_html=True)
        if st.button("📤", help="تصدير السجل (JSON)", use_container_width=True):
            json_str = export_history_json()
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="translation_history.json">📥 تحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; color: rgba(150,175,220,0.3); font-size: 30px;'>📭</div>", unsafe_allow_html=True)

languages_dict = {"Auto-Detect": "auto", "Arabic": "ar", "English": "en", "Russian": "ru", "Chinese": "zh", "German": "de", "Spanish": "es", "Portuguese": "pt", "Korean": "ko"}

DOMAINS = {"political": {"emoji": "🏛️", "name_en": "Political"}, "legal": {"emoji": "⚖️", "name_en": "Legal"}, "economic": {"emoji": "📈", "name_en": "Economic"}, "medical": {"emoji": "🏥", "name_en": "Medical"}, "scientific": {"emoji": "🔬", "name_en": "Scientific"}, "engineering": {"emoji": "🏗️", "name_en": "Engineering"}, "military": {"emoji": "🎖️", "name_en": "Military"}, "educational": {"emoji": "📚", "name_en": "Educational"}, "religious": {"emoji": "🕌", "name_en": "Religious"}, "sports": {"emoji": "⚽", "name_en": "Sports"}, "literary": {"emoji": "📖", "name_en": "Literary"}, "it": {"emoji": "💻", "name_en": "IT / Tech"}, "environmental": {"emoji": "🌿", "name_en": "Environmental"}, "agricultural": {"emoji": "🌾", "name_en": "Agricultural"}, "media": {"emoji": "📺", "name_en": "Media"}, "tourism": {"emoji": "✈️", "name_en": "Tourism"}, "general": {"emoji": "💬", "name_en": "General"}}

STYLE_OPTIONS = {"Auto-Detect": None, "🏛️ Political": "political", "⚖️ Legal": "legal", "📈 Economic": "economic", "🏥 Medical": "medical", "🔬 Scientific": "scientific", "🏗️ Engineering": "engineering", "🎖️ Military": "military", "📚 Educational": "educational", "🕌 Religious": "religious", "⚽ Sports": "sports", "📖 Literary": "literary", "💻 IT / Tech": "it", "🌿 Environmental": "environmental", "🌾 Agricultural": "agricultural", "📺 Media": "media", "✈️ Tourism": "tourism", "💬 General": "general"}

DOMAIN_KEYWORDS = {"political": ["minister", "government", "parliament", "political", "president", "وزير", "حكومة", "برلمان", "سياسة", "رئيس"], "legal": ["contract", "agreement", "legal", "court", "law", "عقد", "اتفاق", "قانون", "محكمة"], "economic": ["economic", "financial", "investment", "cost", "budget", "ربح", "اقتصاد", "مالية", "استثمار", "تكلفة"], "medical": ["doctor", "hospital", "treatment", "disease", "patient", "طبيب", "مستشفى", "علاج", "مرض", "مريض"], "scientific": ["research", "study", "experiment", "theory", "data", "بحث", "دراسة", "تجربة", "نظرية", "بيانات"], "engineering": ["engineering", "structural", "construction", "هندسة", "إنشائي", "بناء"], "military": ["military", "army", "defense", "war", "weapon", "جيش", "عسكري", "دفاع", "حرب", "سلاح"], "educational": ["school", "university", "education", "teacher", "student", "مدرسة", "جامعة", "تعليم", "معلم", "طالب"], "religious": ["mosque", "church", "prayer", "Quran", "religion", "مسجد", "كنيسة", "صلاة", "قرآن", "دين"], "sports": ["sports", "football", "stadium", "team", "player", "رياضة", "كرة القدم", "ملعب", "فريق"], "literary": ["literature", "story", "novel", "poetry", "writer", "أدب", "قصة", "رواية", "شعر", "كاتب"], "it": ["programming", "computer", "software", "website", "برمجة", "حاسوب", "برنامج", "موقع"], "environmental": ["environment", "pollution", "climate", "solar", "wind", "بيئة", "تلوث", "مناخ", "شمسية", "رياح"], "agricultural": ["agriculture", "farm", "crop", "wheat", "rice", "زراعة", "مزرعة", "محصول", "قمح", "أرز"], "media": ["media", "journalism", "television", "news", "report", "إعلام", "صحافة", "تلفزيون", "خبر", "تقرير"], "tourism": ["tourism", "hotel", "travel", "airport", "visa", "سياحة", "فندق", "سفر", "مطار", "تأشيرة"]}

def detect_domains(text):
    text_lower = text.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(text_lower.count(kw.lower()) for kw in keywords)
        if score > 0:
            scores[domain] = score
    return sorted(scores, key=scores.get, reverse=True) if scores else []

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
if "group_chat_messages" not in st.session_state:
    st.session_state.group_chat_messages = []
if "audio_key_counter" not in st.session_state:
    st.session_state.audio_key_counter = 0

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

st.markdown('<div class="section-heading">Domain Style</div>', unsafe_allow_html=True)
selected_style_label = st.selectbox("Style", style_list, index=style_idx, label_visibility="collapsed")
selected_domain = STYLE_OPTIONS[selected_style_label]
st.session_state.selected_style = selected_style_label

tab1, tab2, tab3, tab4 = st.tabs(["🎤 Voice", "📝 Text", "📄 File", "👥 Group"])

with tab1:
    st.markdown("---")
    st.markdown('<div class="section-heading">🎤 Voice Input</div>', unsafe_allow_html=True)
    if not st.session_state.deepl_api_key or not st.session_state.cohere_api_key:
        st.info("تحتاج لمفاتيح DeepL و Cohere لاستخدام هذا التبويب.")
    else:
        audio_value = st.audio_input("", key="mic_audio_main", label_visibility="collapsed")
        if audio_value is not None:
            with st.spinner("⏳ جاري التعرف..."):
                recognized_text, engine_used = speech_to_text_cohere(audio_value.getvalue(), source_lang)
                if recognized_text:
                    st.success(f"✅ {recognized_text}")
                    st.session_state.input_text = recognized_text
                    with st.spinner("⏳ جاري الترجمة..."):
                        translated_text, err = translate_text(recognized_text, target_lang)
                        if translated_text:
                            st.session_state.translated_text = translated_text
                            emotion = analyze_emotion(recognized_text)
                            st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                            st.markdown(f"""<div class="result-box"><span class="label">✦ Translation</span><div class="text">{translated_text}</div><div class="emotion">{emotion}</div></div>""", unsafe_allow_html=True)
                            st.code(translated_text, language=None)
                            audio_bytes_tts = generate_audio(translated_text, target_lang)
                            if audio_bytes_tts:
                                st.audio(audio_bytes_tts, format="audio/mp3")
                            save_translation(recognized_text, translated_text, emotion, source_lang_name, target_lang_name)
                        else:
                            st.error(f"❌ {err}")
                else:
                    st.error(f"❌ {engine_used}")

with tab2:
    st.markdown("---")
    st.markdown('<div class="section-heading">📝 Text Input</div>', unsafe_allow_html=True)
    if not st.session_state.deepl_api_key:
        st.info("تحتاج لمفتاح DeepL لترجمة النصوص.")
    else:
        input_text = st.text_area("", height=70, placeholder="اكتب أو الصق النص هنا...", value=st.session_state.input_text, key="input_text_area")
        if input_text != st.session_state.input_text:
            st.session_state.input_text = input_text
        if input_text.strip():
            detected = detect_domains(input_text)
            if detected:
                badges = ""
                for d in detected[:3]:
                    badges += f'<span class="tag">{DOMAINS[d]["emoji"]} {DOMAINS[d]["name_en"]}</span>'
                st.markdown(f'<div class="context">🔍 {badges}</div>', unsafe_allow_html=True)
        if st.button("Translate ✦", use_container_width=True, key="translate_btn"):
            if not input_text.strip():
                st.warning("الرجاء إدخال نص للترجمة.")
            else:
                with st.spinner("جاري الترجمة..."):
                    translated_text, err = translate_text(input_text, target_lang)
                    if translated_text:
                        emotion = analyze_emotion(input_text)
                        st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                        st.markdown(f"""<div class="result-box"><span class="label">✦ Translation</span><div class="text">{translated_text}</div><div class="emotion">{emotion}</div></div>""", unsafe_allow_html=True)
                        st.code(translated_text, language=None)
                        audio_bytes_tts = generate_audio(translated_text, target_lang)
                        if audio_bytes_tts:
                            st.audio(audio_bytes_tts, format="audio/mp3")
                        save_translation(input_text, translated_text, emotion, source_lang_name, target_lang_name)
                    else:
                        st.error(f"❌ {err}")

with tab3:
    st.markdown("---")
    st.markdown('<div class="section-heading">📄 File Translation</div>', unsafe_allow_html=True)
    if not st.session_state.deepl_api_key:
        st.info("تحتاج لمفتاح DeepL لترجمة الملفات.")
    else:
        uploaded_file = st.file_uploader("اختر ملف", type=None, key="file_uploader")
        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            file_size = len(file_bytes) // 1024
            st.success(f"✅ {uploaded_file.name} ({file_size} KB)")
            if st.button("🔍 استخراج النص وترجمته", key="file_btn"):
                with st.spinner("جاري استخراج النص..."):
                    extracted_text, err = extract_text_from_file(file_bytes, uploaded_file.name)
                    if extracted_text:
                        st.markdown('<div class="section-heading">Extracted Text</div>', unsafe_allow_html=True)
                        display_text = extracted_text[:1500] + ("..." if len(extracted_text) > 1500 else "")
                        st.code(display_text, language=None)
                        st.caption(f"عدد الكلمات: {len(extracted_text.split())}")
                        with st.spinner("جاري الترجمة..."):
                            translated_text, err2 = translate_text(extracted_text, target_lang)
                            if translated_text:
                                emotion = analyze_emotion(extracted_text)
                                st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                                st.markdown(f"""<div class="result-box"><span class="label">✦ Translation</span><div class="text">{translated_text}</div><div class="emotion">{emotion}</div></div>""", unsafe_allow_html=True)
                                st.code(translated_text, language=None)
                                save_translation(extracted_text[:500], translated_text, emotion, "File", target_lang_name)
                                st.download_button(label="📥 تحميل الترجمة (TXT)", data=translated_text, file_name="file_translation.txt", mime="text/plain")
                            else:
                                st.error(f"فشلت الترجمة: {err2}")
                    else:
                        st.error(f"فشل استخراج النص: {err}")

with tab4:
    st.markdown("---")
    st.markdown('<div class="section-heading">👥 Group Chat Translation</div>', unsafe_allow_html=True)
    st.caption("ترجمة فورية مع Cohere للتعرف الصوتي و DeepL للترجمة (مع Google احتياطي)")

    if not st.session_state.cohere_api_key:
        st.error("❌ تحتاج إلى مفتاح Cohere API لاستخدام التعرف الصوتي.")
    else:
        target_options = [k for k in languages_dict.keys() if k != "Auto-Detect"]
        target_lang_group = st.selectbox("ترجمة إلى", target_options, key="group_target_live")
        target_code = languages_dict[target_lang_group]

        mode = st.radio("وضع المحادثة:", ["محادثة مباشرة (متحدث واحد)", "محادثة جماعية (تسجيل واحد)"], key="mode_radio")

        if mode == "محادثة مباشرة (متحدث واحد)":
            st.markdown("---")
            source_lang_group = st.selectbox("اللغة التي ستتحدث بها", list(languages_dict.keys()), key="single_source_lang")
            source_code = languages_dict[source_lang_group]

            speaker_options = ["SPEAKER_1", "SPEAKER_2", "SPEAKER_3", "SPEAKER_4", "مخصص..."]
            selected = st.selectbox("المتحدث", speaker_options, key="single_speaker_select")
            if selected == "مخصص...":
                custom = st.text_input("أدخل الاسم", key="single_custom")
                speaker = custom.strip() if custom.strip() else "SPEAKER"
            else:
                speaker = selected

            audio_chunk = st.audio_input(f"🎤 تحدث كـ {speaker}", key=f"single_chunk_{st.session_state.audio_key_counter}")
            if audio_chunk is not None:
                with st.spinner("⏳ جارٍ النسخ والترجمة..."):
                    text, engine = speech_to_text_cohere(audio_chunk.getvalue(), source_code)
                    if text:
                        tr, err = translate_text(text, target_code)
                        if not tr:
                            tr = f"[خطأ: {err}]"
                        st.session_state.group_chat_messages.append({"speaker": speaker, "original": text, "translated": tr, "lang": source_lang_group})
                        st.session_state.audio_key_counter += 1
                        st.success(f"✅ أُضيفت رسالة {speaker}")
                        st.rerun()
                    else:
                        st.error(f"❌ فشل التعرف: {engine}")

            if st.session_state.group_chat_messages:
                st.markdown("### 💬 سجل المحادثة")
                speaker_colors = {}
                palette = ["#4ECBA0", "#FF6B6B", "#FFD93D", "#6C5CE7", "#45B7D1", "#F39C12", "#9B59B6", "#E74C3C", "#2ECC71", "#3498DB"]
                for msg in st.session_state.group_chat_messages:
                    spk = msg["speaker"]
                    if spk not in speaker_colors:
                        speaker_colors[spk] = palette[len(speaker_colors) % len(palette)]
                    color = speaker_colors[spk]
                    st.markdown(f"""<div class="chat-bubble" style="border-left-color: {color};"><div class="speaker" style="color: {color};">👤 {spk} ({msg.get('lang', '')})</div><div class="original">🎙️ {msg['original']}</div><div class="translated">🌍 {msg['translated']}</div></div>""", unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🧹 مسح", key="clear_single"):
                        st.session_state.group_chat_messages = []
                        st.rerun()
                with col2:
                    last = st.session_state.group_chat_messages[-1]["translated"]
                    if last and not last.startswith("["):
                        audio_out = generate_audio(last, target_code)
                        if audio_out:
                            st.audio(audio_out, format="audio/mp3")
                with col3:
                    full = "\n".join([f"[{m['speaker']}] 🎙️ {m['original']}\n🌍 {m['translated']}" for m in st.session_state.group_chat_messages])
                    st.download_button("📥 تحميل", full, file_name="single_chat.txt")

        else:
            st.markdown("---")
            st.write("سجّل مقطعاً صوتياً واحداً يحوي عدة أشخاص. سيتعرف Cohere على النص ويترجمه DeepL.")
            audio_chunk = st.audio_input("🎙️ اضغط للتسجيل (متعدد المتحدثين)", key="multi_speaker_audio")
            if audio_chunk is not None:
                with st.spinner("⏳ جارٍ النسخ والترجمة..."):
                    text, engine = speech_to_text_cohere(audio_chunk.getvalue(), "auto")
                    if text:
                        tr, err = translate_text(text, target_code)
                        if not tr:
                            tr = f"[خطأ: {err}]"
                        st.session_state.group_chat_messages.append({"speaker": "المجموعة", "original": text, "translated": tr, "lang": "auto"})
                        st.session_state.audio_key_counter += 1
                        st.success("✅ تمت إضافة المحادثة")
                        st.rerun()
                    else:
                        st.error(f"❌ فشل التعرف: {engine}")

            if st.session_state.group_chat_messages:
                st.markdown("### 💬 سجل المحادثة")
                for msg in st.session_state.group_chat_messages:
                    st.markdown(f"""<div class="chat-bubble"><div class="speaker">👤 {msg['speaker']}</div><div class="original">🎙️ {msg['original']}</div><div class="translated">🌍 {msg['translated']}</div></div>""", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🧹 مسح", key="clear_multi"):
                        st.session_state.group_chat_messages = []
                        st.rerun()
                with col2:
                    full = "\n".join([f"[{m['speaker']}] 🎙️ {m['original']}\n🌍 {m['translated']}" for m in st.session_state.group_chat_messages])
                    st.download_button("📥 تحميل", full, file_name="multi_chat.txt")

st.markdown("""<div style="text-align:center; padding: 1rem 0; color:rgba(100,130,170,0.3); font-size:9px; letter-spacing:0.12em; text-transform:uppercase;">HN TRANSLATOR · Voice Translation Suite</div>""", unsafe_allow_html=True)
