#!/usr/bin/env python3
"""
Dify API 測試腳本

比較 Dify 工作室和 API 的回答差異
"""

import requests
import json

# ==================== 配置區 ====================
# 請填入您的 Dify API 配置
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"  # 修改為您的 Dify API 端點
DIFY_API_KEY = "YOUR_API_KEY_HERE"  # 修改為您的 API Key
DIFY_USER = "test-user"  # 使用者識別碼

# 測試問題
TEST_QUESTION = "CrystalDiskMark 5 的內容有什麼"

# ==================== 測試函數 ====================

def test_dify_api(question):
    """
    測試 Dify API
    
    Args:
        question: 要問的問題
        
    Returns:
        dict: API 響應結果
    """
    print("=" * 60)
    print("🧪 測試 Dify API")
    print("=" * 60)
    print(f"問題: {question}")
    print("-" * 60)
    
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": {},
        "query": question,
        "response_mode": "blocking",  # 或 "streaming"
        "conversation_id": "",
        "user": DIFY_USER
    }
    
    try:
        response = requests.post(
            DIFY_API_URL,
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ API 回答:")
            print("-" * 60)
            print(result.get('answer', '無回答'))
            print("-" * 60)
            print(f"\n詳細資訊:")
            print(f"  - 對話 ID: {result.get('conversation_id', 'N/A')}")
            print(f"  - 訊息 ID: {result.get('message_id', 'N/A')}")
            print(f"  - Token 使用: {result.get('metadata', {}).get('usage', 'N/A')}")
            return result
        else:
            print(f"\n❌ API 錯誤:")
            print(f"  - 狀態碼: {response.status_code}")
            print(f"  - 錯誤訊息: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n❌ 請求超時（超過 30 秒）")
        return None
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        return None


def analyze_difference():
    """分析兩種方式的差異"""
    print("\n\n")
    print("=" * 60)
    print("📊 差異分析")
    print("=" * 60)
    
    print("""
    Dify 工作室 vs Dify API 的可能差異：
    
    1. **知識庫範圍**
       - 工作室: 可能使用完整的知識庫
       - API: 可能受限於應用配置的知識範圍
    
    2. **模型版本**
       - 工作室: 可能使用最新版本模型
       - API: 取決於應用配置的模型選擇
    
    3. **提示詞 (System Prompt)**
       - 工作室: 通用助手提示詞
       - API: 應用特定的提示詞配置
    
    4. **檢索設定**
       - 工作室: 預設檢索設定
       - API: 應用自訂的檢索參數
    
    5. **上下文長度**
       - 工作室: 較大的上下文窗口
       - API: 受應用配置限制
    """)
    
    print("\n建議檢查項目:")
    print("  1. 登入 Dify 控制台")
    print("  2. 檢查您的應用配置")
    print("  3. 確認「知識庫」是否已啟用")
    print("  4. 檢查「檢索設定」是否正確")
    print("  5. 確認使用的模型版本")


def main():
    """主程式"""
    print("\n" + "=" * 60)
    print("🔍 Dify API vs 工作室回答差異測試")
    print("=" * 60)
    
    # 檢查配置
    if DIFY_API_KEY == "YOUR_API_KEY_HERE":
        print("\n❌ 錯誤: 請先配置 DIFY_API_KEY")
        print("\n請編輯此腳本，填入您的 Dify API 配置：")
        print("  1. DIFY_API_URL - Dify API 端點")
        print("  2. DIFY_API_KEY - 在 Dify 控制台獲取的 API Key")
        print("\n取得方式：")
        print("  1. 登入 Dify 控制台: https://cloud.dify.ai/")
        print("  2. 選擇您的應用")
        print("  3. 點擊「API 訪問」")
        print("  4. 複製 API Key 和端點 URL")
        return
    
    # 執行測試
    result = test_dify_api(TEST_QUESTION)
    
    # 分析差異
    analyze_difference()
    
    # 總結
    print("\n\n")
    print("=" * 60)
    print("📋 測試總結")
    print("=" * 60)
    
    if result:
        print("✅ Dify API 測試成功")
        print("\n如果 API 回答與工作室不同，請檢查：")
        print("  1. 應用的知識庫配置")
        print("  2. 提示詞設定")
        print("  3. 模型選擇")
    else:
        print("❌ Dify API 測試失敗")
        print("請檢查 API 配置是否正確")


if __name__ == "__main__":
    main()
