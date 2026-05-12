# -*- coding: utf-8 -*-
# Auto-generated from TQ_機器學習算法 XGBoost 提升技術指標一目均衡表的投資績效.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ## XGBoost 優化 一目均線表策略信號 [單一股票績效]

# %% [code] cell 1
# !pip install tejapi
# !pip install zipline-tej
# %% [code] cell 2
import pandas as pd
import numpy as np
import tejapi
import os
import matplotlib.pyplot as plt

tej_key ='your tej api key'
tejapi.ApiConfig.api_key = tej_key
os.environ['TEJAPI_BASE'] = "your base"
os.environ['TEJAPI_KEY'] = tej_key

import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager as fm
# !wget -O MicrosoftJhengHei.ttf https://github.com/a7532ariel/ms-web/raw/master/Microsoft-JhengHei.ttf
# !wget -O ArialUnicodeMS.ttf https://github.com/texttechnologylab/DHd2019BoA/raw/master/fonts/Arial%20Unicode%20MS.TTF

fm.fontManager.addfont('MicrosoftJhengHei.ttf')
matplotlib.rc('font', family='Microsoft Jheng Hei')

matplotlib.font_manager.fontManager.addfont('ArialUnicodeMS.ttf')
matplotlib.rc('font', family='Arial Unicode MS')

# %% [code] cell 3
import TejToolAPI

start_date = '2006-01-01'; end_date = '2024-12-31'
pool = ['6446']
start = pd.Timestamp(start_date, tz = 'utc')
end = pd.Timestamp(end_date, tz = 'utc')
columns = ['coid','Industry', 'vol', 'open_d', 'high_d', 'low_d', 'close_d', 'roi']
df = TejToolAPI.get_history_data(start = start, end = end,
                                 ticker = pool,
                                 columns = columns,
                                 transfer_to_chinese = True)

df

# %% [code] cell 4
def ichimoku_cloud(df):

    high_9 = df['最高價'].rolling(window = 9).max()
    low_9 = df['最低價'].rolling(window = 9).min()

    df['Tenkan_sen'] = (high_9 + low_9) / 2

    high_26 = df['最高價'].rolling(window = 26).max()
    low_26 = df['最低價'].rolling(window = 26).min()

    df['Kijun_sen'] = (high_26 + low_26) / 2

    df['Senkou_Span_A'] = ((df['Tenkan_sen'] + df['Kijun_sen']) / 2).shift(26)

    high_52 = df['最高價'].rolling(window = 52).max()
    low_52 = df['最低價'].rolling(window = 52).min()
    df['Senkou_Span_B'] = ((high_52 + low_52) / 2).shift(26)

    df['Chikou_Span'] = df['收盤價'].shift(-26)

    df['Cloud'] = np.where(
    df['Senkou_Span_A'] < df['Senkou_Span_B'],
    'red',
    'green')


    return df

df = ichimoku_cloud(df)
df

# %% [code] cell 5
# 先產生原始信號
conditions = [
    (df['收盤價'] > df['Senkou_Span_B']) & (df['Cloud'] == 'red') & (df['Tenkan_sen'] > df['Kijun_sen'] * 0.01),
    (df['收盤價'] < df['Senkou_Span_B']) & (df['Cloud'] == 'green') & (df['Tenkan_sen'] < df['Kijun_sen'] * 0.99)
]
choices = ['Buy', 'Sell']
df['RawSignal'] = np.select(conditions, choices, default=np.nan)

# 只保留信號變化的那一刻，連續相同的信號僅保留第一筆
df['Signal'] = df['RawSignal'].where(df['RawSignal'] != df['RawSignal'].shift())
df['Signal'] = np.where(df['Signal'].isin(['Buy', 'Sell']), df['Signal'], 'Hold')

df['Buy_Point'] = np.where(df['Signal'] == 'Buy', df['收盤價'], np.nan)
df['Sell_Point'] = np.where(df['Signal'] == 'Sell', df['收盤價'], np.nan)

