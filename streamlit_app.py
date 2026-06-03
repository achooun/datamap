import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="대학생 장학금 사각지대 분석", layout="wide")

# 제목 부분
st.title("📊 국가장학금 사각지대 및 대출 의존도 종합 분석")
st.markdown("---")

# 2. 데이터 불러오기 함수 (캐싱 적용)
@st.cache_data
def load_data():
    df1 = pd.read_csv("Q1_사각지대_생활비대출_분석용.csv", encoding='utf-8-sig')
    df2 = pd.read_csv("Q2_지도용_최종데이터.csv", encoding='utf-8-sig')
    return df1, df2

try:
    df1, df2 = load_data()

    # 3. 사이드바 전역 필터링 설정
    st.sidebar.header("🔍 통합 데이터 필터링")
    
    selected_region = st.sidebar.selectbox("지역 선택", options=["전체"] + sorted(df2['지역별'].unique().tolist()))
    selected_type = st.sidebar.selectbox("설립유형 선택", options=["전체"] + sorted(df2['설립별'].unique().tolist()))
    
    # 필터링 적용
    filtered_df1 = df1.copy()
    filtered_df2 = df2.copy()
    
    if selected_region != "전체":
        filtered_df1 = filtered_df1[filtered_df1['지역별'] == selected_region]
        filtered_df2 = filtered_df2[filtered_df2['지역별'] == selected_region]
    if selected_type != "전체":
        filtered_df1 = filtered_df1[filtered_df1['설립별'] == selected_type]
        filtered_df2 = filtered_df2[filtered_df2['설립별'] == selected_type]

    st.sidebar.markdown(f"**현재 검색된 대학 수: {len(filtered_df2)}개**")

    # ==========================================
    # [상단 영역] 요약 수치 박스 (가로 4개 배치로 글자 잘림 방지)
    # ==========================================
    overall_avg_tuition = df2['평균등록금(원)'].mean()
    
    if not filtered_df2.empty:
        filtered_avg = filtered_df2['평균등록금(원)'].mean()
        max_tuition_row = filtered_df2.loc[filtered_df2['평균등록금(원)'].idxmax()]
        max_tuition_school = max_tuition_row['학교명']
        max_tuition_val = max_tuition_row['평균등록금(원)']
    else:
        filtered_avg, max_tuition_school, max_tuition_val = 0, "없음", 0

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.markdown(f"""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; text-align:center; border:1px solid #dee2e6;'>
                <p style='margin:0; font-size:14px; color:#6c757d; font-weight:bold;'>🇰🇷 전국 평균 등록금</p>
                <h3 style='margin:5px 0 0 0; color:#1f77b4; font-size:22px;'>{int(overall_avg_tuition):,}원</h3>
            </div>
        """, unsafe_allow_html=True)
        
    with col_m2:
        st.markdown(f"""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; text-align:center; border:1px solid #dee2e6;'>
                <p style='margin:0; font-size:14px; color:#6c757d; font-weight:bold;'>📍 필터 적용 평균 등록금</p>
                <h3 style='margin:5px 0 0 0; color:#ff7f0e; font-size:22px;'>{int(filtered_avg):,}원</h3>
            </div>
        """, unsafe_allow_html=True)
        
    with col_m3:
        st.markdown(f"""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; text-align:center; border:1px solid #dee2e6;'>
                <p style='margin:0; font-size:14px; color:#6c757d; font-weight:bold;'>🏆 최고 등록금 대학</p>
                <h3 style='margin:5px 0 0 0; color:#d62728; font-size:20px;'>{max_tuition_school} <span style='font-size:13px; color:#555;'>({int(max_tuition_val):,}원)</span></h3>
            </div>
        """, unsafe_allow_html=True)

    with col_m4:
        if not filtered_df1.empty:
            max_loan_school = filtered_df1.loc[filtered_df1['총_대출_학생수'].idxmax(), '학교명']
            max_loan_cnt = filtered_df1['총_대출_학생수'].max()
        else:
            max_loan_school, max_loan_cnt = "없음", 0
            
        st.markdown(f"""
            <div style='background-color:#f8f9fa; padding:15px; border-radius:10px; text-align:center; border:1px solid #dee2e6;'>
                <p style='margin:0; font-size:14px; color:#6c757d; font-weight:bold;'>🏦 최다 대출 학생 대학</p>
                <h3 style='margin:5px 0 0 0; color:#2ca02c; font-size:20px;'>{max_loan_school} <span style='font-size:13px; color:#555;'>({int(max_loan_cnt):,}명)</span></h3>
            </div>
        """, unsafe_allow_html=True)
        
    st.write("") # 섹션 간 간격 띄우기

    # ==========================================
    # [중단 영역] 분석 그래프 (왼쪽) + 지도 (오른쪽)
    # ==========================================
    left_col, right_col = st.columns([1.1, 1])

    with left_col:
        tab1, tab2 = st.tabs(["💡 사각지대 분석", "🏛️ 설립유형별 격차"])

        with tab1:
            st.subheader("1. 장학금 사각지대와 생활비 대출의 상관관계")
            fig1 = px.scatter(
                filtered_df1, 
                x="교외장학금 국가", y="총_생활비대출_금액",
                hover_name="학교명", size="총_대출_학생수", 
                color="총_생활비대출_금액", color_continuous_scale="Blues",
                title="국가장학금 수혜액 vs 생활비 대출 규모 (버블: 대출 학생수)"
            )
            st.plotly_chart(fig1, use_container_width=True)

        with tab2:
            st.subheader("2. 국공립 vs 사립대 등록금 및 대출 격차")
            if not filtered_df2.empty:
                avg_data = filtered_df2.groupby("설립별")[["평균등록금(원)", "총_대출_금액"]].mean().reset_index()
                c1, c2 = st.columns(2)
                with c1:
                    fig2 = px.bar(avg_data, x="설립별", y="평균등록금(원)", title="평균 등록금", color="설립별", text_auto='.2s')
                    st.plotly_chart(fig2, use_container_width=True)
                with c2:
                    fig3 = px.bar(avg_data, x="설립별", y="총_대출_금액", title="평균 총 대출 규모", color="설립별", text_auto='.2s')
                    st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("조건에 맞는 데이터가 없습니다.")

    with right_col:
        st.subheader("🗺️ 대학 위치 및 지표 정보")
        south_korea_bounds = [[33.0, 124.0], [39.0, 132.0]]
        if not filtered_df2.empty:
            center_lat, center_lon = filtered_df2['위도'].mean(), filtered_df2['경도'].mean()
        else:
            center_lat, center_lon = 36.2, 127.8

        m = folium.Map(location=[center_lat, center_lon], zoom_start=7, min_zoom=7, max_zoom=14, max_bounds=True, bounds=south_korea_bounds)
        marker_cluster = MarkerCluster().add_to(m)

        for idx, row in filtered_df2.iterrows():
            marker_color = 'blue' if row['설립별'] == '국공립' else 'red'
            popup_html = f"""
            <div style='width: 200px; font-family: sans-serif;'>
                <h5 style='margin: 0 0 5px 0; color: #333;'>{row['학교명']}</h5>
                <p style='margin: 3px 0; font-size: 12px;'><b>설립별:</b> {row['설립별']}</p>
                <p style='margin: 3px 0; font-size: 12px;'><b>평균등록금:</b> {int(row['평균등록금(원)']):,}원</p>
                <p style='margin: 3px 0; font-size: 12px;'><b>대출학생수:</b> {int(row['총_대출_학생수']):,}명</p>
            </div>
            """
            folium.Marker(
                location=[row['위도'], row['경도']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=row['학교명'],
                icon=folium.Icon(color=marker_color, icon='info-sign')
            ).add_to(marker_cluster)

        # 지도 크기를 세로 450으로 줄여서 스크롤 최소화
        st_folium(m, use_container_width=True, height=450, returned_objects=[])

    # ==========================================
    # [하단 영역] 통합 데이터 표
    # ==========================================
    st.markdown("---")
    st.subheader("📋 전체 대학 통합 상세 데이터")
    
    merge_cols_df2 = ['학교명', '학제별', '평균등록금(원)']
    merged_df = pd.merge(filtered_df1, filtered_df2[merge_cols_df2], on='학교명', how='inner')

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        sort_by = st.selectbox(
            "정렬 기준 항목",
            options=["기본(정렬 없음)", "평균등록금(원)", "총_대출_학생수", "총_생활비대출_금액"]
        )
    with col_s2:
        sort_order = st.radio("정렬 방식", options=["오름차순 ↑", "내림차순 ↓"], horizontal=True, disabled=(sort_by == "기본(정렬 없음)"))
    
    if sort_by != "기본(정렬 없음)":
        is_ascending = True if "오름차순" in sort_order else False
        table_df = merged_df.sort_values(by=sort_by, ascending=is_ascending)
    else:
        table_df = merged_df.copy()
        
    display_cols = [
        '학교명', '지역별', '설립별', '학제별', 
        '평균등록금(원)', '교외장학금 국가', '교내장학금 저소득층장학금', 
        '총_생활비대출_금액', '총_대출_학생수'
    ]
    display_df = table_df[display_cols].copy()
    
    rename_dict = {
        '평균등록금(원)': '평균등록금(1년/원)', '교외장학금 국가': '국가장학금(원)', 
        '교내장학금 저소득층장학금': '저소득장학금(원)', '총_생활비대출_금액': '생활비대출(원)', 
        '총_대출_학생수': '대출학생수(명)'
    }
    display_df.rename(columns=rename_dict, inplace=True)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"데이터를 불러오거나 처리하는 중 오류가 발생했습니다: {e}")