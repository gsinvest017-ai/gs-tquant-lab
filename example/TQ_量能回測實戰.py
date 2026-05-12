# -*- coding: utf-8 -*-
# Auto-generated from TQ_量能回測實戰.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 量能回測實戰
#
# ## 交易邏輯
#
# * 成交量增長象徵該檔股票受到投資者青睞，未來預期會有價格大幅波動情形
#
# ## 交易策略
#
# * 當日成交量為前四日簡單移動平均的 2.5 倍時，視為買入訊號，於隔日買入。
# * 當日成交量為前五日簡單移動平均的 0.75 倍時，視為賣出訊號，於隔日賣出。
#
# ## 資料來源
#
# [官網文章:量能回測實戰]:https://www.tejwin.com/?s=%E9%87%8F%E8%83%BD%E5%9B%9E%E6%B8%AC%E5%AF%A6%E6%88%B0
# [官網文章:量能回測實戰]

# %% [markdown] cell 1
# ## 導入資料與套件
#
# 資料導入階段，我們使用 `os.environ` 設置環境變數，分別設定:
#
# 1. TEJAPI_KEY: 為購買 Tquant Lab 隨附的 api key，用於驗證個人身分。
# 2. mdate: 所欲抓取資料的時間範圍，格式為 "西元年份月份日期 西元年份月份日期"。
# 3. ticker: 所欲抓取資料的股價代碼，其中的 _IR0001_ 為大盤指數代碼。
#
# 於本次案例我們抓取台積電、創意、旺宏與台股大盤資料，時間區間設定為 2012-07-02 到 2022-07-02 之間。

# %% [code] cell 2
import pandas as pd 
import numpy as np 
import tejapi
import os 

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'yourkey'

os.environ['mdate'] = '20120702 20220702'
os.environ['ticker'] = 'IR0001 2330 3443 2337'

# 使用 ingest 將股價資料導入暫存，並且命名該股票組合 (bundle) 為 tquant
# !zipline ingest -b tquant 

# %% [markdown] cell 3
# ## 編輯交易策略
#
# ### 導入所需套件

# %% [code] cell 4
from zipline.api import set_slippage, set_commission, set_benchmark, attach_pipeline, order, order_target, symbol, pipeline_output
from zipline.finance import commission, slippage
from zipline.data import bundles
from zipline import run_algorithm
from zipline.pipeline import Pipeline
from zipline.pipeline.filters import StaticAssets
from zipline.pipeline.factors import SimpleMovingAverage
from zipline.pipeline.data import EquityPricing

# %% [markdown] cell 5
# ### 建立 Pipeline 函式
#
# `Pipeline()` 提供使用者同時處理不同標的相關的量化指標與價量資料的功能，於本次案例我們用以處理:
#
# * 各股成交量的四日簡單移動平均
# * 各股成交量的五日簡單移動平均
# * 各股的當日成交量
#
# 此外搭配 `screen` 與 `StaticAssets` 讓我們在每日計算上述指標時，過濾掉大盤資料 (*IR0001*)。讓之後在計算每個股票的成交量的四日簡單移動平均、成交量的五日簡單移動平均與當日成交量時，能跳過計算大盤指數。

# %% [code] cell 6
bundle = bundles.load('tquant')
ir0001_asset = bundle.asset_finder.lookup_symbol('IR0001',as_of_date = None)

def make_pipeline():
    sma_vol_win_4 = SimpleMovingAverage(inputs=[EquityPricing.volume], window_length=4)
    sma_vol_win_5 = SimpleMovingAverage(inputs=[EquityPricing.volume], window_length=5)
    curr_vol = EquityPricing.volume.latest
    
    return Pipeline(
        columns = {
            'sma_4':sma_vol_win_4,
            'sma_5':sma_vol_win_5,
            'curr_vol':curr_vol
        },
        screen = ~StaticAssets([ir0001_asset])
    )

# %% [markdown] cell 7
# ### 建立 initialize 函式
#
# `inintialize` 函式用於定義交易開始前的每日交易環境，與此例中我們設置:
#
# * 流動性滑價
# * 交易手續費
# * 大盤報酬作為基準
# * 將 Pipeline 導入交易流程中

# %% [code] cell 8
def initialize(context):
    set_slippage(slippage.VolumeShareSlippage())
    set_commission(commission.PerShare(cost=0.00285))
    set_benchmark(symbol('IR0001'))
    attach_pipeline(make_pipeline(), 'mystrategy')

