# -*- coding: utf-8 -*-
# Auto-generated from Pipeline built-in factors.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # Pipeline built-in factors
#
# 本文將介紹 zipline 內建的因子。

# %% [code] cell 1
import pandas as pd 
import numpy as np 
import os 

os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"

os.environ['mdate'] = '20150101 20230702'
os.environ['ticker'] = "2330 IR0001"
# !zipline ingest -b tquant

# %% [markdown] cell 2
# <span id="menu"></span>
# ## 選單
# * [AverageDollarVolume](#AverageDollarVolume)
# * [BollingerBands](#BollingerBands)
# * [DailyReturns](#DailyReturns)
# * [SimpleMovingAverage](#SimpleMovingAverage)
# * [LinearWeightedMovingAverage](#LinearWeightedMovingAverage)
# * [ExponentialWeightedMovingAverage](#ExponentialWeightedMovingAverage)
# * [ExponentialWeightedMovingStdDev](#ExponentialWeightedMovingStdDev)
# * [Latest](#Latest)
# * [MaxDrawdown](#MaxDrawdown) 
# * [Returns](#Returns)
# * [RollingPearson](#RollingPearson)
# * [RollingLinearRegressionOfReturns](#RollingLinearRegressionOfReturns)
# * [RollingSpearmanOfReturns](#RollingSpearmanOfReturns)
# * [SimpleBeta](#SimpleBeta)
# * [RSI](#RSI)
# * [VWAP](#VWAP)
# * [WeightedAverageValue](#WeightedAverageValue)
# * [PercentChange](#PercentChange)
# * [PeerCount](#PeerCount)
# * [RateOfChangePercentage](#RateOfChangePercentage)
# * [Aroon](#Aroon)
# * [FastStochasticOscillator](#FastStochasticOscillator)
# * [TrueRange](#TrueRange)
# * [IchimokuKinkoHyo](#IchimokuKinkoHyo)

# %% [code] cell 3
from zipline.TQresearch.tej_pipeline import run_pipeline   
from zipline.pipeline import Pipeline
from zipline.pipeline.data import TWEquityPricing

start_time = pd.Timestamp("2018-02-02", tz="UTC")
end_time = pd.Timestamp("2022-07-02", tz="UTC")

# %% [markdown] cell 4
# <span id="AverageDollarVolume"></span>
# ### zipline.pipeline.factors.AverageDollarVolume
#
# 計算當日以前 n 天的資產平均價值，$ 每日平均價值 = 成交量 \times 價格$。  
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_, optional
#         所欲計算之價格資料，預設 = EquityPricing.close。
# * window_length: _int_
#         決定 n 天。
#         
# [回到選單](#menu)

