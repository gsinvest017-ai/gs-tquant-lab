# -*- coding: utf-8 -*-
# Auto-generated from Pipeline built-in filters.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# <span id="top"></span>
# # <font color=#57a892>Pipeline built-in filters</font>
#
# 本文介紹常用的內建 `Filters`。

# %% [code] cell 1
import os 
import pandas as pd
import numpy as np 

os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
os.environ['TEJAPI_KEY'] = "your key"

os.environ['ticker'] = "1101 1301 1303 1802 2002 2101 2303 2317 2330 2337 2382 2388 2451 2454 2603 2881 2885 2890 2903 3711 IR0001"
os.environ['mdate'] = '20180101 20220330'

# !zipline ingest -b tquant

# %% [code] cell 2
from zipline.data import bundles
from zipline.pipeline import Pipeline
from zipline.TQresearch.tej_pipeline import run_pipeline
from zipline.pipeline.data import TWEquityPricing, TQAltDataSet, TQDataSet
from zipline.pipeline.factors import *
from zipline.pipeline.filters import *

start = pd.Timestamp("2018-02-06", tz='utc')
end = pd.Timestamp("2022-02-06", tz='utc')

bundle = bundles.load('tquant')
sids = bundle.asset_finder.equities_sids
assets = bundle.asset_finder.retrieve_all(sids)

# %% [markdown] cell 3
# <span id="menu"></span>
#     
# ### Menu
# * [All](#All)
# * [Any](#Any)
# * [AtLeastN](#AtLeastN)
# * [AllPresent](#AllPresent)
# * [StaticAssets](#StaticAssets)
# * [StaticSids](#StaticSids)
# * [SingleAsset](#SingleAsset)
# * [top/bottom](#top/bottom)
# * [percentile_between](#percentile_between)
# * [if_else](#if_else)

# %% [markdown] cell 4
# <span id="All"></span>
#
# ## zipline.pipeline.filters.<font color=#57a892>All</font>
#
# 在 n 日內，若一資產每日皆符合條件值，該資產為 True。
#
# >### Parameters:
# >* inputs _( zipline.pipeline.data.Dataset.Boundcolumn_ or _boolean )_ - 資產價量資訊與條件值。
# >* window_length _( int )_ - 決定 n 日。
#
# [Go to Menu](#menu)

# %% [code] cell 5
from zipline.pipeline.filters import All

def make_pipeline():
    return Pipeline(
        columns = {
            "ALL": All(
                inputs = [TWEquityPricing.close.latest > 40], # 設定條件為前一日收盤價 > 40 時為 True
                window_length = 1
            )
        }
    )

run_pipeline(make_pipeline(), start, end)

# %% [markdown] cell 6
# <span id="Any"></span>
#
# ## zipline.pipeline.filters.<font color=#57a892>Any</font>
#
# 在 n 日內，若一資產任一日符合條件值，該資產為 True。
#
# >### Parameters:
# >* inputs _( zipline.pipeline.data.Dataset.Boundcolumn_ or _boolean )_ - 資產價量資訊與條件值。
# >* window_length _( int )_ - 決定 n 日。
#
# [Go to Menu](#menu)

# %% [code] cell 7
from zipline.pipeline.filters import Any

def make_pipeline():
    return Pipeline(
        columns = {
            "Any": Any(
                inputs = [TWEquityPricing.close.latest > 40], 
                window_length = 10
            )
        }
    )

run_pipeline(make_pipeline(), start, end)

# %% [markdown] cell 8
# <span id="AtLeastN"></span>
#
# ## zipline.pipeline.filters.<font color=#57a892>AtLeastN</font>
#
# 在 m 日內，若一資產至少有 n 日符合條件值，該資產為 True。
#
# >### Parameters:
# >* inputs _( zipline.pipeline.data.Dataset.Boundcolumn_ or _boolean )_ - 資產價量資訊與條件值。
# >* window_length _( int )_ - 決定 m 日。
# >* N _( int )_ - 決定 n 日。
#
# [Go to Menu](#menu)

