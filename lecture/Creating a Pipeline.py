# -*- coding: utf-8 -*-
# Auto-generated from Creating a Pipeline.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 建立 Pipeline
#
# Pipeline 幫助使用者於每個交易日整理數據，並計算各種交易所需的指標。在編寫交易策略時，會在 `initialize` 函式中使用 `attach_pipeline` 函數將 Pipeline 導入策略當中，協助我們產出交易所需的指標。
#
# ### zipline.pipeline.Pipeline
#
# #### Parameters:
# * columns: _dict_, optional
#         columns 為一個將欄位名稱映射到 factors、 filters 或 classifiers 的字典，讓 pipeline 知道要輸出哪些資料
# * screen: _zipline.pipeline.Filter_, optional
#         用來設定過濾標的條件。
#
# 於此例中，我們首先 ingest 台積電與旺宏股價。

# %% [code] cell 1
import tejapi
import pandas as pd
import numpy as np

import os
os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'your key'

os.environ['ticker'] = '2330 2337'
os.environ['mdate'] = '20170101 20230701'

from zipline.pipeline import Pipeline
from zipline.pipeline.data import TWEquityPricing

# %% [code] cell 2
# !zipline ingest -b tquant

# %% [markdown] cell 3
# 接著宣告一個 `make_pipeline`，並設定 Pipeline 的 columns 參數。
#
# 在這邊，我們設定 `columns` 為 `TWEquityPricing` 中的最新收盤價格。`TWEquityPricing` 為價量資料的資料集

# %% [code] cell 4
def make_pipeline():
    return Pipeline(columns={'close':TWEquityPricing.close.latest})

# %% [code] cell 5
my_pipe = make_pipeline()

# %% [markdown] cell 6
# ## 運行 Pipeline
#
# 接著我們使用 `run_pipeline`，`run_pipeline` 僅用於研究，並不用於編寫交易策略。
#
# 觀察 Pipeline 輸出資料，可以發現 Pipeline 會提供每間公司每日的收盤價。由於我們這邊沒有設定 `screen` 與 `mask`，所以總共就是我們前面 ingest 的兩家公司（2330 與 2327）。
#
# ### zipline.TQresearch.tej_pipeline.run_pipeline
#
# #### Parameters:
# * pipeline: _zipline.pipeline.Pipeline_
#         已經定義的 pipeline。
# * start_date: _str_ or _pd.Timestamp_
#         起始日期。
# * end_date: _str_ or _pd.Timestamp_
#         結束日期。

# %% [code] cell 7
from zipline.TQresearch.tej_pipeline import run_pipeline

# %% [code] cell 8
result = run_pipeline(my_pipe, '2018-01-03', '2022-12-30')

# %% [code] cell 9
result.head()
