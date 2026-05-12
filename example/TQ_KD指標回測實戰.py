# -*- coding: utf-8 -*-
# Auto-generated from TQ_KD指標回測實戰.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ## 【量化分析】KD指標回測實戰
# 本文來源[Tej medium](https://medium.com/tej-api-%E9%87%91%E8%9E%8D%E8%B3%87%E6%96%99%E5%88%86%E6%9E%90/%E9%87%8F%E5%8C%96%E5%88%86%E6%9E%90-%E5%8D%81-kd%E6%8C%87%E6%A8%99%E5%9B%9E%E6%B8%AC%E5%AF%A6%E6%88%B0-5e743c10468b)

# %% [markdown] cell 1
# ### 一、前言
#
# KD指標是技術分析常見的指標之一，主要用於判斷股價當前的強弱程度與可能反轉的時機。KD指標的數值介於0-100，一般以50作為分水嶺，當指標大於50時，表示股價處於強勢階段；反之，當股價小於50時，股價屬於弱勢階段。另外，當KD指標小於20時，股票往往有超賣的跡象，隨時有反轉向上的可能；反之當KD指標大於80時，股票往往有超買的跡象，隨時有反轉向下的可能。因此，許多人依此來建構交易訊號，作為買賣股票的依據。
#
# KD指標的計算流程:
#
# - RSV = ((當日收盤價-近N日的最低價)/(近N日的最高價-近N日的最低價))*100
# - K值 = 昨日K值 × (2/3) + 當日RSV × (1/3)
# - D值 = 昨日D值 × (2/3) + 當日K值 × (1/3)
#
# 從算式來看，可以把RSV解讀成當日股價相較於近N日 (本文N = 9)股價，是屬於較強勢還是弱勢。K值，又被稱為快線，因為受到當日股價強弱的影響較大；而D值計算的原理如同再進行一次平滑，故對當前股價變化反應較慢。
#
# 本文採用KD指標來判斷股價反轉時機，利用以下進出場規則建立交易策略並進行回測:
# - K ≤ 20，買入，因其代表股價處於較弱、市場過冷
# - K ≥ 80，賣出，代表市場過熱，因此選擇獲利了結

# %% [markdown] cell 2
# ### 二、 環境設定 & import package
# 2.1 輸入tejapi key

# %% [code] cell 3
import os

tej_key = 'your key'
api_base = 'https://api.tej.com.tw'

os.environ['TEJAPI_KEY'] = tej_key 
os.environ['TEJAPI_BASE'] = api_base

# %% [markdown] cell 4
# 2.2 import package

# %% [code] cell 5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# import zipline
from zipline.data import bundles
from zipline.sources.TEJ_Api_Data import get_universe

from zipline.pipeline import Pipeline
from zipline.pipeline.data import TWEquityPricing
from zipline.TQresearch.tej_pipeline import run_pipeline   

from zipline.api import *
from zipline.finance.commission import PerDollar
from zipline.finance.slippage import VolumeShareSlippage

from zipline.sources.TEJ_Api_Data import (get_Treasury_Return,
                                            get_Benchmark_Return)

import pyfolio as pf

plt.rcParams['axes.unicode_minus'] = False

# %% [markdown] cell 6
# ### 三、樣本&期間
# 3.1 設定股票池與期間
#
# - 股票池：抓取台灣50指數的股票(總計81筆)與加權股價報酬指數(IR0001)
# - 期間：從2012-2022年
# - 綁入名稱為tquant的資料庫
# - 指定交易日為台股交易日誌:TEJ_XTAI
#
# 利用tejapi將開高低收量、調整股價資料綁入zipline

# %% [code] cell 7
# set backtest period
start = '2012-01-01'
end = '2022-12-30'

# 抓取台灣50指數的股票
StockList = get_universe(start, end, idx_id='IX0002')
StockList.append('IR0001')

os.environ['ticker'] = ' '.join(StockList)
os.environ['mdate'] = start+' '+end

# calendar------------------------------------------
calendar_name = 'TEJ_XTAI'  
# bundle_name---------------------------------------
bundle_name = 'tquant'

# !zipline ingest -b tquant

# %% [markdown] cell 8
# ### 四、建構交易策略

# %% [markdown] cell 9
# #### 4.1 交易策略參數設定
#
# **交易成本設定：**
# - 初始資金為1,000,000元
# - 設定單次買賣股票金額的0.29%為佣金費用
# - 設定0%為滑價成本

