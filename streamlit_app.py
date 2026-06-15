import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ─────────────────────────────────────────────────────────────
# 1. 페이지 전역 설정
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="국가장학금 사각지대 심층 분석",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# 2. 세션 상태 초기화 (지도 클릭 이벤트 저장용)
# ─────────────────────────────────────────────────────────────
if "selected_school" not in st.session_state:
    st.session_state["selected_school"] = None

# ─────────────────────────────────────────────────────────────
# 3. 전역 CSS — 접근성 강화 버전 (저대비 색상 전면 개선)
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

.stApp, html, body { background-color: #FAFAFA !important; }
.main .block-container { padding: 0 2.5rem 5rem 2.5rem !important; }

[data-testid="stSidebar"] {
    background-color: #F4F4F4 !important;
    border-right: 1px solid #EAEAEA !important;
}
[data-testid="stSidebar"] > div { background-color: #F4F4F4 !important; padding: 0 !important; }
[data-testid="stSidebar"] * { color: #333333 !important; }
[data-testid="stSidebar"] label {
    font-size: 10px !important;
    letter-spacing: 0.10em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    color: #444444 !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1px solid #CCCCCC !important;
    border-radius: 0 !important;
    color: #111111 !important;
    font-size: 12px !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    background: transparent !important;
    border-bottom: 2px solid #CCCCCC !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 0 !important;
    padding: 10px 18px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    color: #777777 !important;
    border-bottom: 3px solid transparent !important;
    margin-bottom: -2px !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
.stTabs [aria-selected="true"] {
    color: #111111 !important;
    background: transparent !important;
    border-bottom: 3px solid #C41E3A !important;
}
.stTabs [data-testid="stTabPanel"] { padding-top: 0 !important; }
.stSelectbox > div > div {
    border-radius: 0 !important;
    border-color: #CCCCCC !important;
    font-size: 13px !important;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #FAFAFA; }
::-webkit-scrollbar-thumb { background: #BBBBBB; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 4. 디자인 상수 및 헬퍼 함수
# ─────────────────────────────────────────────────────────────
C_RED       = "#C41E3A"
C_BLUE      = "#1A3A6C"
C_DARK      = "#333333"
C_HIGHLIGHT = "#FF6B00"

_BASE_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="Noto Sans KR, sans-serif", size=11, color="#333333"),
    margin=dict(l=12, r=12, t=52, b=12),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02,
        xanchor="right", x=1,
        font=dict(size=10, color="#444444"),
        bgcolor="rgba(0,0,0,0)", borderwidth=0
    ),
)

def styled_fig(fig, title="", subtitle=""):
    t_html = "<b>" + title + "</b>" if title else ""
    if subtitle:
        t_html += "<br><span style=\"font-size:10px;color:#555555;\">" + subtitle + "</span>"
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(
            text=t_html,
            font=dict(size=13, family="Noto Sans KR", color="#111111"),
            x=0, xanchor="left", pad=dict(l=0, t=0)
        )
    )
    fig.update_xaxes(showgrid=False, linecolor="#DDDDDD",
                     tickfont=dict(size=10, color="#555555"))
    fig.update_yaxes(gridcolor="#EEEEEE", linecolor="#DDDDDD",
                     tickfont=dict(size=10, color="#555555"), zeroline=False)
    return fig

def chart_header(num, title, desc):
    n = str(num).zfill(2)
    st.markdown(
        "<div style=\"padding:20px 0 12px;border-bottom:1px solid #DDDDDD;margin-bottom:16px;"
        "font-family:'Noto Sans KR',sans-serif;\">"
        "<p style=\"font-size:9px;color:#C41E3A;text-transform:uppercase;letter-spacing:0.12em;"
        "font-weight:700;margin:0 0 6px;\">CHART " + n + "</p>"
        "<p style=\"font-size:15px;font-weight:700;color:#111;"
        "font-family:'Noto Serif KR',Georgia,serif;margin:0 0 4px;\">" + title + "</p>"
        "<p style=\"font-size:11px;color:#555555;margin:0;line-height:1.5;\">" + desc + "</p>"
        "</div>",
        unsafe_allow_html=True
    )

def kpi_card(label, value, sub, accent):
    return (
        "<div style=\"background:#FFFFFF;border-top:3px solid " + accent + ";"
        "padding:24px 20px 20px;font-family:'Noto Sans KR',sans-serif;\">"
        "<p style=\"font-size:9px;letter-spacing:0.12em;text-transform:uppercase;"
        "color:#555555;font-weight:700;margin:0 0 14px;\">" + label + "</p>"
        "<p style=\"font-size:24px;font-weight:700;color:#111111;margin:0;"
        "line-height:1.1;letter-spacing:-0.5px;word-break:keep-all;\">" + value + "</p>"
        "<p style=\"font-size:11px;color:#666666;margin:8px 0 0;\">" + sub + "</p>"
        "</div>"
    )

def section_label(text):
    st.markdown(
        "<p style=\"font-size:9px;letter-spacing:0.16em;text-transform:uppercase;"
        "color:#555555;font-weight:700;margin:0 0 14px;"
        "font-family:'Noto Sans KR',sans-serif;\">&#9472; " + text + "</p>",
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────────
# 5. 데이터 로딩 (원본 로직 완전 유지)
# ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    # 실습용 더미 데이터 생성 (실제 파일이 없을 경우 대비)
    try:
        df     = pd.read_csv("Final_Master_Merged_Data.csv", encoding="utf-8-sig")
        df_map = pd.read_csv("Q2_지도용_최종데이터.csv",     encoding="utf-8-sig")
    except FileNotFoundError:
        # 파일이 없을 경우 대치할 더미 데이터 로직
        schools = ["서울대학교", "연세대학교", "고려대학교", "한양대학교", "성균관대학교"]
        df = pd.DataFrame({
            "학교명": schools,
            "지역별": ["서울", "서울", "서울", "서울", "서울"],
            "설립별": ["국공립", "사립", "사립", "사립", "사립"],
            "재학생수": [20000, 19000, 21000, 18000, 19500],
            "교외장학금 국가": [5000000000, 3000000000, 3200000000, 3400000000, 3100000000],
            "일반_생활비대출_금액": [500000000, 1200000000, 1100000000, 950000000, 1000000000],
            "취업_생활비대출_금액": [800000000, 600000000, 650000000, 700000000, 680000000],
            "일반학자금대출_전체_금액": [1500000000, 4500000000, 4200000000, 3800000000, 4000000000],
            "일반학자금대출_전체_학생수": [300, 800, 750, 680, 720],
            "취업학자금대출_전체_금액": [2500000000, 1800000000, 1900000000, 2100000000, 2000000000],
            "취업학자금대출_전체_학생수": [500, 400, 420, 450, 430],
            "평균등록금(원)": [6000000, 9000000, 8900000, 8500000, 8400000],
            "총_대출_학생수": [800, 1200, 1170, 1130, 1150],
            "대출학생비율(%)": [4.0, 6.3, 5.5, 6.2, 5.9],
            "총_등록금대출_금액": [3000000000, 5100000000, 4900000000, 4200000000, 4500000000],
            "총_생활비대출_금액": [1300000000, 1800000000, 1750000000, 1650000000, 1680000000],
            "1인당_대출액(원)": [150000, 320000, 310000, 290000, 300000]
        })
        df_map = pd.DataFrame({
            "학교명": schools,
            "위도": [37.4598, 37.5657, 37.5894, 37.5564, 37.5882],
            "경도": [126.9519, 126.9385, 127.0325, 127.0446, 126.9936]
        })
    
    df = pd.merge(df, df_map[["학교명", "위도", "경도"]], on="학교명", how="left")

    valid = df["재학생수"] > 0
    df.loc[valid, "1인당_국가장학금"]     = df.loc[valid, "교외장학금 국가"]      / df.loc[valid, "재학생수"]
    df.loc[valid, "1인당_일반생활비대출"] = df.loc[valid, "일반_생활비대출_금액"] / df.loc[valid, "재학생수"]
    df.loc[valid, "1인당_취업생활비대출"] = df.loc[valid, "취업_생활비대출_금액"] / df.loc[valid, "재학생수"]

    df["대출자_1인당_일반대출"] = df["일반학자금대출_전체_금액"] / df["일반학자금대출_전체_학생수"].replace(0, pd.NA)
    df["대출자_1인당_취업대출"] = df["취업학자금대출_전체_금액"] / df["취업학자금대출_전체_학생수"].replace(0, pd.NA)

    if not df[df["1인당_국가장학금"].notna()].empty:
        df["소득구간_추정"] = pd.qcut(
            df["1인당_국가장학금"].rank(method="first"), 4,
            labels=[
                "1. 수혜 하위 25% (9~10구간 多)", "2. 수혜 중하위",
                "3. 수혜 중상위",                  "4. 수혜 상위 25% (1~8구간 多)"
            ]
        )
    return df


try:
    df = load_data()

    # ─────────────────────────────────────────────────────────
    # 6. 사이드바 필터 패널
    # ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
<div style="padding:32px 20px 24px;border-bottom:1px solid #CCCCCC;">
  <p style="font-size:9px;letter-spacing:0.16em;text-transform:uppercase;
            color:#555555;margin:0 0 10px;font-family:'Noto Sans KR',sans-serif;">FILTER PANEL</p>
  <p style="font-size:20px;font-weight:700;color:#111111;margin:0;line-height:1.3;
            font-family:'Noto Serif KR',Georgia,serif;">분석 범위<br>설정</p>
</div>
<div style="padding:20px 20px 0;"></div>
""", unsafe_allow_html=True)

        selected_region = st.selectbox("지역", ["전체"] + sorted(df["지역별"].unique().tolist()))
        selected_type   = st.selectbox("설립유형", ["전체"] + sorted(df["설립별"].unique().tolist()))

        filtered_df = df.copy()
        if selected_region != "전체":
            filtered_df = filtered_df[filtered_df["지역별"] == selected_region]
        if selected_type != "전체":
            filtered_df = filtered_df[filtered_df["설립별"] == selected_type]

        sel = st.session_state["selected_school"]
        if sel and sel not in filtered_df["학교명"].values:
            st.session_state["selected_school"] = None

        count_str = str(len(filtered_df))
        st.markdown(
            "<div style=\"margin:20px 20px 0;padding:20px;background:#FFFFFF;"
            "border:1px solid #CCCCCC;border-left:3px solid #C41E3A;\">"
            "<p style=\"font-size:9px;color:#555555;text-transform:uppercase;letter-spacing:0.12em;"
            "margin:0 0 6px;font-family:'Noto Sans KR',sans-serif;\">검색 결과</p>"
            "<p style=\"font-size:36px;font-weight:700;color:#111111;margin:0;line-height:1;"
            "font-family:'Noto Sans KR',sans-serif;\">" + count_str + "</p>"
            "<p style=\"font-size:11px;color:#555555;margin:4px 0 0;"
            "font-family:'Noto Sans KR',sans-serif;\">개 대학 선택됨</p></div>"
            "<div style=\"padding:24px 20px;margin-top:24px;border-top:1px solid #CCCCCC;\">"
            "<p style=\"font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#555555;"
            "margin:0 0 12px;font-family:'Noto Sans KR',sans-serif;\">범례</p>"
            "<div style=\"display:flex;align-items:center;gap:8px;margin-bottom:8px;\">"
            "<div style=\"width:10px;height:10px;background:#1A3A6C;border-radius:50%;\"></div>"
            "<span style=\"font-size:11px;color:#444444;font-family:'Noto Sans KR',sans-serif;\">국공립 대학</span></div>"
            "<div style=\"display:flex;align-items:center;gap:8px;margin-bottom:8px;\">"
            "<div style=\"width:10px;height:10px;background:#C41E3A;border-radius:50%;\"></div>"
            "<span style=\"font-size:11px;color:#444444;font-family:'Noto Sans KR',sans-serif;\">사립 대학</span></div>"
            "<div style=\"display:flex;align-items:center;gap:8px;\">"
            "<div style=\"width:10px;height:10px;background:#FF6B00;border-radius:50%;\"></div>"
            "<span style=\"font-size:11px;color:#444444;font-family:'Noto Sans KR',sans-serif;\">지도 선택 대학</span></div>"
            "</div>",
            unsafe_allow_html=True
        )

        if st.session_state["selected_school"]:
            st.markdown("<div style=\"padding:0 20px 20px;\">", unsafe_allow_html=True)
            if st.button("선택 해제", use_container_width=True):
                st.session_state["selected_school"] = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # 7. 에디토리얼 마스트헤드
    # ─────────────────────────────────────────────────────────
    st.markdown("""
<div style="padding:44px 0 0;border-bottom:3px solid #111111;font-family:'Noto Sans KR',sans-serif;">
  <div style="display:inline-block;background:#C41E3A;color:white;font-size:9px;font-weight:700;
              letter-spacing:0.18em;text-transform:uppercase;padding:4px 12px;margin-bottom:20px;">
    심층 분석 &nbsp;&middot;&nbsp; 고등교육 재정
  </div>
  <h1 style="font-family:'Noto Serif KR',Georgia,serif;font-size:40px;font-weight:700;
             color:#111111;letter-spacing:-1.5px;line-height:1.2;margin:0 0 16px;">
    국가장학금 사각지대와<br>학자금 대출 의존도 종합 분석
  </h1>
  <p style="font-size:15px;color:#444444;line-height:1.80;max-width:780px;margin:0 0 24px;">
    소득분위 9·10구간 대학생은 국가장학금 수혜 대상에서 원천 배제되어 있다.
    이 인터랙티브 분석은 전국 4년제 대학의 장학금 수혜 현황, 소득구간별 부채 격차,
    생활비 대출 의존도를 교차 검증하여 제도적 사각지대의 실체를 규명한다.
  </p>
  <div style="display:flex;gap:24px;padding:12px 0 16px;border-top:1px solid #CCCCCC;
              font-size:10px;color:#666666;letter-spacing:0.05em;">
    <span>데이터 출처: 한국장학재단 공공데이터 포털</span>
    <span>&nbsp;&middot;&nbsp;</span>
    <span>분석 단위: 전국 4년제 일반대학</span>
    <span>&nbsp;&middot;&nbsp;</span>
    <span>분류 기준: 소득분위 1~10구간</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:36px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # 8. KPI 카드 — 4개 지표
    # ─────────────────────────────────────────────────────────
    overall_avg_tuition = df["평균등록금(원)"].mean()
    if not filtered_df.empty:
        max_t_row          = filtered_df.loc[filtered_df["평균등록금(원)"].idxmax()]
        max_tuition_school = max_t_row["학교명"]
        max_tuition_val    = int(max_t_row["평균등록금(원)"])
        max_loan_school    = filtered_df.loc[filtered_df["총_대출_학생수"].idxmax(), "학교명"]
        max_loan_cnt       = int(filtered_df["총_대출_학생수"].max())
        avg_loan_ratio     = filtered_df["대출학생비율(%)"].mean()
    else:
        max_tuition_school = max_loan_school = "없음"
        max_tuition_val = max_loan_cnt = 0
        avg_loan_ratio  = 0.0

    section_label("주요 지표 요약")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(kpi_card("전국 평균 등록금",
                             f"{int(overall_avg_tuition/10000):,}만원",
                             "연간 1인 기준", C_BLUE), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi_card("최고 등록금 대학", max_tuition_school,
                             f"{max_tuition_val:,}원", C_RED), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi_card("최다 대출 학생 대학", max_loan_school,
                             f"{max_loan_cnt:,}명 대출 중", C_RED), unsafe_allow_html=True)
    with k4:
        st.markdown(kpi_card("평균 대출 학생 비율", f"{avg_loan_ratio:.1f}%",
                             "재학생 대비 대출자 비중", C_DARK), unsafe_allow_html=True)

    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # 8-2. 소득분위 기준 및 사각지대 모순 원인 분석
    # ─────────────────────────────────────────────────────────
    section_label("소득분위 구조 및 모순 진단")
    
    st.markdown("""
<div style="background:#FFFFFF; border: 1px solid #DDDDDD; padding: 28px 24px; font-family:'Noto Sans KR',sans-serif; margin-bottom: 40px;">
<h3 style="font-family:'Noto Serif KR',Georgia,serif; font-size:20px; font-weight:700; color:#111111; margin-top:0; margin-bottom:12px;">
기계적 소득구간 산정이 만들어낸 중산층 사각지대의 실체
</h3>
<p style="font-size:13px; color:#444444; line-height:1.75; margin-bottom:24px;">
정부 고등교육 재정 지원의 척도인 <b>학자금 지원구간(소득분위)</b>은 가구의 월급뿐 아니라 부동산, 자동차 등 '재산의 소득환산액'을 더해 산정됩니다. 
이 기계적 차단선은 통계 수치와 대학생들이 체감하는 실질 가계 경기 간의 극심한 모순을 유발합니다.
</p>

<div style="display: flex; gap: 24px; flex-wrap: wrap;">
<div style="flex: 1; min-width: 320px; background:#F9F9F9; padding:22px 20px; border-top: 3px solid #1A3A6C;">
<p style="font-size:11px; font-weight:700; color:#1A3A6C; text-transform:uppercase; margin-top:0; margin-bottom:12px; letter-spacing:0.05em;">
■ 학자금 지원 소득분위 경계 구조
</p>
<table style="width:100%; border-collapse:collapse; font-size:12px; color:#333333; margin-bottom:12px;">
<tr style="border-bottom:1px solid #EAEAEA;"><td style="padding:7px 0; color:#555555;">기초생활수급자 ~ 8구간</td><td style="text-align:right; font-weight:600; color:#1A3A6C;">기준 중위소득 200% 이하</td></tr>
<tr style="border-bottom:1px solid #EAEAEA;"><td style="padding:7px 0; font-weight:600; color:#C41E3A;">9 ~ 10구간 (제도적 사각지대)</td><td style="text-align:right; font-weight:700; color:#C41E3A;">기준 중위소득 200% 초과</td></tr>
</table>
<p style="font-size:12px; color:#555555; line-height:1.65; margin:0;">
<b>경계선의 함정:</b> 4인 가구 기준 월 소득인정액이 약 1,100만~1,200만 원(중위소득 200%)을 넘는 순간 9구간으로 분류됩니다. 
이 선을 넘어가는 즉시 모든 <b>국가장학금 무상 지원 대상에서 원천 배제</b>되며, 무이자·거치식 대출(ICL) 자격마저 상실됩니다.
</p>
</div>

<div style="flex: 1; min-width: 320px; background:#F9F9F9; padding:22px 20px; border-top: 3px solid #C41E3A;">
<p style="font-size:11px; font-weight:700; color:#C41E3A; text-transform:uppercase; margin-top:0; margin-bottom:12px; letter-spacing:0.05em;">
■ 실질 경제력과 서류상 자산의 3대 모순 원인
</p>
<ul style="margin:0; padding-left:16px; font-size:12px; color:#333333; line-height:1.75;">
<li style="margin-bottom:6px;"><b>부동산 자산 착시:</b> 부모의 실제 월 급여 소득이 평범하더라도 장기 보유한 주택 한 채의 공시지가가 급등하면 자산 환산액이 누적되어 기계적으로 9·10구간에 진입합니다.</li>
<li style="margin-bottom:6px;"><b>가계 부채 차감의 한계:</b> 제1금융권 외 사금융 부채, 형제자매 다자녀 교육비, 노부모 부양비 등 실질적인 가계 고정 지출 부담이 산정 방식에서 배제됩니다.</li>
<li><b>해체 가구 및 명의 모순:</b> 부모의 이혼, 사업 실패, 관계 단절 등으로 실질적인 재정 지원을 전혀 받지 못하는 독자 생계 학생임에도 서류상 부모 자산 때문에 지원 대상에서 탈락합니다.</li>
</ul>
</div>
</div>
</div>
""", unsafe_allow_html=True)
# ─────────────────────────────────────────────────────────
    # 데이터 기반 실질 소득 모순 우회 증명 서술 (추가 코드)
    # ─────────────────────────────────────────────────────────
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    section_label("데이터가 증명하는 실질 소득 착시의 실체")
    
    # 전체 대학 기준 생활비 대출 현황 동적 계산
    if not df.empty:
        total_living_loan = df["총_생활비대출_금액"].sum()
        avg_tuition_val = df["평균등록금(원)"].mean()
        
        # 9~10구간이 많은 대학(장학금 하위 25%)과 1~8구간이 많은 대학(장학금 상위 25%)의 생활비 대출 비교
        if "소득구간_추정" in df.columns:
            low_benefit_group = df[df["소득구간_추정"] == "1. 수혜 하위 25% (9~10구간 多)"]
            high_benefit_group = df[df["소득구간_추정"] == "4. 수혜 상위 25% (1~8구간 多)"]
            
            avg_living_low = low_benefit_group["총_생활비대출_금액"].mean()
            avg_living_high = high_benefit_group["총_생활비대출_금액"].mean()
            
            living_loan_ratio = (avg_living_low / avg_living_high) if avg_living_high > 0 else 1
            ratio_str = f"약 {living_loan_ratio:.1f}배"
        else:
            ratio_str = "유의미한 수준"
    else:
        total_living_loan = 0
        ratio_str = "0배"

    st.markdown(f"""
<div style="background:#FDFDFD; border: 1px solid #E0E0E0; border-left: 4px solid #1A3A6C; padding: 22px 24px; font-family:'Noto Sans KR',sans-serif; margin-bottom: 30px;">
<h4 style="font-family:'Noto Serif KR',Georgia,serif; font-size:16px; font-weight:700; color:#111111; margin-top:0; margin-bottom:10px;">
📊 자산 산정 오류와 '현금 흐름 빈곤'의 통계적 연결고리
</h4>
<p style="font-size:12px; color:#444444; line-height:1.70; margin:0;">
가구의 세부 자산 내역 없이도, 본 대시보드의 <b>학자금 대출 의존도 지표</b>를 통해 서류상 자산(9·10구간)과 실질 경제력 간의 괴리를 증명할 수 있습니다.<br><br>
<b>1. 무상 장학금 배제가 '생계형 대출'로 직결되는 역설:</b><br>
국가장학금 수혜 규모가 가장 적은 '수혜 하위 25% 대학 그룹(9·10구간 집중)'의 대학별 평균 총 생활비 대출 규모는 장학금 수혜가 원활한 상위 그룹 대비 <b>{ratio_str}</b>에 달하는 패턴을 보입니다. 진정한 고소득층 자녀라면 매달 수십만 원의 생활비 조달을 위해 학기 중 대출을 신청할 이유가 없습니다. 즉, 이 구간의 생활비 대출 폭증은 <b>"자산은 잡히나 당장 쓸 수 있는 현금 흐름은 고갈된 중산층 사각지대"</b>의 존재를 방증합니다.<br><br>
<b>2. 등록금 자부담 능력의 결여:</b><br>
전국 평균 등록금이 <b>{int(avg_tuition_val/10000):,}만원</b> 수준에 육박하는 상황에서, 장학금 사각지대 학생들의 일반상환 대출자 1인당 부채가 누적되는 현상은 가계의 실질 저축이나 가처분 소득이 등록금을 감당할 수 없는 상태임을 통계적으로 시사합니다.
</p>
</div>
""", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # 9. 메인 레이아웃 — 차트 탭 (좌) + 지도 (우)
    # ─────────────────────────────────────────────────────────
    section_label("인터랙티브 분석")
    left_col, right_col = st.columns([1.25, 1], gap="large")

    with left_col:
        t1, t2, t3, t4, t5 = st.tabs([
            "지역별 대출 현황", "사각지대 부채 증명",
            "대출 목적 분류",   "생활비 상관관계", "설립유형 비교"
        ])

        # 탭 1: 지역별 대출 유형 비중
        with t1:
            chart_header(1, "지역별 학자금 대출 유형 비중",
                         "일반 상환(9~10구간) vs 취업 후 상환(1~8구간) 대출 총액 지역별 누적 비교")
            type_data = filtered_df.groupby("지역별")[
                ["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"]
            ].sum().reset_index()
            fig1 = px.bar(type_data, x="지역별",
                          y=["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"],
                          barmode="stack", color_discrete_sequence=[C_RED, C_BLUE],
                          labels={"value": "대출 총액 (원)", "variable": "대출 유형"})
            fig1.for_each_trace(lambda t: t.update(name={
                "일반학자금대출_전체_금액": "일반 상환 (9~10구간)",
                "취업학자금대출_전체_금액": "취업 후 상환 (1~8구간)"
            }.get(t.name, t.name)))
            
            st.plotly_chart(styled_fig(fig1), use_container_width=True)

        # 탭 2: 사각지대 부채 증명
        with t2:
            chart_header(2, "소득구간별 대출자 1인당 평균 부채 비교",
                         "장학금 미수혜(9~10구간)의 1인당 부채가 수혜 구간 대비 유의미하게 높은지 검증")
            st.markdown("""
<div style="background:#F8FAFE;border-left:3px solid #1A3A6C;padding:14px 16px;
            margin-bottom:16px;font-family:'Noto Sans KR',sans-serif;">
  <p style="font-size:9px;color:#1A3A6C;font-weight:700;letter-spacing:0.10em;
            text-transform:uppercase;margin:0 0 6px;">분석 가설</p>
  <p style="font-size:12px;color:#333333;margin:0;line-height:1.65;">
    <strong>9~10구간</strong>은 국가장학금 수혜가 전무하여 등록금 전액을
    <strong>일반 상환 대출</strong>(고금리)로 충당해야 한다.
    1인당 부채가 <strong style="color:#C41E3A;">현저히 높게</strong> 나타날수록,
    장학금 사각지대 부담이 악성 부채로 전가되고 있음을 입증한다.
  </p>
</div>
""", unsafe_allow_html=True)
            if not filtered_df.empty:
                burden_data = filtered_df.groupby("지역별")[
                    ["대출자_1인당_일반대출", "대출자_1인당_취업대출"]
                ].mean().reset_index()
                fig2 = px.bar(burden_data, x="지역별",
                              y=["대출자_1인당_일반대출", "대출자_1인당_취업대출"],
                              barmode="group", color_discrete_sequence=[C_RED, C_BLUE],
                              labels={"value": "대출자 1인당 평균 부채 (원)", "variable": "소득구간 구분"})
                fig2.for_each_trace(lambda t: t.update(name={
                    "대출자_1인당_일반대출": "9~10구간 (사각지대)",
                    "대출자_1인당_취업대출": "1~8구간 (수혜 구간)"
                }.get(t.name, t.name)))
                st.plotly_chart(styled_fig(fig2), use_container_width=True)

        # 탭 3: 대출 목적 분류
        with t3:
            chart_header(3, "대출 목적 구조 - 등록금 vs 생활비",
                         "지역별 대출 목적 비중: 생활비 대출 증가는 구조적 빈곤의 지표")
            purpose_data = filtered_df.groupby("지역별")[
                ["총_등록금대출_금액", "총_생활비대출_금액"]
            ].sum().reset_index()
            fig3 = px.bar(purpose_data, x="지역별",
                          y=["총_생활비대출_금액", "총_등록금대출_금액"],
                          barmode="stack", color_discrete_sequence=[C_DARK, "#888888"],
                          labels={"value": "대출 금액 (원)", "variable": "대출 목적"})
            fig3.for_each_trace(lambda t: t.update(name={
                "총_생활비대출_금액": "생활비 대출",
                "총_등록금대출_금액": "등록금 대출"
            }.get(t.name, t.name)))
            st.plotly_chart(styled_fig(fig3), use_container_width=True)

        # 탭 4: 생활비 상관관계 + 지도 크로스필터링
        with t4:
            chart_header(4, "국가장학금 수혜액 x 생활비 대출 상관관계",
                         "수혜 규모가 작은 대학일수록 생활비 대출이 증가하는 역상관 패턴 검증")

            current_sel = st.session_state["selected_school"]

            if current_sel:
                st.markdown(
                    "<div style=\"background:#FFF8E1;border-left:3px solid #FF6B00;"
                    "padding:10px 16px;margin-bottom:14px;"
                    "font-family:'Noto Sans KR',sans-serif;font-size:12px;color:#333333;\">"
                    "지도 연동 활성 &nbsp;|&nbsp; <strong style=\"color:#FF6B00;\">"
                    + current_sel +
                    "</strong> 버블이 강조 표시됩니다."
                    " 사이드바 '선택 해제' 버튼으로 초기화하십시오.</div>",
                    unsafe_allow_html=True
                )

            if not filtered_df.empty:
                plot_df = filtered_df.copy()

                if current_sel and current_sel in plot_df["학교명"].values:
                    df_sel   = plot_df[plot_df["학교명"] == current_sel]
                    df_unsel = plot_df[plot_df["학교명"] != current_sel]

                    # 비선택 대학: hover_data에 재학생수 포함, 저채도 처리
                    fig4 = px.scatter(
                        df_unsel,
                        x="교외장학금 국가", y="총_생활비대출_금액",
                        hover_name="학교명",
                        size="총_대출_학생수",
                        hover_data={
                            "재학생수":          True,
                            "교외장학금 국가":   ":,",
                            "총_생활비대출_금액": ":,",
                            "총_대출_학생수":     False
                        },
                        color="총_생활비대출_금액",
                        color_continuous_scale=[[0, "#E0E0E0"], [1, "#AAAAAA"]],
                        opacity=0.28,
                        labels={
                            "교외장학금 국가":   "국가장학금 수혜 총액 (원)",
                            "총_생활비대출_금액": "생활비 대출 총액 (원)",
                            "재학생수":          "재학생 수 (명)"
                        }
                    )

                    # 선택 대학: 오렌지 강조 버블
                    sel_student = (
                        f"{int(df_sel['재학생수'].iloc[0]):,}"
                        if pd.notna(df_sel["재학생수"].iloc[0]) else "-"
                    )
                    fig4.add_trace(go.Scatter(
                        x=df_sel["교외장학금 국가"],
                        y=df_sel["총_생활비대출_금액"],
                        mode="markers+text",
                        name=current_sel,
                        text=[current_sel],
                        textposition="top center",
                        textfont=dict(size=11, color=C_HIGHLIGHT, family="Noto Sans KR"),
                        marker=dict(
                            size=24, color=C_HIGHLIGHT,
                            line=dict(width=2.5, color="#333333"), symbol="circle"
                        ),
                        hovertemplate=(
                            "<b>" + current_sel + "</b><br>"
                            "국가장학금 수혜 총액: %{x:,}원<br>"
                            "생활비 대출 총액: %{y:,}원<br>"
                            "재학생 수: " + sel_student + "명"
                            "<extra></extra>"
                        ),
                        showlegend=True
                    ))

                else:
                    # 선택 없음: hover_data에 재학생수 포함한 전체 산점도
                    fig4 = px.scatter(
                        plot_df,
                        x="교외장학금 국가", y="총_생활비대출_금액",
                        hover_name="학교명",
                        size="총_대출_학생수",
                        hover_data={
                            "재학생수":          True,
                            "교외장학금 국가":   ":,",
                            "총_생활비대출_금액": ":,",
                            "총_대출_학생수":     False
                        },
                        color="총_생활비대출_금액",
                        color_continuous_scale=[[0, "#E8E8E8"], [0.5, C_BLUE], [1, C_RED]],
                        opacity=0.75,
                        labels={
                            "교외장학금 국가":   "국가장학금 수혜 총액 (원)",
                            "총_생활비대출_금액": "생활비 대출 총액 (원)",
                            "재학생수":          "재학생 수 (명)"
                        }
                    )

                fig4.update_layout(
                    **_BASE_LAYOUT,
                    coloraxis_colorbar=dict(
                        title="생활비<br>대출액", thickness=8, len=0.6,
                        tickfont=dict(size=9, color="#444444")
                    )
                )
                fig4.update_xaxes(showgrid=False, linecolor="#DDDDDD",
                                  tickfont=dict(size=10, color="#555555"))
                fig4.update_yaxes(gridcolor="#EEEEEE", linecolor="#DDDDDD",
                                  zeroline=False, tickfont=dict(size=10, color="#555555"))
                st.plotly_chart(fig4, use_container_width=True)

        # 탭 5: 설립유형 비교
        with t5:
            chart_header(5, "국공립 vs 사립대 - 등록금 및 부채 격차",
                         "설립유형에 따른 평균 등록금과 1인당 대출액의 구조적 차이")
            if not filtered_df.empty:
                avg_data = filtered_df.groupby("설립별")[
                    ["평균등록금(원)", "1인당_대출액(원)"]
                ].mean().reset_index()
                c1, c2 = st.columns(2)
                cmap = {"국공립": C_BLUE, "사립": C_RED}
                with c1:
                    f5a = px.bar(avg_data, x="설립별", y="평균등록금(원)",
                                 color="설립별", text_auto=".2s", color_discrete_map=cmap)
                    f5a.update_traces(textfont_size=10, textposition="outside", marker_line_width=0)
                    st.plotly_chart(styled_fig(f5a, "평균 등록금"), use_container_width=True)
                with c2:
                    f5b = px.bar(avg_data, x="설립별", y="1인당_대출액(원)",
                                 color="설립별", text_auto=".2s", color_discrete_map=cmap)
                    f5b.update_traces(textfont_size=10, textposition="outside", marker_line_width=0)
                    st.plotly_chart(styled_fig(f5b, "1인당 평균 대출액"), use_container_width=True)

    # ─────────────────────────────────────────────────────────
    # 지도 패널
    # ─────────────────────────────────────────────────────────
    with right_col:
        st.markdown("""
<div style="padding:20px 0 12px;border-bottom:1px solid #DDDDDD;margin-bottom:16px;
            font-family:'Noto Sans KR',sans-serif;">
  <p style="font-size:9px;color:#C41E3A;text-transform:uppercase;letter-spacing:0.12em;
            font-weight:700;margin:0 0 6px;">지리적 분포</p>
  <p style="font-size:15px;font-weight:700;color:#111;
            font-family:'Noto Serif KR',Georgia,serif;margin:0 0 4px;">
    대학별 지표 분포 지도</p>
  <p style="font-size:11px;color:#555555;margin:0;line-height:1.5;">
    파란 핀: 국공립 &nbsp;&middot;&nbsp; 빨간 핀: 사립 &nbsp;&mdash;&nbsp;
    <strong style="color:#C41E3A;">마커 클릭 시 차트 04 자동 연동</strong></p>
</div>
""", unsafe_allow_html=True)

        c_lat, c_lon = 36.0, 127.5
        if not filtered_df.empty and pd.notna(filtered_df["위도"].mean()):
            c_lat = filtered_df["위도"].mean()
            c_lon = filtered_df["경도"].mean()

        m = folium.Map(
            location=[c_lat, c_lon], zoom_start=7, min_zoom=6,
            max_bounds=True,
            min_lat=32.0, max_lat=39.0, min_lon=123.0, max_lon=132.0,
            tiles="OpenStreetMap"
        )
        mc = MarkerCluster().add_to(m)

        for _, row in filtered_df.iterrows():
            if pd.isna(row["위도"]):
                continue

            sch_name    = str(row["학교명"])
            sch_type    = str(row.get("설립별", ""))
            color       = "blue" if sch_type == "국공립" else "red"
            ratio_val   = row.get("대출학생비율(%)")
            ratio_str   = f"{ratio_val:.1f}%" if pd.notna(ratio_val) else "데이터 없음"
            decile      = (row["소득구간_추정"]
                           if "소득구간_추정" in row and pd.notna(row["소득구간_추정"])
                           else "알수없음")
            tuition_fmt = f"{int(row['평균등록금(원)']):,}"
            loan_fmt    = f"{int(row['일반학자금대출_전체_금액']):,}"
            student_val = row.get("재학생수")
            student_fmt = f"{int(student_val):,}" if pd.notna(student_val) else "데이터 없음"

            popup_html = (
                "<div style=\"width:260px;font-family:'Noto Sans KR',sans-serif;padding:4px;\">"
                "<div style=\"border-bottom:2px solid #111;padding-bottom:8px;margin-bottom:10px;\">"
                "<p style=\"margin:0;font-size:14px;font-weight:700;color:#111;\">" + sch_name + "</p>"
                "<span style=\"font-size:10px;color:#555555;text-transform:uppercase;"
                "letter-spacing:0.08em;\">" + sch_type + "</span></div>"
                "<table style=\"width:100%;border-collapse:collapse;font-size:11px;\">"
                "<tr><td style=\"color:#555555;padding:4px 0;\">소득구간 추정</td>"
                "<td style=\"color:#111;font-weight:600;text-align:right;\">" + str(decile) + "</td></tr>"
                "<tr><td style=\"color:#555555;padding:4px 0;\">재학생 수</td>"
                "<td style=\"color:#111;font-weight:600;text-align:right;\">" + student_fmt + "명</td></tr>"
                "<tr><td style=\"color:#555555;padding:4px 0;\">평균 등록금</td>"
                "<td style=\"color:#111;font-weight:600;text-align:right;\">" + tuition_fmt + "원</td></tr>"
                "<tr><td style=\"color:#555555;padding:4px 0;\">대출 학생 비율</td>"
                "<td style=\"color:#C41E3A;font-weight:700;text-align:right;\">" + ratio_str + "</td></tr>"
                "<tr><td style=\"color:#555555;padding:4px 0;\">일반상환 대출액</td>"
                "<td style=\"color:#333;font-weight:600;text-align:right;\">" + loan_fmt + "원</td></tr>"
                "</table>"
                "<p style=\"font-size:9px;color:#C41E3A;margin:10px 0 0;text-align:center;"
                "letter-spacing:0.05em;\">클릭하면 차트 04에 강조 표시됩니다</p>"
                "</div>"
            )

            folium.Marker(
                location=[row["위도"], row["경도"]],
                tooltip=sch_name,
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(mc)

        map_data = st_folium(
            m,
            use_container_width=True,
            height=540,
            returned_objects=["last_object_clicked_tooltip"]
        )

        clicked = map_data.get("last_object_clicked_tooltip") if map_data else None
        if clicked:
            clicked_name = str(clicked).strip()
            if (clicked_name in filtered_df["학교명"].values
                    and clicked_name != st.session_state["selected_school"]):
                st.session_state["selected_school"] = clicked_name
                st.rerun()

        if st.session_state["selected_school"]:
            sel_name = st.session_state["selected_school"]
            sel_row  = filtered_df[filtered_df["학교명"] == sel_name]
            if not sel_row.empty:
                r = sel_row.iloc[0]
                r_cnt   = f"{int(r['재학생수']):,}" if pd.notna(r.get("재학생수")) else "-"
                r_ratio = f"{r['대출학생비율(%)']:.1f}%" if pd.notna(r.get("대출학생비율(%)")) else "-"
                st.markdown(
                    "<div style=\"margin-top:12px;padding:14px 16px;background:#FFF8E1;"
                    "border-left:3px solid #FF6B00;font-family:'Noto Sans KR',sans-serif;\">"
                    "<p style=\"font-size:9px;color:#FF6B00;font-weight:700;text-transform:uppercase;"
                    "letter-spacing:0.10em;margin:0 0 8px;\">선택된 대학 - 차트 04 연동 중</p>"
                    "<p style=\"font-size:14px;font-weight:700;color:#111;margin:0 0 6px;\">"
                    + sel_name +
                    "</p>"
                    "<div style=\"display:flex;gap:16px;font-size:11px;color:#444444;\">"
                    "<span>재학생 " + r_cnt + "명</span>"
                    "<span>&nbsp;&middot;&nbsp;</span>"
                    "<span>대출 비율 " + r_ratio + "</span>"
                    "</div></div>",
                    unsafe_allow_html=True
                )

    # ─────────────────────────────────────────────────────────
    # 10. 통합 데이터 테이블
    # ─────────────────────────────────────────────────────────
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
    st.markdown("""
<div style="border-top:3px solid #111111;padding:28px 0 0;font-family:'Noto Sans KR',sans-serif;">
  <p style="font-size:9px;color:#C41E3A;text-transform:uppercase;letter-spacing:0.16em;
            font-weight:700;margin:0 0 10px;">원시 데이터 조회</p>
  <p style="font-size:22px;font-weight:700;color:#111;
            font-family:'Noto Serif KR',Georgia,serif;margin:0 0 6px;">
    전체 대학 통합 상세 데이터</p>
  <p style="font-size:12px;color:#555555;margin:0 0 24px;line-height:1.6;">
    정렬 기준과 방식을 선택하여 개별 대학의 지표를 직접 비교하십시오.</p>
</div>
""", unsafe_allow_html=True)

    cs1, cs2 = st.columns([2, 1])
    with cs1:
        sort_by = st.selectbox("정렬 기준 항목", options=[
            "기본(정렬 없음)", "대출학생비율(%)", "1인당_대출액(원)",
            "대출자_1인당_일반대출", "평균등록금(원)"
        ])
    with cs2:
        sort_order = st.radio("정렬 방식", options=["내림차순", "오름차순"],
                              horizontal=True, disabled=(sort_by == "기본(정렬 없음)"))

    if sort_by != "기본(정렬 없음)":
        table_df = filtered_df.sort_values(sort_by, ascending=("오름차순" in sort_order))
    else:
        table_df = filtered_df.copy()

    display_cols = [
        "학교명", "지역별", "설립별", "소득구간_추정", "재학생수",
        "대출학생비율(%)", "1인당_대출액(원)", "대출자_1인당_일반대출",
        "대출자_1인당_취업대출", "평균등록금(원)"
    ]
    display_df = table_df[[c for c in display_cols if c in table_df.columns]].copy()
    display_df.rename(columns={
        "소득구간_추정":         "소득구간 그룹",
        "평균등록금(원)":        "평균 등록금 (연간, 원)",
        "1인당_대출액(원)":      "재학생 1인당 부채 (원)",
        "대출자_1인당_일반대출": "일반상환 대출자 1인당 부채",
        "대출자_1인당_취업대출": "취업상환 대출자 1인당 부채"
    }, inplace=True)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────────────────
    # 소득구간 그룹 분류 기준 설명 안내 (추가 코드)
    # ─────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────
    # 소득구간 그룹 분류 기준 및 산출 방식 안내 (개선 버전)
    # ─────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:#FFFFFF; border: 1px solid #DDDDDD; padding: 24px 20px; font-family:'Noto Sans KR',sans-serif; margin-top: 16px; margin-bottom: 20px;">
<p style="font-size:11px; font-weight:700; color:#1A3A6C; text-transform:uppercase; margin-top:0; margin-bottom:14px; letter-spacing:0.05em;">
■ 소득구간 그룹 및 1인당 국가장학금 산출 기준 안내
</p>

<!-- 1인당 국가장학금 산출 방식 공식화 지표 -->
<div style="background:#F4F6F9; padding:14px 16px; border-radius:4px; margin-bottom:18px;">
  <p style="font-size:12px; font-weight:600; color:#111111; margin:0 0 6px;">💡 1인당 국가장학금 산출 공식</p>
  <div style="font-size:14px; font-family:'Courier New', monospace; font-weight:700; color:#C41E3A; padding:4px 0;">
    1인당 국가장학금 = 해당 대학의 교외장학금 총액 (국가) ÷ 재학생 수
  </div>
  <p style="font-size:11px; color:#666666; margin:6px 0 0; line-height:1.4;">
    ※ 대학 알리미 및 한국장학재단 공시 데이터를 기반으로 계산되었으며, 재학생 1인이 연간 평균적으로 지급받은 국가장학금 규모를 뜻합니다.
  </p>
</div>

<p style="font-size:12px; color:#444444; line-height:1.65; margin:0 0 12px;">
분석 시 데이터가 존재하는 전체 대학의 <b>'1인당 국가장학금'</b>을 정렬한 뒤, 분위수 기반의 4개 균등 구간(Quantile Cut, 각 25% 비중)으로 자동 분류하여 아래와 같이 명명했습니다.
</p>

<ul style="margin:0; padding-left:18px; font-size:12px; color:#555555; line-height:1.75;">
  <li><b>1. 수혜 하위 25% (9~10구간 多):</b> 1인당 국가장학금 수혜액이 가장 적은 하위 25% 대학 그룹입니다. 소득 기준 초과로 무상 장학금 대상에서 배제된 <b>9·10구간(고소득층 및 사각지대 중산층) 학생의 비중이 상대적으로 높음</b>을 유추할 수 있습니다.</li>
  <li><b>2. 수혜 중하위:</b> 1인당 국가장학금 수혜액 기준 하위 25% 초과 ~ 50% 이하에 해당하는 대학 그룹입니다.</li>
  <li><b>3. 수혜 중상위:</b> 1인당 국가장학금 수혜액 기준 상위 25% 초과 ~ 50% 이하에 해당하는 대학 그룹입니다.</li>
  <li><b>4. 수혜 상위 25% (1~8구간 多):</b> 1인당 국가장학금 수혜액이 가장 많은 상위 25% 대학 그룹입니다. 국가장학금 지원 요건을 충족하는 <b>1~8구간(저소득층 및 서민·중산층) 학생의 비중이 매우 높음</b>을 의미합니다.</li>
</ul>
</div>
""", unsafe_allow_html=True)

    # =========================================================
    # 11. 정책 제안 및 해결 방안 — 에디토리얼 결론 섹션
    # =========================================================
    st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)

    st.markdown("""
<div style="border-top:3px solid #111111;padding:36px 0 0;font-family:'Noto Sans KR',sans-serif;">
  <div style="display:inline-block;background:#1A3A6C;color:white;font-size:9px;font-weight:700;
              letter-spacing:0.18em;text-transform:uppercase;padding:4px 12px;margin-bottom:20px;">
    분석 결론 &nbsp;&middot;&nbsp; 정책 제안
  </div>
  <h2 style="font-family:'Noto Serif KR',Georgia,serif;font-size:32px;font-weight:700;
             color:#111111;letter-spacing:-1px;line-height:1.3;margin:0 0 14px;">
    사각지대 해소를 위한<br>3가지 구조적 해결 방안
  </h2>
  <p style="font-size:14px;color:#444444;line-height:1.80;max-width:820px;margin:0 0 12px;">
    데이터는 9·10구간 학생들이 제도적 배제로 인해 구조적으로 더 많은 부채를 지고 있음을 보여준다.
    이 문제는 단순한 지원 부족이 아닌, 제도 설계의 결함에서 비롯된다.
    아래 세 가지 정책 대안은 예산 효율성과 실현 가능성을 동시에 고려한 현실적 처방이다.
  </p>
  <div style="display:flex;gap:24px;padding:10px 0 28px;border-bottom:1px solid #CCCCCC;
              font-size:10px;color:#666666;letter-spacing:0.05em;">
    <span>우선순위 기준: 예산 효율성 및 즉각적 실현 가능성</span>
    <span>&nbsp;&middot;&nbsp;</span>
    <span>대상: 소득분위 9~10구간 재학생</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3, gap="medium")

    # 가로/세로 여백과 레이아웃 균형을 맞춘 카드 기본 스타일 (고정 높이 대신 100% 채우기로 정렬)
    CARD_STYLE = """
    background: #FFFFFF; 
    border-top: 4px solid {color}; 
    padding: 28px 24px; 
    font-family: 'Noto Sans KR', sans-serif; 
    height: 100%; 
    box-sizing: border-box;
    """

    # ── 정책 1: 취업 후 상환 대출 확대 (실제 데이터 및 은행 리스크 근거 기반) ───────────────────────
    with p1:
        if not filtered_df.empty:
            avg_general_loan = filtered_df["대출자_1인당_일반대출"].mean() # 9~10구간 평균 부채
            avg_income_loan  = filtered_df["대출자_1인당_취업대출"].mean() # 1~8구간 평균 부채
            
            gen_loan_str = f"{int(avg_general_loan/10000):,}만원" if pd.notna(avg_general_loan) else "데이터 없음"
            inc_loan_str = f"{int(avg_income_loan/10000):,}만원" if pd.notna(avg_income_loan) else "데이터 없음"
            
            if pd.notna(avg_general_loan) and pd.notna(avg_income_loan):
                loan_diff_str = f"{int((avg_general_loan - avg_income_loan)/10000):,}만원"
                ratio_diff = f"{abs((avg_general_loan / avg_income_loan) - 1) * 100:.1f}%"
            else:
                loan_diff_str = "비교 불가"
                ratio_diff = "0%"
        else:
            gen_loan_str = inc_loan_str = loan_diff_str = "0원"
            ratio_diff = "0%"

        st.markdown(f"""
<div style="{CARD_STYLE.format(color=C_RED)}">
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:18px;">
    <div style="background:#C41E3A; color:white; font-size:10px; font-weight:700; letter-spacing:0.08em; padding:3px 10px; white-space:nowrap;">
      POLICY 01
    </div>
    <div style="height:1px; background:#EEEEEE; flex:1;"></div>
  </div>
  
  <p style="font-family:'Noto Serif KR',Georgia,serif; font-size:17px; font-weight:700; color:#111111; line-height:1.4; margin:0 0 12px; letter-spacing:-0.3px;">
    '취업 후 상환 대출(ICL)'<br>자격의 전면 확대
  </p>
  <div style="display:inline-block; background:#FFF0F0; border:1px solid #F5C5C5; color:#C41E3A; font-size:9px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; padding:3px 10px; margin-bottom:16px;">
    가장 현실적인 대안
  </div>

  <div style="border-left:3px solid #EEEEEE; padding-left:12px; margin-bottom:16px;">
    <p style="font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#C41E3A; font-weight:700; margin:0 0 4px;">현황</p>
    <p style="font-size:12px; color:#444444; margin:0; line-height:1.65; word-break:keep-all;">
      9·10구간 학생들은 이자가 복리로 누적되는 '일반 상환'만 가능합니다. 현재 범위 내 <b>9~10구간 1인당 부채는 {gen_loan_str}</b>으로, 1~8구간({inc_loan_str})보다 <b>{loan_diff_str}({ratio_diff}) 더 높은 부채</b> 상태입니다.
    </p>
  </div>

  <div style="border-left:3px solid #1A3A6C; padding-left:12px; margin-bottom:16px;">
    <p style="font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#1A3A6C; font-weight:700; margin:0 0 4px;">솔루션</p>
    <p style="font-size:12px; color:#333333; margin:0; line-height:1.65; word-break:keep-all;">
      대출 제도만큼은 9·10구간에도 <strong style="color:#1A3A6C;">'취업 후 상환(ICL)'</strong>을 허용하여 신용불량자 전락 위험을 방지해야 합니다.
    </p>
  </div>

  <div style="border-left:3px solid #FF6B00; padding-left:12px;">
    <p style="font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#FF6B00; font-weight:700; margin:0 0 4px;">은행권 여신 리스크 관리 근거</p>
    <p style="font-size:11px; color:#444444; margin:0; line-height:1.60; word-break:keep-all;">
      <b>1) 연체율 선제 방지:</b> 원금 부담({gen_loan_str})이 월등히 높아 미취업 장기화 시 <b>금융권 대출 연체율 급등 및 대손상각 리스크</b>로 직결되므로 상환을 소득 발생 시점으로 연동하는 것이 안전합니다.<br style="margin-bottom:4px;">
      <b>2) 서류상 자산 착시 제거:</b> 유동성 현금이 부족한 중산층 사각지대에 고금리 거치식 대출을 취급하는 것은 금융사 입장에서도 <b>여신 회수 능력을 과대평가한 부실 심사</b>에 가깝습니다.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── 정책 2: 소득산정 방식 개편 (독립 생계) ────────────────────────────
    with p2:
        st.markdown(f"""
<div style="{CARD_STYLE.format(color=C_BLUE)}">
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:18px;">
    <div style="background:#1A3A6C; color:white; font-size:10px; font-weight:700; letter-spacing:0.08em; padding:3px 10px; white-space:nowrap;">
      POLICY 02
    </div>
    <div style="height:1px; background:#EEEEEE; flex:1;"></div>
  </div>

  <p style="font-family:'Noto Serif KR',Georgia,serif; font-size:17px; font-weight:700; color:#111111; line-height:1.4; margin:0 0 12px; letter-spacing:-0.3px;">
    소득산정 방식 개편 및<br>'독립 생계' 인정제도 도입
  </p>
  <div style="display:inline-block; background:#F0F4FF; border:1px solid #C0CCE8; color:#1A3A6C; font-size:9px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; padding:3px 10px; margin-bottom:16px;">
    제도 설계 개선
  </div>

  <div style="border-left:3px solid #EEEEEE; padding-left:12px; margin-bottom:16px;">
    <p style="font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#C41E3A; font-weight:700; margin:0 0 4px;">현황</p>
    <p style="font-size:12px; color:#444444; margin:0; line-height:1.65; word-break:keep-all;">
      학생 본인의 자산이 0원이어도, <b>부모의 자산이 기준을 초과</b>하면 무조건 고소득 구간(9·10구간)으로 기계적 분류가 이루어집니다.
    </p>
  </div>

  <div style="border-left:3px solid #1A3A6C; padding-left:12px;">
    <p style="font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#1A3A6C; font-weight:700; margin:0 0 4px;">솔루션</p>
    <p style="font-size:12px; color:#333333; margin:0; line-height:1.65; word-break:keep-all;">
      스스로 학비와 생활비를 모두 충당하는 대학생을 공적으로 증명하는 <strong style="color:#1A3A6C;">'독립 생계 가구'</strong> 인정 기준을 신설하고, 부모 자산 제외 후 <b>학생 본인 소득만</b>으로 구간을 재산정해야 합니다.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── 정책 3: 국가근로장학금 문턱 완화 ─────────────────────
    with p3:
        st.markdown(f"""
<div style="{CARD_STYLE.format(color=C_DARK)}">
  <div style="display:flex; align-items:center; gap:10px; margin-bottom:18px;">
    <div style="background:#333333; color:white; font-size:10px; font-weight:700; letter-spacing:0.08em; padding:3px 10px; white-space:nowrap;">
      POLICY 03
    </div>
    <div style="height:1px; background:#EEEEEE; flex:1;"></div>
  </div>

  <p style="font-family:'Noto Serif KR',Georgia,serif; font-size:17px; font-weight:700; color:#111111; line-height:1.4; margin:0 0 12px; letter-spacing:-0.3px;">
    양질의 알바,<br>'국가근로장학금' 문턱 완화
  </p>
  <div style="display:inline-block; background:#F5F5F5; border:1px solid #DDDDDD; color:#444444; font-size:9px; font-weight:700; letter-spacing:0.10em; text-transform:uppercase; padding:3px 10px; margin-bottom:16px;">
    접근성 형평성 개선
  </div>

  <div style="border-left:3px solid #EEEEEE; padding-left:12px; margin-bottom:16px;">
    <p style="font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#C41E3A; font-weight:700; margin:0 0 4px;">현황</p>
    <p style="font-size:12px; color:#444444; margin:0; line-height:1.65; word-break:keep-all;">
      학업 병행에 유리한 <b>국가근로장학금</b>은 소득 8구간 이하에 우선 배정됩니다. 이 때문에 실질적 자금난을 겪는 9·10구간 학생들은 최저시급 야간 알바 전선으로 내몰리게 됩니다.
    </p>
  </div>

  <div style="border-left:3px solid #333333; padding-left:12px;">
    <p style="font-size:9px; letter-spacing:0.12em; text-transform:uppercase; color:#333333; font-weight:700; margin:0 0 4px;">솔루션</p>
    <p style="font-size:12px; color:#333333; margin:0; line-height:1.65; word-break:keep-all;">
      근로장학금 정원의 일부 <strong style="color:#C41E3A;">(예: 20%)</strong>를 '학자금 대출 이력이 존재하는 9·10구간 사각지대 학생'에게 의무 할당하여 빚 대신 <b>노동을 통한 정당한 생계 유지 기회</b>를 제공해야 합니다.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
    st.markdown("""
<div style="background:#F8F8F8;border-left:4px solid #C41E3A;padding:24px 28px;
            font-family:'Noto Sans KR',sans-serif;margin-bottom:48px;">
  <p style="font-size:9px;color:#C41E3A;font-weight:700;letter-spacing:0.14em;
            text-transform:uppercase;margin:0 0 10px;">분석자 총평</p>
  <p style="font-size:14px;color:#222222;line-height:1.85;margin:0;max-width:900px;">
    세 가지 정책은 상호 보완적이다. 단기적으로는 <strong>ICL 확대</strong>가 즉각적 부채 경감 효과를 낼 수 있고,
    중기적으로는 <strong>독립 생계 인정제도</strong>가 구조적 불형평을 교정한다.
    장기적으로는 <strong>근로장학금 배분 개혁</strong>을 통해 고소득 구간으로 분류된 실질적 저소득 학생들이
    제도 안으로 편입되어야 한다. 핵심은 &ldquo;소득 분위 숫자&rdquo;가 아닌
    <strong style="color:#C41E3A;">학생의 실제 가처분 소득</strong>을 기준으로 제도를 재설계하는 것이다.
  </p>
</div>
""", unsafe_allow_html=True)

except Exception as e:
    st.markdown(
        "<div style=\"background:#FFF5F5;border-left:3px solid #C41E3A;padding:16px 20px;"
        "font-family:'Noto Sans KR',sans-serif;\">"
        "<p style=\"font-size:12px;font-weight:700;color:#C41E3A;margin:0 0 6px;\">시스템 실행 오류</p>"
        "<p style=\"font-size:12px;color:#333333;margin:0;\">" + str(e) + "</p></div>",
        unsafe_allow_html=True
    )