# %% [code] cell 6
tab10 = [
    "#1f77b4",  # C0 - 藍色
    "#ff7f0e",  # C1 - 橙色
    "#2ca02c",  # C2 - 綠色
    "#d62728",  # C3 - 紅色
    "#9467bd",  # C4 - 紫色
    "#8c564b",  # C5 - 棕色
    "#e377c2",  # C6 - 粉色
    "#7f7f7f",  # C7 - 灰色
    "#bcbd22",  # C8 - 黃綠色
    "#17becf"   # C9 - 青色
]
split_index = int(len(df) * 0.8)

data = df.iloc[split_index:].copy()

data = data.set_index('日期', drop = False)
plt.figure(figsize = (16,8))
plt.style.use("default")
plt.plot(data.index, data['收盤價'], color=tab10[0], label='Price')
plt.plot(data.index, data['Tenkan_sen'], color=tab10[1], label='Tenkan_sen')
plt.plot(data.index, data['Kijun_sen'], color=tab10[2], label='Kijun_sen')
plt.fill_between(data.index, data['Senkou_Span_A'], data['Senkou_Span_B'],
                    where=data['Senkou_Span_A'] >= data['Senkou_Span_B'],
                    facecolor='lightgreen', alpha=0.5, label='Bullish_Cloud')
plt.fill_between(data.index, data['Senkou_Span_A'], data['Senkou_Span_B'],
                    where=data['Senkou_Span_A'] < data['Senkou_Span_B'],
                    facecolor='lightcoral', alpha=0.5, label='Bearish_Cloud')

# 利用 scatter 畫出買入點 (用向上三角形表示)
plt.scatter(data.index, data['Buy_Point'], marker='^', color='green', s=50, label='Buy')

# 利用 scatter 畫出賣出點 (用向下三角形表示)
plt.scatter(data.index, data['Sell_Point'], marker='v', color='red', s=50, label='Sell')

plt.title(f'{pool}Ichimoku_Cloud')
plt.legend()
plt.show()

# %% [code] cell 7
import pandas as pd
import numpy as np
import xgboost as xgb
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.metrics import classification_report

# %% [code] cell 8
data_ml = df[:].copy()
# 設定交易信號：如果未來 5 天內價格上漲 3%，則標記為 'Buy'
data_ml['Target'] = np.where(data_ml['收盤價'].shift(-5) > data_ml['收盤價'] * 1.03, 'Buy',
                                np.where(data_ml['收盤價'].shift(-5) < data_ml['收盤價'] * 0.97, 'Sell', 'Hold'))

# 把 'Buy'、'Sell'、'Hold' 轉成數字（0, 1, 2）
data_ml['Target'] = data_ml['Target'].map({'Buy': 1, 'Sell': 2, 'Hold': 0})

# %% [code] cell 9
# 1. 資料讀取與前處理
data_ml = data_ml.set_index('日期', drop = False)

# 若想預測隔天收盤價，可以將目標設為收盤價向前平移一個交易日
data_ml['目標收盤價'] = data_ml['收盤價'].shift(-1)

# 2. 特徵與目標設定
# 這裡僅用最基本的價格與成交量作為特徵，你也可以加入其他技術指標（例如 MA、RSI 等）
features = ['開盤價', '最高價', '最低價', '收盤價', '成交量_千股']
features2 = ['Tenkan_sen','Kijun_sen', 'Senkou_Span_A', 'Senkou_Span_B','Chikou_Span', '收盤價', '成交量_千股','開盤價', '最高價', '最低價']
X = data_ml[features2]
y = data_ml['Target']


# 3. 資料切分（依時間順序切分，不建議隨機切分）
# 切分時間點為 2021-03-04
split_index = int(len(data_ml) * 0.8)

X_train, X_test = X.iloc[52:split_index], X.iloc[split_index:-1]
y_train, y_test = y.iloc[52:split_index], y.iloc[split_index:-1]
dates_test = data_ml['日期'].iloc[split_index:-1]  # 用於後續繪圖


