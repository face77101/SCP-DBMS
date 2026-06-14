import os
import json
import bcrypt
import pymysql
from datetime import datetime
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import traceback

load_dotenv()

app = Flask(__name__, static_folder='../frontend', static_url_path='')

# =========================================================================
# ✅ 【核心優化】全域打通 CORS 預檢與 Session Cookie 共享
# =========================================================================
app.secret_key = os.getenv('SECRET_KEY')
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,  # localhost 開發環境允許 HTTP 傳輸
    SESSION_REFRESH_EACH_REQUEST=True
)

CORS(app, supports_credentials=True, origins=["http://localhost", "http://127.0.0.1"])

# 📡 全域請求監聽器 (流量診斷)
@app.before_request
def debug_cookie_traffic():
    if request.path.startswith('/api/'):
        print("\n📡 " + "="*70)
        print(f"【流量診斷】收到請求: {request.method} -> {request.path}")
        print(f"[*] 伺服器記憶體中的 Session 內容: {dict(session)}")
        print(f"[*] 是否持有有效特工身分 (memID): {session.get('memID')}")
        print("="*75 + "\n")

# 建立資料庫連線的 Helper Function
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('SERVERNAME'),
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        database=os.getenv('DBNAME'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# 🛡️ 核心安保 Helper：動態熔斷異常精神狀態者的所有寫入/變更請求
def check_operative_sanity(cursor, mem_id):
    cursor.execute("SELECT mem_status FROM Member WHERE memID = %s", (mem_id,))
    res = cursor.fetchone()
    if res and res.get('mem_status') == 'abnormal':
        return False
    return True

# 靜態路由導向
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
    print("\n🔑 " + "="*60)
    print("【雷達追蹤】收到 /api/login 請求！")
    
    try:
        data = request.get_json()
        username = data.get('username') if data else None
        password_plain = data.get('password').strip() if data and data.get('password') else ""

        if not username or not password_plain:
            return jsonify({"message": "欄位不可為空"}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT memID, password_hash, clearance_lv, dept_name, mem_status FROM Member WHERE memID = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

        if not user:
            print("[X] 驗證失敗：資料庫裡無此 memID！")
            return jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"}), 401

        is_valid = bcrypt.checkpw(
            password_plain.encode('utf-8'), 
            user['password_hash'].encode('utf-8')
        )

        if is_valid:
            session['memID'] = user['memID'] 
            print(f"[📍] 密碼正確！已寫入 Session: memID={session['memID']}")
            return jsonify({
                "message": "登入成功，歡迎回到站點",
                "clearance_lv": user['clearance_lv'],
                "dept_name": user['dept_name'],  
                "mem_status": user['mem_status'], # 👈 傳回精神狀態讓前端同步啟動黑屏
                "redirect": "dashboard.html"
            }), 200
        else:
            return jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"}), 401

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": f"【後端崩潰】: {str(e)}"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 🟢 研究報告上傳 /api/reports/upload (🛡️ 納入心理異常防禦熔斷)
# =========================================================================
@app.route('/api/reports/upload', methods=['POST'])
def upload_report():
    current_mem_id = session.get('memID') 
    if not current_mem_id:
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入基金會系統。"}), 401

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        data = request.get_json()
        title = data.get('title')       
        scp_id = data.get('scpID')       
        abilities = data.get('abilities')   
        weakness = data.get('weakness')    
        appearance = data.get('appearance')  
        others = data.get('others')      
        
        involved_members = data.get('involved_members', [])
        involved_members = [m.strip() for m in involved_members if m and m.strip()]

        if not title or not scp_id:
            return jsonify({"status": "error", "message": "提交失敗：標題與 SCP 代號為必填。"}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # ☣️ 熔斷安全檢查：禁止精神異常者提交
                if not check_operative_sanity(cursor, current_mem_id):
                    return jsonify({"status": "error", "message": "403 Forbidden: 精神狀態異常，研究報告提交功能已遭安保鎖定。"}), 403

                sql_report = """
                    INSERT INTO Report (cmt_time, title, appearance, abilities, weakness, others, scpID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_report, (now_str, title, appearance, abilities, weakness, others, scp_id))

                auto_report_id = cursor.lastrowid

                sql_relation = "INSERT INTO involved_mem (reportID, memID, role) VALUES (%s, %s, 'leader')"
                cursor.execute(sql_relation, (auto_report_id, current_mem_id))

                for mem_id in involved_members:
                    if mem_id == current_mem_id: continue
                    sql_member = "INSERT INTO involved_mem (reportID, memID, role) VALUES (%s, %s, 'involved_member')"
                    cursor.execute(sql_member, (auto_report_id, mem_id))

                conn.commit()
                return jsonify({"status": "success", "message": "研究報告已成功提交。"}), 200
        except Exception as sql_err:
            if 'conn' in locals(): conn.rollback()
            raise sql_err
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"資料庫寫入失敗：{str(e)}"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# ==========================================
# 【API 3】SCP 字典基本資料搜尋 /api/scp/search
# ==========================================
@app.route('/api/scp/search', methods=['GET'])
def search_scp():
    url_lv = request.args.get('clearance_lv')
    user_clearance = int(url_lv) if (url_lv and url_lv.isdigit()) else 0
    current_mem_id = session.get('memID')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
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

            for scp in scps:
                if user_clearance < int(scp['clearance_lv']):
                    scp['appearance'] = scp['abilities'] = scp['weakness'] = scp['others'] = "[REDACTED]"
            
            return jsonify(scps), 200
    except pymysql.MySQLError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

# ==========================================
# 【API 4】O5 專屬研究報告檢索 /api/admin/reports
# ==========================================
@app.route('/api/admin/reports', methods=['GET'])
def search_reports():
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            if not user or int(user['clearance_lv']) < 3:
                return jsonify({"status": "error", "message": "403 Forbidden：此操作僅限 O5 議會"}), 403
            
            cursor.execute("SELECT * FROM Report ORDER BY reportID DESC")
            reports = cursor.fetchall()
            
            for r in reports:
                if isinstance(r.get('cmt_time'), datetime):
                    r['cmt_time'] = r['cmt_time'].strftime('%Y-%m-%d %H:%M:%S')
                    
            return jsonify(reports), 200
    except pymysql.MySQLError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 【API 5-A】O5 審查通過 (🛡️ 納入心理異常防禦熔斷)
# =========================================================================
@app.route('/api/O5/approve', methods=['POST'])
def approve_report():
    current_mem_id = session.get('memID')
    print(f"🕵️ [O5 APPROVE] 當前 Session 特工 ID: {current_mem_id}")
    
    if not current_mem_id:
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入"}), 401

    data = request.get_json()
    report_id = data.get('reportID')
    frontend_clearance_lv = data.get('clearance_lv')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ☣️ 熔斷安全檢查：禁止精神異常者進行審核通過
            if not check_operative_sanity(cursor, current_mem_id):
                return jsonify({"status": "error", "message": "403 Forbidden: 精神狀態異常，情報核准與固化功能已全面鎖定。"}), 403

            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            
            if not user or user.get('clearance_lv') is None or int(user['clearance_lv']) < 3:
                return jsonify({"status": "error", "message": "403 Forbidden：權限不足或特工不存在"}), 403

            cursor.execute("SELECT appearance, abilities, weakness, others, scpID FROM Report WHERE reportID = %s", (report_id,))
            report = cursor.fetchone()
            if not report:
                return jsonify({"status": "error", "message": "找不到該研究報告"}), 404

            update_sql = """
                UPDATE SCP SET 
                    appearance = IF(LENGTH(COALESCE(appearance, '')) = 0, %s, CONCAT(appearance, ' / ', %s)),
                    abilities  = IF(LENGTH(COALESCE(abilities, '')) = 0, %s, CONCAT(abilities, ' / ', %s)),
                    weakness   = IF(LENGTH(COALESCE(weakness, '')) = 0, %s, CONCAT(weakness, ' / ', %s)),
                    others     = IF(LENGTH(COALESCE(others, '')) = 0, %s, CONCAT(others, ' / ', %s)),
                    clearance_lv = COALESCE(%s, clearance_lv)
                WHERE scpID = %s
            """
            
            print(f"👑 [O5 APPROVED] 項目 {report['scpID']} 的情報已成功合流，且安保等級鎖定為: LEVEL {frontend_clearance_lv}")
            
            cursor.execute(update_sql, (
                report['appearance'], report['appearance'],
                report['abilities'], report['abilities'],
                report['weakness'], report['weakness'],
                report['others'], report['others'],
                frontend_clearance_lv, 
                report['scpID']
            ))
            
            cursor.execute("DELETE FROM Report WHERE reportID = %s", (report_id,))
            conn.commit()
            return jsonify({"status": "success", "message": "情報與權限等級整合成功。"}), 200
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        print(f"[🔥 審查崩潰] 原因: {e}") 
        return jsonify({"status": "error", "message": f"後端內部錯誤: {str(e)}"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 🚨 【全新擴充 API 5-B】O5 審查不通過 (🛡️ 納入心理異常防禦熔斷)
# =========================================================================
@app.route('/api/O5/reject', methods=['POST'])
def reject_report():
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
            # ☣️ 熔斷安全檢查
            if not check_operative_sanity(cursor, current_mem_id):
                return jsonify({"status": "error", "message": "403 Forbidden: 精神狀態異常，報告駁回功能鎖定。"}), 403

            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            if not user or int(user['clearance_lv']) < 3:
                return jsonify({"status": "error", "message": "403 Forbidden"}), 403

            cursor.execute("DELETE FROM Report WHERE reportID = %s", (report_id,))
            conn.commit()
            
            return jsonify({"status": "success", "message": "報告已被 O5 議會駁回並物理銷毀。"}), 200
    except pymysql.MySQLError as e:
        if 'conn' in locals(): conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

# ==========================================
# 【API 6】站點收容與監控 /api/admin/sites
# ==========================================
@app.route('/api/admin/sites', methods=['GET'])
def get_admin_sites():
    if not session.get('memID'):
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入系統。"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT siteID, scpID, site_status, door_status, structure FROM Site LEFT JOIN contained_in USING (siteID)"
            cursor.execute(sql)
            return jsonify(cursor.fetchall()), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"資料庫查詢失敗: {str(e)}"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 【API 7】特工管理網關 (🛡️ 納入心理異常防禦熔斷：禁止異常者新增人員)
# =========================================================================
@app.route('/api/admin/members', methods=['GET', 'POST'])
def admin_members_api_gateway():
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"error": "ACCESS DENIED: Session expired or invalid."}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
                current_user = cursor.fetchone()
                
                if not current_user or current_user.get('clearance_lv') is None:
                    return jsonify({"error": "ACCESS DENIED: Invalid operative registry."}), 403
                
                my_clearance = int(current_user['clearance_lv'])
                print(f"🕵️ [MEMBER GUARD] 特工 {current_mem_id} (Level {my_clearance}) 正在請求成員名單...")

                sql_filter = """
                    SELECT memID, dept_name, clearance_lv, permission, mem_status 
                    FROM Member 
                    WHERE clearance_lv <= %s
                    ORDER BY clearance_lv DESC, memID ASC
                """
                cursor.execute(sql_filter, (my_clearance,))
                members_list = cursor.fetchall()
                return jsonify(members_list), 200
                
            elif request.method == 'POST':
                # ☣️ 熔斷安全檢查：精神異常者絕對禁止「編制、新增特工人員」
                if not check_operative_sanity(cursor, current_mem_id):
                    return jsonify({"error": "403 Forbidden: 精神狀態異常特工無權調動或指派新進人員編制。"}), 403

                data = request.get_json()
                dept_name = data.get('dept_name', '').strip()
                clearance_lv = data.get('clearance_lv')
                permission = data.get('permission', '').strip()
                mem_status = data.get('mem_status', 'normal')
                raw_password = data.get('password')

                if not dept_name or not raw_password or not permission:
                    return jsonify({"error": "Fields cannot be empty"}), 400

                password_hash = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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

                print(f"🎉 成功將新特工 {mem_id} 固化至 MySQL 完畢！")
                return jsonify({'message': '新增成功', 'memID': mem_id}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 🔒 【API 7-B】動態修改特工精神狀態 (🛡️ 納入心理異常防禦熔斷：禁止異常者修改任何人狀態)
# =========================================================================
@app.route('/api/admin/members/<mem_id>/status', methods=['PATCH'])
def update_member_status(mem_id):
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入系統。"}), 401

    try:
        data = request.get_json()
        new_status = data.get('mem_status')

        if not new_status:
            return jsonify({"status": "error", "message": "缺少必要參數 mem_status。"}), 400
        
        valid_statuses = ['normal', 'abnormal', 'treating', 'dead', 'suspended']
        if new_status not in valid_statuses:
            return jsonify({"status": "error", "message": f"不合法的精神狀態值。允許範圍: {valid_statuses}"}), 400

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # ☣️ 熔斷安全檢查：遭遇認知危害者，其指令不被信任，不可修改任何人的心理狀態
                if not check_operative_sanity(cursor, current_mem_id):
                    return jsonify({"status": "error", "message": "403 Forbidden: 精神狀態異常特工無權修改或核准特工醫療狀態。"}), 403

                sql = "UPDATE Member SET mem_status = %s WHERE memID = %s"
                affected_rows = cursor.execute(sql, (new_status, mem_id))
                conn.commit()

                if affected_rows == 0:
                    return jsonify({"status": "warning", "message": "未發現變更（可能新舊狀態相同，或查無此特工 ID）。"}), 200
                
                print(f"🚨 [狀態調校] 特工 {current_mem_id} 已將人員 {mem_id} 的精神狀態同步修復為: {new_status.upper()}")
                return jsonify({"status": "success", "message": f"特工 {mem_id} 精神狀態已更新為 {new_status}。"}), 200
                
        except Exception as sql_err:
            if 'conn' in locals(): conn.rollback()
            raise sql_err
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"資料庫狀態更新失敗：{str(e)}"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# =========================================================================
# 🔒 【審查介面專用】動態修改 SCP 安全權限等級
# =========================================================================
@app.route('/api/scp/update_clearance', methods=['PUT'])
def update_scp_clearance():
    current_mem_id = session.get('memID')
    if not current_mem_id:
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入系統。"}), 401

    try:
        data = request.get_json()
        scp_id = data.get('scpID')
        new_lv = data.get('clearance_lv')

        if scp_id is None or new_lv is None:
            return jsonify({"status": "error", "message": "缺少必要參數 scpID 或 clearance_lv。"}), 400
        
        if int(new_lv) not in [0, 1, 2, 3]:
            return jsonify({"status": "error", "message": "不合法的安全等級 (必須為 0~3)。"}), 400

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                sql = "UPDATE SCP SET clearance_lv = %s WHERE scpID = %s"
                affected_rows = cursor.execute(sql, (int(new_lv), scp_id))
                conn.commit()

                if affected_rows == 0:
                    return jsonify({"status": "warning", "message": "未發現變更（可能新舊等級相同，或查過無此 SCPID）。"}), 200
                
                print(f"🚨 [權限變更] 特工 {current_mem_id} 已將項目 {scp_id} 的權限修改為 Level {new_lv}")
                return jsonify({"status": "success", "message": f"SCP-{scp_id} 權限已成功更新為 Level {new_lv}。"}), 200
        except Exception as sql_err:
            if 'conn' in locals(): conn.rollback()
            raise sql_err
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"資料庫更新失敗：{str(e)}"}), 500
    finally:
        if 'conn' in locals(): conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)