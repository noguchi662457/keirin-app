from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re

def scrape_todays_tracks():
    print("本日の開催場リストを取得しています（裏側で実行中）...")
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1920,1080')
    
    # 🌟 追加：クラウドのLinuxサーバーでChromeを動かすための必須設定 🌟
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    try:
        driver.get("https://keirin.jp/")
        time.sleep(3) 
        
        tracks = []
        html_text = driver.page_source
        soup = BeautifulSoup(html_text, 'html.parser')
        
        buttons = soup.find_all('button', class_=lambda c: c and 'slist' in c)
        for btn in buttons:
            tr = btn.find_parent('tr')
            if tr:
                kaisaichi_div = tr.find('div', class_=lambda c: c and 'kaisaichi' in c)
                if kaisaichi_div:
                    track_name = kaisaichi_div.text.strip()
                    if track_name and track_name not in tracks:
                        tracks.append(track_name)
        return tracks
    except Exception as e:
        print(f"開催場取得エラー: {e}")
        return []
    finally:
        driver.quit()

def scrape_racelist_smart_wait(track_name):
    print(f"「{track_name}」のデータ取得を開始します（裏側で実行中）...")
    options = Options()
    options.add_argument('--headless=new') 
    options.add_argument('--window-size=1920,1080')
    
    # 🌟 追加：クラウドのLinuxサーバーでChromeを動かすための必須設定 🌟
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    try:
        driver.get("https://keirin.jp/")
        time.sleep(3)
        
        xpath = f"//tr[.//div[contains(@class, 'kaisaichi') and contains(text(), '{track_name}')]]//button[contains(@class, 'slist')]"
        buttons = driver.find_elements(By.XPATH, xpath)
        clicked = False
        
        for btn in buttons:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", btn)
                clicked = True
                break
            except Exception:
                continue
        
        if not clicked:
            return None

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sllink_name"))
            )
        except Exception:
            return None

        html_text = driver.page_source
        soup = BeautifulSoup(html_text, 'html.parser')
        
        race_tables = soup.find_all('table', class_=lambda c: c and 'sltbl_02' in c)
        races_data = []
        
        for table in race_tables:
            header_td = table.find('td', class_='slva-top sltx-l')
            race_title = "不明なレース"
            if header_td:
                race_title = header_td.text.replace('\xa0', ' ').replace('\n', '').strip()

            racer_links = table.find_all('a', class_='sllink_name')
            racers = []
            
            for link in racer_links:
                player_name = link.text.replace("　", "").replace(" ", "").strip()
                parent_td = link.find_parent('td')
                car_td = None
                if parent_td:
                    prev_sibs = parent_td.find_previous_siblings('td')
                    for sib in prev_sibs:
                        class_list = sib.get('class')
                        if class_list and any('sltb-no' in c for c in class_list):
                            car_td = sib
                            break
                
                car_number = car_td.text.strip() if car_td else "-"
                racers.append({
                    "車番": car_number,
                    "選手名": player_name
                })
            
            if racers:
                races_data.append({
                    "race_title": race_title,
                    "racers": racers
                })
            
        return races_data

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None
    finally:
        driver.quit()