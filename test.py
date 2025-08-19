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
    "https://upload.wikimedia.org/wikipedia/commons/5/55/Human-icon.png",
    "https://upload.wikimedia.org/wikipedia/commons/e/e4/RedDot.png",
    "https://upload.wikimedia.org/wikipedia/commons/5/5c/BlueDot.png",
    "https://upload.wikimedia.org/wikipedia/commons/5/51/GreenDot.png",
    "https://upload.wikimedia.org/wikipedia/commons/0/0c/OrangeDot.png"
]

group_count = len(tribe_icons)

# -----------------------------
# 대륙별 메인 지점
# -----------------------------
main_route = [
    (10.0, 35.0),    # 아프리카 동부
    (39.0, 35.0),    # 유럽 (터키)
    (60.0, 100.0),   # 아시아 (시베리아)
    (65.0, -170.0),  # 베링 해협
    (60.0, -150.0),  # 북미 (알래스카)
    (-55.0, -70.0),  # 남미 (파타고니아)
]

# -----------------------------
# 대륙별 랜덤 경유지 후보
# -----------------------------
continent_waypoints = {
    "africa": [
        (5.0, 20.0),   # 사헬
        (15.0, 30.0),  # 나일강 유역
        (-5.0, 25.0),  # 중앙아프리카
        (-20.0, 25.0), # 남아프리카
    ],
    "europe": [
        (45.0, 20.0),  # 발칸
        (50.0, 10.0),  # 중앙유럽
        (40.0, -5.0),  # 이베리아 반도
    ],
    "asia": [
        (50.0, 90.0),  # 몽골
        (35.0, 100.0), # 중국 내륙
        (30.0, 80.0),  # 인도 북부
    ],
    "north_america": [
        (50.0, -110.0), # 로키산맥
        (40.0, -95.0),  # 대평원
        (30.0, -85.0),  # 멕시코만 연안
    ],
    "south_america": [
        (0.0, -65.0),   # 아마존
        (-15.0, -70.0), # 안데스
        (-30.0, -55.0), # 팜파스
    ]
}

# -----------------------------
# 부족별 경로 생성
# -----------------------------
def build_path():
    path = []
    # 아프리카 시작
    path.append(main_route[0])
    if np.random.rand() < 0.7:
        path.append(continent_waypoints["africa"][np.random.randint(len(continent_waypoints["africa"]))])
    # 유럽
    path.append(main_route[1])
    if np.random.rand() < 0.5:
        path.append(continent_waypoints["europe"][np.random.randint(len(continent_waypoints["europe"]))])
    # 아시아
    path.append(main_route[2])
    if np.random.rand() < 0.7:
        path.append(continent_waypoints["asia"][np.random.randint(len(continent_waypoints["asia"]))])
    # 베링 해협
    path.append(main_route[3])
    path.append(main_route[4])
    if np.random.rand() < 0.7:
        path.append(continent_waypoints["north_america"][np.random.randint(len(continent_waypoints["north_america"]))])
    # 남미
    if np.random.rand() < 0.7:
        path.append(continent_waypoints["south_america"][np.random.randint(len(continent_waypoints["south_america"]))])
    path.append(main_route[5])
    return path

tribe_paths = [build_path() for _ in range(group_count)]

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
# 보간 함수 (프레임 → 좌표)
# -----------------------------
def interpolate_path(path, t):
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
colors = [
    [255, 0, 0],
    [0, 0, 255],
    [0, 255, 0],
    [255, 165, 0],
    [255, 255, 0],
]

path_layers = []
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

view_state = pdk.ViewState(latitude=20, longitude=0, zoom=2)

r = pdk.Deck(
    layers=[icon_layer] + path_layers,
    initial_view_state=view_state,
    map_style=None
)

with col2:
    st.pydeck_chart(r, use_container_width=True)

# -----------------------------
# 애니메이션 진행
# -----------------------------
if st.session_state.play:
    time.sleep(play_speed/1000.0)
    st.session_state.frame = (frame + 5) % (len(main_route) * 100)
    st.rerun()
