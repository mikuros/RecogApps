from flask import Flask, session, render_template
from app_mosaic import mosaic_bp
from app_watermark import watermark_bp
from datetime import timedelta
from flask_session import Session
from models import db

app = Flask(__name__)#Flaskのインスタンス作成

# app_mosaic.pyから。
app.secret_key = 'your_secret_key'  #★セッションの暗号化に使用
app.config['SESSION_TYPE'] = 'filesystem'   #サーバー側に保存
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_PERMANENT'] = True     #永続セッションを有効にする
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  #有効時間を30分
Session(app)#Flask-Sessionを初期化(ここで初めてFlask-Sessionが有効になる)

# app_watermark.pyから。
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///watermarks.db'
db.init_app(app)
with app.app_context():
    db.create_all()

app.register_blueprint(mosaic_bp)
app.register_blueprint(watermark_bp)


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')

# 404エラーを返す代わりに、以下の関数を呼び出す。つまり、404ページの代わりにカスタムHTMLを表示。※戻り値2つ目により、ブラウザに404自体は返している。
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error_page.html'), 404
    