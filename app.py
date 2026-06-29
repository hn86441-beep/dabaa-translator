import streamlit as st
st.set_page_config(page_title="HN TRANSLATOR", page_icon="🌐", layout="wide")

import requests, os, json, tempfile, io, base64, sqlite3, re
from requests_toolbelt.multipart.encoder import MultipartEncoder
from collections import OrderedDict
from datetime import datetime
from PIL import Image

try: import pdfplumber;  PDF_OK=True
except: PDF_OK=False
try: import docx;        DOCX_OK=True
except: DOCX_OK=False
try: import openpyxl;    EXCEL_OK=True
except: EXCEL_OK=False
try:
    from langdetect import detect as _ld, DetectorFactory
    DetectorFactory.seed=42; LD_OK=True
except: LD_OK=False

from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS

# ═══════════════════════════════════════════════════════════
#  LANGUAGES
# ═══════════════════════════════════════════════════════════
LANGS = {
    "Auto-Detect":{"g":"auto",  "d":None,    "tts":"en",    "w":None},
    "Arabic":     {"g":"ar",    "d":"AR",    "tts":"ar",    "w":"ar"},
    "English":    {"g":"en",    "d":"EN-US", "tts":"en",    "w":"en"},
    "Russian":    {"g":"ru",    "d":"RU",    "tts":"ru",    "w":"ru"},
    "Chinese":    {"g":"zh-CN", "d":"ZH",    "tts":"zh-cn", "w":"zh"},
    "German":     {"g":"de",    "d":"DE",    "tts":"de",    "w":"de"},
    "Spanish":    {"g":"es",    "d":"ES",    "tts":"es",    "w":"es"},
    "French":     {"g":"fr",    "d":"FR",    "tts":"fr",    "w":"fr"},
    "Portuguese": {"g":"pt",    "d":"PT-PT", "tts":"pt",    "w":"pt"},
    "Italian":    {"g":"it",    "d":"IT",    "tts":"it",    "w":"it"},
    "Japanese":   {"g":"ja",    "d":"JA",    "tts":"ja",    "w":"ja"},
    "Korean":     {"g":"ko",    "d":"KO",    "tts":"ko",    "w":"ko"},
    "Turkish":    {"g":"tr",    "d":"TR",    "tts":"tr",    "w":"tr"},
    "Dutch":      {"g":"nl",    "d":"NL",    "tts":"nl",    "w":"nl"},
    "Polish":     {"g":"pl",    "d":"PL",    "tts":"pl",    "w":"pl"},
    "Ukrainian":  {"g":"uk",    "d":"UK",    "tts":"uk",    "w":"uk"},
    "Swedish":    {"g":"sv",    "d":"SV",    "tts":"sv",    "w":"sv"},
    "Danish":     {"g":"da",    "d":"DA",    "tts":"da",    "w":"da"},
    "Finnish":    {"g":"fi",    "d":"FI",    "tts":"fi",    "w":"fi"},
    "Romanian":   {"g":"ro",    "d":"RO",    "tts":"ro",    "w":"ro"},
    "Hungarian":  {"g":"hu",    "d":"HU",    "tts":"hu",    "w":"hu"},
    "Czech":      {"g":"cs",    "d":"CS",    "tts":"cs",    "w":"cs"},
    "Bulgarian":  {"g":"bg",    "d":"BG",    "tts":"bg",    "w":"bg"},
    "Greek":      {"g":"el",    "d":"EL",    "tts":"el",    "w":"el"},
    "Indonesian": {"g":"id",    "d":"ID",    "tts":"id",    "w":"id"},
    "Hindi":      {"g":"hi",    "d":None,    "tts":"hi",    "w":"hi"},
    "Persian":    {"g":"fa",    "d":None,    "tts":"fa",    "w":"fa"},
    "Hebrew":     {"g":"iw",    "d":None,    "tts":"iw",    "w":"he"},
    "Urdu":       {"g":"ur",    "d":None,    "tts":"ur",    "w":"ur"},
}
LN         = list(LANGS.keys())
LN_NO_AUTO = [k for k in LN if k != "Auto-Detect"]
LC2N = {
    "ar":"Arabic","en":"English","ru":"Russian","zh-cn":"Chinese","zh":"Chinese",
    "de":"German","es":"Spanish","fr":"French","pt":"Portuguese","it":"Italian",
    "ja":"Japanese","ko":"Korean","tr":"Turkish","nl":"Dutch","pl":"Polish",
    "uk":"Ukrainian","sv":"Swedish","da":"Danish","fi":"Finnish","ro":"Romanian",
    "hu":"Hungarian","cs":"Czech","bg":"Bulgarian","el":"Greek","id":"Indonesian",
    "hi":"Hindi","fa":"Persian","he":"Hebrew","ur":"Urdu",
}

# ═══════════════════════════════════════════════════════════
#  DATABASE
# ═══════════════════════════════════════════════════════════
_DB = os.path.join(tempfile.gettempdir(), "hn_v4.db")
def _db(): return sqlite3.connect(_DB, timeout=10, check_same_thread=False)
def init_db():
    try:
        c = _db()
        c.execute('''CREATE TABLE IF NOT EXISTS history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original TEXT DEFAULT '', translated TEXT DEFAULT '',
            emotion TEXT DEFAULT '', source_lang TEXT DEFAULT '',
            target_lang TEXT DEFAULT '', engine TEXT DEFAULT '',
            timestamp TEXT DEFAULT '')''')
        ex = {r[1] for r in c.execute("PRAGMA table_info(history)")}
        for col, typ in [("engine","TEXT DEFAULT ''"),("emotion","TEXT DEFAULT ''"),
                         ("source_lang","TEXT DEFAULT ''"),("target_lang","TEXT DEFAULT ''")]:
            if col not in ex: c.execute(f"ALTER TABLE history ADD COLUMN {col} {typ}")
        c.commit(); c.close()
    except: pass

def _mpush(e):
    if "_mem" not in st.session_state: st.session_state["_mem"] = []
    st.session_state["_mem"].insert(0, e)
    st.session_state["_mem"] = st.session_state["_mem"][:150]

def save_tr(orig, trans, emo, src, tgt, eng=""):
    e = {"original":str(orig or "")[:400], "translated":str(trans or "")[:400],
         "emotion":str(emo or ""), "source_lang":str(src or ""),
         "target_lang":str(tgt or ""), "engine":str(eng or ""),
         "time":datetime.now().strftime("%Y-%m-%d %H:%M")}
    _mpush(e)
    try:
        c = _db()
        c.execute('''INSERT INTO history
            (original,translated,emotion,source_lang,target_lang,engine,timestamp)
            VALUES(?,?,?,?,?,?,?)''',
            tuple(e[k] for k in ["original","translated","emotion",
                                  "source_lang","target_lang","engine","time"]))
        c.commit(); c.close()
    except: pass

def get_hist(n=60):
    try:
        c = _db()
        rows = c.execute('''SELECT original,translated,emotion,source_lang,
                            target_lang,engine,timestamp
                            FROM history ORDER BY id DESC LIMIT ?''', (n,)).fetchall()
        c.close()
        if rows:
            return [{"original":r[0],"translated":r[1],"emotion":r[2] or "",
                     "source_lang":r[3] or "","target_lang":r[4] or "",
                     "engine":r[5] or "","time":r[6] or ""} for r in rows]
    except: pass
    return st.session_state.get("_mem", [])[:n]

def clr_hist():
    st.session_state["_mem"] = []
    try: c = _db(); c.execute("DELETE FROM history"); c.commit(); c.close()
    except: pass

init_db()

