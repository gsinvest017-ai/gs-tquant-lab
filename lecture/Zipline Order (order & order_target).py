# -*- coding: utf-8 -*-
# Auto-generated from Zipline Order (order & order_target).ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 下單方法介紹(一)
#
# <span id="menu"></span>
# # Zipline Order函數介紹－order和order_target
# Order函數是用於交易股票的函數，可以利用以下六種函數得出我們指定要交易的股票以及數量
#
# > ## Zipline有六種下單函數：
# 	order()：購買指定股數。
# 	order_value()：購買指定價值的股票。
# 	order_percent()：購買指定價值（整個投資組合價值（portfolio value）的一個特定比例）的股票。
# 	order_target()：交易直到該股票帳上總股數達到指定數量為止。
#     order_target_value()：交易到帳上該股票價值達到指定價值為止。
#     order_target_percent()：將股票在投資組合的比重調整到指定的比例。
# >     
# > ## 本篇將會介紹`order()`以及`order_target()`的使用辦法。
# 本文件包含以下四個部份：
# > 1. [函數說明](#下單函數的參數與回傳值)
# > 2. [範例：order（搭配 limit_price）](#limit_price)
# > 3. [範例：order（搭配 stop_price）](#Stop_price)
# > 4. [範例：order_target](#order_target)
# >
# > ## 閱讀本篇之後可以搭配閱讀：
# > 
# > 1. [Zipline Order（value & target_value）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(value%20%26%20target_value).ipynb)
# >
# > 2. [Zipline Order（percent & target_percent）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(percent%20%26%20target_percent).ipynb)

# %% [markdown] cell 1
# <span id="下單函數的參數與回傳值"></span>
# ## 下單函數的參數與回傳值：
# ### <u>Import：</u>     
# 使用前記得先做 import：`from zipline.api import order, order_target`或`from zipline.api import *`。
#
#
# ### <u>Parameters：</u>
# - asset：*zipline.assets.Asset*，為該股票的`Asset`物件（`zipline.assets.Asset`，例如：Equity(0 [1101])，透過`symbol("1101")`可將 symbol 轉成`Asset`物件）。
# - **amount／value／target／percent：數量、價值、目標、比重，依照每個下單函數各有不同，但一律正值代表 long（buy or cover），而負值代表 short（sell or short）。**
# - limit_price：*float, optional*
#   - 限價。
#   - 代表最高的買進價（或最低的賣出價）。
#   - 預設為 None。
#   
#     ```python
#     # 以order為例，其它下單函數概念一樣。
#     from zipline.api import order
#     
#     order(asset, amount, limit_price=limit_price)
#     ```
# - stop_price：*float, optional*
#   - 止損價。
#   - 若為買單，當市價 >= stop price，則用市價買入（若是賣單，則是在市價 <= stop price 後用市價賣出）。
#   - 預設為 None。
#   
#     ```python
#     # 以order為例，其它下單函數概念一樣。
#     from zipline.api import order
#     
#     order(asset, amount, stop_price=stop_price)
#     ```
# - style：*zipline.finance.execution.ExecutionStyle*
#   - 預設為 None。
#   - 設定限價及止損價。如果`limit_price`或`stop_price`已經提供了，就不能使用這個參數。
#   
#     ```python   
#     # 以order為例，其下單函數概念一樣。
#     from zipline.finance.execution import LimitOrder, StopOrder, StopLimitOrder
#     from zipline.api import order
#
#     # Limit order：
#     order(asset, amount, style=LimitOrder(limit_price))
#     # Stop order：
#     order(asset, amount, style=StopOrder(stop_price))
#     # StopLimit order：
#     order(asset, amount, style=StopLimitOrder(limit_price, stop_price))
#     ```
#
# ### <u>Returns：</u>
# order_id：*str or None*，每張訂單獨一無二的 16 進制編碼。
#
# ---
#
# ### 交易機制：
# - 市價皆為**收盤價**。
# - 因 zipline 交易機制的關係，下單後會到next bar才成交（**也就是今天下單，下一交易日才成交**），所以`stop_price`及`limit_price`皆是和**下一個交易日的收盤價**做比較。
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
start='2018-07-24'
end='2018-08-14'
os.environ['mdate'] = '20180724 20180814'

tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)

# calendar
calendar_name='TEJ'

# bundle_name
bundle_name = 'tquant'

os.environ['ticker'] = '1101 1102 IR0001'

# %% [code] cell 4
# !zipline ingest -b tquant

# %% [code] cell 5
from zipline.api import *
from zipline import run_algorithm
from zipline.finance import commission, slippage
from zipline.utils.calendar_utils import get_calendar

from zipline.utils.run_algo import  get_transaction_detail