# %% [code] cell 5
from zipline.pipeline.factors import AverageDollarVolume
def make_pipeline():
    return Pipeline(
        columns = {
            "avg_dollar_volume": AverageDollarVolume(
                inputs = [TWEquityPricing.close, TWEquityPricing.volume],
                window_length = 10
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 6
# <span id="BollingerBands"></span>
# ### zipline.pipeline.factors.BollingerBands
#
# 布林通道利用統計學概念，創造上、中、下三軌，中軌為 n 日的移動平均線，上下兩軌分別為中軌 $\pm m$ 個標準差。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_, optional
#         所欲計算之價格資料，預設 = EquityPricing.close。
# * window_length: _int_
#         決定 n 天。
# * k: _int_
#         決定 m 個標準差。
#         
# #### Note:
# 不推薦以下使用方式。這種方式會產出帶有 tuple 的 DataFrame，在某些 pandas 版本（例如：1.5.3）下會出現`ValueError: no types given`的錯誤。
#
# ```python
# def make_pipeline():
#     return Pipeline(
#         columns = {
#             "bbands": BollingerBands(
#                 inputs = [TWEquityPricing.close], 
#                 window_length = 14,
#                 k=1.5
#             )
#         }
#     )
# ```
#
# [回到選單](#menu)

# %% [code] cell 7
from zipline.pipeline.factors import BollingerBands
def make_pipeline():
    upper = BollingerBands(inputs = [TWEquityPricing.close], window_length = 14, k = 1.5).upper
    middle = BollingerBands(inputs = [TWEquityPricing.close], window_length = 14, k = 1.5).middle
    lower = BollingerBands(inputs = [TWEquityPricing.close], window_length = 14, k = 1.5).lower
    return Pipeline(
        columns = {
            "upper_bound":upper,
            "middle":middle,
            "lower_bound":lower
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 8
# <span id="DailyReturns"></span>
#     
# ### zipline.pipeline.factors.DailyReturns
#
# 計算日報酬率。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_, optional
#         所欲計算之價格資料，預設 = EquityPricing.close。
#         
# [回到選單](#menu)

# %% [code] cell 9
from zipline.pipeline.factors import DailyReturns
def make_pipeline():
    return Pipeline(
        columns = {
            "Daily Return": DailyReturns(
                inputs = [TWEquityPricing.close]
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 10
# <span id="SimpleMovingAverage"></span>
#
# ### zipline.pipeline.factors.SimpleMovingAverage
#
# 計算 n 日的簡單移動平均。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         所欲計算之資料。
# * window_length: _int_
#         決定 n 日。
#         
# [回到選單](#menu
# )

# %% [code] cell 11
from zipline.pipeline.factors import SimpleMovingAverage
def make_pipeline():
    return Pipeline(
        columns = {
            "SMA": SimpleMovingAverage(
                inputs = [TWEquityPricing.close], 
                window_length = 10
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 12
# <span id="LinearWeightedMovingAverage"></span>
# ### zipline.pipeline.factors.LinearWeightedMovingAverage
#
# 計算 n 日的線性加權移動平均，計算方法: 
#
# $$
# \frac{\sum_{i=1}^{n} i \times x_{i}}{\sum_{i=1}^{n} i}
# $$
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         所欲計算之資料。
# * window_length: _int_
#         決定 n 日。
#
# [回到選單](#menu)

# %% [code] cell 13
from zipline.pipeline.factors import LinearWeightedMovingAverage
def make_pipeline():
    return Pipeline(
        columns = {
            "LWMA": LinearWeightedMovingAverage(
                inputs = [TWEquityPricing.close], 
                window_length = 10
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 14
# <span id="ExponentialWeightedMovingAverage"></span>
# ### zipline.pipeline.factors.ExponentialWeightedMovingAverage
#
# 計算 n 日的指數加權移動平均，計算方法: 
#
# $$
# \frac{\sum_{i=1}^{n} {decay}^i \times x_{i}}{\sum_{i=1}^{n} {decay}^i}
# $$
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         所欲計算之資料。
# * window_length: _int_
#         決定 n 日。
# * decay_rate: _float_
#         指數衰退率。
#
# [回到選單](#menu)

# %% [code] cell 15
from zipline.pipeline.factors import ExponentialWeightedMovingAverage
def make_pipeline():
    return Pipeline(
        columns = {
            "EWMA": ExponentialWeightedMovingAverage(
                inputs = [TWEquityPricing.close],
                window_length = 10,
                decay_rate = 0.1
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 16
# <span id="ExponentialWeightedMovingStdDev"></span>
# ### zipline.pipeline.factors.ExponentialWeightedMovingStdDev
#
# 計算 n 日的指數加權移動標準差。
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         所欲計算之資料。
# * window_length: _int_
#         決定 n 日。
# * decay_rate: _float_
#         指數衰退率。
#
# [回到選單](#menu)

# %% [code] cell 17
from zipline.pipeline.factors import ExponentialWeightedMovingStdDev
def make_pipeline():
    return Pipeline(
        columns = {
            "EWMSTD": ExponentialWeightedMovingStdDev(
                inputs = [TWEquityPricing.close],
                window_length = 10,
                decay_rate = 0.1
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 18
# <span id="Latest"></span>
#
# ### zipline.pipeline.factors.Latest
#
# 輸出最近一期資料。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         所欲計算之資料。
#
# [回到選單](#menu)

# %% [code] cell 19
from zipline.pipeline.factors import Latest
def make_pipeline():
    return Pipeline(
        columns = {
            "Latest": Latest(
                inputs = [TWEquityPricing.close]
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 20
# <span id="MaxDrawdown"></span>
#
# ### zipline.pipeline.factors.MaxDrawdown
#
# 以 n 天為周期計算最大回撤。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算最大回徹所需要的價格資訊。
# * window_lengthL: _int_
#         以 n 天為週期計算。
#
#
# [回到選單](#menu)

# %% [code] cell 21
from zipline.pipeline.factors import MaxDrawdown
def make_pipeline():
    return Pipeline(
        columns = {
            "MaxDrawdown": MaxDrawdown(
                inputs = [TWEquityPricing.close],
                window_length = 1
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 22
# <span id="Returns"></span>
#
# ### zipline.pipeline.factors.Returns
#
# 以 n 天為窗格，計算報酬率。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算報酬率所需要的價格資訊，預設 = EquityPricing.close。
# * window_lengthL: _int_
#         以 n 天為週期。
#
#
# [回到選單](#menu)

# %% [code] cell 23
from zipline.pipeline.factors import Returns
def make_pipeline():
    return Pipeline(
        columns = {
            "Returns": Returns(
                inputs = [TWEquityPricing.close],
                window_length = 2
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 24
# <span id="RollingPearson"></span>
#
# ### zipline.pipeline.factors.RollingPearson
#
# 計算因子或變數之間的滾動皮爾森相關係數。
#
# #### Parameters:
# * base_factor: _zipline.pipeline.Factor_
#         計算相關係數的因子。
# * target: _zipline.pipeline.Term or _numerical term_
#         與 base_factor 計算彼此間的相關係數。
# * correlation_length : _int_
#         向前 n 天為窗格計算相關係數，若僅計算前一日設定為 2。
# * mask: _zipline.pipeline.Filter_
#         遮蔽特定證券所需的濾網，遮蔽者將不會計算相關係數。
#
#
# [回到選單](#menu)

# %% [code] cell 25
from zipline.pipeline.factors import RollingPearson
from zipline.pipeline.factors import DailyReturns
from zipline.pipeline.factors import Returns
def make_pipeline():
    base_factor = DailyReturns(inputs = [TWEquityPricing.close])
    target = Returns(inputs = [TWEquityPricing.close], window_length = 6)
    return Pipeline(
        columns = {
            "RollingPearson": RollingPearson(
                base_factor = base_factor,
                target = target,
                correlation_length = 10
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 26
# <span id="RollingLinearRegressionOfReturns"></span>
#
# ### zipline.pipeline.factors.RollingLinearRegressionOfReturns
#
# 以一個特定資產為自變數，其餘資產為應變數，進行 OLS 迴歸。會輸出迴歸式的 beta, alpha, r_value, p_value 與 standard error。迴歸式如下: 
#
# $$
# Return_{i,t} = \beta_{i} \times {Certain Return}_{i,t} + \alpha_{i}
# $$
#
# #### Parameters:
# * target: _zipline.assets.Asset_
#         歸類於自變數的資產。
# * returns_length : _int_
#         向前 n 天為窗格計算報酬，若為日報酬率，設定為 2。
# * regression_length: _int_
#         計算各項迴歸式的向前窗格天數。
# * mask: _zipline.pipeline.Filter_
#         遮蔽特定證券所需的濾網，遮蔽者將不會計算相關係數。
#
# [回到選單](#menu)

# %% [code] cell 27
from zipline.pipeline.factors import RollingLinearRegressionOfReturns
from zipline.pipeline.filters import StaticAssets
from zipline import run_algorithm
from zipline.api import symbol, attach_pipeline, pipeline_output

def make_pipeline():
    regressor = RollingLinearRegressionOfReturns(
                target = symbol("IR0001"),
                returns_length = 2,
                regression_length = 14,
            )
    return Pipeline(
        columns = {
            "beta": regressor.beta,
            "alpha": regressor.alpha,
            "r_value": regressor.r_value,
            "p_value": regressor.p_value,
            "stderr": regressor.stderr
        }, screen = ~StaticAssets([symbol("IR0001")])
    )

def initialize(context):
    my_pipe = attach_pipeline(make_pipeline(), 'my_pipe')
    
def handle_data(context, data):
    pipe = pipeline_output('my_pipe')
    print("=" * 100)
    print(f"Beta: {pipe.beta}")
    print(f"alpha: {pipe.alpha}")
    print(f"r_value: {pipe.r_value}")
    print(f"p_value: {pipe.p_value}")
    print(f"stderr: {pipe.stderr}")

def analyze(context, perf):
    pass

results = run_algorithm(
    start = start_time,
    end = end_time,
    initialize = initialize,
    capital_base = 1e6,
    handle_data = handle_data,
    analyze = analyze, 
    bundle = 'tquant'
)
# %% [markdown] cell 28
# <span id="RollingSpearmanOfReturns"></span>
#
# ### zipline.pipeline.factors.RollingSpearmanOfReturns
#
# 給定一個特定資產，計算其他資產報酬與特定資產報酬的斯匹爾曼等級相關係數。
#
# #### Parameters:
# * target: _zipline.assets.Asset_
#         特定資產。
# * returns_length : _int_
#         向前 n 天為窗格計算報酬，若為日報酬率，設定為 2。
# * correlation_length : _int_
#         計算相關係數的窗格數。
# * mask: _zipline.pipeline.Filter_
#         遮蔽特定證券所需的濾網，遮蔽者將不會計算相關係數。
#
# [回到選單](#menu)

# %% [code] cell 29
from zipline.pipeline.factors import RollingSpearmanOfReturns
from zipline.pipeline.filters import StaticAssets
from zipline import run_algorithm
from zipline.api import symbol, attach_pipeline, pipeline_output

def make_pipeline():
    regressor = RollingSpearmanOfReturns(
                target = symbol("IR0001"),
                returns_length = 2,
                correlation_length = 14,
            )
    return Pipeline(
        columns = {
            "RollingSpearmanOfReturns": regressor
        }, screen = ~StaticAssets([symbol("IR0001")])
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
    start = start_time,
    end = end_time,
    initialize = initialize,
    capital_base = 1e6,
    handle_data = handle_data,
    analyze = analyze, 
    bundle = 'tquant'
)
# %% [markdown] cell 30
# <span id="SimpleBeta"></span>
#
# ### zipline.pipeline.factors.SimpleBeta
#
# 給定一個特定資產，以該特定資產為自變數，其他資產為應變數，進行迴歸計算 beta 值，與 RollingLinearRegressionOfReturns 的 beta 等價。
#
# #### Parameters:
# * target: _zipline.assets.Asset_
#         特定資產。
# * regression_length  : _int_
#         計算 beta 的窗格數。
#
# [回到選單](#menu)

# %% [code] cell 31
from zipline.pipeline.factors import SimpleBeta
from zipline.pipeline.filters import StaticAssets
from zipline import run_algorithm
from zipline.api import symbol, attach_pipeline, pipeline_output

def make_pipeline():
    Beta = SimpleBeta(
                target = symbol("IR0001"),
                regression_length = 30
            )
    return Pipeline(
        columns = {
            "SimpleBeta": Beta
        }, screen = ~StaticAssets([symbol("IR0001")])
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
    start = start_time,
    end = end_time,
    initialize = initialize,
    capital_base = 1e6,
    handle_data = handle_data,
    analyze = analyze, 
    bundle = 'tquant'
)
# %% [markdown] cell 32
# <span id="RSI"></span>
#
# ### zipline.pipeline.factors.RSI
#
# 以 n 天為窗格，計算 RSI。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算報酬率所需要的價格資訊，預設 = EquityPricing.close。
# * window_lengthL: _int_
#         以 n 天為週期，預設為 15 日。
#
#
# [回到選單](#menu)

# %% [code] cell 33
from zipline.pipeline.factors import RSI
def make_pipeline():
    return Pipeline(
        columns = {
            "RSI": RSI(
                inputs = [TWEquityPricing.close],
                window_length = 87
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 34
# <span id="VWAP"></span>
#
# ### zipline.pipeline.factors.VWAP
#
# 以 n 天為窗格，計算 Volume Weighted Average Price (以成交量加權價格)。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算報酬率所需要的價格與成交量資訊，預設 = EquityPricing.close,EquityPricing.volume。
# * window_lengthL: _int_
#         以 n 天為週期。
#
#
# [回到選單](#menu)

# %% [code] cell 35
from zipline.pipeline.factors import VWAP
def make_pipeline():
    return Pipeline(
        columns = {
            "VWAP": VWAP(
                inputs = [TWEquityPricing.close, TWEquityPricing.volume],
                window_length = 87
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 36
# <span id="WeightedAverageValue"></span>
#
# ### zipline.pipeline.factors.WeightedAverageValue
#
# 以 n 天為窗格，與 VWAP 相似，計算以成交量加權的某數值平均。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算報酬率所需要的資訊，預設 = EquityPricing.close,EquityPricing.volume。
# * window_lengthL: _int_
#         以 n 天為週期。
#
#
# [回到選單](#menu)

# %% [code] cell 37
from zipline.pipeline.factors import WeightedAverageValue
def make_pipeline():
    return Pipeline(
        columns = {
            "WeightedAverageValue": WeightedAverageValue(
                inputs = [TWEquityPricing.high, TWEquityPricing.volume],
                window_length = 10
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 38
# <span id="PercentChange"></span>
#
# ### zipline.pipeline.factors.PercentChange
#
# 以 n 天為窗格，計算 x 變數百分比變化。計算公式:
#
# $$
# \frac{new - old}{|old|}
# $$
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         x 變數資訊。
# * window_lengthL: _int_
#         以 n 天為週期，需大於等於 2。
#
#
# [回到選單](#menu)

# %% [code] cell 39
from zipline.pipeline.factors import PercentChange
def make_pipeline():
    return Pipeline(
        columns = {
            "PercentChange": PercentChange(
                inputs = [TWEquityPricing.close],
                window_length = 2
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 40
# <span id="PeerCount"></span>
#
# ### zipline.pipeline.factors.PeerCount
#
# 以 factor/classifier 為判斷基準，呈現同類的公司數量。這裡以報酬率的四分位數為基準。
#
# #### Parameters:
# * inputs: _zipline.pipeline.factors.factor_
#         判斷基準
# * window_lengthL: _int_
#         以 n 天為週期。
#
#
# [回到選單](#menu)

# %% [code] cell 41
from zipline.pipeline.factors import PeerCount, Returns
def make_pipeline():

    Ret = Returns(inputs = [TWEquityPricing.close], window_length = 2)
    quarter = Ret.quartiles()
    
    return Pipeline(
        columns = {
            "PeerCount": PeerCount(
                inputs = [quarter]
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 42
# <span id="RateOfChangePercentage"></span>
#
# ### zipline.pipeline.factors.RateOfChangePercentage
#
# 計算因子在指定時間長度的 %變化量，公式：(尾 - 頭) / 頭 * 100
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算所需價量資料。
# * window_lengthL: _int_
#         以 n 天為週期。
#
#
# [回到選單](#menu)

# %% [code] cell 43
from zipline.pipeline.factors import RateOfChangePercentage
def make_pipeline():
    
    return Pipeline(
        columns = {
            "RateOfChangePercentage": RateOfChangePercentage(
                inputs = [TWEquityPricing.close],
                window_length = 10
            )
        }
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 44
# <span id="Aroon"></span>
#
# ### zipline.pipeline.factors.Aroon
#
# 阿隆指標，計算從指定期間 (window_length) 股價最高/低點到現在的時間，回傳一組 (down, up)，數值介於 0 - 100。
#
# 計算方式：<br>
# up = 取期間 EquityPricing.high 最高那日index，除以 (window_length - 1)，再乘上100 <br>
# down = 取期間 EquityPricing.low 最低那日index，除以 (window_length - 1)，再乘上100 <br>
# 100 = 期間最後一日達到最高/低，0 = 期間第一日達到最高/低<br>
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算所需價量資料，預設 = EquityPricing.low, EquityPricing.high。
# * window_lengthL: _int_
#         以 n 天為週期。
#         
#
# #### Note:
# 不推薦以下使用方式。這種方式會產出帶有 tuple 格式的 DataFrame，在某些 pandas 版本（例如：1.5.3）下會出現`ValueError: no types given`的錯誤。
#
# ```python
# def make_pipeline():
#     
#     return Pipeline(
#         columns = {
#             "Aroon": Aroon(
#                 inputs = [TWEquityPricing.high, TWEquityPricing.low],
#                 window_length = 10,
#                 mask = StaticSids([0])
#             )
#         }, screen=StaticSids([0])
#     )
# ```
#
#
# [回到選單](#menu)

# %% [code] cell 45
from zipline.pipeline.factors import Aroon
from zipline.pipeline.filters import StaticSids
def make_pipeline():
    
    aroon = Aroon(inputs = [TWEquityPricing.high, TWEquityPricing.low],
                  window_length = 10,
                  mask = StaticSids([0]))
    
    return Pipeline(
        columns = {
            "up": aroon.up,
            "down": aroon.down,
        }, screen=StaticSids([0])
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 46
# <span id="FastStochasticOscillator"></span>
#
# ### zipline.pipeline.factors.FastStochasticOscillator
#
# 快速隨機指標 (K值)，0-100，通常超過 80 有超買跡象，低於 20 有超賣跡象；D 值通常為 K 值三日 SMA。
#
# 計算方式：
# (最後收盤價 - 期間最低) / (期間最高 - 期間最低) * 100
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算所需價量資料，預設 = EquityPricing.close, EquityPricing.low, EquityPricing.high。
# * window_lengthL: _int_
#         以 n 天為週期，預設 = 14。
#
# [回到選單](#menu)

# %% [code] cell 47
from zipline.pipeline.factors import FastStochasticOscillator
def make_pipeline():
    
    return Pipeline(
        columns = {
            "FastStochasticOscillator": FastStochasticOscillator(
                inputs = [TWEquityPricing.close, TWEquityPricing.low, TWEquityPricing.high],
                window_length = 10,
                mask = StaticSids([0])
            )
        }, screen=StaticSids([0])
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 48
# <span id="TrueRange"></span>
#
# ### zipline.pipeline.factors.TrueRange
#
# 真實波動幅度，從
#     
#     今天最高 - 今天最低
#     |今天最高 - 昨天收盤| 
#     |今天最低 - 昨天收盤| 
#     
# 中挑出最大值，數值越大代表波動性越大。
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算所需價量資料，預設 = EquityPricing.high, EquityPricing.low, EquityPricing.close。
# * window_length: _int_
#         以 n 天為週期，預設 = 2，且"目前也僅支援 window_length = 2"。
#
# [回到選單](#menu)

# %% [code] cell 49
from zipline.pipeline.factors import TrueRange
def make_pipeline():
    
    return Pipeline(
        columns = {
            "TrueRange": TrueRange(
                inputs = [TWEquityPricing.high, TWEquityPricing.low, TWEquityPricing.close],
                window_length = 2,
                mask = StaticSids([0])
            )
        }, screen=StaticSids([0])
    )
run_pipeline(make_pipeline(), start_time, end_time)

# %% [markdown] cell 50
# <span id="IchimokuKinkoHyo"></span>
#
# ### zipline.pipeline.factors.IchimokuKinkoHyo
#
# 輸出順序為 "tenkan_sen" 轉換線， "kijun_sen" 基準線， "senkou_span_a" 先行帶A， "senkou_span_b" 先行帶B， "chikou_span" 遲行帶<br>
#
# "tenkan_sen" 轉換線：(9日最高 ＋ 9日最低) / 2<br>
# "kijun_sen" 基準線：(26日最高 ＋ 26日最低) / 2<br>
# "senkou_span_a" 先行帶A：前兩項平均<br>
# "senkou_span_b" 先行帶B：(52日最高 ＋ 52日最低) / 2<br>
#  "chikou_span" 遲行帶：26天前收盤價<br>
#
# #### Parameters:
# * inputs: _zipline.pipeline.data.Dataset.BoundColumn_
#         計算所需價量資料，預設 = EquityPricing.high, EquityPricing.low, EquityPricing.close。
# * window_lengthL: _int_
#         以 n 天為週期，預設 = 52。
# * tenkan_sen_length: _int_
#         決定轉換線日數。
# * kijun_sen_length: _int_
#         決定基準線日數。
# * chikou_span_length: _int_
#         決定遲行帶日數。
#
# #### Note:
# 不推薦以下使用方式。這種方式會產出帶有 tuple 格式的 DataFrame，在某些 pandas 版本（例如：1.5.3）下會出現`ValueError: no types given`的錯誤。
#
# ```python
# def make_pipeline():
#     
#     return Pipeline(
#         columns = {
#             "IchimokuKinkoHyo": IchimokuKinkoHyo(
#                 inputs = [TWEquityPricing.high, TWEquityPricing.low, TWEquityPricing.close],
#                 window_length = 52,
#                 mask = StaticSids([0])
#             )
#         }, screen=StaticSids([0])
#     )
# ```
#
# [回到選單](#menu)

# %% [code] cell 51
from zipline.pipeline.factors import IchimokuKinkoHyo
def make_pipeline():
    
    Ich = IchimokuKinkoHyo(
        inputs = [TWEquityPricing.high, TWEquityPricing.low, TWEquityPricing.close],
        window_length = 52,
        mask = StaticSids([0])
    )

    return Pipeline(
        columns = {
            "tenkan_sen": Ich.tenkan_sen,
            "kijun_sen": Ich.kijun_sen,
            "senkou_span_a": Ich.senkou_span_a,
            "senkou_span_b": Ich.senkou_span_b,
            "chikou_span": Ich.chikou_span
        }, screen=StaticSids([0])
    )
run_pipeline(make_pipeline(), start_time, end_time)
