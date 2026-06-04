from flask import Flask, request, jsonify, session
from datetime import datetime
import os
import pymysql
from dotenv import load_dotenv

# 自動載入上層目錄的 config.env 檔案
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '..', 'config.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
# 從環境變數動態抓取金鑰保護 Session
app.secret_key = os.getenv('EXTERNAL_API_KEY', os.urandom(24).hex())

# ==========================================
# 資料庫連線設定：100% 從環境變數動態撈取
# ==========================================
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('SERVERNAME'),      # 讀取 env 中的伺服器 IP 或虛擬通道
        user=os.getenv('USERNAME'),        # 讀取 env 中的帳號
        password=os.getenv('PASSWORD'),    # 讀取 env 中的密碼 (拒絕明文)
        database=os.getenv('DBNAME'),      # 讀取 env 中的資料庫名稱
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# 測試首頁路由
@app.route('/')
def hello():
    return "SCP 基金會後端伺服器已上線。恭喜你測試成功。恭喜你測試成功！這玩意是臨時的~哈~^Ｏ^"

# ==========================================
# 工作 3-2 實作：API - 「研究報告上傳」
# ==========================================
@app.route('/api/reports/upload', methods=['POST', 'OPTIONS'])
def upload_report():
    # 🔌 1. 先處理瀏覽器的 CORS 預檢請求 (Preflight)
    if request.method == 'OPTIONS':
        response = jsonify({"status": "success"})
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 200
    
    #從登入成功的 Session 中抓取 memID，防止前端偽造身分
    #特工測試後門：手動把這位資深特工的 memID 塞進 Session！
    #session['memID'] = '成員代號' 

    current_mem_id = session.get('memID') 
    
    if not current_mem_id:
        response = jsonify({
            "status": "error",
            "message": "拒絕存取：尚未登入基金會系統，無法提交研究報告。"
        })
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 401

    # 後端自動生成精確時間作為 reportID，防止前端偽造時間
    auto_report_id = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        data = request.get_json()
        
        #report欄位
        title        = data.get('title')       # TITLE: [緊急]發現變異種
        scp_id       = data.get('scpID')       # SCPID: SCP-233
        abilities    = data.get('abilities')   # ABL.: 出現隔空崩解
        weakness     = data.get('weakness')    # WEAK.
        appearance   = data.get('appearance')  # APP.
        others       = data.get('others')      # OTHERS
        required_lv  = data.get('required_lv', '1')  # 預設查閱安保等級為 1

        # 🕵️‍♂️ 【新增擴充】接收前端傳過來的「其他涉及成員 ID 陣列」（例如：["RD0000010C", "MG0000020C"]）
        # 如果大整合前前端還沒刻這個欄位，這裡會拿到預設的空陣列 []，完全不影響原本上傳功能！
        involved_members = data.get('involved_members', [])

        # 基本必填欄位防呆驗證
        if not title or not scp_id:
            response = jsonify({
                "status": "error", 
                "message": "提交失敗：報告標題與涉及的 SCP 代號為必填項目。"
            })
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            return response, 400
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. 將報告核心內容寫入主表 Report
            sql_report = """
                INSERT INTO Report (reportID, required_lv, title, appearance, abilities, weakness, others, scpID)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_report, (
                auto_report_id, required_lv, title, 
                appearance, abilities, weakness, others, scp_id
            ))

            # 2. 同步寫入多對多關係表 involved_mem (自動綁定填表人為 leader)
            sql_relation = """
                INSERT INTO involved_mem (reportID, memID, role)
                VALUES (%s, %s, 'leader')
            """
            cursor.execute(sql_relation, (auto_report_id, current_mem_id))

            # 3. 遍歷涉及成員陣列，將所有共同參與特工寫入關係表，role 鎖定為 '涉及成員'
            for mem_id in involved_members:
                # 簡單的防呆：避免重複把填表人自己又塞進涉及成員裡
                if mem_id == current_mem_id:
                    continue
                    
                sql_member = """
                    INSERT INTO involved_mem (reportID, memID, role)
                    VALUES (%s, %s, 'involved_member')
                """
                cursor.execute(sql_member, (auto_report_id, mem_id))

            # 提交 Transaction，確保兩張表資料完整性
            conn.commit()

        response = jsonify({
            "status": "success",
            "message": "研究報告已成功提交，系統已自動生成 reportID 並記錄填表人與時間。"
        })
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 200

    except pymysql.MySQLError as e:
        print(f"發現錯誤 MySQL 噴錯細節：{e}")
        if 'conn' in locals():
            conn.rollback()  # 補上這行：出錯時撤銷前面所有寫入，確保資料完整性！

        response = jsonify({
            "status": "error",
            "message": f"資料庫寫入失敗：{str(e)}"
        })
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 500
    
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)#每次你改 Code，後端就會自動同步，不用手動重啟 Docker！
