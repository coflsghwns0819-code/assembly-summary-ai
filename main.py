import streamlit as st
import pandas as pd

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="국회 주간 일정 브리핑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Assembly Editorial 커스텀 CSS (하얀 글씨 버그 완벽 수정)
st.markdown("""
<style>
/* 전체 배경 (밝은 회백색) */
.stApp {
    background-color: #F7F8F9 !important;
}
p, span, div, h1, h2, h3 {
    color: #333333;
}

/* =========================================
   사이드바 (짙은 청색)
========================================= */
[data-testid="stSidebar"] {
    background-color: #2C4364 !important;
    border-right: none !important;
}

/* ✅ 버그 해결 포인트: 무식하게 모든 글씨를 하얗게 칠하던 코드를 빼고, 
   입력창 위쪽의 '제목(Label)'만 정확히 짚어서 흰색으로 변경! */
[data-testid="stSidebar"] label p,
[data-testid="stSidebar"] label span {
    color: #FFFFFF !important;
    font-weight: 600;
}

/* 사이드바 그룹/섹션 제목 스타일 */
.sidebar-section {
    font-size: 0.85rem;
    font-weight: 600;
    color: #A3B5CC !important;
    margin-bottom: 0.5rem;
    margin-top: 1.5rem;
}

/* 사이드바 입력창 껍데기 (흰색 플랫) */
[data-testid="stSidebar"] div[data-baseweb="input"],
[data-testid="stSidebar"] div[data-baseweb="datepicker"] {
    background-color: #FFFFFF !important;
    border-radius: 4px !important;
    border: none !important;
}

/* ✅ 버그 해결 포인트: 입력창 안에 들어가는 글씨(날짜, 키워드)는 진한 청색으로 확실히 고정! */
[data-testid="stSidebar"] input {
    color: #2C4364 !important;
    -webkit-text-fill-color: #2C4364 !important;
    font-weight: 600 !important;
}

/* 사이드바 '일정 조회하기' 버튼 (흰색 배경, 청색 텍스트) */
[data-testid="stSidebar"] button[kind="primary"] {
    background-color: #FFFFFF !important;
    color: #2C4364 !important;
    border: none;
    font-weight: 700;
    border-radius: 4px;
    padding: 0.5rem 1rem;
    margin-top: 10px;
}
[data-testid="stSidebar"] button[kind="primary"] p {
    color: #2C4364 !important;
}
[data-testid="stSidebar"] button[kind="primary"]:hover {
    background-color: #F0F4F8 !important;
}

/* =========================================
   메인 콘텐츠 (저널 & 에디토리얼)
========================================= */
/* 플랫 콘텐츠 박스 (그림자 제거, 얇은 테두리) */
.editorial-box {
    background-color: #FFFFFF;
    border: 1px solid #E6E8EA;
    border-radius: 6px;
    padding: 24px;
    margin-bottom: 24px;
}

/* 편집형 메타 텍스트 (자색, 청색 등) */
.meta-purple {
    color: #705374;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
}

.title-main {
    color: #222222;
    font-size: 1.6rem;
    font-weight: 800;
    margin: 0 0 0.5rem 0;
}

.desc-text {
    color: #666666;
    font-size: 0.95rem;
    margin-bottom: 1.2rem;
}

/* 자색(퍼플) 테마의 인사이트 박스 */
.insight-box {
    background-color: #F4EFF5;
    color: #705374;
    padding: 1rem 1.2rem;
    border-radius: 4px;
    font-weight: 500;
    border-left: 3px solid #705374;
}

/* 일정 리스트 아이템 */
.schedule-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid #F0F0F0;
}
.schedule-row:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}
.schedule-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.schedule-title {
    color: #222222;
    font-size: 1.05rem;
    font-weight: 700;
}
.schedule-sub {
    color: #888888;
    font-size: 0.9rem;
}

/* 뱃지 시스템 */
.badge {
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
}
.badge-green { background-color: #DDF3E4; color: #2E8B57; }
.badge-blue { background-color: #E3EFFF; color: #4A83FF; }

/* 탭 UI 간소화 */
.stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #E6E8EA; gap: 24px; }
.stTabs [data-baseweb="tab"] { padding-top: 10px; padding-bottom: 10px; }
.stTabs [aria-selected="true"] { border-bottom-color: #2C4364 !important; color: #2C4364 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)


# 3. 사이드바 영역
# 3. 사이드바 영역
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 2rem; margin-top: 1rem;">
        <div style="display: flex; align-items: flex-start; gap: 12px;">
            <!-- 🏛️ 수정한 Lucide Landmark 아이콘 -->
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="3" x2="21" y1="22" y2="22"></line>
                <line x1="6" x2="6" y1="18" y2="11"></line>
                <line x1="10" x2="10" y1="18" y2="11"></line>
                <line x1="14" x2="14" y1="18" y2="11"></line>
                <line x1="18" x2="18" y1="18" y2="11"></line>
                <polygon points="12 2 20 7 4 7"></polygon>
            </svg>
            <div style="line-height: 1.3;">
                <strong style="font-size: 1.3rem; color: #FFFFFF;">국회 브리핑</strong><br>
                <span style="font-size: 0.8rem; color: #A3B5CC; letter-spacing: 0.5px;">ASSEMBLY<br>JOURNAL</span>
            </div>
        </div>
        <hr style="border-color: rgba(255,255,255,0.15); margin-top: 1.5rem;">
    </div>
    """, unsafe_allow_html=True)
    
    # (이 아래부터는 기존의 st.markdown("<div class='sidebar-section'>검색 및 필터</div>" ... 코드가 그대로 이어짐)
    
    st.markdown("<div class='sidebar-section'>검색 및 필터</div>", unsafe_allow_html=True)
    selected_date = st.date_input("조회 기준일")
    keyword = st.text_input("키워드 검색", placeholder="예산, 법안 등")
    search_btn = st.button("일정 조회하기", type="primary", use_container_width=True)
    
    st.markdown("""
    <hr style="border-color: rgba(255,255,255,0.15); margin: 2rem 0 1.5rem 0;">
    <div class='sidebar-section'>NAVIGATION</div>
    
    <style>
    /* 네비게이션 글자와 아이콘 색상을 완벽한 흰색으로 강제 고정 */
    .nav-menu-item {
        color: #FFFFFF !important;
    }
    .nav-menu-item svg {
        stroke: #FFFFFF !important;
    }
    </style>
    
    <div style="display: flex; flex-direction: column; gap: 1rem; font-size: 0.95rem;">
        <div class="nav-menu-item" style="display: flex; align-items: center; gap: 10px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg> 
            주간 의사일정
        </div>
        <div class="nav-menu-item" style="display: flex; align-items: center; gap: 10px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> 
            AI 브리핑
        </div>
    </div>
    """, unsafe_allow_html=True)


