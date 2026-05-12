# -*- coding: utf-8 -*-
# Auto-generated from TQ_乖離率策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 乖離率策略
#
# ## 交易邏輯
# 乖離率為當期股價與均線的垂直距離。
# * 當距離正越大時，股價出現反轉機會上升，應當賣出。
# * 當距離負越大時，股價出現反轉機會上升，應當買入。
#
# ## 交易策略
# 加入收盤價與過去最高低價格比較做為第二層濾網。
# * 若收盤價低於過去 7 天的最低價，同時出現負乖離時，隔日開盤買入。
# * 若收盤價高於過去 7 天最最高價，同時出現正乖離時，隔日開盤賣出。
#
# ## 參考來源
# [官網文章: 乖離率策略]:https://www.tejwin.com/insight/%E4%B9%96%E9%9B%A2%E7%8E%87%E4%BA%A4%E6%98%93%E7%AD%96%E7%95%A5/
# [官網文章: 乖離率策略]

# %% [markdown] cell 1
# ## 導入資料與套件
#
# 資料導入階段，我們使用 `os.environ` 設置環境變數，分別設定:
#
# 1. TEJAPI_BASE: 設定 tej api 網域名稱。
# 2. TEJAPI_KEY: 為購買 TQuant Lab 隨附的 api key，用於驗證個人身分。
# 3. mdate: 所欲抓取資料的時間範圍，格式為 "西元年份月份日期 西元年份月份日期"。
# 4. ticker: 所欲抓取資料的股價代碼。
#
# 於本次案例我們抓取台積電資料，時間區間設定為 2005-07-02 到 2023-07-02 之間。

# %% [code] cell 2
import os
import pandas as pd
import numpy as np 
import tejapi
import matplotlib.pyplot as plt

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'your key' 
os.environ['mdate'] = '20050702 20230702'
os.environ['ticker'] = '2330'

# !zipline ingest -b tquant

# %% [markdown] cell 3
# ## 編輯交易策略
#
# ### 導入所需套件

# %% [code] cell 4
from zipline.api import (set_slippage, 
                         set_commission, 
                         set_benchmark, 
                         attach_pipeline, 
                         symbol, 
                         pipeline_output,
                         record, 
                         order,
                         order_target
                        )
from zipline.pipeline.filters import StaticSids
from zipline.finance import slippage, commission
from zipline import run_algorithm
from zipline.pipeline import CustomFactor, Pipeline
from zipline.pipeline.data import EquityPricing
from zipline.pipeline.factors import ExponentialWeightedMovingAverage

# %% [markdown] cell 5
# ### 建立 Pipeline 函式
#
# `Pipeline()` 提供使用者快速處理多檔標的的量化指標與價量資料的功能，於本次案例我們用以處理:
#
# * 股價的 7 日指數移動平均
# * 過去 7 日的股價最高價 (自定義 factor 函式: `NdaysMaxHigh`)
# * 過去 7 日的股價最低價 (自定義 factor 函式: `NdaysMinLow`)
# * 當日收盤價

# %% [code] cell 6
def make_pipeline():
    ema = ExponentialWeightedMovingAverage(inputs = [EquityPricing.close],window_length = 7,decay_rate = 1/7)
    high = NdaysMaxHigh(inputs = [EquityPricing.close], window_length = 8) # window_length 設定為 8，因為 factor 會包含當日價格。
    low = NdaysMinLow(inputs = [EquityPricing.close], window_length = 8)
    close = EquityPricing.close.latest
    return Pipeline(
        columns = {
            'ema':ema,
            'highesthigh':high,
            'lowestlow':low,
            'latest':close
        }
    )
class NdaysMaxHigh(CustomFactor):
    def compute(self, today, assets, out, data):
        out[:] = np.nanmax(data[:-2], axis=0)
class NdaysMinLow(CustomFactor):
    def compute(self, today, assets, out, data):
        out[:] = np.nanmin(data[:-2], axis=0)

# %% [markdown] cell 7
# ### 建立 initialize 函式
#
# `inintialize` 函式用於定義交易開始前的每日交易環境，與此例中我們設置:
#
# * 流動性滑價
# * 交易手續費
# * 買入持有台積電的報酬作為基準
# * 將 Pipeline 導入交易流程中

# %% [code] cell 8
def initialize(context):
    set_slippage(slippage.VolumeShareSlippage())
    set_commission(commission.PerShare(cost=0.00285))
    set_benchmark(symbol('2330'))
    attach_pipeline(make_pipeline(), 'mystrategy')

# %% [markdown] cell 9
# ### 建立 handle_date 函式
#
# `handle_data` 函式用於處理每天的交易策略或行動，其中:
#
# * condition1: 當日收盤價大於過去 7 日最高價且產生正乖離時，產生賣出訊號。
# * condition2: 當日收盤價小於過去 7 日最低價且產生負乖離時，產生買入訊號。