# %% [markdown] cell 6
# <span id="limit_price"></span>
# # 範例：order（搭配 limit_price）
# 從2018/07/24到2018/08/14，每天買一張1101，limit_price = 45。
#
# [Return to Menu](#menu)

# %% [markdown] cell 7
# `zipline.api.order(asset, amount, limit_price=None, stop_price=None, style=None)`
#
# ####  amount
# - 單位為**股**。
# - 若下單股數有**小數點**的情形，則會**取整數**後再進行下單。取整數的方法為：若股數和最近整數相差在 0.0001 以內，就取最接近整數，否則直接去掉小數（3.9999 -> 4.0　;　5.5 -> 5.0　;　-5.5 -> -5.0）。
#
# ####   limit_price = XX
# 購買的價格必須<=XX才會買進

# %% [markdown] cell 8
# ## 設定交易模型
# #### initialize(context):
# 在回測開始時被調用的函數，進行初始化設定
#
# 這邊透過context參數來儲存和共享各種回測所需的變數和參數
#
# * `context.tickers = ['1101']`
#         定義一個股票代碼列表，這裡我們指定 1101 的股票資料。
# * `context.asset = [symbol(ticker) for ticker in context.tickers]`
#         將股票代碼輸入進 context 中，並轉換為 `Asset` 物件。
# * `set_slippage(slippage.FixedSlippage(spread=0.00))`
#         設定滑價模型，這裡使用的是固定滑價模型，價差為 0。方便觀察。
# * `set_commission(commission.PerDollar(cost=commission_cost))`
#         設定交易費用模型，這裡設定一定比例的交易費用。
# * `set_benchmark(symbol('IR0001'))`
#         設定benchmark，將benchmark設為代碼為 'IR0001' 的資產，即發行量加權股價報酬指數。

# %% [code] cell 9
def initialize(context):
    context.tickers = ['1101']
    context.asset = [symbol(ticker) for ticker in context.tickers]
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))

# %% [markdown] cell 10
# ## 設定交易策略
# #### handle_data(context, data):
# 在每個交易日被調用的函數，用於處理資料並進行交易
# - data用於提供回測過程中的資料。通過data，我們可以獲取股票的歷史價格、成交量等資訊。
#
# 對context.asset中的每檔股票，下單購買 1000 股，限價為 45。
# ```python
# for asset in context.asset: 
#     order(asset, 1000, limit_price = 45)
# ```

# %% [code] cell 11
def handle_data(context, data):

    for asset in context.asset:
        order(asset, 1000, limit_price = 45)

# %% [markdown] cell 12
# ### 設定交易成本、回測
# - commission_cost：交易成本設置
# - capital_base：交易本金

# %% [code] cell 13
commission_cost = 0.001425 + 0.003 / 2
capital_base = 1e6

# %% [markdown] cell 14
# ## 設置run_algorithm中的函數
# run_algorithm是用於運行zipline回測的主要程式碼，通過設定回測的起始日期、結束日期、初始資本金和所使用的數據，並使用initialize、handle_data和 analyze函數來進行回測運算。<br>
# ### positions, transactions, orders = get_transaction_detail(performance)
#         使用get_transaction_detail產出以下三個DataFrame:
#             - positions 持倉狀態
#             - transactions 交易紀錄
#             - orders 訂單紀錄

