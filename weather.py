"""날씨 조회(services)와 응답 정규화(adapters). API 주소(🔌)는 main.API 한 곳에서만 관리한다."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import main

KST = ZoneInfo("Asia/Seoul")

# 지역 → (위도, 경도). 초기 지역은 서울.
REGIONS = {
    "서울": (37.5665, 126.9780),
    "인천": (37.4563, 126.7052),
    "대전": (36.3504, 127.3845),
    "대구": (35.8714, 128.6014),
    "광주": (35.1595, 126.8526),
    "부산": (35.1796, 129.0756),
    "제주": (33.4996, 126.5312),
}

SOURCE_LABEL = {
    "current": "현재 날씨",
    "forecast": "시간대별 예보",
    "air_now": "현재 대기질",
    "air_forecast": "대기질 예보",
}

SLOT_TOLERANCE = timedelta(minutes=90)  # 예보는 3시간 간격이라 가장 가까운 항목을 쓴다


def _kst(ts):
    return datetime.fromtimestamp(ts, KST)


def _entry(item):
    pop = item.get("pop")
    return {
        "time": _kst(item["dt"]),
        "temp": item["main"]["temp"],
        "feels_like": item["main"]["feels_like"],
        "main": item["weather"][0]["main"],
        "desc": item["weather"][0]["description"],
        "pop": None if pop is None else round(pop * 100),  # 없는 값은 0이 아니라 None
    }


def _parse_current(raw):
    return {
        "temp": raw["main"]["temp"],
        "feels_like": raw["main"]["feels_like"],
        "main": raw["weather"][0]["main"],
        "desc": raw["weather"][0]["description"],
    }


PARSERS = {
    "current": _parse_current,
    "forecast": lambda raw: [_entry(i) for i in raw["list"]],
    "air_now": lambda raw: raw["list"][0]["main"]["aqi"],
    "air_forecast": lambda raw: [(_kst(i["dt"]), i["main"]["aqi"]) for i in raw["list"]],
}


API_NAME = {"air_now": "air"}  # 항목 이름과 main.API 키가 다른 경우만 적는다


def _safe(parse, raw):
    if not raw:
        return None
    try:
        return parse(raw) or None
    except (KeyError, IndexError, TypeError):
        return None


def fetch_region(region):
    """네 곳을 따로 불러온다. 하나가 실패해도 나머지는 그대로 쓴다."""
    lat, lon = REGIONS[region]
    now = datetime.now(KST)
    raw = {name: main._get(API_NAME.get(name, name), lat=lat, lon=lon) for name in PARSERS}
    data = {"at": {}, "stale": [], "missing": [], "mock": False}
    for name, parse in PARSERS.items():
        data[name] = _safe(parse, raw[name])
        if data[name] is None:
            data["missing"].append(name)
        else:
            data["at"][name] = now
    return data


def merge_with_previous(new, old):
    """새로 못 가져온 항목은 이전 값을 쓰되 stale 로 표시한다."""
    if not old or old.get("mock"):
        return new
    for name in list(new["missing"]):
        if old.get(name) is not None:
            new[name] = old[name]
            new["at"][name] = old["at"][name]
            new["missing"].remove(name)
            new["stale"].append(name)
    return new


def pick_forecast(forecast, hour, now):
    """시간대 대표 시각(hour시)에 가장 가까운 예보. 이미 지난 시각이면 내일 예보. → (항목, '오늘'|'내일')"""
    if not forecast:
        return None, "오늘"
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    day = "오늘"
    if target + SLOT_TOLERANCE < now:
        target += timedelta(days=1)
        day = "내일"
    best = min(forecast, key=lambda e: abs(e["time"] - target))
    if abs(best["time"] - target) > SLOT_TOLERANCE:
        return None, day
    return best, day


def pick_air(air_forecast, when):
    """예보 시각에 가장 가까운 대기질 등급. 없으면 None (좋음으로 가정하지 않는다)."""
    if not air_forecast:
        return None
    t, aqi = min(air_forecast, key=lambda x: abs(x[0] - when))
    return aqi if abs(t - when) <= SLOT_TOLERANCE else None
