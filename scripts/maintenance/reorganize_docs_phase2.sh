#!/bin/bash

# 文檔整理腳本 - 第二階段
# 整理根目錄剩餘的文檔到 docs/ 目錄

set -e

echo "================================================"
echo "📚 Network Toolbox - 文檔整理（第二階段）"
echo "================================================"
echo ""

cd "$(dirname "$0")"

# 創建必要的目錄
echo "1️⃣  創建目錄結構..."
mkdir -p docs/features/jenkins/artifacts
mkdir -p docs/development
mkdir -p docs/troubleshooting
echo "   ✅ 目錄已創建"
echo ""

# 移動 Jenkins Artifacts 相關文檔
echo "2️⃣  移動 Jenkins Artifacts 文檔..."
if [ -f "ARTIFACTS_AUTO_EXTRACT.md" ]; then
    mv ARTIFACTS_AUTO_EXTRACT.md docs/features/jenkins/artifacts/AUTO_EXTRACT_REPORT.md
    echo "   ✅ ARTIFACTS_AUTO_EXTRACT.md → docs/features/jenkins/artifacts/AUTO_EXTRACT_REPORT.md"
fi

if [ -f "CELERY_ARTIFACTS_TASKS.md" ]; then
    mv CELERY_ARTIFACTS_TASKS.md docs/features/jenkins/artifacts/CELERY_TASKS_REPORT.md
    echo "   ✅ CELERY_ARTIFACTS_TASKS.md → docs/features/jenkins/artifacts/CELERY_TASKS_REPORT.md"
fi

if [ -f "TEST_ARTIFACTS_AUTO_DELETE.md" ]; then
    mv TEST_ARTIFACTS_AUTO_DELETE.md docs/features/jenkins/artifacts/AUTO_DELETE_TEST.md
    echo "   ✅ TEST_ARTIFACTS_AUTO_DELETE.md → docs/features/jenkins/artifacts/AUTO_DELETE_TEST.md"
fi
echo ""

# 移動開發相關文檔
echo "3️⃣  移動開發相關文檔..."
if [ -f "CHANGELOG_AUTO_SYNC.md" ]; then
    mv CHANGELOG_AUTO_SYNC.md docs/development/CHANGELOG_AUTO_SYNC.md
    echo "   ✅ CHANGELOG_AUTO_SYNC.md → docs/development/"
fi

if [ -f "CLEANUP_REPORT.md" ]; then
    mv CLEANUP_REPORT.md docs/development/CLEANUP_REPORT_2025_11_10.md
    echo "   ✅ CLEANUP_REPORT.md → docs/development/CLEANUP_REPORT_2025_11_10.md"
fi

if [ -f "CLEANUP_TEST_SCRIPTS.md" ]; then
    mv CLEANUP_TEST_SCRIPTS.md docs/development/CLEANUP_TEST_SCRIPTS.md
    echo "   ✅ CLEANUP_TEST_SCRIPTS.md → docs/development/"
fi
echo ""

# 移動故障排查文檔
echo "4️⃣  移動故障排查文檔..."
if [ -f "VIEW_FILTER_BUG_FIX.md" ]; then
    mv VIEW_FILTER_BUG_FIX.md docs/troubleshooting/VIEW_FILTER_BUG_FIX.md
    echo "   ✅ VIEW_FILTER_BUG_FIX.md → docs/troubleshooting/"
fi
echo ""

# 顯示根目錄剩餘的 .md 文件
echo "5️⃣  檢查根目錄剩餘文檔..."
remaining_docs=$(ls -1 *.md 2>/dev/null | grep -v "README.md" | grep -v "SUMMARY.md" | grep -v "DOCS_REORGANIZATION_REPORT" || true)

if [ -z "$remaining_docs" ]; then
    echo "   ✅ 根目錄已清理完成，僅保留 README.md 和 SUMMARY.md"
else
    echo "   ⚠️  根目錄仍有以下文檔："
    echo "$remaining_docs" | sed 's/^/      - /'
fi
echo ""

# 顯示整理後的結構
echo "6️⃣  整理後的文檔結構："
echo ""
echo "   docs/features/jenkins/artifacts/"
ls -1 docs/features/jenkins/artifacts/*.md 2>/dev/null | sed 's|docs/features/jenkins/artifacts/|      - |' || echo "      (無文件)"
echo ""
echo "   docs/development/"
ls -1 docs/development/*.md 2>/dev/null | sed 's|docs/development/|      - |' || echo "      (無文件)"
echo ""
echo "   docs/troubleshooting/"
ls -1 docs/troubleshooting/*.md 2>/dev/null | sed 's|docs/troubleshooting/|      - |' || echo "      (無文件)"
echo ""

echo "================================================"
echo "✅ 文檔整理完成！"
echo "================================================"
echo ""
echo "📋 後續建議："
echo "   1. 查看整理報告：cat DOCS_REORGANIZATION_REPORT_2025_11_11.md"
echo "   2. 更新文檔索引：編輯 docs/README.md"
echo "   3. 提交變更：git add docs/ && git commit -m 'docs: 整理文檔結構'"
echo ""
