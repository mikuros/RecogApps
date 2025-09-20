from embedder import generate_secret_key, embed_with_key, detect_with_key#ここでembedder.pyの関数をインポートしてる

from flask import Flask, request, render_template, send_from_directory, url_for, Blueprint, current_app
from models import db, Watermark
import os, cv2, numpy as np
import uuid, bleach
from werkzeug.utils import secure_filename
from PIL import Image #★追加★拡張子セキュリティ
from io import BytesIO#★追加★拡張子セキュリティ

watermark_bp = Blueprint('watermark', __name__, url_prefix='/watermark')

"""画像保存先を static 外の非公開ディレクトリに変更"""
# app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'watermark_processed')
#→app.configとして使うならapp.pyにまとめるべきであるため、app.configを使わずに以下のように定数化した。参照部分の書き換えも完了。
#★ここが課題(current_appを使えない)
# UPLOAD_FOLDER = os.path.join(current_app.root_path, 'watermark_processed')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'watermark_processed')#このファイルの場所を基準にするため、ディレクトリ移動させる際は要注意。BP単位で分けたいときに適した書き方。
"""ここまで"""


# 拡張子セキュリティ(Pillowで画像形式判定)
def validate_image(file):
    try:
        image = Image.open(BytesIO(file.read()))
        image.verify()#整合性チェック            (開く前の検査)
        file.seek(0)#先頭に戻しておく

        if image.format not in ['JPEG', 'PNG']:#(開いた後の検査)
            return "対応していない画像形式です。"
    except Exception:
        return "画像の解析に失敗しました。画像が破損しているか、非対応な形式です。"

    file.seek(0)
    return None  #エラーがなければ None を返す
# ここまで

@watermark_bp.route('/')
def index():
    return render_template('upload_watermark.html')


# このルーティングではPOSTしか許可してない。ブラウザからURLを直接入力してアクセスする場合のHTTPメソッドはGETであるため、弾かれる。
# 故に、upload()内の処理が走ることはない。→if文で囲う必要はない。
# ただ、この状態でURLにアクセスすると、[The method is not allowed for the requested URL.]というエラーが表示されるため、別途エラーページに飛ばしたい場合はif-elseで分岐させても良い。
@watermark_bp.route('/upload', methods=['POST'])
def upload():
    file = request.files['image']
    display_name = bleach.clean(request.form['display_name'].strip(), tags=['u'], attributes={}, strip=True)
		# display_nameのみに下線を引くためにsafeにしてる。

    # この関数はPOSTありき(urlの遷移だけのケースはない。url自体も存在しないため、ifいらないかも？)
    if request.method == 'POST':
        # 拡張子セキュリティ(Pillowで画像形式判定)
        error_msg = validate_image(file)
        if error_msg:
            return render_template('upload_watermark.html', error=error_msg)
        # ここまで

        # 拡張子分岐
        original_filename = secure_filename(file.filename)  #secure_filenameでファイル名に危険なコードが含まれている場合に処理してくれる。
        ext = os.path.splitext(original_filename)[1].lower()#例: ".jpg", ".png"
        # ここまで


        img_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

        key = generate_secret_key()
        watermarked = embed_with_key(img, key)

        uid = uuid.uuid4().hex
        new_filename = f"{uid}{ext}"#ファイルネームを変数に格納。/#extで拡張子を指定

        save_path = os.path.join(UPLOAD_FOLDER, new_filename)#★修正★new_fielname

        # 拡張子分岐
        if ext in ['.jpg', '.jpeg']:
            cv2.imwrite(save_path, watermarked, [cv2.IMWRITE_JPEG_QUALITY, 100])
        else:
            cv2.imwrite(save_path, watermarked, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        # ここまで

        db.session.add(Watermark(display_name_db=display_name, secret_key_db=key))
        db.session.commit()

        # 公開用URLを生成
        public_url = url_for('watermark.processed_file', filename=new_filename)#△ここでfilenameに入れたものが、@watermark_bp.route('/tmp/<filename>')に繋がる
        

        return render_template('result_watermark.html',
                               message=f"<u>{display_name}</u> の電子透かし画像を生成しました。",
                               img_url=public_url,#save_pathからpublic_urlに変更
                               download_name=new_filename)#★修正★new_filename

@watermark_bp.route('/detect', methods=['GET','POST'])
def detect():
    if request.method == 'POST':
        file = request.files['image']

        # 拡張子セキュリティ(Pillowで画像形式判定)
        error_msg = validate_image(file)
        if error_msg:
            return render_template('detect_watermark.html', error=error_msg)
        # ここまで


        img_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

        # records = Watermark.query.order_by(db.text("ROWID DESC")).all()#rowidを使ってデータベースの最新順で探索/rowidは隠し列だから属性として使えない。
        records = Watermark.query.order_by(Watermark.created_at_db.desc()).all()#こっちの方が確実、データベースの最新順で探索

        for record in records:
            found = detect_with_key(img, record.secret_key_db)
            if found:
                msg = f"電子透かし検出成功！この画像の名前は <u>{record.display_name_db}</u> です。"
                break
        else:
            msg = "電子透かしは検出できませんでした"

        return render_template('detect_watermark.html', message=msg)

    return render_template('detect_watermark.html')


# 非公開ディレクトリから画像を取得する
@watermark_bp.route('/tmp/<filename>')#△ディレクトリ名が実際に存在するディレクトリになっていたので、tmpに変更
def processed_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