model = xgb.XGBClassifier(
    n_estimators=500,  # 樹的數量
    max_depth=5,       # 控制樹的深度，防止過擬合
    learning_rate=0.05, # 設定學習率
    subsample=0.8,     # 使用 80% 數據訓練每棵樹，提高泛化能力
    colsample_bytree=0.8,  # 降低過擬合風險
    random_state=42,
    use_label_encoder=False,  # 避免 warning
    eval_metric="mlogloss"  # 適合多類別分類
)


# 訓練 XGBoost 模型
model.fit(X_train, y_train)

# 進行預測
y_pred = model.predict(X_test)


# %% [code] cell 10
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager as fm
# !wget -O MicrosoftJhengHei.ttf https://github.com/a7532ariel/ms-web/raw/master/Microsoft-JhengHei.ttf
# !wget -O ArialUnicodeMS.ttf https://github.com/texttechnologylab/DHd2019BoA/raw/master/fonts/Arial%20Unicode%20MS.TTF

fm.fontManager.addfont('MicrosoftJhengHei.ttf')
matplotlib.rc('font', family='Microsoft Jheng Hei')

matplotlib.font_manager.fontManager.addfont('ArialUnicodeMS.ttf')
matplotlib.rc('font', family='Arial Unicode MS')

# 產生分類報告
print(classification_report(y_test, y_pred))

# 繪製特徵重要性圖
xgb.plot_importance(model)
plt.show()



from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

# 計算混淆矩陣
cm = confusion_matrix(y_test, y_pred)

# 顯示混淆矩陣
disp = ConfusionMatrixDisplay(confusion_matrix=cm)
disp.plot()
plt.show()


from sklearn.metrics import classification_report

print(classification_report(y_test, y_pred))

# %% [code] cell 11
df_test = df.iloc[split_index:-1].copy()  # 取得測試集的對應資料
df_test['日期'] = pd.to_datetime(df_test['日期'])
df_test = df_test.set_index('日期', drop = False)
df_test['Predicted_Signal'] = y_pred  # 新增預測結果


df_test['Predicted_Signal'].plot(figsize = (12, 8))
df_test['Predicted_Signal'].value_counts()

# %% [code] cell 12
from zipline.data.run_ingest import simple_ingest
from zipline.api import set_slippage, set_commission, set_benchmark,  symbol,  record
from zipline.api import order_target_percent, order_percent, order
from zipline.api import set_long_only, set_max_leverage

from zipline.finance import commission, slippage
from zipline import run_algorithm

# %% [code] cell 13
pools = pool + ['IR0001']

start_ingest = start_date.replace('-', '')
end_ingest = end_date.replace('-', '')

simple_ingest(name = 'tquant' , tickers = pools , start_date = start_ingest , end_date = end_ingest)

# %% [code] cell 14
def initialize(context, pools = pools):
        set_slippage(slippage.VolumeShareSlippage(volume_limit=1, price_impact=0.01))
        set_commission(commission.Custom_TW_Commission())
        set_benchmark(symbol(pools[0]))
        context.i = 0
        context.state = np.nan
        context.mix_state = np.nan
        context.pools = pools
        #set_long_only(on_error='log')
        #set_max_leverage(1.5)


def handle_data_raw(context, data, api_data = df_test):
          context.i += 1
          backtest_date = data.current_dt.date()
          today_data = api_data[api_data['日期'] == pd.Timestamp(backtest_date)]
          context.state = today_data['Signal'].iloc[0]


          portfolio_value = context.portfolio.portfolio_value
          position_value = context.portfolio.positions_value
          current_allocation = position_value / portfolio_value
          print(f'回測股票{pool[0]}，使用一般策略，回測日期：{backtest_date}, 持倉比例：{current_allocation:.2f}')

          if context.state == "Buy":
                  if current_allocation == 0:
                          order_target_percent(symbol(pool[0]), 0.5)

                  elif current_allocation >= 0.95:
                          order_target_percent(symbol(pool[0]), 1.0)

                  elif current_allocation <= 0.95:
                          order_target_percent(symbol(pool[0]), min(current_allocation + 0.2, 1))

          if context.state =="Sell":
                  if current_allocation <= 0.05:
                          order_target_percent(symbol(pool[0]), 0)

                  else:
                          order_target_percent(symbol(pool[0]), max(current_allocation - 0.2, -1))

          if context.state == np.nan:
                  if current_allocation > 1.0:
                          order_target_percent(symbol(pool[0]), 1.0)

                  if current_allocation < 0:
                        order_target_percent(symbol(pool[0]), 0)



