import streamlit as st

st.title("اختبار قراءة المفاتيح من secrets")

# محاولة قراءة المفتاح
try:
    cohere_key = st.secrets["COHERE_API_KEY"]
    st.success(f"✅ تم قراءة مفتاح Cohere: {cohere_key[:6]}...{cohere_key[-4:]}")
except KeyError:
    st.error("❌ لم يتم العثور على COHERE_API_KEY في secrets")
    
try:
    deepl_key = st.secrets["DEEPL_API_KEY"]
    st.success(f"✅ تم قراءة مفتاح DeepL: {deepl_key[:6]}...{deepl_key[-4:]}")
except KeyError:
    st.error("❌ لم يتم العثور على DEEPL_API_KEY في secrets")

# عرض جميع المفاتيح الموجودة (للتأكد من وجود الملف)
st.write("جميع المفاتيح الموجودة:", list(st.secrets.keys()))