# %% [markdown] cell 9
# ### 建立 handle_date 函式
#
# `handle_data` 函式用於處理每天的交易策略或行動，其中:
#
# * condition1: 當日成交量大於四日簡單移動平均之 2.5 倍且現金部位大於 0 ，產生買入訊號。
# * condition2: 當日成交量小於五日簡單移動平均之 0.75 倍，產生賣出訊號。

# %% [code] cell 10
def handle_data(context, data):
    out_dir = pipeline_output('mystrategy')
    for i in out_dir.index: # 遍歷過每檔股票
        sma_vol_4 = out_dir.loc[i, 'sma_4']
        sma_vol_5 = out_dir.loc[i, 'sma_5']
        curr_vol = out_dir.loc[i, 'curr_vol']
        
        condition1 = (curr_vol > 2.5 * sma_vol_4) and (context.portfolio.cash > 0)
        condition2 = (curr_vol < 0.75 * sma_vol_5)
        
        if condition1:
            order(i, 10)
        elif condition2:
            order_target(i, 0)
        else:
            pass

# %% [markdown] cell 11
# ### 建立 analyze 函式
#
# 多半用於繪製績效圖表，於本次案例將使用 pyfolio 繪製，故直接略過。

# %% [code] cell 12
def analyze(context, perf):
    pass

# %% [markdown] cell 13
# ## 執行交易策略
#
# 使用 `run_algorithm` 執行上述所編撰的交易策略，設置交易期間為 2012-07-02 到 2022-07-02，所使用資料集為 *tquant*，初始資金為 10,000 元。其中輸出的 __results__ 就是每日績效與交易的明細表。

# %% [code] cell 14
results = run_algorithm(
    start = pd.Timestamp('2012-07-02', tz='UTC'),
    end = pd.Timestamp('2022-07-02', tz ='UTC'),
    initialize=initialize,
    bundle='tquant',
    analyze=analyze,
    capital_base=1e4,
    handle_data = handle_data
)

results

# %% [markdown] cell 15
# ## 視覺化與績效評估
#
# ### 生成 pyfolio 所需資料表
#
# 之後我們使用 pyfolio 進行績效視覺化與評估，首先使用 `extract_rets_pos_txn_from_zipline` 先將上述的 __results__ 資料表細分成以下部分:
#
# * return: 投組每日報酬
# * positions: 持有部位資料表
# * transactions: 交易明細資料表

# %% [code] cell 16
from pyfolio.utils import extract_rets_pos_txn_from_zipline
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)

# %% [code] cell 17
returns.head()

# %% [code] cell 18
positions.head()

# %% [code] cell 19
transactions.head()

# %% [markdown] cell 20
# ### 製作投資績效表
#
# 使用 `show_perf_stats()` 製作績效表，可以快速計算投資常用績效與風險指標。

# %% [code] cell 21
import pyfolio as pf 
benchmark_rets = results['benchmark_return']
perf_stats = pf.plotting.show_perf_stats(
    returns,
    benchmark_rets,
    positions=positions,
    transactions=transactions)

# %% [markdown] cell 22
# ### 製作且繪製投組成份表格
#
# 使用 `show_and_plot_top_positions()` 與 `get_percent_alloc()` 製作且繪製各股於交易期間的成分佔比。

# %% [code] cell 23
pf.plotting.show_and_plot_top_positions(returns, positions_alloc=pf.pos.get_percent_alloc(positions))

# %% [markdown] cell 24
# ### 繪製基準 (benchmark) 與投組累計報酬率
#
# 使用 `plot_rolling_returns()` 繪製，本案例的基準為大盤報酬率。

# %% [code] cell 25
pf.plotting.plot_rolling_returns(returns, factor_returns=benchmark_rets)

# %% [markdown] cell 26
# ### 繪製六個月的滾動波動度
#
# 使用 `plot_rolling_volatility()` 繪製。

# %% [code] cell 27
pf.plotting.plot_rolling_volatility(returns, factor_returns=benchmark_rets)

# %% [markdown] cell 28
# ### 繪製六個月的滾動夏普值
#
# 使用 `plot_rolling_sharpe()` 繪製。

# %% [code] cell 29
pf.plotting.plot_rolling_sharpe(returns)
