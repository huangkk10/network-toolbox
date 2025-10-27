# ============================================
# Windows DHCP Server 租約導出腳本
# 生成時間: 2025-10-27
# 目標: 導出所有 Scope 的租約到 JSON 文件
# ============================================

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Windows DHCP 租約導出工具" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 設定輸出文件
$OutputFile = "C:\dhcp_leases.json"

try {
    Write-Host "[1/4] 檢查 DHCP Server 服務..." -ForegroundColor Yellow
    
    # 獲取所有 Scope
    $scopes = Get-DhcpServerv4Scope -ComputerName localhost
    
    if ($scopes.Count -eq 0) {
        Write-Host "  ✗ 未找到任何 Scope！" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  ✓ 找到 $($scopes.Count) 個 Scope" -ForegroundColor Green
    Write-Host ""
    
    # 顯示 Scope 資訊
    Write-Host "[2/4] Scope 清單:" -ForegroundColor Yellow
    foreach ($scope in $scopes) {
        Write-Host "  - $($scope.ScopeId) : $($scope.Name) ($($scope.State))" -ForegroundColor Cyan
    }
    Write-Host ""
    
    # 獲取所有租約
    Write-Host "[3/4] 獲取租約資料..." -ForegroundColor Yellow
    
    $allLeases = @()
    $totalCount = 0
    
    foreach ($scope in $scopes) {
        Write-Host "  處理 Scope: $($scope.ScopeId)" -ForegroundColor Gray
        
        try {
            $leases = Get-DhcpServerv4Lease -ComputerName localhost -ScopeId $scope.ScopeId
            
            if ($leases) {
                $allLeases += $leases
                $totalCount += $leases.Count
                Write-Host "    ✓ 獲取 $($leases.Count) 筆租約" -ForegroundColor Green
            } else {
                Write-Host "    - 沒有租約" -ForegroundColor Gray
            }
        }
        catch {
            Write-Host "    ✗ 錯誤: $_" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "  ✓ 共獲取 $totalCount 筆租約" -ForegroundColor Green
    Write-Host ""
    
    if ($totalCount -eq 0) {
        Write-Host "  ⚠ 沒有租約資料可導出" -ForegroundColor Yellow
        exit 0
    }
    
    # 轉換為 JSON 格式
    Write-Host "[4/4] 導出到文件..." -ForegroundColor Yellow
    
    $exportData = $allLeases | Select-Object `
        @{Name='IPAddress'; Expression={$_.IPAddress.ToString()}}, `
        @{Name='ClientId'; Expression={$_.ClientId}}, `
        @{Name='HostName'; Expression={$_.HostName}}, `
        @{Name='AddressState'; Expression={$_.AddressState.ToString()}}, `
        @{Name='LeaseExpiryTime'; Expression={$_.LeaseExpiryTime.ToString("yyyy-MM-dd HH:mm:ss")}}, `
        @{Name='ScopeId'; Expression={$_.ScopeId.ToString()}}
    
    # 導出為 JSON（UTF-8 編碼）
    $exportData | ConvertTo-Json -Depth 10 | Out-File -FilePath $OutputFile -Encoding UTF8
    
    # 確認文件
    if (Test-Path $OutputFile) {
        $fileInfo = Get-Item $OutputFile
        Write-Host "  ✓ 成功導出到: $OutputFile" -ForegroundColor Green
        Write-Host "  ✓ 文件大小: $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor Green
        Write-Host ""
        
        # 顯示前 3 筆樣本
        Write-Host "前 3 筆樣本資料:" -ForegroundColor Cyan
        $sampleData = $exportData | Select-Object -First 3
        foreach ($lease in $sampleData) {
            Write-Host "  IP: $($lease.IPAddress) | MAC: $($lease.ClientId) | Hostname: $($lease.HostName)" -ForegroundColor Gray
        }
        Write-Host ""
        
        Write-Host "=====================================" -ForegroundColor Cyan
        Write-Host "  導出完成！" -ForegroundColor Green
        Write-Host "=====================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "下一步操作:" -ForegroundColor Yellow
        Write-Host "  1. 將文件 $OutputFile 複製到 Linux 伺服器" -ForegroundColor White
        Write-Host "  2. 在 Linux 上執行匯入命令（參考文檔）" -ForegroundColor White
        Write-Host ""
        
    } else {
        Write-Host "  ✗ 文件導出失敗！" -ForegroundColor Red
        exit 1
    }
    
}
catch {
    Write-Host ""
    Write-Host "✗ 發生錯誤: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "請確認:" -ForegroundColor Yellow
    Write-Host "  1. 您是否以管理員身份執行此腳本？" -ForegroundColor White
    Write-Host "  2. DHCP Server 服務是否正在運行？" -ForegroundColor White
    Write-Host "  3. 您是否有 DHCP Administrators 權限？" -ForegroundColor White
    Write-Host ""
    exit 1
}