def handle_data_mix(context, data, api_data = df_test):
          context.i += 1
          backtest_date = data.current_dt.date()
          today_data = api_data[api_data['日期'] == pd.Timestamp(backtest_date)]
          context.state = today_data['Signal'].iloc[0]
          context.mix_state = today_data['Predicted_Signal'].iloc[0]


          portfolio_value = context.portfolio.portfolio_value
          position_value = context.portfolio.positions_value
          current_allocation = position_value / portfolio_value
          print(f'回測股票{pool[0]}，使用混合策略（技術指標為主），回測日期：{backtest_date}, 持倉比例：{current_allocation:.2f}')

          if context.state == "Buy":
                  if current_allocation == 0:
                          order_target_percent(symbol(pool[0]), 0.5)

                  elif current_allocation >= 0.95:
                          order_target_percent(symbol(pool[0]), 1.0)

                  elif context.mix_state == 1:
                          order_target_percent(symbol(pool[0]), min(current_allocation + 0.3, 1.0))

                  else:
                          order_target_percent(symbol(pool[0]), min(current_allocation + 0.1, 1.0))




          if context.state =="Sell":
                  if current_allocation <= 0.05:
                          order_target_percent(symbol(pool[0]), 0)
                  elif context.mix_state == 2:
                          order_target_percent(symbol(pool[0]), max(current_allocation - 0.3, 0))
                  else:
                          order_target_percent(symbol(pool[0]), max(current_allocation - 0.1, 0))

          if context.state == np.nan:
                  if current_allocation > 1.0:
                          order_target_percent(symbol(pool[0]), 1.0)
                  if current_allocation < 0:
                        order_target_percent(symbol(pool[0]), 0)

def handle_data_ml(context, data, api_data = df_test):
        context.i += 1
        backtest_date = data.current_dt.date()
        today_data = api_data[api_data['日期'] == pd.Timestamp(backtest_date)]
        context.mix_state = today_data['Predicted_Signal'].iloc[0]


        portfolio_value = context.portfolio.portfolio_value
        position_value = context.portfolio.positions_value
        current_allocation = position_value / portfolio_value
        print(f'回測股票{pool[0]}，使用機器學習策略 XGBoost，回測日期：{backtest_date}, 持倉比例：{current_allocation:.2f}')

        if context.mix_state == 1:
                if current_allocation == 0:
                        order_target_percent(symbol(pool[0]), 0.5)

                if current_allocation > 0.95:
                        order_target_percent(symbol(pool[0]), 1.0)

                if current_allocation <= 0.95:
                        order_target_percent(symbol(pool[0]), min(current_allocation + 0.2, 1.0))  # 增加部位但不超過 100%


        if context.mix_state == 2:
                if current_allocation <= 0.05:
                        order_target_percent(symbol(pool[0]), 0)

                else:
                        order_target_percent(symbol(pool[0]), max(current_allocation - 0.2, -1.0))  # 限制最大空頭部位為 -100%


        if context.mix_state == 0:
                if current_allocation >= 1.0:
                        order_target_percent(symbol(pool[0]), 1.0)
                if current_allocation <= 0:
                        order_target_percent(symbol(pool[0]), 0)




