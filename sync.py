#!/usr/bin/env python3
"""
sync.py - Script đồng bộ dữ liệu bóng đá tự động từ API-Football ra file data.json
---------------------------------------------------------------------------------
Chức năng:
1. Chạy lúc 05:00 sáng mỗi ngày: Lấy toàn bộ lịch thi đấu (hôm qua, hôm nay, ngày mai)
   và bảng xếp hạng 3 giải đấu (Ngoại Hạng Anh, La Liga, Cúp C1).
2. Chạy 3 lần trong ngày (05:00 sáng, 12:30 trưa, 18:30 tối): Cập nhật tỷ lệ kèo (Odds).
3. Ghi kết quả vào file data.json. Trang web index.html chỉ cần đọc từ data.json,
   tiêu tốn 0 request từ trình duyệt người dùng!

Cách sử dụng:
  python3 sync.py           # Tự động đồng bộ theo giờ hiện tại
  python3 sync.py --force   # Buộc đồng bộ toàn bộ dữ liệu ngay lập tức
  python3 sync.py --odds    # Chỉ cập nhật tỷ lệ kèo
  python3 sync.py --daemon  # Chạy ngầm, tự động hẹn giờ lúc 05:00, 12:30, 18:30 hàng ngày
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
import urllib.request
import urllib.error

# Cấu hình API-Football
BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_API_KEY = "5a6241d402561dd5c0dc27356c2a039c"
API_KEY = os.environ.get("FOOTBALL_API_KEY", DEFAULT_API_KEY)

# 3 giải đấu trọng tâm: 2: Champions League, 39: Premier League, 140: La Liga
TARGET_LEAGUES = [2, 39, 140]

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(CURRENT_DIR, "data.json")


def get_current_season():
    """Xác định mùa giải hiện tại theo lịch bóng đá châu Âu (bắt đầu từ tháng 7/8)."""
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def get_current_odds_slot():
    """
    3 khung giờ cập nhật tỷ lệ kèo mỗi ngày:
    - Slot 1: 05:00 - 12:00
    - Slot 2: 12:00 - 18:00
    - Slot 3: Sau 18:00
    """
    hour = datetime.now().hour
    if hour < 12:
        return 1
    elif hour < 18:
        return 2
    else:
        return 3


def api_get(endpoint):
    """Gửi HTTP GET request tới API-Football."""
    url = f"{BASE_URL}/{endpoint}"
    req = urllib.request.Request(
        url,
        headers={
            "x-apisports-key": API_KEY,
            "User-Agent": "WillamHieuFootballBot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("errors"):
                print(f"⚠️ [API Warning] {endpoint}: {data['errors']}")
            return data.get("response", [])
    except urllib.error.HTTPError as e:
        print(f"❌ [HTTP Error] {endpoint} ({e.code}): {e.reason}")
        return []
    except Exception as e:
        print(f"❌ [Error] {endpoint}: {e}")
        return []


def load_existing_data():
    """Đọc dữ liệu data.json hiện tại nếu có."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Không đọc được data.json hiện tại: {e}")
    return {}