# 4. 메인 화면 헤더 (저널 스타일)
st.markdown("""
<div style="margin-bottom: 2rem; margin-top: 0.5rem;">
    <div style="color: #705374; font-weight: 700; letter-spacing: 0.5px; font-size: 0.95rem; margin-bottom: 0.5rem;">WEEKLY LEGISLATIVE REPORT</div>
    <h1 style="color: #222222; font-size: 2.2rem; font-weight: 800; margin: 0;">주간 국회 일정</h1>
    <div style="color: #888888; font-size: 0.95rem; margin-top: 0.5rem;">2026.10.26 — 11.01</div>
    <hr style="border-color: #E6E8EA; margin-top: 1.5rem; margin-bottom: 0;">
</div>
""", unsafe_allow_html=True)


# 5. 메인 탭 분리
tab1, tab2 = st.tabs(["AI 브리핑", "전체 의사일정"])

with tab1:
    if search_btn:
        st.info(f"선택하신 일자({selected_date})의 분석을 시작합니다... (제혁님의 모듈 연동 예정)")
    
    # AI Insight 편집형 박스 (자색 포인트 적용)
    st.markdown("""
    <div class="editorial-box">
        <div class="meta-purple">AI INSIGHT</div>
        <h2 class="title-main">이번 주 핵심 브리핑</h2>
        <p class="desc-text">주요 의정활동 및 입법 현안 요약</p>
        <div class="insight-box">핵심 정책 이슈 01</div>
    </div>
    """, unsafe_allow_html=True)

    
    
    # 주요 의사일정 박스 (하늘색/회색 뱃지)
    st.markdown("""
    <div class="editorial-box">
        <h2 class="title-main" style="margin-bottom: 1.5rem;">주요 의사일정</h2>
        
        <div class="schedule-row">
            <div class="schedule-info">
                <span class="schedule-title">10.26 · 본회의</span>
                <span class="schedule-sub">10:00 · 본회의장</span>
            </div>
            <span class="badge badge-green">확정</span>
        </div>
        
        <div class="schedule-row">
            <div class="schedule-info">
                <span class="schedule-title">10.27 · 상임위원회</span>
                <span class="schedule-sub">14:00 · 위원회 회의</span>
            </div>
            <span class="badge badge-blue">예정</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with tab2:
    st.markdown("""
    <div class="editorial-box">
        <h2 class="title-main">전체 수집 데이터</h2>
        <p class="desc-text">지원님의 fetcher.py 전체 수집 데이터 표가 들어올 자리입니다.</p>
    </div>
    """, unsafe_allow_html=True)