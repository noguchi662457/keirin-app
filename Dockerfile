FROM python:3.11-slim

# クラウドサーバー上にGoogle Chromeを自動インストールする魔法の呪文
RUN apt-get update && apt-get install -y wget gnupg2 curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && sh -c 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 作業フォルダの設定
WORKDIR /app

# 持ち物リストを読み込んでPythonの部品をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリのファイルをすべてコピー
COPY . .

# Gunicorn（本番用サーバー）を起動。スクレイピング待ち時間を考慮してタイムアウトを120秒に設定
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "120"]