# ═══════════════════════════════════════════════════════════
#  SECRETS  (مخفية تماماً، تُقرأ من secrets.toml فقط)
# ═══════════════════════════════════════════════════════════
def _sec(k, d=""):
    try: return st.secrets.get(k, d) or d
    except: return d

_GROQ_KEY   = _sec("GROQ_API_KEY")
_DEEPL_KEY  = _sec("DEEPL_API_KEY")
_COHERE_KEY = _sec("COHERE_API_KEY")

for k, v in {"theme":"dark", "src_lang":"Auto-Detect",
             "tgt_lang":"Arabic", "input_text":""}.items():
    if k not in st.session_state: st.session_state[k] = v

# ═══════════════════════════════════════════════════════════
#  GROQ LLM
# ═══════════════════════════════════════════════════════════
def groq_llm(prompt: str, system: str = "",
             max_tokens: int = 700,
             fast: bool = False,
             cache: bool = True) -> str | None:
    if not _GROQ_KEY: return None
    model = "llama-3.1-8b-instant" if fast else "llama-3.3-70b-versatile"
    msgs  = []
    if system: msgs.append({"role":"system","content":system})
    msgs.append({"role":"user","content":prompt})
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {_GROQ_KEY}",
                     "Content-Type":"application/json"},
            json={"model":model,"messages":msgs,
                  "max_tokens":max_tokens,"temperature":0.4},
            timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return None

# cached version for repeated calls
@st.cache_data(show_spinner=False, ttl=3600)
def groq_cached(prompt: str, system: str = "",
                max_tokens: int = 700, fast: bool = False) -> str | None:
    return groq_llm(prompt, system, max_tokens, fast)

# ═══════════════════════════════════════════════════════════
#  SMART CONTEXTUAL TRANSLATION
#  يفهم السياق · يترجم الأمثال · يتعامل مع العامية
# ═══════════════════════════════════════════════════════════
_SMART_SYS = """You are an expert multilingual translator with deep cultural knowledge.
Your translation principles:
1. NEVER translate word-for-word — always translate MEANING and INTENT
2. Proverbs & idioms: find the EQUIVALENT expression in the target language, not literal words
   Example: "It's raining cats and dogs" → in Arabic: "الأمطار تهطل بغزارة" or "السماء تمطر مدراراً"
   NOT: "الأمطار قطط وكلاب"
3. Colloquial/dialect text: understand it fully, then translate naturally
   Arabic dialects (Egyptian مصري, Gulf خليجي, Moroccan مغربي, Levantine شامي etc.) → understand before translating
4. Keep the SAME register: formal stays formal, casual stays casual, poetic stays poetic
5. For technical/domain-specific text: use correct domain terminology
6. Return ONLY the translation — no explanations, no quotes, no preamble"""

@st.cache_data(show_spinner=False, ttl=3600)
def smart_translate(text: str, tgt: str, src: str = "Auto-Detect") -> tuple:
    """
    Groq contextual → DeepL → Google
    يدعم الأمثال والعامية والسياق
    """
    if not text or not text.strip(): return None, "no text"

    # Groq for contextual quality (especially short-medium texts with idioms/dialect)
    if _GROQ_KEY and len(text) <= 1500:
        result = groq_cached(
            f"Translate from {src} to {tgt}:\n\n{text}",
            system=_SMART_SYS,
            max_tokens=800,
            fast=len(text) < 300)
        if result: return result, "AI Contextual ✦"

    # DeepL fallback
    if _DEEPL_KEY:
        info = LANGS.get(tgt, {})
        if info.get("d"):
            ep = ("https://api-free.deepl.com/v2/translate" if _DEEPL_KEY.endswith(":fx")
                  else "https://api.deepl.com/v2/translate")
            try:
                r = requests.post(ep,
                    headers={"Authorization":f"DeepL-Auth-Key {_DEEPL_KEY}"},
                    data={"text":text,"target_lang":info["d"]}, timeout=15)
                if r.status_code == 200:
                    return r.json()["translations"][0]["text"], "DeepL ✦"
            except: pass

    # Google fallback
    src_g = LANGS.get(src, {}).get("g","auto")
    tgt_g = LANGS.get(tgt, {}).get("g","en")
    try:
        result = GoogleTranslator(source=src_g or "auto", target=tgt_g).translate(text)
        if result: return result, "Google"
    except:
        try:
            s = "en" if (not src_g or src_g == "auto") else src_g
            result = MyMemoryTranslator(source=s, target=tgt_g).translate(text)
            if result: return result, "Google"
        except: pass

    return None, "فشلت الترجمة"

# ═══════════════════════════════════════════════════════════
#  AI CHAT ASSISTANT
#  المساعد الذكي — يؤدي كل المهام عبر المحادثة
# ═══════════════════════════════════════════════════════════
_ASSISTANT_SYS = """\
أنت مساعد ترجمة ذكي محترف مدمج في تطبيق HN Translator.
لديك القدرة على:
- تصحيح الإملاء والنحو والإعراب بدقة عالية
- ترجمة الأمثال والتعابير الاصطلاحية بإيجاد مقابلها الحقيقي لا ترجمتها حرفياً
- التعامل مع اللهجات العربية (مصري، خليجي، شامي، مغربي، عراقي...) وغيرها من لهجات العالم وفهمها وترجمتها
- تحويل العامية إلى فصحى سليمة
- تلخيص النصوص الطويلة
- شرح المصطلحات الغامضة في سياقها
- الترجمة بأساليب مختلفة: رسمي، غير رسمي، أدبي، تقني
- تحسين جودة أي ترجمة موجودة

قواعد مهمة:
- لا تترجم حرفياً — دائماً ترجم المعنى والسياق
- الأمثال: أوجد المقابل الثقافي لا الترجمة الحرفية
- اللهجات: افهم أولاً ثم اترجم بطلاقة
- ردودك مختصرة ومباشرة واحترافية
- إذا طلب المستخدم ترجمة، أعطِ الترجمة مباشرة دون مقدمات"""

def ai_chat(user_msg: str, source_text: str, current_trans: str,
            src_lang: str, tgt_lang: str, history: list) -> str | None:
    """محادثة مع المساعد الذكي مع كامل السياق"""
    context = f"""السياق الحالي:
- النص الأصلي ({src_lang}): {source_text[:600] if source_text else 'لا يوجد'}
- الترجمة الحالية ({tgt_lang}): {current_trans[:400] if current_trans else 'لا يوجد'}
- لغة المصدر: {src_lang}
- لغة الهدف: {tgt_lang}

---
رسالة المستخدم: {user_msg}"""

    msgs = [{"role":"system","content":_ASSISTANT_SYS}]
    # add recent history (last 6 messages for context)
    for h in history[-6:]:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role":"user","content":context})

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {_GROQ_KEY}",
                     "Content-Type":"application/json"},
            json={"model":"llama-3.3-70b-versatile",
                  "messages":msgs,
                  "max_tokens":900,
                  "temperature":0.35},
            timeout=35)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return None

# ═══════════════════════════════════════════════════════════
#  TTS
# ═══════════════════════════════════════════════════════════
def make_tts(text: str, lang: str = "en") -> io.BytesIO | None:
    if not text or not text.strip(): return None
    try:
        buf = io.BytesIO()
        gTTS(text=text[:500], lang=lang, slow=False).write_to_fp(buf)
        buf.seek(0); return buf
    except: return None

# ═══════════════════════════════════════════════════════════
#  EMOTION  (lightweight keywords)
# ═══════════════════════════════════════════════════════════
_POS = {"شكر","ممتاز","رائع","سعيد","فرح","أحب","جميل","موافق","تمام","حلو",
        "happy","good","great","excellent","love","wonderful","amazing","joy","perfect"}
