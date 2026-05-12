# -*- coding: utf-8 -*-
# Auto-generated from Zipline Cancel Order.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# <span id="menu"></span>
# # Zipline Cancel Order 取消訂單

# %% [markdown] cell 1
# > - 若演算法受到**滑價（slippage）的成交量限制**或**股票暫停交易**的影響，可能會導致**下單後無法在一個交易日內成交**，尤其遇到**成交量小**的公司或**下單量很大**時，更是有可能要花費10個交易日以上才能完全成交。
# > - 若是不希望該筆訂單存續過久，可以透過`get_open_orders`與`cancel_order`兩個函數在特定時點**將未完全成交訂單取消**。
# > 
# >     1. `get_open_orders(asset = None)`：取得未完全成交的訂單資料。
# >     2. `cancel_order(order)`：取消某筆訂單。
# > 
# > 
# > 
# > ## 本文件包含以下三個部份：
# >   1. [函數介紹](#函數介紹)
# >   2. [範例：交易量限制、暫停交易搭配取消交易](#交易量限制、暫停交易)
# >   3. [範例：指定特定日期的取消交易搭配stop_price](#指定特定日期的取消交易)
# >   
# > ## 閱讀本篇之前請先閱讀以下文章：
# > 1. [TSMC buy and hold strategy.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/TSMC%20buy%20and%20hold%20strategy.ipynb) 
# > 
# > 2. [Zipline Order（order & order_target）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(order%20%26%20order_target).ipynb)
# > 
# > 3. [Zipline Order（value & target_value）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(value%20%26%20target_value).ipynb)
# >
# > 4. [Zipline Order（percent & target_percent）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(percent%20%26%20target_percent).ipynb)

# %% [markdown] cell 2
# ## 建立環境

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
start='2022-10-15'
end='2022-11-05'
os.environ['mdate'] = '20221015 20221105'

tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)

# calendar
calendar_name='TEJ'

# bundle_name
bundle_name = 'tquant'

# ticker
os.environ['ticker'] = "1216 2330 2327 IR0001 5844"

# %% [code] cell 4
# !zipline ingest -b tquant

# %% [code] cell 5
from zipline.api import *
from zipline import run_algorithm
from zipline.finance import commission, slippage
from zipline.utils.calendar_utils import get_calendar

from zipline.utils.run_algo import  (get_transaction_detail,
                                     get_record_vars)

from logbook import Logger, StderrHandler, INFO

# 設定log顯示方式
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [markdown] cell 6
# <span id="函數介紹"></span>
# ## 函數介紹
# [Return to Menu](#menu)
#
#   
# <br>
#
# ### zipline.api.get_open_orders(asset=None)
# 取得未完全成交的訂單資料
#
# **Parameters:**  
# asset：*zipline.assets.Asset*
# - 預設為 None，會回傳**所有**未完全成交的訂單資料。
# - 若提供該股票的`Asset`物件（`zipline.assets.Asset`，例如：Equity(0 [1101])，透過`symbol("1101")`可將 symbol 轉成`Asset`物件），則僅回傳**該股票**的未完全成交訂單資料。
#
#
# **Returns:**  
# 回傳未完全成交的訂單資料，資料型態為`dict[list[Order]]`
#
# - 訂單資料為一個字典，key 是 asset 物件，value 是一個 list，list 中有 order 物件（`zipline.finance.order.Order`）。
# - order物件範例如下：
# ```python
# Event({'id': '3096bfae27824859a4f9aba7a75fb31a', 'dt': Timestamp('2022-10-17 05:30:00+0000', tz='UTC'), 'reason': None, 'created': Timestamp('2022-10-17 05:30:00+0000', tz='UTC'), 'amount': 1500000, 'filled': 0, 'commission': 0, 'stop': None, 'limit': None, 'stop_reached': False, 'limit_reached': False, 'sid': Equity(1 [1216]), 'status': <ORDER_STATUS.OPEN: 0>})
# ```
# - order 物件中的屬性，可以用 order.xxx 單獨呼叫，例如：使用 order.id 會回傳該張訂單的 order_id。
# - 屬性定義參考以下連結中`orders`的說明：[lecture/TSMC buy and hold strategy.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/TSMC%20buy%20and%20hold%20strategy.ipynb)。
#
#   
# <br>
#
# ### zipline.api.cancel_order(order_param)
# 取消某筆訂單。  
#
# **Parameters:**  
# order_param：*str or Order* 
# - 可以使用 **order_id** （`zipline.finance.order.Order.id`）或 **order 物件**（`zipline.finance.order.Order`）來指定欲取消的訂單。
# - order_id：
#   - 每張訂單**獨一無二**的 16 進制編碼。
#   - order 系列函數在下單時的回傳值就是 order_id。
# - order 物件（`zipline.finance.order.Order`）：
#   - 可透過`zipline.api.get_open_orders`取得。
#   - 可將 order_id 傳入`zipline.api.get_order(order_id)`取得。
#   
# ###  補充說明 
# - `get_open_orders`與`cancel_order`兩個函數通常在`handle_data`階段使用。
# - 使用函數前記得先做 import：`from zipline.api import cancel_order, get_open_orders`或`from zipline.api import *`。

