document.addEventListener('DOMContentLoaded', () => {
	//新しくタブを開いて接続したときセッションを初期化する(ページの再読み込みではセッションは維持される)(※共通処理)
	if (!sessionStorage.getItem('visited')) {
    sessionStorage.setItem('visited', 'true');
      fetch('/reconnect', { method: 'POST' });
  }

	//ファイル入力チェック(index.html専用)
	const imageInput = document.getElementById('image');
	if(imageInput){
  	//拡張子・サイズのチェック
  	imageInput.addEventListener('change', () => {
    	const file = imageInput.files[0];
    	if (!file) return;

    	const validTypes = ['image/jpeg', 'image/png'];
    	if (!validTypes.includes(file.type)) {
      	alert('JPEGまたはPNG画像のみ選択できます');
      	imageInput.value = '';
      	return;
    	}

    	const maxSize = 16 * 1024 * 1024;
    	if (file.size > maxSize) {
    	  alert('画像サイズは16MB以下にしてください');
    	  imageInput.value = '';
    	  return;
    	}
  	});
	}
});



