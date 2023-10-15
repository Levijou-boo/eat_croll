import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
from config import MONGO_URI

# MongoDB 연결

client = MongoClient(MONGO_URI, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client['eat_croll']
collection = db['eat_croll_data']

documents = list(collection.find({}))
data = pd.DataFrame(documents)
data_sorted = data.sort_values(by='날짜')
data_sorted['낙찰률'] = data_sorted['낙찰예정가격'] * data_sorted['낙찰방식'] / (data_sorted['기초가격'] + 0.0001)
data_sorted = data_sorted[data_sorted['낙찰률'] < 1000]
data_sorted = data_sorted[data_sorted['날짜'] >= '2000-01-01']
data_sorted['발주처_id'] = data_sorted['발주처'].astype('category').cat.codes


app = dash.Dash(__name__)
server = app.server 

# 날짜 필터링 옵션
# 날짜 필터링 옵션

# 날짜별 및 년도별 옵션 생성
start_year = data_sorted['날짜'].min().year
end_year = data_sorted['날짜'].max().year
year_options = [{'label': str(year), 'value': str(year)} for year in range(start_year, end_year + 1)]
date_options = ['1개월', '3개월', '6개월', '1년', '3년', '5년', '전체보기']

combined_options = year_options + [{'label': option, 'value': option} for option in date_options]
bid_method_options = [{'label': method, 'value': method} for method in data_sorted['낙찰방식'].unique()]
app.layout = html.Div([
    html.H1("시간에 따른 낙찰률"),
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
    dcc.Dropdown(  # 새로 추가된 부분
        id='bid-method-dropdown',
        options=bid_method_options,
        multi=True,
        placeholder="낙찰 방식 선택"
    ),
    dcc.Graph(id='rate-graph')
])
@app.callback(
    Output('rate-graph', 'figure'),
    Input('date-dropdown', 'value'),
    Input('contractor-dropdown', 'value'),
    Input('bid-method-dropdown', 'value')  # 새로 추가된 부분
)
def update_graph(selected_date, selected_contractors, selected_methods):
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
    
    figure = create_rate_graph_hi(filtered_data, selected_contractors, cutoff_date)
    
    # y축의 스케일을 자동으로 조정
    figure['layout']['yaxis'].update(autorange=True)
    
    return figure
import plotly.graph_objs as go

def create_rate_graph_hi(data, selected_contractors, cutoff_date):
    traces = []
    if selected_contractors is None:
        selected_contractors = []

    # 모든 발주처 데이터를 초록색 마커로 먼저 표시
    trace_all = go.Scattergl(
        x=data['날짜'], 
        y=data['낙찰률'], 
        mode='markers', 
        text=data['발주처'],
        marker=dict(color='green', opacity=0.3)
    )
    traces.append(trace_all)

    # 선택된 발주처 데이터만 빨간색 라인 및 마커로 위에 그립니다.
    for contractor in selected_contractors:
        contractor_data = data[data['발주처'] == contractor]
        trace = go.Scattergl(
            x=contractor_data['날짜'], 
            y=contractor_data['낙찰률'], 
            mode='lines+markers', 
            name=contractor,
            marker=dict(size=10, color='red', opacity=0.7)
        )
        traces.append(trace)
    
    # 가장 많이 나온 상위 100개의 낙찰률을 선택합니다.
    most_common_rates = data['낙찰률'].value_counts().nlargest(50).index
    y_max = data['낙찰률'].max()  # 현재 데이터의 최대 낙찰률
    y_range_max = y_max + (0.1 * y_max)  # y축 범위의 최대값을 현재 최대 낙찰률보다 10% 더 크게 설정

    for rate in most_common_rates:
        # 선 그리기
        line = go.Scatter(
            x=[cutoff_date, data['날짜'].max()],
            y=[rate, rate],
            mode='lines',
            line=dict(width=0.1, color='blue'),
            showlegend=False
        )
        traces.append(line)
        
        # 텍스트 표시
        text = go.Scatter(
            x=[data['날짜'].max() + timedelta(days=5)],  # 텍스트의 x 좌표를 선보다 약간 오른쪽으로 옮김
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
        width=3000, 
        height=2000,
        autosize=True,
        xaxis=dict(
            spikemode='across',
            spikecolor='black',
            spikesnap='cursor',
            spikethickness=1,
            spikedash='dot',
            tickmode='linear',  # 달 단위로 틱 간격을 조절
            tick0=data['날짜'].min(),  # 첫 틱의 위치를 데이터의 최소 날짜로 설정
            dtick="M1",  # 달 단위로 틱 간격 설정
            fixedrange=False 
        ),
        yaxis=dict(
            range=[0, y_range_max],  # y축 범위 설정
            spikemode='across',
            spikecolor='black',
            spikesnap='cursor',
            spikethickness=1,
            spikedash='dot',
            dtick=0.1,  # y축의 틱 간격을 0.1로 설정
            fixedrange=False,
        )
    )
    return {
        'data': traces,
        'layout': layout
    }
if __name__ == "__main__":
    app.run_server(host='0.0.0.0')