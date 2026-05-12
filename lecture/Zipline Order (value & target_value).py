# -*- coding: utf-8 -*-
# Auto-generated from Zipline Order (value & target_value).ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 下單方法介紹(二)
#
# <span id="menu"></span>
# # Zipline order_value 和 order_target_value
#
# > ## Zipline有六種下單函數：
# 	order()：購買指定股數。
# 	order_value()：購買指定價值的股票。
# 	order_percent()：購買指定價值（整個投資組合價值（portfolio value）的一個特定比例）的股票。
# 	order_target()：交易直到該股票帳上總股數達到指定數量為止。
#     order_target_value()：交易到帳上該股票價值達到指定價值為止。
#     order_target_percent()：將股票在投資組合的比重調整到指定的比例。
# >
# > ## 本篇將會介紹`order_value()`以及`order_target_value()`的使用辦法。
# > 本文件包含以下兩個部份：
#   > - [函數介紹](#函數介紹)
#   > - [範例：order_value與order_target_value](#Order_value與Order_target_value)
# >
# >
# > ## 閱讀本篇之前請先閱讀：
# >
# > [Zipline Order (order & order_target).ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(order%20%26%20order_target).ipynb)
# > ## 閱讀本篇之後可以搭配閱讀：
# > 
# > [Zipline Order（percent & target_percent）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(percent%20%26%20target_percent).ipynb)

# %% [markdown] cell 1
# <span id="函數介紹"></span>
#
# ## 函數介紹：
#
# 使用前記得先做 import：`from zipline.api import order_value, order_target_value`或`from zipline.api import *`。
#
# <br>
#
# *　order_value：買賣指定價值的股票。
#
# `zipline.api.order_value(asset, value, limit_price=None, stop_price=None, style=None)`
#
# **value**：*float*股票價值
#
# *　order_target_value：透過買／賣使手上股票在**下單當下**的市場價值達到指定目標。
#
# `zipline.api.order_target_value(asset, target, limit_price=None, stop_price=None, style=None)`
#
# **target**：*float*目標價值
#
# ---
#
# ### 交易機制：
# - 市價皆為**收盤價**。
# - 因zipline交易機制的關係，下單後會到next bar才成交（**也就是今天下單，下一交易日才成交**），所以`stop_price`及`limit_price`皆是和**下一個交易日的收盤價**做比較。
# - `order_value`與`order_target_value`運作邏輯類似，都是以**下單日的收盤價**做基準，將下單的價值**轉換為 amount**。實際交易時再用**當天的收盤價**，和**下單時算出的 amount 成交**，所以**下單時指定的價值不一定會與實際成交時價值一致**。
# - 與其他 order 系列函數相同，下單時算出的 amount 若有**小數點**，則會**取整數**後再進行下單。取整數的方法為：若股數和最近整數相差在 0.0001 以內，就取最接近整數，否則直接去掉小數（3.9999 -> 4.0　;　5.5 -> 5.0　;　-5.5 -> -5.0）。
# - 若遇到**股票分割、股票股利等股數變動**情形：
#   - 在**除權日之前**下的單，`stop_price`及`limit_price`會在**除權日**進行調整。
#   - 新的`stop_price`及`limit_price`都是**原本數值乘以 ratio（也就是僅除權的調整係數）** 並 round 到小數以下第二位。（**僅除權的調整係數**使用 TEJ API 的 TWN/APIPRCD（交易資料-股價資料）中的 adjfac_a 欄位進行計算）
#   
# ### 規則補充：
# - order 系列函數通常在`handle_data`階段使用且不得在`before_trading_start`階段使用。
# - 當使用 limit order、stop order、stop limit order 等**條件單（contingent order）**時，會產生額外的交易成本（**機會成本 opportunity cost**），因這些條件單的使用可能會影響潛在利潤。order 系列函數都提供相關功能可以模擬該成本。

# %% [markdown] cell 2
# ## 設定環境

# %% [code] cell 3
import pandas as pd
import numpy as np
import datetime
import tejapi
import time
import os
import warnings
warnings.filterwarnings('ignore')

# tej_key
tej_key ='your key'
tejapi.ApiConfig.api_key = tej_key
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
os.environ['TEJAPI_KEY'] = tej_key

# date
# set date
start='2022-09-16'
end='2022-10-16'

os.environ['mdate'] = '20220916 20221016'

tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)

# calendar
calendar_name='TEJ'

# bundle_name
bundle_name = 'tquant'

os.environ['ticker'] = '2603 IR0001'

# %% [code] cell 4
# !zipline ingest -b tquant

# %% [code] cell 5
from zipline.api import *
from zipline import run_algorithm
from zipline.finance import commission, slippage
from zipline.utils.calendar_utils import get_calendar

from zipline.utils.run_algo import  get_transaction_detail

# %% [markdown] cell 6
# <span id="Order_value與Order_target_value"></span>
# ## 範例：order_value與order_target_value
#
# [Return to Menu](#menu)

