from flask import Flask, render_template, request
# 先ほど作った「scrape_todays_tracks」を新しくインポートします
from scrape_test import scrape_racelist_smart_wait, scrape_todays_tracks
import urllib.request
import csv
import io
import re

app = Flask(__name__)

# 🌟 ここにコピーしたCSVのURLを貼り付けてください 🌟
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRR5wiFHX2u1-44p1Hc4a7_BV3TeDMWxCzyKi6Zy3E_IQVqrhnTGYzsNQ7gQJ9d0Uy091bvEj2T83oA/pub?output=csv"

# 🌟 本日の開催場を一時保存するリスト（毎回ブラウザを開くと遅いため） 🌟
TODAYS_TRACKS = []

def get_youtube_embed_url(youtube_url):
    if not youtube_url:
        return None
    pattern = r'(?:v=|youtu\.be/)([^&?]+)'
    match = re.search(pattern, youtube_url)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/embed/{video_id}"
    return None

def get_sheet_data(url):
    sheet_dict = {}
    if not url.startswith("http"):
        return sheet_dict
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            csv_data = response.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_data))
        for row in reader:
            if "選手名" in row:
                name_key = row["選手名"].replace("　", "").replace(" ", "").strip()
                sheet_dict[name_key] = row
    except Exception as e:
        print(f"シート読み込みエラー: {e}")
    return sheet_dict

@app.route("/", methods=["GET", "POST"])
def index():
    global TODAYS_TRACKS # 記憶しておいたリストを使う宣言
    results = None
    track_name = None

    # アプリを起動して最初にアクセスした時だけ、今日の開催場を取得する
    if not TODAYS_TRACKS:
        TODAYS_TRACKS = scrape_todays_tracks()

    if request.method == "POST":
        # クリックされたボタンの value（競輪場名）を受け取る
        track_name = request.form.get("track_name")
        
        if track_name:
            scraped_data = scrape_racelist_smart_wait(track_name)
            sheet_data = get_sheet_data(CSV_URL)
            
            if scraped_data:
                for race in scraped_data:
                    for racer in race['racers']:
                        racer_name = racer['選手名']
                        if racer_name in sheet_data:
                            racer['sheet_info'] = sheet_data[racer_name]
                            yt_url = racer['sheet_info'].get('YouTubeリンク', '')
                            racer['sheet_info']['embed_url'] = get_youtube_embed_url(yt_url)
                        else:
                            racer['sheet_info'] = None
                results = scraped_data

    # TODAYS_TRACKS も画面側に渡してボタンを生成させる
    return render_template("index.html", results=results, track_name=track_name, todays_tracks=TODAYS_TRACKS)

if __name__ == "__main__":
    app.run(debug=True)