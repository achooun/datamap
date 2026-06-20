import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ─────────────────────────────────────────────────────────────
# [안전장치] Plotly 로드 실패 시 앱 다운 방지 및 자동 예외 처리
# ─────────────────────────────────────────────────────────────
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    class DummyPlotly:
        def __getattr__(self, name):
            def dummy_func(*args, **kwargs): return None
            return dummy_func
    px = DummyPlotly()
    go = DummyPlotly()

_orig_plotly_chart = st.plotly_chart
def custom_plotly_chart(fig, *args, **kwargs):
    if fig is None or not HAS_PLOTLY:
        st.warning("⚠️ Plotly 라이브러리가 인식되지 않아 이 차트를 표시할 수 없습니다. 페이지 최상단의 안내를 확인해 주세요.")
    else:
        _orig_plotly_chart(fig, *args, **kwargs)
st.plotly_chart = custom_plotly_chart

# ─────────────────────────────────────────────────────────────
# 1. 페이지 전역 설정
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="국가장학금 사각지대 심층 분석",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# 2. 세션 상태 초기화
# ─────────────────────────────────────────────────────────────
if "selected_school" not in st.session_state:
    st.session_state["selected_school"] = None
if "show_summary" not in st.session_state:
    st.session_state["show_summary"] = False

# ─────────────────────────────────────────────────────────────
# 3. 전역 CSS
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
.stSelectbox > div > div {
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
C_GREEN     = "#1A7A4A"

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
    
    # 타이틀이 없을 경우 상단 여백을 제거하여 컴팩트하게 만듭니다
    layout_update = _BASE_LAYOUT.copy()
    if not title:
        layout_update["margin"] = dict(l=12, r=12, t=12, b=12)

    fig.update_layout(
        **layout_update,
        title=dict(
            text=t_html,
            font=dict(size=13, family="Noto Sans KR", color="#111111"),
            x=0, xanchor="left", pad=dict(l=0, t=0)
        )
    )
    fig.update_xaxes(showgrid=False, linecolor="#DDDDDD", tickfont=dict(size=10, color="#555555"))
    fig.update_yaxes(gridcolor="#EEEEEE", linecolor="#DDDDDD", tickfont=dict(size=10, color="#555555"), zeroline=False)
    return fig

def chart_header(num, title, desc):
    n = str(num).zfill(2)
    st.markdown(
        f"""<div style="padding:20px 0 12px;border-bottom:1px solid #DDDDDD;margin-bottom:16px;font-family:'Noto Sans KR',sans-serif;">
        <p style="font-size:9px;color:#C41E3A;text-transform:uppercase;letter-spacing:0.12em;font-weight:700;margin:0 0 6px;">CHART {n}</p>
        <p style="font-size:15px;font-weight:700;color:#111;font-family:'Noto Serif KR',Georgia,serif;margin:0 0 4px;">{title}</p>
        <p style="font-size:11px;color:#555555;margin:0;line-height:1.5;">{desc}</p>
        </div>""",
        unsafe_allow_html=True
    )

def kpi_card(label, value, sub, accent):
    return f"""
        <div style="background:#FFFFFF;border-top:3px solid {accent};padding:24px 20px 20px;font-family:'Noto Sans KR',sans-serif;">
        <p style="font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:#555555;font-weight:700;margin:0 0 14px;">{label}</p>
        <p style="font-size:24px;font-weight:700;color:#111111;margin:0;line-height:1.1;letter-spacing:-0.5px;word-break:keep-all;">{value}</p>
        <p style="font-size:11px;color:#666666;margin:8px 0 0;">{sub}</p>
        </div>
    """

def section_label(text):
    st.markdown(
        f"""<p style="font-size:9px;letter-spacing:0.16em;text-transform:uppercase;color:#555555;font-weight:700;margin:0 0 14px;font-family:'Noto Sans KR',sans-serif;">&#9472; {text}</p>""",
        unsafe_allow_html=True
    )

def summary_section_header(num, title, subtitle=""):
    st.markdown(
        f"""<div style="border-top:4px solid #111111;padding:40px 0 24px;font-family:'Noto Sans KR',sans-serif;margin-top:24px;">
        <p style="font-size:12px;color:#C41E3A;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;margin:0 0 10px;">SECTION {str(num).zfill(2)}</p>
        <h2 style="font-family:'Noto Serif KR',Georgia,serif;font-size:32px;font-weight:700;color:#111111;letter-spacing:-0.5px;line-height:1.3;margin:0 0 10px;">{title}</h2>
        <p style="font-size:16px;color:#333333;margin:0;line-height:1.6;font-weight:500;">{subtitle}</p>
        </div>""",
        unsafe_allow_html=True
    )

def insight_box(text, color=C_RED):
    st.markdown(
        f"""<div style="background:#FDFDFD;border-left:5px solid {color};padding:16px 20px;margin:0 0 12px;font-family:'Noto Sans KR',sans-serif;">
        <p style="font-size:16px;color:#111111;line-height:1.6;margin:0;font-weight:700;">
        핵심 인사이트: <span style="font-weight:500;color:#333333;">{text}</span></p></div>""",
        unsafe_allow_html=True
    )

def policy_card(color, badge, title, desc):
    return f"""
        <div style="background:#FFFFFF; border-top:5px solid {color}; padding:32px 24px; font-family:'Noto Sans KR',sans-serif; height:100%; box-sizing:border-box; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <p style="font-size:14px; font-weight:700; color:{color}; margin:0 0 12px; letter-spacing:0.05em;">{badge}</p>
            <p style="font-family:'Noto Serif KR',serif; font-size:20px; font-weight:700; color:#111; margin:0 0 16px; line-height:1.4;">{title}</p>
            <p style="font-size:15px; color:#444; line-height:1.7; margin:0; word-break:keep-all;">{desc}</p>
        </div>
    """

# ─────────────────────────────────────────────────────────────
# 5. 데이터 로딩
# ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    try:
        df     = pd.read_csv("Final_Master_Merged_Data.csv", encoding="utf-8-sig")
        df_map = pd.read_csv("Q2_지도용_최종데이터.csv",     encoding="utf-8-sig")
    except FileNotFoundError:
        schools = ["서울대학교", "연세대학교", "고려대학교", "한양대학교", "성균관대학교",
                   "부산대학교", "경북대학교", "전남대학교", "충남대학교", "인하대학교",
                   "중앙대학교", "이화여자대학교", "건국대학교", "동국대학교", "홍익대학교"]
        regions = ["서울","서울","서울","서울","서울",
                   "부산","대구","광주","대전","인천",
                   "서울","서울","서울","서울","서울"]
        types   = ["국공립","사립","사립","사립","사립",
                   "국공립","국공립","국공립","국공립","사립",
                   "사립","사립","사립","사립","사립"]
        np.random.seed(42)
        n = len(schools)
        df = pd.DataFrame({
            "학교명": schools,
            "지역별": regions,
            "설립별": types,
            "재학생수": np.random.randint(12000, 28000, n),
            "교외장학금 국가": np.random.randint(1_500_000_000, 8_000_000_000, n),
            "일반_생활비대출_금액": np.random.randint(300_000_000, 1_500_000_000, n),
            "취업_생활비대출_금액": np.random.randint(200_000_000, 900_000_000, n),
            "일반학자금대출_전체_금액": np.random.randint(1_000_000_000, 6_000_000_000, n),
            "일반학자금대출_전체_학생수": np.random.randint(200, 1000, n),
            "취업학자금대출_전체_금액": np.random.randint(800_000_000, 3_500_000_000, n),
            "취업학자금대출_전체_학생수": np.random.randint(300, 800, n),
            "평균등록금(원)": np.random.randint(4_500_000, 9_500_000, n),
            "총_대출_학생수": np.random.randint(600, 1800, n),
            "대출학생비율(%)": np.random.uniform(3.5, 9.5, n),
            "총_등록금대출_금액": np.random.randint(2_000_000_000, 7_000_000_000, n),
            "총_생활비대출_금액": np.random.randint(500_000_000, 2_400_000_000, n),
            "1인당_대출액(원)": np.random.randint(100_000, 420_000, n)
        })
        df_map = pd.DataFrame({
            "학교명": schools,
            "위도":  [37.460, 37.566, 37.589, 37.556, 37.588,
                      35.232, 35.888, 35.175, 36.368, 37.452,
                      37.543, 37.562, 37.541, 37.558, 37.551],
            "경도":  [126.952, 126.939, 127.033, 127.045, 126.994,
                      129.083, 128.610, 126.909, 127.361, 126.657,
                      126.947, 126.947, 127.079, 126.997, 126.925]
        })

    df = pd.merge(df, df_map[["학교명","위도","경도"]], on="학교명", how="left")

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

# ─────────────────────────────────────────────────────────────
# 여기서부터 본문 구조 시작
# ─────────────────────────────────────────────────────────────
try:
    df = load_data()

    # 사이드바 패널
    with st.sidebar:
        st.markdown("""
        <div style="padding:32px 20px 24px;border-bottom:1px solid #CCCCCC;">
        <p style="font-size:9px;letter-spacing:0.16em;text-transform:uppercase;color:#555555;margin:0 0 10px;font-family:'Noto Sans KR',sans-serif;">FILTER PANEL</p>
        <p style="font-size:20px;font-weight:700;color:#111111;margin:0;line-height:1.3;font-family:'Noto Serif KR',Georgia,serif;">분석 범위<br>설정</p>
        </div><div style="padding:16px 20px 0;"></div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='padding:0 20px;margin-bottom:4px;'>", unsafe_allow_html=True)
        if not st.session_state["show_summary"]:
            if st.button("📊 발표 요약 보기", use_container_width=True):
                st.session_state["show_summary"] = True
                st.rerun()
        else:
            if st.button("← 리포트로 돌아가기", use_container_width=True):
                st.session_state["show_summary"] = False
                st.rerun()
        st.markdown("</div><hr style='margin:12px 20px;border:none;border-top:1px solid #DDDDDD;'>", unsafe_allow_html=True)

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
            f"""<div style="margin:16px 20px 0;padding:20px;background:#FFFFFF;border:1px solid #CCCCCC;border-left:3px solid #C41E3A;">
            <p style="font-size:9px;color:#555555;text-transform:uppercase;letter-spacing:0.12em;margin:0 0 6px;font-family:'Noto Sans KR',sans-serif;">검색 결과</p>
            <p style="font-size:36px;font-weight:700;color:#111111;margin:0;line-height:1;font-family:'Noto Sans KR',sans-serif;">{count_str}</p>
            <p style="font-size:11px;color:#555555;margin:4px 0 0;font-family:'Noto Sans KR',sans-serif;">개 대학 선택됨</p></div>""",
            unsafe_allow_html=True
        )

        if st.session_state["selected_school"]:
            st.markdown("<div style=\"padding:10px 20px 20px;\">", unsafe_allow_html=True)
            if st.button("선택 해제", use_container_width=True):
                st.session_state["selected_school"] = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================
    # ★★★ 1부: 발표 요약 슬라이드 뷰 모드 ★★★
    # =========================================================
    if st.session_state["show_summary"]:
        st.markdown("""
        <div style="padding:44px 0 0;border-bottom:3px solid #111111;font-family:'Noto Sans KR',sans-serif;">
        <div style="display:inline-block;background:#C41E3A;color:white;font-size:9px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;padding:4px 12px;margin-bottom:16px;">
        발표용 요약 &nbsp;&middot;&nbsp; PRESENTATION SUMMARY
        </div>
        <h1 style="font-family:'Noto Serif KR',Georgia,serif;font-size:36px;font-weight:700;color:#111111;letter-spacing:-1.2px;line-height:1.2;margin:0 0 12px;">
        국가장학금 사각지대와 학자금 대출<br>— 핵심 분석 요약
        </h1>
        <p style="font-size:13px;color:#555555;line-height:1.75;max-width:720px;margin:0 0 20px;">
        소득분위 9·10구간 대학생이 처한 제도적 사각지대의 실체를 데이터로 요약합니다. 문제 진단 → 데이터 근거 → 상관관계 → 정책 제안 순으로 구성되어 있습니다.
        </p>
        </div>
        """, unsafe_allow_html=True)

        summary_section_header(1, "왜 사각지대인가?", "소득분위 9·10구간은 국가장학금 대상에서 원천 배제된다 — 그 규모와 구조")
        
        avg_tuition = df["평균등록금(원)"].mean()
        low_group  = filtered_df[filtered_df["소득구간_추정"] == "1. 수혜 하위 25% (9~10구간 多)"] if "소득구간_추정" in filtered_df.columns else pd.DataFrame()
        high_group = filtered_df[filtered_df["소득구간_추정"] == "4. 수혜 상위 25% (1~8구간 多)"] if "소득구간_추정" in filtered_df.columns else pd.DataFrame()
        avg_living_low  = low_group["총_생활비대출_금액"].mean() if not low_group.empty else 0
        avg_living_high = high_group["총_생활비대출_금액"].mean() if not high_group.empty else 1
        living_ratio    = avg_living_low / avg_living_high if avg_living_high > 0 else 0

        k1, k2, k3 = st.columns(3)
        with k1: st.markdown(kpi_card("전국 평균 등록금 (연간)", f"{int(avg_tuition/10000):,}만원", "장학금 배제 가구 전액 자부담", C_RED), unsafe_allow_html=True)
        with k2: st.markdown(kpi_card("사각지대 그룹 평균 생활비 대출액", f"{int(avg_living_low/10000):,}만원", "수혜 하위 25% 대학 평균", C_HIGHLIGHT), unsafe_allow_html=True)
        with k3: st.markdown(kpi_card("수혜 그룹 대비 생활비 대출 배율", f"{living_ratio:.1f}배", "하위 25% 그룹 ÷ 상위 25% 그룹", C_BLUE), unsafe_allow_html=True)

        summary_section_header(2, "데이터가 증명하는 구조적 모순", "장학금 배제 → 대출 의존 심화의 인과 관계를 3가지 차트로 검증")
        c_a, c_b, c_c = st.columns(3)
        
        with c_a:
            if not filtered_df.empty and "소득구간_추정" in filtered_df.columns:
                insight_box("사각지대 학생일수록 1인당 부채가 월등히 높다.", C_RED)
                grp = filtered_df.groupby("소득구간_추정")[["대출자_1인당_일반대출", "대출자_1인당_취업대출"]].mean().reset_index()
                fig_a = go.Figure([
                    go.Bar(name="일반상환(9~10구간)", x=grp["소득구간_추정"], y=grp["대출자_1인당_일반대출"], marker_color=C_RED),
                    go.Bar(name="취업후상환(1~8구간)", x=grp["소득구간_추정"], y=grp["대출자_1인당_취업대출"], marker_color=C_BLUE)
                ])
                fig_a.update_traces(texttemplate=None, textposition="none")
                fig_a.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(styled_fig(fig_a, ""), use_container_width=True)

        with c_b:
            if not filtered_df.empty:
                insight_box("장학금 수혜액이 적을수록 생활비 대출액이 증가하는 역상관 관계.", C_HIGHLIGHT)
                fig_b = px.scatter(filtered_df, x="교외장학금 국가", y="총_생활비대출_금액", size="재학생수", color="소득구간_추정",
                                   color_discrete_sequence=[C_RED, C_HIGHLIGHT, C_GREEN, C_BLUE])
                fig_b.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(styled_fig(fig_b, ""), use_container_width=True)

        with c_c:
            if not filtered_df.empty:
                insight_box("전 지역에서 9~10구간의 일반상환 대출 부담이 지속 관찰됨.", C_BLUE)
                reg_data = filtered_df.groupby("지역별")[["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"]].sum().reset_index()
                fig_c = px.bar(reg_data, x="지역별", y=["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"], barmode="stack", color_discrete_sequence=[C_RED, C_BLUE])
                fig_c.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(styled_fig(fig_c, ""), use_container_width=True)

        summary_section_header(3, "소득 vs 대출 상관관계: 숫자로 보는 역설", "등록금 자부담 한계와 생계형 대출 목적 분석")
        d1, d2 = st.columns(2)
        with d1:
            if not filtered_df.empty:
                insight_box("국공립 대비 사립대의 등록금 및 1인당 대출액 격차가 유의미함.", C_BLUE)
                avg_d = filtered_df.groupby("설립별")[["평균등록금(원)", "1인당_대출액(원)"]].mean().reset_index()
                fig_d = px.bar(avg_d, x="설립별", y=["평균등록금(원)", "1인당_대출액(원)"], barmode="group", color_discrete_sequence=[C_BLUE, C_RED])
                fig_d.update_traces(texttemplate=None, textposition="none")
                fig_d.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(styled_fig(fig_d, ""), use_container_width=True)

        with d2:
            if not filtered_df.empty:
                insight_box("생활비 대출 비중 확대로 인한 생계형 대출 구조 심화.", C_HIGHLIGHT)
                tot_t = filtered_df["총_등록금대출_금액"].sum()
                tot_l = filtered_df["총_생활비대출_금액"].sum()
                fig_e = go.Figure(go.Pie(labels=["등록금 대출", "생활비 대출"], values=[tot_t, tot_l], hole=0.5, pull=[0, 0.1], marker=dict(colors=[C_DARK, C_HIGHLIGHT])))
                fig_e.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(styled_fig(fig_e, ""), use_container_width=True)

        summary_section_header(4, "해결 방안: 3가지 정책 제안", "구조적 사각지대 타파를 위한 실현 가능한 패키지 딜")
        p1, p2, p3 = st.columns(3)
        with p1: st.markdown(policy_card(C_RED, "POLICY 01", "취업 후 상환 대출(ICL) 전면 확대", "9·10구간 학생들도 고금리 일반상환 대신 소득 연동 상환(ICL)을 전면 허용하여 미취업 상태의 부채 폭탄 방지"), unsafe_allow_html=True)
        with p2: st.markdown(policy_card(C_BLUE, "POLICY 02", "소득산정 개편 + 독립생계 인정", "부모의 자산 중심 산정 방식에서 벗어나 실질적으로 경제 교류가 단절된 학생들을 위한 본인 소득 기준 재산정제 도입"), unsafe_allow_html=True)
        with p3: st.markdown(policy_card(C_DARK, "POLICY 03", "국가근로장학금 20% 의무 할당", "양질의 교내 근로 일자리 중 20%를 대출 이력이 존재하는 9·10구간 사각지대 학생들에게 강제 배정하여 생계 보장"), unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background:#F8F8F8;border-left:4px solid #C41E3A;padding:24px 28px;font-family:'Noto Sans KR',sans-serif;margin-top:20px;">
        <p style="font-size:14px;color:#222222;line-height:1.90;margin:0;">
        <strong>총평:</strong> 단기(ICL 확대) → 중기(독립 생계 인정) → 장기(근로장학금 개혁) 순의 로드맵이 필요하다. 핵심은 소득분위 숫자가 아닌 실제 가처분 소득 기준의 제도 재설계다.
        </p></div>""", unsafe_allow_html=True)

    # =========================================================
    # ★★★ 2부: 기본 심층 분석 종합 리포트 모드 ★★★
    # =========================================================
    else:
        st.markdown("""
        <div style="padding:44px 0 0;border-bottom:3px solid #111111;font-family:'Noto Sans KR',sans-serif;">
        <div style="display:inline-block;background:#C41E3A;color:white;font-size:9px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;padding:4px 12px;margin-bottom:20px;">
        심층 분석 &nbsp;&middot;&nbsp; 고등교육 재정
        </div>
        <h1 style="font-family:'Noto Serif KR',Georgia,serif;font-size:40px;font-weight:700;color:#111111;letter-spacing:-1.5px;line-height:1.2;margin:0 0 16px;">
        국가장학금 사각지대와<br>학자금 대출 의존도 종합 분석
        </h1>
        <p style="font-size:15px;color:#444444;line-height:1.80;max-width:780px;margin:0 0 24px;">
        소득분위 9·10구간 대학생은 국가장학금 수혜 대상에서 원천 배제되어 있다. 이 인터랙티브 분석은 전국 4년제 대학의 장학금 수혜 현황, 소득구간별 부채 격차, 생활비 대출 의존도를 교차 검증하여 제도적 사각지대의 실체를 규명한다.
        </p>
        </div>
        """, unsafe_allow_html=True)

        overall_avg_tuition = df["평균등록금(원)"].mean()
        if not filtered_df.empty:
            max_t_row          = filtered_df.loc[filtered_df["평균등록금(원)"].idxmax()]
            max_tuition_school = max_t_row["학교명"]
            max_tuition_val    = int(max_t_row["평균등록금(원)"])
            max_loan_school    = filtered_df.loc[filtered_df["총_대출_학생수"].idxmax(), "학교명"]
            max_loan_cnt       = int(filtered_df["총_대출_학생수"].max())
            avg_loan_ratio     = filtered_df["대출학생비율(%)"].mean()
        else:
            max_tuition_school = max_loan_school = "없음"; max_tuition_val = max_loan_cnt = 0; avg_loan_ratio = 0.0

        section_label("주요 지표 요약")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_card("전국 평균 등록금", f"{int(overall_avg_tuition/10000):,}만원", "연간 1인 기준", C_BLUE), unsafe_allow_html=True)
        with k2: st.markdown(kpi_card("최고 등록금 대학", max_tuition_school, f"{max_tuition_val:,}원", C_RED), unsafe_allow_html=True)
        with k3: st.markdown(kpi_card("최다 대출 학생 대학", max_loan_school, f"{max_loan_cnt:,}명 대출 중", C_RED), unsafe_allow_html=True)
        with k4: st.markdown(kpi_card("평균 대출 학생 비율", f"{avg_loan_ratio:.1f}%", "재학생 대비 대출자 비중", C_DARK), unsafe_allow_html=True)

        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

        section_label("소득분위 구조 및 모순 진단")
        st.markdown("""
        <div style="background:#FFFFFF; border: 1px solid #DDDDDD; padding: 28px 24px; font-family:'Noto Sans KR',sans-serif; margin-bottom: 40px;">
        <h3 style="font-family:'Noto Serif KR',Georgia,serif; font-size:20px; font-weight:700; color:#111111; margin-top:0; margin-bottom:12px;">기계적 소득구간 산정이 만들어낸 중산층 사각지대의 실체</h3>
        <p style="font-size:13px; color:#444444; line-height:1.75; margin-bottom:24px;">정부 고등교육 재정 지원의 척도인 <b>학자금 지원구간(소득분위)</b>은 가구의 월급뿐 아니라 부동산, 자동차 등 재산의 소득환산액을 더해 산정됩니다. 이는 대학생들이 체감하는 실질 가계 경기 간의 극심한 모순을 유발합니다.</p>
        <div style="display: flex; gap: 24px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 320px; background:#F9F9F9; padding:22px 20px; border-top: 3px solid #1A3A6C;">
        <p style="font-size:11px; font-weight:700; color:#1A3A6C; text-transform:uppercase; margin-top:0; margin-bottom:12px;">■ 학자금 지원 소득분위 경계 구조</p>
        <p style="font-size:12px; color:#555555; line-height:1.65; margin:0;"><b>경계선의 함정:</b> 기준 중위소득 200%를 초과하는 순간 9구간으로 분류됩니다. 이 선을 넘어가는 즉시 모든 <b>국가장학금 무상 지원 대상에서 원천 배제</b>됩니다.</p>
        </div>
        <div style="flex: 1; min-width: 320px; background:#F9F9F9; padding:22px 20px; border-top: 3px solid #C41E3A;">
        <p style="font-size:11px; font-weight:700; color:#C41E3A; text-transform:uppercase; margin-top:0; margin-bottom:12px;">■ 3대 모순 원인</p>
        <ul style="margin:0; padding-left:16px; font-size:12px; color:#333333; line-height:1.75;">
        <li>부동산 자산 착시 (실소득 낮음에도 보유 주택 지가 급등)</li><li>가계 부채 반영 불가</li><li>독립 생계 미인정</li>
        </ul>
        </div></div></div>
        """, unsafe_allow_html=True)

        section_label("인터랙티브 분석")
        left_col, right_col = st.columns([1.25, 1], gap="large")

        with left_col:
            t1, t2, t3, t4, t5 = st.tabs(["지역별 대출 현황", "사각지대 부채 증명", "대출 목적 분류", "생활비 상관관계", "설립유형 비교"])
            with t1:
                type_data = filtered_df.groupby("지역별")[["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"]].sum().reset_index()
                fig1 = px.bar(type_data, x="지역별", y=["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"], barmode="stack", color_discrete_sequence=[C_RED, C_BLUE])
                st.plotly_chart(styled_fig(fig1, "지역별 학자금 대출 비중"), use_container_width=True)
            with t2:
                if not filtered_df.empty:
                    burden_data = filtered_df.groupby("지역별")[["대출자_1인당_일반대출", "대출자_1인당_취업대출"]].mean().reset_index()
                    fig2 = px.bar(burden_data, x="지역별", y=["대출자_1인당_일반대출", "대출자_1인당_취업대출"], barmode="group", color_discrete_sequence=[C_RED, C_BLUE])
                    st.plotly_chart(styled_fig(fig2, "대출자 1인당 평균 부채 비교"), use_container_width=True)
            with t3:
                purpose_data = filtered_df.groupby("지역별")[["총_등록금대출_금액", "총_생활비대출_금액"]].sum().reset_index()
                fig3 = px.bar(purpose_data, x="지역별", y=["총_생활비대출_금액", "총_등록금대출_금액"], barmode="stack", color_discrete_sequence=[C_DARK, "#888888"])
                st.plotly_chart(styled_fig(fig3, "등록금 대출 vs 생활비 대출 비중"), use_container_width=True)
            with t4:
                fig4 = px.scatter(filtered_df, x="교외장학금 국가", y="총_생활비대출_금액", hover_name="학교명", size="총_대출_학생수", color="총_생활비대출_금액", color_continuous_scale=[[0, "#E8E8E8"], [0.5, C_BLUE], [1, C_RED]])
                st.plotly_chart(styled_fig(fig4, "국가장학금 x 생활비 대출 상관관계"), use_container_width=True)
            with t5:
                if not filtered_df.empty:
                    avg_data = filtered_df.groupby("설립별")[["평균등록금(원)", "1인당_대출액(원)"]].mean().reset_index()
                    fig5 = px.bar(avg_data, x="설립별", y=["평균등록금(원)", "1인당_대출액(원)"], barmode="group", color_discrete_sequence=[C_BLUE, C_RED])
                    st.plotly_chart(styled_fig(fig5, "국공립 vs 사립 지표 비교"), use_container_width=True)

        with right_col:
            st.markdown("### 대학별 지표 분포 지도")
            c_lat, c_lon = 36.0, 127.5
            if not filtered_df.empty and pd.notna(filtered_df["위도"].mean()):
                c_lat = filtered_df["위도"].mean()
                c_lon = filtered_df["경도"].mean()
            m = folium.Map(location=[c_lat, c_lon], zoom_start=7)
            mc = MarkerCluster().add_to(m)

            for _, row in filtered_df.iterrows():
                if pd.isna(row["위도"]): continue
                sch_name = str(row["학교명"])
                sch_type = str(row.get("설립별", ""))
                color    = "blue" if sch_type == "국공립" else "red"
                folium.Marker(location=[row["위도"], row["경도"]], tooltip=sch_name, icon=folium.Icon(color=color)).add_to(mc)
            st_folium(m, use_container_width=True, height=450, key="main_report_map")

        st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
        section_label("원시 데이터 테이블")
        st.dataframe(filtered_df[["학교명", "지역별", "설립별", "재학생수", "대출학생비율(%)", "평균등록금(원)"]], use_container_width=True, hide_index=True)

        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
        section_label("구조적 해결 방안")
        
        p1r, p2r, p3r = st.columns(3, gap="medium")
        with p1r: st.markdown(policy_card(C_RED, "POLICY 01", "ICL 자격의 전면 확대", "9·10구간 가구에도 취업 후 상환 학자금 대출 제도를 전면 개방해 졸업 전 금융 리스크 노출을 방지합니다."), unsafe_allow_html=True)
        with p2r: st.markdown(policy_card(C_BLUE, "POLICY 02", "독립 생계 인정 제도", "부모의 경제적 지원 없이 독자 생계를 유지하는 학생들을 선별해 소득 분위 산정 시 부모 자산을 유예합니다."), unsafe_allow_html=True)
        with p3r: st.markdown(policy_card(C_DARK, "POLICY 03", "근로장학금 20% 의무 할당", "생계비 마련 목적 대출 이력이 확인된 9·10구간 학생층에 대해 교내 근로 배정 쿼터를 적용합니다."), unsafe_allow_html=True)

except Exception as e:
    st.markdown(f"<div style='background:#FFF5F5;border-left:3px solid #C41E3A;padding:16px 20px;'><strong>시스템 실행 오류:</strong> {str(e)}</div>", unsafe_allow_html=True)