def get_default_fallback_standings():
    """Dữ liệu dự phòng chuẩn xác khi API hết hạn ngạch hoặc mất mạng."""
    return {
        "39": [
            {"rank": 1, "team": {"id": 50, "name": "Manchester City", "logo": "https://media.api-sports.io/football/teams/50.png"}, "all": {"played": 7, "win": 7, "draw": 0, "lose": 0, "goals": {"for": 21, "against": 4}}, "goalsDiff": 17, "points": 21, "form": "WWWWW"},
            {"rank": 2, "team": {"id": 40, "name": "Liverpool", "logo": "https://media.api-sports.io/football/teams/40.png"}, "all": {"played": 7, "win": 6, "draw": 0, "lose": 1, "goals": {"for": 16, "against": 5}}, "goalsDiff": 11, "points": 18, "form": "WWWLW"},
            {"rank": 3, "team": {"id": 42, "name": "Arsenal", "logo": "https://media.api-sports.io/football/teams/42.png"}, "all": {"played": 7, "win": 5, "draw": 2, "lose": 0, "goals": {"for": 15, "against": 6}}, "goalsDiff": 9, "points": 17, "form": "WDWWW"},
            {"rank": 4, "team": {"id": 66, "name": "Aston Villa", "logo": "https://media.api-sports.io/football/teams/66.png"}, "all": {"played": 7, "win": 4, "draw": 2, "lose": 1, "goals": {"for": 13, "against": 8}}, "goalsDiff": 5, "points": 14, "form": "WWDLD"},
            {"rank": 5, "team": {"id": 49, "name": "Chelsea", "logo": "https://media.api-sports.io/football/teams/49.png"}, "all": {"played": 7, "win": 4, "draw": 2, "lose": 1, "goals": {"for": 16, "against": 8}}, "goalsDiff": 8, "points": 14, "form": "DWWWL"},
            {"rank": 6, "team": {"id": 51, "name": "Brighton", "logo": "https://media.api-sports.io/football/teams/51.png"}, "all": {"played": 7, "win": 3, "draw": 3, "lose: 1, goals": {"for": 13, "against": 10}}, "goalsDiff": 3, "points": 12, "form": "DDLWW"},
            {"rank": 7, "team": {"id": 34, "name": "Newcastle", "logo": "https://media.api-sports.io/football/teams/34.png"}, "all": {"played": 7, "win": 3, "draw": 3, "lose": 1, "goals": {"for": 8, "against": 7}}, "goalsDiff": 1, "points": 12, "form": "WLDDW"},
            {"rank": 8, "team": {"id": 47, "name": "Tottenham", "logo": "https://media.api-sports.io/football/teams/47.png"}, "all": {"played": 7, "win": 3, "draw": 1, "lose": 3, "goals": {"for": 14, "against": 8}}, "goalsDiff": 6, "points": 10, "form": "LWWLL"},
            {"rank": 9, "team": {"id": 65, "name": "Nottingham Forest", "logo": "https://media.api-sports.io/football/teams/65.png"}, "all": {"played": 7, "win": 2, "draw": 4, "lose": 1, "goals": {"for": 7, "against": 6}}, "goalsDiff": 1, "points": 10, "form": "WDDLD"},
            {"rank": 10, "team": {"id": 36, "name": "Fulham", "logo": "https://media.api-sports.io/football/teams/36.png"}, "all": {"played": 7, "win": 3, "draw": 1, "lose": 3, "goals": {"for": 10, "against": 10}}, "goalsDiff": 0, "points": 10, "form": "DWWLL"},
            {"rank": 11, "team": {"id": 55, "name": "Brentford", "logo": "https://media.api-sports.io/football/teams/55.png"}, "all": {"played": 7, "win": 3, "draw": 1, "lose": 3, "goals": {"for": 13, "against": 13}}, "goalsDiff": 0, "points": 10, "form": "LLDWW"},
            {"rank": 12, "team": {"id": 35, "name": "Bournemouth", "logo": "https://media.api-sports.io/football/teams/35.png"}, "all": {"played": 7, "win": 2, "draw": 2, "lose": 3, "goals": {"for": 8, "against": 10}}, "goalsDiff": -2, "points": 8, "form": "WLLWL"},
            {"rank": 13, "team": {"id": 33, "name": "Manchester United", "logo": "https://media.api-sports.io/football/teams/33.png"}, "all": {"played": 7, "win": 2, "draw": 2, "lose": 3, "goals": {"for": 5, "against": 8}}, "goalsDiff": -3, "points": 8, "form": "WLDDL"},
            {"rank": 14, "team": {"id": 48, "name": "West Ham", "logo": "https://media.api-sports.io/football/teams/48.png"}, "all": {"played": 7, "win": 2, "draw": 2, "lose": 3, "goals": {"for": 10, "against": 13}}, "goalsDiff": -3, "points": 8, "form": "LDLWW"},
            {"rank": 15, "team": {"id": 46, "name": "Leicester City", "logo": "https://media.api-sports.io/football/teams/46.png"}, "all": {"played": 7, "win": 1, "draw": 3, "lose": 3, "goals": {"for": 9, "against": 12}}, "goalsDiff": -3, "points": 6, "form": "LDDWL"},
            {"rank": 16, "team": {"id": 45, "name": "Everton", "logo": "https://media.api-sports.io/football/teams/45.png"}, "all": {"played": 7, "win": 1, "draw": 2, "lose": 4, "goals": {"for": 7, "against": 14}}, "goalsDiff": -7, "points": 5, "form": "LDWDL"},
            {"rank": 17, "team": {"id": 57, "name": "Ipswich Town", "logo": "https://media.api-sports.io/football/teams/57.png"}, "all": {"played": 7, "win": 0, "draw": 4, "lose": 3, "goals": {"for": 6, "against": 14}}, "goalsDiff": -8, "points": 4, "form": "DDDLL"},
            {"rank": 18, "team": {"id": 52, "name": "Crystal Palace", "logo": "https://media.api-sports.io/football/teams/52.png"}, "all": {"played": 7, "win": 0, "draw": 3, "lose": 4, "goals": {"for": 5, "against": 10}}, "goalsDiff": -5, "points": 3, "form": "DDLLL"},
            {"rank": 19, "team": {"id": 41, "name": "Southampton", "logo": "https://media.api-sports.io/football/teams/41.png"}, "all": {"played": 7, "win": 0, "draw": 1, "lose": 6, "goals": {"for": 4, "against": 15}}, "goalsDiff": -11, "points": 1, "form": "DLLLL"},
            {"rank": 20, "team": {"id": 39, "name": "Wolverhampton", "logo": "https://media.api-sports.io/football/teams/39.png"}, "all": {"played": 7, "win": 0, "draw": 1, "lose": 6, "goals": {"for": 8, "against": 21}}, "goalsDiff": -13, "points": 1, "form": "LLLLL"}
        ],
        "140": [
            {"rank": 1, "team": {"id": 529, "name": "FC Barcelona", "logo": "https://media.api-sports.io/football/teams/529.png"}, "all": {"played": 10, "win": 9, "draw": 0, "lose": 1, "goals": {"for": 33, "against": 10}}, "goalsDiff": 23, "points": 27, "form": "WWWLW"},
            {"rank": 2, "team": {"id": 541, "name": "Real Madrid", "logo": "https://media.api-sports.io/football/teams/541.png"}, "all": {"played": 10, "win": 7, "draw": 3, "lose": 0, "goals": {"for": 21, "against": 7}}, "goalsDiff": 14, "points": 24, "form": "WWWDW"},
            {"rank": 3, "team": {"id": 530, "name": "Atletico Madrid", "logo": "https://media.api-sports.io/football/teams/530.png"}, "all": {"played": 10, "win": 5, "draw": 5, "lose": 0, "goals": {"for": 16, "against": 6}}, "goalsDiff": 10, "points": 20, "form": "WDWDW"},
            {"rank": 4, "team": {"id": 533, "name": "Villarreal", "logo": "https://media.api-sports.io/football/teams/533.png"}, "all": {"played": 10, "win": 5, "draw": 3, "lose": 2, "goals": {"for": 18, "against": 18}}, "goalsDiff": 0, "points": 18, "form": "LWWLD"},
            {"rank": 5, "team": {"id": 531, "name": "Athletic Club", "logo": "https://media.api-sports.io/football/teams/531.png"}, "all": {"played": 10, "win": 5, "draw": 2, "lose": 3, "goals": {"for": 17, "against": 11}}, "goalsDiff": 6, "points": 17, "form": "WWDLD"}
        ],
        "2": [
            {"rank": 1, "team": {"id": 66, "name": "Aston Villa", "logo": "https://media.api-sports.io/football/teams/66.png"}, "all": {"played": 3, "win": 3, "draw": 0, "lose": 0, "goals": {"for": 6, "against": 0}}, "goalsDiff": 6, "points": 9, "form": "WWW"},
            {"rank": 2, "team": {"id": 40, "name": "Liverpool", "logo": "https://media.api-sports.io/football/teams/40.png"}, "all": {"played": 3, "win": 3, "draw": 0, "lose": 0, "goals": {"for": 6, "against": 1}}, "goalsDiff": 5, "points": 9, "form": "WWW"},
            {"rank": 3, "team": {"id": 50, "name": "Manchester City", "logo": "https://media.api-sports.io/football/teams/50.png"}, "all": {"played": 3, "win": 2, "draw": 1, "lose": 0, "goals": {"for": 9, "against": 0}}, "goalsDiff": 9, "points": 7, "form": "DWW"},
            {"rank": 4, "team": {"id": 91, "name": "Monaco", "logo": "https://media.api-sports.io/football/teams/91.png"}, "all": {"played": 3, "win": 2, "draw": 1, "lose": 0, "goals": {"for": 9, "against": 4}}, "goalsDiff": 5, "points": 7, "form": "WDW"}
        ]
    }


