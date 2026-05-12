# -*- coding: utf-8 -*-
# Auto-generated from Zipline Order (percent & target_percent).ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 下單方法介紹(三)
#
# <span id="menu"></span>
# # Zipline order_percent和order_target_percent
#
# > ## Zipline有六種下單函數：
# 	order()：購買指定股數。
# 	order_value()：購買指定價值的股票。
# 	order_percent()：購買指定價值（整個投資組合價值（portfolio value）的一個特定比例）的股票。
# 	order_target()：交易直到該股票帳上總股數達到指定數量為止。
#     order_target_value()：交易到帳上該股票價值達到指定價值為止。
#     order_target_percent()：將股票在投資組合的比重調整到指定的比例。
# >     
# > ## 本篇將會介紹`order_percent()`以及`order_target_percent()`的使用辦法。
# 本文件包含以下三個部份：
# > * [函數說明](#函數說明)
# > * [範例：order_percent](#Order_percent)
# > * [範例：order_target_percent](#Order_target_percent)
# > 
# > ## 閱讀本篇之前請先閱讀：
# > 
# > 1. [Zipline Order（order & order_target）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(order%20%26%20order_target).ipynb)
# > 
# > 2. [Zipline Order（value & target_value）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(value%20%26%20target_value).ipynb)

# %% [markdown] cell 1
# <span id="函數說明"></span>
# ## 函數說明
# 使用前記得先做 import：`from zipline.api import order_percent, order_target_percent`或`from zipline.api import *`。
#
# *　order_percent：買賣一檔股票，買賣量為目前**投資組合價值（portfolio value）**的某個特定比例。
#
# `zipline.api.order_percent(asset, percent, limit_price=None, stop_price=None, style=None)`
#
# **percent**：*float*，特定比例。
#
# <br>
#
#
# *　order_target_percent：買／賣一檔股票使得該股票價值占**投資組合價值的某個目標比例（target）**，而不是直接買／賣目前**投資組合價值**的某個特定比例。
#
# `zipline.api.order_target_percent(asset, target, limit_price=None, stop_price=None, style=None)`
#
# **target**：*float*，目標比例。
#
# ---
#
# ### 交易機制：
# - 市價皆為**收盤價**。
# - 因 zipline 交易機制的關係，下單後會到 next bar 才成交（**也就是今天下單，下一交易日才成交**），所以`stop_price`及`limit_price`皆是和**下一個交易日的收盤價**做比較。
# - 若遇到**股票分割、股票股利等股數變動**情形：
#   - 在**除權日之前**下的單，`stop_price`及`limit_price`會在**除權日**進行調整。
#   - 新的`stop_price`及`limit_price`都是**原本數值乘以 ratio（也就是僅除權的調整係數）** 並 round 到小數以下第二位。（**僅除權的調整係數**使用 TEJ API 的 TWN/APIPRCD（交易資料-股價資料）中的 adjfac_a 欄位進行計算）
#   
# ### 規則補充：
# - order 系列函數通常在`handle_data`階段使用且不得在`before_trading_start`階段使用。
# - 當使用 limit order、stop order、stop limit order 等**條件單（contingent order）**時，會產生額外的交易成本（**機會成本 opportunity cost**），因這些條件單的使用可能會影響潛在利潤。order 系列函數都提供相關功能可以模擬該成本。

# %% [markdown] cell 2
# # 範例講解

# %% [markdown] cell 3
# ## 設定環境

# %% [code] cell 4
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
start='2018-07-24'
end='2018-08-14'
os.environ['mdate'] = '20180724 20180814'

tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)

# calendar
calendar_name='TEJ'

# bundle_name
bundle_name = 'tquant'

os.environ['ticker'] = '1101 2330 IR0001'

# %% [code] cell 5
# !zipline ingest -b tquant

# %% [code] cell 6
from zipline.api import *
from zipline import run_algorithm
from zipline.finance import commission, slippage
from zipline.utils.calendar_utils import get_calendar

from zipline.utils.run_algo import  get_transaction_detail

# %% [markdown] cell 7
# <span id="Order_percent"></span>
# ## 範例：order_percent
# [Return to Menu](#menu)
#
# - 運作方式：
#   - 先用自行輸入的比例（percent）及目前投資組合價值，算出需要購買的**總金額**。
#   - 再搭配下單日的收盤價，算出要買的**股數 amount**進行下單。
#   - 到了**下一個交易日**再用**該日的收盤價**和**下單時算出的 amount** 成交。
#   - 所以**下單時指定的百分比不一定會與實際成交時的百分比一致**。  
#   
#
# - 與其他 order 系列函數相同，下單時算出的 amount 若有**小數點**，則會**取整數**後再進行下單。取整數的方法為：若股數和最近整數相差在 0.0001 以內，就取最接近整數，否則直接去掉小數（3.9999 -> 4.0　;　5.5 -> 5.0　;　-5.5 -> -5.0）。