def handle_data_mix_2(context, data, api_data = df_test):
        context.i += 1
        backtest_date = data.current_dt.date()
        today_data = api_data[api_data['日期'] == pd.Timestamp(backtest_date)]
        context.state = today_data['Signal'].iloc[0]
        context.mix_state = today_data['Predicted_Signal'].iloc[0]


        portfolio_value = context.portfolio.portfolio_value
        position_value = context.portfolio.positions_value
        current_allocation = position_value / portfolio_value
        print(f'回測股票{pool[0]}，使用混合策略(機器學習為主體），回測日期：{backtest_date}, 持倉比例：{current_allocation:.2f}')

        if context.mix_state == 1:
                if current_allocation == 0:
                        order_target_percent(symbol(pool[0]), 0.5)

                elif current_allocation >= 0.95:
                        order_target_percent(symbol(pool[0]), 1.0)

                elif context.state == 'Buy':
                        order_target_percent(symbol(pool[0]), min(current_allocation + 0.3, 1.0))

                else:
                        order_target_percent(symbol(pool[0]), min(current_allocation + 0.1, 1.0))




        if context.mix_state == 2:
                if current_allocation <= 0.05:
                        order_target_percent(symbol(pool[0]), 0)
                elif context.state == 'Sell':
                        order_target_percent(symbol(pool[0]), max(current_allocation - 0.3, 0))
                else:
                        order_target_percent(symbol(pool[0]), max(current_allocation - 0.1, 0))

        if context.mix_state == 0:
                if current_allocation >= 1.0:
                        order_target_percent(symbol(pool[0]), 1.0)

                if current_allocation < 0:
                        order_target_percent(symbol(pool[0]), -1.0)
# %% [code] cell 15
handle_data = [handle_data_mix, handle_data_ml, handle_data_mix_2 ,handle_data_raw]

strategy_results = pd.DataFrame()
test_results = pd.DataFrame()
leverage_results = pd.DataFrame()
sharp_results = pd.DataFrame()
for idx, method in enumerate(handle_data):
  def analyze(context, perf):
        #perf.to_csv(f"{method}.csv")
        #print(f"績效以保存至{method}.csv")
        strategy_results[idx] = (1 + perf['returns']).cumprod() - 1
        strategy_results['benchmark_return'] = perf['benchmark_period_return']

        test_results[idx] = perf['returns']
        test_results['benchmark'] = perf['benchmark_return']

        leverage_results[idx] = perf['net_leverage']

        sharp_results[idx] = perf['sharpe']



  results = run_algorithm(
            start = pd.Timestamp(df_test['日期'].iloc[0], tz = 'utc'),
            end = pd.Timestamp(df_test['日期'].iloc[-1], tz = 'utc'),
            initialize = initialize,
            handle_data = method,
            analyze = analyze,
            bundle = 'tquant',
            capital_base = 1e8)

# %% [code] cell 16
# 調整 benchmark 的基準位置，讓累積報酬率從 0 開始
strategy_results['benchmark_return'] = strategy_results['benchmark_return'] - strategy_results['benchmark_return'].iloc[0]

print(f"Benchmark Return: {strategy_results['benchmark_return'].iloc[-1]:.2%}")
print(f"Raw Strategy Return: {strategy_results[3].iloc[-1]:.2%}")
print(f"Mix Strategy 1 Return(技術指標為主): {strategy_results[0].iloc[-1]:.2%}")
print(f"ML Strategy Return: {strategy_results[1].iloc[-1]:.2%}")
print(f"Mix Strategy 2 Return(機器學習為主): {strategy_results[2].iloc[-1]:.2%}")

plt.figure(figsize = (20,8))
plt.plot(strategy_results.index, strategy_results[3], color = tab10[0], label = 'Raw_Strategy')
plt.plot(strategy_results.index, strategy_results[0], color = tab10[1], label = 'Mix_Strategy_1')
plt.plot(strategy_results.index, strategy_results[1], color = tab10[2], label = 'ML_Strategy')
plt.plot(strategy_results.index, strategy_results[2], color = tab10[3], label = 'Mix_Strategy_2')
plt.plot(strategy_results.index, strategy_results['benchmark_return'], color = tab10[4], label = 'Buy_and_Hold_Strategy')
plt.title(f'{pool[0]} Strategy Comparison with XGBoost')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
plt.show()

# %% [code] cell 17
df_analyze = df
df_analyze = df_analyze.set_index('日期', drop = False)
backtest_start = df_test['日期'].iloc[0]
backtest_end = df_test['日期'].iloc[-1]

print(f"回測期間：{backtest_start} 至 {backtest_end}")

# %% [code] cell 18
# 設定圖表大小
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(20, 15), sharex=False)

