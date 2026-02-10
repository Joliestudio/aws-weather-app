import streamlit as st
import requests
import os
import pandas as pd
import logging
import json
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import pytz

# --- 1. 系統設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 載入環境變數
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')
load_dotenv(dotenv_path=env_path, override=True)

st.set_page_config(page_title="AI 氣象旅遊嚮導", page_icon="🤖", layout="wide")

# --- 2. 資料庫設定 (PostgreSQL) ---
# 從環境變數讀取 DB 設定 (Terraform 會注入這些變數)
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "weatherdb")

# 如果是在本地開發，且沒有 DB，使用 SQLite 當作備案 (避免報錯)
if DB_HOST:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
else:
    DATABASE_URL = "sqlite:///local_test.db"
    logger.warning("⚠️ 使用本地 SQLite 模式 (未偵測到 RDS)")

# 建立 DB Engine
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 定義 Log 資料表結構
class SearchLog(Base):
    __tablename__ = 'search_logs'
    id = Column(Integer, primary_key=True)
    query_city = Column(String)
    weather_desc = Column(String)
    temp = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

# 初始化資料庫 (如果表不存在則建立)
try:
    Base.metadata.create_all(engine)
except Exception as e:
    logger.error(f"DB Init Error: {e}")

# DB 操作函式
def log_to_db(city, weather, temperature):
    """寫入查詢紀錄"""
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        new_log = SearchLog(query_city=city, weather_desc=weather, temp=str(temperature), timestamp=datetime.now(pytz.timezone('Asia/Taipei')))
        session.add(new_log)
        session.commit()
        session.close()
        logger.info(f"✅ Log saved: {city}")
    except Exception as e:
        logger.error(f"DB Save Error: {e}")

def get_all_logs():
    """讀取所有紀錄"""
    try:
        df = pd.read_sql("SELECT * FROM search_logs ORDER BY timestamp DESC", engine)
        return df
    except Exception as e:
        logger.error(f"DB Read Error: {e}")
        return pd.DataFrame()

# --- 3. 核心功能函式 (Geocoding + Weather + AI) ---
@st.cache_data(ttl=600)
def get_weather_data(city_name, api_key):
    if not api_key: return None
    try:
        # Geocoding
        geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        geo_res = requests.get(geo_url, params={"q": city_name, "limit": 1, "appid": api_key})
        geo_data = geo_res.json()
        if not geo_data: return None
        
        lat, lon = geo_data[0]['lat'], geo_data[0]['lon']
        city_en = geo_data[0]['name']

        # Weather
        w_url = "http://api.openweathermap.org/data/2.5/weather"
        w_res = requests.get(w_url, params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "zh_tw"})
        w_res.raise_for_status()
        
        final_data = w_res.json()
        final_data['geo_name'] = city_en
        return final_data
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None

def get_ai_advice(api_key, city, desc, temp):
    if not api_key: return "API Key Missing", None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"地點：{city}，天氣：{desc}，溫度：{temp}°C。請給半日遊建議 (繁體中文)。"
        response = model.generate_content(prompt)
        return response.text, {"response": response.text}
    except Exception as e:
        return f"AI Error: {e}", {"error": str(e)}

# --- 4. UI 與 主程式 ---
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

st.title("🤖 AI 氣象旅遊嚮導")

# 側邊欄：導航
page = st.sidebar.radio("導航", ["🌏 旅遊查詢", "🔐 管理者後台"])

if page == "🌏 旅遊查詢":
    if not WEATHER_API_KEY: st.error("System Error: No API Key"); st.stop()
    
    st.sidebar.header("🔍 目的地")
    city_input = st.sidebar.text_input("輸入城市", "台北")
    run_query = st.sidebar.button("🚀 查詢", type="primary")
    
    if run_query or city_input:
        with st.spinner("查詢中..."):
            data = get_weather_data(city_input, WEATHER_API_KEY)
            if data:
                desc = data['weather'][0]['description']
                temp = data['main']['temp']
                found_name = data.get('geo_name', data['name'])
                
                # 1. 寫入資料庫 (Log)
                log_to_db(found_name, desc, temp)
                
                # 2. 顯示資訊
                col1, col2 = st.columns([1, 1.5])
                with col1:
                    st.metric(f"{found_name}", f"{temp} °C", desc)
                    st.map(pd.DataFrame({'lat': [data['coord']['lat']], 'lon': [data['coord']['lon']]}))
                with col2:
                    st.subheader("🤖 AI 建議")
                    if GEMINI_API_KEY:
                        advice, _ = get_ai_advice(GEMINI_API_KEY, found_name, desc, temp)
                        st.markdown(advice)
            else:
                st.error("找不到城市")

elif page == "🔐 管理者後台":
    st.header("🔐 管理者登入")
    
    # 簡單的登入機制
    with st.form("login_form"):
        user = st.text_input("帳號")
        pwd = st.text_input("密碼", type="password")
        submitted = st.form_submit_button("登入")
    
    if submitted:
        if user == "admin" and pwd == "admin123": # 實務上密碼不應寫死在 code 裡
            st.session_state['logged_in'] = True
            st.success("登入成功")
        else:
            st.error("帳號或密碼錯誤")
    
    if st.session_state.get('logged_in'):
        st.divider()
        st.subheader("📊 查詢紀錄報表")
        
        # 顯示資料庫內容
        df_logs = get_all_logs()
        if not df_logs.empty:
            st.dataframe(df_logs, use_container_width=True)
            
            # 簡單統計圖表
            st.subheader("📈 熱門查詢城市")
            if 'query_city' in df_logs.columns:
                city_counts = df_logs['query_city'].value_counts()
                st.bar_chart(city_counts)
        else:
            st.info("目前沒有查詢紀錄")