_NEG = {"حزين","سيء","كره","غضب","ألم","خطأ","فشل","مزعج","خطير","قلق",
        "sad","bad","hate","angry","pain","fail","dangerous","terrible","horrible"}

def emotion(text: str) -> str:
    tl = text.lower()
    p  = sum(1 for w in _POS if w in tl)
    n  = sum(1 for w in _NEG if w in tl)
    return "😊 إيجابي" if p > n else ("😔 سلبي" if n > p else "😐 محايد")

# ═══════════════════════════════════════════════════════════
#  LANGUAGE DETECTION
# ═══════════════════════════════════════════════════════════
def detect_lang(text: str) -> tuple:
    if not text: return "en", "English"
    ar = sum(1 for c in text if "\u0600"<=c<="\u06FF") / max(len(text),1)
    cy = sum(1 for c in text if "\u0400"<=c<="\u04FF") / max(len(text),1)
    cj = sum(1 for c in text if "\u4E00"<=c<="\u9FFF") / max(len(text),1)
    if ar > 0.12: return "ar", "Arabic"
    if cy > 0.12: return "ru", "Russian"
    if cj > 0.12: return "zh", "Chinese"
    if LD_OK and len(text.strip()) >= 5:
        try: code = _ld(text); return code, LC2N.get(code, code.capitalize())
        except: pass
    return "en", "English"

# ═══════════════════════════════════════════════════════════
#  FILE EXTRACTION
# ═══════════════════════════════════════════════════════════
def extract_file(fb: bytes, fn: str) -> tuple:
    ext = os.path.splitext(fn)[1].lower()
    if ext == ".pdf":
        if not PDF_OK: return None, "pdfplumber not installed"
        try:
            txt = ""
            with pdfplumber.open(io.BytesIO(fb)) as pdf:
                for pg in pdf.pages:
                    t = pg.extract_text()
                    if t: txt += t + "\n"
            return (txt.strip(), None) if txt.strip() else (None, "No text in PDF")
        except Exception as e: return None, str(e)
    if ext == ".docx":
        if not DOCX_OK: return None, "python-docx not installed"
        try:
            d   = docx.Document(io.BytesIO(fb))
            txt = "\n".join(p.text for p in d.paragraphs)
            return (txt.strip(), None) if txt.strip() else (None, "No text in DOCX")
        except Exception as e: return None, str(e)
    if ext in (".xlsx",".xls"):
        if not EXCEL_OK: return None, "openpyxl not installed"
        try:
            wb    = openpyxl.load_workbook(io.BytesIO(fb), data_only=True)
            parts = [str(c.value) for sh in wb.worksheets
                     for row in sh.iter_rows() for c in row if c.value is not None]
            txt   = "\n".join(parts)
            return (txt.strip(), None) if txt.strip() else (None, "No text in Excel")
        except Exception as e: return None, str(e)
    if ext == ".txt":
        for enc in ("utf-8","windows-1256","latin-1"):
            try:
                t = fb.decode(enc)
                if t.strip(): return t.strip(), None
            except: pass
    return None, f"Unsupported: {ext}"

# ═══════════════════════════════════════════════════════════
#  OCR  (Groq Vision)
# ═══════════════════════════════════════════════════════════
def _mime(b: bytes) -> str:
    try:
        fmt = Image.open(io.BytesIO(b)).format or "JPEG"
        return f"image/{'jpeg' if fmt.upper() in ('JPG','JPEG') else fmt.lower()}"
    except: return "image/jpeg"

def ocr_image(img: bytes) -> tuple:
    if not _GROQ_KEY: return None, "أضف GROQ_API_KEY في secrets.toml"
    try:
        mime = _mime(img); b64 = base64.b64encode(img).decode()
        for model in ["meta-llama/llama-4-scout-17b-16e-instruct",
                      "llama-3.2-11b-vision-preview"]:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {_GROQ_KEY}",
                         "Content-Type":"application/json"},
                json={"model":model,"temperature":0,"max_tokens":2048,
                      "messages":[{"role":"user","content":[
                          {"type":"image_url",
                           "image_url":{"url":f"data:{mime};base64,{b64}"}},
                          {"type":"text","text":
                           "Extract ALL text from this image exactly as written. "
                           "Preserve original language. Return ONLY the raw text."}]}]},
                timeout=30)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                return (txt, None) if txt else (None, "No text found")
            if r.status_code == 404: continue
        return None, "Groq Vision unavailable"
    except Exception as e: return None, str(e)

# ═══════════════════════════════════════════════════════════
#  STT  (Groq → Cohere → Whisper)
# ═══════════════════════════════════════════════════════════
def _wl(c: str):
    if not c or c == "auto": return None
    return {"zh-CN":"zh","zh-cn":"zh","iw":"he"}.get(c, c[:2])

def groq_stt(audio: bytes, lang="auto", verbose=False) -> tuple:
    if not _GROQ_KEY: return None, "No Groq key"
    lc = _wl(lang)
    files = {
        "file":            ("audio.wav", audio, "audio/wav"),
        "model":           (None, "whisper-large-v3-turbo"),
        "response_format": (None, "verbose_json" if verbose else "json"),
    }
    if verbose: files["timestamp_granularities[]"] = (None, "segment")
    if lc:     files["language"] = (None, lc)
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization":f"Bearer {_GROQ_KEY}"},
            files=files, timeout=60)
        if r.status_code == 200:
            data = r.json()
            if verbose: return data, None
            txt = data.get("text","").strip()
            return (txt, None) if txt else (None, "No speech")
        return None, f"Groq STT {r.status_code}"
    except Exception as e: return None, str(e)

def cohere_stt(audio: bytes, lang="en") -> tuple:
    if not _COHERE_KEY: return None, "No Cohere key"
    lc = _wl(lang) or "en"
    try:
        fields = OrderedDict([("language",lc),
                              ("model","cohere-transcribe-03-2026"),
                              ("file",("audio.wav",audio,"audio/wav"))])
        enc = MultipartEncoder(fields=fields)
        r = requests.post("https://api.cohere.com/v2/audio/transcriptions",
            headers={"Authorization":f"Bearer {_COHERE_KEY}",
                     "Content-Type":enc.content_type},
            data=enc, timeout=30)
        if r.status_code == 200:
            txt = r.json().get("text","").strip()
            return (txt, None) if txt else (None, "No speech")
        return None, f"Cohere {r.status_code}"
    except Exception as e: return None, str(e)

@st.cache_resource(show_spinner=False)
def _load_wh():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel("small", device="cpu", compute_type="int8")
    except: return None

def local_stt(audio: bytes, lang=None) -> tuple:
    m = _load_wh()
    if not m: return None, "Whisper unavailable"
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio); tmp = f.name
        segs, _ = m.transcribe(tmp, language=lang, beam_size=5, vad_filter=True)
        txt = " ".join(s.text for s in segs).strip()
        return (txt, None) if txt else (None, "No speech")
    except Exception as e: return None, str(e)
    finally:
        if tmp and os.path.exists(tmp): os.unlink(tmp)

def stt(audio: bytes, lang_code: str = "auto") -> tuple:
    wl = _wl(lang_code)
    if _GROQ_KEY:
        r, _ = groq_stt(audio, lang_code)
        if r: return r, None
    if _COHERE_KEY:
        r, _ = cohere_stt(audio, lang_code)
        if r: return r, None
    return local_stt(audio, lang=wl)

