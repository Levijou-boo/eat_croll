import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
from config import MONGO_URI
import os
import ast
import json
import dash_core_components as dcc
import dash_html_components as html

def extract_city(location_str):
    try:
        # Check if location_str is already a dictionary, if so return the desired value
        if isinstance(location_str, dict):
            return location_str.get('시/군/구', "Unknown")
        
        # Otherwise, try converting string representation of dictionary to actual dictionary using json.loads
        location_dict = json.loads(location_str.replace("'", '"'))  # Convert single quotes to double quotes for JSON
        
        # Extract city if present, otherwise return "Unknown"
        return location_dict.get('시/군/구', "Unknown")
    except Exception as e:
        
        return "Unknown"
    
def data_sorting(data):
    data['날짜'] = pd.to_datetime(data['날짜'])
    data_sorted = data.sort_values(by='날짜')
    data_sorted['낙찰률'] = data_sorted['낙찰예정가격'] * data_sorted['낙찰방식'] / (data_sorted['기초가격'] + 0.0001)
    data_sorted = data_sorted[data_sorted['낙찰률'] < 1000]
    data_sorted = data_sorted[data_sorted['날짜'] >= '2000-01-01']
    data_sorted['발주처_id'] = data_sorted['발주처'].astype('category').cat.codes
    data_sorted['시/군/구'] = data_sorted['지역'].apply(extract_city)
    return data_sorted


def data_reload():
    print('data_reload called')
    global data_sorted, start_year, end_year, date_options, combined_options, bid_method_options, unknown_values
    try:
        
        client = MongoClient(MONGO_URI)
        
        client.admin.command('ping')
        
        db = client['eat_croll']
        collection = db['eat_croll_data']
        
        documents = list(collection.find({}))
        data = pd.DataFrame(documents)
        data_sorted = data_sorting(data)
        unknown_values = data_sorted[data_sorted['시/군/구'] == "Unknown"]['지역']
        
    except Exception as e:
        if os.path.exists('eat_croll_data.csv'):
            data = pd.read_csv('eat_croll_data.csv')
            data_sorted = data_sorting(data)
        else:
            print("eat_croll_data.csv not found!")
    start_year = data_sorted['날짜'].min().year
    end_year = data_sorted['날짜'].max().year
    year_options = [{'label': str(year), 'value': str(year)} for year in range(start_year, end_year + 1)]
    date_options = ['1개월', '3개월', '6개월', '1년', '3년', '5년']
    combined_options = year_options + [{'label': option, 'value': option} for option in date_options]
    bid_method_options = [{'label': method, 'value': method} for method in data_sorted['낙찰방식'].unique()]
    print('data_reloding endpoint')    

        
# MongoDB 연결
print('Trying to connect to MongoDB...')
try:
    client = MongoClient(MONGO_URI)
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
    db = client['eat_croll']
    collection = db['eat_croll_data']
    documents = list(collection.find({}))
    data = pd.DataFrame(documents)
    data_sorted = data_sorting(data)
    print(data_sorted['시/군/구'].unique())
    # '지역' 컬럼에서 '시/군/구' 값을 추출하여 '시/군/구' 컬럼을 생성
    # '시/군/구' 값이 "Unknown"인 행의 '지역' 컬럼 값을 출력
    unknown_values = data_sorted[data_sorted['시/군/구'] == "Unknown"]['지역']
    print(unknown_values.head())
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    print("Using eat_croll_data.csv instead...")
    # MongoDB 연결 실패 시 로컬 CSV 파일 사용
    if os.path.exists('eat_croll_data.csv'):
        data = pd.read_csv('eat_croll_data.csv')
        data_sorted = data_sorting(data)
    else:
        print("eat_croll_data.csv not found!")
        
app = dash.Dash(__name__)
server = app.server 


# 날짜별 및 년도별 옵션 생성
start_year = data_sorted['날짜'].min().year
end_year = data_sorted['날짜'].max().year
year_options = [{'label': str(year), 'value': str(year)} for year in range(start_year, end_year + 1)]
date_options = ['1개월', '3개월', '6개월', '1년', '3년', '5년']
combined_options = year_options + [{'label': option, 'value': option} for option in date_options]
bid_method_options = [{'label': method, 'value': method} for method in data_sorted['낙찰방식'].unique()]