# 第一張圖：波動率 (Volatility)
df_analyze['Volatility'] = df_analyze['報酬率'].rolling(window=50).std() * np.sqrt(252)
axes[0].plot(df_analyze.index, df_analyze['Volatility'], color=tab10[5], label = "Volatility")
axes[0].axvline(pd.to_datetime(backtest_start), color='red', linestyle='--', label="Test Start")
axes[0].axvline(pd.to_datetime(backtest_end), color='red', linestyle='--', label="Test End")
axes[0].set_title(f'{pool[0]} Volatility')
axes[0].set_ylabel('Volatility')
axes[0].legend()

# 第二張圖：50日均線斜率 (Trend Slope)
df_analyze['trend_slope'] = df_analyze['收盤價'].rolling(window=50).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0], raw=True)
axes[1].plot(df_analyze.index, df_analyze['trend_slope'], label='Trend Slope (50d)', color=tab10[6])
axes[1].axvline(pd.to_datetime(backtest_start), color='red', linestyle='--', label="Test Start")
axes[1].axvline(pd.to_datetime(backtest_end), color='red', linestyle='--', label="Test End")
axes[1].axhline(0, linestyle='--', color=tab10[0])
axes[1].set_title(f"{pool[0]} Market Trend Slope Over Time")
axes[1].set_ylabel("Trend Slope")
axes[1].legend()

# 第三張圖：收盤價 (Closing Price)
axes[2].plot(df_analyze.index, df_analyze['收盤價'], color=tab10[7], label = 'Price')
axes[2].axvline(pd.to_datetime(backtest_start), color='red', linestyle='--', label="Test Start")
axes[2].axvline(pd.to_datetime(backtest_end), color='red', linestyle='--', label="Test End")
axes[2].set_title(f"{pool[0]} Closing Price")
axes[2].set_xlabel('Date')
axes[2].set_ylabel("Price")
axes[2].legend()

# 調整子圖間距
plt.tight_layout()

# 顯示圖表
plt.show()

# %% [code] cell 19
strategy_analysis_1 = strategy_results.copy()
strategy_analysis_1 = strategy_analysis_1.rename(columns = {0: 'Mix_Strategy_1', 1:'ML_Strategy', 2:'Mix_Strategy_2', 3:'Raw_Strategy'})


strategy_analysis_2 = test_results.copy()
strategy_analysis_2 = strategy_analysis_2.rename(columns = {0: 'Mix_Strategy_1', 1:'ML_Strategy', 2:'Mix_Strategy_2', 3:'Raw_Strategy'})

strategy_analysis_3 = leverage_results.copy()
strategy_analysis_3 = strategy_analysis_3.rename(columns = {0: 'Mix_Strategy_1', 1:'ML_Strategy', 2:'Mix_Strategy_2', 3:'Raw_Strategy'})


strategy_analysis_4 = sharp_results.copy()
strategy_analysis_4 = strategy_analysis_4.rename(columns = {0: 'Mix_Strategy_1', 1:'ML_Strategy', 2:'Mix_Strategy_2', 3:'Raw_Strategy'})
# %% [code] cell 20
fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(30, 20), sharex=False)


# 四個策略和基準的波動度圖表
days = 50
strategy_analysis_2['ML_Strategy_vol'] = strategy_analysis_2['ML_Strategy'].rolling(window=days).std() * np.sqrt(252)
strategy_analysis_2['Mix_Strategy_1_vol'] = strategy_analysis_2['Mix_Strategy_1'].rolling(window=days).std() * np.sqrt(252)
strategy_analysis_2['Mix_Strategy_2_vol'] = strategy_analysis_2['Mix_Strategy_2'].rolling(window=days).std() * np.sqrt(252)
strategy_analysis_2['Raw_Strategy_vol'] = strategy_analysis_2['Raw_Strategy'].rolling(window=days).std() * np.sqrt(252)
strategy_analysis_2['benchmark_vol'] = strategy_analysis_2['benchmark'].rolling(window=days).std() * np.sqrt(252)

