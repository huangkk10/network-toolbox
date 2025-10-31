#!/usr/bin/env python3
"""
測試 IPXE SSH 連線並查看 Docker 容器日誌
"""
import paramiko
import sys

def test_ipxe_connection():
    """測試連線到 IPXE 伺服器並查看日誌"""
    
    # SSH 連線資訊
    host = "10.250.50.2"
    username = "rvt"
    password = "1.a"  # 您提供的密碼
    
    print(f"正在連線到 {host}...")
    
    try:
        # 建立 SSH 客戶端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 連線
        ssh.connect(
            hostname=host,
            username=username,
            password=password,
            timeout=10
        )
        
        print(f"✅ SSH 連線成功！\n")
        
        # 1. 列出所有 Docker 容器
        print("=" * 60)
        print("步驟 1: 列出所有 Docker 容器")
        print("=" * 60)
        
        stdin, stdout, stderr = ssh.exec_command("sudo -S docker ps -a", get_pty=True)
        stdin.write(password + "\n")
        stdin.flush()
        
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        print(output)
        if error and 'password' not in error.lower():
            print(f"錯誤: {error}")
        
        # 2. 查找 IPXE 相關的容器
        print("\n" + "=" * 60)
        print("步驟 2: 查找 IPXE 相關的容器名稱")
        print("=" * 60)
        
        stdin, stdout, stderr = ssh.exec_command("sudo -S docker ps --format '{{.Names}}'", get_pty=True)
        stdin.write(password + "\n")
        stdin.flush()
        
        all_output = stdout.read().decode('utf-8')
        # 過濾掉 sudo 提示和空行，只保留容器名稱
        ipxe_containers = [
            line.strip() 
            for line in all_output.split('\n') 
            if line.strip() and 'password' not in line.lower() and 'sudo' not in line.lower() and 'ipxe' in line.lower()
        ]
        print(f"找到的 IPXE 容器: {ipxe_containers}")
        
        # 3. 如果找不到，列出所有容器名稱
        if not ipxe_containers:
            print("\n未找到包含 'ipxe' 的容器，列出所有容器名稱：")
            stdin, stdout, stderr = ssh.exec_command("sudo -S docker ps --format '{{.Names}}'", get_pty=True)
            stdin.write(password + "\n")
            stdin.flush()
            
            all_output = stdout.read().decode('utf-8')
            all_containers = [
                line.strip() 
                for line in all_output.split('\n') 
                if line.strip() and 'password' not in line.lower() and 'sudo' not in line.lower()
            ]
            print("\n所有容器:")
            for i, container in enumerate(all_containers, 1):
                print(f"  {i}. {container}")
        
        # 4. 查看容器日誌（最近100行）
        if ipxe_containers:
            for container in ipxe_containers:
                print("\n" + "=" * 60)
                print(f"步驟 3: 查看容器 '{container}' 的最近 100 行日誌")
                print("=" * 60)
                
                stdin, stdout, stderr = ssh.exec_command(f"sudo -S docker logs --tail 100 {container}", get_pty=True)
                stdin.write(password + "\n")
                stdin.flush()
                
                logs = stdout.read().decode('utf-8')
                print(logs)
                
                # 5. 分析日誌格式
                print("\n" + "=" * 60)
                print("步驟 4: 分析日誌格式")
                print("=" * 60)
                
                log_lines = [line for line in logs.split('\n') if line.strip()]
                if log_lines:
                    print(f"\n總共 {len(log_lines)} 行日誌")
                    print(f"\n前 10 行範例:")
                    for i, line in enumerate(log_lines[:10], 1):
                        print(f"{i}. {line}")
                    
                    print(f"\n最後 5 行範例:")
                    for i, line in enumerate(log_lines[-5:], 1):
                        print(f"{i}. {line}")
        
        ssh.close()
        print("\n✅ 測試完成！")
        
    except paramiko.AuthenticationException:
        print(f"❌ 認證失敗：使用者名稱或密碼錯誤")
        return False
    except paramiko.SSHException as e:
        print(f"❌ SSH 連線錯誤：{e}")
        return False
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_ipxe_connection()
    sys.exit(0 if success else 1)
