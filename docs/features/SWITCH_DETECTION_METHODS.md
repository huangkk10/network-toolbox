# Switch 設備識別方法大全

> **目標**: 從 DHCP Server 和網路環境中識別出哪些設備是 Switch

## 📋 目錄

1. [DHCP 資料庫分析方法](#1-dhcp-資料庫分析方法)
2. [網路封包分析方法](#2-網路封包分析方法)
3. [主動探測方法](#3-主動探測方法)
4. [靜態配置分析方法](#4-靜態配置分析方法)
5. [實際案例](#5-實際案例)

---

## 1. DHCP 資料庫分析方法

### 1.1 DHCP Option 60 (Vendor Class Identifier)

**原理**: Switch 在請求 DHCP 時會發送 Option 60，包含廠商資訊

**檢查方式**:
```sql
SELECT ip_address, mac_address, hostname, vendor_class
FROM api_dhcplease
WHERE vendor_class ~* 'cisco|switch|catalyst|procurve|aruba|juniper';
```

**典型的 Switch VCI 範例**:
- `Cisco Systems, Inc. IP Phone 7960` ❌ (IP Phone)
- `Cisco IOS Software, Catalyst 2960` ✅ (Catalyst Switch)
- `HP ProCurve Switch 2650` ✅ (HP Switch)
- `Aruba Instant On 1830` ✅ (Aruba Switch)
- `Juniper Networks EX Series` ✅ (Juniper Switch)

**優點**: 最準確的方法（廠商主動告知設備型號）  
**缺點**: 並非所有 Switch 都會發送 Option 60

---

### 1.2 DHCP Option 12 (Hostname) 關鍵字分析

**原理**: Switch 的主機名稱通常包含特定關鍵字

**檢查方式**:
```sql
SELECT ip_address, mac_address, hostname
FROM api_dhcplease
WHERE hostname ~* 'switch|sw-|sw_|catalyst|2960|3750|3850|procurve|access-|core-|distribution-';
```

**典型的 Switch Hostname 範例**:
- ✅ `switch-floor1`
- ✅ `sw-01`, `sw-core`, `sw_office`
- ✅ `catalyst-2960-a1`
- ✅ `access-sw-lobby`
- ✅ `core-switch-dc1`
- ✅ `distribution-sw-02`
- ❌ `pc-switch-user` (可能是使用者電腦，誤判)

**優點**: 簡單易懂，命名規範的網路容易識別  
**缺點**: 依賴命名規範，可能有誤判

---

### 1.3 MAC Address OUI (Organization Unique Identifier) 分析

**原理**: Switch 製造商的 MAC 地址前綴（OUI）具有特徵性

**Cisco Switch 常見 OUI**:
```
d0:85:43  ← 從 Wireshark 發現的 Switch
00:1e:bd, 00:1e:be, 00:1e:f6, 00:1e:f7
00:21:1b, 00:21:1c, 00:22:0c, 00:22:0d
b8:be:bf, c0:25:5c, e0:5f:b9, f0:29:29
```

**HP/Aruba Switch 常見 OUI**:
```
9c:8c:d8, d4:85:64
00:15:60, 00:17:a4, 00:1f:29
```

**檢查方式**:
```sql
SELECT ip_address, mac_address, hostname
FROM api_dhcplease
WHERE SUBSTRING(mac_address, 1, 8) IN (
    'd0:85:43', '00:1e:bd', '00:1e:be',
    '9c:8c:d8', 'd4:85:64'
);
```

**優點**: 不依賴配置，基於硬體特徵  
**缺點**: 需要維護 OUI 資料庫，新型號可能遺漏

**本專案已內建**: `device_type_detector.py` 包含 750+ 網路設備 OUI

---

### 1.4 DHCP Option 77 (User Class) 分析

**原理**: 部分設備會發送 Option 77 標示設備類別

**檢查方式**:
```sql
SELECT ip_address, mac_address, user_class
FROM api_dhcplease
WHERE user_class IS NOT NULL;
```

**優點**: 明確的設備類別資訊  
**缺點**: 很少設備支援此 Option

---

## 2. 網路封包分析方法

### 2.1 Wireshark 封包捕獲分析

**適用場景**: **Switch 使用靜態 IP，不在 DHCP Lease 中**

**方法**:
```bash
# 1. 捕獲網路封包
sudo tcpdump -i eth0 -w capture.pcap -c 1000

# 2. 使用 tshark 分析
tshark -r capture.pcap -T fields -e eth.src -e ip.src | sort | uniq -c

# 3. 查找 Gateway MAC（出現次數最多的 MAC）
```

**識別特徵**:
- ✅ MAC 地址出現在大量封包中（作為 Gateway）
- ✅ 同時作為 Source 和 Destination（轉發流量）
- ✅ 參與 ARP 回應（代理其他設備）

**實際案例** (本專案):
```
Frame 1: Ethernet II, Dst: Cisco_4c:1b:df (d0:85:43:4c:1b:df)
Frame 2: Ethernet II, Src: Cisco_4c:1b:df (d0:85:43:4c:1b:df)
→ 結論: d0:85:43:4c:1b:df 是 Cisco Switch
```

**優點**: 可發現靜態 IP 設備  
**缺點**: 需要網路封包捕獲權限

---

### 2.2 ARP Table 分析

**原理**: 分析 ARP 表，尋找 Gateway 或經常出現的 MAC

**方法**:
```bash
# 檢查本機 ARP 表
arp -a

# 或從路由器/防火牆匯出 ARP 表
ssh router "show arp"
```

**識別特徵**:
- Gateway IP 對應的 MAC 通常是 Switch/Router
- 多個 IP 對應同一個 MAC（VLAN 配置）

---

### 2.3 LLDP/CDP 協定分析

**原理**: Switch 會發送 LLDP (Link Layer Discovery Protocol) 或 CDP (Cisco Discovery Protocol) 廣播

**方法**:
```bash
# 使用 tcpdump 捕獲 LLDP
sudo tcpdump -i eth0 ether proto 0x88cc -vv

# 使用 tcpdump 捕獲 CDP
sudo tcpdump -i eth0 ether dst 01:00:0c:cc:cc:cc -vv
```

**識別特徵**:
- LLDP/CDP 封包包含設備名稱、型號、能力
- 只有網路設備會發送這些協定

**優點**: 最權威的識別方法（設備主動宣告）  
**缺點**: 需要 LLDP/CDP 啟用（部分環境會關閉）

---

## 3. 主動探測方法

### 3.1 SNMP 掃描

**原理**: Switch 通常啟用 SNMP，可查詢設備資訊

**方法**:
```bash
# 掃描 SNMP Community
nmap -sU -p 161 --script snmp-sysdescr 192.168.1.0/24

# 查詢 sysDescr OID
snmpget -v2c -c public 192.168.1.1 1.3.6.1.2.1.1.1.0
```

**識別特徵**:
- sysDescr 包含 "Switch", "Cisco IOS", "ProCurve"
- sysObjectID 對應 Switch 型號

**優點**: 可獲取詳細設備資訊  
**缺點**: 需要 SNMP Community String（安全性考量）

---

### 3.2 端口掃描（Service Fingerprinting）

**原理**: Switch 通常開放特定管理端口

**方法**:
```bash
# Nmap 服務識別
nmap -sV -p 22,23,80,443 192.168.1.0/24

# 識別 Switch 管理介面
curl -s http://192.168.1.1 | grep -i "switch\|cisco\|hp\|aruba"
```

**常見 Switch 管理端口**:
- 22 (SSH)
- 23 (Telnet)
- 80/443 (Web 管理介面)
- 161/162 (SNMP)

**識別特徵**:
- HTTP Title 包含 "Switch Configuration"
- SSH Banner 顯示 "Cisco IOS Software"
- Web 介面顯示交換器管理頁面

---

### 3.3 TTL (Time To Live) 分析

**原理**: 不同設備的預設 TTL 值不同

**方法**:
```bash
# Ping 並查看 TTL
ping -c 1 192.168.1.1 | grep ttl

# 批量檢查
for i in {1..254}; do 
    ping -c 1 -W 1 192.168.1.$i | grep ttl
done
```

**典型 TTL 值**:
- Cisco IOS: TTL=255
- Linux: TTL=64
- Windows: TTL=128

**優點**: 非侵入式  
**缺點**: 準確度較低（僅供參考）

---

## 4. 靜態配置分析方法

### 4.1 檢查 DHCP Server 排除清單

**原理**: Switch 通常配置靜態 IP，會在 DHCP Scope 排除清單中

**Windows DHCP Server**:
```powershell
Get-DhcpServerv4Scope | Get-DhcpServerv4ExclusionRange
```

**結果範例**:
```
Scope ID: 192.168.1.0
Exclusion Range: 192.168.1.1 - 192.168.1.10  ← 通常是 Gateway/Switch
```

---

### 4.2 檢查 DNS 反向解析（PTR 記錄）

**方法**:
```bash
# 反查 IP 的 PTR 記錄
nslookup 192.168.1.1

# 批量反查
for i in {1..10}; do 
    nslookup 192.168.1.$i | grep "name ="
done
```

**識別特徵**:
- PTR 記錄包含 "switch", "sw-", "router", "gw"

---

### 4.3 分析網路文檔/IP 規劃表

**檢查項目**:
- 網路規劃文檔（Network Design Document）
- IP 地址分配表（IP Address Management Spreadsheet）
- Visio 網路拓撲圖

**優點**: 最直接的方法  
**缺點**: 文檔可能過時或不存在

---

## 5. 實際案例

### 案例 1: 從 DHCP Lease 發現 Switch（成功）

**環境**: 企業網路，使用 Cisco Catalyst 系列

**方法**: DHCP Option 60 分析

**結果**:
```sql
SELECT * FROM api_dhcplease 
WHERE vendor_class ~* 'catalyst';

IP: 192.168.1.50  MAC: 00:1e:bd:4a:1b:2c  VCI: "Cisco IOS, Catalyst 2960-X"
```

**結論**: ✅ 成功識別（Switch 啟用 DHCP Client）

---

### 案例 2: 從 Wireshark 發現 Switch（本專案）

**環境**: Switch 使用靜態 IP，不在 DHCP Lease 中

**方法**: Wireshark 封包分析

**結果**:
```
Frame 1-200: 所有封包都經過 Cisco_4c:1b:df (d0:85:43:4c:1b:df)
```

**結論**: ✅ 成功識別（透過封包捕獲）

**補救**: 將 `d0:85:43` 加入 `device_type_detector.py` OUI 資料庫

---

### 案例 3: 從 Hostname 識別 Switch（成功）

**環境**: 有命名規範的網路

**方法**: DHCP Option 12 分析

**結果**:
```sql
SELECT * FROM api_dhcplease 
WHERE hostname ~* '^sw-';

IP: 192.168.1.10  MAC: d4:85:64:3a:2b:1c  Hostname: "sw-floor1"
IP: 192.168.1.11  MAC: 9c:8c:d8:5f:3e:4d  Hostname: "sw-core-01"
```

**結論**: ✅ 成功識別（依賴命名規範）

---

### 案例 4: 從 LLDP 協定發現 Switch（最可靠）

**環境**: 啟用 LLDP 的企業網路

**方法**: tcpdump 捕獲 LLDP

**結果**:
```bash
$ sudo tcpdump -i eth0 ether proto 0x88cc -vv

Chassis ID: 00:1e:bd:4a:1b:2c
System Name: Catalyst-2960-Switch-01
System Description: Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 15.0(2)SE11
Port ID: GigabitEthernet0/1
```

**結論**: ✅ 最權威的識別方法（設備主動宣告詳細資訊）

---

## 🎯 總結：推薦的識別策略

### 優先順序（從高到低）

1. **LLDP/CDP 協定** ✅✅✅
   - 最可靠、最詳細
   - 需要網路設備啟用

2. **DHCP Option 60 (VCI)** ✅✅
   - 準確度高
   - 需要設備支援

3. **Hostname 關鍵字** ✅
   - 簡單易懂
   - 依賴命名規範

4. **MAC OUI 資料庫** ✅
   - 不依賴配置
   - 需要維護資料庫

5. **Wireshark 封包分析** ✅
   - 可發現靜態 IP 設備
   - 需要封包捕獲權限

6. **SNMP 掃描** ⚠️
   - 詳細資訊
   - 安全性考量

### 本專案已實現

- ✅ MAC OUI 資料庫（750+ 網路設備）
- ✅ Hostname 關鍵字分析
- ✅ DHCP Option 60 支援（數據庫欄位）
- ✅ Wireshark 分析案例（發現 d0:85:43 Cisco Switch）

### 未來可擴展

- ⏳ LLDP/CDP 自動探測
- ⏳ SNMP 掃描整合
- ⏳ 定期網路掃描任務（Scheduled Task）
- ⏳ 網路拓撲自動繪製

---

**文檔版本**: 1.0  
**更新日期**: 2025-10-28  
**作者**: Network Toolbox Team
