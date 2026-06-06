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
    ('Member', 'members.json'), 
    ('SCP', 'scps.json'),
    ('Site', 'sites.json'),
    ('Report', 'reports.json'),
    ('Mission', 'missions.json'),
    ('involved_mem', 'involved_mem.json'),
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
        # 1. 確保雜湊處理
        if table_name == 'Member' and 'password_plain' in row:
            plain = row.pop('password_plain')
            # 👈 加上這兩行顯微紀錄器，看清楚從 JSON 讀出來的到底是什麼鬼魅
            print(f"🕵️ 正在幫 {row['memID']} 鑄造密碼鎖...", flush=True)
            print(f"   ↳ JSON 讀出的明文字串: [{plain}] (字數長度: {len(str(plain))})", flush=True)
            row['password_hash'] = bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 2. 建立標準的佔位符
        keys = ", ".join(row.keys()) 
        placeholders = ", ".join(["%s"] * len(row)) 
        
        # 3. 核心修正：安全且明確地指派更新值，避免 VALUES() 函數造成的快取錯亂
        # 改用傳統的 col = %s 或是利用別名，這裡用明確的動態字串：
        updates = ", ".join([f"{k} = '{v}'" if k == 'password_hash' else f"{k} = VALUES({k})" for k, v in row.items()])
        
        # 為了絕對安全，如果是 Member 表，我們甚至可以直接這樣寫：
        if table_name == 'Member':
            # 1. 徹底消滅 SQL 內部的 '{row[...]}' 拼接，改用標準的 VALUES(password_hash)
            sql = """
                INSERT INTO Member (memID, dept_name, clearance_lv, permission, mem_status, password_hash) 
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                dept_name = VALUES(dept_name),
                clearance_lv = VALUES(clearance_lv),
                permission = VALUES(permission),
                mem_status = VALUES(mem_status),
                password_hash = VALUES(password_hash)
            """
            # 2. 所有資料一律透過安全管道 (Tuple) 餵給 MySQL 驅動，確保特殊符號不被解譯
            cursor.execute(sql, (
                row['memID'], 
                row['dept_name'], 
                row['clearance_lv'], 
                row['permission'], 
                row['mem_status'], 
                row['password_hash']
            ))
    
    print(f"✅ 資料表 {table_name} 處理完畢。")

db.commit()
cursor.close()
db.close()
print("🎉 所有資料表初始化完成！")