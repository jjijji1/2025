# app.py
import streamlit as st
import random

st.set_page_config(page_title="공룡 연애 시뮬레이션", page_icon="🦖", layout="centered")

st.title("🦕 타이타노사우루스 ♥ 알로사우루스 연애 시뮬레이터")
st.write("적극적인 타이타노사우루스와 소심하지만 강단 있는 알로사우루스의 연애 경로를 추정합니다.")

# 사용자 변수 입력
st.subheader("💬 상황 설정")
date_location = st.selectbox("첫 데이트 장소", ["초원 소풍", "화산 근처 탐험", "강가 낚시", "거대한 숲 속 산책"])
conflict_level = st.slider("성격 차이 정도 (0=거의 없음, 10=매우 큼)", 0, 10, 5)
random_seed = st.number_input("랜덤 시드 (같은 번호면 같은 결과)", min_value=0, value=0)

# 시뮬레이션 로직
if st.button("💖 시뮬레이션 시작"):
    random.seed(random_seed)

    # 단계별 시뮬레이션
    intro = f"첫 만남은 '{date_location}'에서 시작됩니다. 타이타노사우루스는 활짝 웃으며 먼저 말을 걸고, 알로사우루스는 조심스럽게 대답합니다."
    
    # 친밀감 형성
    closeness_roll = random.randint(0, 10)
    if closeness_roll > 4:
        closeness = "타이타노의 적극적인 성격에 알로사우루스가 조금씩 마음을 열기 시작합니다."
    else:
        closeness = "알로사우루스는 아직 마음을 열지 않고 조심스러운 태도를 유지합니다."
    
    # 갈등 단계
    conflict_roll = conflict_level + random.randint(-3, 3)
    if conflict_roll < 4:
        conflict = "둘은 큰 갈등 없이 서로의 성격을 존중합니다."
    elif conflict_roll < 7:
        conflict = "작은 의견 차이가 있지만, 대화를 통해 해결합니다."
    else:
        conflict = "성격 차이가 커져 서로 서운한 감정을 느낍니다."
    
    # 결말
    ending_roll = random.randint(0, 10)
    if ending_roll > 7:
        ending = "🌸 해피 엔딩: 서로의 다름을 존중하며 평생 함께합니다."
    elif ending_roll > 4:
        ending = "🔥 열정 폭발 엔딩: 짧지만 강렬한 사랑 후 각자의 길을 갑니다."
    else:
        ending = "🌿 우정 엔딩: 친구로 남아 서로를 응원합니다."
    
    # 출력
    st.subheader("📜 시뮬레이션 결과")
    st.write(intro)
    st.write(closeness)
    st.write(conflict)
    st.write(f"**결말:** {ending}")
