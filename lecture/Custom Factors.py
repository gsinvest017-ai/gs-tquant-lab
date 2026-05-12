# -*- coding: utf-8 -*-
# Auto-generated from Custom Factors.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 客製化因子
#
# 上一個章節（[lecture/Factors.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Factors.ipynb)）我們介紹了何謂因子以及如何使用因子，TQuant Lab 已經內建許多不同因子。然而在因子研究不斷勃發之下，許多新型態價量因子持續問世，或許您也有自己的專屬策略因子，因此本章將示範如何客製化因子並運用於 TQuant Lab 中。
#
# 概念上而言，客製化因子與內建因子十分相同。兩者皆以 _inputs_, _window_length_, _mask_ 為輸入參數，並且輸出 _factor_ 物件的類別。
#
# 假使欲計算每檔股票每天的滾動標準差 ([standard deviation](https://zh.wikipedia.org/zh-tw/%E6%A8%99%E6%BA%96%E5%B7%AE))，我們可以使用 `zipline.pipeline.CustomFactor` 子類與 `compute` 方法函式建構。
#
# ### _class_ zipline.pipeline.CustomFactor 
#
# #### Parameters:
# * inputs: _iterable_, optional        
#     
#         輸入資料。
#     
# * outputs: _iterable[str]_, optional
#     
#         輸出的因子。
#
# * window_length: _int_, optional
#     
#         輸入資料的時間窗格。
#   
# * mask: _zipline.pipeline.Filter_, optional
#    
#         決定哪些資產需要計算因子。
#
# #### def compute(self, today, assets, out, *inputs)
#
# - today: 為pandas.Timestamp型態，記錄 Pipeline 啟動當天的日期。
# - assets: 是長度為 N 的numpy array，紀錄 sids（資產）。
# - *inputs: 為 MxN 的 numpy.arrays，M 為 window_length 且 N 為資產數量，可以設立多個inputs。
# - out: 是長度為 N 的numpy arrays。out 將會產出當天的 CustomFactor 計算結果。

# %% [markdown] cell 1
# ## 導入價量資料與必要模組

# %% [code] cell 2
import os
import pandas as pd
import numpy as np 
import tejapi
import warnings
warnings.filterwarnings('ignore')

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'YOUR KEY'

os.environ['mdate'] = '20080401 20230702'
os.environ['ticker'] = '2330 2409'

from zipline.pipeline import Pipeline, CustomFactor
from zipline.TQresearch.tej_pipeline import run_pipeline
from zipline.pipeline.data import TWEquityPricing
from zipline.pipeline.filters import StaticAssets,StaticSids
from zipline.api import sid, symbol

# ingest stock data
# !zipline ingest -b tquant

# %% [markdown] cell 3
# ## 建立計算標準差的因子
#
# 於此例我們使用 `np.nanstd` 計算輸入值的標準差，輸入值與時間區間會依照 `make_pipeline()` 中的 `StdDev` 所給的 __inputs__ 與 __window_length__ 所決定。以此例中，若我們想要計算台積電 (2330) 與友達 (2409) 的 7 日收盤價標準差，可以設定為:
#
# 1. inputs = [TWEquityPricing.close]， TWEquityPricing 內建 bundle 內所有股票的價量資料。
# 2. window_length = 7
#
# 接著使用 `run_pipeline` 呼叫 `Pipeline` ，於回測期間內，逐日計算因子，最終產出 dataframe。可以發現該dataframe有MultiIndex，分別是時間與標的，並且每個指標於每天都會生成 7 日收盤價標準差。
#
# ### zipline.TQresearch.tej_pipeline.run_pipeline
#
# 執行 Pipeline 並生成資料表。
#
# #### Parameters:
# * pipeline: _zipline.pipeline.Pipeline_
#         欲運行的 pipeline 函式。
# * start_date: _pd.Timestamp_
#         pipeline 起始執行的日期。需注意該日期必須於 bundle 時間區間內。
# * end_date: _pd.Timestamp_
#         pipeline 執行結束的日期。需注意該日期必須於 bundle 時間區間內。
#         
# #### Returns
#   _pd.DataFrame_, 輸出 Pipeline 執行結果。

