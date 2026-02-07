# 1. 使用輕量級的 Python 3.9 基底映像檔
FROM python:3.9-slim

# 2. 設定容器內的工作目錄
WORKDIR /app

# 3. 複製需求清單並安裝 (利用 Docker Cache 加速)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 複製所有程式碼到容器內
COPY . .

# 5. 告訴 Docker 這個容器會使用 8501 Port
EXPOSE 8501

# 6. 設定啟動指令
# --server.address=0.0.0.0 是讓容器可以被外部存取的關鍵
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]