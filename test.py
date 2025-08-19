# app.py
# -*- coding: utf-8 -*-
import math
from typing import List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="초기 인류 아메리카 최남단 이동 시뮬레이션", layout="wide")

st.title("초기 인류의 아메리카 최남단 이동 시뮬레이션")
st.caption(
    "가정: 약 1만 년 전 초기 인류가 아프리카에서 출발 → 유럽·아시아 경유 → "
    "빙하기의 **베링 해협(육교/빙설면)**을 통해 아메리카로 진입 → 남미 최남단(티에라 델 푸에고) 도달. "
    "요청 조건에 따라 **베링 해협 구간만** 바다 횡단(빙결)을 허용하고, 그 외는 가능한 한 **육상 경로**를 따릅니다."
)

# -----------------------
# 경로 설정 (주요 경유 지점; 바다를 피해 육로로 이어짐, 베링 해협 구간만 예외)
# 위도(lat), 경도(lon) 순서 (북+, 동+)
# -----------------------
WAYPOINTS: List[Tuple[float, float, str]] = [
    # 아프리카 기원(동아프리카 고지대 부근 가정)
    (9.0, 40.0, "아프리카 기원(동아프리카)"),
    (15.0, 32.0, "나일 상류"),
    (30.0, 31.0, "이집트-레반트"),
    # 유럽 측면으로 일부 북상
    (41.0, 28.9, "발칸/보스포루스 인근"),
    (45.0, 20.0, "중앙유럽 남부"),
    (50.0, 14.0, "중앙유럽 북부"),
    # 다시 아시아 심부로 동진
    (48.0, 60.0, "서시베리아"),
    (55.0, 90.0, "시베리아 중앙"),
    (62.0, 120.0, "동시베리아"),
    (66.0, 170.0, "추코트카 동단"),
    # 베링 해협(빙결/육교 가정) — 바다 횡단 허용 구간
    (66.0, -168.0, "베링 해협 건너(알래스카 서북)"),
    # 북미 종단(가능한 육상 경로)
    (64.0, -150.0, "알래스카 내륙"),
    (57.0, -135.0, "브리티시컬럼비아 북부"),
    (49.0, -123.0, "태평양 연안 내륙로"),
    (44.0, -113.0, "로키 산악로"),
    (41.0, -111.0, "그레이트베이슨 동"),
    (37.0, -109.0, "포코노/4코너즈 인근"),
    (33.0, -106.0, "뉴멕시코"),
    (29.0, -104.0, "텍사스 서부"),
    (24.0, -100.0, "멕시코 고원"),
    (20.0, -99.0,  "멕시코 중앙"),
    (17.0, -92.0,  "치아파스/과테말라"),
    (10.0, -84.0,  "코스타리카"),
    (8.5, -79.5,   "파나마 이스무스"),
    # 남미
    (5.0, -75.0,   "콜롬비아 안데스 북부"),
    (-4.0, -79.0,  "에콰도르/페루 북부 안데스"),
    (-12.0, -77.0, "페루 중부"),
    (-16.0, -68.0, "볼리비아 고원"),
    (-23.0, -67.0, "아르헨티나 북서부"),
    (-33.0, -70.0, "중부 칠레/산티아고 인근"),
    (-41.0, -72.0, "칠레 남부/파타고니아 북"),
    (-49.0, -72.0, "파타고니아 남부"),
    (-54.0, -68.3, "티에라 델 푸에고(최남단)"),
]

# -----------------------
# 유틸: 경도 언랩(±180 경계 넘김 보정) 및 구간 보간
# -----------------------
def unwrap_lons(lons: np.ndarray) -> np.ndarray:
    """연속적인 선을 위해 경도 급변(±180 경계)을 완만하게 보정"""
    unwrapped = [lons[0]]
    for lon in lons[1:]:
        prev = unwrapped[-1]
        d = lon - prev
        if d > 180:
            lon -= 360
        elif d < -180:
            lon += 360
        unwrapped.append(lon)
    return np.array(unwrapped)

def interpolate_segment(p0: Tuple[float, float], p1: Tuple[float, float], n: int) -> Tuple[np.ndarray, np.ndarray]:
    """위·경도 선형 보간(작은 구간 기준으로 충분히 근사)"""
    lat0, lon0 = p0
    lat1, lon1 = p1
    lats = np.linspace(lat0, lat1, n, endpoint=False)
    lons = np.linspace(lon0, lon1, n, endpoint=False)
    return lats, lons

def build_route(points: List[Tuple[float, float, str]], seg_density: int) -> pd.DataFrame:
    """웨이포인트 사이를 보간해 전체 경로 프레임 생성"""
    all_lats, all_lons, labels = [], [], []
    names = []
    for i in range(len(points) - 1):
        p0 = (points[i][0], points[i][1])
        p1 = (points[i + 1][0], points[i + 1][1])
        n = max(2, seg_density)
        lats, lons = interpolate_segment(p0, p1, n)
        all_lats.extend(lats.tolist())
        all_lons.extend(lons.tolist())
        labels.extend([i] * len(lats))
        names.append(points[i][2])
    # 마지막 웨이포인트 추가
    all_lats.append(points[-1][0])
    all_lons.append(points[-1][1])
    labels.append(len(points) - 1)

    # 경도 언랩
    uw = unwrap_lons(np.array(all_lons))
    df = pd.DataFrame({
        "lat": np.array(all_lats),
        "lon_unwrap": uw,
        "seg": labels,
    })
    # 프레임 인덱스(시간축) 부여
    df["t"] = np.arange(len(df))
    return df

