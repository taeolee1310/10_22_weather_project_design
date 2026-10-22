"""하루 세 번 날씨 안내 서비스 (뼈대, 디자인 제외).

사용법: python main.py [morning|lunch|evening]   (생략하면 지금 시각으로 고름)
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

API = {
    "current": "https://api.openweathermap.org/data/2.5/weather",  # 🔌 현재 날씨(체감온도)
    "forecast": "https://api.openweathermap.org/data/2.5/forecast",  # 🔌 3시간 예보(강수확률)
    "air": "https://api.openweathermap.org/data/2.5/air_pollution",  # 🔌 대기질(AQI 1~5)
}

CITY = "Seoul,KR"
AQI_LABEL = {1: "좋음", 2: "보통", 3: "나쁨", 4: "매우 나쁨", 5: "위험"}

load_dotenv()


def _get(name, **params):
    """API 한 곳 호출. 실패하면 None (주소·키는 출력하지 않는다)."""
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        print("OPENWEATHER_API_KEY 가 .env 에 없어요.")
        return None
    try:
        res = requests.get(API[name], params={**params, "appid": key, "units": "metric", "lang": "kr"}, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception:
        print(f"{name} 날씨 정보를 가져오지 못했어요.")
        return None


def fetch_weather():
    """현재 날씨 → 체감온도·날씨 상태·좌표."""
    data = _get("current", q=CITY)
    if not data:
        return None
    return {
        "feels_like": data["main"]["feels_like"],
        "temp": data["main"]["temp"],
        "main": data["weather"][0]["main"],  # Rain, Clear, Clouds ...
        "desc": data["weather"][0]["description"],
        "lat": data["coord"]["lat"],
        "lon": data["coord"]["lon"],
    }


def fetch_rain_probability():
    """가까운 예보의 비 올 확률(0~100%)."""
    data = _get("forecast", q=CITY, cnt=3)
    if not data:
        return None
    return round(max(item.get("pop", 0) for item in data["list"]) * 100)


def fetch_air(lat, lon):
    """대기질 지수(1~5)."""
    data = _get("air", lat=lat, lon=lon)
    if not data:
        return None
    return data["list"][0]["main"]["aqi"]


# ---------- 시간대별 안내 ----------

def morning(weather, rain):
    """아침: 출근길 체크리스트."""
    print("[아침] 출근길 체크리스트")
    if weather:
        print(f"- 체감온도 {weather['feels_like']:.0f}°C ({weather['desc']})")
    items = []
    if rain is not None:
        print(f"- 비 올 확률 {rain}%")
        items.append(("우산 챙겼어요", rain >= 50))
    if weather:
        items.append(("겉옷 챙겼어요", weather["feels_like"] < 15))
    for text, needed in items:
        print(f"  [ ] {text}" if needed else f"  (오늘은 안 챙겨도 돼요) {text}")


def lunch(weather, aqi):
    """점심: 날씨·미세먼지에 맞는 메뉴 추천 카드."""
    print("[점심] 오늘의 메뉴 카드")
    if not weather:
        return
    if weather["main"] in ("Rain", "Drizzle", "Thunderstorm"):
        menu = "짬뽕"
    elif weather["feels_like"] >= 27:
        menu = "냉면"
    elif weather["feels_like"] <= 5:
        menu = "국밥"
    elif aqi is not None and aqi >= 3:
        menu = "삼겹살 (미세먼지엔 역시?)"
    else:
        menu = "비빔밥"
    print(f"- 추천: {menu}")
    if aqi is not None:
        print(f"- 대기질: {AQI_LABEL.get(aqi, '알 수 없음')}")


def evening(aqi):
    """저녁: 퇴근길 할 일 또는 위로 문구."""
    print("[저녁] 퇴근길 한마디")
    if aqi is None:
        print("- 오늘도 수고했어요.")
    elif aqi <= 2:
        print("- 공기가 좋아요. 오늘은 공원 산책 어때요?")
    else:
        print("- 공기가 좋지 않아요. 오늘은 집에서 홈트 어때요?")
    print("- 오늘도 수고했어요.")


def pick_slot():
    hour = datetime.now(ZoneInfo("Asia/Seoul")).hour
    if hour < 11:
        return "morning"
    if hour < 16:
        return "lunch"
    return "evening"


def main():
    slot = sys.argv[1] if len(sys.argv) > 1 else pick_slot()
    weather = fetch_weather()
    if slot == "morning":
        morning(weather, fetch_rain_probability())
    elif slot == "lunch":
        aqi = fetch_air(weather["lat"], weather["lon"]) if weather else None
        lunch(weather, aqi)
    elif slot == "evening":
        aqi = fetch_air(weather["lat"], weather["lon"]) if weather else None
        evening(aqi)
    else:
        print("morning, lunch, evening 중 하나를 골라 주세요.")


if __name__ == "__main__":
    main()
