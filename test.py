# app.py
# Streamlit: 초기 인류의 베링 육교 → 아메리카 최남단 이동 시뮬레이션
# 단순화된 해안 회랑 + 고지대 감속 효과 반영

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
# 고지대 구간 정의 (단순화)
# lat, lon, 영향 반경(km)
# -----------------------------
HIGHLAND_ZONES = [
    (10.0, -75.0, 500),   # 안데스 북부
    (-13.5, -71.9, 500),  # 안데스 중부 (쿠스코 주변)
    (-28.0, -67.0, 500),  # 안데스 남부
]


def highland_slowdown(lat, lon, base_speed, factor=0.5):
    """고지대 근처면 이동 속도 감소 (factor 비율 곱)"""
    for hz in HIGHLAND_ZONES:
        d = haversine_km(lat, lon, hz[0], hz[1])
        if d < hz[2]:
            return base_speed * factor
    return base_speed


# -----------------------------
# 해안 회랑 경로
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


@dataclass
class Group:
    speed_km_per_year: float
    rest_prob: float
    jitter_km: float
    s: float = 0.0
    finished: bool = False


# -----------------------------
# 시뮬레이션 로직
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
st.caption("고지대 감속 효과를 반영한 단순 모델")

with st.sidebar:
    st.header("파라미터")
    start_bp = st.number_input("시작 시점 (BP)", min_value=8000, max_value=20000, value=12000, step=100)
    mean_speed = st.slider("평균 이동 속도 (km/년)", 3.0, 30.0, 10.0, 0.5)
    speed_sd_frac = st.slider("연도별 속도 변동", 0.0, 1.0, 0.2, 0.05)
    rest_prob = st.slider("연간 휴식 확률", 0.0, 0.8, 0.15, 0.05)
    jitter_km = st.slider("소규모 지터 (km)", 0.0, 50.0, 5.0, 1.0)
    inland_bias = st.slider("내륙 성향", 0.0, 1.0, 0.2, 0.05)
    n_groups = st.slider("집단 수", 1, 200, 50, 1)
    max_years = st.slider("시뮬레이션 기간 (년)", 500, 7000, 4000, 100)
    seed = st.number_input("난수 시드", min_value=0, max_value=1_000_000, value=42, step=1)

CURRENT_PATH = COASTAL_WAYPOINTS
CUMDIST = cumulative_path(CURRENT_PATH)
PATH_LEN = float(CUMDIST[-1])

rng = random.Random(seed)
groups = [Group(speed_km_per_year=max(0.1, rng.normalvariate(mean_speed, mean_speed*0.05)),
                rest_prob=rest_prob,
                jitter_km=jitter_km) for _ in range(n_groups)]

DF = simulate(groups, CUMDIST, PATH_LEN, max_years=max_years, variability=speed_sd_frac, inland_bias=inland_bias, rng=rng)

arrivals = (DF[DF["s"] >= PATH_LEN].groupby("group")["year"].min().dropna())

elapsed_median = float(arrivals.median()) if len(arrivals) > 0 else float("nan")
elapsed_mean = float(arrivals.mean()) if len(arrivals) > 0 else float("nan")

st.metric("경로 길이 (km)", f"{PATH_LEN:,.0f}")
st.metric("도착 비율", f"{100*len(arrivals)/n_groups:.1f}%")
st.metric("중앙 도착 연수", "—" if math.isnan(elapsed_median) else f"{elapsed_median:,.0f} 년")

# 지도 시각화 등 나머지 코드는 이전과 동일
# (pydeck chart, 도착 분포, 데이터 다운로드 등)

