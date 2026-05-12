# -*- coding: utf-8 -*-
# Auto-generated from Zipline Trading Controls.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# <span id="menu"></span>
# # Zipline Trading Controls 交易限制函數

# %% [markdown] cell 1
# > ## 在 Zipline 中可以加入六種不同的交易限制：
# > 交易限制功能可以確保演算法如您所預期的的方式執行，並有助於避免預期外交易所帶來的不良後果。
# > 
# > 1. [set_do_not_order_list](#set_do_not_order_list)：預先設定一個不希望交易到的股票清單。
# > 2. [set_long_only](#set_long_only)：預先設定投資組合不能持有任何短部位（short positions）。
# > 3. [set_max_leverage](#set_max_leverage)：設定投資組合的槓桿限制。
# > 4. [set_max_order_count](#set_max_order_count)：限制一天內能夠下幾張 order。
# > 5. [set_max_order_size](#set_max_order_size)：限制特定股票（或全部）的單次下單股數及金額。
# > 6. [set_max_position_size](#set_max_position_size)：限制特定股票（或全部）在帳上的股數及市值。
# > 
# > ## 閱讀本篇之前請先閱讀以下文章：
# > 
# > 1. [TSMC buy and hold strategy.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/TSMC%20buy%20and%20hold%20strategy.ipynb) 
# > 
# > 2. [Zipline Order（order & order_target）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(order%20%26%20order_target).ipynb)
# > 
# > 3. [Zipline Order（value & target_value）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(value%20%26%20target_value).ipynb)
# >
# > 4. [Zipline Order（percent & target_percent）.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Order%20(percent%20%26%20target_percent).ipynb)
# >
# > 5. [Zipline Slippage.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Zipline%20Slippage.ipynb)

# %% [markdown] cell 2
# ### 補充說明：
# - 交易限制系列函數通常在`initialize`階段使用。
# - 可以一次加入多個交易限制。
# - 因為交易限制函數皆是 zipline api 方法，需先`from zipline.api import <欲使用的方法>` 或 `from zipline.api import *`。

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
start='2018-07-24'
end='2018-08-24'
os.environ['mdate'] = '20180724 20180824'

tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)

# calendar
calendar_name='TEJ'

# bundle_name
bundle_name = 'tquant'

os.environ['ticker'] = "2330 1216 1101 IR0001 2317 5844 2454 2357"

# %% [code] cell 5
# !zipline ingest -b tquant

# %% [code] cell 6
from zipline.api import *
from zipline import run_algorithm
from zipline.finance import commission, slippage
from zipline.utils.calendar_utils import get_calendar

from zipline.utils.run_algo import  get_transaction_detail

from logbook import Logger, StderrHandler, INFO

# 設定log顯示方式
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [markdown] cell 7
# <span id="set_do_not_order_list"></span>
# # set_do_not_order_list
#
# [Return to Menu](#menu)
#
# ### zipline.api.set_do_not_order_list(restricted_list, on_error='fail')
# 預先設定一個不希望交易到的股票清單
#
#
# - restricted_list (*container[Asset], SecurityList*)
#   - 預先限制不能交易的股票清單。
#   - container 中必須是`Asset`物件（`zipline.assets.Asset`，例如：Equity(0 [1101])，透過`symbol("1101")`可將 symbol 轉成`Asset`物件）
#   
#
# - on_error (*str, optional*)：
#   - on_error有兩種選項：'fail' 和 'log'。前者直接中斷程式並顯示錯誤訊息，後者會照樣執行但記錄錯誤。預設為'fail'。
#   - 若要使用on_error = 'log'，請同時進行以下設定，才能顯示 log：
#
#     ```python
#     from logbook import Logger, StderrHandler, INFO
#     # 設定log顯示方式
#     log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
#                                 '{record.level_name}: {record.func_name}: {record.message}',
#                                 level=INFO)
#     log_handler.push_application()
#     log = Logger('Algorithm')
#     ```
#     
# #### 範例1
#
# 在以下程式中，我們把 **1101 加入限制清單**，**on_error（發生時處理方法）使用'log'**，然後設定在7/26下單。
# ```python
# def initialize(context):
#     ...
#     set_do_not_order_list(restricted_list = [symbol('1101')], on_error='log')
#     ...
#
# def handle_data(context, data): 
#     ...
#     if context.i == 2:  # 2018-07-26
#         order(symbol('1101'), 100)
#     ...
# ```        
#         
# 可以看到執行時跳出
# ```
# ERROR: handle_violation: Order for 100 shares of Equity(0 [1101]) at 2018-07-26 05:30:00+00:00 violates trading constraint RestrictedListOrder({})
# ```
#  
# 但是觀察 transactions ，可以發現7/27時照樣買入了 1101。