# %% [markdown] cell 8
# ### 設置交易策略
# #### def handle_data(context, data):
#
# 在回測的第一個交易時間點（i 等於 0，2018-07-27）時
# ```python
# if context.i == 0:
#     order_percent(symbol('1101'), 0.3, limit_price = 43.5)
#     # 使用限價訂單購買股票 '1101'，量為投資組合當前價值的 30%，限價為 43.5
#     order_percent(symbol('2330'), 0.3, limit_price = 240.6)
#     # 使用限價訂單購買股票 '2330'，量為投資組合當前價值的 30%，限價為 240.6
# ```    
# 在回測的第七個交易時間點（i 等於 6，2018-08-01）時
# ```python
# if context.i == 6:
#     order_percent(symbol('1101'), 0.2)
#     # 購買股票 '1101'，量為投資組合當前價值的 20%
#     order_percent(symbol('2330'), 0.2)
#     # 購買股票 '2330'，量為投資組合當前價值的 20%
# ```       
# 記錄投資組合中所有資產的收盤價
# ```python
# record(close=data.current(context.asset, 'close'))
# context.i += 1
# ```  

# %% [code] cell 9
def initialize(context):
    context.i = 0
    context.tickers = ['1101','2330']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    if context.i == 0:  # 2018-07-27
        order_percent(symbol('1101'), 0.3, limit_price = 43.5)
        order_percent(symbol('2330'), 0.3, limit_price = 240.6)
        
    if context.i == 6:  # 2018-08-01
        order_percent(symbol('1101'), 0.2)
        order_percent(symbol('2330'), 0.2)

    record(close=data.current(context.asset, 'close'))
    context.i += 1

commission_cost = 0.001425 + 0.003 / 2
capital_base = 1e5