# %% [code] cell 10
def handle_data(context, data):
    
    pipe = pipeline_output('mystrategy')
    
    for i in pipe.index:
        ema = pipe.loc[i, 'ema']
        highesthigh = pipe.loc[i, 'highesthigh']
        lowestlow = pipe.loc[i, 'lowestlow']
        close = pipe.loc[i, 'latest']
        bias = close - ema
        residual_position = context.portfolio.positions[i].amount # 當日該資產的股數
        condition1 = (close > highesthigh) and (bias > 0) and (residual_position > 0) # 賣出訊號
        condition2 = (close < lowestlow) and (bias < 0) # 買入訊號
        
        record( # 用以紀錄以下資訊至最終產出的 result 表格中
            con1 = condition1,
            con2 = condition2,
            price = close,
            ema = ema,
            bias = bias,
            highesthigh = highesthigh,
            lowestlow = lowestlow
        )
    
        if condition1:
            order_target(i, 0)
        elif condition2:
            order(i, 10)
        else:
            pass

# %% [markdown] cell 11
# ### 建立 analyze 函式
#
# 多半用於繪製績效圖表，於本案例使用 matplotlib 將視覺化買賣點與投組價值變化。

# %% [code] cell 12
import matplotlib.pyplot as plt
def analyze(context, perf):
    fig = plt.figure()
    ax1 = fig.add_subplot(211)
    perf.portfolio_value.plot(ax=ax1)
    ax1.set_ylabel("Portfolio value (NTD)")
    ax2 = fig.add_subplot(212)
    ax2.set_ylabel("Price (NTD)")
    perf.price.plot(ax=ax2)
    ax2.plot( # 繪製買入訊號
        perf.index[perf.con2],
        perf.loc[perf.con2, 'price'],
        '^',
        markersize=5,
        color='red'
    )
    ax2.plot( # 繪製賣出訊號
        perf.index[perf.con1],
        perf.loc[perf.con1, 'price'],
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
# 使用 `run_algorithm` 執行上述所編撰的交易策略，設置交易期間為 2015-01-05 到 2022-07-02，所使用資料集為 *tquant*，初始資金為 10,000 元。其中輸出的 __results__ 就是每日績效與交易的明細表。

# %% [code] cell 14
results = run_algorithm(start = pd.Timestamp('20150106', tz='UTC'),
                       end = pd.Timestamp('20221125', tz='UTC'),
                       initialize=initialize,
                       bundle='tquant',
                       analyze=analyze,
                       capital_base=1e4,
                       handle_data = handle_data
                      )

# %% [code] cell 15
results # 績效與交易明細

# %% [markdown] cell 16
# # 績效評估與視覺化

# %% [code] cell 17
import pyfolio as pf 
returns, positions, transactions = pf.utils.extract_rets_pos_txn_from_zipline(results)

# %% [markdown] cell 18
# ### 交易策略投組報酬率

# %% [code] cell 19
returns

# %% [markdown] cell 20
# ### 交易策略部位數量

# %% [code] cell 21
positions

# %% [markdown] cell 22
# ### 交易策略交易紀錄

# %% [code] cell 23
transactions

# %% [markdown] cell 24
# ## 視覺化與績效評估
#
# ### 生成 pyfolio 所需資料表
#
# 之後我們使用 pyfolio 進行績效視覺化與評估，首先使用 `extract_rets_pos_txn_from_zipline()` 先將上述的 __results__ 資料表細分成以下部分:
#
# * return: 投組每日報酬
# * positions: 持有部位資料表
# * transactions: 交易明細資料表

# %% [code] cell 25
benchmark_rets = results['benchmark_return'] 
from pyfolio.utils import extract_rets_pos_txn_from_zipline
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)

# %% [code] cell 26
returns.head()

# %% [code] cell 27
positions.head()

# %% [code] cell 28
transactions.head()

# %% [markdown] cell 29
# ### 製作投資績效表
#
# 使用 `show_perf_stats()` 製作績效表，可以快速計算投資常用績效與風險指標。

# %% [code] cell 30
import pyfolio as pf 
perf_stats = pf.plotting.show_perf_stats(
        returns,
        benchmark_rets,
        positions=positions,
        transactions=transactions)

# %% [markdown] cell 31
# ### 繪製基準 (benchmark) 與投組累積報酬率
#
# 使用 `plot_rolling_returns()` 繪製，本案例的基準為台積電買入持有。

# %% [code] cell 32
pf.plotting.plot_rolling_returns(returns, factor_returns=benchmark_rets)
