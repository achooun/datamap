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

    # 1차, 2차 분석용 기존 데이터 로드

    df1 = pd.read_csv("Q1_사각지대_생활비대출_분석용.csv", encoding='utf-8-sig')

    df2 = pd.read_csv("Q2_지도용_최종데이터.csv", encoding='utf-8-sig')

   

    try:

        # 업로드된 재적학생 현황 데이터 로드 (다중 헤더 구조이므로 상단 6줄 스킵)

        df3 = pd.read_csv("Q3.csv", header=None, skiprows=6, encoding='utf-8-sig')

        # 필요한 5번(학교명)과 7번(재학생수) 컬럼만 추출

        df3 = df3.rename(columns={5: '학교명', 7: '재학생수'})[['학교명', '재학생수']]

       

        # 대학명 병합률을 높이기 위해 '(김해)', '(제2캠퍼스)' 등 괄호 안 내용과 공백 제거

        df3['학교명'] = df3['학교명'].str.replace(r'\(.*\)', '', regex=True).str.strip()

        df2['학교명_정제'] = df2['학교명'].str.replace(r'\(.*\)', '', regex=True).str.strip()

       

        # df2(지도데이터)에 재학생수 병합

        df2 = pd.merge(df2, df3, left_on='학교명_정제', right_on='학교명', how='left')

        df2 = df2.drop(columns=['학교명_y', '학교명_정제']).rename(columns={'학교명_x': '학교명'})

       

        # Topic 4를 위한 파생 변수 계산

        df2['재학생수'] = pd.to_numeric(df2['재학생수'], errors='coerce')

        df2['1인당_대출액(원)'] = df2['총_대출_금액'] / df2['재학생수']

        df2['대출학생비율(%)'] = (df2['총_대출_학생수'] / df2['재학생수']) * 100

       

    except Exception as e:

        st.warning(f"재학생 데이터를 로드하는 중 문제가 발생했습니다: {e}")

        df2['재학생수'] = None

        df2['1인당_대출액(원)'] = None

        df2['대출학생비율(%)'] = None



    return df1, df2