# %% [code] cell 15
closing_price = tejapi.fastget('TWN/APIPRCD',
                               coid=['1101'],
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

# %% [markdown] cell 16
# ## 講解說明

# %% [markdown] cell 17
# ### 7/25
# - 可以觀察到在每日收盤價7/25的收盤價大於 limit_price 的 45 元，因此只有下單，沒有買入股票。

# %% [code] cell 18
closing_price[0:2]

# %% [code] cell 19
# 7/24~7/25只有下單，沒有買入股票
orders.loc['2018-07-24':'2018-07-25']

# %% [code] cell 20
# 7/24~7/25沒有交易紀錄
transactions.loc['2018-07-24':'2018-07-25']

# %% [markdown] cell 21
# ### 7/26
# - 2018/7/26是**除權日**，配發 10% 股票股利。ratio = 0.908945。
#   - orders 中的 amount 由 1000 股變 1100 股（1000 / 0.908945）。
#   - 在7/24、7/25下的單（created），limit 皆變成 45 * 0.908945 = 40.9。
# - 因為7/26的收盤價 40.5 <= 40.9，所以兩單都在7/26成交（**status=1**），下單量也都調整成了 1100（amount）。而且**limit_reached在成交時也都變成了True**。
#
# - 但是7/26當天下的單（**created = '2018-07-26'**），limit_price 還是 45 沒有調整，amount 還是 1000。代表除權日後如果股價 <= 45（limit_price），則買進 1000 股。

# %% [code] cell 22
closing_price[0:3]

# %% [code] cell 23
orders.query('created.dt.strftime("%Y-%m-%d") in ["2018-07-24", "2018-07-25","2018-07-26"]')

# %% [code] cell 24
transactions.loc['2018-07-26']

# %% [markdown] cell 25
# ### 7/27
# - 因為7/27收盤價為 40.3 <= 45，於是用 40.3 元成交 1000 股。

# %% [code] cell 26
closing_price[3:4]

# %% [code] cell 27
orders.query('created.dt.strftime("%Y-%m-%d") == "2018-07-26"')

# %% [code] cell 28
transactions.loc['2018-07-27']

# %% [markdown] cell 29
# ### 補充：
# 若原本 limit_price 設為 43.5，其餘條件不變，那7/24、7/25下的那兩單，要一直等到7/31股價 <= 43.5 * 0.908945 = 39.54 後，才會各以當天收盤價 39.35 及 1100 股成交。

# %% [code] cell 30
closing_price[0:6]

# %% [markdown] cell 31
# <span id="Stop_price"></span>
# # 範例：order（搭配 stop_price）
# [Return to Menu](#menu)

# %% [markdown] cell 32
# ## 從2018/07/24到2018/08/14，每天買一張1101，stop_price = 43
# ### stop_price = xx
# 當價格>=xx時買入股票
#
# ### handle_data設置
# 這邊將交易策略進行修改：每天買一張 1101，購買的金額要 >= 43。

# %% [code] cell 33
def initialize(context):

    context.tickers = ['1101']
    context.asset = [symbol(ticker) for ticker in context.tickers]
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))

def handle_data(context, data):

    for asset in context.asset:
        order(asset, 1000, stop_price = 43)

    record(close=data.current(context.asset, 'close'))

# %% [code] cell 34
performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 35
# ## 講解說明
#
# ### 7/25
#   
# - 1101 在7/25（還沒發股票股利）收盤價為 45.1 >= 43（stop_price），所以7/24的單在7/25以 45.1 * 1000 股成交。成交時 'stop_reached' 也會變成 True。

# %% [code] cell 36
closing_price[0:2]

# %% [code] cell 37
orders.query('created.dt.strftime("%Y-%m-%d") == "2018-07-24"')

# %% [code] cell 38
transactions.loc['2018-07-25']

# %% [markdown] cell 39
# ### 7/26
#
# - 7/26為除權日，7/25的單處理邏輯是：下單量調整成 1000 / 0.908945 = 1100，stop_price 調整為 43 * 0.908945 = 39.08。
#   - 因為7/26收盤價 40.5 >= 39.08（新 stop_price），所以會以 40.5 * 1100 股成交。

# %% [code] cell 40
closing_price[2:3]

# %% [code] cell 41
orders.query('created.dt.strftime("%Y-%m-%d") == "2018-07-25"')

# %% [code] cell 42
transactions.loc['2018-07-26']

# %% [markdown] cell 43
# - 7/26和之後下的單子，因為收盤價一直沒有達到 43，7/26到8/13的單子都累積到了8/14才各自用 43.3 * 1000 股成交。

# %% [code] cell 44
closing_price[3:]

# %% [markdown] cell 45
# - 在下面這張 positions 表格可以看到，7/25的 1000 股（amount），是除權前就成交的（7/24下單，7/25成交）。
# - 而7/25的單在除權日（7/26）成交，所以才會變成買入 1100 股，原本帳上持有的 1000 股也在7/26變成 1100 股，帳上共 2200 股（amount）。
# - 7/26至8/13共計 13 交易日的單子，則全部在8/14成交，因為下單跟成交都在除權後發生，沒有受到影響，每一單都是 1000 股。

# %% [code] cell 46
positions

# %% [markdown] cell 47
# <span id="order_target"></span>
# # 範例：order_target
# [Return to Menu](#menu)

# %% [markdown] cell 48
# `zipline.api.order_target(asset, target, limit_price=None, stop_price=None, style=None)`
#
# - `order_target`的概念和`order`很像，差別是`order_target`會透過買／賣讓**帳上的股票數量達到指定的數量('target')**，而不像`order`直接買／賣該數量('amount')。
# - 若下單股數若有**小數點**情形，則會**取整數**後再進行下單。取整數的方法為：若股數和最近整數相差在 0.0001 以內，就取最接近整數，否則直接去掉小數（3.9999 -> 4.0　;　5.5 -> 5.0　;　-5.5 -> -5.0）。
# - target 單位為**股**。