# -----------------------
# 사이드바 옵션
# -----------------------
with st.sidebar:
    st.header("시뮬레이션 옵션")
    seg_density = st.slider("구간 보간(밀도)", 4, 100, 25, help="값이 높을수록 경로가 더 매끈해집니다.")
    speed = st.select_slider(
        "재생 속도",
        options=["매우 느림", "느림", "보통", "빠름", "매우 빠름"],
        value="보통"
    )
    show_points = st.checkbox("주요 경유지 라벨 표시", value=True)
    show_front = st.checkbox("이동 선두(Marker) 표시", value=True)
    st.markdown("---")
    st.caption("※ 베링 해협 구간만 바다(빙결)를 가정하고, 나머지는 육상 경로를 따르는 웨이포인트로 구성했습니다.")

# 속도 → 프레임 지속 시간(ms)
speed_map = {
    "매우 느림": 600,
    "느림": 350,
    "보통": 200,
    "빠름": 120,
    "매우 빠름": 60,
}
frame_dur = speed_map[speed]

# 경로 데이터 구성
route_df = build_route(WAYPOINTS, seg_density=seg_density)

# plotly 애니메이션 프레임 생성
frames = []
for i in range(2, len(route_df) + 1):
    sub = route_df.iloc[:i]
    frames.append(
        go.Frame(
            data=[
                go.Scattergeo(
                    lat=sub["lat"],
                    lon=sub["lon_unwrap"],
                    mode="lines",
                    line=dict(width=3),
                    name="경로",
                ),
                # 선두점
                go.Scattergeo(
                    lat=[sub["lat"].iloc[-1]],
                    lon=[sub["lon_unwrap"].iloc[-1]],
                    mode="markers",
                    marker=dict(size=8),
                    name="선두",
                    visible=show_front,
                ) if show_front else go.Scattergeo(lat=[], lon=[]),
            ],
            name=str(i),
        )
    )

# 초기 데이터(짧은 선)
init = route_df.iloc[:2]

# 주요 경유지 라벨
label_trace = go.Scattergeo(
    lat=[lat for lat, lon, name in WAYPOINTS],
    lon=unwrap_lons(np.array([lon for lat, lon, name in WAYPOINTS])),
    mode="markers+text",
    text=[name for lat, lon, name in WAYPOINTS],
    textposition="top center",
    marker=dict(size=6),
    name="주요 경유지",
    visible=show_points,
)

fig = go.Figure(
    data=[
        go.Scattergeo(
            lat=init["lat"],
            lon=init["lon_unwrap"],
            mode="lines",
            line=dict(width=3),
            name="경로",
        ),
        go.Scattergeo(
            lat=[init["lat"].iloc[-1]],
            lon=[init["lon_unwrap"].iloc[-1]],
            mode="markers",
            marker=dict(size=8),
            name="선두",
            visible=show_front,
        ) if show_front else go.Scattergeo(lat=[], lon=[]),
        label_trace,
    ],
    frames=frames
)

# 지도 레이아웃
fig.update_layout(
    height=700,
    margin=dict(l=0, r=0, t=10, b=0),
    geo=dict(
        projection_type="natural earth",
        showland=True,
        landcolor="#EAE7DC",
        showcountries=True,
        countrycolor="#8C8C8C",
        showcoastlines=True,
        coastlinecolor="#8C8C8C",
        showocean=True,
        oceancolor="#DCE9F9",
        showlakes=True,
        lakecolor="#DCE9F9",
        showrivers=False,
        lataxis=dict(showgrid=True, gridwidth=0.5),
        lonaxis=dict(showgrid=True, gridwidth=0.5),
        resolution=50,
        scope="world",
    ),
    updatemenus=[
        dict(
            type="buttons",
            x=0.02, y=0.02,
            xanchor="left", yanchor="bottom",
            direction="right",
            showactive=True,
            buttons=[
                dict(
                    label="▶ 재생",
                    method="animate",
                    args=[
                        None,
                        dict(
                            frame=dict(duration=frame_dur, redraw=True),
                            fromcurrent=True,
                            mode="immediate",
                            transition=dict(duration=0),
                        ),
                    ],
                ),
                dict(
                    label="⏹ 정지",
                    method="animate",
                    args=[
                        [None],
                        dict(frame=dict(duration=0, redraw=False), mode="immediate"),
                    ],
                ),
            ],
        )
    ],
    sliders=[
        dict(
            active=0,
            x=0.05, y=0,
            xanchor="left", yanchor="top",
            currentvalue=dict(prefix="프레임: "),
            transition=dict(duration=0),
            pad=dict(b=30, t=40),
            len=0.9,
            steps=[
                dict(method="animate",
                     args=[[str(k + 2)],
                           dict(frame=dict(duration=0, redraw=True),
                                mode="immediate")],
                     label=str(k + 2))
                for k in range(len(route_df) - 1)
            ],
        )
    ],
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("모형 및 데이터 설명", expanded=False):
    st.markdown(
        """
- **경유지(Waypoints)**: 바다를 피한 육상 이동을 따르도록 수작업으로 지정했습니다.  
  베링 해협 구간만 **빙하기의 빙결/육교 가정**으로 바다 구간을 통과합니다.
- **보간(밀도)**: 웨이포인트 사이를 선형 보간하여 매끈한 경로를 만들었습니다(지구 곡률 효과는 짧은 구간으로 근사).
- **애니메이션**: 프레임이 증가할수록 경로가 길어지며 이동 선두 마커가 남하합니다. 속도는 사이드바에서 조절하세요.
- **주의**: 이는 단순화한 **시각적 시뮬레이션**이며, 실제 고고학·유전학적 이동 시기/세부 경로와는 다를 수 있습니다.
        """
    )