# %% [code] cell 8
def initialize(context):
    context.i = 0
    set_do_not_order_list(restricted_list = [symbol('1101')], on_error='log')
    set_slippage(slippage.FixedSlippage(spread = 0.0))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    if context.i == 0:  # 2018-07-24
        order(symbol('2330'), 100)
        
    if context.i == 2:  # 2018-07-26
        order(symbol('1101'), 100)

    if context.i == 4:  # 2018-07-30
        order(symbol('1216'), 100)
        
    context.i += 1
    

commission_cost = 0.001425
capital_base = 1e6

performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [code] cell 9
# 7/27 照樣買入了1101。
transactions

# %% [markdown] cell 10
# #### 範例2
# 但如果 **on_error 設定成 'fail'**，整個程式會被中止，然後顯示一樣的錯誤訊息。
#
# ```python
# set_do_not_order_list(restricted_list = [symbol('1101')], on_error='fail')
# ```

# %% [code] cell 11
def initialize(context):
    context.i = 0
    set_do_not_order_list(restricted_list = [symbol('1101')], on_error='fail')
    set_slippage(slippage.FixedSlippage(spread = 0.0))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    if context.i == 0:  # 2018-07-24
        order(symbol('2330'), 100)
        
    if context.i == 2:  # 2018-07-26
        order(symbol('1101'), 100)

    if context.i == 4:  # 2018-07-30
        order(symbol('1216'), 100)
        
    context.i += 1


commission_cost = 0.001425
capital_base = 1e6

performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 12
# <span id="set_long_only"></span>
# # set_long_only
# 預先設定投資組合**不能**持有任何**短部位（short positions）**
#
# [Return to Menu](#menu)
#
# ### zipline.api.set_long_only(on_error='fail')
#
# on_error (*str, optional*)：
# - on_error有兩種選項：'fail' 和 'log'。前者直接中斷程式並顯示錯誤訊息，後者會照樣執行但記錄錯誤。預設為'fail'。
# - 若要使用on_error = 'log'，請同時進行以下設定，才能顯示 log：
#
# ```python
# from logbook import Logger, StderrHandler, INFO
# # 設定log顯示方式
# log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
#                             '{record.level_name}: {record.func_name}: {record.message}',
#                             level=INFO)
# log_handler.push_application()
# log = Logger('Algorithm')
# ```
#
# <br>
#
# #### 範例
# - 在以下這個範例我們設定`set_long_only(on_error='log')`，並且在7/24買入 1000 股 2330 股票、7/26賣出 500 股 2330 股票且在7/30賣出 800  股 2330 股票。
#
# ```python
# def initialize(context):
#     ...
#     set_long_only(on_error='log')
#     ...
#     
# def handle_data(context, data):  
#     if context.i == 0: # 7/24
#         order(symbol('2330'), 1000)
#
#     if context.i == 2: # 7/26 
#         order(symbol('2330'), -500)
#
#     if context.i == 4: # 7/30
#         order(symbol('2330'), -800)
#     ...
# ```
#
# - 當帳上持有 1000 股時賣出 500 股（7/26）是不會有問題的，但是如果再賣出 800 股（7/30），就會變成   - 300 股（short position），所以就會跳出了警示：
# ```python
# ERROR: handle_violation: Order for -800 shares of Equity(14 [2330]) at 2018-07-30 05:30:00+00:00 violates trading 
# constraint LongOnly({})
# ```
# 但因為 on_error 設定是 'log'，股票依然成功賣出。