# ═══════════════════════════════════════════════════════════
#  GROUP CHAT
# ═══════════════════════════════════════════════════════════
_ICONS = ["🧑","👤","👩","👱","🧔","🧕","👲","🧑‍💼","👩‍💼","🙍"]

def _grp_segs(segs, gap=0.6):
    if not segs: return []
    groups, cur = [], [segs[0]]
    for i in range(1, len(segs)):
        if segs[i].get("start",0) - segs[i-1].get("end",0) >= gap:
            groups.append(cur); cur = []
        cur.append(segs[i])
    if cur: groups.append(cur)
    return groups

def group_analyze(audio: bytes, tgt: str) -> tuple:
    tgt_tts = LANGS.get(tgt, {}).get("tts","en")
    def _mk(txt, lc, ln, t0=0, t1=0):
        sn = LC2N.get(lc,"Auto-Detect")
        tr, eng = smart_translate(txt, tgt, sn)
        return [{"spk":1,"icon":_ICONS[0],"lc":lc,"lang":ln,
                 "orig":txt,"trans":tr or "","eng":eng,"t0":t0,"t1":t1}]
    data, _ = groq_stt(audio, lang="auto", verbose=True)
    if data is None:
        txt = None
        if _COHERE_KEY: txt, _ = cohere_stt(audio)
        if not txt: txt, err = local_stt(audio)
        if not txt: return None, "تعذر التعرف على الكلام"
        lc, ln = detect_lang(txt)
        return _mk(txt, lc, ln), None
    segs = data.get("segments",[]); full = data.get("text","").strip()
    if not segs:
        if not full: return None, "لم يُكتشف كلام"
        lc, ln = detect_lang(full)
        return _mk(full, lc, ln), None
    groups = _grp_segs(segs); results = []; l2s = {}; spk_n = 1
    for grp in groups:
        txt = " ".join(s.get("text","").strip() for s in grp).strip()
        if not txt: continue
        lc, ln = detect_lang(txt)
        if lc not in l2s: l2s[lc] = spk_n; spk_n += 1
        spk  = l2s[lc]; icon = _ICONS[min(spk-1, len(_ICONS)-1)]
        sn   = LC2N.get(lc,"Auto-Detect")
        tr, eng = smart_translate(txt, tgt, sn)
        results.append({"spk":spk,"icon":icon,"lc":lc,"lang":ln,
                        "orig":txt,"trans":tr or "","eng":eng,
                        "t0":grp[0].get("start",0),"t1":grp[-1].get("end",0)})
    return (results, None) if results else (None, "لم يُكتشف كلام")

# ═══════════════════════════════════════════════════════════
#  SUBTITLES
# ═══════════════════════════════════════════════════════════
def secs_to_srt(s: float) -> str:
    h=int(s//3600); m=int((s%3600)//60); sc=int(s%60); ms=int((s%1)*1000)
    return f"{h:02d}:{m:02d}:{sc:02d},{ms:03d}"

def blocks_to_srt(blocks: list) -> str:
    return "\n\n".join(
        f"{b['num']}\n{b['start']} --> {b['end']}\n{b['text']}" for b in blocks)

def video_to_srt(audio_bytes: bytes, tgt: str) -> tuple:
    data, err = groq_stt(audio_bytes, lang="auto", verbose=True)
    if data is None: return None, err
    segs = data.get("segments", [])
    if not segs: return None, "No segments found"
    orig_blocks, trans_blocks = [], []
    for i, s in enumerate(segs, 1):
        b = {"num":str(i),
             "start":secs_to_srt(s.get("start",0)),
             "end":  secs_to_srt(s.get("end",0)),
             "text": s.get("text","").strip()}
        orig_blocks.append(b)
        tr, _ = smart_translate(b["text"], tgt)
        trans_blocks.append({**b, "text": tr or b["text"]})
    return {"original":blocks_to_srt(orig_blocks),
            "translated":blocks_to_srt(trans_blocks),
            "blocks":trans_blocks,
            "count":len(orig_blocks)}, None

# ═══════════════════════════════════════════════════════════
#  DOMAIN (quick)
# ═══════════════════════════════════════════════════════════
_DOM = {
    "medical":   {"e":"🏥","na":"طبي",    "kw":["doctor","hospital","طبيب","مستشفى","علاج"]},
    "legal":     {"e":"⚖️","na":"قانوني", "kw":["contract","court","law","عقد","قانون"]},
    "political": {"e":"🏛️","na":"سياسي", "kw":["minister","government","رئيس","وزير","برلمان"]},
    "economic":  {"e":"📈","na":"اقتصادي","kw":["economic","investment","اقتصاد","استثمار"]},
    "scientific":{"e":"🔬","na":"علمي",   "kw":["research","experiment","بحث","تجربة"]},
    "military":  {"e":"🎖️","na":"عسكري", "kw":["military","army","جيش","عسكري","سلاح"]},
    "sports":    {"e":"⚽","na":"رياضي",  "kw":["football","stadium","كرة","ملعب","فريق"]},
    "it":        {"e":"💻","na":"تقني",   "kw":["programming","software","برمجة","تطبيق"]},
    "religious": {"e":"🕌","na":"ديني",   "kw":["mosque","prayer","مسجد","صلاة","قرآن"]},
    "literary":  {"e":"📖","na":"أدبي",   "kw":["story","poem","قصة","شعر","رواية"]},
}
def quick_domain(text: str) -> list:
    tl = text.lower()
    return [d for d,s in sorted(
        [(d, sum(tl.count(k) for k in v["kw"])) for d,v in _DOM.items()],
        key=lambda x:-x[1]) if s > 0][:2]

# ═══════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════
def _css(t):
    dk = t != "light"
    if dk:
        ac,bg,card,brd,txt,sub,sbg = (
            "#4ECBA0",
            "linear-gradient(135deg,#07071a 0%,#0c1525 55%,#070f1a 100%)",
            "rgba(78,203,160,.08)","rgba(78,203,160,.2)","#F0F4FF",
            "rgba(78,203,160,.78)","rgba(7,7,26,.98)")
        ib,it,ph = "#0f1827","#F0F4FF","#3a7a60"
        chat_u,chat_a = "rgba(78,203,160,.12)","rgba(255,255,255,.04)"
        hint_c = "rgba(78,203,160,.35)"
    else:
        ac,bg,card,brd,txt,sub,sbg = (
            "#1a9e70","#EFF3F8",
            "rgba(26,158,112,.07)","rgba(26,158,112,.22)","#111827",
            "rgba(26,158,112,.82)","rgba(255,255,255,.99)")
        ib,it,ph = "#FFFFFF","#111827","rgba(26,158,112,.4)"
        chat_u,chat_a = "rgba(26,158,112,.1)","rgba(0,0,0,.04)"
        hint_c = "rgba(26,158,112,.3)"
    tl = "#111827" if not dk else "#8fa8c8"
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Tajawal:wght@400;500;700&display=swap');
.stApp{{background:{bg} !important;font-family:'Space Grotesk','Tajawal',system-ui,sans-serif !important}}
/* Header */
.hdr{{text-align:center;padding:.6rem 0 .3rem}}
.hdr .br-row{{display:flex;align-items:center;justify-content:center;gap:.45rem;margin-bottom:.2rem}}
.hdr .brand{{font-size:9px;font-weight:700;letter-spacing:.35em;color:{ac};text-transform:uppercase;opacity:.7}}
.hdr .dot{{color:{ac};font-size:7px;opacity:.4}}
.hdr h1{{font-family:'Space Grotesk',sans-serif;font-size:30px;font-weight:700;
  color:{txt};margin:.1rem 0;letter-spacing:-.02em;text-shadow:0 0 40px {ac}38}}
.hdr h1 .ac{{color:{ac}}}
.hdr .tags{{display:flex;justify-content:center;gap:.3rem;margin:.2rem 0 0;flex-wrap:wrap}}
.hdr .tag{{font-size:9.5px;font-weight:600;background:{card};border:1px solid {brd};
  border-radius:20px;padding:2px 8px;color:{sub};letter-spacing:.02em}}
.hdr .dv{{width:80px;height:2px;
  background:linear-gradient(90deg,transparent,{ac},transparent);margin:.3rem auto 0}}
/* Buttons */
.stButton>button{{background:linear-gradient(135deg,{ac},#1a9d6a) !important;
  color:#041510 !important;font-weight:700 !important;font-size:13px !important;
  border:none !important;border-radius:10px !important;
  box-shadow:0 3px 10px {ac}35 !important;transition:all .18s !important}}
.stButton>button:hover{{filter:brightness(1.1) !important;transform:translateY(-2px) !important}}
/* Textarea */
textarea,.stTextArea textarea{{
  background:{ib} !important;color:{it} !important;
  font-size:17px !important;font-family:'Tajawal','Space Grotesk',Arial,sans-serif !important;
  font-weight:600 !important;line-height:1.85 !important;
  border:2px solid {brd} !important;border-radius:12px !important;
  padding:14px 16px !important;caret-color:{ac} !important;
  -webkit-font-smoothing:antialiased !important}}
textarea:focus{{border-color:{ac} !important;
  box-shadow:0 0 0 3px {ac}22 !important;outline:none !important}}
textarea::placeholder{{color:{ph} !important;opacity:.65 !important;
  font-weight:400 !important;font-size:15px !important}}
.stTextArea label{{color:{sub} !important;font-size:10px !important;
  font-weight:700 !important;text-transform:uppercase !important;letter-spacing:.1em !important}}
/* Translation panel */
.t-panel{{background:rgba(255,255,255,.025) if {str(dk)} == 'True' else rgba(0,0,0,.02);
  border:1.5px solid {brd};border-radius:14px;
  padding:.9rem 1.1rem;min-height:180px;position:relative}}
.t-panel{{background:{"rgba(255,255,255,.025)" if dk else "rgba(0,0,0,.02)"};
  border:1.5px solid {brd};border-radius:14px;
  padding:.9rem 1.1rem;min-height:180px;position:relative}}
.t-panel::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,{ac},transparent)}}
.t-panel .p-txt{{font-size:17px;color:{txt};
  font-family:'Tajawal','Space Grotesk',sans-serif;
  font-weight:600;line-height:1.85;min-height:80px}}