# %% [markdown] cell 49
# ## 把本單元所有概念結合
# ### 設定交易策略
# #### handle_data
# 1. ```python
#     if context.i == 0: # 2018-07-24
#         for asset in context.asset:
#             order(asset, 1000)
#    ```
#    在回測的第一個時間點（context.i 為 0，2018-07-24），下單購買 1000 股的1101。
#         
# 2. ```python
#     if context.i == 1: # 2018-07-25
#         for asset in context.asset:
#             order_target(asset, 1100)
#    ```
#    在回測的第二個時間點（context.i 為 1，2018-07-25），對投資組合中的每檔股票進行調整，使其持有量達到 1100 股。    
#         
# 3. ```python
#     if context.i == 3: # 2018-07-27
#         for asset in context.asset:
#             order_target(asset, 2000)
#    ```
#    在回測的第四個時間點（context.i 為 3，2018-07-27），對投資組合中的每檔股票進行調整，使其持有量達到 2000 股。
#     
# 4. ```python
#     if context.i == 5: # 2018-07-31
#         for asset in context.asset:
#             order_target(asset, 3000, stop_price = 40, limit_price = 40.3)
#    ```
#    在回測的第六個時間點（context.i 為 5，2018-07-31），對投資組合中的每檔股票進行調整，使其持有量達到 3000 股。此外，此訂單還設定了（stop_price）為 40 和（limit_price）為 40.3，代表當股價在 >= 40 及 <= 40.3 時才會進行交易。
#         
# 5. 
# ```python
# record(close=data.current(context.asset, 'close'))
# context.i += 1
# ```
# 記錄每檔股票的收盤價，並將 `context.i` 遞增 1，表示回測進入下一個時間點。

# %% [code] cell 50
def initialize(context):
    context.i = 0
    context.tickers = ['1101']
    context.asset = [symbol(ticker) for ticker in context.tickers]
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))

def handle_data(context, data):

    if context.i == 0: # 2018-07-24
        for asset in context.asset:
            order(asset, 1000)

    if context.i == 1: # 2018-07-25
        for asset in context.asset:
            order_target(asset, 1100)

    if context.i == 3: # 2018-07-27
        for asset in context.asset:
            order_target(asset, 2000)

    if context.i == 5: # 2018-07-30
        for asset in context.asset:
            order_target(asset, 3000, stop_price = 40, limit_price = 40.3)

    record(close=data.current(context.asset, 'close'))
    context.i += 1

# %% [code] cell 51
performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 52
# ## 講解說明

# %% [markdown] cell 53
# ### 7/24、7/25
# - 7/24時用最基本的order功能下單 1000 股的台泥（1101）。並在7/25成交。
# - 7/25用 order_target 將目標股數設為 1100，於是下單 100 股。

# %% [code] cell 54
orders.loc['2018-07-24':'2018-07-25']

# %% [markdown] cell 55
# 在下一個交易日（7/26）遇到除權日，ratio = 0.908945，所以7/25的單子amount會調整成 100 / 0.908945 = 110。

# %% [code] cell 56
orders.query('created.dt.strftime("%Y-%m-%d") == "2018-07-25"')

# %% [markdown] cell 57
# 原本帳上的 1000 股也在除權日調整成 1100 股，所以7/26收盤時手上共有 1100 + 110 = 1210 股。 不會是原先設定的 1100 股。

# %% [code] cell 58
positions.loc['2018-07-25':'2018-07-26']

# %% [markdown] cell 59
# ### 7/27
# 在7/27時用 order_target 將手上股數調整成 2000，算出還需要 2000 - 1210 = 790股，下單後隔日成交。

# %% [code] cell 60
orders.loc['2018-07-27':'2018-07-30']

# %% [code] cell 61
positions[3:4]

# %% [markdown] cell 62
# ### 7/31
# 在7/31時下單：`order_target(asset, 3000, stop_price = 40, limit_price = 40.3)`
# - 這代表當股價 >= 40 以後，買 1000 股將帳上持有股數從 2000 股調整成 3000 股，但是限制買入價不能超過 40.3。
# - 在8/1時股價就超過 40，所以一直要到8/7時股價 <= 40.3 時才會買入 1000 股。

# %% [code] cell 63
# 下order_target(asset, 3000, stop_price = 40, limit_price = 40.3)
orders.loc['2018-07-31']

# %% [code] cell 64
# 8/1-8/6股價 > 40.3，8/7 <= 40.3
closing_price[4:11]

# %% [code] cell 65
# 8/7成交
orders.loc['2018-08-07']

# %% [code] cell 66
# 8/7帳上由2000股->3000股
positions[4:10]

# %% [markdown] cell 67
# [Return to Menu](#menu)
