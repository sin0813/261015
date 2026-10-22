import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="전국 시군구 고령화 단계구분도 (2026년)", layout="wide")

st.title("🗺️ 2026년 전국 시군구별 고령화율 단계구분도")
st.markdown("전국 읍·면·동 인구 데이터를 바탕으로 시군구별 65세 이상 인구 비율(%)을 시각화합니다.")

@st.cache_data
def load_data():
    # 1. 인구 데이터 로드 (ZIP 압축 CSV)
    pop_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(pop_url, compression='zip')
    
    # 코드를 5자리 문자열로 변환 및 2026년 데이터 추출
    df['코드'] = df['코드'].astype(str).str.zfill(8)  # 법정동 코드는 보통 8~10자리
    df_2026 = df[df['연도'] == 2026].copy()
    
    # 시군구 단위 추출 (앞 5자리)
    df_2026['sigungu_code'] = df_2026['코드'].str[:5]
    
    # 열 이름 추출
    total_cols = [c for c in df_2026.columns if c.startswith('계_')]
    
    # 65세 이상 열 추출 (계_65세 ~ 계_100세 이상)
    elderly_cols = []
    for c in total_cols:
        age_str = c.replace('계_', '').replace('세', '').replace(' 이상', '')
        if age_str.isdigit() and int(age_str) >= 65:
            elderly_cols.append(c)
        elif '100세 이상' in c:
            elderly_cols.append(c)
            
    # 시군구별 전체 인구 및 65세 이상 인구 합산
    df_2026['전체인구'] = df_2026[total_cols].sum(axis=1)
    df_2026['고령인구'] = df_2026[elderly_cols].sum(axis=1)
    
    grouped = df_2026.groupby('sigungu_code')[['전체인구', '고령인구']].sum().reset_index()
    grouped['고령화율'] = (grouped['고령인구'] / grouped['전체인구']) * 100
    grouped['고령화율'] = grouped['고령화율'].round(2)
    
    # 2. GeoJSON 경계 데이터 로드
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/sigungu_kr.geojson"
    geojson = requests.get(geojson_url).json()
    
    # GeoJSON 내부 코드 문자열 맞춤 (5자리)
    for feature in geojson['features']:
        feature['properties']['코드'] = str(feature['properties']['코드']).zfill(5)
        
    return grouped, geojson

with st.spinner("데이터를 불러오는 중입니다..."):
    df_sigungu, geojson_data = load_data()

# Plotly 단계구분도 생성
fig = px.choropleth_mapbox(
    df_sigungu,
    geojson=geojson_data,
    locations='sigungu_code',
    featureidkey='properties.코드',
    color='고령화율',
    color_continuous_scale='Reds',
    range_color=(df_sigungu['고령화율'].min(), df_sigungu['고령화율'].max()),
    mapbox_style="white-bg",  # 배경 지도(타일) 없이 경계만 표시
    center={"lat": 35.9, "lon": 127.8},  # 대한민국 중심점
    zoom=6,
    hover_name=df_sigungu['sigungu_code'].map(
        {f['properties']['코드']: f['properties']['시군구'] for f in geojson_data['features']}
    ),
    hover_data={'sigungu_code': False, '고령화율': ':.2f'}
)

fig.update_traces(
    marker_line_width=0.5,
    marker_line_color='gray',
    hovertemplate="<b>%{hovertext}</b><br>고령화율: %{z:.2f}%<extra></extra>"
)

fig.update_layout(
    margin={"r":0, "t":30, "l":0, "b":0},
    coloraxis_colorbar=dict(title="고령화율 (%)")
)

st.plotly_chart(fig, use_container_width=True)