app.layout = html.Div([
    html.H1("시간에 따른 낙찰률"),
        dcc.Interval(
        id='interval-component',
        interval=30*60*1000,  # 1분마다
        n_intervals=0
    ),
    dcc.Dropdown(
        id='date-dropdown',
        options=combined_options,
        value='1년'
    ),
    dcc.Dropdown( 
        id='contractor-dropdown',
        options=[{'label': contractor, 'value': contractor} for contractor in data_sorted['발주처'].unique()],
        multi=True,
        placeholder="발주처 검색 및 선택"
    ),
    dcc.Dropdown( # '낙찰 방식' 필터를 위한 드롭다운 추가
        id='bid-method-dropdown',
        options=bid_method_options,
        multi=True,
        placeholder="낙찰 방식 선택"
    ),
    dcc.Dropdown(  # '시/군/구' 필터를 위한 드롭다운 추가
        id='region-dropdown',
        options=[{'label': region, 'value': region} for region in data_sorted['시/군/구'].unique()],
        multi=True,
        placeholder="시/군/구 검색 및 선택",
        value=['김해시','거제시','통영시']
    ),
    dcc.Graph(id='rate-graph'),
    html.Div(id='spike-line-value', style={
        'position': 'fixed',
        'bottom': '0',
        'left': '0',
        'width': '100%',
        'background-color': '#f9f9f9',
        'padding': '10px',
        'border-top': '1px solid #ddd',
        'text-align': 'center',
    })
])

@app.callback(
    [Output('rate-graph', 'figure'),
     Output('spike-line-value', 'children')],
    [Input('date-dropdown', 'value'),
     Input('contractor-dropdown', 'value'),
     Input('bid-method-dropdown', 'value'),
     Input('region-dropdown', 'value'),
     Input('rate-graph', 'hoverData'),
     Input('interval-component', 'n_intervals')]
)
def update_graph(selected_date, selected_contractors, selected_methods, selected_regions, hoverData, n_intervals):
    ctx = dash.callback_context
    if not ctx.triggered:
        trigger_id = 'No input yet'
    else:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # n_intervals 입력이 콜백을 트리거했는지 확인
    if trigger_id == 'interval-component':
        data_reload()
    filtered_data = data_sorted
    # 년도 선택 시
    if selected_date.isdigit():
        start_date = datetime(int(selected_date), 1, 1)
        end_date = datetime(int(selected_date) + 1, 1, 1)
        filtered_data = data_sorted[(data_sorted['날짜'] >= start_date) & (data_sorted['날짜'] < end_date)]
        cutoff_date = start_date  # 그래프 생성 함수에 전달
    else:
        # 다른 날짜 옵션 선택 시
        if selected_date == '1개월':
            cutoff_date = datetime.now() - timedelta(days=30)
        elif selected_date == '3개월':
            cutoff_date = datetime.now() - timedelta(days=90)
        elif selected_date == '6개월':
            cutoff_date = datetime.now() - timedelta(days=180)
        elif selected_date == '1년':
            cutoff_date = datetime.now() - timedelta(days=365)
        elif selected_date == '3년':
            cutoff_date = datetime.now() - timedelta(days=3*365)
        elif selected_date == '5년':
            cutoff_date = datetime.now() - timedelta(days=5*365)
        else:
            cutoff_date = datetime.min  # 전체 데이터 선택
    
    # 선택된 날짜에 따른 필터링
    if cutoff_date != datetime.min:
        filtered_data = filtered_data[filtered_data['날짜'] >= cutoff_date]
    
    # 낙찰 방식에 따른 필터링
    if selected_methods:
        filtered_data = filtered_data[filtered_data['낙찰방식'].isin(selected_methods)]
        # 3. 데이터 필터링
    if selected_regions:
        filtered_data = filtered_data[filtered_data['시/군/구'].isin(selected_regions)]
    
    figure = create_rate_graph_hi(filtered_data, selected_contractors, cutoff_date)
    
    # y축의 스케일을 자동으로 조정
    figure['layout']['yaxis'].update(autorange=True)
    hover_text = "Hover"
    if hoverData:
        pass
        # x_hovered = hoverData['points'][0]['x']
        
        # # 해당 x 위치에서의 모든 y 값들을 가져옵니다.
        # y_values_at_x_hovered = filtered_data[filtered_data['날짜'] == x_hovered]['rate'].tolist()
        # y_value = y_values_at_x_hovered[0]

        # figure['layout']['yaxis']['tickvals'] = [y_value]
        # figure['layout']['yaxis']['ticktext'] = [f"{y_value:.2f}%"]
        # figure['layout']['yaxis']['showticklabels'] = True
        # figure['layout']['yaxis']['side'] = 'right'  # 오른쪽에 틱 표시
        # hover_text = f"Spike Line Value: {y_value:.2f}%"
    else:
        hover_text = "Hover over the graph to see the spike line value!"
    return figure, hover_text


