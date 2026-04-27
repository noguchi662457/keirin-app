from flask import Flask, render_template, request
from scrape_test import scrape_racelist_smart_wait, scrape_todays_tracks
import urllib.request
import csv
import io
import re
import threading
from datetime import datetime, time as dt_time, timezone, timedelta # 🌟 timezone と timedelta を追加

# 🌟 サーバーに「日本時間（JST）」を教える設定
JST = timezone(timedelta(hours=+9), 'JST')

app = Flask(__name__)

# 🌟 ご自身のスプレッドシートのCSV URL
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRR5wiFHX2u1-44p1Hc4a7_BV3TeDMWxCzyKi6Zy3E_IQVqrhnTGYzsNQ7gQJ9d0Uy091bvEj2T83oA/pub?output=csv"

# 状態管理用の変数
TODAYS_TRACKS = []
RACE_CACHE = {} 
IS_FETCHING = False 
LAST_UPDATE_DATE = None 

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

def background_fetch_all():
    """裏側でデータを一括取得する"""
    global TODAYS_TRACKS, RACE_CACHE, IS_FETCHING, LAST_UPDATE_DATE
    if IS_FETCHING:
        return
    IS_FETCHING = True
    
    try:
        # 🌟 日本時間でログを出力
        print(f"[裏方作業] {datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')} 日本時間でデータ更新を開始します...")
        tracks = scrape_todays_tracks()
        TODAYS_TRACKS = tracks
        
        sheet_data = get_sheet_data(CSV_URL)
        new_cache = {} 
        
        for track in tracks:
            scraped_data = scrape_racelist_smart_wait(track)
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
                new_cache[track] = scraped_data
        
        RACE_CACHE = new_cache
        LAST_UPDATE_DATE = datetime.now(JST).date() # 🌟 日本時間の日付を記録
        print(f"[裏方作業] ✨ {LAST_UPDATE_DATE} のデータ準備がすべて完了しました！")
    except Exception as e:
        print(f"[裏方作業エラー]: {e}")
    finally:
        IS_FETCHING = False

@app.route("/", methods=["GET", "POST"])
def index():
    global TODAYS_TRACKS, RACE_CACHE, IS_FETCHING, LAST_UPDATE_DATE

    # 🌟 現在時刻を「日本時間」で取得するように変更
    now = datetime.now(JST)
    today = now.date()
    update_time = dt_time(8, 0) 

    # 自動更新判定ロジック
    should_update = False
    if LAST_UPDATE_DATE is None:
        should_update = True
    elif today > LAST_UPDATE_DATE and now.time() >= update_time:
        should_update = True

    if should_update and not IS_FETCHING:
        print("🌟 午前8時(日本時間)を過ぎたため、最新データへの更新を開始します")
        TODAYS_TRACKS = []
        thread = threading.Thread(target=background_fetch_all)
        thread.start()

    results = None
    track_name = None

    if request.method == "POST":
        track_name = request.form.get("track_name")
        if track_name and track_name in RACE_CACHE:
            results = RACE_CACHE[track_name]
        elif track_name:
            scraped_data = scrape_racelist_smart_wait(track_name)
            sheet_data = get_sheet_data(CSV_URL)
            if scraped_data:
                for race in scraped_data:
                    for racer in race['racers']:
                        racer_name = racer['選手名']
                        if racer_name in sheet_data:
                            racer['sheet_info'] = sheet_data[racer_name]
                            racer['sheet_info']['embed_url'] = get_youtube_embed_url(racer['sheet_info'].get('YouTubeリンク', ''))
                        else:
                            racer['sheet_info'] = None
                results = scraped_data

    return render_template("index.html", results=results, track_name=track_name, todays_tracks=TODAYS_TRACKS)

if __name__ == "__main__":
    app.run(debug=True)
