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

def sites_list(app):
    @app.get('/api/admin/sites')
    def get_sites_list():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT *
                    FROM Site left join contained_in using (siteID)
                """)
                sites = cursor.fetchall()
            return jsonify(sites)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
            