# %% [code] cell 9
from zipline.pipeline.filters import AtLeastN

def make_pipeline():
    return Pipeline(
        columns = {
            "AtLeastN": AtLeastN(
                inputs = [TWEquityPricing.close.latest > 40],
                window_length = 10,
                N = 2
            )
        }
    )

run_pipeline(make_pipeline(), start, end)

# %% [markdown] cell 10
# <span id="AllPresent"></span>
#
# ## zipline.pipeline.filters.<font color=#57a892>AllPresent</font>
#
# 在 n 日內，若每日皆有指定資料，該資產為 True。
#
# >### Parameters:
# >* inputs _( zipline.pipeline.data.Dataset.Boundcolumn_ or _boolean )_ - 資產價量資訊。
# >* window_length _( int )_ - 決定 n 日。
#
# [Go to Menu](#menu)

# %% [code] cell 11
from zipline.pipeline.filters import AllPresent

def make_pipeline():
    return Pipeline(
        columns = {
            "AllPresent": AllPresent(
                inputs = [TWEquityPricing.close], 
                window_length = 10
            )
        }
    )

run_pipeline(make_pipeline(), start, end).loc["2018-05-04"]
# 可注意到 3711 在 2018-04-30 才上市，因此 2018-05-04 為 False

# %% [code] cell 12
# 首先抓出所有 bundle 中的股價
from zipline.data import bundles

bundle = bundles.load('tquant')
sids = bundle.asset_finder.equities_sids
assets = bundle.asset_finder.retrieve_all(sids)
assets

# %% [markdown] cell 13
# <span id="StaticAssets"></span>
#
# ## zipline.pipeline.filters.<font color=#57a892>StaticAssets</font>
#
# 指定特定資產為 True。
#
# >### Parameters:
# >* assets _( zipline.assets.Asset, iterable )_ - 指定資產。
#
# [Go to Menu](#menu)

# %% [code] cell 14
from zipline.pipeline.filters import StaticAssets
from zipline import run_algorithm
from zipline.api import symbol, attach_pipeline, pipeline_output

def make_pipeline():
    return Pipeline(
        columns = {
            "StaticAssets": StaticAssets(
                assets = assets[4:8]
            )
        }
    )

def initialize(context):
    my_pipe = attach_pipeline(make_pipeline(), 'my_pipe')
    
def handle_data(context, data):
    pipe = pipeline_output('my_pipe')
    print("=" * 100)
    print(pipe)

def analyze(context, perf):
    pass

results = run_algorithm(
    start = pd.Timestamp('2019-01-02', tz='utc'),
    end = pd.Timestamp('2019-01-02', tz='utc'),
    initialize = initialize,
    capital_base = 1e6,
    handle_data = handle_data,
    analyze = analyze, 
    bundle = 'tquant'
)

# %% [markdown] cell 15
# <span id="StaticSids"></span>
#
# ## zipline.pipeline.filters.<font color=#57a892>StaticSids</font>
#
# 指定特定資產為 True。
#
# >### Parameters:
# >* sids _( int, iterable )_ - 指定資產的 sid。
#
# [Go to Menu](#menu)

# %% [code] cell 16
from zipline.pipeline.filters import StaticSids
from zipline import run_algorithm
from zipline.api import symbol, attach_pipeline, pipeline_output

def make_pipeline():
    return Pipeline(
        columns = {
            "StaticSids": StaticSids(
                sids = range(4,8)
            )
        }
    )

def initialize(context):
    my_pipe = attach_pipeline(make_pipeline(), 'my_pipe')
    
def handle_data(context, data):
    pipe = pipeline_output('my_pipe')
    print("=" * 100)
    print(pipe)

def analyze(context, perf):
    pass

