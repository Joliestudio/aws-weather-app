# 🌤️ Cloud Weather Architecture

[![CI/CD Build](https://github.com/joliestudio/weather-app-demo/actions/workflows/deploy.yml/badge.svg)](https://github.com/你的帳號/weather-app-demo/actions)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-purple)](https://www.terraform.io/)
[![Docker](https://img.shields.io/badge/Container-Docker-blue)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/Cloud-AWS%20EC2-orange)](https://aws.amazon.com/)

這是一個展示現代化雲端後端架構的專案。目標是建立一個高可用、自動化部署的 Python 前端應用程式。
整合了 **Infrastructure as Code (IaC)**、**Containerization** 與 **CI/CD Pipeline**。

---

## 系統架構 (System Architecture)

### 1. 雲端基礎設施 (AWS + Terraform)
本專案不使用手動點擊 Console，而是全權透過 Terraform 進行資源編排。
* **Compute:** AWS EC2 (t3.micro) - 採用 Cost-Effective 策略。
* **Network:** VPC, Security Group (只開放必要 Port 8501, 22)。
* **Provisioning:** 使用 User Data 在實例啟動時自動安裝 Docker 環境。

*(請在此處插入你的 Mermaid 雲端架構圖圖片)*

### 2. CI/CD 流水線 (GitHub Actions)
自動化流程確保程式碼更動能即時反映到生產環境。
1. **Source:** 開發者推送代碼至 `develop` / `main` 分支。
2. **Build:** GitHub Actions 啟動，建立 Docker Image。
3. **Push:** 將 Image 推送至 Docker Hub (Public Registry)。
4. **Deploy:** 透過 Terraform Replace 或 EC2 User Data 拉取最新映像檔。


*(請在此處插入你的 CI/CD 流程圖圖片)*

---

## 技術棧 

| Category | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | Python Streamlit | 快速建構資料視覺化儀表板 |
| **Container** | Docker | 確保開發與生產環境一致性 (Write Once, Run Anywhere) |
| **IaC** | Terraform | 定義 AWS 基礎設施，實現可重複部署 |
| **CI/CD** | GitHub Actions | 自動化建置與發布流程 |
| **Cloud** | AWS EC2 (Free Tier) | 雲端運算資源 |
| **API** | OpenWeatherMap | 第三方 RESTful API 氣象資料來源 |

---

## 快速開始 

### 1. 環境變數設定
請複製範本檔案並設定您的 API Key：
```bash
cp .env.example .env
# 編輯 .env 填入 OPENWEATHER_API_KEY