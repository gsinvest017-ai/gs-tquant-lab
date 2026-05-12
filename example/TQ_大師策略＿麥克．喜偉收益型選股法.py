# -*- coding: utf-8 -*-
# Auto-generated from TQ_大師策略＿麥克．喜偉收益型選股法.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import pandas as pd 
import numpy as np 
import tejapi
import os 
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Arial'
tej_key ='your key'
tejapi.ApiConfig.api_key = tej_key
os.environ['TEJAPI_BASE'] = "your base"
os.environ['TEJAPI_KEY'] = tej_key

# %% [code] cell 1
from zipline.sources.TEJ_Api_Data import get_universe
pool = get_universe(start = pd.Timestamp('2019-12-01', tz = 'UTC'),
                    end = pd.Timestamp('2023-12-31', tz = "UTC"), 
                    mkt_bd_e = ['TSE', 'OTC'], stktp_e = 'Common Stock')
pool

# %% [code] cell 2
import TejToolAPI

columns = ['Industry', '本益比', '收盤價', '流動比率', '股東權益總計', '負債總額', '營收成長率','eps','mt_div','現金股利率']

start_dt = pd.Timestamp('2019-12-29', tz = 'UTC')
end_dt = pd.Timestamp('2023-12-31', tz = "UTC")

data__ = TejToolAPI.get_history_data(start = start_dt,
                                   end = end_dt,
                                   ticker = pool,
                                   fin_type = 'A', # 為累計資料
                                   columns = columns,
                                   transfer_to_chinese = True)

data__[data__['股票代碼'] == '2330']

# %% [code] cell 3
# 找尋每年當中的12月以及6月的最後一天交易日日期
sample = data__[data__['股票代碼'] == '2330']
last_day_ = list(sample.groupby(sample['日期'].dt.year)['日期'].max())

june_data = sample[sample['日期'].dt.month == 6]
last_june_day = list(june_data.groupby(june_data['日期'].dt.year)['日期'].max())

march_data = sample[sample['日期'].dt.month == 3]
last_march_day = list(march_data.groupby(march_data['日期'].dt.year)['日期'].max())

sep_data = sample[sample['日期'].dt.month == 9]
last_sep_day = list(sep_data.groupby(sep_data['日期'].dt.year)['日期'].max())

last_day_ = last_day_ + last_june_day  + last_march_day + last_sep_day
modified_day = []
for i in last_day_:
    modified_day.append(i.date())


modified_day

# %% [code] cell 4
pools = pool + ['IR0001']
from zipline.data.run_ingest import simple_ingest
# 價量資料
simple_ingest(name = 'tquant' , tickers = pools , start_date = '20191201' , end_date = '20231231')

# %% [code] cell 5
from zipline.api import set_slippage, set_commission, set_benchmark,  symbol,  record, order_target_percent
from zipline.finance import commission, slippage
from zipline import run_algorithm

# %% [code] cell 6
def compute_stock(date, data):  # 創建一個函數，在指定的日期進行選股，輸出篩選出的股票列表。
    # 提取出調整部位當日的股票資訊
    df = data[data['日期'] == pd.Timestamp(date)].reset_index(drop = True)

    # 本益比小於市場平均值
    df['產業平均本益比'] = df.groupby('主產業別_中文')['本益比'].transform('mean')
    set_1 = set(df[df['本益比'] < df['產業平均本益比']]['股票代碼'])

    # 流動比例大於市場平均值
    df['產業平均流動比率'] = df.groupby('主產業別_中文')['流動比率_A'].transform('mean')
    set_2 = set(df[df['流動比率_A'] > df['產業平均流動比率']]['股票代碼'])

    # 負債佔股東權益小於20%
    df['負債佔股東權益'] = df['負債總額_A'] / df['股東權益總計_A']
    set_3 = set(df[df['負債佔股東權益'] < 0.2]['股票代碼'])

    # 現金股利率大於市場平均值
    df['產業平均現金股利率'] = df.groupby('主產業別_中文')['現金股利率'].transform('mean')
    set_4 = set(df[df['現金股利率'] > df['產業平均現金股利率']]['股票代碼'])

    # 股利收益率加上獲利成長率大於10%
    set_5 = set(df[df['營收成長率_A']*0.01 + df['現金股利率']*0.01 > 0.1]['股票代碼'])  # 因為單位問題進行調整，將％調整為正確單位

    tickers = list(set_1 & set_2 & set_3 & set_4 & set_5)

    return tickers

