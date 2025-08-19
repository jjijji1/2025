import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import time

st.set_page_config(page_title="인류 아메리카 이동 시뮬레이션", layout="wide")

# -----------------------------
# 사이드바 파라미터
# -----------------------------
st.sidebar.title("시뮬레이션 설정")
start_year = st.sidebar.number_input("시작 시점 (BP)", 10000, 30000, 20000, step=1000)
speed = st.sidebar.number_input("평균 속도 (km/년)", 0.5, 10.0, 2.0, step=0.1)
variation = st.sidebar.slider("속도 변동(±km/년)", 0.0, 5.0, 1.0)
rest_prob = st.sidebar.slider("연간 휴식 확률", 0.0, 1.0, 0.05)
group_count = st.sidebar.slider("집단 수", 1, 20, 5)
duration = st.sidebar.number_input("총 기간 (년)", 1000, 30000, 10000, step=500)

# -----------------------------
# 부족별 색상/아이콘
# -----------------------------
tribe_icons = [
    "https://upload.wikimedia.org/wikipedia/commons/5/55/Human-icon.png",  # 기본 아이콘
    "https://upload.wikimedia.org/wikipedia/commons/e/e4/RedDot.png",       # 빨강
    "https://upload.wikimedia.org/wikipedia/commons/5/5c/BlueDot.png",      # 파랑
    "https://upload.wikimedia.org/wikipedia/commons/5/51/GreenDot.png",     # 초록
    "https://upload.wikimedia.org/wikipedia/commons/0/0c/OrangeDot.png"     # 주황
]

# -----------------------------
# 기본 경로 (오늘날 터키에서 시작)
# -----------------------------
base_path = [
    (39.0, 35.0),   # 터키
    (60.0, 60.0),   # 시베리아
    (65.0, -170.0), # 베링 해협
    (60.0, -150.0), # 알래스카
    (40.0, -120.0), # 북미 서부
    (20.0, -100.0), # 멕시코
    (-10.0, -60.0), # 아마존
    (-55.0, -70.0), # 남미 최남단 (티에라 델 푸에고)
]

# -----------------------------
# 경유지 후보 (랜덤하게 일부 부족에게만 추가)
# -----------------------------
waypoints = [
    # 아시아/유럽 경유지
    (30.0, 80.0),    # 인도 북부
    (50.0, 90.0),    # 몽골
    (35.0, 100.0),   # 중국 내륙
    (10.0, 40.0),    # 아프리카 동부

    # 북미 경유지
    (50.0, -110.0),  # 로키 산맥
    (40.0, -95.0),   # 대평원
    (30.0, -85.0),   # 멕시코만 연안

    # 남미 경유지
    (0.0, -65.0),    # 아마존 분지
    (-15.0, -70.0),  # 안데스 고원
    (-30.0, -55.0),  # 남미 대평원 (팜파스)
    (-40.0, -60.0),  # 남미 남부 내륙
]

# 부족마다 base_path 중간에 waypoint 삽입
tribe_paths = []
for i in range(group_count):
    p = base_path.copy()
    if np.random.rand() < 0.5:   # 50% 확률로 경유지 하나 추가
        wp = waypoints[np.random.randint(len(waypoints))]
        insert_idx = np.random.randint(1, len(p)-1)
        p.insert(insert_idx, wp)  # 랜덤 위치에 경유지 끼워 넣기
    tribe_paths.append(p)

# -----------------------------
# 고지대 정의 (안데스 산맥 부근)
# -----------------------------
highland_segments = [
    ((0.0, -80.0), (-20.0, -70.0)),
    ((-20.0, -70.0), (-40.0, -70.0))
]

# -----------------------------
# 거리 계산 함수
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2.0)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2.0)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# -----------------------------
# 시뮬레이션 실행
# -----------------------------
def simulate():
    np.random.seed(0)
    groups = []
    for g in range(group_count):
        groups.append({"pos": tribe_paths[g][0], "seg": 0, "dist": 0.0, "path": tribe_paths[g]})

    snapshots = []
    for year in range(0, duration, 50):
        snap = []
        for g in groups:
            path = g["path"]
            if g["seg"] >= len(path)-1:
                snap.append((g["pos"], g))
                continue

            base_speed = np.random.normal(speed, variation)
            if np.random.rand() < rest_prob:
                base_speed = 0

            # 고지대 감속
            lat1, lon1 = path[g["seg"]]
            lat2, lon2 = path[g["seg"]+1]
            seg_dist = haversine(lat1, lon1, lat2, lon2)
            factor = 1.0
            for (hl1, hl2) in highland_segments:
                if (min(hl1[0], hl2[0]) <= g["pos"][0] <= max(hl1[0], hl2[0]) and
                    min(hl1[1], hl2[1]) <= g["pos"][1] <= max(hl1[1], hl2[1])):
                    factor = 0.5
            move = base_speed * factor * 50

            g["dist"] += move
            if g["dist"] >= seg_dist:
                g["seg"] += 1
                g["dist"] = 0.0
                if g["seg"] >= len(path)-1:
                    g["pos"] = path[-1]
                else:
                    g["pos"] = path[g["seg"]]
            else:
                ratio = g["dist"] / seg_dist
                g["pos"] = (
                    lat1 + (lat2 - lat1) * ratio,
                    lon1 + (lon2 - lon1) * ratio,
                )
            snap.append((g["pos"], g))
        snapshots.append((year, snap))
    return snapshots

snapshots = simulate()

# -----------------------------
# 애니메이션 상태 관리
# -----------------------------
if "frame" not in st.session_state:
    st.session_state.frame = 0
if "play" not in st.session_state:
    st.session_state.play = False

col1, col2 = st.columns([1,4])
with col1:
    if st.button("▶️ Play" if not st.session_state.play else "⏸️ Pause"):
        st.session_state.play = not st.session_state.play
    play_speed = st.slider("재생 속도 (ms/frame)", 100, 2000, 500, step=100)

with col2:
    frame = st.session_state.frame
    year, snap = snapshots[frame]

    # 부족별 아이콘 레이어 생성
    icon_data = []
    for idx, (pos, g) in enumerate(snap):
        lat, lon = pos
        icon_data.append({
            "lat": lat,
            "lon": lon,
            "icon": {
                "url": tribe_icons[idx % len(tribe_icons)],
                "width": 128,
                "height": 128,
                "anchorY": 128,
            }
        })

    icon_layer = pdk.Layer(
        "IconLayer",
        data=icon_data,
        get_icon="icon",
        get_size=4,
        get_position="[lon, lat]",
        pickable=True
    )

    # 부족별 경로 시각화
    path_layers = []
    for i, tp in enumerate(tribe_paths):
        path_layers.append(
            pdk.Layer(
                "PathLayer",
                data=[{"path": [[lon, lat] for lat, lon in tp]}],
                get_color="[255, 255, 0]",  # 공통 밝은 노란색
                width_scale=2,
                width_min_pixels=2,
            )
        )

    view_state = pdk.ViewState(latitude=20, longitude=-40, zoom=2)

    r = pdk.Deck(layers=[icon_layer] + path_layers, initial_view_state=view_state, map_style="mapbox://styles/mapbox/dark-v9")

    st.pydeck_chart(r)
    st.write(f"현재 연도: {start_year - year} BP")

# -----------------------------
# 애니메이션 루프
# -----------------------------
if st.session_state.play:
    time.sleep(play_speed/1000.0)
    st.session_state.frame = (frame + 1) % len(snapshots)
    st.rerun()
