from flask import Flask, send_from_directory
from mem import register_routes
from sites import sites_list

app = Flask(__name__)

register_routes(app)
sites_list(app)

@app.route('/')
def hello():
    return "SCP 基金會後端伺服器已上線。恭喜你測試成功！這玩意是臨時的~哈~^Ｏ^"

@app.get('/members')
def members_page():
    return send_from_directory('/frontend', 'mem.html')

@app.get('/members/add')
def add_member_page():
    return send_from_directory('/frontend', 'add_mem.html')

@app.get('/sites')
def sites_page():
    return send_from_directory('/frontend', 'sites.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) #每次你改 Code，後端就會自動同步，不用手動重啟 Docker！