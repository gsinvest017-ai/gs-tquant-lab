# -*- coding: utf-8 -*-
# Auto-generated from TQ_布林通道交易策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 布林通道實戰
#
# ## 交易邏輯
#
# * 根據統計學的常態分佈理論，有 95.44% 的樣本都會位於正負兩個標準差這個區間，因此當股價超出這區間時，產生反轉的機率會大幅上升。
# * 我們可以把移動平均、正二標準差、負二標準差，轉換成中軌、上軌、下軌
#
# ## 交易策略
#
# * 當今天的收盤價觸碰到上軌且持有部位時，隔日賣出。
# * 當今天的收盤價觸碰到下軌且現金部位大於零時，隔日買入。
# * 當今天的收盤價觸碰到下軌、現金部位大於零且當日收盤價低於上次買入訊號收盤價時，隔日加碼一單位。
#
# ## 資料來源
#
# [布林通道交易策略](https://www.tejwin.com/insight/%e5%b8%83%e6%9e%97%e9%80%9a%e9%81%93%e4%ba%a4%e6%98%93%e7%ad%96%e7%95%a5/)

# %% [markdown] cell 1
# ## 編輯交易策略
#
# ### 載入所需套件與輸入資料

# %% [code] cell 2
import pandas as pd 
import numpy as np 
import tejapi
import os 
import matplotlib.pyplot as plt

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'YOUR KEY'
os.environ['mdate'] = '20210401 20221231'
os.environ['ticker'] = '2409'

# 使用 ingest 將股價資料導入暫存，並且命名該股票組合 (bundle) 為 tquant
# !zipline ingest -b tquant 

# %% [markdown] cell 3
# ### 載入所需套件

# %% [code] cell 4
from zipline.api import set_slippage, set_commission, set_benchmark, attach_pipeline, order, order_target, symbol, pipeline_output, record
from zipline.finance import commission, slippage
from zipline.data import bundles
from zipline import run_algorithm
from zipline.pipeline import Pipeline
from zipline.pipeline.filters import StaticAssets
from zipline.pipeline.factors import BollingerBands
from zipline.pipeline.data import EquityPricing

# %% [markdown] cell 5
# ### 建立 Pipeline 函式
#
# `Pipeline()` 提供使用者快速處理多檔標的的量化指標與價量資料的功能，於本次案例我們用以處理:
#
# * 過去 20 日布林通道上軌
# * 過去 20 日布林通道中軌
# * 過去 20 日布林通道下軌
# * 當期收盤價

# %% [code] cell 6
def make_pipeline():
    
    perf = BollingerBands(inputs=[EquityPricing.close], window_length=20, k=2)
    upper,middle,lower = perf.upper,perf.middle, perf.lower
    curr_price = EquityPricing.close.latest
     
    return Pipeline(
        columns = {
            'upper':  upper,
            'middle':  middle,
            'lower':  lower,
            'curr_price':curr_price
        }
    )

# %% [markdown] cell 7
# ### 建立 initialize 函式
#
# `inintialize` 函式用於定義交易開始前的每日交易環境，與此例中我們設置:
#
# * 流動性滑價
# * 交易手續費
# * 買入持有友達的報酬作為基準
# * 將 Pipeline 導入交易流程中
# * 設定 __context.last_signal_price__ 紀錄上次買入訊號的收盤價

# %% [code] cell 8
def initialize(context):
    context.last_buy_price = 0
    set_slippage(slippage.VolumeShareSlippage())
    set_commission(commission.PerShare(cost=0.00285))
    set_benchmark(symbol('2409'))
    attach_pipeline(make_pipeline(), 'mystrategy')
    context.last_signal_price = 0

# %% [markdown] cell 9
# ### 建立 handle_date 函式
#
# `handle_data` 函式用於處理每天的交易策略或行動。