import plotly.graph_objs as go
# 불투명도 계산 함수 정의
def calculate_opacity(index, total_count, max_opacity=0.3, min_opacity=0.1):
    if total_count <= 1:
        return max_opacity
    opacity = max_opacity - (index / (total_count - 1)) * (max_opacity - min_opacity)
    return opacity


def create_rate_graph_hi(data, selected_contractors, cutoff_date):
    traces = []
    if selected_contractors is None:
        selected_contractors = []

    # 모든 발주처 데이터를 초록색 마커로 먼저 표시
    trace_all = go.Scattergl(
        x=data['날짜'], 
        y=data['낙찰률'], 
        mode='markers', 
        text=[f"날짜: {date}<br>낙찰률: {rate:.2f}%<br>발주처: {contractor}" 
          for date, rate, contractor in zip(data['날짜'], data['낙찰률'], data['발주처'])],
        marker=dict(color='green', opacity=0.3)
    )
    traces.append(trace_all)
    
    # 선택된 발주처 데이터만 빨간색 라인 및 마커로 위에 그립니다.
        # 불투명도 계산
    
    for index,contractor in enumerate(selected_contractors):
        opacity = calculate_opacity(index, len(selected_contractors))
        contractor_data = data[data['발주처'] == contractor]
        trace = go.Scattergl(
            x=contractor_data['날짜'], 
            y=contractor_data['낙찰률'], 
            mode='lines+markers', 
            name=contractor,
            marker=dict(color='red', opacity=opacity, size=9)
        )
        traces.append(trace)
    
    # 가장 많이 나온 상위 100개의 낙찰률을 선택합니다.
    most_common_rates = data['낙찰률'].value_counts().nlargest(50).index
    y_max = data['낙찰률'].max()  # 현재 데이터의 최대 낙찰률
    y_range_max = y_max + (0.1 * y_max)  # y축 범위의 최대값을 현재 최대 낙찰률보다 10% 더 크게 설정
    
    for rate in most_common_rates:
        # 선 그리기
        line = go.Scatter(
            x=[cutoff_date, data['날짜'].max()+ timedelta(days=40)],
            y=[rate, rate],
            mode='lines',
            line=dict(width=0.1, color='red'),
            showlegend=False
        )
        traces.append(line)
        
        # 텍스트 표시
        text = go.Scatter(
            x=[data['날짜'].max() + timedelta(days=40)],  # 텍스트의 x 좌표를 선보다 약간 오른쪽으로 옮김
            y=[rate],  # 선의 y 좌표에 텍스트를 위치시킴
            mode='text',
            text=[f"{rate:.2f}%"],
            textposition="top center",  # 텍스트 위치를 'top center'로 변경
            textfont=dict(size=8),
            showlegend=False
        )
        traces.append(text)

    # 그래프 레이아웃 설정 부분에서 y축 범위를 조절
    layout = go.Layout(
        title="시간에 따른 낙찰률", 
        width=3500, 
        height=2000,
        autosize=True,
        xaxis=dict(
            spikemode='across',
            spikecolor='black',
            spikesnap='cursor',
            spikethickness=1,
            spikedash='solid',
            tickmode='linear',  # 달 단위로 틱 간격을 조절
            tick0=data['날짜'].min(),  # 첫 틱의 위치를 데이터의 최소 날짜로 설정
            dtick="M1",  # 달 단위로 틱 간격 설정
            fixedrange=False 
        ),
        yaxis=dict(
            zeroline=False,
            range=[0, y_range_max],  # y축 범위 설정
            spikemode='across',
            spikecolor='black',
            spikesnap='cursor',
            spikethickness=1,
            spikedash='solid',
            dtick=0.1,  # y축의 틱 간격을 0.1로 설정
            fixedrange=False,
        )
    )
    
    return {
        'data': traces,
        'layout': layout
    }
if __name__ == "__main__":
    app.run_server(host='0.0.0.0', port=8050, debug=True)