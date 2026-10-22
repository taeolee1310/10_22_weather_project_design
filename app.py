"""하루 날씨 (Streamlit 화면). 실행: streamlit run app.py"""
import random
from datetime import datetime

import streamlit as st

import main  # 날씨 호출과 API 주소(🔌)
import mock_data
import recommend
import store
import weather

CACHE_SECONDS = 600
RETRY_SECONDS = 30
SLOT_HOUR = {"morning": 8, "lunch": 12, "evening": 18}  # 시간대별 예보를 볼 대표 시각
SLOT_TITLE = {"morning": "🌅 아침", "lunch": "🍚 점심", "evening": "🌙 저녁"}

st.set_page_config(page_title="하루 날씨", page_icon="⛅", layout="wide")
st.markdown(
    """
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css");
.stApp, .stApp p, .stApp label, .stApp button, .stApp h1, .stApp h2, .stApp h3 {
    font-family: Pretendard, -apple-system, "Malgun Gothic", sans-serif;
}
.stApp [class*="st-key-card-"] { padding: 8px; }
.stApp [class*="st-key-card-"][class*="-now"] { border: 2px solid #2563eb; border-radius: 8px; }
</style>
""",
    unsafe_allow_html=True,
)

now = datetime.now(weather.KST)
today = now.strftime("%Y-%m-%d")


# ---------- 데이터 ----------

def get_data(region, use_mock, force):
    if use_mock:
        return mock_data.build(now)
    cache = st.session_state.setdefault("cache", {})
    old = cache.get(region)
    # 실패한 항목이 있으면 30초 뒤 다시 시도한다 (실패를 10분간 붙들고 있지 않는다)
    ttl = RETRY_SECONDS if old and old["data"]["missing"] else CACHE_SECONDS
    expired = old is None or (now - old["fetched"]).total_seconds() > ttl
    if expired or force:
        with st.spinner("날씨를 불러오는 중이에요..."):
            data = weather.merge_with_previous(weather.fetch_region(region), old and old["data"])
        cache[region] = {"data": data, "fetched": now}
        return data
    return old["data"]


# ---------- 카드 ----------

def basis(entry, day, hour):
    if entry is None:
        return f"{day} {hour:02d}시 예보: 정보 없음"
    note = " (오늘 시간대는 지나서 내일 예보예요)" if day == "내일" else ""
    return f"{day} {entry['time']:%H}시 예보 기준{note}"


def _save_check(region, name, widget_key):
    store.put(region, today, name, st.session_state[widget_key])


def morning_card(entry, day, aqi, region):
    st.subheader(SLOT_TITLE["morning"])
    st.caption(basis(entry, day, SLOT_HOUR["morning"]))
    if entry is None:
        st.info("출근 시간대 예보를 가져오지 못해 준비물을 안내할 수 없어요.")
        return
    st.markdown("**출근 전, 이것만 챙겨요**")
    st.write(
        f"기온 {entry['temp']:.0f}°C · 체감 {entry['feels_like']:.0f}°C · "
        f"강수확률 {recommend.pop_text(entry['pop'])}"
    )
    items = recommend.morning_items(entry, aqi)
    if not items:
        st.success("오늘은 따로 챙길 게 없어요.")
    for name, label, why in items:
        wkey = f"chk-{region}-{today}-{name}"
        done = st.checkbox(
            label,
            value=store.get(region, today, f"chk-{name}", False),
            key=wkey,
            on_change=_save_check,
            args=(region, f"chk-{name}", wkey),
        )
        st.caption(("✅ 완료 · " if done else "") + why)
    if aqi is None:
        st.caption("대기질 정보가 없어서 마스크는 안내하지 못했어요.")


def _next_menu(key, names):
    current = st.session_state.get(key)
    st.session_state[key] = random.choice([n for n in names if n != current] or names)


def lunch_card(entry, day, aqi, region):
    st.subheader(SLOT_TITLE["lunch"])
    st.caption(basis(entry, day, SLOT_HOUR["lunch"]))
    if entry is None:
        st.info("점심 시간대 예보를 가져오지 못해 메뉴를 추천할 수 없어요.")
        return
    group = recommend.menu_group(entry)
    menus = dict(recommend.MENUS[group])
    key = f"menu-{region}-{today}"
    if st.session_state.get(key) not in menus:
        st.session_state[key] = random.choice(list(menus))
    name = st.session_state[key]
    st.markdown(f"### {menus[name]} {name}")
    st.write(recommend.MENU_REASON[group])
    st.caption(f"체감 {entry['feels_like']:.0f}°C · {entry['desc']} · 대기질 {recommend.aqi_text(aqi)}")
    if aqi is not None and aqi >= recommend.RULES["mask_aqi"]:
        st.warning("오늘은 가까운 실내에서 식사해 보세요.")
    st.button(
        "다른 메뉴 보기",
        key=f"next-{key}",
        on_click=_next_menu,
        args=(key, list(menus)),
        disabled=len(menus) < 2,
    )


