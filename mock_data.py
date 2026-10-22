"""예시 데이터. 화면에서는 항상 '예시 데이터' 배지와 함께 보여 준다."""
import math
from datetime import timedelta


def build(now):
    start = now.replace(minute=0, second=0, microsecond=0)
    start += timedelta(hours=3 - start.hour % 3)  # 다음 3시간 경계
    forecast = []
    for i in range(24):
        rainy = i % 9 in (3, 4)
        temp = 13 + 7 * math.sin((i - 2) / 8 * math.pi)
        forecast.append({
            "time": start + timedelta(hours=3 * i),
            "temp": temp,
            "feels_like": temp - 2,
            "main": "Rain" if rainy else "Clouds",
            "desc": "비" if rainy else "구름 조금",
            "pop": 80 if rainy else 10 + (i % 3) * 10,
        })
    hourly = now.replace(minute=0, second=0, microsecond=0)
    air_forecast = [(hourly + timedelta(hours=h), 1 + (h // 6) % 4) for h in range(72)]
    return {
        "current": {"temp": 14.2, "feels_like": 12.5, "main": "Clouds", "desc": "구름 조금"},
        "forecast": forecast,
        "air_now": 2,
        "air_forecast": air_forecast,
        "at": {k: now for k in ("current", "forecast", "air_now", "air_forecast")},
        "stale": [],
        "missing": [],
        "mock": True,
    }
