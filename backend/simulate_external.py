import os
import requests
from dotenv import load_dotenv

# 載入 .env 檔案以獲取 EXTERNAL_API_KEY
load_dotenv('config.env')
API_KEY = os.getenv('EXTERNAL_API_KEY')

if not API_KEY:
    print("❌ 錯誤: 請確保 config.env 中已設定 EXTERNAL_API_KEY")
    exit()

# 後端 API 的本地網址
URL = "http://127.0.0.1:5000/api/external/site_update"

# 模擬外部警報系統發送的 JSON 數據 (破壞 1F-B 設施)
payload = {
    "siteID": "1F-B",       # 你在 sites.json 中設定的某個設施 (確保裡面有收容 SCP)
    "door_status": True,    # 門禁強制開啟
    "structure": "Broken"   # 牆壁結構被破壞
}

# 將 API Key 放入請求的 Header 中
headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

print(f"🚀 正在模擬外部系統發送收容失效警報至 {URL}...")
print(f"📦 夾帶金鑰: {API_KEY[:4]}... (部分隱藏)")

try:
    # 發送 POST 請求
    response = requests.post(URL, json=payload, headers=headers)
    
    print("\n📡 伺服器回應:")
    print(f"狀態碼: {response.status_code}")
    print(f"回傳內容: {response.json()}")

except requests.exceptions.RequestException as e:
    print(f"\n❌ 連線失敗: {e}")