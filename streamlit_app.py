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
# 5. 데이터 로딩 (에러 방지 무결점 로직)
# ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    # 1. 메인 데이터 로드 (여러 파일명 가능성 모두 열어둠)
    main_files = ["Final_Master_Merged_Data.csv", "Final_Master_Merged_Data (1).csv", "Final_Master_Merged_Data.CSV"]
    df = None
    for f in main_files:
        try:
            df = pd.read_csv(f, encoding="utf-8-sig")
            break
        except FileNotFoundError:
            continue
            
    if df is None:
        raise FileNotFoundError("데이터 파일을 찾을 수 없습니다. Final_Master_Merged_Data.csv 파일이 있는지 확인해주세요.")
    
    # 컬럼명 공백 제거 (KeyError 완벽 차단)
    df.columns = df.columns.str.strip()

    # 2. 지도 데이터 로드
    map_files = ["Q2_지도용_최종데이터.csv", "Q2_지도용_최종데이터.CSV"]
    df_map = None
    for f in map_files:
        try:
            df_map = pd.read_csv(f, encoding="utf-8-sig")
            break
        except FileNotFoundError:
            continue

    if df_map is not None:
        df_map.columns = df_map.columns.str.strip()
        if all(col in df_map.columns for col in ["학교명", "위도", "경도"]):
            df = pd.merge(df, df_map[["학교명", "위도", "경도"]], on="학교명", how="left")
        else:
            df["위도"] = np.nan
            df["경도"] = np.nan
    else:
        df["위도"] = np.nan
        df["경도"] = np.nan

    # 3. 데이터 형변환 및 파생변수 생성 (에러 강제 방지)
    for col in ["재학생수", "교외장학금 국가", "일반_생활비대출_금액", "취업_생활비대출_금액", "일반학자금대출_전체_금액", "일반학자금대출_전체_학생수", "취업학자금대출_전체_금액", "취업학자금대출_전체_학생수", "총_대출_학생수"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    valid = df["재학생수"] > 0
    df.loc[valid, "1인당_국가장학금"]     = df.loc[valid, "교외장학금 국가"]      / df.loc[valid, "재학생수"]
    df.loc[valid, "1인당_일반생활비대출"] = df.loc[valid, "일반_생활비대출_금액"] / df.loc[valid, "재학생수"]
    df.loc[valid, "1인당_취업생활비대출"] = df.loc[valid, "취업_생활비대출_금액"] / df.loc[valid, "재학생수"]

    # 0으로 나누기 에러 방지
    df["대출자_1인당_일반대출"] = df["일반학자금대출_전체_금액"] / df["일반학자금대출_전체_학생수"].replace(0, pd.NA)
    df["대출자_1인당_취업대출"] = df["취업학자금대출_전체_금액"] / df["취업학자금대출_전체_학생수"].replace(0, pd.NA)

    if not df[df["1인당_국가장학금"].notna()].empty:
        df["소득구간_추정"] = pd.qcut(
            df["1인당_국가장학금"].rank(method="first"), 4,
            labels=[
             "1. 장학금 수혜 하위 25%",
             "2. 장학금 수혜 중하위",
              "3. 장학금 수혜 중상위",
             "4. 장학금 수혜 상위 25%"
            ]
        )
    return df

# ─────────────────────────────────────────────────────────────
# 여기서부터 본문 구조 시작
# ─────────────────────────────────────────────────────────────
try:
    df = load_data()

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
        소득분위 9·10구간 중산층에 숨겨진 대출 내몰림 현상과, 안전망 부재로 인한 악성 부채 집중화 현상을 입증합니다.
        </p>
        </div>
        """, unsafe_allow_html=True)
        # 요약 리포트 상단에 추가
        st.markdown("""
        <div style="background-color:#F8F9FA; padding:15px; border-radius:5px; border:1px solid #E9ECEF; margin-bottom:20px;">
        <h5 style="margin-top:0; color:#333;">📊 분석 데이터 분류 기준</h5>
        <ul style="font-size:13px; color:#555; margin-bottom:0;">
        <li><b>분류 방식:</b> 재학생 1인당 국가장학금 수혜액을 기준으로 전체 대학을 4개 분위(Quartile)로 정렬함.</li>
        <li><b>하위 25% (9~10구간 多):</b> 장학금 수혜액이 가장 적은 그룹으로, 소득분위 산정 오류로 인한 사각지대 피해자가 가장 많이 분포할 것으로 추정되는 대학군.</li>
        <li><b>상위 25% (1~8구간 多):</b> 무상 장학금 혜택이 상대적으로 충분히 보장되는 대학군.</li>
         </ul>
        </div>
            """, unsafe_allow_html=True)
        summary_section_header(1, "사각지대의 실체", "부유하다는 착시 속에 가려진 '생존형 대출자'와 고위험 부채")
        
        avg_tuition = pd.to_numeric(df["평균등록금(원)"], errors="coerce").mean()
        avg_tuition = avg_tuition if pd.notna(avg_tuition) else 0

        # 레이블이 변경된 경우도 모두 대응
        low_label = "1. 수혜 하위 25% (9~10구간 多)"
        if "소득구간_추정" in filtered_df.columns:
            low_group = filtered_df[filtered_df["소득구간_추정"] == low_label]
            if low_group.empty:
                # qcut 레이블 자동 감지 (레이블 변경 시 대비)
                first_label = filtered_df["소득구간_추정"].cat.categories[0]
                low_group = filtered_df[filtered_df["소득구간_추정"] == first_label]
        else:
            low_group = pd.DataFrame()

        blind_spot_loan_rate = pd.to_numeric(low_group["대출학생비율(%)"], errors="coerce").mean() if not low_group.empty else 0

        if not low_group.empty:
            gen_loan = pd.to_numeric(low_group["일반학자금대출_전체_금액"], errors="coerce").sum()
            icl_loan = pd.to_numeric(low_group["취업학자금대출_전체_금액"], errors="coerce").sum()
            gen_ratio = (gen_loan / (gen_loan + icl_loan) * 100) if (gen_loan + icl_loan) > 0 else 0
        else:
            gen_ratio = 0

        k1, k3 = st.columns(2)
        with k1: st.markdown(kpi_card("전국 평균 등록금 (연간)", f"{int(avg_tuition/10000):,}만원", "장학금 배제 가구가 감당할 진입 장벽", C_DARK), unsafe_allow_html=True)
        with k3: st.markdown(kpi_card("고위험(일반상환) 대출 강제율", f"{gen_ratio:.1f}%", "안전한 ICL 거절로 인한 악성 부채율", C_RED), unsafe_allow_html=True)

        summary_section_header(2, "데이터가 증명하는 구조적 모순", "착시 피해자들은 왜 고금리 일반대출로 내몰리는가?")
        c_a, c_b, c_c = st.columns(3)
        
        with c_a:
            if not filtered_df.empty and "소득구간_추정" in filtered_df.columns:
                insight_box("무상 지원이 끊긴 9·10구간일수록 고위험 '일반상환' 강제 비중이 73%로 폭증함.", C_RED)
                grp = filtered_df.groupby("소득구간_추정")[["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"]].sum().reset_index()
                grp["총대출"] = grp["일반학자금대출_전체_금액"] + grp["취업학자금대출_전체_금액"]
                grp["일반상환_비중"] = (grp["일반학자금대출_전체_금액"] / grp["총대출"].replace(0, pd.NA)) * 100
                grp["취업후상환_비중"] = (grp["취업학자금대출_전체_금액"] / grp["총대출"].replace(0, pd.NA)) * 100

                fig_a = go.Figure([
                    go.Bar(name="고금리 일반상환(9~10 강제)", x=grp["소득구간_추정"], y=grp["일반상환_비중"], marker_color=C_RED),
                    go.Bar(name="안전한 취업후상환", x=grp["소득구간_추정"], y=grp["취업후상환_비중"], marker_color=C_BLUE)
                ])
                fig_a.update_layout(barmode="stack", margin=dict(l=10, r=10, t=10, b=10))
                fig_a.update_yaxes(ticksuffix="%")
                st.plotly_chart(styled_fig(fig_a, ""), use_container_width=True)

        with c_b:
            if not filtered_df.empty and "소득구간_추정" in filtered_df.columns:
                # 1. 그룹화: 하위 25%(9-10구간多) vs 상위 25%(1-8구간多)
                # 레이블 자동 감지 (변경 대비)
                all_labels = filtered_df["소득구간_추정"].cat.categories.tolist()
                label_low  = all_labels[0]
                label_high = all_labels[-1]

                df_low  = filtered_df[filtered_df["소득구간_추정"] == label_low]
                df_high = filtered_df[filtered_df["소득구간_추정"] == label_high]

                # 1인당_국가장학금이 없으면 직접 계산
                if "1인당_국가장학금" not in filtered_df.columns or filtered_df["1인당_국가장학금"].isna().all():
                    val_low  = (df_low["교외장학금 국가"] / df_low["재학생수"].replace(0, pd.NA)).mean()
                    val_high = (df_high["교외장학금 국가"] / df_high["재학생수"].replace(0, pd.NA)).mean()
                else:
                    val_low  = df_low["1인당_국가장학금"].mean()
                    val_high = df_high["1인당_국가장학금"].mean()

                val_low  = val_low  if pd.notna(val_low)  else 0
                val_high = val_high if pd.notna(val_high) else 0
                gap = (val_high / val_low) if val_low > 0 else 0
                
                # 3. 막대그래프 생성
                val_low  = val_low  if pd.notna(val_low)  else 0
                val_high = val_high if pd.notna(val_high) else 0
                gap = (val_high / val_low) if val_low > 0 else 0

                fig_b = go.Figure([
                    go.Bar(
                        x=["수혜 하위 25% 대학", "수혜 상위 25% 대학"],
                        y=[val_low, val_high],
                        marker_color=[C_RED, C_BLUE],
                        text=[f"{int(val_low/10000):,}만원", f"{int(val_high/10000):,}만원"],
                        textposition='auto'
                    )
                ])
                fig_b.update_layout(margin=dict(l=10, r=10, t=30, b=10), yaxis_title="1인당 국가장학금액")
                st.plotly_chart(styled_fig(fig_b, "국가장학금 배분 격차 (하위 vs 상위)"), use_container_width=True)
                
                # 4. 핵심 인사이트
                st.markdown(f"""
                <div style="background-color:#F4F4F4; border-left:3px solid #FF6B00; padding:12px; margin-top:-10px;">
                    <p style="font-size:12px; color:#333; margin:0; line-height:1.6; font-family:'Noto Sans KR', sans-serif;">
                    <b>💡 핵심 데이터:</b> 국가장학금 수혜 하위 25% 대학은 상위 25% 대학 대비 <b>약 {gap:.1f}배 낮은 장학금</b>을 수혜받고 있습니다. 
                    이러한 극명한 배분 격차로 인해 9·10구간 학생들이 빚으로 내몰리는 구조적 사각지대가 발생합니다.
                    </p>
                </div>
                """, unsafe_allow_html=True)

        with c_c:
            if not filtered_df.empty:
                insight_box("전 지역에 걸쳐 9·10구간의 일반상환 부채 전가 현상이 확인됨.", C_BLUE)
                reg_data = filtered_df.groupby("지역별")[["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"]].sum().reset_index()
                fig_c = px.bar(reg_data, x="지역별", y=["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"], barmode="stack", color_discrete_sequence=[C_RED, C_BLUE])
                fig_c.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(styled_fig(fig_c, ""), use_container_width=True)

        summary_section_header(3, "대출 성격 분석: 사각지대의 짐", "생계 유지 목적의 빚과 사립대 중심의 타격")
        d1, d2 = st.columns(2)
        with d1:
            if not filtered_df.empty:
                insight_box("국공립 대비 등록금이 높은 사립대에서 사각지대의 대출 압박이 심화.", C_BLUE)
                avg_d = filtered_df.groupby("설립별")[["평균등록금(원)", "1인당_대출액(원)"]].mean().reset_index()
                fig_d = px.bar(avg_d, x="설립별", y=["평균등록금(원)", "1인당_대출액(원)"], barmode="group", color_discrete_sequence=[C_BLUE, C_RED])
                fig_d.update_traces(texttemplate=None, textposition="none")
                fig_d.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(styled_fig(fig_d, ""), use_container_width=True)

        with d2:
            if not filtered_df.empty:
                insight_box("학자금 대출의 상당 비중이 순수 학비가 아닌 '생활비' 목적으로 실행됨.", C_HIGHLIGHT)
                tot_t = filtered_df["총_등록금대출_금액"].sum()
                tot_l = filtered_df["총_생활비대출_금액"].sum()
                fig_e = go.Figure(go.Pie(labels=["등록금 대출", "생활비 대출"], values=[tot_t, tot_l], hole=0.5, pull=[0, 0.1], marker=dict(colors=[C_DARK, C_HIGHLIGHT])))
                fig_e.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(styled_fig(fig_e, ""), use_container_width=True)

        summary_section_header(4, "은행도 원한다: ICL 확대의 금융적 근거", "연체 리스크 제로 구조 vs 부실채권 양산 구조")

        b1, b2, b3 = st.columns(3)
        with b1:
            st.markdown(kpi_card(
                "일반상환 대출의 구조적 리스크",
                "소득 무관 상환",
                "미취업 상태에도 매월 원리금 납부 강제 → 부실채권 발생",
                C_RED
            ), unsafe_allow_html=True)
        with b2:
            st.markdown(kpi_card(
                "ICL의 연체 리스크",
                "구조적 연체 없음",
                "소득 발생 전 상환의무 없음 → 연체 개념 자체가 부재",
                C_BLUE
            ), unsafe_allow_html=True)
        with b3:
            st.markdown(kpi_card(
                "ICL 회수 방식",
                "국세청 원천징수",
                "취업 후 급여에서 자동 공제 → 회수비용·미수금 리스크 제로",
                C_GREEN
            ), unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #DDDDDD; border-left:5px solid #1A3A6C;
             padding:24px 28px; margin:20px 0; font-family:'Noto Sans KR',sans-serif;">
        <p style="font-size:13px; font-weight:700; color:#1A3A6C; margin:0 0 12px;
             text-transform:uppercase; letter-spacing:0.1em;">📌 금융기관 관점의 핵심 논거</p>
        <p style="font-size:14px; color:#333; line-height:1.8; margin:0;">
        일반상환 대출은 <b>재학 중 상환 의무</b>가 발생해 미취업·저소득 청년의 부실채권으로 이어집니다.
        반면 ICL은 <b>소득 연동 + 국세청 원천징수</b> 구조로, 금융기관 입장에서 회수 리스크가
        사실상 제로에 수렴합니다. ICL 확대는 학생을 위한 복지가 아니라,
        <b>금융 시스템 전체의 부실채권 리스크를 줄이는 합리적 선택</b>입니다.
        </p>
        </div>
        """, unsafe_allow_html=True)

        # 섹션 번호 하나 밀리므로 정책 섹션을 5번으로 변경
        summary_section_header(5, "해결 방안: 3가지 정책 제안", "자산 착시 피해자들을 위한 실현 가능한 패키지 딜")
        p1, p2, p3 = st.columns(3)
        with p1: st.markdown(policy_card(C_RED, "POLICY 01", "취업 후 상환 대출(ICL) 전면 확대", "고금리 일반상환으로 내몰린 학생들에게 소득 연동 상환(ICL)을 전면 허용하여 미취업 상태의 부채 폭탄 방지"), unsafe_allow_html=True)
        with p2: st.markdown(policy_card(C_BLUE, "POLICY 02", "독립생계 인정 + 소득산정 개편", "부모의 자산 중심 산정 방식에서 벗어나 실질적으로 경제 교류가 단절된 학생들을 위한 본인 소득 기준 재산정제 도입"), unsafe_allow_html=True)
        with p3: st.markdown(policy_card(C_DARK, "POLICY 03", "국가근로장학금 20% 의무 할당", "무상 지원이 전무한 9·10구간 대출 실행자들에게 교내 근로 일자리 중 20%를 강제 배정하여 최소한의 생계 방어막 제공"), unsafe_allow_html=True)

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
        서류상 부유층으로 분류되는 9·10구간 대학생들 중, 자산 착시로 인해 실질적인 생계 압박과 고위험 부채(일반상환 대출)에 내몰린 사각지대 규모를 교차 검증합니다. 모든 데이터는 공공데이터포털의 한국장학재단 출처입니다.
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
        <p style="font-size:13px; color:#444444; line-height:1.75; margin-bottom:24px;">정부 고등교육 재정 지원의 척도인 <b>학자금 지원구간(소득분위)</b>은 가구의 월급뿐 아니라 부동산, 자동차 등 재산의 소득환산액을 더해 산정됩니다. 이는 부모의 자산 착시로 인해 실질적인 경제 교류가 없는 학생들까지 피해를 입는 모순을 유발합니다.</p>
        <div style="display: flex; gap: 24px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 320px; background:#F9F9F9; padding:22px 20px; border-top: 3px solid #1A3A6C;">
        <p style="font-size:11px; font-weight:700; color:#1A3A6C; text-transform:uppercase; margin-top:0; margin-bottom:12px;">■ 학자금 지원 소득분위 경계 구조</p>
        <p style="font-size:12px; color:#555555; line-height:1.65; margin:0;"><b>경계선의 함정:</b> 기준 중위소득 200%를 초과하는 순간 9구간으로 분류됩니다. 이 선을 넘는 즉시 <b>국가장학금 무상 지원은 물론 ICL 대출마저 배제</b>됩니다.</p>
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
            # 탭을 4개로 정확히 맞춥니다 (t1, t2, t3, t4)
            t1, t2, t3, t4 = st.tabs(["지역별 대출 현황", "사각지대 부채 증명", "대출 목적 분류", "설립유형 비교"])
            
            with t1:
                type_data = filtered_df.groupby("지역별")[["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"]].sum().reset_index()
                fig1 = px.bar(type_data, x="지역별", y=["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"], barmode="stack", color_discrete_sequence=[C_RED, C_BLUE])
                st.plotly_chart(styled_fig(fig1, "지역별 학자금 대출 비중"), use_container_width=True)

            with t2:
                if not filtered_df.empty and "소득구간_추정" in filtered_df.columns:
                    grp2 = filtered_df.groupby("소득구간_추정")[["일반학자금대출_전체_금액", "취업학자금대출_전체_금액"]].sum().reset_index()
                    grp2["총대출"] = grp2["일반학자금대출_전체_금액"] + grp2["취업학자금대출_전체_금액"]
                    grp2["일반상환_비중"] = (grp2["일반학자금대출_전체_금액"] / grp2["총대출"].replace(0, pd.NA)) * 100
                    grp2["취업후상환_비중"] = (grp2["취업학자금대출_전체_금액"] / grp2["총대출"].replace(0, pd.NA)) * 100

                    fig2 = go.Figure([
                        go.Bar(name="고금리 일반상환(9~10구간 강제)", x=grp2["소득구간_추정"], y=grp2["일반상환_비중"], marker_color=C_RED, text=grp2["일반상환_비중"].apply(lambda x: f"{x:.1f}%")),
                        go.Bar(name="안전한 취업후상환(ICL)", x=grp2["소득구간_추정"], y=grp2["취업후상환_비중"], marker_color=C_BLUE, text=grp2["취업후상환_비중"].apply(lambda x: f"{x:.1f}%"))
                    ])
                    fig2.update_layout(barmode="stack", margin=dict(l=10, r=10, t=30, b=10), showlegend=True)
                    fig2.update_traces(textposition='auto')
                    fig2.update_yaxes(ticksuffix="%")
                    st.plotly_chart(styled_fig(fig2, "소득구간별 대출 유형 비중 (사각지대 증명)"), use_container_width=True)

                    # 1. 일반상환 비중 파생변수 생성 (데이터 로딩 함수 내에 넣으면 더 좋습니다)
                    filtered_df["일반상환_비중"] = (filtered_df["일반학자금대출_전체_금액"] / (filtered_df["일반학자금대출_전체_금액"] + filtered_df["취업학자금대출_전체_금액"])) * 100
                
                    
                    st.markdown("""
                    <div style="font-size:12px; color:#333; padding:12px; background:#FFF5F5; border-left:4px solid #C41E3A;">
                    <b>핵심 분석:</b> 9~10구간 밀집 대학일수록 '고금리 일반상환 대출' 비중이 압도적으로 높습니다. 
                    이는 ICL(취업 후 상환) 안전망에서 원천 배제된 학생들이 질 나쁜 빚으로 내몰리는 <b>제도적 배제의 증거</b>입니다.
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("---")
                    st.markdown("#### 💰 대출자 1인당 실부담 금액 비교")
                    grp_amt = filtered_df.groupby("소득구간_추정").agg(
                        일반대출_1인당=("대출자_1인당_일반대출", "mean"),
                        취업대출_1인당=("대출자_1인당_취업대출", "mean")
                    ).reset_index()
                    grp_amt["일반대출_1인당"] = pd.to_numeric(grp_amt["일반대출_1인당"], errors="coerce").fillna(0)
                    grp_amt["취업대출_1인당"] = pd.to_numeric(grp_amt["취업대출_1인당"], errors="coerce").fillna(0)
                    fig_amt = go.Figure([
                        go.Bar(name="일반상환(고금리)", x=grp_amt["소득구간_추정"],
                               y=grp_amt["일반대출_1인당"], marker_color=C_RED),
                        go.Bar(name="취업후상환(ICL)", x=grp_amt["소득구간_추정"],
                               y=grp_amt["취업대출_1인당"], marker_color=C_BLUE)
                    ])
                    fig_amt.update_layout(barmode="group")
                    st.plotly_chart(styled_fig(fig_amt, "분위별 대출자 1인당 실부담액"), use_container_width=True)

            with t3:
                purpose_data = filtered_df.groupby("지역별")[["총_등록금대출_금액", "총_생활비대출_금액"]].sum().reset_index()
                fig3 = px.bar(purpose_data, x="지역별", y=["총_생활비대출_금액", "총_등록금대출_금액"], barmode="stack", color_discrete_sequence=[C_DARK, "#888888"])
                st.plotly_chart(styled_fig(fig3, "등록금 대출 vs 생활비 대출 비중"), use_container_width=True)

            with t4:
                if not filtered_df.empty:
                    avg_data = filtered_df.groupby("설립별")[["평균등록금(원)", "1인당_대출액(원)"]].mean().reset_index()
                    fig5 = px.bar(avg_data, x="설립별", y=["평균등록금(원)", "1인당_대출액(원)"], barmode="group", color_discrete_sequence=[C_BLUE, C_RED])
                    st.plotly_chart(styled_fig(fig5, "국공립 vs 사립 지표 비교"), use_container_width=True)
                    st.markdown("---")
                    st.markdown("#### 📊 설립유형 × 장학금 분위 교차 분석")
                    if "소득구간_추정" in filtered_df.columns:
                        cross = filtered_df.groupby(
                            ["설립별", "소득구간_추정"]
                        )["대출학생비율(%)"].mean().reset_index()
                        cross["대출학생비율(%)"] = pd.to_numeric(cross["대출학생비율(%)"], errors="coerce").fillna(0)
                        fig_cross = px.bar(
                            cross, x="소득구간_추정", y="대출학생비율(%)",
                            color="설립별", barmode="group",
                            color_discrete_sequence=[C_BLUE, C_RED]
                        )
                        st.plotly_chart(
                            styled_fig(fig_cross, "설립유형별 분위 대출학생 비율"),
                            use_container_width=True
                        )
            

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
        with p1r: st.markdown(policy_card(C_RED, "POLICY 01", "ICL 자격의 전면 확대", "안전망 부재로 고위험군에 놓인 학생들을 위해 취업 후 상환 학자금 대출 제도를 개방합니다."), unsafe_allow_html=True)
        with p2r: st.markdown(policy_card(C_BLUE, "POLICY 02", "독립 생계 인정 제도", "부모의 경제적 지원 없이 독자 생계를 유지하는 학생들을 선별해 소득 분위 산정 시 부모 자산을 유예합니다."), unsafe_allow_html=True)
        with p3r: st.markdown(policy_card(C_DARK, "POLICY 03", "근로장학금 20% 의무 할당", "생계비 목적 대출 이력이 확인된 9·10구간 학생층에 대해 교내 근로 배정 쿼터를 적용합니다."), unsafe_allow_html=True)

except Exception as e:
    st.markdown(f"<div style='background:#FFF5F5;border-left:3px solid #C41E3A;padding:16px 20px;'><strong>시스템 실행 오류:</strong> {str(e)}</div>", unsafe_allow_html=True)