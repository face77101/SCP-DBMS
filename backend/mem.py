from flask import jsonify, request
import pymysql
import os
import bcrypt

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('SERVERNAME'),
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        database=os.getenv('DBNAME'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def register_routes(app):
    # 查看現有成員資料
    # 限制：
    #   - 人員編級高的可以查看比他低的，反過來不 OK
    @app.get('/api/admin/members')
    def get_mem_list():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                '''
                登入系統能用再改
                urrent_permission = session.get('permission')
                level_order = ['A', 'B', 'C', 'D']
                current_index = level_order.index(current_permission)
                allowed = tuple(level_order[current_index:])

                cursor.execute("""
                    SELECT memID, dept_name, clearance_lv, permission, mem_status
                    FROM Member
                    WHERE permission IN %s""", (allowed,))
                '''
                
                cursor.execute("""
                    SELECT memID, dept_name, clearance_lv, permission, mem_status
                    FROM Member
                """)

                members = cursor.fetchall()
            return jsonify(members)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    # 更新現有成員的精神狀態
    # 限制：
    #   - 人員編級高的可以修改比他低的，反過來不 OK
    @app.patch('/api/admin/members/<memID>/status')
    def update_mem_status(memID):
        conn = get_db_connection()
        try:
            data = request.get_json()
            new_status = data.get('mem_status')

            with conn.cursor() as cursor:
                # 等登入做好之後在這裡加檢視限制
                cursor.execute("""
                    UPDATE Member
                    SET mem_status = %s
                    WHERE memID = %s
                """, (new_status, memID))
                conn.commit()
            return jsonify({'message': '更新成功'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    # 新增成員資料
    @app.post('/api/admin/members')
    def add_member():
        conn = get_db_connection()
        try:
            data = request.get_json()
            dept_name    = data.get('dept_name')
            clearance_lv = data.get('clearance_lv')
            permission   = data.get('permission')
            mem_status   = data.get('mem_status', 'normal')
            raw_password = data.get('password')

            # 加鹽雜湊
            password_hash = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS cnt FROM Member WHERE dept_name = %s", (dept_name,))
                count = cursor.fetchone()['cnt']
                mem_id = f"{dept_name}{str(count + 1).zfill(5)}{permission}"

                cursor.execute("""
                    INSERT INTO Member (memID, dept_name, clearance_lv, permission, mem_status, password_hash)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (mem_id, dept_name, clearance_lv, permission, mem_status, password_hash))
                conn.commit()

            return jsonify({'message': '新增成功', 'memID': mem_id})

        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
            