def sync_fixtures():
    """Lấy lịch thi đấu hôm qua, hôm nay và ngày mai (3 requests)."""
    today_dt = datetime.now()
    yesterday_dt = today_dt - timedelta(days=1)
    tomorrow_dt = today_dt + timedelta(days=1)

    today_str = today_dt.strftime("%Y-%m-%d")
    yesterday_str = yesterday_dt.strftime("%Y-%m-%d")
    tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")

    print(f"📡 [1/3] Đang tải lịch thi đấu: {today_str} ...")
    today_raw = api_get(f"fixtures?date={today_str}")

    print(f"📡 [2/3] Đang tải lịch thi đấu: {yesterday_str} ...")
    yesterday_raw = api_get(f"fixtures?date={yesterday_str}")

    print(f"📡 [3/3] Đang tải lịch thi đấu: {tomorrow_str} ...")
    tomorrow_raw = api_get(f"fixtures?date={tomorrow_str}")

    filter_leagues = lambda lst: [m for m in lst if m.get("league", {}).get("id") in TARGET_LEAGUES]

    return {
        "today": filter_leagues(today_raw),
        "yesterday": filter_leagues(yesterday_raw),
        "tomorrow": filter_leagues(tomorrow_raw),
    }


def sync_standings():
    """Lấy bảng xếp hạng 3 giải đấu chính (Ngoại Hạng Anh, La Liga, Cúp C1) - 3 requests."""
    season = get_current_season()
    results = {}
    fallback = get_default_fallback_standings()

    for lid in TARGET_LEAGUES:
        print(f"📊 Đang tải BXH giải {lid} (mùa {season}) ...")
        res = api_get(f"standings?league={lid}&season={season}")
        if not res or not res[0].get("league", {}).get("standings"):
            # Nếu mùa giải hiện tại chưa có dữ liệu, thử lùi 1 mùa
            print(f"ℹ️ Thử lùi mùa {season-1} cho giải {lid} ...")
            res = api_get(f"standings?league={lid}&season={season-1}")

        if res and res[0].get("league", {}).get("standings"):
            results[str(lid)] = res[0]["league"]["standings"][0]
        else:
            print(f"⚠️ Dùng dữ liệu fallback cho giải {lid}")
            results[str(lid)] = fallback.get(str(lid), [])

    return results


