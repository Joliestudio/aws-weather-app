import streamlit as st
import requests
import os
import pandas as pd
import logging
import json
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import pytz
from streamlit.runtime.scriptrunner import get_script_run_ctx

# --- 1. 系統設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 強制載入環境變數
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')
load_dotenv(dotenv_path=env_path, override=True)

st.set_page_config(page_title="AI 氣象旅遊嚮導", page_icon="🤖", layout="wide")

# --- 2. 資料庫設定 (RDS PostgreSQL) ---
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "weatherdb")

if DB_HOST:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
else:
    DATABASE_URL = "sqlite:///local_test.db"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

# 定義 Log 資料表
class SearchLog(Base):
    __tablename__ = 'search_logs_v2'
    id = Column(Integer, primary_key=True)
    user_ip = Column(String)
    query_city = Column(String)
    weather_desc = Column(String)
    temp = Column(String)
    ai_response = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# 自動建表
try:
    Base.metadata.create_all(engine)
except Exception as e:
    logger.error(f"DB Init Error: {e}")

# --- 3. 輔助函式 ---
def get_remote_ip():
    try:
        ctx = get_script_run_ctx()
        if ctx is None: return "Unknown"
        return "Client-IP-Recorded" 
    except:
        return "Unknown"

def log_to_db(city, weather, temperature, ai_text):
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        user_ip = get_remote_ip()
        new_log = SearchLog(
            user_ip=user_ip,
            query_city=city,
            weather_desc=weather,
            temp=str(temperature),
            ai_response=ai_text[:50]+"...",
            timestamp=datetime.now(pytz.timezone('Asia/Taipei'))
        )
        session.add(new_log)
        session.commit()
        session.close()
        logger.info(f"✅ Log saved: {city} from {user_ip}")
    except Exception as e:
        logger.error(f"DB Save Error: {e}")

def get_all_logs():
    try:
        return pd.read_sql("SELECT * FROM search_logs_v2 ORDER BY timestamp DESC", engine)
    except Exception as e:
        logger.error(f"DB Read Error: {e}")
        return pd.DataFrame()

