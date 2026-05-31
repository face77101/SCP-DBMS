from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "SCP 基金會後端伺服器已上線。恭喜你測試成功！這玩意是臨時的~哈~^Ｏ^"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) #每次你改 Code，後端就會自動同步，不用手動重啟 Docker！