# %% [code] cell 10
def handle_data(context, data):
    out_dir = pipeline_output('mystrategy')
    for i in out_dir.index: 
        upper = out_dir.loc[i, 'upper']
        middle = out_dir.loc[i, 'middle']
        lower = out_dir.loc[i, 'lower']
        curr_price = out_dir.loc[i, 'curr_price']
        cash_position = context.portfolio.cash
        stock_position = context.portfolio.positions[i].amount
        
        buy, sell = False, False
        record(price = curr_price, upper = upper, lower = lower, buy = buy, sell = sell)
        
        if stock_position == 0:
            if (curr_price <= lower) and (cash_position >= curr_price * 1000):
                order(i, 1000)
                context.last_signal_price = curr_price
                buy = True
                record(buy = buy)
        elif stock_position > 0:
            if (curr_price <= lower) and (curr_price <= context.last_signal_price) and (cash_position >= curr_price * 1000):
                order(i, 1000)
                context.last_signal_price = curr_price
                buy = True
                record(buy = buy)
            elif (curr_price >= upper):
                order_target(i, 0)
                context.last_signal_price = 0
                sell = True
                record(sell = sell)
            else:
                pass
        else:
            pass

# %% [markdown] cell 11
# ### 建立 analyze 函式
#
# 多半用於繪製績效圖表，於本案例使用 matplotlib 將視覺化買賣點與投組價值變化。

# %% [code] cell 12
def analyze(context, perf):
    fig = plt.figure()
    ax1 = fig.add_subplot(211)
    perf.portfolio_value.plot(ax=ax1)
    ax1.set_ylabel("Portfolio value (NTD)")
    ax2 = fig.add_subplot(212)
    ax2.set_ylabel("Price (NTD)")
    perf.price.plot(ax=ax2)
    perf.upper.plot(ax=ax2)
    perf.lower.plot(ax=ax2)
    ax2.plot( # 繪製買入訊號
        perf.index[perf.buy],
        perf.loc[perf.buy, 'price'],
        '^',
        markersize=5,
        color='red'
    )
    ax2.plot( # 繪製賣出訊號
        perf.index[perf.sell],
        perf.loc[perf.sell, 'price'],
        'v',
        markersize=5,
        color='green'
    )
    plt.legend(loc=0)
    plt.gcf().set_size_inches(18,8)
    plt.show()
# %% [markdown] cell 13
# ## 執行交易策略
#
# 使用 `run_algorithm` 執行上述所編撰的交易策略，設置交易期間為 2021-06-01 到 2022-12-31，所使用資料集為 *tquant*，初始資金為 500,000 元。其中輸出的 __results__ 就是每日績效與交易的明細表。

# %% [code] cell 14
results = run_algorithm(
    start = pd.Timestamp('2021-06-01', tz='UTC'),
    end = pd.Timestamp('2022-12-31', tz ='UTC'),
    initialize=initialize,
    bundle='tquant',
    analyze=analyze,
    capital_base=5e5,
    handle_data = handle_data
)

results

# %% [markdown] cell 15
# ## 績效評估
#
# 使用 `extract_rets_pos_txn_from_zipline()` 計算報酬、部位與交易紀錄。

# %% [code] cell 16
import pyfolio as pf 
returns, positions, transactions = pf.utils.extract_rets_pos_txn_from_zipline(results)

# %% [markdown] cell 17
# ### 報酬紀錄

# %% [code] cell 18
returns.tail()

# %% [markdown] cell 19
# ### 部位紀錄

# %% [code] cell 20
positions.head()

# %% [markdown] cell 21
# ### 交易紀錄

# %% [code] cell 22
transactions.head()

# %% [markdown] cell 23
# ### 繪製基準 (benchmark) 與投組累積報酬率
#
# 使用 `plot_rolling_returns()` 繪製，本案例的基準為友達買入持有。

# %% [code] cell 24
benchmark_rets = results['benchmark_return'] 

# %% [markdown] cell 25
# ### 製作績效表

# %% [code] cell 26
perf_stats = pf.plotting.show_perf_stats(
        returns,
        benchmark_rets,
        positions=positions,
        transactions=transactions)
