import streamlit as st
import requests
import os
import pandas as pd
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. 系統設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

st.set_page_config(page_title="AI 氣象旅遊嚮導", page_icon="🤖", layout="wide")

# --- 2. 核心功能函式 ---
@st.cache_data(ttl=600)
def get_weather_data(city_name, api_key):
    """取得 OpenWeatherMap 資料"""
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city_name, "appid": api_key, "units": "metric", "lang": "zh_tw"}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Weather API Error: {e}")
        return None

def get_ai_travel_advice(api_key, city, weather_desc, temp, humidity):
    """呼叫 Google Gemini 生成旅遊建議"""
    if not api_key:
        return "⚠️ 請設定 Google Gemini API Key 以啟用 AI 功能"
    
    try:
        # 設定 API Key
        genai.configure(api_key=api_key)
        
        # 使用最新的 Flash 模型 (速度快且穩定)
        model = genai.GenerativeModel('	gemini-2.5-flash-lite') 
        
        prompt = f"""
        你是一位專業的旅遊嚮導。請根據以下即時天氣資訊，為旅客規劃一個簡單的半日遊行程。
        
        地點：{city}
        天氣狀況：{weather_desc}
        氣溫：{temp}°C
        濕度：{humidity}%
        
        請用繁體中文回答，包含以下內容：
        1. 一句幽默的開場白（關於天氣）。
        2. 穿搭建議。
        3. 推薦的 3 個景點或活動（如果下雨請推薦室內，晴天推薦戶外）。
        4. 當地特色美食推薦。
        """
        
        with st.spinner('🤖 AI 正在絞盡腦汁為您規劃行程...'):
            response = model.generate_content(prompt)
            return response.text
            
    except Exception as e:
        # 增加錯誤日誌以便除錯
        logging.error(f"Gemini AI Error: {e}")
        return f"AI 暫時無法連線: {str(e)}"

# --- 3. UI 介面設計 ---
st.title("🤖 AI 氣象旅遊嚮導")
st.markdown("### 結合 OpenWeatherMap 與 Google Gemini 的智慧決策系統")
st.markdown("---")

# 側邊欄
with st.sidebar:
    st.header("⚙️ 設定")
    
    # 氣象 API Key
    weather_api_key = os.getenv("OPENWEATHER_API_KEY")
    if not weather_api_key:
        weather_api_key = st.text_input("OpenWeather API Key", type="password")

    # Gemini API Key (新增)
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        gemini_api_key = st.text_input("Google Gemini API Key", type="password")
        
    city = st.text_input("輸入城市 (英文)", "Kyoto")
    st.info("💡 提示：AI 會根據天氣好壞自動調整行程建議")

# --- 4. 主邏輯 ---
if st.button("🚀 啟動 AI 規劃", type="primary") or city:
    if not weather_api_key:
        st.error("❌ 缺少 Weather API Key")
    else:
        # 1. 取得天氣
        weather_data = get_weather_data(city, weather_api_key)
        
        if weather_data:
            # 版面配置：左氣象，右 AI
            col1, col2 = st.columns([1, 1.5])
            
            with col1:
                st.subheader(f"📍 {weather_data['name']} 即時氣象")
                
                # 數據提取
                desc = weather_data['weather'][0]['description']
                temp = weather_data['main']['temp']
                humid = weather_data['main']['humidity']
                
                st.metric("溫度", f"{temp} °C")
                st.metric("濕度", f"{humid} %")
                st.info(f"現況：{desc}")
                
                # 地圖
                lat = weather_data['coord']['lat']
                lon = weather_data['coord']['lon']
                st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=10)

            with col2:
                st.subheader("🤖 Gemini 旅遊顧問建議")
                
                # 2. 呼叫 AI
                if gemini_api_key:
                    advice = get_ai_travel_advice(gemini_api_key, city, desc, temp, humid)
                    st.markdown(advice)
                else:
                    st.warning("⚠️ 未設定 Google API Key，僅顯示氣象資料。")
                    st.markdown("""
                    **想要 AI 幫你排行程嗎？**
                    1. 去 Google AI Studio 申請 Key
                    2. 填入側邊欄
                    """)
        else:
            st.error("找不到城市或連線失敗")

st.markdown("---")
st.caption("Powered by Streamlit, OpenWeatherMap & Google Gemini")