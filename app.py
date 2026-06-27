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
import torch

# ════════════════════════════════════════════════════════════
#  استيراد مكتبات الصوت والتعرف الجماعي
# ════════════════════════════════════════════════════════════
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    from sklearn.cluster import KMeans
    import librosa
    RESEMBLYZER_AVAILABLE = True
except ImportError:
    RESEMBLYZER_AVAILABLE = False

# ════════════════════════════════════════════════════════════
#  استيراد EasyOCR للصور (للملفات فقط)
# ════════════════════════════════════════════════════════════
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# ════════════════════════════════════════════════════════════
#  استيراد مكتبات الملفات (PDF, DOCX, Excel)
# ════════════════════════════════════════════════════════════
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

# ════════════════════════════════════════════════════════════
#  استيراد أدوات الترجمة والصوت
# ════════════════════════════════════════════════════════════
from deep_translator import GoogleTranslator
from gtts import gTTS

# ════════════════════════════════════════════════════════════
#  قاعدة بيانات SQLite
# ════════════════════════════════════════════════════════════
DB_PATH = "translations.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original TEXT NOT NULL,
            translated TEXT NOT NULL,
            emotion TEXT,
            source_lang TEXT,
            target_lang TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_translation(original, translated, emotion, source_lang, target_lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO history (original, translated, emotion, source_lang, target_lang, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (original, translated, emotion, source_lang, target_lang, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_history(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT original, translated, emotion, source_lang, target_lang, timestamp
        FROM history
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "original": row[0],
            "translated": row[1],
            "emotion": row[2],
            "source_lang": row[3],
            "target_lang": row[4],
            "time": row[5]
        }
        for row in rows
    ]

def clear_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM history')
    conn.commit()
    conn.close()

def export_history_json():
    history = get_history(limit=1000)
    return json.dumps(history, ensure_ascii=False, indent=2)

init_db()

# ════════════════════════════════════════════════════════════
#  تحليل المشاعر
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_emotion_classifier():
    try:
        return pipeline("text-classification", model="nlptown/bert-base-multilingual-uncased-sentiment")
    except Exception as e:
        st.warning(f"⚠️ فشل تحميل النموذج: {e}")
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

# ════════════════════════════════════════════════════════════
#  تحويل النص إلى صوت (gTTS)
# ════════════════════════════════════════════════════════════
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
    except Exception:
        return None

# ════════════════════════════════════════════════════════════
#  استخراج النص من الملفات
# ════════════════════════════════════════════════════════════
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
            if text.strip():
                return text.strip(), None
            return None, "لم يتم العثور على نص في ملف PDF"
        except Exception as e:
            return None, str(e)
    
    elif ext == '.docx':
        if not DOCX_AVAILABLE:
            return None, "مكتبة python-docx غير مثبتة"
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            if text.strip():
                return text.strip(), None
            return None, "لم يتم العثور على نص في ملف DOCX"
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
            if text.strip():
                return text.strip(), None
            return None, "لم يتم العثور على نص في ملف Excel"
        except Exception as e:
            return None, str(e)
    
    elif ext == '.txt':
        try:
            text = file_bytes.decode('utf-8')
            if text.strip():
                return text.strip(), None
            return None, "الملف فارغ"
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode('windows-1256')
                if text.strip():
                    return text.strip(), None
            except:
                pass
            return None, "تعذر قراءة الملف، تأكد من أنه نص عادي"
    
    else:
        return None, f"نوع الملف غير مدعوم: {ext}"

# ════════════════════════════════════════════════════════════
#  دوال الترجمة والتعرف على الصوت (Voice / Text / File)
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
def load_whisper_model_old():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("small", device="cpu", compute_type="int8")
    except:
        return None

def speech_to_text_whisper(audio_bytes):
    model = load_whisper_model_old()
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
#  دوال المحادثة الجماعية (مجانية بالكامل، بدون HF Token)
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_whisper_model():
    if WHISPER_AVAILABLE:
        try:
            # نموذج medium لدقة أفضل، يمكن تغييره لـ "large-v3" لو توفرت موارد
            return WhisperModel("medium", device="cpu", compute_type="int8")
        except:
            return None
    return None

@st.cache_resource
def load_resemblyzer_encoder():
    if RESEMBLYZER_AVAILABLE:
        return VoiceEncoder()
    return None

whisper_model = load_whisper_model()
resemblyzer_encoder = load_resemblyzer_encoder()

def diarize_segments(audio_path, segments, num_speakers=None):
    """تجميع المقاطع الصوتية حسب المتحدث باستخدام Resemblyzer + KMeans."""
    if resemblyzer_encoder is None:
        for seg in segments:
            seg["speaker"] = "SPEAKER_0"
        return segments

    if len(segments) == 0:
        return segments

    try:
        wav, sr = librosa.load(audio_path, sr=16000)
    except Exception:
        for seg in segments:
            seg["speaker"] = "SPEAKER_0"
        return segments

    embeddings = []
    valid_indices = []
    for i, seg in enumerate(segments):
        start_sample = int(seg["start"] * sr)
        end_sample = int(seg["end"] * sr)
        if end_sample - start_sample < 4000:  # أقل من 0.25 ثانية نتجاهل
            continue
        snippet = wav[start_sample:end_sample]
        if np.abs(snippet).max() < 0.01:
            continue
        try:
            snippet = preprocess_wav(snippet, source_sr=sr)
            if snippet is None or len(snippet) == 0:
                continue
            embed = resemblyzer_encoder.embed_utterance(snippet)
            embeddings.append(embed)
            valid_indices.append(i)
        except:
            continue

    if len(embeddings) == 0:
        for seg in segments:
            seg["speaker"] = "SPEAKER_0"
        return segments

    if num_speakers is None or num_speakers <= 0:
        max_speakers = min(10, len(embeddings))
        inertias = []
        K_range = range(1, max_speakers + 1)
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(embeddings)
            inertias.append(kmeans.inertia_)
        if len(K_range) > 1:
            diffs = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
            best_k = np.argmax(diffs) + 1
        else:
            best_k = 1
        num_speakers = best_k

    kmeans = KMeans(n_clusters=num_speakers, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    for idx, label in zip(valid_indices, labels):
        segments[idx]["speaker"] = f"SPEAKER_{label}"
    for i, seg in enumerate(segments):
        if "speaker" not in seg:
            closest = min(valid_indices, key=lambda j: abs(segments[j]["start"] - seg["start"]), default=None)
            seg["speaker"] = segments[closest]["speaker"] if closest is not None else "SPEAKER_0"

    return segments

def transcribe_with_speakers_free(audio_bytes, source_lang="auto", num_speakers=None):
    """تحويل الصوت إلى نص مع تمييز المتحدثين (بدون Hugging Face Token)."""
    if whisper_model is None:
        return None, "نموذج Whisper غير محمّل"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        lang = None if source_lang == "auto" else source_lang
        segs, info = whisper_model.transcribe(
            tmp_path,
            language=lang,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        raw_segments = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segs]
        final_segments = diarize_segments(tmp_path, raw_segments, num_speakers)
        detected_lang = info.language if source_lang == "auto" else source_lang
        return final_segments, detected_lang
    except Exception as e:
        return None, str(e)
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except:
            pass

def translate_text(text, target_lang):
    """ترجمة النص مع احتياطي LibreTranslate إذا وُجد."""
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text), None
    except Exception as e1:
        libre_url = os.environ.get("LIBRETRANSLATE_URL", st.secrets.get("LIBRETRANSLATE_URL", ""))
        if libre_url:
            try:
                resp = requests.post(
                    f"{libre_url}/translate",
                    json={"q": text, "source": "auto", "target": target_lang},
                    timeout=10
                )
                if resp.status_code == 200:
                    return resp.json()["translatedText"], None
                else:
                    return None, f"Google: {e1} | LibreTranslate: {resp.status_code}"
            except Exception as e2:
                return None, f"Google: {e1} | LibreTranslate: {e2}"
        return None, f"Google Translator error: {e1} (يمكنك توفير LIBRETRANSLATE_URL)"

# ════════════════════════════════════════════════════════════
#  إعدادات الصفحة
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="HN TRANSLATOR",
    page_icon="🌐",
    layout="centered"
)

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# ════════════════════════════════════════════════════════════
#  CSS (كما هو سابقاً مع إضافة فقاعات المحادثة)
# ════════════════════════════════════════════════════════════
def get_css(theme):
    if theme == "light":
        return """
        .stApp { background: #f5f7fa !important; }
        .app-header { text-align: center; padding: 0.8rem 0 0.5rem 0; position: relative; }
        .app-header .brand { font-family: 'Space Grotesk', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.3em; color: #2a7a60; text-transform: uppercase; display: block; margin-bottom: 0.2rem; opacity: 0.8; }
        .app-header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 32px; font-weight: 700; color: #1a1a2e; margin: 0; letter-spacing: -0.02em; }
        .app-header h1 .accent { color: #2a7a60; }
        .app-header .divider { width: 60px; height: 3px; background: linear-gradient(90deg, #2a7a60, transparent); margin: 0.3rem auto 0; border-radius: 2px; }
        .stButton > button { background: #2a7a60 !important; color: white !important; }
        .stButton > button:hover { background: #1a5a48 !important; }
        textarea { background: white !important; color: #1a1a2e !important; border: 1px solid #ccc !important; }
        .result-box { background: rgba(42,122,96,0.06); border: 1px solid rgba(42,122,96,0.2); border-radius: 12px; padding: 0.5rem 0.8rem; margin-top: 0.4rem; }
        .result-box .label { font-size: 8px; font-weight: 700; text-transform: uppercase; color: rgba(42,122,96,0.7); letter-spacing: 0.15em; }
        .result-box .text { font-size: 14px; color: #1a1a2e; }
        .result-box .emotion { font-size: 13px; color: #2a7a60; font-weight: 500; margin-top: 4px; }
        .stSelectbox > div > div { background: white !important; color: #1a1a2e !important; border-color: #ccc !important; }
        .stSelectbox label { color: #2a7a60 !important; }
        [data-testid="stSidebar"] { background: rgba(255,255,255,0.98) !important; border-right: 1px solid #ddd !important; }
        .history-item { padding: 6px 10px; margin-bottom: 4px; border-bottom: 1px solid rgba(0,0,0,0.05); }
        .history-item .original { font-size: 12px; color: #1a1a2e; }
        .history-item .translated { font-size: 12px; color: #2a7a60; }
        div[data-testid="stAudioInput"] > div { background: rgba(42,122,96,0.08); border: 2px solid rgba(42,122,96,0.3); border-radius: 60px; }
        div[data-testid="stAudioInput"] button { color: #1a1a2e !important; }
        .stCode, code, pre { background: #f0f0f0 !important; color: #1a1a2e !important; border: 1px solid #ddd !important; border-radius: 8px !important; }
        .section-heading { font-size: 9px; font-weight: 700; text-transform: uppercase; color: #2a7a60; margin: 0.6rem 0 0.3rem; }
        hr { margin: 0.5rem 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(42,122,96,0.2), transparent); }
        button[data-baseweb="tab"] {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #1a1a2e !important;
            background: transparent !important;
            border: none !important;
            padding: 0.5rem 1.2rem !important;
            border-radius: 8px 8px 0 0 !important;
            transition: all 0.3s ease !important;
        }
        button[data-baseweb="tab"]:hover {
            background: rgba(42,122,96,0.08) !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: rgba(42,122,96,0.12) !important;
            color: #2a7a60 !important;
            border-bottom: 2px solid #2a7a60 !important;
        }
        div[data-baseweb="tab-list"] {
            gap: 4px !important;
            border-bottom: 1px solid rgba(0,0,0,0.08) !important;
            padding-bottom: 0 !important;
        }
        .chat-bubble {
            margin: 10px 0;
            border-radius: 15px;
            padding: 12px;
            background: rgba(42,122,96,0.05);
            border-left: 5px solid #2a7a60;
        }
        .chat-bubble .speaker {
            font-weight: bold;
            margin-bottom: 5px;
            color: #2a7a60;
        }
        .chat-bubble .original { color: #333; font-size: 14px; }
        .chat-bubble .translated { color: #1a5a48; font-size: 14px; margin-top: 5px; }
        """
    else:
        return """
        .stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0f1728 40%, #0a1520 100%) !important; }
        .app-header { text-align: center; padding: 0.8rem 0 0.5rem 0; position: relative; }
        .app-header .brand { font-family: 'Space Grotesk', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.3em; color: #4ECBA0; text-transform: uppercase; display: block; margin-bottom: 0.2rem; opacity: 0.8; }
        .app-header h1 { font-family: 'Space Grotesk', sans-serif; font-size: 32px; font-weight: 700; color: #f0f4ff; margin: 0; letter-spacing: -0.02em; }
        .app-header h1 .accent { color: #4ECBA0; }
        .app-header .divider { width: 60px; height: 3px; background: linear-gradient(90deg, #4ECBA0, transparent); margin: 0.3rem auto 0; border-radius: 2px; }
        .stButton > button { background: linear-gradient(135deg, #4ECBA0 0%, #2fa87a 100%) !important; color: #0a1520 !important; }
        .stButton > button:hover { background: linear-gradient(135deg, #5ed9b0 0%, #3dbf8a 100%) !important; }
        textarea { background: #1a1a2e !important; color: #f0f4ff !important; border: 1px solid rgba(255,255,255,0.15) !important; }
        .result-box { background: rgba(78,203,160,0.06); border: 1px solid rgba(78,203,160,0.2); border-radius: 12px; padding: 0.5rem 0.8rem; margin-top: 0.4rem; }
        .result-box .label { font-size: 8px; font-weight: 700; text-transform: uppercase; color: rgba(78,203,160,0.7); letter-spacing: 0.15em; }
        .result-box .text { font-size: 14px; color: #e8f0ff; }
        .result-box .emotion { font-size: 13px; color: #4ECBA0; font-weight: 500; margin-top: 4px; }
        .stSelectbox > div > div { background: rgba(255,255,255,0.05) !important; color: #e8f0ff !important; border-color: rgba(255,255,255,0.12) !important; }
        .stSelectbox label { color: rgba(78,203,160,0.75) !important; }
        [data-testid="stSidebar"] { background: rgba(10,10,26,0.98) !important; border-right: 1px solid rgba(78,203,160,0.1) !important; }
        .history-item { padding: 6px 10px; margin-bottom: 4px; border-bottom: 1px solid rgba(78,203,160,0.1); }
        .history-item .original { font-size: 12px; color: #e8f0ff; }
        .history-item .translated { font-size: 12px; color: #4ECBA0; }
        div[data-testid="stAudioInput"] > div { background: rgba(78,203,160,0.08); border: 2px solid rgba(78,203,160,0.3); border-radius: 60px; }
        div[data-testid="stAudioInput"] button { color: #e8f0ff !important; }
        .stCode, code, pre { background: rgba(0,0,0,0.35) !important; color: #a8f0d8 !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 8px !important; }
        .section-heading { font-size: 9px; font-weight: 700; text-transform: uppercase; color: rgba(150,185,230,0.5); margin: 0.6rem 0 0.3rem; }
        hr { margin: 0.5rem 0; border: none; height: 1px; background: linear-gradient(90deg, transparent, rgba(78,203,160,0.2), transparent); }
        button[data-baseweb="tab"] {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #b0c4de !important;
            background: transparent !important;
            border: none !important;
            padding: 0.5rem 1.2rem !important;
            border-radius: 8px 8px 0 0 !important;
            transition: all 0.3s ease !important;
        }
        button[data-baseweb="tab"]:hover {
            background: rgba(78,203,160,0.06) !important;
            color: #e8f0ff !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: rgba(78,203,160,0.1) !important;
            color: #4ECBA0 !important;
            border-bottom: 2px solid #4ECBA0 !important;
        }
        div[data-baseweb="tab-list"] {
            gap: 4px !important;
            border-bottom: 1px solid rgba(78,203,160,0.1) !important;
            padding-bottom: 0 !important;
        }
        .chat-bubble {
            margin: 10px 0;
            border-radius: 15px;
            padding: 12px;
            background: rgba(255,255,255,0.05);
            border-left: 5px solid #4ECBA0;
        }
        .chat-bubble .speaker {
            font-weight: bold;
            margin-bottom: 5px;
            color: #4ECBA0;
        }
        .chat-bubble .original { color: #ccc; font-size: 14px; }
        .chat-bubble .translated { color: #a8f0d8; font-size: 14px; margin-top: 5px; }
        """

st.markdown(f"<style>{get_css(st.session_state.theme)}</style>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  العنوان
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <span class="brand">✦ Smart Voice Translator ✦</span>
    <h1>HN <span class="accent">TRANSLATOR</span></h1>
    <div class="divider"></div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  الشريط الجانبي
# ════════════════════════════════════════════════════════════
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
            st.markdown(f"""
            <div class="history-item">
                <div class="original">{item.get('original', '')}</div>
                <div class="translated">{item.get('translated', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("📤", help="تصدير السجل (JSON)", use_container_width=True):
            json_str = export_history_json()
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="translation_history.json">📥 تحميل</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center; color: rgba(150,175,220,0.3); font-size: 30px;'>📭</div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  الإعدادات الأساسية
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
#  API KEYS (لـ Voice, Text, File)
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
if "group_chunks" not in st.session_state:
    st.session_state.group_chunks = []

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
#  واجهة المستخدم
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

# ════════════════════════════════════════════════════════════
#  التبويبات
# ════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["🎤 Voice", "📝 Text", "📄 File", "👥 Group"])

# ----- Tab 1: Voice (يحتاج DeepL + Cohere) -----
with tab1:
    st.markdown("---")
    st.markdown('<div class="section-heading">🎤 Voice Input</div>', unsafe_allow_html=True)

    if not st.session_state.deepl_api_key or not st.session_state.cohere_api_key:
        st.info("تحتاج لمفاتيح DeepL و Cohere لاستخدام هذا التبويب.")
    else:
        col_mic, col_clear = st.columns([5, 1])
        with col_mic:
            audio_value = st.audio_input("", key="mic_audio_main", label_visibility="collapsed")
        with col_clear:
            if "mic_audio_main" in st.session_state and st.session_state.mic_audio_main is not None:
                if st.button("✖", key="clear_btn", help="حذف التسجيل", type="secondary"):
                    clear_audio()
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
                            st.markdown(f"""
                            <div class="result-box">
                                <span class="label">✦ Translation</span>
                                <div class="text">{translated_text}</div>
                                <div class="emotion">{emotion}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.code(translated_text, language=None)
                            audio_bytes_tts = generate_audio(translated_text, target_lang)
                            if audio_bytes_tts:
                                st.audio(audio_bytes_tts, format="audio/mp3")
                            save_translation(recognized_text, translated_text, emotion, source_lang_name, target_lang_name)
                        else:
                            st.error(f"❌ {engine}")
                else:
                    st.error(f"❌ {engine_used}")

# ----- Tab 2: Text (يحتاج DeepL) -----
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
                    dn = DOMAINS[d]["name_en"]
                    emoji = DOMAINS[d]["emoji"]
                    badges += f'<span class="tag">{emoji} {dn}</span>'
                st.markdown(f'<div class="context">🔍 {badges}</div>', unsafe_allow_html=True)
        if st.button("Translate ✦", use_container_width=True, key="translate_btn"):
            if not input_text.strip():
                st.warning("الرجاء إدخال نص للترجمة.")
            else:
                with st.spinner("جاري الترجمة..."):
                    translation_result, _ = fetch_ai_translation(input_text, target_lang)
                    if translation_result:
                        emotion = analyze_emotion(input_text)
                        st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="result-box">
                            <span class="label">✦ Translation</span>
                            <div class="text">{translation_result}</div>
                            <div class="emotion">{emotion}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.code(translation_result, language=None)
                        audio_bytes_tts = generate_audio(translation_result, target_lang)
                        if audio_bytes_tts:
                            st.audio(audio_bytes_tts, format="audio/mp3")
                        save_translation(input_text, translation_result, emotion, source_lang_name, target_lang_name)
                    else:
                        st.error(f"❌ {translation_result}")

# ----- Tab 3: File (يحتاج DeepL) -----
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
                            translated_text, _ = fetch_ai_translation(extracted_text, target_lang)
                            if translated_text:
                                emotion = analyze_emotion(extracted_text)
                                st.markdown('<div class="section-heading">Translation Result</div>', unsafe_allow_html=True)
                                st.markdown(f"""
                                <div class="result-box">
                                    <span class="label">✦ Translation</span>
                                    <div class="text">{translated_text}</div>
                                    <div class="emotion">{emotion}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                st.code(translated_text, language=None)
                                save_translation(extracted_text[:500], translated_text, emotion, "File", target_lang_name)
                                st.download_button(
                                    label="📥 تحميل الترجمة (TXT)",
                                    data=translated_text,
                                    file_name="file_translation.txt",
                                    mime="text/plain"
                                )
                            else:
                                st.error("فشلت الترجمة")
                    else:
                        st.error(f"فشل استخراج النص: {err}")

# ----- Tab 4: Group Chat (مجاني بالكامل، بدون Hugging Face Token) -----
with tab4:
    st.markdown("---")
    st.markdown('<div class="section-heading">👥 Group Chat Translation (مجاني)</div>', unsafe_allow_html=True)
    st.caption("ترجمة المحادثات الجماعية مع تمييز المتحدثين · بدون الحاجة إلى Hugging Face Token")
    
    if whisper_model is None or resemblyzer_encoder is None:
        st.error("❌ النماذج غير متاحة. تأكد من تثبيت faster-whisper و resemblyzer و scikit-learn و librosa.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            source_lang_group = st.selectbox("اللغة المنطوقة (أو تلقائي)", list(languages_dict.keys()), key="group_source_free")
        with col2:
            target_options = [k for k in languages_dict.keys() if k != "Auto-Detect"]
            target_lang_group = st.selectbox("اللغة الهدف للترجمة", target_options, key="group_target_free")
        
        source_code = languages_dict[source_lang_group]
        target_code = languages_dict[target_lang_group]
        
        num_speakers = st.number_input("عدد المتحدثين المتوقع (اختياري، اترك 0 للتلقائي)", min_value=0, max_value=20, value=0, key="num_speakers")
        num_speakers = num_speakers if num_speakers > 0 else None
        
        mode = st.radio("اختر وضع الإدخال:", ["رفع ملف صوتي (اجتماع مسجل)", "تسجيل مباشر (مقاطع متعددة)"], key="mode_radio")
        
        if mode == "رفع ملف صوتي (اجتماع مسجل)":
            audio_file = st.file_uploader("اختر ملف صوتي (WAV, MP3, M4A)", type=["wav", "mp3", "m4a"], key="group_audio_free")
            if audio_file is not None:
                file_bytes = audio_file.getvalue()
                file_size = len(file_bytes) // 1024
                st.success(f"✅ {audio_file.name} ({file_size} KB)")
                if st.button("🚀 تحليل وترجمة المحادثة", key="group_free_btn"):
                    with st.spinner("⏳ جاري التعرف على المتحدثين وترجمة الحوار..."):
                        segments, detected_lang = transcribe_with_speakers_free(file_bytes, source_code, num_speakers)
                        if segments:
                            lang_display = detected_lang if isinstance(detected_lang, str) else "تلقائي"
                            st.info(f"اللغة المكتشفة: {lang_display}")
                            translated_segments = []
                            progress_bar = st.progress(0)
                            for idx, seg in enumerate(segments):
                                text = seg["text"]
                                speaker = seg["speaker"]
                                translated_text, err2 = translate_text(text, target_code)
                                if translated_text:
                                    translated_segments.append({
                                        "speaker": speaker,
                                        "original": text,
                                        "translated": translated_text
                                    })
                                else:
                                    translated_segments.append({
                                        "speaker": speaker,
                                        "original": text,
                                        "translated": f"[خطأ: {err2}]"
                                    })
                                progress_bar.progress((idx + 1) / len(segments))
                            progress_bar.empty()
                            
                            st.markdown('<div class="section-heading">💬 المحادثة المترجمة</div>', unsafe_allow_html=True)
                            speaker_colors = {}
                            color_palette = ["#4ECBA0", "#FF6B6B", "#FFD93D", "#6C5CE7", "#45B7D1", "#F39C12", "#9B59B6", "#E74C3C", "#2ECC71", "#3498DB"]
                            for item in translated_segments:
                                spk = item["speaker"]
                                if spk not in speaker_colors:
                                    speaker_colors[spk] = color_palette[len(speaker_colors) % len(color_palette)]
                                color = speaker_colors[spk]
                                st.markdown(f"""
                                <div class="chat-bubble" style="border-left-color: {color};">
                                    <div class="speaker" style="color: {color};">👤 {spk}</div>
                                    <div class="original">🎙️ {item['original']}</div>
                                    <div class="translated">🌍 {item['translated']}</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            full_text = "\n".join([f"[{item['speaker']}] 🎙️ {item['original']}\n🌍 {item['translated']}" for item in translated_segments])
                            st.code(full_text, language=None)
                            
                            if translated_segments:
                                last_translated = translated_segments[-1]["translated"]
                                if last_translated and not last_translated.startswith("[خطأ"):
                                    audio_bytes_tts = generate_audio(last_translated, target_code)
                                    if audio_bytes_tts:
                                        st.audio(audio_bytes_tts, format="audio/mp3")
                            
                            save_translation("محادثة جماعية", full_text, analyze_emotion(full_text), "Group", target_lang_group)
                            st.download_button(
                                label="📥 تحميل الترجمة كاملة (TXT)",
                                data=full_text,
                                file_name="group_translation.txt",
                                mime="text/plain"
                            )
                        else:
                            st.error(f"❌ فشل المعالجة: {detected_lang if isinstance(detected_lang, str) else 'خطأ'}")
        else:  # تسجيل مباشر
            st.info("سيتم تسجيل عدة مقاطع صوتية متتالية، ثم تحليلها معًا.")
            audio_chunk = st.audio_input("تحدث الآن (اضغط لإضافة مقطع)", key="live_chunk")
            if audio_chunk:
                st.session_state.group_chunks.append(audio_chunk.getvalue())
                st.success(f"تمت إضافة مقطع #{len(st.session_state.group_chunks)}")
                st.rerun()
            
            if st.session_state.group_chunks:
                st.write(f"المقاطع المسجلة: {len(st.session_state.group_chunks)}")
                if st.button("🧹 مسح جميع المقاطع", key="clear_chunks"):
                    st.session_state.group_chunks = []
                    st.rerun()
                if st.button("🚀 تحليل المحادثة المجمعة", key="process_live"):
                    with st.spinner("⏳ جاري دمج المقاطع وتحليلها..."):
                        full_audio = b''.join(st.session_state.group_chunks)
                        segments, detected_lang = transcribe_with_speakers_free(full_audio, source_code, num_speakers)
                        if segments:
                            lang_display = detected_lang if isinstance(detected_lang, str) else "تلقائي"
                            st.info(f"اللغة المكتشفة: {lang_display}")
                            translated_segments = []
                            progress_bar = st.progress(0)
                            for idx, seg in enumerate(segments):
                                text = seg["text"]
                                speaker = seg["speaker"]
                                translated_text, err2 = translate_text(text, target_code)
                                if translated_text:
                                    translated_segments.append({
                                        "speaker": speaker,
                                        "original": text,
                                        "translated": translated_text
                                    })
                                else:
                                    translated_segments.append({
                                        "speaker": speaker,
                                        "original": text,
                                        "translated": f"[خطأ: {err2}]"
                                    })
                                progress_bar.progress((idx + 1) / len(segments))
                            progress_bar.empty()
                            
                            st.markdown('<div class="section-heading">💬 المحادثة المترجمة</div>', unsafe_allow_html=True)
                            speaker_colors = {}
                            color_palette = ["#4ECBA0", "#FF6B6B", "#FFD93D", "#6C5CE7", "#45B7D1", "#F39C12", "#9B59B6", "#E74C3C", "#2ECC71", "#3498DB"]
                            for item in translated_segments:
                                spk = item["speaker"]
                                if spk not in speaker_colors:
                                    speaker_colors[spk] = color_palette[len(speaker_colors) % len(color_palette)]
                                color = speaker_colors[spk]
                                st.markdown(f"""
                                <div class="chat-bubble" style="border-left-color: {color};">
                                    <div class="speaker" style="color: {color};">👤 {spk}</div>
                                    <div class="original">🎙️ {item['original']}</div>
                                    <div class="translated">🌍 {item['translated']}</div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            full_text = "\n".join([f"[{item['speaker']}] 🎙️ {item['original']}\n🌍 {item['translated']}" for item in translated_segments])
                            st.code(full_text, language=None)
                            
                            if translated_segments:
                                last = translated_segments[-1]["translated"]
                                if last and not last.startswith("[خطأ"):
                                    aud = generate_audio(last, target_code)
                                    if aud:
                                        st.audio(aud, format="audio/mp3")
                            save_translation("محادثة مباشرة", full_text, analyze_emotion(full_text), "Group", target_lang_group)
                            st.download_button("📥 تحميل الترجمة", full_text, file_name="group_live_translation.txt")
                        else:
                            st.error(f"❌ فشل المعالجة: {detected_lang if isinstance(detected_lang, str) else 'خطأ'}")

# Footer
st.markdown("""
<div style="text-align:center; padding: 1rem 0; color:rgba(100,130,170,0.3); font-size:9px; letter-spacing:0.12em; text-transform:uppercase;">
    HN TRANSLATOR · Voice Translation Suite
</div>
""", unsafe_allow_html=True)
