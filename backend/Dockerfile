FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    postgresql-client \
    iputils-ping \
    cifs-utils \
    p7zip-full \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt /app/

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . /app/

# 創建日誌目錄
RUN mkdir -p /app/logs && chmod 777 /app/logs

# 設置啟動腳本權限
RUN chmod +x /app/entrypoint.sh /app/mount_nas.sh

# 暴露端口
EXPOSE 8000

# 設定啟動命令
CMD ["/app/entrypoint.sh"]
