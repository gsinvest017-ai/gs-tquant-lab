# -*- coding: utf-8 -*-
# Auto-generated from QA_因子出現 Bin edges must be unique array nan 問題.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ## 問題集: 
# 使用內建因子時，出現以下 error message: <br>
#
# ValueError: Bin edges must be unique: array([nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan]). You can drop duplicate edges by setting the 'duplicates' kwarg
#
# ## 解決方法:
#
# 將日期設定為交易日之間。

# %% [markdown] cell 1
# # 導入價料資料

# %% [code] cell 2
import os
os.environ["TEJAPI_BASE"] = "https://api.tej.com.tw"
os.environ["TEJAPI_KEY"] = "your key"
os.environ["ticker"] = "2330 2337 1101 2409 1301 1304 1315 1321 1504 2049 1540 1535 1517 2340 2303 3016 4967 3035 6515 3189"
os.environ['mdate'] = "20210104 20230708"
# !zipline ingest -b tquant

# %% [code] cell 3
from zipline.data import bundles
bundle_name = 'tquant'
bundle = bundles.load(bundle_name)

# %% [markdown] cell 4
# # 問題
#
# 計算每家企業每日平均交易金額 (Average Dollar Volume)。因為 TQuant 在 2021/01/04(一) 時會導入 2021/01/03(日) 的資料，然而 1/3 為非交易日故沒有資料，造成 ValueError: Bin edges must be unique: array([nan, nan, nan, nan, nan]).
# You can drop duplicate edges by setting the 'duplicates' kwarg。

# %% [code] cell 5
from zipline.pipeline import Pipeline
from zipline.pipeline.factors import AverageDollarVolume
from zipline.utils.calendar_utils import get_calendar
from zipline.pipeline.data import EquityPricing
from zipline.api import attach_pipeline, pipeline_output
from zipline import run_algorithm
import pandas as pd

def make_pipeline():
    return Pipeline(
        columns = {
            "Deciles" : AverageDollarVolume(window_length = 2).quartiles()
        }
    )
def initialize(context):
    attach_pipeline(make_pipeline(), "my_strate")
    
def handle_data(context, data):
    outs = pipeline_output("my_strate")
    print(outs)
    
def analyze(context, perf):
    pass

results = run_algorithm(
    start = pd.Timestamp("2021-01-04", tz = 'utc'),
    end = pd.Timestamp("2023-01-01", tz = 'utc'),
    initialize = initialize,
    handle_data = handle_data,
    analyze = analyze,
    capital_base = 1e6, 
    bundle = 'tquant',
    data_frequency='daily'
)

# %% [markdown] cell 6
# # 解決
#
# 將 start 改成 2021/01/05 。

# %% [code] cell 7
def make_pipeline():
    return Pipeline(
        columns = {
            "Deciles" : AverageDollarVolume(window_length = 2).quartiles()
        }
    )
def initialize(context):
    attach_pipeline(make_pipeline(), "my_strate")
    
def handle_data(context, data):
    outs = pipeline_output("my_strate")
    print(outs)
    
def analyze(context, perf):
    pass

results = run_algorithm(
    start = pd.Timestamp("2022-01-05", tz = 'utc'),
    end = pd.Timestamp("2023-01-03", tz = 'utc'),
    initialize = initialize,
    handle_data = handle_data,
    analyze = analyze,
    capital_base = 1e6, 
    bundle = 'tquant',
    data_frequency='daily'
)