# %% [code] cell 10
"""
Model Settings
"""
starting_portfolio = 1e6
'''
cost params setting
'''
commission_pct = 0.0029
slippage_volume_limit = 1.0
slippage_impact = 0

# %% [markdown] cell 11
# #### 4.2 建立Pipeline函式
#
# 取得 TQuant Lab 的內建因子 *FastStochasticOscillator* ，即為交易策略所需的 K 值
#
# ##### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算所需價量資料，預設 = EquityPricing.close, EquityPricing.low, EquityPricing.high。
# * window_lengthL: _int_
#         以 n 天為週期，預設 = 14。

# %% [code] cell 12
from zipline.pipeline.factors import FastStochasticOscillator

def make_pipeline():
    
    return Pipeline(
        columns = {
            "FastStochasticOscillator": FastStochasticOscillator(
                inputs = [TWEquityPricing.close, TWEquityPricing.low, TWEquityPricing.high],
                window_length = 10
            )
        }
    )

start_date = pd.Timestamp('2022-01-01',tz='utc')
end_date = pd.Timestamp('2022-12-26',tz='utc')
result = run_pipeline(make_pipeline(), start_date, end_date)

result

# %% [markdown] cell 13
# #### 4.3 建立 initialize 函式
#
# `inintialize` 函式用於定義交易開始前的每日交易環境，與此例中我們設置:
#
# * 交易手續費
# * 流動性滑價
# * 買入持有加權股價報酬指數(IR0001)的報酬作為基準
# * 將 Pipeline 導入交易流程中

# %% [code] cell 14
bundle = bundles.load('tquant')

def initialize(context):
    set_commission(PerDollar(cost=commission_pct))
    set_slippage(VolumeShareSlippage(volume_limit=slippage_volume_limit, price_impact=slippage_impact)) 
    # setting benchmark    
    set_benchmark(symbol('IR0001'))  
    attach_pipeline(make_pipeline(), 'mystrategy')

# %% [markdown] cell 15
# #### 4.4 建立 handle_date 函式
#
# `handle_data` 函式用於處理每天的交易策略或行動。
#
# 本範例運用KD指標來建構交易策略，在指標顯示超賣時買進，在指標顯示超買時賣出。
#
# **交易策略的進出場規則：**
#
# - Long Entry:
#     - K ≤ 20，買入股票池中條件成立股票，配置帳戶資金1%。
#
# - Short Entry:
#     - K ≥ 80，賣出條件成立股票。

# %% [code] cell 16
def handle_data(context, data):
    out_dir = pipeline_output('mystrategy')  # 取得每天 pipeline 的 K 值
    for i in out_dir.index:
        short_kd = out_dir.loc[i, 'FastStochasticOscillator']
        position = context.portfolio.positions[i].amount
        if (position == 0 and short_kd <= 20) :
            order_target_percent(i, 0.01)
                
        elif (position > 0 and short_kd >= 80) :
            order_target_percent(i, 0.0)

# %% [markdown] cell 17
# #### 4.5 執行交易策略
#
# 使用 `run_algorithm` 執行上述所編撰的交易策略，設置交易期間為 2022-01-01 到 2022-12-26，所使用資料集為 *tquant*，初始資金為 1,000,000 元 (於4.1設定初始資金)。其中輸出的 __results__ 就是每日績效與交易的明細表。

# %% [code] cell 18
from zipline import run_algorithm

start_date = pd.Timestamp('2022-01-01',tz='utc')
end_date = pd.Timestamp('2022-12-26',tz='utc')

results = run_algorithm(start= start_date,  
                        end=end_date,
                        initialize=initialize,                      
                        capital_base=starting_portfolio,                      
                        handle_data=handle_data,
                        data_frequency='daily',
                        bundle='tquant'
                        )
results

# %% [markdown] cell 19
# 利用cumsum().plot()畫出累計報酬率的圖

# %% [code] cell 20
results.returns.cumsum().plot()

# %% [markdown] cell 21
# ### 五、策略績效分析
# 5.1 利用pyfolio分析評估策略的風險與報酬表現

# %% [code] cell 22
import pyfolio as pf
import empyrical

bt_returns, bt_positions, bt_transactions = pf.utils.extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return

# Creating a Full Tear Sheet
pf.create_full_tear_sheet(bt_returns, positions=bt_positions, transactions=bt_transactions,
                        benchmark_rets=benchmark_rets,
                        #live_start_date='2022-01-01', 
                        round_trips=False)
