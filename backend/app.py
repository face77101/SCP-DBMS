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
# ✅ 【核心優化】全域打通 CORS 預檢與 Session Cookie 共享（免去手動寫 OPTIONS）
# =========================================================================
app.secret_key = os.getenv('EXTERNAL_API_KEY', os.urandom(24).hex())
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,  # localhost 開發環境允許 HTTP 傳輸
    SESSION_REFRESH_EACH_REQUEST=True
)

# 💡 一行全域託管：允許跨域攜帶憑證，免除在各 API 內手動添加 Access-Control 標頭
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
            sql = "SELECT memID, password_hash, clearance_lv FROM Member WHERE memID = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

        if not user:
            print("[X] 驗證失敗：資料庫裡無此 memID！")
            return jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"}), 401

        # Bcrypt 密碼大驗兵
        is_valid = bcrypt.checkpw(
            password_plain.encode('utf-8'), 
            user['password_hash'].encode('utf-8')
        )

        if is_valid:
            session['memID'] = user['memID'] 
            print(f"[📍] 密碼正確！已寫入 Session 記憶體: memID={session['memID']}")
            return jsonify({
                "message": "登入成功，歡迎回到站點",
                "clearance_lv": user['clearance_lv'],
                "redirect": "dashboard.html"
            }), 200
        else:
            return jsonify({"message": "權限驗證失敗（帳號或密碼錯誤）"}), 401

    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": f"【後端崩潰】: {str(e)}"}), 500
    finally:
        if 'conn' in locals(): conn.close()

# ==========================================
# 【API 2】研究報告上傳 /api/reports/upload
# ==========================================
@app.route('/api/reports/upload', methods=['POST'])
def upload_report():
    current_mem_id = session.get('memID') 
    if not current_mem_id:
        return jsonify({"status": "error", "message": "拒絕存取：尚未登入基金會系統。"}), 401

    auto_report_id = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        data = request.get_json()
        title = data.get('title')       
        scp_id = data.get('scpID')       
        abilities = data.get('abilities')   
        weakness = data.get('weakness')    
        appearance = data.get('appearance')  
        others = data.get('others')      
        required_lv = data.get('required_lv', '1')  
        involved_members = data.get('involved_members', [])

        if not title or not scp_id:
            return jsonify({"status": "error", "message": "提交失敗：標題與 SCP 代號為必填。"}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. 寫入主表 Report
            sql_report = """
                INSERT INTO Report (reportID, required_lv, title, appearance, abilities, weakness, others, scpID)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_report, (auto_report_id, required_lv, title, appearance, abilities, weakness, others, scp_id))

            # 2. 同步寫入多對多關係表 (填表人為 leader)
            sql_relation = "INSERT INTO involved_mem (reportID, memID, role) VALUES (%s, %s, 'leader')"
            cursor.execute(sql_relation, (auto_report_id, current_mem_id))

            # 3. 寫入共同參與特工
            for mem_id in involved_members:
                if mem_id == current_mem_id: continue
                sql_member = "INSERT INTO involved_mem (reportID, memID, role) VALUES (%s, %s, 'involved_member')"
                cursor.execute(sql_member, (auto_report_id, mem_id))

            conn.commit()
            return jsonify({"status": "success", "message": "研究報告已成功提交。"}), 200

    except pymysql.MySQLError as e:
        traceback.print_exc()
        if 'conn' in locals(): conn.rollback()
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

            # 動態情報遮蔽審查
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
            return jsonify(cursor.fetchall()), 200
    except pymysql.MySQLError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()

# ==========================================
# 【API 5】O5 審查並統整至 SCP 字典 /api/O5/approve
# ==========================================
@app.route('/api/O5/approve', methods=['POST'])
def approve_report():
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
            cursor.execute("SELECT clearance_lv FROM Member WHERE memID = %s", (current_mem_id,))
            user = cursor.fetchone()
            if not user or int(user['clearance_lv']) < 3:
                return jsonify({"status": "error", "message": "403 Forbidden：此操作僅限 O5 議會"}), 403

            cursor.execute("SELECT appearance, abilities, weakness, others, scpID FROM Report WHERE reportID = %s", (report_id,))
            report = cursor.fetchone()
            if not report:
                return jsonify({"status": "error", "message": "找不到該研究報告"}), 404

            update_sql = """
                UPDATE SCP SET appearance = %s, abilities = %s, weakness = %s, others = %s WHERE scpID = %s
            """
            cursor.execute(update_sql, (report['appearance'], report['abilities'], report['weakness'], report['others'], report['scpID']))
            conn.commit()
            return jsonify({"status": "success", "message": f"SCP 情報已整併至 {report['scpID']}。"}), 200
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

# ==========================================
# 【API 7】特工管理網關 /api/admin/members
# ==========================================
@app.route('/api/admin/members', methods=['GET', 'POST'])
def admin_members_api_gateway():
    if not session.get('memID'):
        return jsonify({"error": "ACCESS DENIED: Session expired or invalid."}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT memID, dept_name, clearance_lv, permission, mem_status FROM Member")
                return jsonify(cursor.fetchall()), 200
                
            elif request.method == 'POST':
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

                # ID 生成邏輯
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)