axes[1].plot(strategy_analysis_2.index, strategy_analysis_2['ML_Strategy_vol'], label='ML_Strategy', color=tab10[2])
axes[1].plot(strategy_analysis_2.index, strategy_analysis_2['Mix_Strategy_1_vol'], label='Mix_Strategy_1', color=tab10[1])
axes[1].plot(strategy_analysis_2.index, strategy_analysis_2['Mix_Strategy_2_vol'], label='Mix_Strategy_2', color=tab10[3])
axes[1].plot(strategy_analysis_2.index, strategy_analysis_2['Raw_Strategy_vol'], label='Raw_Strategy', color=tab10[0])
axes[1].plot(strategy_analysis_2.index, strategy_analysis_2['benchmark_vol'], label='Benchmark', color=tab10[4])
axes[1].set_title(f'{pool[0]} Volatility (window = {days})')
axes[1].set_xlabel('Date')
axes[1].set_ylabel('Standard deviation')
axes[1].legend()



axes[0].plot(strategy_analysis_1.index, strategy_analysis_1['Raw_Strategy'], color = tab10[0], label = 'Raw_Strategy')
axes[0].plot(strategy_analysis_1.index, strategy_analysis_1['Mix_Strategy_1'], color = tab10[1], label = 'Mix_Strategy_1')
axes[0].plot(strategy_analysis_1.index, strategy_analysis_1['ML_Strategy'], color = tab10[2], label = 'ML_Strategy')
axes[0].plot(strategy_analysis_1.index, strategy_analysis_1['Mix_Strategy_2'], color = tab10[3], label = 'Mix_Strategy_2')
axes[0].plot(strategy_analysis_1.index, strategy_analysis_1['benchmark_return'], color = tab10[4], label = 'Buy_and_Hold_Strategy')
axes[0].set_title(f'{pool[0]} Strategy Comparison with XGBoost')
axes[0].set_xlabel('Date')
axes[0].set_ylabel('Cumulative Return')
axes[0].legend()


axes[2].plot(strategy_analysis_3.index, strategy_analysis_3['Raw_Strategy'], color = tab10[0], label = 'Raw_Strategy')
axes[2].plot(strategy_analysis_3.index, strategy_analysis_3['Mix_Strategy_1'], color = tab10[1], label = 'Mix_Strategy_1')
axes[2].plot(strategy_analysis_3.index, strategy_analysis_3['ML_Strategy'], color = tab10[2], label = 'ML_Strategy')
axes[2].plot(strategy_analysis_3.index, strategy_analysis_3['Mix_Strategy_2'], color = tab10[3], label = 'Mix_Strategy_2')
axes[2].set_title(f'{pool[0]} Portfolio Allocation')
axes[2].set_xlabel('Date')
axes[2].set_ylabel('Net Leverage')
axes[2].legend()

axes[3].plot(strategy_analysis_4.index, strategy_analysis_4['Raw_Strategy'], color = tab10[0], label = 'Raw_Strategy')
axes[3].plot(strategy_analysis_4.index, strategy_analysis_4['Mix_Strategy_1'], color = tab10[1], label = 'Mix_Strategy_1')
axes[3].plot(strategy_analysis_4.index, strategy_analysis_4['ML_Strategy'], color = tab10[2], label = 'ML_Strategy')
axes[3].plot(strategy_analysis_4.index, strategy_analysis_4['Mix_Strategy_2'], color = tab10[3], label = 'Mix_Strategy_2')
axes[3].set_title(f'{pool[0]} Sharpe Ratio')
axes[3].set_xlabel('Date')
axes[3].set_ylabel('Sharpe Ratio(6 month)')
axes[3].legend()
# 調整子圖間距
plt.tight_layout()

# 顯示圖表
plt.show()

