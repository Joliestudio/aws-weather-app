# Cloud Weather App (雲端氣象儀表板)

這是一個基於 Python Streamlit 的氣象查詢應用程式，展示了現代化雲端架構的建置流程。
專案整合了 Docker 容器化技術、AWS 雲端基礎設施 (IaC) 以及 CI/CD 自動化部署。

## 專案特色

* **Frontend:** 使用 Python `Streamlit` 快速建構互動式介面。
* **API Integration:** 串接 OpenWeatherMap RESTful API 取得即時氣象。
* **Containerization:** 使用 `Docker` 確保開發與生產環境一致。
* **IaC:** 使用 `Terraform` 自動部署 AWS EC2 資源。
* **CI/CD:** 使用 `GitHub Actions` 自動建置並推送 Image 至 Docker Hub。

## 架構設計 

### 雲端架構圖
![Cloud Architecture](./docs/architecture_diagram.png)
*(請將 Mermaid 產生的圖存檔放在 docs 資料夾或直接貼圖)*

本專案採用 **AWS EC2 (Free Tier)** 搭配 **Docker** 進行部署。
* **Cost Optimization:** 選擇 t3.micro 實例以利用 AWS 免費方案。
* **Automation:** 透過 User Data 腳本在開機時自動拉取最新的 Docker Image。

## ⚙️ 如何執行 

### 1. 本地開發 
```bash
# 安裝依賴
pip install -r requirements.txt

# 設定 API Key (.env)
echo "OPENWEATHER_API_KEY=your_key_here" > .env

# 啟動應用
streamlit run app.py