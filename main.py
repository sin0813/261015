 import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.express as px

st.set_page_config(page_title="전국 인구 지표 단계구분도", layout="wide")

st.title("🗺️ 전국 시군구별 인구 지표 단계구분도")

# 1. GeoJSON 경계 데이터 로드 함수
@st.cache_data
def load_geojson():
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/sigungu_kr.geojson"
    geojson = requests.get(geojson_url).json()
    
    # GeoJSON 코드 5자리 문자열 보정
    for feature in geojson['features']:
        feature['properties']['코드'] = str(feature['properties']['코드']).zfill(5)
        
    return geojson

# 2. 인구 데이터 로드 및 전처리 함수
@st.cache_data
def load_population_data():
    pop_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(pop_url, compression='zip')
    
    # 동 코드 5자리 시군구 코드로 변환
    df['코드'] = df['코드'].astype(str).str.zfill(8)
    df['sigungu_code'] = df['코드'].str[:5]
    
    # --- 옛 행정구역 코드 보정 ---
    # 1) 강원특별자치도 (42xxx -> 51xxx)
    mask_42 = df['sigungu_code'].str.startswith('42')
    df.loc[mask_42, 'sigungu_code'] = '51' + df.loc[mask_42, 'sigungu_code'].str[2:]
    
    # 2) 전북특별자치도 (45xxx -> 52xxx)
    mask_45 = df['sigungu_code'].str.startswith('45')
    df.loc[mask_45, 'sigungu_code'] = '52' + df.loc[mask_45, 'sigungu_code'].str[2:]
    
    # 3) 대구광역시 군위군 (47720 -> 27720)
    df.loc[df['sigungu_code'] == '47720', 'sigungu_code'] = '27720'
    
    # 전체/고령/유소년 열 분류
    total_cols = [c for c in df.columns if c.startswith('계_')]
    
    elderly_cols = []
    youth_cols = []
    
    for c in total_cols:
        age_str = c.replace('계_', '').replace('세', '').replace(' 이상', '')
        if age_str.isdigit():
            age = int(age_str)
            if age >= 65:
                elderly_cols.append(c)
            elif age <= 14:
                youth_cols.append(c)
        elif '100세 이상' in c:
            elderly_cols.append(c)
            
    # 행별 인구 합계 계산
    df['전체인구'] = df[total_cols].sum(axis=1)
    df['고령인구'] = df[elderly_cols].sum(axis=1)
    df['유소년인구'] = df[youth_cols].sum(axis=1)
    
    # 연도별, 시군구별 집계
    grouped = df.groupby(['연도', 'sigungu_code'])[['전체인구', '고령인구', '유소년인구']].sum().reset_index()
    
    # 비율 계산 (%)
    grouped['고령화율'] = (grouped['고령인구'] / grouped['전체인구']) * 100
    grouped['유소년비율'] = (grouped['유소년인구'] / grouped['전체인구']) * 100
    
    return grouped

with st.spinner("데이터 및 경계 지도를 불러오는 중입니다..."):
    geojson_data = load_geojson()
    pop_df = load_population_data()

# GeoJSON의 코드-시군구-시도 매핑 dictionary 생성
geo_info = {}
for f in geojson_data['features']:
    code = f['properties']['코드']
    sigungu_name = f['properties']['시군구']
    sido_name = f['properties']['시도']
    geo_info[code] = {'시군구': sigungu_name, '시도': sido_name}

# --- 사이드바 및 컨트롤 ---
st.sidebar.header("⚙️ 지도 설정")

# 1. 지표 선택
metric_option = st.sidebar.selectbox(
    "📊 지표 선택",
    ["고령화율 (65세 이상)", "유소년 비율 (0~14세)"]
)

is_elderly = "고령화율" in metric_option
metric_col = "고령화율" if is_elderly else "유소년비율"
metric_label = "고령화율 (%)" if is_elderly else "유소년 비율 (%)"

# 2. 연도 선택 슬라이더
available_years = sorted(pop_df['연도'].unique())
selected_year = st.sidebar.slider(
    "📅 연도 선택",
    min_value=int(min(available_years)),
    max_value=int(max(available_years)),
    value=int(max(available_years)),
    step=1
)

# 선택된 연도 데이터 필터링
df_year = pop_df[pop_df['연도'] == selected_year].copy()

# 지도 데이터에 시군구 이름 및 시도 이름 결합
df_year['시군구'] = df_year['sigungu_code'].map(lambda x: geo_info.get(x, {}).get('시군구', '미매칭 지역'))
df_year['시도'] = df_year['sigungu_code'].map(lambda x: geo_info.get(x, {}).get('시도', '미매칭'))

# 3. 시도 선택 드롭다운
sido_list = ["전국"] + sorted(list(set(info['시도'] for info in geo_info.values())))
selected_sido = st.sidebar.selectbox("🗺️ 시도 선택", sido_list)

# 선택 시도에 맞춰 데이터 필터링 (카드 지표용)
if selected_sido != "전국":
    filtered_df = df_year[df_year['시도'] == selected_sido]
else:
    filtered_df = df_year

# --- 상단 지표 카드 3개 ---
total_pop = filtered_df['전체인구'].sum()
target_pop = filtered_df['고령인구'].sum() if is_elderly else filtered_df['유소년인구'].sum()
national_avg = (target_pop / total_pop * 100) if total_pop > 0 else 0

valid_df = filtered_df[filtered_df['시군구'] != '미매칭 지역']