# %% [markdown] cell 7
# <span id="交易量限制、暫停交易"></span>
# ## 範例：交易量限制、暫停交易
# 若訂單在建立後的下一個交易日未能完全成交，希望取消訂單。
#
#
# [Return to Menu](#menu)
#
# 在以下這個範例，我們設計了 **PART A** 及 **PART B** 兩部分程式碼：
#
# - **PART A**
#     - 在每天交易前利用`get_open_orders`檢查並用`cancel_order`取消還沒成交的訂單。
#     ```python
#     def handle_data(context, data):
#         
#         open_orders = get_open_orders()
#
#         for asset in open_orders:
#             for o in open_orders[asset]:
#                 cancel_order(o)
#         ...
#     ```
#     - 設定滑價模型：`set_slippage(slippage.VolumeShareSlippage(volume_limit=0.025, price_impact=0.1))`，並限制買賣量最高只能是當天實際成交量的 **2.5%**。
#     
#     - 設定交易：
#       - 在2022/10/17 long 1500000 股的 1216 股票。
#       - 在2022/10/19 long 1000 股的 2327 股票。
#       - 在2022/10/20 long 1000 股的 2327 股票。    
#       - 每天顯示 2327 股票`data.is_stale`的狀態。
#
#     ```python
#     def handle_data(context, data):
#         ...
#         print(get_datetime(), symbol('2327'), 'is_stale =', data.is_stale(symbol('2327')))
#
#         if context.i == 0: # 2022-10-17
#             order(symbol('1216'), 1500000)
#
#         if context.i == 2: # 2022-10-19
#             order(symbol('2327'), 1000) 
#
#         if context.i == 3: # 2022-10-20
#             order(symbol('2327'), 1000) 
#         ...
#     ```
#
# - **PART B**  
# 在每天**下單後**，檢查 **data.is_stale = True** 的股票，並取消該股票所有的訂單。
# ```python
# def handle_data(context, data):
#     
#     ...
#     open_orders = get_open_orders()
#        
#     for asset in open_orders:
#         if data.is_stale(asset):
#             for o in open_orders[asset]:
#                 cancel_order(o)
#     ...
# ```
#
# ###  補充說明
#
# > ### data.is_stale(assets)：  
# > - 若該股票未下市、曾經有交易紀錄且當天 volume = 0 則回傳 **True**，否則 **False**。
# > - 通常當股票當天**暫停交易**或是**成交量為 0** 時會回傳 **True**，這種情況下 zipline 是不會交易的。 
# >
# > **Parameters:**  
# > asset：*zipline.assets.Asset or iterable of zipline.assets.Asset*，該股票的`Asset`物件（例如：Equity(0 [1101])）。
# > 
# > **Return type:**  
# > bool or pd.Series[bool]

