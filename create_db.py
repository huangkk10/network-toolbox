#!/usr/bin/env python3
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 連接到 postgres 預設資料庫
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres123",
    database="postgres"
)

# 設定自動提交模式
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# 創建資料庫
cursor = conn.cursor()
try:
    cursor.execute("CREATE DATABASE network_toolbox;")
    print("✅ 資料庫 'network_toolbox' 創建成功！")
except psycopg2.errors.DuplicateDatabase:
    print("ℹ️  資料庫 'network_toolbox' 已存在")
except Exception as e:
    print(f"❌ 錯誤: {e}")
finally:
    cursor.close()
    conn.close()
