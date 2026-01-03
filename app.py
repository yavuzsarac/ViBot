import streamlit as st
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import yt_dlp
import glob
import re
import time
import random

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="ViBot",
    page_icon="🤖",
    layout="centered"
    


)

# --- CSS: MODERN TASARIM & İMZA ---
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(to bottom right, #0f2027, #203a43, #2c5364); 
        color: white;
    }
    .header-text {
        font-size: 3.5rem; font-weight: 800;
        background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center;
        text-shadow: 0px 0px 30px rgba(0, 210, 255, 0.3);
    }
    .sub-text { text-align: center; color: #b0c4de; margin-bottom: 30px; }
    
    .stButton>button {
        width: 100%; background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
        color: white; border: none; padding: 15px; font-size: 18px; font-weight: bold;
        border-radius: 50px; transition: 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02); box-shadow: 0 10px 20px rgba(0, 210, 255, 0.4);
    }
    .result-card {
        background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);
        padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);
        margin-top: 20px;
    }
    
    /* İMZA KISMI (Sabit Footer) */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #0E1117; color: #808495;
        text-align: center; padding: 10px; font-size: 13px;
        border-top: 1px solid #1f2937; z-index: 999;
    }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.markdown('<p class="header-text">ViBot 🤖</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Yapay Zeka Destekli Video Analiz Asistanı</p>', unsafe_allow_html=True)

# --- API KONTROL ---
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ API Anahtarı Bulunamadı! (.env dosyasını kontrol et)")
    st.stop()

# --- TEMİZLİK ---
def clean_vtt(text):
    lines = text.split('\n')
    cleaned = []
    seen = set()
    for line in lines:
        if '-->' in line or line.strip() == 'WEBVTT' or not line.strip() or line.strip().isdigit():
            continue
        clean = re.sub(r'<[^>]+>', '', line).strip()
        clean = re.sub(r'align:.*', '', clean).strip()
        if clean and clean not in seen:
            cleaned.append(clean)
            seen.add(clean)
    return " ".join(cleaned)

# --- ZEKİ İNDİRME FONKSİYONU ---
def get_transcript_smart(url):
    try:
        for f in glob.glob("vibot_subs*"):
            try: os.remove(f)
            except: pass

        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['all'], 
            'outtmpl': 'vibot_subs',
            'quiet': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'socket_timeout': 15,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob("vibot_subs*.vtt")
        if not files:
            return None, "Bu videoda ne yazık ki hiçbir dilde altyazı veya konuşma bulunamadı."

        # DOSYA SEÇİM MANTIĞI:
        selected_file = None
        # 1. Önce Türkçe var mı?
        for f in files:
            if '.tr' in f:
                selected_file = f
                break
        # 2. Yoksa İngilizce var mı?
        if not selected_file:
            for f in files:
                if '.en' in f:
                    selected_file = f
                    break
        # 3. Yoksa en büyük dosyayı al (en çok yazı olan)
        if not selected_file:
            selected_file = max(files, key=os.path.getsize)

        with open(selected_file, 'r', encoding='utf-8') as f:
            content = f.read()
            final_text = clean_vtt(content)
        
        for f in glob.glob("vibot_subs*"):
            try: os.remove(f)
            except: pass
            
        return final_text, None

    except Exception as e:
        return None, f"Hata: {str(e)}"

# --- ARAYÜZ ---
video_url = st.text_input("", placeholder="Video linkini yapıştır...", label_visibility="collapsed")
analyze_btn = st.button("Analiz Et ✨")

if video_url:
    st.video(video_url)

if analyze_btn and video_url:
    with st.status("ViBot Verileri İşliyor...", expanded=True) as status:
        st.write("📡 Altyazılar taranıyor... (Bu işlem birkaç dakika sürebilir.)")
        text, error = get_transcript_smart(video_url)
        
        if error:
            status.update(label="Analiz Başarısız", state="error")
            st.warning(error)
            st.info("İpucu: Oyun videolarında konuşma yoksa analiz yapılamaz.")
        else:
            st.write(f"✅ Metin alındı ({len(text)} karakter)")
            st.write("🧠 ViBot düşünüyor...")
            
            try:
                llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
                prompt = f"""
                Sen ViBot adında asistanımsın. Metni analiz et (Türkçe).
                METİN: {text[:30000]}
                GÖREVLER: 1. Özet 2. Önemli Noktalar 3. Ana Fikir
                """
                res = llm.invoke(prompt)
                
                status.update(label="Analiz Tamamlandı!", state="complete")
                st.session_state['result'] = res.content
                st.session_state['full_text'] = text
            except Exception as e:
                st.error(f"AI Hatası: {e}")

if 'result' in st.session_state:
    st.markdown(f'<div class="result-card">{st.session_state["result"]}</div>', unsafe_allow_html=True)

if 'full_text' in st.session_state:
    st.divider()
    if q := st.chat_input("Video hakkında sor..."):
        with st.chat_message("user"): st.write(q)
        with st.chat_message("assistant", avatar="🤖"):
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
            ans = llm.invoke(f"Metin: {st.session_state['full_text'][:30000]}\nSoru: {q}\nCevap:")
            st.write(ans.content)

# --- İMZA (FOOTER) ---
st.markdown('<div class="footer">Developed by Yavuz Saraç 🚀 | ViBot v1.0</div>', unsafe_allow_html=True)