# %% [code] cell 4
class StdDev(CustomFactor):
    def compute(self, today, assets, out, values):
        out[:] = np.nanstd(values, axis=0)
        
def make_pipeline():
    std_dev = StdDev(inputs=[TWEquityPricing.close], window_length=7)
    return Pipeline(
        columns={
            'std_dev':std_dev
        }
    )
result = run_pipeline(make_pipeline(), pd.Timestamp('2013-01-03', tz='UTC'), pd.Timestamp('2023-01-03', tz='UTC'))
result

# %% [markdown] cell 5
# ## 預設輸入參數
#
# 當建立客製化因子時，也可以預先設定輸入之參數，於此例中我們欲建立一個計算開收盤價差 10 日平均的因子，在 `TenDayMeanDifference` 中我們預先宣告 `inputs` 與 `window_length` 為 `[TWEquityPricing.close, TWEquityPricing.open]` 與 `window_length = 10`。

# %% [code] cell 6
class TenDayMeanDifference(CustomFactor):
    inputs = [TWEquityPricing.close, TWEquityPricing.open]
    window_length = 10
    def compute(self, today, assets, out, c_price, o_price):
        out[:] = np.nanmean(c_price - o_price, axis=0)
        
def make_pipeline():
    close_open_diff = TenDayMeanDifference()
    return Pipeline(
        columns={
            'close_open_diff':close_open_diff
        }
    )

result = run_pipeline(make_pipeline(), pd.Timestamp('2013-01-03', tz='UTC'), pd.Timestamp('2023-01-03', tz='UTC'))
result

# %% [markdown] cell 7
# 若在 `make_pipeline` 中賦予 `TenDayMeanDifference` 新的參數則會覆蓋掉預設的參數（`TWEquityPricing.high`、`TWEquityPricing.low`），可以發現下方表格的結果與上方表格不同。

# %% [code] cell 8
def make_pipeline():
    close_open_diff = TenDayMeanDifference(inputs=[TWEquityPricing.high, TWEquityPricing.low])
    return Pipeline(
        columns={
            'close_open_diff':close_open_diff
        }
    )

result = run_pipeline(make_pipeline(), pd.Timestamp('2013-01-03', tz='UTC'), pd.Timestamp('2023-01-03', tz='UTC'))
result

# %% [markdown] cell 9
# ## window length 時間區間
#
# `Pipeline` 會在每個交易日計算出因子的真實數值。
#
# 請注意因子的時間區間必定是從前一個交易日開始計算，以計算前 10 日最低收盤價格為因子，我們可以建立 `TenDaysLowest`。所得出資料表包含每日各股票往前十個日的最低收盤價，以 2023-03-19 為例，在計算因子時就會從 2023-03-18 開始向前推十日。

# %% [code] cell 10
class TenDaysLowest(CustomFactor):
    inputs=[TWEquityPricing.close]
    window_length=10
    def compute(self, today, assets, out, close):
        out[:] = np.nanmin(close, axis=0)
        
def make_pipeline():
    tendl = TenDaysLowest()
    return Pipeline(
        columns={
            'TenDaysLowest':tendl
        }
    )
results = run_pipeline(make_pipeline(), pd.Timestamp('2013-03-18', tz='UTC'), pd.Timestamp('2023-01-03', tz='UTC'))        
results

# %% [markdown] cell 11
# 由上表可以發現 2013-03-19 台積電的 `TenDaysLowest` 為 100.5，而下表可以發現確實從 2013-03-05 到 2013-03-18 之間的最低收盤價為 100.5 而非 2013-03-19 的 100，代表 pipeline 在計算因子時是從前一日開始，避免前視偏誤。

# %% [code] cell 12
from zipline.data.data_portal import DataPortal, get_bundle
df_bundle = get_bundle(bundle_name='tquant',
                       calendar_name='TEJ',
                       start_dt=pd.Timestamp('2013-01-05', tz='UTC'),
                       end_dt=pd.Timestamp('2023-01-03', tz='UTC'))

df_bundle.loc[(df_bundle['symbol']=='2330') & (df_bundle['date'].between('2013-03-04','2013-03-19'))][["date", 'close']]