.t-panel .p-empty{{font-size:14px;color:{sub};opacity:.28;padding:.5rem 0;font-style:italic}}
/* Cards */
.card{{background:{card};border:1px solid {brd};border-radius:12px;
  padding:.75rem 1rem;margin:.4rem 0;position:relative;overflow:hidden}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,{ac},transparent)}}
.card .lbl{{font-size:9px;font-weight:700;text-transform:uppercase;color:{sub};letter-spacing:.2em}}
.card .body{{font-size:16px;color:{txt};margin-top:.35rem;line-height:1.75;
  font-family:'Tajawal','Space Grotesk',sans-serif;font-weight:500}}
.card .meta{{font-size:10px;color:{sub};margin-top:5px;opacity:.7;display:flex;gap:.5rem;flex-wrap:wrap}}
/* Section heading */
.sh{{font-size:9px;font-weight:700;text-transform:uppercase;color:{sub};
  margin:.55rem 0 .25rem;letter-spacing:.12em;display:flex;align-items:center;gap:.4rem}}
.sh::before{{content:'';display:inline-block;width:3px;height:11px;
  background:{ac};border-radius:2px}}
/* Domain badges */
.dom-row{{display:flex;gap:.3rem;flex-wrap:wrap;margin:.3rem 0}}
.dom-badge{{font-size:11px;font-weight:600;padding:2px 9px;border-radius:20px;
  background:{card};border:1px solid {brd};color:{sub}}}
/* AI CHAT */
.chat-wrap{{border:1.5px solid {brd};border-radius:14px;overflow:hidden;margin-top:.5rem}}
.chat-header{{background:{card};padding:.5rem 1rem;display:flex;align-items:center;gap:.5rem;
  border-bottom:1px solid {brd}}}
.chat-header .ch-ic{{font-size:18px}}
.chat-header .ch-title{{font-size:11px;font-weight:700;color:{ac};text-transform:uppercase;letter-spacing:.1em}}
.chat-header .ch-sub{{font-size:10px;color:{sub};opacity:.7}}
.chat-body{{max-height:320px;overflow-y:auto;padding:.6rem .8rem;
  scrollbar-width:thin;scrollbar-color:{brd} transparent}}
.msg-u{{background:{chat_u};border:1px solid {brd};border-radius:12px 12px 3px 12px;
  padding:.55rem .9rem;margin:.4rem 0 .4rem auto;max-width:85%;
  font-size:14px;color:{txt};font-family:'Tajawal','Space Grotesk',sans-serif;
  font-weight:500;line-height:1.6;text-align:right}}
.msg-a{{background:{chat_a};border:1px solid {brd};border-radius:12px 12px 12px 3px;
  padding:.55rem .9rem;margin:.4rem auto .4rem 0;max-width:90%;
  font-size:14px;color:{txt};font-family:'Tajawal','Space Grotesk',sans-serif;
  line-height:1.65;border-left:3px solid {ac}}}
.msg-a .a-eng{{font-size:9px;color:{sub};opacity:.5;margin-top:3px}}
.chat-hints{{display:flex;gap:.35rem;flex-wrap:wrap;padding:.5rem .8rem;
  border-top:1px solid {brd};background:{card}}}
.hint-btn{{font-size:11px;color:{sub};background:transparent;border:1px solid {hint_c};
  border-radius:20px;padding:3px 10px;cursor:pointer;transition:all .15s;
  font-family:'Space Grotesk',sans-serif}}
.hint-btn:hover{{background:{card};border-color:{ac};color:{ac}}}
/* SRT lines */
.srt-line{{display:flex;gap:.7rem;padding:.35rem 0;
  border-bottom:1px solid {brd}22;font-size:13px;align-items:flex-start}}
.srt-num{{color:{sub};opacity:.4;min-width:20px;font-size:10px;padding-top:2px}}
.srt-time{{color:{sub};opacity:.6;font-size:10px;min-width:90px;padding-top:2px;font-family:monospace}}
.srt-trans{{color:{txt};flex:1;font-weight:600;
  font-family:'Tajawal','Space Grotesk',sans-serif}}
/* Chat bubbles (group) */
.cb{{border-radius:14px;padding:.85rem 1.1rem;margin-bottom:.65rem;
  border:1px solid {brd};background:{card};transition:all .15s}}
.cb:hover{{transform:translateX(3px)}}
.cb-hd{{display:flex;align-items:center;gap:9px;margin-bottom:.4rem}}
.cb-ic{{font-size:22px;line-height:1}}
.cb-nfo{{display:flex;flex-direction:column;gap:2px}}
.cb-spk{{font-size:13px;font-weight:700}}
.cb-lang{{font-size:10px;color:{sub};opacity:.8}}
.cb-ts{{font-size:9px;color:{sub};opacity:.45}}
.cb-orig{{font-size:13px;color:{sub};font-style:italic;border-left:3px solid {brd};
  padding-left:8px;margin-bottom:.3rem;opacity:.85;line-height:1.5}}