# %% [code] cell 13
def initialize(context):
    context.i = 0
    set_long_only(on_error='log')
    set_slippage(slippage.FixedSlippage(spread = 0.0))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    if context.i == 0: # 7/24
        order(symbol('2330'), 1000)
        
    if context.i == 2: # 7/26 
        order(symbol('2330'), -500)

    if context.i == 4: # 7/30
        order(symbol('2330'), -800)
          
    context.i += 1
    
commission_cost = 0.001425
capital_base = 1e6

performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [code] cell 14
# 7/31持有股數（amount）變成-300
positions[0:6]

# %% [code] cell 15
# 持有short_position的股票個數
performance.shorts_count

# %% [markdown] cell 16
# <span id="set_max_leverage"></span>
# # set_max_leverage
# 設定投資組合的槓桿限制
#
# [Return to Menu](#menu)
#
# ### zipline.api.set_max_leverage(max_leverage)
#
# max_leverage (*float*) 
# - 投資組合的最高槓桿，必須 > 0。
# - 這邊的槓桿指的是`gross leverage`。
#   - 計算方式：`（long_exposure - short_exposure）／（long_exposure + short_exposure + ending_cash）`。
#     - ending_cash：當日結束時帳上持有現金。計算方式：starting_cash - capital_used。
#     - long_exposure：sum ( 持有股數 * 收盤價 ) = sum ( amount * last_sale_price )，where amount > 0。
#     - short_exposure：sum ( 持有股數 * 收盤價 ) = sum ( amount * last_sale_price )，where amount < 0。所以short_exposure <= 0。
#   - 參考連結：[lecture/TSMC buy and hold strategy.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/TSMC%20buy%20and%20hold%20strategy.ipynb)
#
# <br>
#
# #### 補充說明
# - 當投資組合的槓桿**超過**`max_leverage`時，程式會 **fail**。
# - 無法選擇以'log'方式呈現。
#
# #### 範例
# - 在以下這個範例，我們設定`set_max_leverage(3.0)`。
# - 在7/24先 long 價值一百萬的 2330 股票，short 價值一百萬的 2317 股票。
# ```python
# def handle_data(context, data):
#     if context.i == 0:   # 7/24
#         order_value(symbol('2330'), 1e6)
#         order_value(symbol('2317'), -1e6)
#     ...
# ```
# - 在7/26 long 價值五十萬的 2454 股票。
# ```python
# if context.i == 2:   # 7/26
#     order_value(symbol('2454'), 5e5)
# ```

# %% [code] cell 17
def initialize(context):
    context.i = 0
    set_slippage(slippage.FixedSlippage(spread = 0.0))
    set_max_leverage(3.0)
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    if context.i == 0:   # 7/24
        order_value(symbol('2330'), 1e6)
        order_value(symbol('2317'), -1e6)
            
    if context.i == 2:   # 7/26
        order_value(symbol('2454'), 5e5)

    context.i += 1
    
commission_cost = 0.001425
capital_base = 1e6


performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 18
# `gross_leverage` 可以直接從`run_algorithm`的結果進行觀察。（`performance['gross_leverage']`）
# - 計算方式如下，以7/25為例：
#
# ```
# leverage
# = ( long_exposure - short_exposure ) ／ ( long_exposure + short_exposure + ending_cash )
# = ( 2330 的 amount * 2330 的 last_sale_price - 2317 的 amount * 2317 的 last_sale_price ) / 
#   ( ending_cash + 2330 的 amount * 2330 的 last_sale_price + 2317 的 amount * 2317 的 last_sale_price )
# = ( 4149 * 240.5 - (- 11737 ) * 82.7 ) / ( 970010.30973 + 4149 * 240.5 + (- 11737 ) * 82.7 )
# = 1.974022
# ```
#
# #### 範例說明：
#   - `last_sale_price`及`amount`皆來自`performance`中的`positions`。
#     - `last_sale_price`代表標的最近一筆的收盤價。
#     - `amount`代表該標的總持有股數。
#   - `ending_cash`來自`performance`中的`ending_cash`，代表當日結束時帳上持有現金。
#   - 以上欄位定義的參考連結：[lecture/TSMC buy and hold strategy.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/TSMC%20buy%20and%20hold%20strategy.ipynb)

# %% [code] cell 19
performance.loc['2018-07-25':'2018-07-27',['gross_leverage','portfolio_value','ending_cash']]

