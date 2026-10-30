import streamlit as st

# 1. 페이지 기본 설정 (와이드 모드)
st.set_page_config(
    page_title="국회 일정 요약 서비스",
    page_icon="",
    layout="wide"
)

# 2. 사이드바 영역 (사용자가 검색이나 필터를 조작하는 곳)
with st.sidebar:
    st.header("검색 및 필터")
    selected_date = st.date_input("조회할 날짜를 선택하세요")
    keyword = st.text_input("키워드 검색 (예: 예산, 법안)")
    search_btn = st.button("일정 조회하기", type="primary")

# 3. 메인 화면 타이틀 영역
st.title("주간 국회 일정 자동 요약 브리핑")
st.markdown("국회 의사일정을 자동으로 수집하여 핵심 내용을 AI로 요약해 주는 서비스입니다.")
st.divider()

# 4. 탭으로 화면 나누기 (요약 결과 / 상세 목록)
tab1, tab2 = st.tabs(["✨ AI 요약 브리핑", "📋 전체 일정 목록"])

with tab1:
    st.subheader("이번 주 핵심 브리핑")
    # 나중에 제혁님이 만든 summarizer.py 결과가 들어올 자리
    if search_btn:
        st.info(f"선택하신 날짜({selected_date})의 일정을 분석 중입니다... (여기에 AI 요약 결과가 표시됩니다)")
    else:
        st.write("👈 왼쪽 사이드바에서 날짜를 고르고 조회 버튼을 눌러주세요!")

with tab2:
    st.subheader("수집된 원본 일정 데이터")
    # 나중에 지원님이 만든 fetcher.py 데이터(표)가 들어올 자리
    st.write("아직 데이터가 연동되지 않았습니다. (데이터 수집 모듈이 들어올 자리)")