.cb-trans{{font-size:15px;color:{txt};font-weight:600;line-height:1.7;
  font-family:'Tajawal','Space Grotesk',sans-serif}}
.cb-eng{{font-size:9px;color:{sub};opacity:.42;margin-top:3px}}
/* Sidebar */
[data-testid="stSidebar"]{{background:{sbg} !important;
  border-right:1px solid {brd} !important}}
.hist{{padding:5px 7px;border-bottom:1px solid {brd}22;transition:background .12s}}
.hist:hover{{background:{card};border-radius:5px}}
.hist .o{{color:{txt};font-size:11.5px;line-height:1.4}}
.hist .tr{{color:{ac};font-size:11.5px;line-height:1.4}}
.hist .m{{font-size:9px;color:{sub};opacity:.5}}
/* Audio input */
div[data-testid="stAudioInput"]>div{{background:{card} !important;
  border:2px solid {brd} !important;border-radius:60px !important}}
div[data-testid="stAudioInput"]>div:hover{{border-color:{ac} !important}}
/* Tabs */
button[data-baseweb="tab"]{{font-family:'Space Grotesk',sans-serif !important;
  font-size:12px !important;font-weight:600 !important;color:{tl} !important;
  background:transparent !important;border:none !important;
  border-radius:7px 7px 0 0 !important;padding:.42rem .9rem !important;
  transition:all .15s}}
button[data-baseweb="tab"][aria-selected="true"]{{background:{card} !important;
  color:{ac} !important;border-bottom:2px solid {ac} !important}}
div[data-baseweb="tab-list"]{{gap:3px !important;border-bottom:1px solid {brd} !important}}
/* Selectbox */
.stSelectbox label,.stMultiSelect label{{color:{sub} !important;font-size:10px !important}}
.stSelectbox>div>div{{background:{ib} !important;color:{it} !important;
  border-color:{brd} !important;border-radius:8px !important;font-size:14px !important}}
/* Upload */
[data-testid="stFileUploadDropzone"]{{background:{card} !important;
  border:1.5px dashed {brd} !important;border-radius:10px !important}}
[data-testid="stFileUploadDropzone"]:hover{{border-color:{ac} !important}}
hr{{margin:.4rem 0;border:none;height:1px;
  background:linear-gradient(90deg,transparent,{brd},transparent)}}
/* Chat input override */
[data-testid="stChatInput"]{{background:{ib} !important;
  border:1.5px solid {brd} !important;border-radius:12px !important}}
[data-testid="stChatInput"] textarea{{
  background:{ib} !important;color:{it} !important;
  font-size:14px !important;border:none !important;font-weight:500 !important}}
@media(max-width:768px){{
  [data-testid="stHorizontalBlock"]{{flex-direction:column !important}}
  .hdr h1{{font-size:24px !important}}
}}
"""

st.markdown(f"<style>{_css(st.session_state.theme)}</style>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════
st.markdown("""<div class="hdr">
<div class="br-row">
  <span class="dot">◆</span>
  <span class="brand">Smart Voice Translator</span>
  <span class="dot">◆</span>
</div>
<h1>HN <span class="ac">TRANSLATOR</span></h1>
<div class="tags">
  <span class="tag">🎙️ Voice</span>
  <span class="tag">✍️ Text + AI Chat</span>
  <span class="tag">📸 Vision</span>
  <span class="tag">🎬 Subtitles</span>
  <span class="tag">🌍 Group</span>
