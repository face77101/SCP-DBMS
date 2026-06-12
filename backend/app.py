import os
import json
import bcrypt
import pymysql
from datetime import datetime
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__,static_folder='../frontend',      #讓 Flask 找不到路由時去這裡找 CSS/JS 
            static_url_path='')

# =========================================================================
# 🔬 [DEBUG PROGRAM] 全域請求監聽器
# =========================================================================
@app.before_request
def debug_cookie_traffic():
    # 只監聽我們的 API 路徑
    if request.path.startswith('/api/'):
        print("\n" + "📡 " + "="*70)
        print(f"【流量診斷】收到請求: {request.method} -> {request.path}")
        print(f"[*] 瀏覽器送過來的原始 Cookie 字串: {request.headers.get('Cookie')}")
        print(f"[*] Flask 解析後的 Cookies 字典: {dict(request.cookies)}")
        print(f"[*] 目前伺服器記憶體中的 Session 內容: {dict(session)}")
        print(f"[*] 是否持有有效特工身分 (memID): {session.get('memID')}")
        print("="*75 + "\n")

# 從環境變數動態抓取金鑰保護 Session
app.secret_key = os.getenv('EXTERNAL_API_KEY', os.urandom(24).hex())

# =========================================================================
# ✅ 【核心修正】強行打通跨網域（CORS）下的 Session Cookie 傳遞
# =========================================================================
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',  # 允許跨網域傳輸 Cookie
    SESSION_COOKIE_SECURE=False,     # localhost 環境下允許不使用 HTTPS 傳輸
    SESSION_REFRESH_EACH_REQUEST=True
)

# 載入環境變數（隱形斗篷）
load_dotenv()

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
# =========================================================================
# 🔬 [DEBUG LOGIN] 全斷點雷達追蹤版 API
# =========================================================================
@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    print("\n🔑 " + "="*60)
    print("【雷達追蹤】收到 /api/login 請求！")
    print(f"[*] 請求 Method: {request.method}")
    print(f"[*] 請求 Headers:\n{request.headers}")
    print(f"[*] 請求夾帶的原始 Cookies: {request.cookies}")

    # 斷點 1：處理 OPTIONS 預檢
    if request.method == 'OPTIONS':
        print("[📍 斷點 1] 正在響應瀏覽器的 OPTIONS 預檢...")
        response = jsonify({"status": "success"})
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        print("="*60 + "\n")
        return response, 200

    try:
        # 斷點 2：解析 JSON
        data = request.get_json()
        print(f"[📍 斷點 2] 成功解析前端傳來的 JSON 數據: {data}")
        
        username = data.get('username') if data else None
        password_plain = data.get('password').strip() if data and data.get('password') else ""

        if not username or not password_plain:
            print("[X] 攔截：前端傳入的帳號或密碼為空值！")
            response = jsonify({"message": "欄位不可為空"})
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            return response, 400

        # 斷點 3：向學校資料庫要人
        print(f"[📍 斷點 3] 正在向學校 MySQL 查詢特工代號: {username} ...")
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT memID, password_hash, clearance_lv FROM Member WHERE memID = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()
        
        print(f"[*] 資料庫回傳原始紀錄: {user}")

        if not user:
            print("[X] 驗證失敗：資料庫裡根本沒有這個 memID！")
            response = jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"})
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            return response, 401

        # 斷點 4：Bcrypt 密碼大驗兵
        print(f"[📍 斷點 4] 開始進行 Bcrypt 雜湊密碼比對...")
        print(f"    -> 明文密碼長度: {len(password_plain)}")
        print(f"    -> 資料庫雜湊值: {user.get('password_hash')}")
        
        is_valid = bcrypt.checkpw(
            password_plain.encode('utf-8'), 
            user['password_hash'].encode('utf-8')
        )
        print(f"[*] Bcrypt 比對最終結果 (is_valid): {is_valid}")

        if is_valid:
            # 斷點 5：寫入 Session
            session['memID'] = user['memID'] 
            print(f"[📍 斷點 5] 密碼正確！已成功將 memID={session['memID']} 寫入 Flask Session 記憶體。")

            response = jsonify({
                "message": "登入成功，歡迎回到站點",
                "clearance_lv": user['clearance_lv'],
                "redirect": "dashboard.html"
            })
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            print("🎉 【登入流程完美通關】成功發送 Set-Cookie 響應！")
            print("="*60 + "\n")
            return response, 200
        else:
            print("[X] 驗證失敗：密碼錯誤（與資料庫雜湊值對不起來）")
            response = jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"})
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            return response, 401

    except Exception as e:
        print(f"[🔥 崩潰] 登入 API 內部發生非預期嚴重錯誤！")
        import traceback
        traceback.print_exc() # 印出最詳細的報錯行數
        response = jsonify({"message": f"【後端崩潰原因】: {str(e)}"})
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        return response, 500
    finally:
        if 'connection' in locals():
            connection.close()
