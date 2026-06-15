import os
import json
import bcrypt
import pymysql
from datetime import datetime
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import traceback

# 載入 .env 檔案中的環境變數（如資料庫帳密），避免機密寫死在程式碼中
load_dotenv()

# 初始化 Flask 應用程式，並設定前端靜態檔案的資料夾路徑
app = Flask(__name__, static_folder='../frontend', static_url_path='')

# =========================================================================
# ✅ 【核心優化】全域打通 CORS 預檢與 Session Cookie 共享
# =========================================================================
app.secret_key = os.getenv('SECRET_KEY') # 用於加密 Session 的金鑰
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',        # 允許部分跨站請求攜帶 Cookie（前端與後端同源時適用）
    SESSION_COOKIE_SECURE=False,          # 開發環境 (localhost) 沒 HTTPS，設為 False；上線正式環境務必改為 True
    SESSION_REFRESH_EACH_REQUEST=True     # 每次請求都刷新 Session 過期時間
)

# 允許跨域請求（CORS），並明確允許攜帶憑證 (supports_credentials=True)
CORS(app, supports_credentials=True, origins=["http://localhost", "http://127.0.0.1"])

# =========================================================================
# 🎯 共用工具函式區 (Helpers)
# =========================================================================

# 📡 全域請求監聽器 (流量診斷)
# 每次收到 /api/ 開頭的請求前，都會先執行這裡，方便開發者在終端機監控流量
@app.before_request
def debug_cookie_traffic():
    if request.path.startswith('/api/'):
        print("\n📡 " + "="*70)
        print(f"【流量診斷】收到請求: {request.method} -> {request.path}")
        print(f"[*] 記憶體中的 Session 內容: {dict(session)}")
        print(f"[*] 是否持有有效特工身分 (memID): {session.get('memID')}")
        print("="*75 + "\n")

# 🔌 建立資料庫連線
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('SERVERNAME'),
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        database=os.getenv('DBNAME'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor # 讓撈出來的資料變成字典格式 (dict)，方便用 key 讀取
    )

# 🛡️ 核心安保 Helper：動態熔斷異常精神狀態者的所有寫入/變更請求
def check_operative_sanity(cursor, mem_id):
    cursor.execute("SELECT mem_status FROM Member WHERE memID = %s", (mem_id,))
    res = cursor.fetchone()
    # 如果查無此人，或是狀態為 abnormal，回傳 False 拒絕操作
    if res and res.get('mem_status') == 'abnormal':
        return False
    return True

# =========================================================================
# 網頁靜態路由導向
# =========================================================================
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/dashboard.html')
def dashboard():
    return app.send_static_file('dashboard.html')

