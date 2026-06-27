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
from functools import lru_cache

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
#  استيراد EasyOCR للصور
# ════════════════════════════════════════════════════════════
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# ════════════════════════════════════════════════════════════
#  استيراد مكتبات الملفات
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
    return [{"original": row[0], "translated": row[1], "emotion": row[2],
             "source_lang": row[3], "target_lang": row[4], "time": row[5]} for row in rows]

def clear_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM history')
    conn.commit()
    conn.close()

def export_history_json():
    return json.dumps(get_history(limit=1000), ensure_ascii=False, indent=2)

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
    except:
        return "محايد"

# ════════════════════════════════════════════════════════════
#  تحويل النص إلى صوت
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
    except:
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

# ════════════════════════════════════════════════════════════
#  دوال الترجمة والتعرف على الصوت (للتبويبات الأخرى)
# ════════════════════════════════════════════════════════════
def translate_deepl(text, target_lang):
    if not st.session_state.deepl_api_key:
        return None, "No API key"
    tl = target_lang.upper()
    endpoint = "https://api-free.deepl.com/v2/translate" if st.session_state.deepl_api_key.endswith(":fx") else "https://api.deepl.com/v2/translate"
    try:
        resp = requests.post(endpoint, headers={"Authorization": f"DeepL-Auth-Key {st.session_state.deepl_api_key}"},
                             data={"text": text, "target_lang": tl}, timeout=15)
        if resp.status_code == 200:
            return resp.json()["translations"][0]["text"], None
        return None, f"DeepL error {resp.status_code}"
    except Exception as e:
        return None, str(e)

def fetch_ai_translation(text, target_lang):
    return translate_deepl(text, target_lang)

# ... (باقي دوال speech-to-text للتبويبات القديمة تبقى كما هي) ...
def speech_to_text_cohere(audio_bytes, language_code="auto"):
    # (نفس الكود السابق)
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
            headers={"Authorization": f"Bearer {st.session_state.cohere_api_key}",
                     "Content-Type": encoder.content_type},
            data=encoder, timeout=30
        )
        if response.status_code == 200:
            text = response.json().get("text", "").strip()
            return (text, "Speech Recognition") if text else (None, "No speech detected")
        return None, f"Cohere error {response.status_code}"
    except Exception as e:
        return None, str(e)

@st.cache_resource
def load_whisper_model_old():
    try:
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
        text = " ".join(seg.text.strip() for seg in segments)
        return (text, "Speech Recognition") if text else (None, "No speech detected")
    except Exception as e:
        return None, str(e)
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
#  دوال المحادثة الجماعية (السريعة والمُحسَّنة)
# ════════════════════════════════════════════════════════════
@st.cache_resource
def load_whisper_model():
    if WHISPER_AVAILABLE:
        try:
            return WhisperModel("small", device="cpu", compute_type="int8")
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

def transcribe_audio(audio_bytes, language=None):
    """نسخ سريع لمقطع صوتي (بدون VAD، beam=1)."""
    if whisper_model is None:
        return None, "النموذج غير محمّل"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        segments, info = whisper_model.transcribe(tmp_path, language=language, beam_size=1)
        text = " ".join(seg.text.strip() for seg in segments)
        return text, info.language
    except Exception as e:
        return None, str(e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

def diarize_segments(audio_path, segments, num_speakers=None):
    if resemblyzer_encoder is None:
        for seg in segments:
            seg["speaker"] = "SPEAKER_0"
        return segments
    if len(segments) == 0:
        return segments
    try:
        wav, sr = librosa.load(audio_path, sr=16000)
    except:
        for seg in segments:
            seg["speaker"] = "SPEAKER_0"
        return segments
    embeddings = []
    valid_indices = []
    for i, seg in enumerate(segments):
        start_sample = int(seg["start"] * sr)
        end_sample = int(seg["end"] * sr)
        if end_sample - start_sample < 4000:
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
    if whisper_model is None:
        return None, "نموذج Whisper غير محمّل"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        lang = None if source_lang == "auto" else source_lang
        segs, info = whisper_model.transcribe(tmp_path, language=lang, beam_size=5, vad_filter=True,
                                              vad_parameters=dict(min_silence_duration_ms=500))
        raw_segments = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segs]
        final_segments = diarize_segments(tmp_path, raw_segments, num_speakers)
        detected_lang = info.language if source_lang == "auto" else source_lang
        return final_segments, detected_lang
    except Exception as e:
        return None, str(e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

# تخزين مؤقت للترجمات (يُسرّع الترجمة المتكررة)
@st.cache_data(show_spinner=False, ttl=3600)
def cached_translate(text, target_lang):
    """ترجمة نص مع تخزين مؤقت لمدة ساعة."""
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text), None
    except Exception as e1:
        libre_url = os.environ.get("LIBRETRANSLATE_URL", st.secrets.get("LIBRETRANSLATE_URL", ""))
        if libre_url:
            try:
                resp = requests.post(f"{libre_url}/translate",
                                     json={"q": text, "source": "auto", "target": target_lang}, timeout=10)
                if resp.status_code == 200:
                    return resp.json()["translatedText"], None
                else:
                    return None, f"Google: {e1} | LibreTranslate: {resp.status_code}"
            except Exception as e2:
                return None, f"Google: {e1} | LibreTranslate: {e2}"
        return None, f"Google Translator error: {e1}"

