# app.py
# Streamlit: 초기 인류의 베링 육교 → 아메리카 최남단 이동 시뮬레이션
# 해안 회랑 + 고지대 감속 효과 + 사람 아이콘 애니메이션

import math
import random
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import pydeck as pdk

# -----------------------------
# 유틸 함수
# -----------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def interpolate_point(p1, p2, fraction):
    lat = p1[0] + (p2[0] - p1[0]) * fraction
    lon = p1[1] + (p2[1] - p1[1]) * fraction
    return (lat, lon)


def cumulative_path(path: List[Tuple[float, float]]):
    cumdist = [0.0]
    for i in range(1, len(path)):
        cumdist.append(cumdist[-1] + haversine_km(*path[i-1], *path[i]))
    return np.array(cumdist)


def point_at_distance(path: List[Tuple[float, float]], cumdist: np.ndarray, s: float):
    if s <= 0:
        return path[0]
    if s >= cumdist[-1]:
        return path[-1]
    i = np.searchsorted(cumdist, s) - 1
    seg_len = cumdist[i+1] - cumdist[i]
    frac = (s - cumdist[i]) / seg_len if seg_len > 0 else 0
    return interpolate_point(path[i], path[i+1], frac)

# -----------------------------
# 고지대 구간
# -----------------------------
HIGHLAND_ZONES = [
    (10.0, -75.0, 500),   # 안데스 북부
    (-13.5, -71.9, 500),  # 안데스 중부
    (-28.0, -67.0, 500),  # 안데스 남부
]

def highland_slowdown(lat, lon, base_speed, factor=0.5):
    for hz in HIGHLAND_ZONES:
        d = haversine_km(lat, lon, hz[0], hz[1])
        if d < hz[2]:
            return base_speed * factor
    return base_speed

# -----------------------------
# 경로
# -----------------------------
COASTAL_WAYPOINTS = [
    (66.0, -169.0), (63.5, -165.5), (60.0, -151.0), (55.0, -133.0),
    (49.3, -123.1), (47.6, -122.3), (45.5, -123.9), (37.8, -122.5),
    (34.0, -118.5), (32.5, -117.0), (27.0, -112.0), (23.2, -106.4),
    (20.7, -105.3), (17.0, -100.3), (15.8, -96.5), (14.8, -92.3),
    (13.5, -90.7), (9.0, -79.5), (5.0, -77.5), (3.0, -80.0),
    (-5.2, -80.7), (-12.1, -77.0), (-16.4, -71.5), (-23.6, -70.4),
    (-33.5, -71.6), (-41.5, -73.0), (-46.6, -71.8), (-50.3, -72.3),
    (-53.2, -70.9), (-54.8, -68.3)
]

INLAND_HOPS = [
    (49.0, -120.0), (40.0, -120.0), (25.0, -104.0),
    (15.0, -88.0), (-10.0, -76.0), (-20.0, -69.0)
]

from dataclasses import dataclass
@dataclass
class Group:
    speed_km_per_year: float
    rest_prob: float
    jitter_km: float
    s: float = 0.0
    finished: bool = False

# -----------------------------
# 시뮬레이션
# -----------------------------

def simulate(groups: List[Group], cumdist: np.ndarray, path_len: float, max_years: int, variability: float, inland_bias: float, rng: random.Random):
    records = []
    inland_scale = inland_bias

    for year in range(max_years + 1):
        for gi, g in enumerate(groups):
            lat, lon = point_at_distance(CURRENT_PATH, cumdist, g.s)

            if inland_scale > 0 and 0 < g.s < path_len:
                near = min(INLAND_HOPS, key=lambda p: haversine_km(lat, lon, p[0], p[1]))
                offset_km = inland_scale * 10.0
                dlat = (near[0] - lat)
                dlon = (near[1] - lon)
                norm = math.hypot(dlat, dlon)
                if norm > 0:
                    lat += dlat / norm * (offset_km / 110.0)
                    lon += dlon / norm * (offset_km / 110.0)

            records.append((year, gi, lat, lon, g.s, g.finished))

        for gi, g in enumerate(groups):
            if g.finished:
                continue
            if rng.random() < g.rest_prob:
                continue
            v = max(0.0, rng.normalvariate(g.speed_km_per_year, g.speed_km_per_year * variability))
            lat, lon = point_at_distance(CURRENT_PATH, cumdist, g.s)
            v = highland_slowdown(lat, lon, v, factor=0.5)
            g.s += v
            if g.s >= path_len:
                g.s = path_len
                g.finished = True

    df = pd.DataFrame(records, columns=["year", "group", "lat", "lon", "s", "finished"])
    return df

# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="초기 인류 아메리카 종단 시뮬레이션", layout="wide")

st.title("🌎 초기 인류의 아메리카 최남단 도달 시뮬레이션")
st.caption("고지대 감속 + 사람 아이콘 애니메이션")

with st.sidebar:
    st.header("파라미터")
    mean_speed = st.slider("평균 이동 속도 (km/년)", 3.0, 30.0, 10.0, 0.5)
    speed_sd_frac = st.slider("연도별 속도 변동", 0.0, 1.0, 0.2, 0.05)
    rest_prob = st.slider("연간 휴식 확률", 0.0, 0.8, 0.15, 0.05)
    jitter_km = st.slider("소규모 지터 (km)", 0.0, 50.0, 5.0, 1.0)
    inland_bias = st.slider("내륙 성향", 0.0, 1.0, 0.2, 0.05)
    n_groups = st.slider("집단 수", 1, 50, 5, 1)
    max_years = st.slider("시뮬레이션 기간 (년)", 500, 7000, 2000, 100)
    seed = st.number_input("난수 시드", min_value=0, max_value=1_000_000, value=42, step=1)
    play_speed = st.slider("애니메이션 속도 (ms/frame)", 100, 2000, 500, 100)

CURRENT_PATH = COASTAL_WAYPOINTS
CUMDIST = cumulative_path(CURRENT_PATH)
PATH_LEN = float(CUMDIST[-1])

rng = random.Random(seed)
groups = [Group(speed_km_per_year=max(0.1, rng.normalvariate(mean_speed, mean_speed*0.05)),
                rest_prob=rest_prob,
                jitter_km=jitter_km) for _ in range(n_groups)]

DF = simulate(groups, CUMDIST, PATH_LEN, max_years=max_years, variability=speed_sd_frac, inland_bias=inland_bias, rng=rng)

# -----------------------------
# 애니메이션: Streamlit rerun trick
# -----------------------------
frame = st.session_state.get("frame", 0)
max_frame = int(DF["year"].max())

col1, col2 = st.columns([1,5])
with col1:
    if st.button("▶️ Play"):
        st.session_state.play = True
    if st.button("⏸️ Pause"):
        st.session_state.play = False

if "play" not in st.session_state:
    st.session_state.play = False

if st.session_state.play:
    import time
    time.sleep(play_speed/1000.0)
    st.session_state.frame = (frame + 50) % (max_frame+1)
    st.experimental_rerun()

frame = st.session_state.get("frame", 0)
snap = DF[DF["year"] == frame]

# -----------------------------
# 지도 아이콘 레이어
# -----------------------------
icon_url = "https://upload.wikimedia.org/wikipedia/commons/9/99/Stickman.png"

icon_data = [
    {
        "lat": row.lat,
        "lon": row.lon,
        "icon": {
            "url": icon_url,
            "width": 128,
            "height": 128,
            "anchorY": 128,
        }
    }
    for _, row in snap.iterrows()
]

icon_layer = pdk.Layer(
    "IconLayer",
    data=icon_data,
    get_icon="icon",
    get_size=4,
    get_position='[lon, lat]',
    pickable=True
)

path_coords = [[lon, lat] for lat, lon in CURRENT_PATH]
path_layer = pdk.Layer(
    "PathLayer",
    data=[{"path": path_coords, "name": "Coastal Corridor"}],
    get_path="path",
    get_width=3,
    width_min_pixels=3,
    pickable=False,
)

view_state = pdk.ViewState(latitude=10, longitude=-90, zoom=2.2)

r = pdk.Deck(layers=[path_layer, icon_layer], initial_view_state=view_state)

st.pydeck_chart(r, use_container_width=True)

st.caption("사람 아이콘이 해안 회랑 경로를 따라 이동하는 애니메이션")