# ==========================================
# 【API 1】特工身分驗證 /api/login
# ==========================================
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password_plain = data.get('password', '').strip()

        if not username or not password_plain:
            return jsonify({"message": "欄位不可為空"}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT memID, password_hash, clearance_lv, dept_name, mem_status FROM Member WHERE memID = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

        if not user:
            # 防禦列舉攻擊：找不到帳號，依然回傳「帳號或密碼錯誤」
            return jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"}), 401

        # 使用 bcrypt 比對密碼雜湊值
        is_valid = bcrypt.checkpw(password_plain.encode('utf-8'), user['password_hash'].encode('utf-8'))

        if is_valid:
            session['memID'] = user['memID'] # 登入成功，核發 Session 識別證
            return jsonify({
                "message": "登入成功，歡迎回到站點",
                "clearance_lv": user['clearance_lv'],
                "dept_name": user['dept_name'],  
                "mem_status": user['mem_status'], 
                "redirect": "dashboard.html"
            }), 200
        else:
            return jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"}), 401

    except Exception as e:
        # 🔒 【安全隱碼】: 內部印出詳細錯誤，外部回傳罐頭訊息
        print(f"💥 [LOGIN CRITICAL ERROR]: {str(e)}")
        return jsonify({"message": "安保系統連線異常，請稍後再試。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 【API 2】🔍 特工身分動態查核 /api/user-profile
# =========================================================================
@app.route('/api/user-profile', methods=['GET'])
def get_user_profile():
    try:
        # 檢查是否有 Session
        if 'memID' not in session:
            return jsonify({"message": "未授權的存取，請重新登入"}), 401

        current_username = session['memID']
        conn = get_db_connection()
        
        with conn.cursor() as cursor:
            sql = "SELECT clearance_lv, dept_name, permission, mem_status FROM Member WHERE memID = %s"
            cursor.execute(sql, (current_username,))
            user = cursor.fetchone()

        if not user:
            return jsonify({"message": "特工檔案已遭銷毀"}), 403

        # 回傳最新權限狀態
        return jsonify({
            "clearance_lv": user['clearance_lv'],
            "dept_name": user['dept_name'],
            "permission": user['permission'],
            "mem_status": user['mem_status']
        }), 200

    except Exception as e:
        # 🔒 【安全隱碼】
        print(f"💥 [PROFILE CRITICAL ERROR]: {str(e)}")
        return jsonify({"message": "無法同步安保資料，請聯絡管理員。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 🟢 【API 3】研究報告上傳 /api/reports/upload
# =========================================================================
@app.route('/api/reports/upload', methods=['POST'])
def upload_report():
    current_mem_id = session.get('memID') 
    if not current_mem_id:
        return jsonify({"message": "拒絕存取：尚未登入。"}), 401

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        data = request.get_json()
        title = data.get('title')       
        scp_id = data.get('scpID')       
        abilities = data.get('abilities')   
        weakness = data.get('weakness')    
        appearance = data.get('appearance')  
        others = data.get('others')      
        
        involved_members = [m.strip() for m in data.get('involved_members', []) if m and m.strip()]

        if not title or not scp_id:
            return jsonify({"message": "提交失敗：標題與 SCP 代號為必填。"}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # ☣️ 熔斷安全檢查：禁止精神異常者提交
            if not check_operative_sanity(cursor, current_mem_id):
                return jsonify({"message": "403 Forbidden: 精神狀態異常，報告提交功能已鎖定。"}), 403

            # 插入報告主表
            sql_report = """
                INSERT INTO Report (cmt_time, title, appearance, abilities, weakness, others, scpID)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_report, (now_str, title, appearance, abilities, weakness, others, scp_id))
            auto_report_id = cursor.lastrowid # 取得剛新增的報告 ID

            # 插入人員關聯表 (負責人)
            cursor.execute("INSERT INTO involved_mem (reportID, memID, role) VALUES (%s, %s, 'leader')", 
                           (auto_report_id, current_mem_id))

            # 插入人員關聯表 (其他參與者)
            for mem_id in involved_members:
                if mem_id == current_mem_id: continue
                cursor.execute("INSERT INTO involved_mem (reportID, memID, role) VALUES (%s, %s, 'involved_member')", 
                               (auto_report_id, mem_id))

            conn.commit() # 確認寫入資料庫
            return jsonify({"message": "研究報告已成功提交。"}), 200
            
    except Exception as e:
        if 'conn' in locals(): conn.rollback() # 發生錯誤時撤銷所有寫入，確保資料完整性
        # 🔒 【安全隱碼】
        print(f"💥 [UPLOAD CRITICAL ERROR]: {str(e)}")
        return jsonify({"message": "資料庫寫入失敗，請檢查輸入格式或聯絡管理員。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# ==========================================
# 【API 4】SCP 字典基本資料搜尋 /api/scp/search
# ==========================================
@app.route('/api/scp/search', methods=['GET'])
def search_scp():
    url_lv = request.args.get('clearance_lv')
    user_clearance = int(url_lv) if (url_lv and url_lv.isdigit()) else 0
    current_mem_id = session.get('memID')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 覆寫為資料庫最真實的權限
            if current_mem_id:
                cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
                user = cursor.fetchone()
                if user: user_clearance = int(user['clearance_lv'])

            search_id = request.args.get('scpID')
            if search_id:
                cursor.execute("SELECT * FROM SCP WHERE scpID LIKE %s", (f"%{search_id}%",))
            else:
                cursor.execute("SELECT * FROM SCP")
            
            scps = cursor.fetchall()

            # 資料遮蔽：權限不足的欄位直接蓋掉變為 [REDACTED]
            for scp in scps:
                if user_clearance < int(scp['clearance_lv']):
                    scp['appearance'] = scp['abilities'] = scp['weakness'] = scp['others'] = "[REDACTED]"
            
            return jsonify(scps), 200
    except Exception as e:
        # 🔒 【安全隱碼】
        print(f"💥 [SCP SEARCH ERROR]: {str(e)}")
        return jsonify({"message": "檔案檢索系統異常。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# ==========================================
# 【API 5】O5 專屬研究報告檢索 /api/admin/reports
# ==========================================
@app.route('/api/admin/reports', methods=['GET'])
def search_reports():
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"message": "拒絕存取：尚未登入"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            if not user or int(user['clearance_lv']) < 3:
                return jsonify({"message": "403 Forbidden：此操作僅限 O5 議會"}), 403
            
            cursor.execute("SELECT * FROM Report ORDER BY reportID DESC")
            reports = cursor.fetchall()
            
            for r in reports:
                if isinstance(r.get('cmt_time'), datetime):
                    r['cmt_time'] = r['cmt_time'].strftime('%Y-%m-%d %H:%M:%S')
                    
            return jsonify(reports), 200
    except Exception as e:
        # 🔒 【安全隱碼】
        print(f"💥 [REPORT SEARCH ERROR]: {str(e)}")
        return jsonify({"message": "報告系統讀取失敗。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 【API 6-A】O5 審查通過 /api/O5/approve
# =========================================================================
@app.route('/api/O5/approve', methods=['POST'])
def approve_report():
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"message": "拒絕存取：尚未登入"}), 401

    data = request.get_json()
    report_id = data.get('reportID')
    frontend_clearance_lv = data.get('clearance_lv')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if not check_operative_sanity(cursor, current_mem_id):
                return jsonify({"message": "403 Forbidden: 精神異常，核准功能鎖定。"}), 403

            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            if not user or int(user.get('clearance_lv', 0)) < 3:
                return jsonify({"message": "403 Forbidden：權限不足"}), 403

            cursor.execute("SELECT appearance, abilities, weakness, others, scpID FROM Report WHERE reportID = %s", (report_id,))
            report = cursor.fetchone()
            if not report:
                return jsonify({"message": "找不到該研究報告"}), 404

            # 將報告內容合併至主 SCP 表
            update_sql = """
                UPDATE SCP SET 
                    appearance = IF(LENGTH(COALESCE(appearance, '')) = 0, %s, CONCAT(appearance, ' / ', %s)),
                    abilities  = IF(LENGTH(COALESCE(abilities, '')) = 0, %s, CONCAT(abilities, ' / ', %s)),
                    weakness   = IF(LENGTH(COALESCE(weakness, '')) = 0, %s, CONCAT(weakness, ' / ', %s)),
                    others     = IF(LENGTH(COALESCE(others, '')) = 0, %s, CONCAT(others, ' / ', %s)),
                    clearance_lv = COALESCE(%s, clearance_lv)
                WHERE scpID = %s
            """
            cursor.execute(update_sql, (
                report['appearance'], report['appearance'],
                report['abilities'], report['abilities'],
                report['weakness'], report['weakness'],
                report['others'], report['others'],
                frontend_clearance_lv, report['scpID']
            ))
            
            cursor.execute("DELETE FROM Report WHERE reportID = %s", (report_id,))
            conn.commit()
            return jsonify({"message": "情報與權限等級整合成功。"}), 200
            
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        # 🔒 【安全隱碼】
        print(f"💥 [O5 APPROVE ERROR]: {str(e)}") 
        return jsonify({"message": "後端合併情報時發生異常。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 【API 6-B】O5 審查駁回 /api/O5/reject
# =========================================================================
@app.route('/api/O5/reject', methods=['POST'])
def reject_report():
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"message": "拒絕存取：尚未登入"}), 401

    report_id = request.get_json().get('reportID')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if not check_operative_sanity(cursor, current_mem_id):
                return jsonify({"message": "403 Forbidden: 精神異常，駁回功能鎖定。"}), 403

            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            if not user or int(user['clearance_lv']) < 3:
                return jsonify({"message": "403 Forbidden：權限不足"}), 403

            cursor.execute("DELETE FROM Report WHERE reportID = %s", (report_id,))
            conn.commit()
            return jsonify({"message": "報告已被駁回並物理銷毀。"}), 200
            
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        # 🔒 【安全隱碼】
        print(f"💥 [O5 REJECT ERROR]: {str(e)}") 
        return jsonify({"message": "資料庫刪除作業異常。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# ==========================================
# 【API 7】站點收容與監控 /api/admin/sites
# ==========================================
@app.route('/api/admin/sites', methods=['GET'])
def get_admin_sites():
    if not session.get('memID'):
        return jsonify({"message": "拒絕存取：尚未登入。"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT siteID, scpID, site_status, door_status, structure FROM Site LEFT JOIN contained_in USING (siteID)"
            cursor.execute(sql)
            return jsonify(cursor.fetchall()), 200
    except Exception as e:
        # 🔒 【安全隱碼】
        print(f"💥 [SITES DB ERROR]: {str(e)}") 
        return jsonify({"message": "站點連線失敗。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 【API 8】特工管理網關 (讀取名單 / 新增人員) /api/admin/members
# =========================================================================
@app.route('/api/admin/members', methods=['GET', 'POST'])
def admin_members_api_gateway():
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"message": "拒絕存取：尚未登入。"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
                current_user = cursor.fetchone()
                
                if not current_user:
                    return jsonify({"message": "無效的特工憑證。"}), 403
                
                my_clearance = int(current_user['clearance_lv'])
                # 只能看到權限小於等於自己的人員
                sql_filter = "SELECT memID, dept_name, clearance_lv, permission, mem_status FROM Member WHERE clearance_lv <= %s ORDER BY clearance_lv DESC, memID ASC"
                cursor.execute(sql_filter, (my_clearance,))
                return jsonify(cursor.fetchall()), 200
                
            elif request.method == 'POST':
                if not check_operative_sanity(cursor, current_mem_id):
                    return jsonify({"message": "403 Forbidden: 精神異常，無權編制新人員。"}), 403

                data = request.get_json()
                dept_name = data.get('dept_name', '').strip()
                clearance_lv = data.get('clearance_lv')
                permission = data.get('permission', '').strip()
                mem_status = data.get('mem_status', 'normal')
                raw_password = data.get('password')

                if not dept_name or not raw_password or not permission:
                    return jsonify({"message": "欄位不可為空。"}), 400

                password_hash = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                # 自動產生流水號 ID
                cursor.execute("SELECT COUNT(*) AS cnt FROM Member WHERE dept_name = %s", (dept_name,))
                next_num = cursor.fetchone()['cnt'] + 1

                if dept_name.upper() == 'O5':
                    mem_id = f"{dept_name}{str(next_num).zfill(6)}O5"
                else:
                    mem_id = f"{dept_name}{str(next_num).zfill(7)}{permission}"

                cursor.execute("""
                    INSERT INTO Member (memID, dept_name, clearance_lv, permission, mem_status, password_hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (mem_id, dept_name, clearance_lv, permission, mem_status, password_hash))
                
                conn.commit()
                return jsonify({'message': '新增成功', 'memID': mem_id}), 200

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        
        err_msg = str(e)
        # 🟢 強制印出原始錯誤字串，這行一定要有！
        print(f"💥 [MEMBERS GATEWAY ERROR - RAW]: {err_msg}") 
        
        # 🟢 改成檢查 Trigger 常見的錯誤特徵，或者直接檢查是否包含 "wrong" 或 "clearance"
        # 只要你的 Trigger 訊息包含這些關鍵字，就會觸發
        if "1644" in err_msg or "wrong" in err_msg.lower() or "clearance" in err_msg.lower():
            return jsonify({"message": "操作不合法：不符合基金會人事編制規則。"}), 400
            
        return jsonify({"message": "處理人員名單時發生伺服器錯誤。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 【API 9】動態修改特工精神狀態 /api/admin/members/<mem_id>/status
# =========================================================================
@app.route('/api/admin/members/<mem_id>/status', methods=['PATCH'])
def update_member_status(mem_id):
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"message": "拒絕存取：尚未登入。"}), 401

    try:
        new_status = request.get_json().get('mem_status')
        valid_statuses = ['normal', 'abnormal', 'treating', 'dead', 'suspended']
        
        if new_status not in valid_statuses:
            return jsonify({"message": "不合法的精神狀態值。"}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            if not check_operative_sanity(cursor, current_mem_id):
                return jsonify({"message": "403 Forbidden: 精神異常，無權修改醫療狀態。"}), 403

            sql = "UPDATE Member SET mem_status = %s WHERE memID = %s"
            cursor.execute(sql, (new_status, mem_id))
            conn.commit()

            return jsonify({"message": f"特工 {mem_id} 狀態已更新為 {new_status}。"}), 200
            
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        # 🔒 【安全隱碼】
        print(f"💥 [UPDATE STATUS ERROR]: {str(e)}") 
        return jsonify({"message": "狀態更新失敗。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 【API 10】動態修改 SCP 安全權限等級 /api/scp/update_clearance
# =========================================================================
@app.route('/api/scp/update_clearance', methods=['PUT'])
def update_scp_clearance():
    if not session.get('memID'):
        return jsonify({"message": "拒絕存取：尚未登入。"}), 401

    try:
        data = request.get_json()
        scp_id = data.get('scpID')
        new_lv = data.get('clearance_lv')

        if int(new_lv) not in [0, 1, 2, 3]:
            return jsonify({"message": "不合法的安全等級。"}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "UPDATE SCP SET clearance_lv = %s WHERE scpID = %s"
            cursor.execute(sql, (int(new_lv), scp_id))
            conn.commit()
            return jsonify({"message": f"SCP-{scp_id} 權限已更新為 Level {new_lv}。"}), 200
            
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        # 🔒 【安全隱碼】
        print(f"💥 [UPDATE SCP LEVEL ERROR]: {str(e)}") 
        return jsonify({"message": "權限變更系統異常。"}), 500
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear() # 清除所有 Session 資料
    return jsonify({"message": "已登出"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)