# %% [code] cell 8
def initialize(context):
    context.i = 0  
    context.tickers = ['1216', '2330', '2327']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage. VolumeShareSlippage(volume_limit=0.025, price_impact=0.1))
    set_commission(commission.PerDollar(cost = commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    # PART A---------------------------------------------------------------------------------------
    open_orders = get_open_orders()
    
    for asset in open_orders:
        for o in open_orders[asset]:
            cancel_order(o)

    
    print(get_datetime(), symbol('2327'), 'is_stale =', data.is_stale(symbol('2327')))

    if context.i == 0: # 2022-10-17
        order(symbol('1216'), 1500000)
    
    if context.i == 2: # 2022-10-19
        order(symbol('2327'), 1000) 

    if context.i == 3: # 2022-10-20
        order(symbol('2327'), 1000) 
     
    # PART B---------------------------------------------------------------------------------------
    open_orders = get_open_orders()
       
    for asset in open_orders:
        if data.is_stale(asset):
            for o in open_orders[asset]:
                cancel_order(o)

    
    record(close=data.current(context.asset, 'close'))
    record(volume=data.current(context.asset, 'volume')*1000)
    context.i += 1
    

commission_cost = 0.001425
capital_base = 1e8


performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

closing_price = tejapi.fastget('TWN/APIPRCD',
                               coid=['1216'],
                               opts={'columns':['mdate','coid','open_d','close_d','vol']},
                               mdate={'gte':start,'lte':end },
                               paginate=True)

closing_price['vol'] = closing_price['vol'] * 1000

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 9
# ## 講解說明
# ### 10/17
# - 在10/17下單 1500 張統一（1216）股票，因為下單量超過10/18總交易量的2.5%，所以**10/18只成交總交易量的2.5%，剩下分批成交**。
#   - amount = 162350 股 = 6494000 * 2.5%。
#   - 滑價說明參考：[lecture/Zipline Slippage.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Slippage.ipynb)。
# - 如果**希望達到10/18限制量就停止成交**，則可使用 **PART A** 程式碼，在**每天交易前檢查並取消還沒成交的訂單**。
# - 在 orders 資料中的 'status' 可以看到該訂單在買完第10/18的量時就被提前取消（**'status' 由 0 變成 2**）。

# %% [code] cell 10
# vol：實際成交量，單位為股。
closing_price.query('(coid == "1216") & (mdate == "2022-10-18")')

# %% [code] cell 11
orders.query('symbol == "1216"')

# %% [code] cell 12
transactions

# %% [markdown] cell 13
# ### 10/19
# - 國巨（2327） 在10/20~10/28暫停交易（因此 is_stale = True），按照原本 zipline 的機制，不管是暫停前一天，或是暫停期間下單，都會在恢復交易當天成交（如果有辦法的話）。
# - 如果要加入限制機制，可以參考以上程式　PART B：
#   - 在每天下單後，檢查任何 is_stale = True 的股票，並取消相關的訂單。
#   - 從 orders 資料中可以發現，10/19下的單子在10/20被取消；在10/20下的單子，當天就被取消。

# %% [code] cell 14
orders.query('symbol == "2327"')

# %% [markdown] cell 15
# <span id="指定特定日期的取消交易"></span>
# ## 範例：指定特定日期的取消交易、stop_price應用
# 希望未成交訂單不要保留超過10天。
#
# [Return to Menu](#menu)
#
# 在以下這個範例，我們設計了 **PART C** 的程式碼：
#
# - 取消訂單邏輯：
#   - 每天利用`get_open_orders`產出未完全成交的訂單。
#   - 針對上述訂單逐筆進行以下判斷：若距離訂單建立日（`zipline.finance.order.Order.created`）達10個交易日（不含建立日），但還沒有完全成交時取消該訂單。
#
#     ```python
#     calendar_name='TEJ'
#     
#     def handle_data(context, data):
#         open_orders = get_open_orders()
#
#         for asset in open_orders:
#             for o in open_orders[asset]:
#                 waiting_time = (len(get_calendar(calendar_name).sessions_in_range(o.created, get_datetime())))
#                 if waiting_time == 10:
#                     cancel_order(o)
#         ...
#     ```
# - 設定交易：
#   - 在10/17 long 1000 股的 1216 股票，並設定 stop_price = 66。
#   - 在10/20 long 1000 股的 1216 股票，並設定 stop_price = 65.5。    
#
#     ```python    
#     def handle_data(context, data):
#         ...
#         if context.i == 0: # 2022-10-17
#             order(symbol('1216'), 1000, stop_price = 66)
#
#         if context.i == 3: # 2022-10-20
#             order(symbol('1216'), 1000, stop_price = 65.5)
#         ...
#     ```

# %% [code] cell 16
def initialize(context):
    context.i = 0  
    context.tickers = ['1216', '2330', '2327']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage. VolumeShareSlippage(volume_limit=0.025, price_impact=0.1))
    set_commission(commission.PerDollar(cost = commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    #PART C    
    open_orders = get_open_orders()

    for asset in open_orders:
        for o in open_orders[asset]:
            waiting_time = (len(get_calendar(calendar_name).sessions_in_range(o.created, get_datetime())))
            if waiting_time == 10:
                cancel_order(o)
    
    if context.i == 0: # 2022-10-17
        order(symbol('1216'), 1000, stop_price = 66)

    if context.i == 3: # 2022-10-20
        order(symbol('1216'), 1000, stop_price = 65.5)
        
   
    record(close=data.current(context.asset, 'close'))
    record(volume=data.current(context.asset, 'volume'))
    context.i += 1


commission_cost = 0.001425
capital_base = 1e8

performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

closing_price = tejapi.get('TWN/APIPRCD',
                           coid=['1216'],
                           opts={'columns':['mdate','coid','close_d']},
                           mdate={'gte':start,'lte':end },
                           paginate=True)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 17
# ## 講解說明
# ### 10/17
# - 在10/17下的訂單，設定 stop_price = 66，所以理論上這單會一直在 open_orders 中，直到在11/1才會買入（收盤價 >= 66）。
# - 因為理論上 zipline 會**無限期**等 **stop_price 和 limit_price 達到目標**，如果希望設下限制，當等待時間達到十個交易日（10/31）就取消，可以參考 **PART C** 程式碼。
# - 這段程式碼先運用了**order 物件中的created屬性**（`zipline.finance.order.Order.created`）取得訂單建立時間，再用`get_datetime()`取得當天時間，接著用 `get_calendar(calendar_name).sessions_in_range(start, end)` 算出經過了多少個交易日，最後建立迴圈並逐日檢查並取消等待太久的訂單。

# %% [code] cell 18
closing_price.query('(mdate <= "2022-11-01")')

# %% [code] cell 19
orders.query('created.dt.strftime("%Y-%m-%d") == "2022-10-17"')

# %% [markdown] cell 20
# ### 10/20
# 在10/20下的訂單，stop_price = 65.5，在10/25就成交，並沒有等待超過十天，因此不會被 **PART C** 這段程式給取消掉。

# %% [code] cell 21
closing_price.query('(mdate <= "2022-10-25") & (mdate >= "2022-10-20")')

# %% [code] cell 22
orders.query('created.dt.strftime("%Y-%m-%d") == "2022-10-20"')

# %% [code] cell 23
transactions

# %% [markdown] cell 24
# [Return to Menu](#menu)