# %% [code] cell 20
positions[0:2]

# %% [markdown] cell 21
# - 假設我們設定`set_max_leverage(2.0)`，在7/26時因為股價波動，leverage 超過 2.0，程式就會被終止，跳出錯誤訊息。
# - 那如果`set_max_leverage(2.4)`，且在7/27 long價值 50 萬的 2454，leverage 會達到 2.48，程式也一樣會被終止，跳出錯誤訊息。

# %% [markdown] cell 22
# <span id="set_max_order_count"></span>
# # set_max_order_count
# 限制一天內能夠下幾張 order
#
# [Return to Menu](#menu)
#
# ### zipline.api.set_max_order_count(max_count, on_error='fail')
# - max_count (*int*)：一天內最多的下單數。
#   
# - on_error (*str, optional*)：
#   - on_error有兩種選項：'fail' 和 'log'。前者直接中斷程式並顯示錯誤訊息，後者會照樣執行但記錄錯誤。預設為'fail'。
#   - 若要使用on_error = 'log'，請同時進行以下設定，才能顯示 log：
#
#     ```python
#     from logbook import Logger, StderrHandler, INFO
#     # 設定log顯示方式
#     log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
#                                 '{record.level_name}: {record.func_name}: {record.message}',
#                                 level=INFO)
#     log_handler.push_application()
#     log = Logger('Algorithm')
#     ```
#     
# #### 範例
# - 在以下範例中，我們設定`set_max_order_count(max_count=3, on_error='log')`，限制最大下單數為 3。
# - 設定滑價模型：`set_slippage(slippage.VolumeShareSlippage(volume_limit=0.025, price_impact=0.1))`，成交量限制為 2.5%。
# - 下單：
#   - 7/24 long 2330 及 2357 兩檔股票。
#   - 7/25 long 2454、2317 及 1101 三檔股票。
#
# ```python
# def handle_data(context, data):
#     if context.i == 0:  # 7/24
#         order_value(symbol('2330'), 5e8)
#         order_value(symbol('2357'), 3e8)
#
#     if context.i == 1:  # 7/25
#         order_value(symbol('2454'), 5e5)
#         order_value(symbol('2317'), 5e5)
#         order_value(symbol('1101'), 5e5)
#     ...
# ```
#
# #### 補充說明
# - 訂單數的計算方式：若要計算2018/7/25的訂單數，則從`performance`的`orders`取出`created = '2018-07-25'`的訂單進行計算。
# - 也就是說，如果因**滑價**或**條件單**的關係，訂單被拆成好幾天成交，則該張訂單只有在**成立那天**才會納入計算。
#
# [Return to Menu](#menu)

# %% [code] cell 23
def initialize(context):
    context.i = 0
    set_slippage(slippage.VolumeShareSlippage(volume_limit=0.025, price_impact=0.1))
    set_max_order_count(max_count=3, on_error='log')
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):
    
    if context.i == 0:  # 7/24
        order_value(symbol('2330'), 5e8)
        order_value(symbol('2357'), 3e8)
            
    if context.i == 1:  # 7/25
        order_value(symbol('2454'), 5e5)
        order_value(symbol('2317'), 5e5)
        order_value(symbol('1101'), 5e5)

    context.i += 1
    

commission_cost = 0.001425
capital_base = 1e9

performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 24
# #### 範例說明
# - 在7/24下單大量的 2330 和 2357，因為`VolumeShareSlippage`的限制，所以會拆成數天成交。
# - 這個會導致7/25不只有當天下的三張訂單，還有前一天 2330 和 2357 的單，共五張單。
# - 但是程式沒有跳出任何錯誤或警告，因為第一天下兩張單，第二天下三張單，程式判定都沒有超過 3，所以沒有問題。

# %% [code] cell 25
orders.loc['2018-07-25']

# %% [markdown] cell 26
# 如果設定`set_max_order_count(max_count=2, on_error='log')`，則在7/25會出現以下訊息：
#
# ```python
# ERROR: handle_violation: Order for 11086 shares of Equity(0 [1101]) at 2018-07-25 05:30:00+00:00 violates trading constraint MaxOrderCount({'max_count': 2})
# ```