# %% [code] cell 21
plt.figure(figsize = (20,6))
plt.plot(strategy_analysis_2.index, strategy_analysis_2['ML_Strategy_vol'], label='ML_Strategy', color=tab10[2])
plt.plot(strategy_analysis_2.index, strategy_analysis_2['Mix_Strategy_1_vol'], label='Mix_Strategy_1', color=tab10[1])
plt.plot(strategy_analysis_2.index, strategy_analysis_2['Mix_Strategy_2_vol'], label='Mix_Strategy_2', color=tab10[3])
plt.plot(strategy_analysis_2.index, strategy_analysis_2['Raw_Strategy_vol'], label='Raw_Strategy', color=tab10[0])
plt.plot(strategy_analysis_2.index, strategy_analysis_2['benchmark_vol'], label='Benchmark', color=tab10[4])
plt.title(f'{pool[0]} Volatility (window = {days})')
plt.xlabel('Date')
plt.ylabel('Standard deviation')
plt.legend()
plt.show()

# %% [code] cell 22
plt.figure(figsize = (20,6))
plt.plot(strategy_analysis_3.index, strategy_analysis_3['Raw_Strategy'], color = tab10[0], label = 'Raw_Strategy')
plt.plot(strategy_analysis_3.index, strategy_analysis_3['Mix_Strategy_1'], color = tab10[1], label = 'Mix_Strategy_1')
plt.plot(strategy_analysis_3.index, strategy_analysis_3['ML_Strategy'], color = tab10[2], label = 'ML_Strategy')
plt.plot(strategy_analysis_3.index, strategy_analysis_3['Mix_Strategy_2'], color = tab10[3], label = 'Mix_Strategy_2')
plt.title(f'{pool[0]} Portfolio Allocation')
plt.xlabel('Date')
plt.ylabel('Net Leverage')
plt.legend()
plt.show()

# %% [code] cell 23
plt.figure(figsize = (20,6))
plt.plot(strategy_analysis_4.index, strategy_analysis_4['Raw_Strategy'], color = tab10[0], label = 'Raw_Strategy')
plt.plot(strategy_analysis_4.index, strategy_analysis_4['Mix_Strategy_1'], color = tab10[1], label = 'Mix_Strategy_1')
plt.plot(strategy_analysis_4.index, strategy_analysis_4['ML_Strategy'], color = tab10[2], label = 'ML_Strategy')
plt.plot(strategy_analysis_4.index, strategy_analysis_4['Mix_Strategy_2'], color = tab10[3], label = 'Mix_Strategy_2')
plt.title(f'{pool[0]} Sharpe Ratio')
plt.xlabel('Date')
plt.ylabel('Sharpe Ratio(6 month)')
plt.legend()
plt.show()

# %% [code] cell 24
import matplotlib
import matplotlib.font_manager as fm
# !wget -O MicrosoftJhengHei.ttf https://github.com/a7532ariel/ms-web/raw/master/Microsoft-JhengHei.ttf
# !wget -O ArialUnicodeMS.ttf https://github.com/texttechnologylab/DHd2019BoA/raw/master/fonts/Arial%20Unicode%20MS.TTF

fm.fontManager.addfont('MicrosoftJhengHei.ttf')
matplotlib.rc('font', family='Microsoft Jheng Hei')

fm.fontManager.addfont('ArialUnicodeMS.ttf')
matplotlib.rc('font', family='Arial Unicode MS')

import pyfolio
from pyfolio.utils import extract_rets_pos_txn_from_zipline

returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return
pyfolio.tears.create_full_tear_sheet(returns=returns,
                                     positions=positions,
                                     transactions=transactions,
                                     benchmark_rets=benchmark_rets
                                    )

# %% [code] cell 25
corr = df_analyze[['trend_slope', 'Volatility']].corr()
print(f"Trend Slope & Volatility Correlation Matrix")
print(corr)
print("-"*50)



from scipy.stats import ttest_ind

# 設定兩組回報率
returns_raw = test_results[0]
returns_mix1 = test_results[1]
returns_ml = test_results[2]
returns_mix2 = test_results[3]
returns_bh = test_results['benchmark']


testing = [returns_raw, returns_mix1, returns_ml, returns_mix2]

for var in testing:
    var_name = [name for name, value in globals().items() if value is var][0]  # 找到變數名稱
    t_stat, p_value = ttest_ind(var, returns_bh, equal_var=False)
    print(f"{var_name}: T-statistic = {t_stat:.4f}, P-value = {p_value:.4f}")