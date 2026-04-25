from flask import Flask, render_template, request
from scrape_test import scrape_racelist_smart_wait, scrape_todays_tracks
import urllib.request
import csv
import io
import re
import threading # 🌟 奥義の鍵：マルチスレッド（並行処理）をインポート

app = Flask(__name__)

# 🌟 ここにご自身のスプレッドシートのCSV URLを貼り付けてください
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRR5wiFHX2u1-44p1Hc4a7_BV3TeDMWxCzyKi6Zy3E_IQVqrhnTGYzsNQ7gQJ9d0Uy091bvEj2T83oA/pub?output=csv"

TODAYS_TRACKS = []
# 🌟 奥義2：全競輪場のデータを保存しておく「キャッシュ（記憶領域）」
RACE_CACHE = {} 
# 🌟 奥義2：裏側でデータ取得中かどうかを判定するフラグ
IS_FETCHING = False 

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
    """🌟 サーバーの裏側でコッソリ全データを集めておく関数 🌟"""
    global TODAYS_TRACKS, RACE_CACHE, IS_FETCHING
    if IS_FETCHING:
        return
    IS_FETCHING = True
    
    try:
        print("[裏方作業] 本日の開催場と全レースデータの先回り取得を開始します...")
        tracks = scrape_todays_tracks()
        TODAYS_TRACKS = tracks
        
        sheet_data = get_sheet_data(CSV_URL)
        
        for track in tracks:
            print(f"[裏方作業] {track} のデータを事前取得中...")
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
                
                # 🌟 取得したデータを記憶領域（メモリ）に保存！
                RACE_CACHE[track] = scraped_data
        
        print("[裏方作業] ✨ すべてのデータの事前準備が完了しました！")
    except Exception as e:
        print(f"[裏方作業エラー]: {e}")
    finally:
        IS_FETCHING = False

@app.route("/", methods=["GET", "POST"])
def index():
    global TODAYS_TRACKS, RACE_CACHE, IS_FETCHING

    # 誰もアクセスしていない最初の状態なら、裏方さんに作業を指示する
    if not TODAYS_TRACKS and not IS_FETCHING:
        thread = threading.Thread(target=background_fetch_all)
        thread.start()

    results = None
    track_name = None

    if request.method == "POST":
        track_name = request.form.get("track_name")
        
        if track_name:
            # 🌟 奥義2発動：記憶領域（キャッシュ）にデータがあれば、1秒以下で返す！
            if track_name in RACE_CACHE:
                print(f"✨ {track_name}のデータをキャッシュから一瞬で返します！")
                results = RACE_CACHE[track_name]
            else:
                # 万が一まだ裏方さんが取得していなかった場合は、その場で取りに行く
                print(f"⚠️ {track_name}はまだ準備中だったため、今から取得します...")
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
                    RACE_CACHE[track_name] = scraped_data # ついでに記憶しておく
                    results = scraped_data

    return render_template("index.html", results=results, track_name=track_name, todays_tracks=TODAYS_TRACKS)

if __name__ == "__main__":
    app.run(debug=True)
