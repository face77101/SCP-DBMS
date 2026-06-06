import os
import json
import bcrypt
import pymysql
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# 從環境變數動態抓取金鑰保護 Session
app.secret_key = os.getenv('EXTERNAL_API_KEY', os.urandom(24).hex())

# 載入環境變數（隱形斗篷）
load_dotenv()

app = Flask(__name__,static_folder='../frontend',      #讓 Flask 找不到路由時去這裡找 CSS/JS 
            static_url_path='')
CORS(app)  # 啟用 CORS，允許前端跨域請求

# 讓根目錄直接回傳 index.html 登入畫面
@app.route('/')
def index():
    return app.send_static_file('index.html')

# 讓 /dashboard.html 指向主控制台
@app.route('/dashboard.html')
def dashboard():
    return app.send_static_file('dashboard.html')

# 建立資料庫連線的 Helper Function（確保每次請求都能穩定連線）
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('SERVERNAME'),
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        database=os.getenv('DBNAME'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor  # 讓撈出來的資料自動變 Dict，如：user['clearance_lv']
    )

# ==========================================
# 【核心驗證 API】/api/login
# ==========================================
@app.route('/api/login', methods=['POST'])
def login():
    # 解析前端傳來的 JSON 資料
    data = request.get_json()
    username = data.get('username')
    password_plain = data.get('password').strip()

    # 防禦性程式設計：檢查欄位
    if not username or not password_plain:
        return jsonify({"message": "欄位不可為空"}), 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 依據用戶名搜尋該成員的雜湊密碼與權限等級
            sql = "SELECT memID, password_hash, clearance_lv FROM Member WHERE memID = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

        # 邏輯判斷 1：使用者是否存在？
        if not user:
            return jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"}), 401

        # 邏輯判斷 2：利用 Bcrypt 比對明文密碼與資料庫中的雜湊值
        # Bcrypt 要求傳入 bytes 型態，因此必須加上 .encode('utf-8')
        # 在 is_valid = bcrypt.checkpw(...) 的正上方加上：
        debug_salt = bcrypt.gensalt()
        debug_hash = bcrypt.hashpw("12345678".encode('utf-8'), debug_salt)
        debug_verify = bcrypt.checkpw("12345678".encode('utf-8'), debug_hash)
        
        is_valid = bcrypt.checkpw(
            password_plain.encode('utf-8'), 
            user['password_hash'].encode('utf-8')
        )

        if is_valid:
            # 驗證成功，回傳權限等級與跳轉指令
            return jsonify({
                "message": "登入成功，歡迎回到站點",
                "clearance_lv": user['clearance_lv'],
                "redirect": "dashboard.html"
            }), 200
        else:
            # 密碼錯誤，回傳與帳號不存在相同的模糊訊息（防止帳號列舉攻擊）
            return jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"}), 401

    except Exception as e:
        # 直接把底層的錯誤字串 (str(e)) 塞進 message 傳回前端
        return jsonify({
            "message": f"【資料庫/後端崩潰原因】: {str(e)}"
        }), 500
    finally:
        connection.close() # 務必關閉連線，釋放資源
========================================
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

# ==========================================
# 工作 3-3 實作：API - 「SCP 字典基本資料搜尋」(黃家福)
# ==========================================
@app.route('/api/scp/search', methods=['GET'])
def search_scp():
    # session['memID'] = 'O5000001O5'
    # session['memID'] = 'RD0000114C'
    current_mem_id = session.get('memID')
    
    # 預設安保等級為 0 (最低)
    user_clearance = 0 
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 取得當前使用者的安保等級
            if current_mem_id:
                cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
                user = cursor.fetchone()
                if user:
                    user_clearance = int(user['clearance_lv'])

            # 2. 允許前端傳遞查詢參數 (例如 ?scpID=SCP-001)
            search_id = request.args.get('scpID')
            
            if search_id:
                cursor.execute("SELECT * FROM SCP WHERE scpID = %s", (search_id,))
                scps = cursor.fetchall()
            else:
                cursor.execute("SELECT * FROM SCP")
                scps = cursor.fetchall()

            # 3. 動態情報遮蔽邏輯 (Dynamic Redaction)
            for scp in scps:
                scp_req_lv = int(scp['clearance_lv'])
                
                # 若特工等級低於 SCP 要求等級，將敏感欄位抹除
                if user_clearance < scp_req_lv:
                    scp['appearance'] = "[REDACTED]"
                    scp['abilities']  = "[REDACTED]"
                    scp['weakness']   = "[REDACTED]"
                    scp['others']     = "[REDACTED]"
            
            response = jsonify(scps)
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response, 200

    except pymysql.MySQLError as e:
        return jsonify({"status": "error", "message": f"資料庫查詢失敗：{str(e)}"}), 500
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()


# ==========================================
# 工作 3-3 實作：API - 「O5 專屬研究報告檢索」(黃家福)
# ==========================================
@app.route('/api/admin/reports', methods=['GET'])
def search_reports():
    # session['memID'] = 'O5000001O5'
    current_mem_id = session.get('memID')
    
    if not current_mem_id:
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 驗證 O5 權限 (等級必須為 3)
            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            
            if not user or int(user['clearance_lv']) < 3:
                return jsonify({"status": "error", "message": "403 Forbidden：此操作僅限 O5 議會成員"}), 403
            
            # 撈取所有報告
            cursor.execute("SELECT * FROM Report ORDER BY reportID DESC")
            reports = cursor.fetchall()
            
            return jsonify(reports), 200

    except pymysql.MySQLError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()


# ==========================================
# 工作 3-3 實作：API - 「O5 審查並統整至 SCP 字典」(黃家福)
# ==========================================
@app.route('/api/O5/approve', methods=['POST', 'OPTIONS'])
def approve_report():
    # 處理 CORS 預檢請求
    if request.method == 'OPTIONS':
        response = jsonify({"status": "success"})
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 200

    current_mem_id = session.get('memID')
    
    if not current_mem_id:
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入"}), 401

    data = request.get_json()
    report_id = data.get('reportID')

    if not report_id:
        return jsonify({"status": "error", "message": "缺少 reportID"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 驗證 O5 權限
            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            
            if not user or int(user['clearance_lv']) < 3:
                return jsonify({"status": "error", "message": "403 Forbidden：此操作僅限 O5 議會成員"}), 403

            # 2. 抓取報告的精華情報
            cursor.execute("SELECT appearance, abilities, weakness, others, scpID FROM Report WHERE reportID = %s", (report_id,))
            report = cursor.fetchone()

            if not report:
                return jsonify({"status": "error", "message": "找不到該研究報告"}), 404

            # 3. 執行 DML：將報告情報覆蓋/更新回官方 SCP 字典表中
            update_sql = """
                UPDATE SCP 
                SET appearance = %s, abilities = %s, weakness = %s, others = %s
                WHERE scpID = %s
            """
            cursor.execute(update_sql, (
                report['appearance'], 
                report['abilities'], 
                report['weakness'], 
                report['others'], 
                report['scpID']
            ))
            
            conn.commit()

            response = jsonify({
                "status": "success", 
                "message": f"SCP 檔案更新成功！情報已整併至 {report['scpID']}。"
            })
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response, 200

    except pymysql.MySQLError as e:
        if 'conn' in locals():
            conn.rollback()
        return jsonify({"status": "error", "message": f"資料庫更新失敗：{str(e)}"}), 500
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) #每次你改 Code，後端就會自動同步，不用手動重啟 Docker！