# %% [markdown] cell 27
# <span id="set_max_order_size"></span>
# # set_max_order_size
# 這個函數限制特定股票（或全部）的**單次下單股數和金額**
#
# [Return to Menu](#menu)
#
# ### zipline.api.set_max_order_size(asset=None, max_shares=None, max_notional=None, on_error='fail')
# - asset (*Asset, optional*)
#   - 必須是`Asset`物件（`zipline.assets.Asset`，例如：Equity(0 [1101])，透過`symbol("1101")`可將 symbol 轉成`Asset`物件）
#   - 若**不為 None** 會對**指定股票**進行限制。
#   - 若設定為 **None** 則會讓**所有股票**皆適用這個限制條件。
# - max_shares (*int, optional*)－最大單次下單股數。
# - max_notional (*float, optional*)－最大單次下單金額。
# - on_error (*str, optional*)：
#   - on_error有兩種選項：'fail' 和 'log'。前者直接中斷程式並顯示錯誤訊息，後者會照樣執行但記錄錯誤。預設為'fail'。
#   - 若要使用on_error = 'log'，請同時進行以下設定，才能顯示log：
#
#     ```python
#     from logbook import Logger, StderrHandler, INFO
#     # 設定log顯示方式
#     log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
#                                 '{record.level_name}: {record.func_name}: {record.message}',
#                                 level=INFO)
#     log_handler.push_application()
#     log = Logger('Algorithm')
#     ```
#
# #### 補充說明：
# - `max_shares` 是以**下單時股數**為準。
# - `max_notional` 計算方法為**下單時的股數 * 下單當天收盤價**，所以成交時的股數和金額可能還是會超過`set_max_order_size`的限制，細節在下面的範例說明。
#
# #### 範例
# - 在以下這個範例，我們限制 1101 的 max_shares = 1000，且限制 2330 的 max_shares = 2000 、max_notional = 481000。
# ```python
# def initialize(context):
#     ...
#     set_max_order_size(asset= symbol('1101'), max_shares=1000, on_error='log')
#     set_max_order_size(asset= symbol('2330'), max_shares=2000, max_notional=481000, on_error='log')
#     ...
# ```
# - 在7/25 long 1000股的 1101 股票及 2000 股的 2330 股票。
# ```python
# def handle_data(context, data):
#     if context.i == 1:  # 2018-07-25
#         order(symbol('1101'), 1000)
#         order(symbol('2330'), 2000)
#     ...
# ```
# - 在8/16 long 2005 股的 2330 股票。
# ```python
# if context.i == 17:  # 2018-08-16
#     order(symbol('2330'), 2005)
# ```

# %% [code] cell 28
def initialize(context):
    context.i = 0
    set_max_order_size(asset= symbol('1101'), max_shares=1000, on_error='log')
    set_max_order_size(asset= symbol('2330'), max_shares=2000, max_notional=481000, on_error='log')
    set_slippage(slippage.FixedSlippage(spread = 0.0))
    set_commission(commission.PerDollar(cost=0.01))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):

    if context.i == 1:  # 2018-07-25
        order(symbol('1101'), 1000)
        order(symbol('2330'), 2000)

    if context.i == 17:  # 2018-08-16
        order(symbol('2330'), 2005)

    context.i += 1


commission_cost = 0.001425
capital_base = 1e6


performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

closing_price = tejapi.fastget('TWN/APIPRCD',
                               coid=['1101','2330'],
                               opts={'columns':['mdate','coid','close_d']},
                               mdate={'gte':start_dt,'lte':end_dt },
                               paginate=True)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 29
# #### 觀察7/25下的 1101
# - 在7/25下單 1000 股。
# - 但7/26遇到除權事件，調整後實際上買了1100股 > 限制的 1000 股，但是因為下單時是 1000 股，所以沒有問題。

# %% [code] cell 30
orders.query('symbol == "1101"')

# %% [markdown] cell 31
# #### 觀察7/25下的 2330
# - 在7/25下單 2000 股的 2330 ，當下的 notional = 2000 * 240.5（當天收盤）= 481000，符合設定的兩個限制。
# - 7/26成交時是以 241 元成交，當下的 notional = 2000 * 241 = 482000，超出原本設定的 `max_notional`，但並不會跳錯訊息。

