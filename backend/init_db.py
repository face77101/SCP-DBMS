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
        
    for row in data:
        # 1. 處理成員密碼加密
        if table_name == 'Member' and 'password_plain' in row:
            plain = row.pop('password_plain')
            row['password_hash'] = bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 2. 【安全革命】動態建構語法，絕對不把 row 的數值用 '{v}' 拼進 SQL 字串中！
        keys = ", ".join(row.keys()) 
        placeholders = ", ".join(["%s"] * len(row)) 
        
        # 💡 全部統一改用資料庫原生的 VALUES(欄位名)，安全不破裂
        updates = ", ".join([f"{k} = VALUES({k})" for k in row.keys()])
        
        # 3. 執行分流注入
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
        else:
            # 其餘 6 張表使用標準參數化管道，這能確保任何 JSON 裡的引號或換行都不會造成 SQL 錯位
            sql = f"""
                INSERT INTO {table_name} ({keys}) 
                VALUES ({placeholders}) 
                ON DUPLICATE KEY UPDATE {updates}
            """
            cursor.execute(sql, tuple(row.values()))
    
    print(f"✅ 資料表 {table_name} 資料群已成功固化至 MySQL。")

db.commit()
cursor.close()
db.close()
print("🎉 所有資料表初始化完成！")