if not valid_df.empty:
    max_row = valid_df.loc[valid_df[metric_col].idxmax()]
    min_row = valid_df.loc[valid_df[metric_col].idxmin()]
    
    max_str = f"{max_row['시도']} {max_row['시군구']} ({max_row[metric_col]:.2f}%)"
    min_str = f"{min_row['시도']} {min_row['시군구']} ({min_row[metric_col]:.2f}%)"
else:
    max_str = "N/A"
    min_str = "N/A"

col1, col2, col3 = st.columns(3)
col1.metric(f"전국/지역 평균 {metric_label.split()[0]}", f"{national_avg:.2f}%")
col2.metric("가장 높은 시군구", max_str)
col3.metric("가장 낮은 시군구", min_str)

st.write("")

# --- 구간 분할 및 범주화 (범주형 단계구분도) ---
if is_elderly:
    bins = [0, 19, 23, 28, 38, 100]
    labels = ["19% 미만", "19% ~ 23%", "23% ~ 28%", "28% ~ 38%", "38% 이상"]
    color_discrete_map = {
        "19% 미만": "#FEE5D9",
        "19% ~ 23%": "#FCAE91",
        "23% ~ 28%": "#FB6A4A",
        "28% ~ 38%": "#DE2D26",
        "38% 이상": "#A50F15"
    }
else:
    bins = [0, 6, 9, 12, 15, 100]
    labels = ["6% 미만", "6% ~ 9%", "9% ~ 12%", "12% ~ 15%", "15% 이상"]
    color_discrete_map = {
        "6% 미만": "#EDF8FB",
        "6% ~ 9%": "#B2E2E2",
        "9% ~ 12%": "#66C2A4",
        "12% ~ 15%": "#2CA25F",
        "15% 이상": "#006D2C"
    }

df_year['구간'] = pd.cut(df_year[metric_col], bins=bins, labels=labels, right=False)

# --- 시도 선택에 따른 지도 위치 및 확대 축소(Zoom) 지정 ---
sido_centers = {
    "전국": {"lat": 35.9, "lon": 127.8, "zoom": 6.0},
    "서울특별시": {"lat": 37.5665, "lon": 126.9780, "zoom": 9.5},
    "부산광역시": {"lat": 35.1796, "lon": 129.0756, "zoom": 9.5},
    "대구광역시": {"lat": 35.8714, "lon": 128.6014, "zoom": 9.0},
    "인천광역시": {"lat": 37.4563, "lon": 126.7052, "zoom": 9.0},
    "광주광역시": {"lat": 35.1595, "lon": 126.8526, "zoom": 10.0},
    "대전광역시": {"lat": 36.3504, "lon": 127.3845, "zoom": 10.0},
    "울산광역시": {"lat": 35.5384, "lon": 129.3114, "zoom": 9.5},
    "세종특별자치시": {"lat": 36.4800, "lon": 127.2890, "zoom": 10.5},
    "경기도": {"lat": 37.4138, "lon": 127.5183, "zoom": 8.2},
    "강원특별자치도": {"lat": 37.8228, "lon": 128.1555, "zoom": 8.0},
    "충청북도": {"lat": 36.6357, "lon": 127.4912, "zoom": 8.3},
    "충청남도": {"lat": 36.5184, "lon": 126.8000, "zoom": 8.3},
    "전북특별자치도": {"lat": 35.7175, "lon": 127.1530, "zoom": 8.3},
    "전라남도": {"lat": 34.8161, "lon": 126.4629, "zoom": 8.0},
    "경상북도": {"lat": 36.5760, "lon": 128.5056, "zoom": 8.0},
    "경상남도": {"lat": 35.4606, "lon": 128.2132, "zoom": 8.3},
    "제주특별자치도": {"lat": 33.4890, "lon": 126.4983, "zoom": 9.0}
}

center_info = sido_centers.get(selected_sido, {"lat": 35.9, "lon": 127.8, "zoom": 6.0})

# --- Plotly 단계구분도 생성 ---
fig = px.choropleth_mapbox(
    df_year,
    geojson=geojson_data,
    locations='sigungu_code',
    featureidkey='properties.코드',
    color='구간',
    color_discrete_map=color_discrete_map,
    category_orders={"구간": labels},
    mapbox_style="white-bg",
    center={"lat": center_info["lat"], "lon": center_info["lon"]},
    zoom=center_info["zoom"],
    hover_name='시군구',
    hover_data={'sigungu_code': False, metric_col: ':.2f%', '구간': False}
)

fig.update_traces(
    marker_line_width=0.5,
    marker_line_color='gray',
    hovertemplate="<b>%{hovertext}</b><br>" + f"{metric_col}: " + "%{customdata[0]:.2f}%<extra></extra>"
)

fig.update_layout(
    margin={"r":0, "t":10, "l":0, "b":0},
    legend_title_text=metric_label,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)

st.plotly_chart(fig, use_container_width=True)

# --- 미매칭 지역 안내 문구 ---
geo_codes = set(f['properties']['코드'] for f in geojson_data['features'])
pop_codes = set(df_year['sigungu_code'].unique())
unmatched_codes = geo_codes - pop_codes

if unmatched_codes:
    unmatched_names = [f"{geo_info[c]['시도']} {geo_info[c]['시군구']}({c})" for c in unmatched_codes if c in geo_info]
    st.info(
        f"💡 **안내**: {selected_year}년 데이터 기준으로 행정구역 개편 또는 데이터 누락으로 인해 "
        f"지도에 표시되지 않는 지역(회색)이 있습니다: **{', '.join(unmatched_names)}**"
    )