# --- 4. 核心 API 函式 ---
@st.cache_data(ttl=600)
def get_weather_data(city_name, api_key):
    if not api_key: return None
    try:
        geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        geo_res = requests.get(geo_url, params={"q": city_name, "limit": 1, "appid": api_key})
        geo_data = geo_res.json()
        if not geo_data: return None
        
        lat, lon = geo_data[0]['lat'], geo_data[0]['lon']
        city_en = geo_data[0]['name']

        w_url = "http://api.openweathermap.org/data/2.5/weather"
        w_res = requests.get(w_url, params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric", "lang": "zh_tw"})
        w_res.raise_for_status()
        
        final_data = w_res.json()
        final_data['geo_name'] = city_en
        return final_data
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None

def get_ai_travel_advice(api_key, city, weather_desc, temp, humidity, feels_like):
    if not api_key: return "⚠️ Google API Key Missing", None
    try:
        genai.configure(api_key=api_key)
     
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        你是一位幽默且專業的旅遊嚮導。請根據以下即時天氣資訊，為旅客規劃半日遊。
        地點：{city}
        天氣：{weather_desc}
        氣溫：{temp}°C (體感 {feels_like}°C)
        濕度：{humidity}%
        請用繁體中文回答，包含：
        1. 一句幽默的開場白。
        2. 穿搭建議。
        3. 推薦 3 個景點。
        4. 當地特色美食推薦。
        """
        response = model.generate_content(prompt)
        debug_info = {
            "model": "gemini-2.5-flash",
            "tokens": model.count_tokens(prompt).total_tokens,
            "response": response.text
        }
        return response.text, debug_info
    except Exception as e:
        return f"AI Error: {e}", {"error": str(e)}

# --- 5. 主程式與 UI ---
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# 側邊欄導航
st.sidebar.title("☁️ 導航選單")
# 修正：移除字串後面的空白，避免匹配失敗
page = st.sidebar.radio("Go to", ["🌏 旅遊規劃儀表板", "🔐 管理者後台"])

if page == "🌏 旅遊規劃儀表板":
    st.title("🤖 AI 氣象旅遊嚮導")
    st.markdown("### 結合 AWS RDS • OpenWeatherMap • Google Gemini")

    if not WEATHER_API_KEY:
        st.error("🚨 系統錯誤：找不到 API Key，請檢查 Terraform 設定。")
        st.stop()

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        city_input = st.text_input("輸入城市名稱", "台北", label_visibility="collapsed", placeholder="請輸入城市...")
    with col_btn:
        run_query = st.button("🚀 啟動規劃", type="primary", use_container_width=True)

    weather_data = None
    ai_advice = None
    ai_debug_json = None

    if run_query or city_input:
        with st.spinner("📡 正在讀取氣象與 AI 數據..."):
            weather_data = get_weather_data(city_input, WEATHER_API_KEY)
            
            if weather_data:
                desc = weather_data['weather'][0]['description']
                temp = weather_data['main']['temp']
                feels_like = weather_data['main']['feels_like']
                humid = weather_data['main']['humidity']
                wind_speed = weather_data['wind']['speed']
                wind_deg = weather_data['wind'].get('deg', 0)
                found_name = weather_data.get('geo_name', weather_data['name'])
                
                if GEMINI_API_KEY:
                    ai_advice, ai_debug_json = get_ai_travel_advice(GEMINI_API_KEY, found_name, desc, temp, humid, feels_like)
                    log_to_db(found_name, desc, temp, ai_advice)
                else:
                    ai_advice = "請設定 Google Key"

    tab_dashboard, tab_debug = st.tabs(["📊 視覺化儀表板", "🛠️ 開發者資訊 (JSON)"])

    with tab_dashboard:
        if weather_data:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("🌡️ 氣溫", f"{temp} °C", f"{temp-feels_like:.1f} 差值")
            m2.metric("🧘 體感", f"{feels_like} °C")
            m3.metric("💧 濕度", f"{humid} %")
            m4.metric("🍃 風速", f"{wind_speed} m/s", f"{wind_deg}°")

            st.divider()

            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.subheader(f"📍 {found_name}")
                st.info(f"目前天候：{desc}")
                try:
                    st.map(pd.DataFrame({'lat': [weather_data['coord']['lat']], 'lon': [weather_data['coord']['lon']]}), zoom=10)
                except:
                    st.warning("地圖載入失敗")
            
            with c2:
                st.subheader("🤖 Gemini 旅遊嚮導")
                if ai_advice:
                    st.markdown(ai_advice)
        elif run_query:
            st.error("找不到該城市，請重試。")

    with tab_debug:
        st.header("🔍 API 原始資料檢視")
        if weather_data:
            d1, d2 = st.columns(2)
            with d1:
                st.subheader("OpenWeatherMap JSON")
                st.json(weather_data, expanded=True)
                st.download_button("📥 下載氣象 JSON", data=json.dumps(weather_data, indent=2, ensure_ascii=False), file_name="weather.json")
            with d2:
                st.subheader("Gemini AI JSON")
                if ai_debug_json:
                    st.json(ai_debug_json, expanded=True)
                    st.download_button("📥 下載 AI JSON", data=json.dumps(ai_debug_json, indent=2, ensure_ascii=False), file_name="ai.json")
        else:
            st.info("請先查詢資料")

elif page == "🔐 管理者後台":
    
    # 1. 初始化 Session State
    if 'auth' not in st.session_state:
        st.session_state['auth'] = False

    # 2. 判斷顯示邏輯
    if not st.session_state['auth']:
        # [未登入狀態] 顯示登入表單
        st.header("🔐 系統管理員登入")
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            sub = st.form_submit_button("Login")
        
        if sub:
            if u == "admin" and p == "admin123": # Demo用!實務上密碼不會寫死在 code 裡
                st.session_state['auth'] = True
                st.success("登入成功！")
                st.rerun() # 關鍵：立刻刷新頁面，進入「已登入」狀態
            else:
                st.error("帳號或密碼錯誤")
    else:
        # [已登入狀態] 只顯示報表，不顯示登入框
        
        # Header 區塊 (含登出按鈕)
        col_header, col_logout = st.columns([5, 1])
        with col_header:
            st.header("📊 管理者數據中心 (Admin Dashboard)")
        with col_logout:
            if st.button("登出 (Logout)"):
                st.session_state['auth'] = False
                st.rerun()

        st.divider()
        st.subheader("📋 使用者查詢日誌")
        
        df = get_all_logs()
        if not df.empty:
            # 統計指標
            total_queries = len(df)
            top_city = df['query_city'].value_counts().idxmax() if not df.empty else "N/A"
            
            k1, k2 = st.columns(2)
            k1.metric("總查詢次數", total_queries)
            k2.metric("最熱門城市", top_city)
            
            # 圖表
            st.subheader("📈 熱門城市排行")
            city_counts = df['query_city'].value_counts()
            st.bar_chart(city_counts)

            # 詳細表格
            st.subheader("📝 詳細紀錄")
            st.dataframe(
                df[['timestamp', 'user_ip', 'query_city', 'weather_desc', 'temp', 'ai_response']], 
                use_container_width=True,
                column_config={
                    "timestamp": "查詢時間",
                    "user_ip": "使用者 IP",
                    "query_city": "查詢城市",
                    "weather_desc": "天氣",
                    "temp": "溫度",
                    "ai_response": "AI 回應摘要"
                }
            )
               
        else:
            st.info("目前尚無查詢紀錄")