# %% [code] cell 7
def initialize(context):
    set_slippage(slippage.TW_Slippage(spread = 1 , volume_limit = 1))
    # 設定為台灣股票手續費計算方法
    set_commission(commission.Custom_TW_Commission(min_trade_cost=20, discount=1.0, tax = 0.003))
    # 設定台灣大盤為比較基準
    set_benchmark(symbol('IR0001'))
    context.i = 0
    context.state = False
    context.order_tickers = []
    context.last_tickers = []

# %% [code] cell 8
def handle_data(context, data):
    # 避免前視偏誤，在篩選股票下一交易日下單
    if context.state == True:
        print(f"下單日期：{data.current_dt.date()}, 擇股股票數量：{len(context.order_tickers)}")

        for i in context.last_tickers:
            if i not in context.order_tickers:
                order_target_percent(symbol(i), 0)
        
                
        for i in context.order_tickers:
            order_target_percent(symbol(i), 1 / len(context.order_tickers))

            curr = data.current(symbol(i), 'price')
            record(price = curr, days = context.i)
        
        context.last_tickers = context.order_tickers

    context.state = False
    
    backtest_date = data.current_dt.date()
    

    # 查看回測時間是否符合指定日期
    for idx, j in enumerate(modified_day):
        if backtest_date == j:
            # 調整狀態，在下一個交易下單
            context.state = True
            context.order_tickers = compute_stock(date = backtest_date, data = data__)
            

    context.i += 1

# %% [code] cell 9
def analyze(context, perf):
    # plt.style.use('dark_background')
    # 重置為預設樣式
    plt.style.use('default')

    plt.title(f'Portfolio Value')
    plt.plot(perf['portfolio_value'], label='Portfolio Value')
    plt.legend()
    plt.show()

    cumulative_returns = (1 + perf['returns']).cumprod() - 1
    plt.title(f'Period Return Portfolio & Benchmark')
    plt.plot(perf.index, cumulative_returns, label = 'Portfolio')
    plt.plot(perf.index, perf['benchmark_period_return'], label = 'Benchmark')
    plt.legend()
    plt.show()

    perf.to_csv(f"perf_3month.csv")
    #perf.to_csv(f"perf_half_year.csv")
    #perf.to_csv(f"perf_year.csv")
# %% [code] cell 10
capital_base = 1e7

results = run_algorithm(
    start = pd.Timestamp('20191230', tz = 'utc'),
    end = pd.Timestamp('20231230', tz = 'utc'),
    initialize = initialize,
    handle_data = handle_data,
    analyze = analyze,
    bundle = 'tquant',
    capital_base = capital_base
)
results

# %% [code] cell 11
perf_1 = pd.read_csv(f"perf_year.csv")
perf_2 = pd.read_csv(f"perf_half_year.csv")
perf_3 = pd.read_csv(f"perf_3month.csv")


cumulative_returns_1 = (1 + perf_1['returns']).cumprod() - 1
cumulative_returns_2 = (1 + perf_2['returns']).cumprod() - 1
cumulative_returns_3 = (1 + perf_3['returns']).cumprod() - 1
plt.title(f'Period Return Portfolio & Benchmark')
plt.plot(perf_1.index, cumulative_returns_1, label = 'Yearly')
plt.plot(perf_2.index, cumulative_returns_2, label = '6 month')
plt.plot(perf_3.index, cumulative_returns_3, label = '3 month')
plt.plot(perf_3.index, perf_3['benchmark_period_return'], label = 'Benchmark')

plt.legend()
plt.show()

# %% [code] cell 12
import pyfolio
from pyfolio.utils import extract_rets_pos_txn_from_zipline

plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.sans-serif'] = ['Arial']  # 設定為其他可用的字體
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return
pyfolio.plot_gross_leverage(returns, positions)
pyfolio.tears.create_full_tear_sheet(returns=returns,
                                     positions=positions,
                                     transactions=transactions,
                                     benchmark_rets=benchmark_rets
                                    )