results = run_algorithm(
    start = pd.Timestamp('2019-01-01', tz='utc'),
    end = pd.Timestamp('2019-01-02', tz='utc'),
    initialize = initialize,
    capital_base = 1e6,
    handle_data = handle_data,
    analyze = analyze, 
    bundle = 'tquant'
)
# %% [markdown] cell 17
# <span id="SingleAsset"></span>
#
# ## zipline.pipeline.filters.<font color=#57a892>SingleAsset</font>
#
# 指定單一特定資產為 True。
#
# >### Parameters:
# >* assets _( zipline.assets.Asset )_ - 指定資產。
#
# [Go to Menu](#menu)

# %% [code] cell 18
from zipline.pipeline.filters import SingleAsset
from zipline import run_algorithm
from zipline.api import symbol, attach_pipeline, pipeline_output

def make_pipeline():
    return Pipeline(
        columns = {
            "SingleAsset": SingleAsset(
                asset = assets[4]
            )
        }
    )

def initialize(context):
    my_pipe = attach_pipeline(make_pipeline(), 'my_pipe')
    
def handle_data(context, data):
    pipe = pipeline_output('my_pipe')
    print("=" * 100)
    print(pipe)

def analyze(context, perf):
    pass

results = run_algorithm(
    start = pd.Timestamp('2019-01-02', tz='utc'),
    end = pd.Timestamp('2019-01-02', tz='utc'),
    initialize = initialize,
    capital_base = 1e6,
    handle_data = handle_data,
    analyze = analyze, 
    bundle = 'tquant'
)

# %% [markdown] cell 19
# <span id="top/bottom"></span>
#
# ## <font color=#57a892>top/bottom</font>
#
# 將最大 / 最小的 N 項標為 True，其餘為 False。
#
# >### Parameters:
# >* N _( int )_ - 數量。
# >* mask _( zipline.pipeline.Filter, optional )_ - 預設為無，若加上 mask，僅排名 mask = True 的項目。
# >* groupby _( zipline.pipeline.Classifier, optional )_ -
# >   * 預設為無。
# >   * 必須為 `Classifier`，若給定 `Classifier` 則是每個分類取最大／最小的 N 項。
#
# [Go to Menu](#menu)

# %% [markdown] cell 20
# ### Examples－top
#
# 在以下範例中： 
# * *sma_quartiles* 將股票依據 SMA 由低至高分成四個級距 (0, 1, 2, 3)
# * *top_beta* 會先篩出平均成交額超過 5 億的股票，再從 4 個 SMA 等級中，各挑 beta 最高的 2 支股票。

# %% [code] cell 21
assets_ex_IR0001 = [i for i in assets if i!= bundle.asset_finder.lookup_symbol('IR0001', as_of_date=None)]

def make_pipeline():

#     quartiles
    sma = SimpleMovingAverage(inputs = [TWEquityPricing.close], window_length = 30)
    sma_quartiles = sma.quartiles(mask = StaticAssets(assets_ex_IR0001))
    
#     top  
    sbeta = SimpleBeta(target = bundle.asset_finder.lookup_symbol('IR0001', as_of_date=None),
                       regression_length = 300,
                       allowed_missing_percentage = 0.25)
    
    adv = AverageDollarVolume(window_length = 10)
    top_dollar = adv > 500000000
    top_beta = sbeta.top(N = 2, mask = top_dollar & StaticAssets(assets_ex_IR0001), groupby = sma_quartiles)
    
    return Pipeline(
        columns={
            'SMA': sma,
            'SMA Quartile': sma_quartiles,
            'Average Dollar Volume':adv,
            'Simple Beta': sbeta,
            'top_beta': top_beta
        }
    )

# %% [markdown] cell 22
# 可以看到在 *top_beta* 欄位中，4 個 SMA 級距各有兩檔股票被標為 True，且平均成交額皆大於 5 億 ( 5e+08 )。

