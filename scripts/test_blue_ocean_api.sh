#!/bin/bash
# 快速測試 Blue Ocean Pipeline Stage API

API_BASE_URL="http://localhost/api"

echo "========================================"
echo "  Blue Ocean Pipeline Stage API 測試"
echo "========================================"
echo ""

# 1. 獲取所有 Build
echo "📋 步驟 1: 獲取所有 Build..."
response=$(curl -s "${API_BASE_URL}/jenkins-builds/?limit=5")
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"

# 檢查是否有 Build
build_count=$(echo "$response" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
echo ""
echo "找到 $build_count 個 Build"
echo ""

if [ "$build_count" -gt 0 ]; then
    # 獲取第一個 Build 的 ID
    build_id=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'])" 2>/dev/null)
    
    if [ -n "$build_id" ]; then
        echo "📋 步驟 2: 測試 Build #${build_id} 的 Pipeline Stage API..."
        echo ""
        
        # 2. 獲取 Pipeline Stage 資訊 (GET)
        echo "🔍 GET /api/jenkins-builds/${build_id}/pipeline_stages/"
        curl -s "${API_BASE_URL}/jenkins-builds/${build_id}/pipeline_stages/" | python3 -m json.tool 2>/dev/null
        echo ""
        
        # 3. 同步 Pipeline Stage 資訊 (POST)
        echo ""
        echo "🔄 POST /api/jenkins-builds/${build_id}/pipeline_stages/ (同步)"
        curl -s -X POST "${API_BASE_URL}/jenkins-builds/${build_id}/pipeline_stages/" | python3 -m json.tool 2>/dev/null
        echo ""
    else
        echo "❌ 無法獲取 Build ID"
    fi
else
    echo "❌ 找不到任何 Build，請先創建測試數據"
    echo ""
    echo "提示: 執行以下命令創建測試數據"
    echo "docker exec nt-django python create_jenkins_test_data.py"
fi

echo ""
echo "========================================"
echo "  測試完成"
echo "========================================"
