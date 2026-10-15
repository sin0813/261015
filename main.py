import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드", page_icon="🏡", layout="wide"
)


# -----------------------------------------------------------------------------
# 2. 데이터 불러오기 함수 (캐싱 적용)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # 압축된 CSV 파일 주소에서 데이터를 직접 판다스로 읽어옵니다.
    url = "https://raw.githubusercontent.com/sin0813/261015/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(url)
    return df


# 데이터 읽기
df = load_data()

# 가장 최신 연도 데이터만 추출합니다.
latest_year = int(df["연도"].max())
df_latest = df[df["연도"] == latest_year].copy()


# -----------------------------------------------------------------------------
# 3. 화면 타이틀 및 설명
# -----------------------------------------------------------------------------
st.title("🏡 우리 동네 인구 피라미드")
st.markdown(
    f"**{latest_year}년 기준** 전국 읍·면·동별 남녀 연령별 인구 구조를 한눈에 확인해보세요."
)
st.markdown("---")


# -----------------------------------------------------------------------------
# 4. 드롭다운 선택 UI (시도 → 시군구 → 동 순서로 필터링)
# -----------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

# 1) 시·도 선택
with col1:
    sido_list = sorted(df_latest["시도"].dropna().unique())
    selected_sido = st.selectbox("1. 시·도 선택", sido_list)

# 선택된 시·도에 해당하는 데이터만 1차 필터링
filtered_by_sido = df_latest[df_latest["시도"] == selected_sido]

# 2) 시·군·구 선택
with col2:
    sigungu_list = sorted(filtered_by_sido["시군구"].dropna().unique())
    selected_sigungu = st.selectbox("2. 시·군·구 선택", sigungu_list)

# 선택된 시·군·구에 해당하는 데이터만 2차 필터링
filtered_by_sigungu = filtered_by_sido[
    filtered_by_sido["시군구"] == selected_sigungu
]

# 3) 읍·면·동 선택
with col3:
    dong_list = sorted(filtered_by_sigungu["동"].dropna().unique())
    selected_dong = st.selectbox("3. 읍·면·동 선택", dong_list)

# 최종 선택된 특정 동네의 행(Row) 추출
target_row = filtered_by_sigungu[filtered_by_sigungu["동"] == selected_dong]


# -----------------------------------------------------------------------------
# 5. 데이터 가공 및 주요 지표 계산
# -----------------------------------------------------------------------------
if not target_row.empty:
    row = target_row.iloc[0]

    # 0세부터 100세 이상까지의 연령 라벨 목록
    ages = [f"{i}세" for i in range(100)] + ["100세 이상"]

    # 컬럼명 생성
    male_cols = [f"남_{age}" for age in ages]
    female_cols = [f"여_{age}" for age in ages]

    # 인구 수 추출 (남성은 그래프용으로 음수 변환)
    male_pop = [
        -int(row[col]) if col in row and pd.notna(row[col]) else 0
        for col in male_cols
    ]
    female_pop = [
        int(row[col]) if col in row and pd.notna(row[col]) else 0
        for col in female_cols
    ]

    # 지표 계산용 순수 양수 인구 수 배열
    male_pop_abs = [abs(x) for x in male_pop]
    female_pop_abs = female_pop

    # 연령별 전체 인구 (남 + 여)
    pop_by_age = [m + f for m, f in zip(male_pop_abs, female_pop_abs)]

    # 1) 총인구 계산
    total_pop = sum(pop_by_age)

    if total_pop > 0:
        # 나이 숫자 배열 (100세 이상은 100으로 간주하여 계산)
        age_nums = list(range(100)) + [100]

        # 2) 평균연령 계산: (나이 * 인구수)의 총합 / 총인구
        weighted_age_sum = sum(
            age * pop for age, pop in zip(age_nums, pop_by_age)
        )
        avg_age = weighted_age_sum / total_pop

        # 3) 고령화율 계산: 65세 이상 인구 비율 (%)
        elderly_pop = sum(pop_by_age[65:])  # 65세부터 끝까지 합산
        aging_rate = (elderly_pop / total_pop) * 100

        # 유소년 인구 비율 (0~14세)
        child_pop = sum(pop_by_age[:15])  # 0~14세 합산
        child_rate = (child_pop / total_pop) * 100
    else:
        avg_age = 0.0
        aging_rate = 0.0
        child_rate = 0.0

    # -----------------------------------------------------------------------------
    # 6. 상단 주요 지표 카드 (3개 나란히 배치)
    # -----------------------------------------------------------------------------
    m_col1, m_col2, m_col3 = st.columns(3)

    with m_col1:
        st.metric(label="👥 총인구", value=f"{total_pop:,} 명")

    with m_col2:
        st.metric(label="🎂 평균연령", value=f"{avg_age:.1f} 세")

    with m_col3:
        # 고령화율이 20% 이상인 경우 경고 표시(⚠️) 및 안내문 추가
        if aging_rate >= 20.0:
            st.metric(
                label="👵 고령화율 (65세 이상) ⚠️",
                value=f"{aging_rate:.1f} %",
                delta="⚠️ 초고령사회 (20% 이상)",
                delta_color="inverse",
            )
        else:
            st.metric(
                label="👵 고령화율 (65세 이상)",
                value=f"{aging_rate:.1f} %",
            )

    st.markdown("---")

    # -----------------------------------------------------------------------------
    # 7. Plotly 인구 피라미드 그래프 생성 및 시각화
    # -----------------------------------------------------------------------------
    fig = go.Figure()

    # 남성 막대 그래프 (왼쪽 방향)
    fig.add_trace(
        go.Bar(
            y=ages,
            x=male_pop,
            name="남성",
            orientation="h",
            marker=dict(color="#6BAED6"),  # 소프트 블루
            text=[f"{abs(val):,}명" for val in male
