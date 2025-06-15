# ベースとなるOSとPythonのバージョンを指定
FROM python:3.11-slim

# コンテナ内での作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコンテナにコピー
COPY requirements.txt .

# requirements.txtに書かれたライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトの他のファイルもすべてコンテナにコピー
COPY . .

# gunicornでアプリを起動するコマンド
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:app"]