try:

    df1, df2 = load_data()



    # 3. 사이드바 전역 필터링 설정

    st.sidebar.header("🔍 통합 데이터 필터링")

   

    selected_region = st.sidebar.selectbox(

        "지역 선택",

        options=["전체"] + sorted(df2['지역별'].unique().tolist())

    )

   

    selected_type = st.sidebar.selectbox(

        "설립유형 선택",

        options=["전체"] + sorted(df2['설립별'].unique().tolist())

    )

   

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



    # 4. 메인 화면 레이아웃 분할 (왼쪽: 통합 그래프, 오른쪽: 전체평균+지도)

    left_col, right_col = st.columns([1.3, 1])



    # ==========================================

    # [왼쪽 영역] 통합 4가지 분석 그래프 (탭 구조)

    # ==========================================

    with left_col:

        tab1, tab2, tab3, tab4 = st.tabs([

            "💡 사각지대 분석",

            "🏛️ 설립유형별 격차",

            "🎓 장학금 분배 구조",

            "📉 1인당 대출 집중도"

        ])



        # Topic 1. 국가장학금 사각지대

        with tab1:

            st.subheader("1. 장학금 사각지대와 생활비 대출의 상관관계")

            if not filtered_df1.empty:

                avg_living_loan = int(filtered_df1['총_생활비대출_금액'].mean())

                max_loan_school = filtered_df1.loc[filtered_df1['총_생활비대출_금액'].idxmax(), '학교명']

            else:

                avg_living_loan, max_loan_school = 0, "없음"



            col1, col2, col3 = st.columns(3)

            col1.metric("해당 조건 대학 수", f"{len(filtered_df1):,d}개")

            col2.metric("평균 생활비 대출", f"{avg_living_loan:,d}원")

            col3.metric("대출 규모 최대 학교", max_loan_school)

           

            fig1 = px.scatter(

                filtered_df1,

                x="교외장학금 국가", y="총_생활비대출_금액",

                hover_name="학교명", size="총_대출_학생수",

                color="총_생활비대출_금액", color_continuous_scale="Blues",

                title="국가장학금 수혜액 vs 생활비 대출 규모 (버블: 대출 학생수)"

            )

            st.plotly_chart(fig1, use_container_width=True)



        # Topic 2. 국공립 vs 사립대

        with tab2:

            st.subheader("2. 국공립 vs 사립대 등록금 및 대출 격차")

            if not filtered_df2.empty:

                avg_data = filtered_df2.groupby("설립별")[["평균등록금(원)", "총_대출_금액"]].mean().reset_index()

               

                col_a, col_b = st.columns(2)

                with col_a:

                    fig2 = px.bar(avg_data, x="설립별", y="평균등록금(원)",

                                 title="평균 등록금", color="설립별", text_auto='.2s')

                    st.plotly_chart(fig2, use_container_width=True)

                   

                with col_b:

                    fig3 = px.bar(avg_data, x="설립별", y="총_대출_금액",

                                 title="평균 총 대출 규모", color="설립별", text_auto='.2s')

                    st.plotly_chart(fig3, use_container_width=True)



        # Topic 3. 교내장학금 분배 구조 (새로운 분석)

        with tab3:

            st.subheader("3. 교내장학금 분배 기준이 대출에 미치는 영향")

            if '교내장학금 성적우수장학금' in filtered_df1.columns:

                fig_3 = px.scatter(

                    filtered_df1,

                    x="교내장학금 저소득층장학금",

                    y="교내장학금 성적우수장학금",

                    size="총_생활비대출_금액",

                    color="설립별",

                    hover_name="학교명",

                    title="성적우수 vs 저소득층 장학금 비중 (버블: 생활비 대출액)"

                )

                st.plotly_chart(fig_3, use_container_width=True)

                st.info("💡 위쪽(성적 치중)으로 치우칠수록 대출 규모(버블 크기)가 커진다면, 복지보다 스펙 위주의 장학금이 대출을 유발한다는 가설을 증명할 수 있습니다.")

            else:

                st.warning("데이터에 '성적우수장학금' 컬럼이 없어 비교가 제한됩니다.")

                fig_3 = px.scatter(filtered_df1, x="교내장학금 저소득층장학금", y="총_생활비대출_금액", hover_name="학교명", size="총_대출_학생수")

                st.plotly_chart(fig_3, use_container_width=True)



        # Topic 4. 대학 규모 대비 대출 집중도 (새로운 분석)

        with tab4:

            st.subheader("4. 대학 규모 착시 제거: 재학생 대비 대출 집중도")

            if '대출학생비율(%)' in filtered_df2.columns and not filtered_df2['대출학생비율(%)'].isna().all():

                # 비율이 높은 Top 10 추출

                top10_ratio = filtered_df2.sort_values(by="대출학생비율(%)", ascending=False).head(10)

               

                fig_4 = px.bar(

                    top10_ratio,

                    x="학교명",

                    y="대출학생비율(%)",

                    color="설립별",

                    text_auto=".1f",

                    title="재학생 중 대출을 받은 학생 비율 Top 10 대학 (%)"

                )

                fig_4.update_layout(yaxis_title="대출 학생 비율 (%)")

                st.plotly_chart(fig_4, use_container_width=True)

                st.info("💡 총액 기준으로는 대형 대학이 상위권이었으나, '재학생 규모'로 나누면 진짜 빚 부담이 심각한 소규모/지방 대학이 수면 위로 드러납니다.")

            else:

                st.warning("재학생 데이터를 병합할 수 없어 비율을 계산하지 못했습니다.")



    # ==========================================

    # [오른쪽 영역] 평균 등록금 요약 박스 + 지도

    # ==========================================

    with right_col:

        overall_avg_tuition = df2['평균등록금(원)'].mean()

        st.markdown(

            f"""

            <div style='background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center; margin-bottom:20px; border:1px solid #d1d5db;'>

                <p style='margin:0; font-size:16px; color:#555;'>🇰🇷 대한민국 대학생 전체 평균 등록금 (1년)</p>

                <h2 style='margin:5px 0 0 0; color:#1f77b4; font-size:32px;'>{int(overall_avg_tuition):,}원</h2>

            </div>

            """, unsafe_allow_html=True

        )



        south_korea_bounds = [[33.0, 124.0], [39.0, 132.0]]

        if not filtered_df2.empty:

            center_lat, center_lon = filtered_df2['위도'].mean(), filtered_df2['경도'].mean()

        else:

            center_lat, center_lon = 36.2, 127.8



        m = folium.Map(location=[center_lat, center_lon], zoom_start=7, min_zoom=7, max_zoom=14, max_bounds=True, bounds=south_korea_bounds)

        marker_cluster = MarkerCluster().add_to(m)



        for idx, row in filtered_df2.iterrows():

            marker_color = 'blue' if row['설립별'] == '국공립' else 'red'

           

            # 팝업에 새로 구한 재학생 수와 대출학생 비율 추가

            ratio_text = f"{row['대출학생비율(%)']:.1f}%" if pd.notna(row.get('대출학생비율(%)')) else "알수없음"

            student_cnt = f"{int(row['재학생수']):,}명" if pd.notna(row.get('재학생수')) else "알수없음"

           

            popup_html = f"""

            <div style='width: 230px; font-family: sans-serif;'>

                <h4 style='margin: 0 0 8px 0; color: #333;'>{row['학교명']}</h4>

                <p style='margin: 4px 0; font-size: 13px;'><b>설립별:</b> {row['설립별']} / <b>재학생:</b> {student_cnt}</p>

                <p style='margin: 4px 0; font-size: 13px;'><b>평균등록금:</b> {int(row['평균등록금(원)']):,}원</p>

                <p style='margin: 4px 0; font-size: 13px;'><b>대출학생수:</b> {int(row['총_대출_학생수']):,}명

                <span style='color:red;'><b>({ratio_text})</b></span></p>

            </div>

            """

           

            folium.Marker(

                location=[row['위도'], row['경도']],

                popup=folium.Popup(popup_html, max_width=300),

                tooltip=row['학교명'],

                icon=folium.Icon(color=marker_color, icon='info-sign')

            ).add_to(marker_cluster)



        st_folium(m, use_container_width=True, height=540, returned_objects=[])



    # ==========================================

    # [하단 영역] 통합 데이터 표 (3, 4번 지표 모두 포함)

    # ==========================================

    st.markdown("---")

    st.subheader("📋 전체 대학 통합 상세 데이터")

   

    # df1(장학금/대출)과 새로운 파생변수가 들어간 df2 병합

    merge_cols_df2 = ['학교명', '학제별', '평균등록금(원)']

    if '재학생수' in filtered_df2.columns:

        merge_cols_df2.extend(['재학생수', '대출학생비율(%)', '1인당_대출액(원)'])

       

    merged_df = pd.merge(filtered_df1, filtered_df2[merge_cols_df2], on='학교명', how='inner')



    col_s1, col_s2 = st.columns(2)

    with col_s1:

        sort_by = st.selectbox(

            "정렬 기준 항목 선택",

            options=["기본(정렬 없음)", "평균등록금(원)", "대출학생비율(%)", "총_생활비대출_금액", "1인당_대출액(원)"]

        )

    with col_s2:

        sort_order = st.radio("정렬 방식 선택", options=["오름차순 ↑", "내림차순 ↓"], horizontal=True, disabled=(sort_by == "기본(정렬 없음)"))

   

    if sort_by != "기본(정렬 없음)" and sort_by in merged_df.columns:

        is_ascending = True if "오름차순" in sort_order else False

        table_df = merged_df.sort_values(by=sort_by, ascending=is_ascending)

    else:

        table_df = merged_df.copy()

       

    # 출력용 컬럼 정리

    display_cols = [

        '학교명', '지역별', '설립별', '학제별', '재학생수',

        '평균등록금(원)', '교외장학금 국가', '교내장학금 저소득층장학금',

        '총_생활비대출_금액', '총_대출_학생수', '대출학생비율(%)', '1인당_대출액(원)'

    ]

    # 존재하는 컬럼만 필터링

    available_cols = [col for col in display_cols if col in table_df.columns]

    display_df = table_df[available_cols].copy()

   

    # 표 이름 깔끔하게 변경

    rename_dict = {

        '학교명': '학교명', '지역별': '지역', '설립별': '설립유형', '학제별': '학제', '재학생수': '재학생수(명)',

        '평균등록금(원)': '평균등록금(1년/원)', '교외장학금 국가': '국가장학금(원)', '교내장학금 저소득층장학금': '저소득장학금(원)',

        '총_생활비대출_금액': '생활비대출(원)', '총_대출_학생수': '대출학생수(명)',

        '대출학생비율(%)': '대출학생비율(%)', '1인당_대출액(원)': '1인당 대출액(원)'

    }

    display_df.rename(columns=rename_dict, inplace=True)

   

    st.dataframe(display_df, use_container_width=True, hide_index=True)



except Exception as e:

    st.error(f"데이터를 불러오거나 처리하는 중 오류가 발생했습니다: {e}")