# %% [code] cell 32
closing_price.query('(coid == "2330") & (mdate in ["2018-07-25","2018-07-26"])')

# %% [code] cell 33
transactions.loc['2018-07-26']

# %% [markdown] cell 34
# #### 觀察8/16下的 2330
# 在8/16下 2005 股的 2330，雖然當天 notional = 239 * 2005 = 479195 沒有超過預先設定的 481000，但已經超過 2000 股的限制。因為on_error = 'log'，程式繼續運作，照樣成交，但是跳出錯誤訊息：
#
# ```python  
# ERROR: handle_violation: Order for 2005 shares of Equity(14 [2330]) at 2018-08-16 05:30:00+00:00 violates trading  
# constraint MaxOrderSize({'asset': Equity(14 [2330]), 'max_shares': 2000, 'max_notional': 481000})
# ```    

# %% [code] cell 35
closing_price.query('(coid == "2330") & (mdate in ["2018-08-16","2018-08-17"])')

# %% [code] cell 36
transactions.loc['2018-08-17']

# %% [markdown] cell 37
# <span id="set_max_position_size"></span>
# # set_max_position_size
# 限制特定股票（或全部）在帳上的股數及市值
#
# [Return to Menu](#menu)
#
# ### zipline.api.set_max_position_size(asset=None, max_shares=None, max_notional=None, on_error='fail')
# - asset (*Asset, optional*)
#   - 必須是`Asset`物件（`zipline.assets.Asset`，例如：Equity(0 [1101])）
#   - 若**不為 None** 會對**指定股票**進行限制。
#   - 若設定為 **None** 則會讓**所有股票**皆適用這個限制條件。
# - max_shares (*int, optional*)－最大**持股**股數。
# - max_notional (*float, optional*)－最大**持股**市值。
# - on_error (*str, optional*)：
#   - on_error有兩種選項：'fail' 和 'log'。前者直接中斷程式並顯示錯誤訊息，後者會照樣執行但記錄錯誤。預設為'fail'。
#   - 若要使用on_error = 'log'，請同時進行以下設定，才能顯示log：
#
#     ```python
#     from logbook import Logger, StderrHandler, INFO
#     # 設定log顯示方式
#     log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
#                                 '{record.level_name}: {record.func_name}: {record.message}',
#                                 level=INFO)
#     log_handler.push_application()
#     log = Logger('Algorithm')
#     ```
#     
# #### 補充說明
# - 這個函數用法跟`set_max_order_size()`非常類似，差別在於它是限制某支（或全部）股票在**帳上**的股數及市值，而非針對**單筆訂單**。
# - 這函數**只會在下單當下進行檢查**並判斷帳上的部位（position）會不會超過限制，並不是一直追蹤帳上的部位。
# - 若是我們同一檔股票下兩張訂單，則每張訂單將會**個別判定**。
# - 下面用一些比較特殊的例子，同時應用`max_order_size`和`max_position_size`來解釋運作規則。
#
# #### 範例
# - 在範例中，我們做以下限制：　
#   - 限制 2330 單筆訂單的 max_shares = 2000、max_notional = 481000。
#   - 限制 1101 持股部位的 max_shares = 1050。
#   - 限制 2330 持股部位的 max_shares = 2000、max_notional = 600000。
#   
#     ```python
#     def initialize(context):
#         ...
#         set_max_order_size(asset= symbol('2330'), max_shares=2000, max_notional=481000, on_error='log')
#         set_max_position_size(asset= symbol('1101'), max_shares=1050, on_error='log')
#         set_max_position_size(asset= symbol('2330'), max_shares=2000, max_notional=600000, on_error='log')
#         ...
#     ```
# - 下單設定：
#   - 在7/24 long 1000股的 1101 股票。
#     ```python
#     def handle_data(context, data):
#         if context.i ==0: # 2018-07-24
#             order(symbol('1101'), 1000)
#     ```
#   - 在7/25 下兩張訂單，分別 long 2000 股及 1000 股的 2330 股票。
#     ```python
#         if context.i == 1: # 2018-07-25
#             order(symbol('2330'), 2000)
#             order(symbol('2330'), 1000)
#     ```
#   - 在7/31 long 500股的 2330 股票。
#     ```python
#         if context.i == 5: # 2018-07-31
#             order(symbol('2330'), 500)
#     ```

