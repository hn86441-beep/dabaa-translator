import streamlit as st
import requests
import json
from pathlib import Path
import tempfile
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict

# ════════════════════════════════════════════════════════════
#  CONFIG & SETUP (المفاتيح والمكتبات)
# ════════════════════════════════════════════════════════════
st.set_page_config(page_title="HASSAN NASSER | Voice Translator", page_icon="🎤", layout="wide")

# ... (CSS الخاص بك يظل كما هو دون تغيير في هذا الجزء) ...

# ════════════════════════════════════════════════════════════
#  SPEECH-TO-TEXT ENGINES (COHERE + DEEPGRAM)
# ════════════════════════════════════════════════════════════

def speech_to_text_cohere(audio_bytes, language_code):
    if not st.session_state.cohere_api_key:
        return None, "مفتاح Cohere API غير موجود."
    try:
        fields = OrderedDict([
            ('language', language_code),
            ('model', 'cohere-transcribe-03-2026'),
            ('file', ('audio.wav', audio_bytes, 'audio/wav'))
        ])
        encoder = MultipartEncoder(fields=fields)
        response = requests.post(
            "https://api.cohere.com/v2/audio/transcriptions",
            headers={"Authorization": f"Bearer {st.session_state.cohere_api_key}", "Content-Type": encoder.content_type},
            data=encoder, timeout=45
        )
        if response.status_code == 200:
            text = response.json().get("text", "").strip()
            return (text, "Cohere Transcribe") if text else (None, "لم يتم التعرف على كلام")
        return None, f"Cohere error {response.status_code}"
    except Exception as e:
        return None, str(e)

def speech_to_text_deepgram(audio_bytes, language_code):
    # نستخدم مفتاحك المعتمد هنا
    api_key = "36227b819e619b5dfec352e7b4c2bc4b97bab743"
    url = f"https://api.deepgram.com/v1/listen?model=nova-2&language={language_code}&smart_format=true"
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "audio/wav"}
    try:
        response = requests.post(url, headers=headers, data=audio_bytes)
        if response.status_code == 200:
            transcript = response.json()['results']['channels'][0]['alternatives'][0]['transcript']
            return transcript, "Deepgram Nova-2"
        return None, f"Deepgram Error: {response.text}"
    except Exception as e:
        return None, str(e)

# المبدل الذكي (Engine Switcher)
def speech_to_text(audio_bytes, language_code):
    # إذا كانت اللغة روسية، استخدم Deepgram، وإلا استخدم Cohere
    if language_code == "ru":
        return speech_to_text_deepgram(audio_bytes, language_code)
    return speech_to_text_cohere(audio_bytes, language_code)

# ════════════════════════════════════════════════════════════
#  بقية منطق البرنامج (كما هو في كودك الأصلي)
# ════════════════════════════════════════════════════════════

# (قم بلصق بقية كود UI الخاص بك هنا، مع ملاحظة أن استدعاء speech_to_text 
#  سيعمل تلقائياً مع المحرك الصحيح حسب اللغة التي يختارها المستخدم)

# مثال لطريقة الاستدعاء في جزء الـ Voice Input:
# recognized_text, engine_used = speech_to_text(audio_bytes, source_lang)
# st.success(f"✅ تم التعرف ({engine_used}): {recognized_text}")