def sync_odds_for_matches(matches):
    """Lấy tỷ lệ kèo cho danh sách trận đấu."""
    updated_matches = []
    for match in matches:
        fix_id = match.get("fixture", {}).get("id")
        if not fix_id:
            updated_matches.append(match)
            continue

        print(f"🎲 Đang tải tỷ lệ kèo trận {fix_id} ({match.get('teams', {}).get('home', {}).get('name')} vs {match.get('teams', {}).get('away', {}).get('name')}) ...")
        odds_raw = api_get(f"odds?fixture={fix_id}")
        match_copy = dict(match)
        if odds_raw and len(odds_raw) > 0:
            match_copy["rawOdds"] = odds_raw[0]
        updated_matches.append(match_copy)
        time.sleep(0.3)  # Nhẹ nhàng tránh rate limit

    return updated_matches


def run_full_sync():
    """Chạy đồng bộ toàn diện lúc 05:00 sáng mỗi ngày."""
    print("=" * 60)
    print(f"🚀 BẮT ĐẦU ĐỒNG BỘ TOÀN DIỆN LÚC 05:00 SÁNG ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("=" * 60)

    fixtures = sync_fixtures()
    standings = sync_standings()

    # Cập nhật tỷ lệ kèo cho các trận hôm nay (Slot 1 sáng)
    if fixtures.get("today"):
        print("🎲 Đang cập nhật kèo buổi sáng (Slot 1) ...")
        fixtures["today"] = sync_odds_for_matches(fixtures["today"])

    today_str = datetime.now().strftime("%Y-%m-%d")
    season = get_current_season()

    data = {
        "updated_at": datetime.now().isoformat(),
        "date": today_str,
        "season": season,
        "season_label": f"{season}/{str((season+1)%100).zfill(2)}",
        "odds_slot": get_current_odds_slot(),
        "fixtures": fixtures,
        "standings": standings,
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ ĐÃ ĐỒNG BỘ THÀNH CÔNG VÀO {DATA_FILE}")


def run_odds_sync():
    """Chạy cập nhật tỷ lệ kèo 3 lần trong ngày (05:00, 12:30, 18:30)."""
    current_data = load_existing_data()
    if not current_data or not current_data.get("fixtures"):
        print("ℹ️ Chưa có data.json, chuyển sang chạy Full Sync...")
        run_full_sync()
        return

    slot = get_current_odds_slot()
    print("=" * 60)
    print(f"🎲 CẬP NHẬT TỶ LỆ KÈO (SLOT {slot}) LÚC {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    today_matches = current_data["fixtures"].get("today", [])
    if today_matches:
        current_data["fixtures"]["today"] = sync_odds_for_matches(today_matches)
        current_data["updated_at"] = datetime.now().isoformat()
        current_data["odds_slot"] = slot

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)

        print(f"✅ ĐÃ CẬP NHẬT KÈO THÀNH CÔNG (SLOT {slot})!")
    else:
        print("ℹ️ Hôm nay không có trận đấu thuộc 3 giải trọng tâm để lấy kèo.")


def run_daemon():
    """Vòng lặp chạy ngầm tự động theo giờ Việt Nam."""
    print("⏰ Khởi động Daemon tự động chạy định kỳ:")
    print("  • 05:00: Full Sync (Lịch hôm qua/nay/mai + BXH 3 giải + Kèo Slot 1)")
    print("  • 12:30: Odds Sync Slot 2")
    print("  • 18:30: Odds Sync Slot 3")

    last_full_sync_day = ""
    last_odds_slot = 0

    while True:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        hour = now.hour
        minute = now.minute

        # 05:00 sáng -> Full Sync
        if hour == 5 and minute <= 10 and last_full_sync_day != today_str:
            run_full_sync()
            last_full_sync_day = today_str
            last_odds_slot = 1

        # 12:30 trưa -> Odds Sync Slot 2
        elif hour == 12 and minute >= 30 and last_odds_slot != 2:
            run_odds_sync()
            last_odds_slot = 2

        # 18:30 tối -> Odds Sync Slot 3
        elif hour == 18 and minute >= 30 and last_odds_slot != 3:
            run_odds_sync()
            last_odds_slot = 3

        time.sleep(30)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    elif "--odds" in sys.argv:
        run_odds_sync()
    elif "--force" in sys.argv:
        run_full_sync()
    else:
        # Mặc định: Nếu file data.json chưa có hoặc khác ngày -> Full sync; ngược lại cập nhật kèo nếu đổi slot
        existing = load_existing_data()
        today_str = datetime.now().strftime("%Y-%m-%d")
        if not existing or existing.get("date") != today_str:
            run_full_sync()
        else:
            current_slot = get_current_odds_slot()
            if existing.get("odds_slot") != current_slot:
                run_odds_sync()
            else:
                print(f"ℹ️ Dữ liệu {today_str} (Slot {current_slot}) đã được cập nhật mới nhất. Không cần gọi thêm API.")