# %% [code] cell 38
def initialize(context):
    context.i = 0
    
    set_max_order_size(asset= symbol('2330'), max_shares=2000, max_notional=481000, on_error='log')
    set_max_position_size(asset= symbol('1101'), max_shares=1050, on_error='log')
    set_max_position_size(asset= symbol('2330'), max_shares=2000, max_notional=600000, on_error='log')
    
    set_slippage(slippage.FixedSlippage(spread = 0.0))
    set_commission(commission.PerDollar(cost=0.01))
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):

    if context.i ==0: # 2018-07-24
        order(symbol('1101'), 1000)
    
    if context.i == 1: # 2018-07-25
        order(symbol('2330'), 2000)
        order(symbol('2330'), 1000)

    if context.i == 5: # 2018-07-31
        order(symbol('2330'), 500)
        
    context.i += 1


commission_cost = 0.001425
capital_base = 1e6

performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

closing_price = tejapi.fastget('TWN/APIPRCD',
                               coid=['1101','2330'],
                               opts={'columns':['mdate','coid','close_d']},
                               mdate={'gte':start_dt,'lte':end_dt },
                               paginate=True)

positions, transactions, orders = get_transaction_detail(performance)

# %% [markdown] cell 39
# #### 觀察7/24下的訂單
# - 雖然7/24下的 1000 股 1101 在7/26除權之後變成 1100 股，超過限制的 1050 股，但沒有錯誤訊息（`MaxPositionSize`）。
# - 此外**因為在下單時，系統判定買 1000 股會讓手上 position 從 0 變成 1000 股，沒有超過 1050**，所以沒有錯誤訊息。
# - 同樣道理，如果單子因為除權事件造成成交股數和下單時股數不同，還是以**下單時股數**為主。

# %% [code] cell 40
orders[0:2]

# %% [code] cell 41
positions[0:2]

# %% [markdown] cell 42
# #### 觀察7/25下的訂單
# - 在7/25連續下了兩單，分別是 2000 股和 1000 股的 2330，雖然總和是 3000 股，超過限制的 2000 股，但也沒有錯誤訊息（`MaxOrderSize`）。**因為兩單都沒有超過max_order_size 的 2000 股限制**。
# - 而因為這兩張單子隔天（7/26）才會成交，下單時 position = 0，`max_position_size`認為其中一單是讓 position 從 0 變成 2000，另一單是讓 position 從 0 變成 1000，都沒有超過總股數 2000 的限制（`max_notional`部分也是同樣概念），所以也沒有錯誤訊息（`MaxPositionSize`）。
# - 接下來幾天股價上升，notional也早就超過`max_notional(600000)`，但也沒有錯誤訊息，因為並不是一直追蹤帳上的部位。

# %% [markdown] cell 43
# #### 觀察7/31下的訂單
# - 7/31下單 500 股 2330 時跳出以下錯誤訊息，因為帳上 3000 股，再加 500，就會超過2000（`max_notional`部分也是同樣概念）。
# - 而且因為**超過了兩個限制**，同一筆交易跳出**兩行**錯誤訊息（但因為我們用on_error = 'log'，所有訂單還是成交）。
#
# ```python
# ERROR: handle_violation: Order for 500 shares of Equity(3 [2330]) at 2018-07-31 05:30:00+00:00 violates trading constraint MaxPositionSize({'asset': Equity(3 [2330]), 'max_shares': 2000, 'max_notional': 600000})
#
# ERROR: handle_violation: Order for 500 shares of Equity(3 [2330]) at 2018-07-31 05:30:00+00:00 violates trading constraint MaxPositionSize({'asset': Equity(3 [2330]), 'max_shares': 2000, 'max_notional': 600000})
# ```

# %% [code] cell 44
orders.query('symbol=="2330"')

# %% [code] cell 45
positions['mv'] = positions['amount'] * positions['last_sale_price']
positions.loc[positions.symbol=='2330']

# %% [markdown] cell 46
# [Return to Menu](#menu)
