document.addEventListener('DOMContentLoaded', () => {
	const form = document.getElementById('form-upload-watermark') || document.querySelector('form-detect-watermark');

	if (form) {
    const fileInput = form.querySelector('input[name="image"]');//画像ファイル取得

    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (!file) {
        return;
      }
			

			//拡張子チェック(MINEタイプ)
      const validTypes = ['image/jpeg', 'image/png'];
      if (!validTypes.includes(file.type)) {
        alert('JPEGまたはPNG画像のみ選択できます');
        fileInput.value = '';
        return;
      }


			//ファイルサイズチェック※8GBの画像ファイルの電子透かし付与後のサイズが14GB程度。そのため、各ページで画像サイズ上限を変更
			if(form.id=="form-upload-watermark"){				
				const maxSize = 8*1024*1024;
				if(file.size > maxSize){
					alert('画像サイズは8MB以下にしてください');
					fileInput.value = '';
					return;
				}
			}else{
				const maxSize = 14*1024*1024;
				if(file.size > maxSize){
					alert('画像サイズは14MB以下にしてください');
					fileInput.value = '';
					return;
				}
			}

    });
	}
});