# %% [markdown] cell 7
# ### 交易策略
#
# #### def handle_data(context, data):
#
# 在回測的第一個時間點（context.i 為 0，2022-09-16），購買`context.asset`中每檔股票，每檔價值皆為 40000 元。
# ```python
# if context.i == 0:
#     for asset in context.asset:
#         order_value(asset, 40000)
# ```
#
# 在回測的第十一個時間點（context.i 為 10，2022-09-30），對投資組合中的每檔股票進行調整，使其帳上持有的價值達到 60000 元。
# ```python
# if context.i == 10:
#     for asset in context.asset:
#         order_target_value(asset, 60000)
# ```
# 在回測的第十六個時間點（context.i 為 15，2022-10-07），對投資組合中的每檔股票進行調整，使其帳上持有的價值減少到 30000 元。
# ```python
# if context.i == 15:
#     for asset in context.asset:
#         order_target_value(asset, 30000)
# ```
# 最後，使用 record 函數記錄每檔股票的收盤價。然後遞增 context.i 的值，表示回測已進入下一個時間點。  
# ```python
# record(close=data.current(context.asset, 'close'))
# context.i += 1
# ```
# 記錄每檔股票的收盤價，並將 `context.i` 遞增 1，表示回測進入下一個時間點。

# %% [code] cell 8
def initialize(context):
    context.i = 0
    context.tickers = ['2603']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    if context.i == 0:   # 2022-09-16
        for asset in context.asset:
            order_value(asset, 40000)
            
    if context.i == 10:  # 2022-09-30
        for asset in context.asset:
            order_target_value(asset, 60000)

    if context.i == 15:  # 2022-10-07
        for asset in context.asset:
            order_target_value(asset, 30000)
            
    record(close=data.current(context.asset, 'close'))
    context.i += 1

commission_cost = 0.001425 + 0.003 / 2  # commission + tax 
capital_base = 1e6

# %% [code] cell 9
closing_price = tejapi.fastget('TWN/APIPRCD',
                               coid=['2603'],
                               opts={'columns':['mdate','coid','close_d']},
                               mdate={'gte':start_dt,'lte':end_dt },
                               paginate=True)

performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 10
# ## 9/16
# - 在9/16時下單買進價值 40000 元的長榮（2603）股票，用9/16的收盤價計算出應買股數為 40000 / 80.8 $\approx$ 495。
# - 下個交易日（9/19）遇到減資，ratio是 2.314356，所以下單量調整成 495 / 2.314356 $\approx$ 213，並以當天收盤價 169 元成交。

# %% [code] cell 11
closing_price.query('mdate <= "2022-09-19"')

# %% [code] cell 12
orders.loc['2022-09-16':'2022-09-19']

# %% [markdown] cell 13
# ## 9/30
# - 9/30利用 order_target_value 下單，希望將 2603 的持股價值調整為 60000 元。
# - 首先計算9/30帳上長榮的市值 146（last_sale_price）* 213股 = 31098，所以還需要 ( 60000 - 31098 ) / 146 $\approx$ 197股（無條件捨去）。

# %% [code] cell 14
positions.loc['2022-09-30']

# %% [markdown] cell 15
# 下一個交易日（10/3）成交。

# %% [code] cell 16
orders.loc['2022-09-30':'2022-10-03']

# %% [markdown] cell 17
# ## 10/7
# - 在10/7利用order_target_value()下單，希望將 2603 的持股價值調整為 30000 元。因為帳上長榮股票市值超過 30000，需要賣掉一定數量來達到目標。
# - 用10/7的收盤價和帳上持有數量，計算出價值為 155.5（last_sale_price） * 410 = 63755，需要賣掉 ( 63755 - 30000 ) / 155.5 $\approx$ 217股（無條件捨去）。

# %% [code] cell 18
positions.loc['2022-10-07']

# %% [markdown] cell 19
# - 在下個交易日（10/11），以當天收盤價 156 賣出

# %% [code] cell 20
orders.query('created.dt.strftime("%Y-%m-%d") == "2022-10-07"')

# %% [markdown] cell 21
# ### Exposure：
# - 在 performance （`run_algorithm` 產出的報表）中的 `long_exposure` （帳上股票長部位市值）可以看到，在10/3第一次調整，目標是 6 萬元，但因為10/3市價相對於下單日（9/30）提高了，然而還是會用9/30算出來的 amount 去買，因此 long_exposure 超出了目標。
# - 同理，在10/11第二次調整，目標是 3 萬，但因為10/11市價相對於下單日（10/7）提高了，然而還是會用10/7算出來的 amount 去買，因此 long_exposure 也超出了目標。

# %% [code] cell 22
performance[['period_open','long_exposure']].query('period_open.dt.strftime("%Y-%m-%d") in ["2022-10-03","2022-10-11"]')

# %% [code] cell 23
closing_price

# %% [markdown] cell 24
# [Return to Menu](#menu)