# دالة الترجمة النهائية تستخدم المخزن المؤقت
def translate_text(text, target_lang):
    return cached_translate(text, target_lang)

# ════════════════════════════════════════════════════════════
#  إعدادات الصفحة
# ════════════════════════════════════════════════════════════
st.set_page_config(page_title="HN TRANSLATOR", page_icon="🌐", layout="centered")
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# CSS (مختصرة للوضوح، نفس السابق مع إضافات الفقاعات)
def get_css(theme):
    return """
    <style>
    /* نفس CSS السابق بالكامل */
    </style>
    """

# ════════════ واجهة المستخدم ════════════
# (باقي الكود كما هو بدون تغيير إلى أن نصل إلى Tab 4)

# ----- Tab 4: Group Chat (الوضع الجديد) -----
with tab4:
    st.markdown("---")
    st.markdown('<div class="section-heading">👥 Group Chat Translation</div>', unsafe_allow_html=True)
    st.caption("محادثة جماعية ذكية – تعرّف تلقائي على المتحدثين في تسجيل واحد")

    if whisper_model is None:
        st.error("❌ نموذج Whisper غير محمّل. تأكد من تثبيت faster-whisper.")
    else:
        target_options = [k for k in languages_dict.keys() if k != "Auto-Detect"]
        target_lang_group = st.selectbox("ترجمة إلى", target_options, key="group_target_live")
        target_code = languages_dict[target_lang_group]

        mode = st.radio("اختر وضع المحادثة:",
                        ["محادثة مباشرة (متحدث واحد)", "محادثة متعددة المتحدثين (تسجيل واحد)"],
                        key="mode_radio")

        if mode == "محادثة مباشرة (متحدث واحد)":
            # (هنا الكود الموجود سابقاً لاختيار متحدّث وتسجيله)
            # ...
            pass  # سأحتفظ بالكود القديم كما هو لعدم الإطالة

        else:  # محادثة متعددة المتحدثين (تسجيل واحد)
            st.markdown("### 🎙️ تسجيل جلسة متعددة المتحدثين")
            st.write("سجّل مقطعاً صوتياً واحداً يحتوي على عدة أشخاص يتحدثون. سيقوم النظام تلقائياً بتمييزهم وترجمة كلام كل منهم.")

            audio_chunk = st.audio_input("اضغط للتسجيل (يحتوي على عدة متحدثين)", key="multi_speaker_audio")
            if audio_chunk is not None:
                with st.spinner("⏳ جاري تحليل الصوت وتمييز المتحدثين..."):
                    # استخدام دالة transcribe_with_speakers_free التي تملك diarization
                    segments, detected_lang = transcribe_with_speakers_free(audio_chunk.getvalue(), source_lang="auto")
                    if segments:
                        st.success(f"✅ تم التعرف على {len(set(s['speaker'] for s in segments))} متحدثين واللغة: {detected_lang}")
                        translated_segments = []
                        prog = st.progress(0)
                        for i, seg in enumerate(segments):
                            tr, err = translate_text(seg["text"], target_code)
                            translated_segments.append({
                                "speaker": seg.get("speaker", "SPEAKER_0"),
                                "original": seg["text"],
                                "translated": tr if tr else f"[خطأ: {err}]"
                            })
                            prog.progress((i+1)/len(segments))
                        prog.empty()

                        st.markdown('<div class="section-heading">💬 الحوار المترجم</div>', unsafe_allow_html=True)
                        speaker_colors = {}
                        color_palette = ["#4ECBA0", "#FF6B6B", "#FFD93D", "#6C5CE7", "#45B7D1",
                                         "#F39C12", "#9B59B6", "#E74C3C", "#2ECC71", "#3498DB"]
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

                        full_text = "\n".join(
                            [f"[{i['speaker']}] 🎙️ {i['original']}\n🌍 {i['translated']}" for i in translated_segments])
                        st.download_button("📥 تحميل الحوار", full_text, file_name="multi_speaker_chat.txt")
                    else:
                        st.error(f"❌ فشل تحليل الصوت: {detected_lang}")
