import os
import socket
import sys

def diagnose():
    print("=" * 50)
    print("【基金會安全伺服器 - 網路自我診斷開始】")
    print("=" * 50)

    # 1. 檢查環境變數是否正確載入
    db_host = os.environ.get("DB_HOST") or os.environ.get("SERVERNAME")  # 根據你 env 的 key 調整
    db_port = int(os.environ.get("DB_PORT", 3306))
    
    print(f"[*] 讀取到環境變數中的學校資料庫 IP: {db_host}")
    print(f"[*] 讀取到環境變數中的資料庫 Port: {db_port}")
    
    if not db_host:
        print("[X] 錯誤：找不到資料庫 IP 設定，請檢查 config.env 是否有正確餵給容器。")
        return

    # 2. 測試容器是否能用 TCP 連上學校 IP (斷點 A)
    print(f"\n[1/2] 正在測試 容器 -> 學校資料庫 ({db_host}:{db_port}) 的物理連線...")
    try:
        # 設定 5 秒超時
        sock = socket.create_connection((db_host, db_port), timeout=5)
        sock.close()
        print("[O] 成功！Docker 容器內部可以透過網路觸及學校資料庫。")
    except socket.timeout:
        print("[X] 失敗：連線超時 (Timeout)！")
        print("    -> 兇手機率最大：你的實體電腦有開學校 VPN，但 Docker 容器沒有共享到這個 VPN 路由。")
        return
    except Exception as e:
        print(f"[X] 失敗：連線被拒絕或無法解析。錯誤訊息: {e}")
        print("    -> 可能是學校防火牆不允許這個 Docker 網路橋接器的內部 IP 進入。")
        return

    # 3. 如果物理連線通了，暗示可能是 Python 代碼裡的驅動或認證問題 (斷點 B)
    print("\n[2/2] 物理連線正常。請嘗試檢查 Python 後端日誌 (docker compose logs backend)。")
    print("    -> 如果前端仍顯示無法連線，代表是【你的瀏覽器 -> 後端 5000 Port】被阻擋 (例如 CORS 問題)。")

if __name__ == "__main__":
    diagnose()