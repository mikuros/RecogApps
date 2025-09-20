import numpy as np
import cv2
import hashlib
import uuid
import time#開発用
import logging#開発用

# 中周波数帯：ジグザグスキャン順 8〜14番目 ※添え字は0からで、slice(i,j-1)なので(8,15)になる
# ※埋め込みすぎて重くなってるから、埋め込み量を半分にする。
MIDDLE_FREQ_RANGE = slice(8, 15)  # Pythonの範囲指定 slice(含む, 含まない)
STRANGTH = 2.0 #※1.5~2ぐらいがいい。2でも全然見えない。それ以上だとちょっと見える。



def generate_secret_key():
    #ランダムな16文字の16進数キーを生成
    return uuid.uuid4().hex[:16]

def seed_from_key(key: str) -> int:
    #キーから32bitの乱数シードを生成
    h = hashlib.sha256(key.encode()).hexdigest()
    return int(h, 16) % (2**32)

def zigzag_map(size=8):
    #JPEG標準ジグザグスキャン順インデックスを返す（(i,j)座標のリスト)
    index_map = []
    for s in range(2 * size - 1):
        if s % 2 == 0:
            for i in range(s + 1):
                x, y = i, s - i
                if x < size and y < size:
                    index_map.append((x, y))
        else:
            for i in range(s + 1):
                x, y = s - i, i
                if x < size and y < size:
                    index_map.append((x, y))
    return index_map  #長さ64のリスト



def embed_with_key(img: np.ndarray, key: str) -> np.ndarray:
    seed = seed_from_key(key)
    rng = np.random.default_rng(seed)

    img_f = img.astype(np.float32)
    channels = cv2.split(img_f)#BGR各チャンネル(青・緑・赤)に分割※カラー画像対応用の下処理
    watermarked = []    

    zz_map = zigzag_map()  #8×8固定

    """ ◆乱数生成を先におこなって配列に格納しとく """
    h,w =img.shape[:2]            #高さ幅をループ外で取得。画像サイズと周波数領域サイズは同じため。
    max_blocks = int((h*w*7/64))  #★画像サイズに合わせてここを変動させる。1ブロック辺り7乱数必要。
    rand_vals = rng.normal(0, 1, size=max_blocks)#sizeは生成する乱数の個数。
    list_cnt=0                    #1次元乱数配列(リスト)rand_valsの添え字
    """ ◆ここまで """

    for ch in channels:#BGRで3チャンネルあるので、3回回す。
        h, w = ch.shape
        # ch_dct = np.zeros_like(ch)#ここで空の画像を用意して、処理したらそのパーツを埋め込む(パズルみたいな)方式だったため、未処理部分が黒くなってしまった。
        ch_dct = ch.copy()
        tmp_embed=0             #★埋め込むブロック数を1/4にして処理不可を減らす
        updates = []            #★★修正★★

        for i in range(0, h-h%8, 8):#range(start, stop, step)なので、stop = h - h % 8 ← h を 8 で割り切れる直前の値までやるということ。端には埋め込まない。それは問題なし。
            for j in range(0, w-w%8, 8):#同様
                tmp_embed+=1
                if tmp_embed % 4 != 0:#★4回に1回しか埋め込まないようにした。
                    continue
                else:     #★tmp=4の時    
                    block = ch[i:i+8, j:j+8]#(1)numpy配列から8×8を取り出す。
                    dct_block = cv2.dct(block)#dct変換/離散コサイン変換(空間領域(画像)から周波数領域(DCT係数)に変換)

                    for (u, v) in zz_map[MIDDLE_FREQ_RANGE]:
                        dct_block[u, v] += rand_vals[list_cnt]* STRANGTH#◆既に作ってある乱数配列を使用。
                        list_cnt+=1                           					#◆1次元乱数配列の添え字をカウントアップ
                        # dct_blockは8×8になっており、zz_mapは、周波数領域8×8の[ジグザグ順で8~14番目]の範囲を探索するような添え字のmapを持つ。
                        # [3,0][2,1][1,2][0,3][0,4][1,3][2,2][3,1][4,0][5,0][4,1][3,2][2,3][1,4][0,5]
                        # この添え字を持つdct_blockにノイズを付加してる。
                    
                        # if tmp<20:
                        # test_tmp(u,v)検査用

                    idct_block = cv2.idct(dct_block)#逆離散コサイン変換(周波数領域→空間領域に戻す) ※ノイズが画像に微妙な形で反映されることが分かる。
                    updates.append((i, j, idct_block))##★★修正★★
        for i, j, block in updates:                   ##★★修正★★
            ch_dct[i:i+8, j:j+8] = block              ##★★修正★★

        watermarked.append(ch_dct)#1チャンネルの処理が終わったので、リストに追加(BGRの順番)

    merged = cv2.merge(watermarked)#3チャンネル追加し終わったので、マージしてカラー画像に。(最初の画像と比べると、透かしが追加されている以外違いはない)
    
    return np.clip(merged, 0, 255).astype(np.uint8)

def detect_with_key(img: np.ndarray, key: str) -> bool:
    """start_time = time.time()"""    #デバッグ用
    seed = seed_from_key(key)
    rng = np.random.default_rng(seed)

    img_f = img.astype(np.float32)
    channels = cv2.split(img_f)

    zz_map = zigzag_map()

    score = 0.0
    coeff_cnt = 0#スコアに寄与したDCT係数の数をカウント

    """ ◆乱数生成を先におこなって配列に格納しとく """
    h,w =img.shape[:2]            #高さ幅をループ外で取得。画像サイズと周波数領域サイズは同じため。
    max_blocks = int((h*w*7/64))  #★画像サイズに合わせてここを変動させる。1ブロック辺り7乱数必要。
    rand_vals = rng.normal(0, 1, size=max_blocks)#sizeは生成する乱数の個数。
    list_cnt=0                    #1次元乱数配列(リスト)rand_valsの添え字
    """ ◆ここまで """


    for ch in channels:
        h, w = ch.shape
        tmp_detect=0             #★埋め込むブロック数を1/4にして処理負荷を減らす

        for i in range(0, h-h%8, 8):
            for j in range(0, w-w%8, 8):
                tmp_detect+=1
                if tmp_detect % 4 != 0:#★4回に1回しか埋め込まないようにした。
                    continue
                else:            #★tmp=4の時    
                    block = ch[i:i+8, j:j+8]
                    dct_block = cv2.dct(block)

                    for (u, v) in zz_map[MIDDLE_FREQ_RANGE]:
                        score += dct_block[u, v] * rand_vals[list_cnt] * STRANGTH#◆既に作った乱数配列を使用。
                        coeff_cnt += 1
                        list_cnt+=1                                   #◆1次元乱数配列の添え字をカウントアップ

		""" タイム(デバッグ用) 
    end_time = time.time()                           
    sa = end_time - start_time                       
    print(f"時間{sa}")                               
		"""

    score /= coeff_cnt#正規化
    """print(f"鍵 {key} の相関スコア: {score:.3f}")""" #デバッグ用
    return score > 0.2#閾値を0.2に設定。
