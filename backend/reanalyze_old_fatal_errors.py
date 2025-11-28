#!/usr/bin/env python
"""
批量重新分析舊版本的 Fatal Error 分析結果

此腳本用於修復 ANSI 控制字符 Bug 導致的錯誤分析結果。
會刪除舊的 fatal_analysis.json 並重新觸發分析任務。

使用方式：
    python reanalyze_old_fatal_errors.py --limit 100 --cutoff-date "2025-11-28T07:28:00"
"""

import os
import sys
import django
import json
import argparse
from pathlib import Path
from datetime import datetime

# Django 設置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_toolbox.settings')
django.setup()

from api.models import JenkinsBuild
from library.utils.console_log_analyzer import ConsoleLogAnalyzer


def main():
    parser = argparse.ArgumentParser(description='批量重新分析 Fatal Error')
    parser.add_argument('--limit', type=int, default=100, help='檢查最近 N 個 FAILURE Builds（預設 100）')
    parser.add_argument('--cutoff-date', type=str, default='2025-11-28T07:28:00', 
                        help='分析時間早於此時間的需要重新分析（預設 2025-11-28T07:28:00）')
    parser.add_argument('--dry-run', action='store_true', help='僅顯示需要重新分析的 Builds，不實際執行')
    parser.add_argument('--delete-only', action='store_true', help='僅刪除舊 JSON，不觸發新分析')
    
    args = parser.parse_args()
    
    print(f'=== 批量重新分析 Fatal Error ===')
    print(f'檢查範圍: 最近 {args.limit} 個 FAILURE Builds')
    print(f'分界時間: {args.cutoff_date}')
    print(f'模式: {"僅顯示" if args.dry_run else "僅刪除" if args.delete_only else "刪除並重新分析"}\n')
    
    # 查詢 FAILURE Builds
    builds = JenkinsBuild.objects.filter(
        result='FAILURE'
    ).select_related('job__server').order_by('-created_at')[:args.limit]
    
    print(f'共查詢到 {len(builds)} 個 FAILURE Builds\n')
    
    # 統計
    analyzed_count = 0
    error_builds = []
    
    for build in builds:
        server_url = build.job.server.url
        server_ip = server_url.replace('http://', '').replace('https://', '').split(':')[0]
        json_path = Path(f'/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/{server_ip}/{build.job.name}/{build.build_number}/fatal_analysis.json')
        
        if json_path.exists():
            analyzed_count += 1
            
            # 讀取分析時間
            try:
                with open(json_path) as f:
                    data = json.load(f)
                
                analyzed_at = data['build_info'].get('analyzed_at', '')
                fatal_count = data['summary'].get('total_fatal_count', 0)
                
                # 檢查是否需要重新分析
                if analyzed_at < args.cutoff_date:
                    error_builds.append({
                        'id': build.id,
                        'job': build.job.name,
                        'number': build.build_number,
                        'analyzed_at': analyzed_at,
                        'fatal_count': fatal_count,
                        'json_path': json_path
                    })
            except Exception as e:
                print(f'⚠️  讀取 {json_path} 失敗: {e}')
    
    print(f'統計結果:')
    print(f'  - 已分析的 Builds: {analyzed_count}')
    print(f'  - 需要重新分析: {len(error_builds)}\n')
    
    if not error_builds:
        print('✅ 沒有需要重新分析的 Builds')
        return
    
    # 顯示前 10 個
    print(f'前 10 個需要重新分析的 Builds:')
    for i, b in enumerate(error_builds[:10], 1):
        print(f'  {i}. Build #{b["number"]} ({b["job"]}) - Fatal: {b["fatal_count"]}, 分析時間: {b["analyzed_at"][:19]}')
    
    if len(error_builds) > 10:
        print(f'  ... 還有 {len(error_builds) - 10} 個')
    
    print()
    
    # Dry run 模式
    if args.dry_run:
        print('🔍 Dry run 模式，不執行實際操作')
        return
    
    # 確認
    confirm = input(f'確定要處理 {len(error_builds)} 個 Builds? (yes/no): ')
    if confirm.lower() != 'yes':
        print('❌ 取消操作')
        return
    
    # 開始處理
    print(f'\n開始處理...\n')
    deleted_count = 0
    reanalyzed_count = 0
    failed_count = 0
    
    for i, b in enumerate(error_builds, 1):
        print(f'[{i}/{len(error_builds)}] 處理 Build #{b["number"]} ({b["job"]})...')
        
        try:
            # 刪除舊 JSON
            if b['json_path'].exists():
                b['json_path'].unlink()
                deleted_count += 1
                print(f'  ✅ 已刪除舊分析: {b["json_path"]}')
            
            # 重新分析
            if not args.delete_only:
                # 獲取 console.log 路徑
                server_url = JenkinsBuild.objects.get(id=b['id']).job.server.url
                server_ip = server_url.replace('http://', '').replace('https://', '').split(':')[0]
                console_log_path = Path(f'/mnt/mdt/Team/PQ1-3/tool/jenkins_test_storage/{server_ip}/{b["job"]}/{b["number"]}/console.log')
                
                if console_log_path.exists():
                    # 執行分析
                    analyzer = ConsoleLogAnalyzer(
                        log_file_path=str(console_log_path),
                        server_ip=server_ip,
                        job_name=b['job'],
                        build_number=b['number']
                    )
                    result = analyzer.analyze_fatal_errors()
                    
                    # 保存結果
                    analyzer.save_analysis_to_json(str(b['json_path']))
                    reanalyzed_count += 1
                    print(f'  ✅ 已重新分析，Fatal 數: {result["summary"]["total_fatal_count"]}')
                else:
                    print(f'  ⚠️  Console.log 不存在: {console_log_path}')
        
        except Exception as e:
            failed_count += 1
            print(f'  ❌ 處理失敗: {e}')
    
    # 最終統計
    print(f'\n=== 處理完成 ===')
    print(f'刪除舊分析: {deleted_count}')
    if not args.delete_only:
        print(f'觸發重新分析: {reanalyzed_count}')
    print(f'失敗: {failed_count}')


if __name__ == '__main__':
    main()
