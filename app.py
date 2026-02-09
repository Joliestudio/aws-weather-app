import streamlit as st
import requests
import os
import pandas as pd  # <---【新增 1】記得引入 pandas
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 頁面設定
st.set_page_config(page_title="雲端氣象儀表板", page_icon="🌤️")

# 取得 API Key
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# --- 介面設計 ---
st.title("🌤️ 雲端架構師氣象站")
st.markdown("### Python Streamlit + AWS ECS Demo")

# 側邊欄
with st.sidebar:
    st.header("查詢設定")
    city = st.text_input("請輸入城市 (英文)", "Taipei")
    st.caption("例如: Tokyo, New York, London")

# --- 邏輯處理 ---
if st.button("查詢天氣", type="primary"):
    if not API_KEY:
        st.error("⚠️ 錯誤：找不到 API Key。請確認 .env 檔案或雲端環境變數已設定。")
    else:
        try:
            # 發送 API 請求
            params = {
                "q": city,
                "appid": API_KEY,
                "units": "metric",
                "lang": "zh_tw"
            }
            response = requests.get(BASE_URL, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # 1. 顯示主要數據 
                col1, col2, col3 = st.columns(3)
                col1.metric("溫度", f"{data['main']['temp']} °C")
                col2.metric("體感", f"{data['main']['feels_like']} °C")
                col3.metric("濕度", f"{data['main']['humidity']} %")
                
                weather_desc = data['weather'][0]['description']
                st.info(f"📍 {city} 目前天氣：{weather_desc}")
                
                # 2. 地圖功能 
                st.subheader("🗺️ 地理位置")
                lat = data['coord']['lat']
                lon = data['coord']['lon']
                
                # 建立 DataFrame 讓 st.map 使用
                map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
                
                # 顯示地圖 (zoom參數可調整縮放大小，預設自動)
                st.map(map_data, zoom=10)
                # ==========================================

                # 顯示 Raw Data
                with st.expander("查看原始 JSON 資料"):
                    st.json(data)

            else:
                st.error(f"找不到城市 '{city}'，請確認拼寫是否正確。")
                
        except Exception as e:
            st.error(f"連線發生錯誤: {e}")