from flask import Flask, render_template, request, send_from_directory, url_for, session, send_file, redirect, flash, Blueprint, current_app
from facenet_pytorch import MTCNN
from PIL import Image
import os, cv2, uuid, numpy as np
from werkzeug.utils import secure_filename
from io import BytesIO
from flask_session import Session
from datetime import timedelta

mosaic_bp = Blueprint('mosaic', __name__, url_prefix='/mosaic')

# ※Flask-Sessionの初期化はBlueprint内ではできないため。app.pyに移行済み。


UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "mosaic_uploads")
PROCESSED_FOLDER = os.path.join(os.path.dirname(__file__), "mosaic_processed")


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# 拡張子セキュリティ(Pillowで画像形式判定)
def validate_image(file):
    try:
        image = Image.open(BytesIO(file.read()))
        image.verify()#整合性チェック(開く前の検査)
        file.seek(0)#先頭に戻しておく

        if image.format not in ['JPEG', 'PNG']:#整合性チェック(開いた後の検査)
            return "対応していない画像形式です。"
    except Exception:
        return "画像の解析に失敗しました。画像が破損しているか、非対応な形式です。"

    return None  #エラーがなければ None を返す


# モザイク処理関数
def apply_mosaic(img, box, mosaic_size=15):
    x1, y1, x2, y2 = [int(point) for point in box]
    face = img[y1:y2, x1:x2]
    face = cv2.resize(face, (mosaic_size, mosaic_size))
    face = cv2.resize(face, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)
    img[y1:y2, x1:x2] = face
    return img

def process_image(upload_path, processed_path, mosaic_level, ext, filename):
    # 顔検出モデルの初期化
    mtcnn = MTCNN(keep_all=True)

    # OpenCVで読み込み
    img_cv = cv2.imread(upload_path)
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb)

    # 顔検出（バウンディングボックス取得）
    boxes, _ = mtcnn.detect(img_pil)#複数の戻り値の内、1つだけ使うための記述方法。(右辺は複数の値(タプル)を返すため。)
        
    # 顔領域にモザイクを適用
    if boxes is not None:
        for box in boxes:
            img_cv = apply_mosaic(img_cv, box, mosaic_level)#3つ目の引数追記
        
    # ★拡張子分岐
    if ext in ['.jpg', '.jpeg']:
        cv2.imwrite(processed_path, img_cv, [cv2.IMWRITE_JPEG_QUALITY, 100])
    else:
        cv2.imwrite(processed_path, img_cv, [cv2.IMWRITE_PNG_COMPRESSION, 0])
    
		# 公開用URLを生成
    image_url = url_for('mosaic.download', filename_r=filename)#画像のダウンロード用URLを生成(/download/filename※filenameは[~.jpg])
		
    return image_url


@mosaic_bp.route('/', methods=['GET', 'POST'])
def index():
    # htmlに値を埋め込んでいるもの・変数は、全てにNoneなどを入れておかないと、処理を通さずにそのURLにアクセスした際にInternal Server Errorになる。
    error = None 
    image_url = None
    mosaic_level = 15  #初期値

    if request.method == 'POST':
        file = request.files.get('image')
        mosaic_level = int(request.form.get('mosaic_level_input1', 15))


        # 拡張子セキュリティ(Pillowで画像形式判定)
        error_msg = validate_image(file)
        if error_msg:
            return render_template('upload_mosaic.html', error=error_msg, mosaic_level_input1=mosaic_level)
        # ここまで

        ext = os.path.splitext(secure_filename(file.filename))[1].lower()#拡張子だけを安全に取り出す".jpg"のように。
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{ext}"#ファイルネームを変数に格納。/#extで拡張子を指定
       
        # os.path.join()は、「path形式で文字列結合をする」だけの関数で、ファイル自体はまだ存在しない。
        # original_path = "/root/app/mosaic_uploads/abcdefg-1234.png"  UPLOAD_FOLDER=/root/app/mosaic_uploads, new_filename=abcdefg-1234.png
        upload_path = os.path.join(UPLOAD_FOLDER, filename)
        processed_path = os.path.join(PROCESSED_FOLDER, filename)

        #
        session['image_path'] = upload_path													#★2回目はここから画像を取ってくる。
        session['image_filename'] = filename												#★2回目はここから画像を取ってくる。
        session['image_ext'] = ext                                  #★2回目はここから画像を取ってくる。
        #


        file.save(upload_path)#original_pathに処理前の画像を保存

        image_url = process_image(upload_path, processed_path, 34 - mosaic_level, ext, filename)#4~30の値を反転させてる(濃←→薄を薄←→濃にするため)

        return render_template('result_mosaic.html', image_url=image_url, mosaic_level_input2=mosaic_level)#POSTしたときだけ遷移するからこのインデント。
        
    return render_template('upload_mosaic.html')


@mosaic_bp.route('/tmp2', methods=['GET', 'POST'])
def index2():
    image_url = None
    mosaic_level = 15  #初期値
        
    if request.method == 'POST': #セッション切れてる状態で[送信ボタン]押した場合は、トップページに戻って、赤文字の表示も行う。
        if 'image_ext' not in session:
            flash('セッションが切れました。もう一度操作してください。')
            return redirect(url_for('mosaic.index'))
        
        ext = session.get('image_ext')

        mosaic_level = int(request.form.get('mosaic_level_input2', 15))

        file_id = str(uuid.uuid4())
        filename = session.get('image_filename')#★sessionから取り出し
       
        # os.path.join()は、「path形式で文字列結合をする」だけの関数で、ファイル自体はまだ存在しない。
        # original_path = "/root/app/mosaic_uploads/abcdefg-1234.png"  UPLOAD_FOLDER=/root/app/mosaic_uploads, new_filename=abcdefg-1234.png
        upload_path = session.get('image_path')#★sessionから取り出し
        processed_path = os.path.join(PROCESSED_FOLDER, filename)

        # file.save(upload_path)#original_pathに処理前の画像を保存→既に保存済みなのでいらない。

        image_url = process_image(upload_path, processed_path, 34 - mosaic_level, ext, filename)#4~30の値を反転させてる(濃←→薄を薄←→濃にするため)

    return render_template('result_mosaic.html', image_url=image_url, mosaic_level_input2=mosaic_level)#errorをNoneに変更

@mosaic_bp.route('/back_to_top')
def back():
    return redirect(url_for('mosaic.index'))#index()関数があるrouteに遷移するということ。


@mosaic_bp.route('/download/<filename_r>')
def download(filename_r):
    return send_from_directory(PROCESSED_FOLDER, filename_r)


@mosaic_bp.route('/reconnect', methods=['POST'])
def reconnect():
    session.clear()  #セッションを破棄
    return '', 204