def _choose_activity(region, activity):
    store.put(region, today, "evening", activity)


def evening_card(entry, day, aqi, region):
    st.subheader(SLOT_TITLE["evening"])
    st.caption(basis(entry, day, SLOT_HOUR["evening"]))
    if entry is None:
        st.info("퇴근 시간대 예보를 가져오지 못해 활동을 추천할 수 없어요.")
        st.write("오늘도 수고했어요.")
        return
    act, phrase, button, why = recommend.evening_activity(entry, aqi)
    st.markdown(f"### 오늘은 {phrase} 어때요?")
    st.write(why)
    st.caption(f"체감 {entry['feels_like']:.0f}°C · {entry['desc']} · 대기질 {recommend.aqi_text(aqi)}")
    chosen = store.get(region, today, "evening")
    if chosen == act:
        st.success(f"✅ {phrase}, 선택했어요. 오늘도 수고했어요.")
    else:
        st.button(button, key=f"act-{region}-{today}-{act}", on_click=_choose_activity, args=(region, act))
        st.write("오늘도 수고했어요.")


# ---------- 화면 ----------

title_col, region_col, refresh_col, setting_col = st.columns([4, 2, 1, 1], vertical_alignment="bottom")
title_col.title("⛅ 하루 날씨")
region = region_col.selectbox("지역", list(weather.REGIONS), index=0)
force = refresh_col.button("새로고침")
with setting_col.popover("설정"):
    use_mock = st.toggle("예시 데이터로 보기", key="use_mock")

data = get_data(region, use_mock, force)

if data["mock"]:
    st.warning("🧪 예시 데이터예요. 실제 날씨가 아니에요.")
for name in data["missing"]:
    st.warning(f"{weather.SOURCE_LABEL[name]} 정보를 가져오지 못했어요.")
for name in data["stale"]:
    st.warning(f"{weather.SOURCE_LABEL[name]} 갱신에 실패해서 {data['at'][name]:%H:%M} 기준 정보를 보여 드려요.")

current = data["current"]
forecast = data["forecast"] or []
upcoming = forecast[:3]  # 앞으로 약 9시간

with st.container(border=True):
    if current:
        st.markdown(f"**{region}** · 현재 {current['desc']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재 기온", f"{current['temp']:.0f}°C")
        c2.metric("체감온도", f"{current['feels_like']:.0f}°C")
    else:
        st.markdown(f"**{region}** · 현재 날씨 정보 없음")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재 기온", "정보 없음")
        c2.metric("체감온도", "정보 없음")
    with_pop = [e for e in upcoming if e["pop"] is not None]
    if with_pop:
        peak = max(with_pop, key=lambda e: e["pop"])
        c3.metric("비 올 확률", f"{peak['pop']}%", f"{peak['time']:%H}시 예보", delta_color="off")
    else:
        c3.metric("비 올 확률", "정보 없음")
    c4.metric("대기질", recommend.aqi_text(data["air_now"]))
    if data["at"]:
        newest = max(data["at"].values())
        st.caption(f"갱신 {newest:%Y-%m-%d %H:%M} (한국 시간)")

st.markdown("**앞으로 24시간 예보**")
if forecast:
    hourly = forecast[:8]
    for col, e in zip(st.columns(len(hourly)), hourly):
        col.markdown(f"**{e['time']:%H}시**")
        col.write(f"{e['temp']:.0f}°C")
        col.caption(f"{e['desc']}\n\n강수 {recommend.pop_text(e['pop'])}")
else:
    st.info("시간대별 예보를 가져오지 못했어요.")

current_slot = main.pick_slot()
cards = {"morning": morning_card, "lunch": lunch_card, "evening": evening_card}
for col, slot in zip(st.columns(3), cards):
    entry, day = weather.pick_forecast(forecast, SLOT_HOUR[slot], now)
    aqi = weather.pick_air(data["air_forecast"], entry["time"]) if entry else None
    is_now = slot == current_slot
    with col, st.container(border=True, key=f"card-{slot}" + ("-now" if is_now else "")):
        if is_now:
            st.markdown(":blue-badge[지금 시간대]")
        cards[slot](entry, day, aqi, region)

st.divider()
st.write("하루 세 번, 필요한 순간에 알려드려요")
st.caption("기본 시간은 07:30 / 12:00 / 18:30이에요. 알림 발송 기능은 아직 연결되지 않았어요.")
