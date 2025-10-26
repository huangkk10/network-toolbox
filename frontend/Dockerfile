FROM node:18-alpine

# 設定工作目錄
WORKDIR /app

# 複製 package 文件
COPY package*.json ./

# 安裝依賴
RUN npm install

# 複製應用程式代碼
COPY . .

# 暴露端口
EXPOSE 3000

# 設定啟動命令
CMD ["npm", "start"]
