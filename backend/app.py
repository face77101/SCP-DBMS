import os
import json
import bcrypt
import pymysql
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

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
        
        print(f"⚙️ 系統 Bcrypt 本地自檢結果 (預期應為 True): {debug_verify}", flush=True)
        print(f"🔑 前端傳進來的明文密碼: [{password_plain}] (長度: {len(password_plain)})", flush=True)
        print(f"🔒 資料庫撈出的雜湊密碼: [{user['password_hash']}] (長度: {len(user['password_hash'])})", flush=True)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) #每次你改 Code，後端就會自動同步，不用手動重啟 Docker！