# ========================================
# 工作 3-2 實作：API - 「研究報告上傳」
# ==========================================
@app.route('/api/reports/upload', methods=['POST', 'OPTIONS'])
def upload_report():
    print("\n📝 " + "="*60)
    print("【雷達追蹤】收到 /api/reports/upload 報告提交請求！")
    print(f"[*] 請求 Method: {request.method}")
    print(f"[*] 請求 Headers:\n{request.headers}")
    print(f"[*] 請求夾帶的原始 Cookies: {request.cookies}")
    print(f"[*] 伺服器記憶體中的 Session 內容: {dict(session)}")

    # 🔌 1. 先處理瀏覽器的 CORS 預檢請求 (Preflight)
    if request.method == 'OPTIONS':
        print("[📍 斷點 1] 正在響應瀏覽器的 OPTIONS 預檢...")
        response = jsonify({"status": "success"})
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        print("="*60 + "\n")
        return response, 200
    
    # 2. 檢查特工身分
    current_mem_id = session.get('memID') 
    print(f"[📍 斷點 2] 從 Session 中解密出的特工身分 (memID): {current_mem_id}")
    
    if not current_mem_id:
        print("[X] 攔截：Session 內無 memID，判定為非法存取（401）！")
        response = jsonify({
            "status": "error",
            "message": "拒絕存取：尚未登入基金會系統，無法提交研究報告。"
        })
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        print("="*60 + "\n")
        return response, 401

    # 3. 測試時間模組是否正常
    try:
        auto_report_id = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[*] 成功生成系統時間戳記 reportID: {auto_report_id}")
    except NameError:
        print("[🔥 錯誤] 程式碼頂部可能漏寫了 `from datetime import datetime`！")
        response = jsonify({"status": "error", "message": "後端 datetime 模組未導入"})
        return response, 500

    try:
        data = request.get_json()
        print(f"[📍 斷點 3] 成功解析前端傳來的 JSON Payload:\n{data}")
        
        title        = data.get('title')       
        scp_id       = data.get('scpID')       
        abilities    = data.get('abilities')   
        weakness     = data.get('weakness')    
        appearance   = data.get('appearance')  
        others       = data.get('others')      
        required_lv  = data.get('required_lv', '1')  
        involved_members = data.get('involved_members', [])

        if not title or not scp_id:
            print("[X] 攔截：欄位閹割！標題或 SCP 代號為空（400）。")
            response = jsonify({
                "status": "error", 
                "message": "提交失敗：報告標題與涉及的 SCP 代號為必填項目。"
            })
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            return response, 400
        
        print("[📍 斷點 4] 啟動資料庫寫入事務 (Database Transaction)...")
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. 將報告核心內容寫入主表 Report
            print("    -> [SQL 1/3] 正在將核心數據打入 Report 表...")
            sql_report = """
                INSERT INTO Report (reportID, required_lv, title, appearance, abilities, weakness, others, scpID)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_report, (
                auto_report_id, required_lv, title, 
                appearance, abilities, weakness, others, scp_id
            ))

            # 2. 同步寫入多對多關係表 involved_mem (自動綁定填表人為 leader)
            print(f"    -> [SQL 2/3] 正在將填表人 {current_mem_id} 以 'leader' 身分綁定至關係表...")
            sql_relation = """
                INSERT INTO involved_mem (reportID, memID, role)
                VALUES (%s, %s, 'leader')
            """
            cursor.execute(sql_relation, (auto_report_id, current_mem_id))

            # 3. 遍歷涉及成員陣列
            print("    -> [SQL 3/3] 開始遍歷寫入共同參與的特工群...")
            for mem_id in involved_members:
                if mem_id == current_mem_id:
                    print(f"       [*] 偵測到填表人自己 ({mem_id})，自動跳過防重複寫入。")
                    continue
                    
                print(f"       [*] 寫入涉及成員身分: {mem_id}")
                sql_member = """
                    INSERT INTO involved_mem (reportID, memID, role)
                    VALUES (%s, %s, 'involved_member')
                """
                cursor.execute(sql_member, (auto_report_id, mem_id))

            # 提交 Transaction，確保兩張表資料完整性
            print("[📍 斷點 5] 正在發送最後的 conn.commit() 指令...")
            conn.commit()
            print("🎉 【資料庫事務順利閉環】報告已成功固化至 MySQL 中！")

        response = jsonify({
            "status": "success",
            "message": "研究報告已成功提交，系統已自動生成 reportID 並記錄填表人與時間。"
        })
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        print("="*60 + "\n")
        return response, 200

    except pymysql.MySQLError as e:
        print(f"[🔥 MySQL 嚴重崩潰] 事務失敗！觸發安全回滾機制 (Rollback)。原因：{e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()

        response = jsonify({
            "status": "error",
            "message": f"資料庫寫入失敗：{str(e)}"
        })
        response.headers.add("Access-Control-Allow-Origin", "http://localhost")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        print("="*60 + "\n")
        return response, 500
    
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

# ==========================================
# 工作 3-3 實作：API - 「SCP 字典基本資料搜尋」(黃家福)
# ==========================================
@app.route('/api/scp/search', methods=['GET'])
def search_scp():
    print("\n🔍 " + "="*60)
    print("【雷達追蹤】收到 /api/scp/search 查詢請求！")
    print(f"[*] 前端傳過來的原始網址參數 (Args): {dict(request.args)}")
    print(f"[*] 伺服器記憶體中的 Session 內容: {dict(session)}")

    # 斷點 1：讀取權限
    url_lv = request.args.get('clearance_lv')
    print(f"[📍 斷點 1] 從網址抓到的 clearance_lv 參數為: {url_lv} (型態: {type(url_lv)})")
    
    # 初始化權限
    user_clearance = int(url_lv) if (url_lv and url_lv.isdigit()) else 0
    print(f"[*] 經轉換後的初始 user_clearance = {user_clearance}")

    current_mem_id = session.get('memID')
    print(f"[*] 從 Session 嘗試讀取特工代號 (memID): {current_mem_id}")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if current_mem_id:
                cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
                user = cursor.fetchone()
                if user:
                    user_clearance = int(user['clearance_lv'])
                    print(f"[📍 斷點 2] 成功啟動 Session 覆蓋！資料庫查詢該特工真實等級為: LEVEL {user_clearance}")
            else:
                print("[!] 警告：Session 內無 memID，放棄資料庫權限覆蓋，維持初始等級。")

            # 最終定案權限
            print(f"💡 【決議】本輪查詢使用的特工判定權限 user_clearance = {user_clearance}")

            search_id = request.args.get('scpID')
            if search_id:
                cursor.execute("SELECT * FROM SCP WHERE scpID LIKE %s", (f"%{search_id}%",))
            else:
                cursor.execute("SELECT * FROM SCP")
            scps = cursor.fetchall()

            # 斷點 3：逐筆資料比對監聽
            print(f"\n[📍 斷點 3] 開始對 {len(scps)} 筆 SCP 進行動態情報遮蔽審查:")
            for scp in scps:
                scp_id = scp['scpID']
                scp_req_lv = int(scp['clearance_lv'])
                
                # 比對邏輯
                if user_clearance < scp_req_lv:
                    print(f"    ❌ 權限不足！ {user_clearance} < {scp_req_lv} -> 遮蔽 {scp_id}")
                    scp['appearance'] = "[REDACTED]"
                    scp['abilities']  = "[REDACTED]"
                    scp['weakness']   = "[REDACTED]"
                    scp['others']     = "[REDACTED]"
                else:
                    print(f"    ✅ 准予查閱！ {user_clearance} >= {scp_req_lv} -> 放行 {scp_id}")
            
            print("="*60 + "\n")
            response = jsonify(scps)
            response.headers.add("Access-Control-Allow-Origin", "http://localhost")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response, 200

    except pymysql.MySQLError as e:
        print(f"[🔥 錯誤] SQL 執行崩潰: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
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