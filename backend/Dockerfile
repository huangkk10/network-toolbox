FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    postgresql-client \
    iputils-ping \
    cifs-utils \
    p7zip-full \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    supervisor \
    ntpsec-ntpdate \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# NTP 自動時間同步配置
# ============================================================================
# 配置 sudo 無密碼執行 ntpdate
RUN echo "# Allow root user to run ntpdate without password" > /etc/sudoers.d/ntpdate && \
    echo "# Created: 2025-11-23" >> /etc/sudoers.d/ntpdate && \
    echo "# Purpose: NTP auto sync system" >> /etc/sudoers.d/ntpdate && \
    echo "" >> /etc/sudoers.d/ntpdate && \
    echo "root ALL=(ALL) NOPASSWD: /usr/sbin/ntpdate" >> /etc/sudoers.d/ntpdate && \
    echo "" >> /etc/sudoers.d/ntpdate && \
    echo "# 防止 tty 要求問題" >> /etc/sudoers.d/ntpdate && \
    echo "Defaults:root !requiretty" >> /etc/sudoers.d/ntpdate && \
    chmod 0440 /etc/sudoers.d/ntpdate && \
    visudo -c

# 建立 Supervisor 日誌目錄
RUN mkdir -p /var/log/supervisor

# 複製依賴文件
COPY requirements.txt /app/

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . /app/

# 創建日誌目錄
RUN mkdir -p /app/logs && chmod 777 /app/logs

# 複製 Supervisor 配置
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 設置啟動腳本權限
RUN chmod +x /app/entrypoint.sh /app/mount_nas.sh

# 暴露端口
EXPOSE 8000

# 設定啟動命令
CMD ["/app/entrypoint.sh"]
