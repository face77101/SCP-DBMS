import os                    # 【作業系統橋樑】讓你能夠存取電腦內部的環境變數 (Environment Variables)。
import json                  # 【資料結構翻譯官】用來讀取與解析你的 JSON 格式種子資料 (seed data)。
import bcrypt                # 【特工密碼鎖】這是專案的安全核心，負責將明文密碼進行高強度的加鹽雜湊處理。
import pymysql              # 【資料庫管道】Python 與 MySQL 資料庫之間的翻譯官，負責傳送 SQL 指令並接收回傳值。
from dotenv import load_dotenv # 【隱形斗篷】負責將 .env 檔案內的敏感設定（如密碼）安全地載入系統環境中。

# 載入環境變數
load_dotenv()

# 1. 配置資料庫連線
db = pymysql.connect(
    host=os.getenv('SERVERNAME'),
    user=os.getenv('USERNAME'),
    password=os.getenv('PASSWORD'),
    database=os.getenv('DBNAME')
)
cursor = db.cursor()

# 2. 定義資料表與對應的 JSON 檔名（順序依據外鍵依賴關係排列）
# 這裡注意：你的第一個成員 JSON 檔名叫成員列表，所以我們直接用 'members.example.json'
tables = [
    ('Member', 'members.example.json'), 
    ('SCP', 'scps.json'),
    ('Site', 'sites.json'),
    ('Report', 'reports.json'),
    ('Mission', 'missions.json'),
    ('research_leader', 'research_leader.json'),
    ('contained_in', 'contained_in.json')
]

# 取得這個腳本 (init_db.py) 所在的絕對路徑目錄（即 /app）
base_dir = os.path.dirname(os.path.abspath(__file__))

# 3. 處理與寫入
for table_name, file_name in tables:
    # 使用 os.path.join 確保路徑不管在本地或容器內都絕對精準
    # 這裡的尋路邏輯：/app/database/seed_data/某個檔案.json
    json_path = os.path.join(base_dir, 'database', 'seed_data', file_name)
    
    # 檢查檔案到底存不存在，不存在就先跳過，避免程式整支壞掉
    if not os.path.exists(json_path):
        print(f"⚠️ 找不到種子檔案：{json_path}，跳過此表格。")
        continue

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for row in data:
        # 如果是 Member 表，且裡面有明文密碼，就執行雜湊
        if table_name == 'Member' and 'password_plain' in row:
            row['password_hash'] = bcrypt.hashpw(row.pop('password_plain').encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 動態生成 SQL
        keys = ", ".join(row.keys()) 
        placeholders = ", ".join(["%s"] * len(row)) 
        updates = ", ".join([f"{k} = VALUES({k})" for k in row.keys()]) 
        
        sql = f"INSERT INTO {table_name} ({keys}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"
        cursor.execute(sql, tuple(row.values()))
    
    print(f"✅ 資料表 {table_name} 處理完畢。")

db.commit()
cursor.close()
db.close()
print("🎉 所有資料表初始化完成！")