</div>
<div class="dv"></div></div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    if st.button("🌓 تبديل المظهر", use_container_width=True):
        st.session_state.theme = (
            "light" if st.session_state.theme == "dark" else "dark")
        st.rerun()
    st.divider()
    hist = get_hist(60)
    if hist:
        ca, cb = st.columns(2)
        with ca:
            if st.button("🗑️ مسح", use_container_width=True):
                clr_hist(); st.rerun()
        with cb:
            b64h = base64.b64encode(
                json.dumps(hist, ensure_ascii=False, indent=2).encode()).decode()
            st.markdown(
                f'<a href="data:application/json;base64,{b64h}" download="history.json">📥 تصدير</a>',
                unsafe_allow_html=True)
        for it in hist:
            st.markdown(f"""<div class="hist">
<div class="o">{it.get('original','')[:48]}</div>
<div class="tr">{it.get('translated','')[:48]}</div>
<div class="m">{it.get('engine','')} · {it.get('target_lang','')} · {it.get('time','')}</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(
            "<div style='text-align:center;font-size:28px;opacity:.2;padding:1rem'>📭</div>",
            unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  LANGUAGE SELECTOR
# ═══════════════════════════════════════════════════════════
def _swap():
    s = st.session_state.get("src_lang","Auto-Detect")
    t = st.session_state.get("tgt_lang","Arabic")
    ns = t; nt = s if s != "Auto-Detect" else "Arabic"
    if nt == ns: nt = next((k for k in LN_NO_AUTO if k != ns),"English")
    st.session_state["src_lang"] = ns
    st.session_state["tgt_lang"] = nt

st.markdown('<div class="sh">Translation Direction</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([1, .18, 1])
with c1: src_name = st.selectbox("From", LN, key="src_lang")
with c2:
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.button("⇄", on_click=_swap, use_container_width=True, key="_sw")
with c3:
    tgt_opts = [k for k in LN_NO_AUTO if k != src_name]
    if st.session_state.get("tgt_lang") not in tgt_opts:
        st.session_state["tgt_lang"] = tgt_opts[0]
    tgt_name = st.selectbox("To", tgt_opts, key="tgt_lang")

src_g   = LANGS.get(src_name, {}).get("g","auto")
tgt_tts = LANGS.get(tgt_name, {}).get("tts","en")

# ═══════════════════════════════════════════════════════════
#  TABS
# ═══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["🎙️ Voice", "✍️ Text + AI", "📄 File", "📸 Camera", "🎬 Subtitles", "🌍 Group Chat"])

# ─────────────────────────── TAB 1: VOICE ───────────────────────
with tab1:
    st.markdown("---")
    av = st.audio_input("🎙️ اضغط وسجّل", key="_mic1", label_visibility="visible")
    if av:
        with st.spinner("⏳ التعرف على الكلام..."):
            recognized, _ = stt(av.getvalue(), src_g)
        if recognized:
            st.success(f"✅ {recognized}")
            with st.spinner("⏳ الترجمة الذكية..."):
                trans, eng = smart_translate(recognized, tgt_name, src_name)
            if trans:
                emo  = emotion(recognized)
                doms = quick_domain(recognized)
                d_str= " ".join(f'{_DOM[d]["e"]} {_DOM[d]["na"]}' for d in doms)
                st.markdown(f"""<div class="card">
<span class="lbl">✦ الترجمة</span>
<div class="body">{trans}</div>
<div class="meta">
  <span>{emo}</span><span>·</span><span>{eng}</span>
  {'<span>·</span><span>'+d_str+'</span>' if d_str else ''}
</div></div>""", unsafe_allow_html=True)
                st.code(trans, language=None)
                aud = make_tts(trans, tgt_tts)
                if aud: st.audio(aud, format="audio/mp3")
                save_tr(recognized, trans, emo, src_name, tgt_name, eng)
            else: st.error(f"❌ الترجمة فشلت")
        else: st.error("❌ تعذر التعرف على الكلام")

# ─────────────────────────── TAB 2: TEXT + AI CHAT ─────────────
with tab2:
    st.markdown("---")

    # Side-by-side
    col_s, col_t = st.columns(2, gap="medium")
    with col_s:
        st.markdown('<div class="sh">📝 النص الأصلي</div>', unsafe_allow_html=True)
        input_text = st.text_area("",
            height=200,
            placeholder="اكتب النص هنا … الترجمة تظهر فوراً\nيدعم العامية والأمثال واللهجات",
            value=st.session_state.input_text,
            key="_txt",
            label_visibility="collapsed")
        st.session_state.input_text = input_text

    # Auto smart translate
    auto_trans = ""; auto_eng = ""; doms = []
    if input_text and len(input_text.strip()) >= 3:
        ck = f"{input_text.strip()}||{tgt_name}||{src_name}"
        if ck != st.session_state.get("_tc_key"):
            res = smart_translate(input_text.strip(), tgt_name, src_name)
            st.session_state["_tc_key"] = ck
            st.session_state["_tc_val"] = res
        auto_trans, auto_eng = st.session_state.get("_tc_val", ("",""))
        doms = quick_domain(input_text)

    with col_t:
        eng_badge = (f'<span style="font-size:9px;opacity:.5">{auto_eng}</span>'
                     if auto_eng else "")
        st.markdown(f'<div class="sh">🌐 الترجمة {eng_badge}</div>',
                    unsafe_allow_html=True)
        if auto_trans:
            st.markdown(f'<div class="t-panel"><div class="p-txt">{auto_trans}</div></div>',
                        unsafe_allow_html=True)
            ca, cb, cc = st.columns(3)
            with ca:
                aud = make_tts(auto_trans, tgt_tts)
                if aud: st.audio(aud, format="audio/mp3")
            with cb: st.code(auto_trans, language=None)
            with cc:
                emo_v = emotion(input_text) if input_text.strip() else ""
                if emo_v:
                    st.markdown(
                        f"<div style='font-size:14px;padding-top:.4rem'>{emo_v}</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="t-panel"><div class="p-empty">الترجمة تظهر هنا تلقائياً …</div></div>',
                unsafe_allow_html=True)

    # Domain badges
    if doms:
        badges = "".join(
            f'<span class="dom-badge">{_DOM[d]["e"]} {_DOM[d]["na"]}</span>'
            for d in doms)
        st.markdown(f'<div class="dom-row">{badges}</div>', unsafe_allow_html=True)

    if auto_trans and input_text.strip():
        save_tr(input_text.strip(), auto_trans, emotion(input_text),
                src_name, tgt_name, auto_eng)

    # ───────────────────────────────────────────────────────────
    #  AI CHAT ASSISTANT  🤖
    # ───────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="sh">🤖 المساعد الذكي</div>', unsafe_allow_html=True)

    if not _GROQ_KEY:
        st.info("💡 أضف GROQ_API_KEY في secrets.toml لتفعيل المساعد الذكي")
    else:
        # initialize chat history
        if "_chat_hist" not in st.session_state:
            st.session_state["_chat_hist"] = []

        # hint buttons (rendered as HTML, trigger via session_state)
        _HINTS = [
            ("🔤 صحح الإملاء والإعراب","صحح الإملاء والأخطاء النحوية في النص الأصلي"),
            ("🎭 ترجم الأمثال","ابحث عن مقابل الأمثال والتعابير الاصطلاحية في اللغة الهدف"),
            ("📝 لخص النص","لخص النص في 2-3 جمل بلغة الهدف"),
            ("🔍 اشرح المصطلحات","اشرح المصطلحات الغامضة في سياقها"),
            ("🗣️ حوّل العامية لفصحى","حوّل النص العامي أو اللهجي إلى لغة فصحى سليمة"),
            ("✨ حسّن الترجمة","حسّن الترجمة الحالية واجعلها أكثر دقة وطبيعية"),
        ]

        # hint buttons
        hint_cols = st.columns(3)
        for idx, (label, prompt) in enumerate(_HINTS):
            with hint_cols[idx % 3]:
                if st.button(label, key=f"_hint_{idx}", use_container_width=True):
                    st.session_state["_pending_msg"] = prompt

        # display chat history
        if st.session_state["_chat_hist"]:
            chat_html = '<div class="chat-wrap"><div class="chat-body">'
            for msg in st.session_state["_chat_hist"][-12:]:
                if msg["role"] == "user":
                    chat_html += f'<div class="msg-u">{msg["content"]}</div>'
                else:
                    chat_html += f'<div class="msg-a">{msg["content"]}</div>'
            chat_html += "</div></div>"
            st.markdown(chat_html, unsafe_allow_html=True)
            if st.button("🗑️ مسح المحادثة", key="_clr_chat"):
                st.session_state["_chat_hist"] = []
                st.rerun()

        # chat input
        user_input = st.chat_input(
            "اكتب تعليماتك للمساعد … مثل: صحح الأخطاء · ترجم المثل · اجعله رسمياً",
            key="_chat_in")

        # handle pending hint
        if st.session_state.get("_pending_msg"):
            user_input = st.session_state.pop("_pending_msg")

        if user_input:
            # add user message
            st.session_state["_chat_hist"].append(
                {"role":"user","content":user_input})

            with st.spinner("المساعد يفكر..."):
                reply = ai_chat(
                    user_msg       = user_input,
                    source_text    = input_text or "",
                    current_trans  = auto_trans or "",
                    src_lang       = src_name,
                    tgt_lang       = tgt_name,
                    history        = st.session_state["_chat_hist"][:-1],
                )

            if reply:
                st.session_state["_chat_hist"].append(
                    {"role":"assistant","content":reply})
            else:
                st.session_state["_chat_hist"].append(
                    {"role":"assistant","content":"⚠️ لم أستطع الرد. تحقق من اتصال Groq."})
            st.rerun()

# ─────────────────────────── TAB 3: FILE ─────────────────────────
with tab3:
    st.markdown("---")
    uploaded = st.file_uploader("📄 اختر ملفاً (PDF · DOCX · XLSX · TXT)", key="_file")
    if uploaded:
        st.caption(f"📎 {uploaded.name} — {len(uploaded.getvalue())//1024} KB")
        if st.button("🔍 استخراج وترجمة", key="_file_btn"):
            with st.spinner("استخراج النص..."):
                extracted, err = extract_file(uploaded.getvalue(), uploaded.name)
            if extracted:
                st.markdown('<div class="sh">النص المستخرج</div>', unsafe_allow_html=True)
                st.code(extracted[:2500]+("…" if len(extracted)>2500 else ""), language=None)
                st.caption(f"الكلمات: {len(extracted.split())}")
                with st.spinner("الترجمة الذكية..."):
                    trans, eng = smart_translate(extracted, tgt_name, src_name)
                if trans:
                    emo = emotion(extracted[:400])
                    st.markdown(f"""<div class="card">
<span class="lbl">✦ الترجمة</span>
<div class="body">{trans}</div>
<div class="meta"><span>{eng}</span></div>
</div>""", unsafe_allow_html=True)
                    ca, cb = st.columns(2)
                    with ca: st.download_button("📥 النص الأصلي", data=extracted,
                                                file_name="original.txt", mime="text/plain")
                    with cb: st.download_button("📥 الترجمة", data=trans,
                                                file_name="translated.txt", mime="text/plain")
                    aud = make_tts(trans, tgt_tts)
                    if aud: st.audio(aud, format="audio/mp3")
                    save_tr(extracted[:300], trans, emo, "File", tgt_name, eng)
                else: st.error("❌ فشلت الترجمة")
            else: st.error(f"❌ {err}")

# ─────────────────────────── TAB 4: CAMERA ────────────────────────
with tab4:
    st.markdown("---")
    cam = st.file_uploader("📸 اختر صورة",
                           type=["png","jpg","jpeg","webp","bmp"], key="_cam")
    if cam:
        img_b = cam.getvalue()
        try:
            st.image(Image.open(io.BytesIO(img_b)).convert("RGB"),
                     caption=cam.name, use_container_width=True)
        except: pass
        if st.button("🔍 استخراج النص وترجمته", key="_cam_btn"):
            with st.spinner("استخراج النص بالذكاء الاصطناعي..."):
                extracted, err = ocr_image(img_b)
            if not extracted:
                st.error(f"❌ {err}")
            else:
                lc, ln  = detect_lang(extracted)
                src_for = LC2N.get(lc, src_name)
                st.markdown('<div class="sh">النص المستخرج</div>', unsafe_allow_html=True)
                st.code(extracted, language=None)
                st.caption(f"اللغة: {ln} · الكلمات: {len(extracted.split())}")
                with st.spinner("الترجمة الذكية..."):
                    trans, eng = smart_translate(extracted, tgt_name, src_for)
                if trans:
                    emo = emotion(extracted[:400])
                    st.markdown(f"""<div class="card">
<span class="lbl">✦ الترجمة ({src_for} → {tgt_name})</span>
<div class="body">{trans}</div>
<div class="meta"><span>{emo}</span><span>·</span><span>{eng}</span></div>
</div>""", unsafe_allow_html=True)
                    st.code(trans, language=None)
                    ca, cb = st.columns(2)
                    with ca: st.download_button("📥 النص", data=extracted,
                                                file_name="ocr.txt", mime="text/plain")
                    with cb: st.download_button("📥 الترجمة", data=trans,
                                                file_name="ocr_tr.txt", mime="text/plain")
                    aud = make_tts(trans, tgt_tts)
                    if aud: st.audio(aud, format="audio/mp3")
                    save_tr(extracted, trans, emo, f"Camera/{ln}", tgt_name, eng)
                else: st.error("❌ فشلت الترجمة")

# ─────────────────────────── TAB 5: SUBTITLES ─────────────────────
with tab5:
    st.markdown("---")
    st.markdown('<div class="sh">🎯 اللغة الهدف</div>', unsafe_allow_html=True)
    sub_tgt = st.selectbox("",
        LN_NO_AUTO,
        index=LN_NO_AUTO.index(tgt_name) if tgt_name in LN_NO_AUTO else 0,
        key="_sub_tgt", label_visibility="collapsed")
    av_file = st.file_uploader(
        "🎵 ارفع ملف صوتي أو مقطع فيديو",
        type=["mp3","wav","m4a","ogg","mp4","webm","mov"], key="_av_up")
    if av_file:
        st.caption(f"📎 {av_file.name} — {len(av_file.getvalue())//1024} KB")
        if not _GROQ_KEY:
            st.warning("⚠️ يتطلب GROQ_API_KEY في secrets.toml")
        elif st.button("🎙️ تفريغ وترجمة", use_container_width=True, key="_av_btn"):
            bar = st.progress(0, text="⏳ جاري التفريغ والترجمة...")
            result, err = video_to_srt(av_file.getvalue(), sub_tgt)
            bar.progress(100); bar.empty()
            if not result: st.error(f"❌ {err}")
            else:
                st.session_state["_av_result"] = result
                st.success(f"✅ تم تفريغ {result['count']} مقطع")
    av_res = st.session_state.get("_av_result")
    if av_res:
        st.markdown('<div class="sh">معاينة</div>', unsafe_allow_html=True)
        for b in av_res["blocks"][:10]:
            st.markdown(f"""<div class="srt-line">
<span class="srt-num">{b['num']}</span>
<span class="srt-time">{b['start'][:8]}</span>
<span class="srt-trans">{b['text']}</span>
</div>""", unsafe_allow_html=True)
        if av_res["count"] > 10:
            st.caption(f"… و{av_res['count']-10} مقطعاً آخر")
        ca, cb, cc = st.columns(3)
        with ca:
            st.download_button("📥 SRT أصلي", data=av_res["original"],
                               file_name="original.srt", mime="text/plain", key="_av_o")
        with cb:
            st.download_button("📥 SRT مترجم", data=av_res["translated"],
                               file_name=f"translated.srt", mime="text/plain", key="_av_t")
        with cc:
            bilingual = "\n\n".join(
                f"{b['num']}\n{b['start']} --> {b['end']}\n{b['text']}"
                for b in av_res["blocks"])
            st.download_button("📥 SRT ثنائي", data=bilingual,
                               file_name="bilingual.srt", mime="text/plain", key="_av_b")

# ─────────────────────────── TAB 6: GROUP CHAT ────────────────────
with tab6:
    st.markdown("---")
    st.markdown('<div class="sh">🎯 اللغة الهدف</div>', unsafe_allow_html=True)
    grp_tgt = st.selectbox("",
        LN_NO_AUTO,
        index=LN_NO_AUTO.index(tgt_name) if tgt_name in LN_NO_AUTO else 0,
        key="_g_tgt", label_visibility="collapsed")
    grp_tts_l = LANGS.get(grp_tgt, {}).get("tts","en")
    st.markdown("---")
    grp_audio = st.audio_input("🎙️ سجّل المحادثة الجماعية",
                                key="_g_mic", label_visibility="visible")
    if grp_audio:
        if st.button("🚀 تحليل وترجمة", use_container_width=True, key="_g_btn"):
            bar = st.progress(0, text="⏳ تمييز المتحدثين وترجمة...")
            results, err = group_analyze(grp_audio.getvalue(), grp_tgt)
            bar.progress(100); bar.empty()
            if not results:
                st.error(f"❌ {err or 'تعذر'}")
            else:
                spks = sorted({r["spk"] for r in results})
                st.markdown(
                    f"<div style='text-align:center;font-size:12px;opacity:.6;"
                    f"margin-bottom:.5rem'>"
                    f"{len(results)} مقطع · {len(spks)} متحدث{'ون' if len(spks)>1 else ''}</div>",
                    unsafe_allow_html=True)
                log = []
                for item in results:
                    hue = (item["spk"] * 83 + 140) % 360
                    sc  = f"hsl({hue},65%,62%)"; bc = f"hsl({hue},65%,40%)"
                    ts  = f"{item['t0']:.1f}s – {item['t1']:.1f}s" if item["t1"]>0 else ""
                    st.markdown(f"""<div class="cb" style="border-left:3px solid {bc}">
<div class="cb-hd">
  <span class="cb-ic">{item['icon']}</span>
  <div class="cb-nfo">
    <span class="cb-spk" style="color:{sc}">المتحدث {item['spk']}</span>
    <span class="cb-lang">🌐 {item['lang']}</span>
    {'<span class="cb-ts">⏱ '+ts+'</span>' if ts else ''}
  </div>
</div>
<div class="cb-orig">"{item['orig']}"</div>
<div class="cb-trans">{item['trans'] or '—'}</div>
<div class="cb-eng">{item['eng']}</div>
</div>""", unsafe_allow_html=True)
                    aud = make_tts(item["trans"], grp_tts_l)
                    if aud: st.audio(aud, format="audio/mp3")
                    emo = emotion(item["orig"])
                    save_tr(item["orig"], item["trans"], emo,
                            f"Group/{item['lang']}", grp_tgt, item["eng"])
                    log.append(
                        f"المتحدث {item['spk']} ({item['lang']}) [{ts}]\n"
                        f"  الأصلي  : {item['orig']}\n"
                        f"  الترجمة : {item['trans']}\n")
                st.markdown("---")
                st.download_button("📥 تحميل المحضر", data="\n".join(log),
                                   file_name="transcript.txt", mime="text/plain",
                                   use_container_width=True, key="_g_dl")