# %% [code] cell 23
result = run_pipeline(make_pipeline(), end, end)
result.loc[:,['Average Dollar Volume', 'SMA Quartile', 'Simple Beta', 'top_beta']]\
            [result.top_beta == True].sort_values(['SMA Quartile', 'Simple Beta'], ascending=[False, False])

# %% [markdown] cell 24
# <span id="percentile_between"></span>
#
# ## <font color=#57a892>percentile_between</font>
#
# 將數值大小介於兩個百分位數（含）之間的資料標為 True，其餘為 False。
#
# >### Parameters:
# >* min_percentile _( float )_ - 下限，介於 [0.0, 100.0]。
# >* max_percentile _( float )_ - 上限，介於 [0.0, 100.0]。
# >* mask _( zipline.pipeline.Filter, optional )_ - 預設為無，若加上 mask，僅排名 mask = True 的項目。
#
# [Go to Menu](#menu)

# %% [markdown] cell 25
# ### Examples－percentile_between
#
# 在以下範例中：
# ```python
# daily_r = DailyReturns()
# top_r = daily_r.percentile_between(min_percentile = 80, max_percentile = 100, mask=StaticAssets(assets_ex_IR0001))
# ```
# 篩選出日報酬率前 20% 的股票。

# %% [code] cell 26
def make_pipeline():

#     percentile_between  
    daily_r = DailyReturns(inputs = [TWEquityPricing.close])
    top_r = daily_r.percentile_between(min_percentile = 80, max_percentile = 100, mask=StaticAssets(assets_ex_IR0001))
    
    return Pipeline(
        columns={
            'Daily Return': daily_r,
            'top_r': top_r
        }
    )

# %% [markdown] cell 27
# 共有 20 x ( 100% - 80% ) = 4 檔股票被標為 True。

# %% [code] cell 28
result = run_pipeline(make_pipeline(), end, end)
result.loc[:,['Daily Return','top_r']].sort_values(by = 'Daily Return', ascending = False).head(10)

# %% [markdown] cell 29
# <span id="if_else"></span>
#
# ## <font color=#57a892>if_else</font>(if_true, if_false)
#
# 在 `if_else` 函數前會先給定一個條件，若符合條件則回傳 *if_true* 的值，不符合條件則回傳 *if_false* 的值。
#
# >### Parameters:
# >* if_true _( zipline.pipeline.term.ComputableTerm )_ - 符合條件回傳的值。
# >* if_false _( zipline.pipeline.term.ComputableTerm )_ - 不符合條件回傳的值。
#
# [Go to Menu](#menu)

# %% [code] cell 30
columns = ['Industry', 'Sub_Industry']

fields = ' '.join(columns)
os.environ['fields'] = fields

# !zipline ingest -b fundamentals

# %% [markdown] cell 31
# ### Examples - if_else
#
# ```python
# ind = TQAltDataSet.Sub_Industry.latest.eq('').if_else(TQAltDataSet.Industry.latest, TQAltDataSet.Sub_Industry.latest)
# ```
# 此範例的條件為子產業別 ( Sub_Industry ) 是否沒有值，若符合條件則回傳主產業別 ( Industry )，否則回傳子產業別 ( Sub_Industry )。

# %% [code] cell 32
def make_pipeline():

    Industry = TQAltDataSet.Industry.latest
    Sub_Industry = TQAltDataSet.Sub_Industry.latest
    check = TQAltDataSet.Sub_Industry.latest.eq('')
    ind = TQAltDataSet.Sub_Industry.latest.eq('').if_else(TQAltDataSet.Industry.latest, TQAltDataSet.Sub_Industry.latest)
    
    return Pipeline(
        columns={
            '主產業別': Industry,
            '子產業別': Sub_Industry,
            '是否符合條件': check,
            '回傳產業': ind
        }
    )

run_pipeline(make_pipeline(), end, end).head(10)
