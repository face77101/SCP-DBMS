import os
import json
import bcrypt
import pymysql
from dotenv import load_dotenv

load_dotenv()

# 1. 配置資料庫連線
db = pymysql.connect(
    host=os.getenv('SERVERNAME'),
    user=os.getenv('USERNAME'),
    password=os.getenv('PASSWORD'),
    database=os.getenv('DBNAME')
)
cursor = db.cursor()

# 2. 定義資料表與對應的 JSON 檔名
tables = [
    ('Member', 'members.json'), 
    ('SCP', 'scps.json'),
    ('Site', 'sites.json'),
    ('Report', 'reports.json'),   
    ('Mission', 'missions.json'),
    ('involved_mem', 'involved_mem.json'), 
    ('contained_in', 'contained_in.json')
]

base_dir = os.path.dirname(os.path.abspath(__file__))

# 3. 處理與寫入
for table_name, file_name in tables:
    json_path = os.path.join(base_dir, 'database', 'seed_data', file_name)
    
    if not os.path.exists(json_path):
        print(f"⚠️ 找不到種子檔案：{json_path}，跳過此表格。")
        continue

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    is_json_updated = False  # 💡 用來標記此 JSON 檔案是否需要被重新覆寫儲存
        
    try:
        for row in data:
            # 1. 處理成員密碼加密
            if table_name == 'Member' and 'password_plain' in row:
                plain = row.pop('password_plain')
                row['password_hash'] = bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # 2. 動態建構語法
            keys = ", ".join(row.keys()) 
            placeholders = ", ".join(["%s"] * len(row)) 
            updates = ", ".join([f"{k} = VALUES({k})" for k in row.keys()])
            
            # 3. 執行注入
            if table_name == 'Member':
                sql = """
                    INSERT INTO Member (memID, dept_name, clearance_lv, permission, mem_status, password_hash) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    dept_name = VALUES(dept_name), clearance_lv = VALUES(clearance_lv),
                    permission = VALUES(permission), mem_status = VALUES(mem_status), password_hash = VALUES(password_hash)
                """
                cursor.execute(sql, (
                    row['memID'], row['dept_name'], row['clearance_lv'], 
                    row['permission'], row['mem_status'], row['password_hash']
                ))
            elif table_name == 'involved_mem':
                # 💡 面對有 Trigger 限制 leader 的關係表，用 INSERT IGNORE 最安全
                sql = f"INSERT IGNORE INTO involved_mem ({keys}) VALUES ({placeholders})"
                cursor.execute(sql, tuple(row.values()))
            else:
                sql = f"""
                    INSERT INTO {table_name} ({keys}) 
                    VALUES ({placeholders}) 
                    ON DUPLICATE KEY UPDATE {updates}
                """
                cursor.execute(sql, tuple(row.values()))

            # 💡 【核心修正位置】必須在 execute 執行完之後，才去抓 LAST_INSERT_ID()！
            if table_name == 'Report' and row.get('reportID') is None:
                cursor.execute("SELECT LAST_INSERT_ID()")
                result = cursor.fetchone()
                if result and result[0] > 0: 
                    new_id = result[0]
                    row['reportID'] = new_id  # 寫回 Python 的記憶體物件中
                    is_json_updated = True    # 開啟回寫開關
        
        # 固化當前資料表
        db.commit()
        print(f"✅ 資料表 {table_name} 資料群已成功固化至 MySQL (已 Commit)。")

        # 💡 【核心回寫邏輯】如果這張表的資料有長出新 ID，將整張 data 回寫存進 JSON 檔
        if is_json_updated:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 系統已自動將最新產生的主鍵儲存至：{file_name}")

    except Exception as e:
        db.rollback()
        print(f"❌ 資料表 {table_name} 注入失敗，已回滾該表。錯誤原因: {e}")

cursor.close()
db.close()
print("🏁 腳本執行完畢！")