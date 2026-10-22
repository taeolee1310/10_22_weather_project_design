"""준비물·메뉴·활동 추천 규칙. 기준값은 서비스용 임시 규칙이라 RULES 에서 고친다."""
import main

RULES = {
    "umbrella_pop": 50,  # 강수확률(%) 이상이면 우산
    "coat_feels": 15,  # 체감온도(°C) 이하면 겉옷
    "mask_aqi": 3,  # 대기질 등급 이상이면 마스크 안내 (3 = 나쁨)
    "hot": 27,  # 체감온도 이상이면 더운 날
    "cold": 5,  # 체감온도 이하면 쌀쌀한 날
    "extreme_hot": 33,  # 폭염: 야외 활동 부적절
    "extreme_cold": -5,  # 한파: 야외 활동 부적절
}

RAINY = ("Rain", "Drizzle", "Thunderstorm")

MENUS = {
    "rain": [("짬뽕", "🍜"), ("우동", "🍲"), ("칼국수", "🍜")],
    "hot": [("냉면", "🥶"), ("메밀국수", "🍜")],
    "cold": [("국밥", "🍲"), ("따뜻한 수프", "🥣")],
    "mild": [("비빔밥", "🍚"), ("샌드위치", "🥪")],
}
MENU_REASON = {
    "rain": "비 오는 날엔 따뜻한 국물이 어울려요.",
    "hot": "더운 날엔 시원한 면 요리가 어울려요.",
    "cold": "쌀쌀한 날엔 따뜻한 메뉴가 어울려요.",
    "mild": "온화한 날씨엔 가볍게 먹기 좋은 메뉴가 어울려요.",
}


def aqi_text(aqi):
    return "정보 없음" if aqi is None else main.AQI_LABEL.get(aqi, "정보 없음")


def pop_text(pop):
    return "정보 없음" if pop is None else f"{pop}%"


def is_rainy(entry):
    return entry["main"] in RAINY


def morning_items(entry, aqi):
    """필요한 준비물만 돌려준다. [(id, 이름, 이유)]"""
    items = []
    if entry is None:
        return items
    pop = entry["pop"]
    if is_rainy(entry) or (pop is not None and pop >= RULES["umbrella_pop"]):
        why = "비 예보가 있어요." if pop is None else f"강수확률이 {pop}%예요."
        items.append(("umbrella", "우산 챙겼어요", why))
    if entry["feels_like"] <= RULES["coat_feels"]:
        items.append(("coat", "겉옷 챙겼어요", f"체감 {entry['feels_like']:.0f}°, 가벼운 겉옷이 필요해요."))
    if aqi is not None and aqi >= RULES["mask_aqi"]:
        items.append(("mask", "마스크 챙겼어요", f"대기질이 '{aqi_text(aqi)}'이에요. 마스크를 준비해 보세요."))
    return items


def menu_group(entry):
    if is_rainy(entry):
        return "rain"
    if entry["feels_like"] >= RULES["hot"]:
        return "hot"
    if entry["feels_like"] <= RULES["cold"]:
        return "cold"
    return "mild"


def evening_activity(entry, aqi):
    """(id, 한 줄 제안, 버튼 이름, 이유). 야외가 맞지 않거나 판단할 수 없으면 실내 활동."""
    indoor = ("stretch", "집에서 가볍게 스트레칭", "스트레칭 할래요")
    if is_rainy(entry):
        return (*indoor, "비가 와서 실내 활동을 권해요.")
    feels = entry["feels_like"]
    if feels >= RULES["extreme_hot"] or feels <= RULES["extreme_cold"]:
        return (*indoor, "야외 활동을 하기엔 기온이 극단적이에요.")
    if aqi is None:
        return (*indoor, "대기질 정보를 확인하지 못해 실내 활동을 먼저 권해요.")
    if aqi >= RULES["mask_aqi"]:
        return (*indoor, f"대기질이 '{aqi_text(aqi)}'이라 실내 활동을 권해요.")
    return ("walk", "공원 산책", "산책할래요", f"비가 없고 대기질이 '{aqi_text(aqi)}'이에요.")
