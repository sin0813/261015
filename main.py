import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏡",
    layout="wide"
)


# -----------------------------------------------------------------------------
# 2. 데이터 불러오기 함수 (캐싱을 적용하여 실행 속도 최적화)
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
    f"**{latest_year}년 기준** 전국 읍·면·동별 남녀 연령별 인구 구조를 따뜻한 시선으로 한눈에 확인해보세요."
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
# 5. Plotly 인구 피라미드 그래프 생성 및 시각화
# -----------------------------------------------------------------------------
if not target_row.empty:
    row = target_row.iloc[0]

    # 0세부터 100세 이상까지의 연령 라벨 목록을 생성합니다. (0세가 리스트의 첫 번째)
    ages = [f"{i}세" for i in range(100)] + ["100세 이상"]

    # 데이터 프레임 컬럼 이름에 맞게 남/여 컬럼 목록 생성
    male_cols = [f"남_{age}" for age in ages]
    female_cols = [f"여_{age}" for age in ages]

    # 인구 수 데이터 추출
    # 남성은 왼쪽 배치를 위해 음수(-)값으로 변환하고, 여성은 양수(+)값으로 유지합니다.
    male_pop = [
        -int(row[col]) if col in row and pd.notna(row[col]) else 0
        for col in male_cols
    ]
    female_pop = [
        int(row[col]) if col in row and pd.notna(row[col]) else 0
        for col in female_cols
    ]

    # Plotly 시각화 객체 생성
    fig = go.Figure()

    # 남성 막대 그래프 (왼쪽 방향)
    fig.add_trace(
        go.Bar(
            y=ages,
            x=male_pop,
            name="남성",
            orientation="h",
            marker=dict(color="#6BAED6"),  # 포근한 소프트 블루
            text=[f"{abs(val):,}명" for val in male_pop],
            hoverinfo="text",
            hovertemplate="<b>%{y} 남성</b>: %{text}<extra></extra>",
        )
    )

    # 여성 막대 그래프 (오른쪽 방향)
    fig.add_trace(
        go.Bar(
            y=ages,
            x=female_pop,
            name="여성",
            orientation="h",
            marker=dict(color="#FB6A4A"),  # 따뜻한 피치 코랄
            text=[f"{val:,}명" for val in female_pop],
            hoverinfo="text",
            hovertemplate="<b>%{y} 여성</b>: %{text}<extra></extra>",
        )
    )

    # X축 눈금을 양수로 깔끔하게 정돈하기 위한 자동 범위 산출
    all_abs_vals = [abs(x) for x in male_pop] + female_pop
    max_val = max(all_abs_vals) if all_abs_vals else 100

    step = max(1, int(max_val / 4))
    tick_vals = list(range(-step * 4, step * 5, step))
    tick_texts = [f"{abs(v):,}" for v in tick_vals]

    # 그래프 레이아웃 세부 설정
    fig.update_layout(
        title={
            "text": f"<b>{selected_sido} {selected_sigungu} {selected_dong}</b> 인구 피라미드 ({latest_year}년)",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20},
        },
        barmode="overlay",  # 남/여 막대를 중심축 기준으로 양옆 배치
        xaxis=dict(
            title="인구 수 (명)",
            tickmode="array",
            tickvals=tick_vals,
            ticktext=tick_texts,
            zeroline=True,
            zerolinecolor="#999999",
            zerolinewidth=1.5,
        ),
        yaxis=dict(
            title="나이",
            # 핵심 설정: categoryorder='array'와 categoryarray를 사용하여
            # ages 배열 순서대로 (맨 아래: '0세' ~ 맨 위: '100세 이상') 축에 직접 고정합니다.
            categoryorder="array",
            categoryarray=ages,
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
        height=950,  # 0~100세 눈금이 답답하지 않게 세로 길이를 넉넉히 설정
        margin=dict(l=60, r=60, t=100, b=60),
        plot_bgcolor="#FAF9F6",  # 따뜻한 웜화이트 배경
        paper_bgcolor="#FFFFFF",
    )

    # 스트림릿 화면에 그래프 표시
    st.plotly_chart(fig, use_container_width=True)
