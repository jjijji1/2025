import streamlit as st
import pydeck as pdk
import numpy as np
import time

st.set_page_config(layout="wide")

st.title("🌍 초기 인류의 아메리카 대륙 이동 시뮬레이션")

# -----------------------------
# 부족별 아이콘 (밝은 색상)
# -----------------------------
tribe_icons = [
    "https://upload.wikimedia.org/wikipedia/commons/5/55/Human-icon.png",  # 기본
    "https://upload.wikimedia.org/wikipedia/commons/e/e4/RedDot.png",       # 빨강
    "https://upload.wikimedia.org/wikipedia/commons/5/5c/BlueDot.png",      # 파랑
    "https://upload.wikimedia.org/wikipedia/commons/5/51/GreenDot.png",     # 초록
    "https://upload.wikimedia.org/wikipedia/commons/0/0c/OrangeDot.png"     # 주황
]

group_count = len(tribe_icons)

# -----------------------------
# 기본 경로 (터키 → 아메리카 남단)
# -----------------------------
base_path = [
    (39.0, 35.0),   # 터키
    (60.0, 60.0),   # 시베리아
    (65.0, -170.0), # 베링 해협
    (60.0, -150.0), # 알래스카
    (40.0, -120.0), # 북미 서부
    (20.0, -100.0), # 멕시코
    (-10.0, -60.0), # 아마존
    (-55.0, -70.0), # 남미 최남단
]

# -----------------------------
# 경유지 후보 (랜덤 삽입)
# -----------------------------
waypoints = [
    # 아시아/유럽
    (30.0, 80.0),   # 인도 북부
    (50.0, 90.0),   # 몽골
    (35.0, 100.0),  # 중국 내륙
    (10.0, 40.0),   # 아프리카 동부

    # 북미
    (50.0, -110.0), # 로키 산맥
    (40.0, -95.0),  # 대평원
    (30.0, -85.0),  # 멕시코만 연안

    # 남미
    (0.0, -65.0),   # 아마존 분지
    (-15.0, -70.0), # 안데스 고원
    (-30.0, -55.0), # 남미 대평원 (팜파스)
    (-40.0, -60.0), # 남미 남부 내륙
]

# -----------------------------
# 부족별 경로 생성 (랜덤하게 waypoint 추가)
# -----------------------------
tribe_paths = []
for i in range(group_count):
    p = base_path.copy()
    if np.random.rand() < 0.7:   # 70% 확률로 경유지 추가
        wp = waypoints[np.random.randint(len(waypoints))]
        p.insert(np.random.randint(1, len(p)-1), wp)  # 중간에 랜덤 삽입
    tribe_paths.append(p)

# -----------------------------
# 애니메이션 상태 관리
# -----------------------------
if "frame" not in st.session_state:
    st.session_state.frame = 0
if "play" not in st.session_state:
    st.session_state.play = False

col1, col2 = st.columns([1, 5])

with col1:
    if st.button("▶ Play / ⏸ Pause"):
        st.session_state.play = not st.session_state.play

    play_speed = st.slider("속도 조절 (ms/frame)", 100, 2000, 500, step=100)

    frame = st.session_state.frame

# -----------------------------
# 현재 프레임에서 부족 위치 계산
# -----------------------------
def interpolate_path(path, t):
    """경로 path에서 t번째 좌표 계산"""
    segment = t // 100
    progress = (t % 100) / 100
    if segment >= len(path) - 1:
        return path[-1]
    lat1, lon1 = path[segment]
    lat2, lon2 = path[segment+1]
    return (lat1 + (lat2-lat1)*progress, lon1 + (lon2-lon1)*progress)

positions = [interpolate_path(p, frame) for p in tribe_paths]

# -----------------------------
# 지도 표시 (pydeck)
# -----------------------------
icon_data = []
for i, pos in enumerate(positions):
    lat, lon = pos
    icon_data.append({
        "position": [lon, lat],
        "icon_url": tribe_icons[i],
        "size": 4,
    })

icon_layer = pdk.Layer(
    "IconLayer",
    data=icon_data,
    get_icon="icon_url",
    get_size="size",
    get_position="position",
    size_scale=8,
    pickable=True,
)

# 부족 경로 레이어
path_layers = []
colors = [
    [255, 0, 0],
    [0, 0, 255],
    [0, 255, 0],
    [255, 165, 0],
    [255, 255, 0],
]

for i, path in enumerate(tribe_paths):
    coords = [[lon, lat] for lat, lon in path]
    path_layers.append(
        pdk.Layer(
            "PathLayer",
            data=[{"path": coords}],
            get_path="path",
            get_color=colors[i % len(colors)],
            width_scale=2,
            width_min_pixels=2,
        )
    )

view_state = pdk.ViewState(latitude=20, longitude=-60, zoom=2)

r = pdk.Deck(
    layers=[icon_layer] + path_layers,
    initial_view_state=view_state,
    map_style=None   # ← 토큰 필요 없는 기본 세계지도
)

with col2:
    st.pydeck_chart(r, use_container_width=True)

# -----------------------------
# 애니메이션 진행
# -----------------------------
if st.session_state.play:
    time.sleep(play_speed/1000.0)
    st.session_state.frame = (frame + 5) % (len(base_path) * 100)
    st.rerun()