# %% [code] cell 10
closing_price = tejapi.fastget('TWN/APIPRCD',
                               coid=['1101','2330'], 
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

# %% [markdown] cell 11
# ## 7/24
# 7/24建立兩單，1101、2330 各 30%，limit_price 分別為 43.5、240.6。

# %% [markdown] cell 12
# #### 在7/24時起始現金為 100,000，30%的金額為 30000
# #### 1101 購買股數 = 30000 / 45.5 $\approx$ 659 股
# #### 2330 購買股數 = 30000 / 241 $\approx$ 124股

# %% [code] cell 13
closing_price.query('(mdate == "2018-07-24")')

# %% [code] cell 14
orders.loc['2018-07-24']

# %% [markdown] cell 15
# ## 7/25
# - 到了7/25時 2330 的收盤價為 240.5，低於limit_price 的 240.6，於是成交（status = 1）。
# - 但 1101 股價高於 limit_price 43.5，沒有成交。

# %% [code] cell 16
closing_price.query('(mdate == "2018-07-25")')

# %% [code] cell 17
orders.query('created.dt.strftime("%Y-%m-%d") == "2018-07-24"')

# %% [markdown] cell 18
# ## 7/26
# - 到了7/26時 1101 經過一次除權，ratio = 0.908945，7/24訂單的 limit_price 現在變成 43.5 * 0.908945 = 39.54，amount = 659 / 0.908945 = 725。
# - 單子還繼續開著，到了7/31才以 39.35 成交。
# - 注意，購買量是用下單日的價值、收盤價計算，成交時用成交日收盤價，所以購入的金額在成交日時不會剛好是投資組合的 30%。

# %% [code] cell 19
closing_price.query('(mdate <= "2018-07-31") & (coid == "1101")')

# %% [code] cell 20
orders.query('(created.dt.strftime("%Y-%m-%d") == "2018-07-24")  & (symbol == "1101")')

# %% [markdown] cell 21
# ## 8/1
# - 8/1時 1101、2330 各下單 20%，沒有 stop／limit price。
# - 利用 ( 8/1 的 portfolio value * 0.2) / ( 8/1收盤價 )，算出 1101 需要買入 496 股，2330 需要買入 82 股，並於下一個交易日成交。
#
# #### 在8/1時 portfolio value 為 101992，20% 的金額為 20398
# #### 1101 購買股數 = 20398 / 41.05 $\approx$ 496 股
# #### 2330 購買股數 = 20398 / 248 $\approx$ 82 股

# %% [code] cell 22
# portfolio value
performance[['portfolio_value']].loc['2018-08-01']

# %% [code] cell 23
# 收盤價
closing_price.query('(mdate == "2018-08-01")')

# %% [markdown] cell 24
# #### 8/1交易訊號跑出

# %% [code] cell 25
orders.loc['2018-08-01']

# %% [markdown] cell 26
# #### 8/2買入股票

# %% [code] cell 27
orders.loc['2018-08-02']

# %% [markdown] cell 28
# <span id="Order_target_percent"></span>
# ## 範例：order_target_percent
# order_target_percent 用來限制該股票占投資組合價值的比例，如果持股價值超過設定的比例，他就會賣出股票來達到目標權重。相對的，如果持股價值低於設定的比例，則買入股票。<br>
#
# - 與`order_percent`原理類似，實際成交後該股票占投資組合價值的比例不一定會與目標相同。
# - 與其他 order 系列函數相同，下單時算出的 amount 若有**小數點**，則會**取整數**後再進行下單。取整數的方法為：若股數和最近整數相差在 0.0001 以內，就取最接近整數，否則直接去掉小數（3.9999 -> 4.0　;　5.5 -> 5.0　;　-5.5 -> -5.0）。
#
# [Return to Menu](#menu)

# %% [markdown] cell 29
# ### 設置交易策略
# #### def handle_data(context, data):
#
# 在回測的第一個交易時間點（i 等於 0，2018-07-27）時
# ```python
# if context.i == 0:
#     order_target_percent(symbol('1101'), 0.3, limit_price = 43.5)
#     # 使用限價訂單購買股票 '1101'，使得持股價值達到為投資組合當前價值的 30%，限價為 43.5
#     order_target_percent(symbol('2330'), 0.3, limit_price = 240.6)
#     # 使用限價訂單購買股票 '2330'，使得持股價值達到投資組合當前價值的 30%，限價為 240.6
# ```
# 在回測的第七個交易時間點（i 等於 6，2018-08-01）時
# ```python
# if context.i == 6:
#     order_target_percent(symbol('1101'), 0.2)
#     # 調整 '1101' 持股使得持股價值達到投資組合當前價值的 20%
#     order_target_percent(symbol('2330'), 0.2)
#     # 調整 '2330' 持股使得持股價值達到投資組合當前價值的 20%
# ```    
# 記錄投資組合中所有資產的收盤價
# ```python
# record(close=data.current(context.asset, 'close'))
# context.i += 1
# ```

# %% [code] cell 30
def initialize(context):
    context.i = 0
    context.tickers = ['1101','2330']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    if context.i == 0:  # 2018-07-27
        order_target_percent(symbol('1101'), 0.3, limit_price = 43.5)
        order_target_percent(symbol('2330'), 0.3, limit_price = 240.6)
         
    if context.i == 6:  # 2018-08-01
        print(calculate_order_target_percent_amount(symbol('1101'), 0.2))
        order_target_percent(symbol('1101'), 0.2)
        order_target_percent(symbol('2330'), 0.2)

    record(close=data.current(context.asset, 'close'))
    context.i += 1

# %% [code] cell 31
performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 32
# ## 7/25及7/31
# 7/25及7/31成交的部分跟上面 order_percent 結果一樣，因為一開始的投資組合價值皆為 100,000（起始現金）。

# %% [code] cell 33
transactions.loc[:'2018-07-31']

# %% [markdown] cell 34
# ## 8/1
# #### 在8/1時portfolio value為 101992，20%的金額為 20398
# #### 1101 目標股數 = 20398 / 41.05 = 496 股，因此 496 - 725 = - 228.09378806333734 $\approx$ - 228
#      要將出售 228 股，才能讓股票價值變成當下 portfolio value 的 20%。
# #### 2330 目標股數 = 20398 / 248 = 82 股，因此 82 - 124 = - 41.75 $\approx$ - 41
#      要將出售 41 股，才能讓股票價值變成當下 portfolio value 的 20%。

# %% [code] cell 35
# portfolio value
performance[['portfolio_value']].loc['2018-08-01']

# %% [code] cell 36
# 收盤價
closing_price.query('(mdate == "2018-08-01")')

# %% [code] cell 37
positions.loc['2018-08-01']

# %% [markdown] cell 38
# #### 8/1交易訊號跑出並下單

# %% [code] cell 39
orders.loc['2018-08-01']

# %% [markdown] cell 40
# #### 8/2賣出股票

# %% [code] cell 41
orders.loc['2018-08-02']

# %% [markdown] cell 42
# **8/2當天兩檔股票的價值都不會剛好是 20398。**

# %% [code] cell 43
positions['value'] = positions['amount'] * positions['last_sale_price']
positions.loc['2018-08-02']

# %% [markdown] cell 44
# [Return to Menu](#menu)
