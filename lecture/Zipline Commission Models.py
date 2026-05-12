# -*- coding: utf-8 -*-
# Auto-generated from Zipline Commission Models.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# <span id="top"></span>
# # <font color=#57a892>手續費模型（Commission Models）</font>

# %% [markdown] cell 1
# - 交易成本（transaction costs）被廣泛認為是影響投資績效的重要因素。它們不僅影響投資績效，還影響了將資產轉換成現金的難易度。
#
# - 在真實世界的交易中存在許多種類的交易成本，其中一種是**直接成本（direct cost）**。直接成本包含了**手續費（commission）、證交稅**等等，這些成本是在交易前已經**提前知道的成本**。此類成本皆可以使用 Zipline 中的 **commission models** 進行模擬。這也是回測（backtesting）的一大目的，考量投資策略在真實世界運行的可能性。

# %% [markdown] cell 2
# ## zipline.api.<font color=#57a892>set_commission</font>(self, equities=None, futures=None)
#
# 設定回測時所使用的手續費模型。
#
#
# > ### Parameters：
# > - equities *(EquityCommissionModel, optional)* －用於交易股票的手續費模型。
# >   - EquityCommissionModel：`zipline.finance.commission`
# > - futures *(FutureCommissionModel, optional)* －用於交易期貨的手續費模型。（目前不支援）
# >   - FutureCommissionModel：`zipline.finance.commission`
# > 
# > ### Raises：
# > **SetCommissionPostInit**－`set_commission` **只能**在 `initialize` 階段使用。
# > 
# > ### Notes：
# > - `set_commission` 只能一次用**一種**方法。
# > - 手續費計算時，**價格以成交日收盤價為準，數量也以成交時為準**。也就是說，如果因為股數變動造成 amount 有任何變化，計算上都是用成交時新的 amount。
# > 
# > ### See also：
# > - `zipline.finance.commission.PerShare`
# > - `zipline.finance.commission.PerTrade`
# > - `zipline.finance.commission.PerDollar`
# > - `zipline.finance.commission.Custom_TW_Commission`
# > 
# > ### Examples：
# > ```python
# > from zipline.api import set_commission
# > from zipline.finance import commission
# > 
# > def initialize(context):
# >     set_commission(commission.<其中一種commission models>)
# > ```

# %% [markdown] cell 3
# ## class zipline.finance.commission.<font color=#57a892>CommissionModel</font>
# > 手續費模型的抽象基類（Abstract Base Class）。
# > 
# > 手續費模型是用來計算每筆交易需繳交多少手續費。Zipline 目前有五種模型：
# >  
# > 1. `PerDollar`：按照交易金額抽成計算。
# > 2. `PerTrade`：一筆交易收取一筆固定費用。
# > 3. `PerShare`：按照下單的股數計算費用，同時還可以設定一個最低費用。
# > 4. `Custom_TW_Commission`：台灣專用的手續費模型。
# > 5. `NoCommission`：不收任何手續費。
#
# ## class zipline.finance.commission.<font color=#57a892>PerDollar</font>(cost=0.0015)
# > - 按照交易金額抽成計算。
# > - 僅適用於 equities。
# > 
# > ### Parameters：
# > - cost *(float, optional)*－每交易一元的股票所需支付的固定費用。預設為 0.0015 元。
#
# ## class zipline.finance.commission.<font color=#57a892>PerTrade</font>(cost=0.0)
# > - 一筆交易收取一筆固定費用。
# > - 適用於 equities 與 futures。
# > 
# > ### Parameters：
# > - cost *(float, optional)*－每進行一筆交易所需支付的固定費用。預設為 0 元。
#
# ## class zipline.finance.commission.<font color=#57a892>PerShare</font>(cost=0.001, min_trade_cost=0.0)
# > - 按照下單的股數計算費用，同時還可以設定一個最低費用。
# > - 僅適用於 equities。
# > - 為**預設模型**。
# > 
# > ### Parameters：
# > - cost *(float, optional)*－每交易一股的股票所需支付的固定費用。預設為 0.001 元。
# > - min_trade_cost *(float, optional)*－最低費用，預設為無最低費用。
#
# ## class zipline.finance.commission.<font color=#57a892>Custom_TW_Commission</font>(min_trade_cost=20, discount=1.0, tax = 0.003)
# > - 台灣股票適用的手續費模型，考量券商手續費（費率：0.001425）及證交稅，同時還可以設定一個最低費用。
# > - 台灣交易股票時的情況的情況：在台灣交易股票時，主要有兩個直接成本：**手續費**及**證交稅**。`Custom_TW_Commission` 可模擬這兩項成本。
# >   - 手續費
# >     - **買進**或**賣出**時皆須繳交。
# >     - 計算方式為：成交價 × 成交股數 × 0.1425 % × 折扣（折扣預設是 1，沒有折扣）。
# >     - 手續費有**最低價格**（預設是 20 元）。
# > 
# >   - 證交稅
# >     - **賣出**時才要繳交。
# >     - 計算方式為：成交價 × 成交股數 × 證交稅率（證交稅率預設是 0.3%）。
# > - 僅適用於 equities。
# >  
# > ### Parameters：
# > - min_trade_cost *(float, optional)*－最低費用。預設為 20 元。
# > - discount *(float, optional)*－券商手續費折扣比率。預設為 1，代表沒有折扣。
# > - tax *(float, optional)*－證交稅率，預設為 0.003。
# > 
# > ### Notes：
# > - 手續費計算時，**價格以成交日收盤價為準，數量也以成交時為準**，也就是說，如果因為股數變動造成 amount 有任何變化，計算上都是用成交時新的 amount。
#
# ## class zipline.finance.commission.<font color=#57a892>NoCommission</font>()
# > - 不收任何手續費，此模型主要用來測試。
# > - 適用於 equities 與 futures。

# %% [markdown] cell 4
# ### Examples－CommissionModel
# 以下範例比較各種模型計算方法。

# %% [markdown] cell 5
# #### Import settings

# %% [code] cell 6
import pandas as pd
import datetime
import tejapi
import os
import warnings
from logbook import Logger, StderrHandler, INFO
warnings.filterwarnings('ignore')

# set log
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('CommissionModel')

# tej_key
os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"

# date
# set date
start='2022-12-01'
end='2022-12-31'
os.environ['mdate'] = '20221201 20221231'

tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)

# calendar
calendar_name='TEJ'

# bundle_name
bundle_name = 'tquant'

# ticker
os.environ['ticker'] = '1216 IR0001'

# ingest
# !zipline ingest -b tquant

# %% [code] cell 7
from zipline.finance import commission, slippage
from zipline.api import *

from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar

from zipline.utils.run_algo import (get_transaction_detail,
                                    get_record_vars)

# %% [markdown] cell 8
# #### 比較各種模型計算方法
# - 注意四個 `initialize` 函數的差別。
#   - `initialize_perdollar`：commission.PerTrade(cost=0.5)
#   - `initialize_pertrade`：commission.PerTrade(cost=0.5)
#   - `initialize_pershare`：commission.PerShare(cost=0.001, min_trade_cost=5.0)
#   - `initialize_Custom`：commission.Custom_TW_Commission(min_trade_cost=20, discount = 1.0, tax = 0.003)
# - 這個範例將滑價模型設定為：`slippage.FixedSlippage(spread=0.00)`。其中，spread 設定為 0，這樣會比較好觀察結果，因為滑價會導致成交價格改變。若有滑價則會使用考慮滑價後的價格計算手續費。

# %% [code] cell 9
def initialize_perdollar(context):
    context.i = 0
    context.tickers = ['1216']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage.FixedSlippage(spread=0.00))
    
    # set_commission
    set_commission(equities=commission.PerDollar(cost=0.001))
    
    set_benchmark(symbol('IR0001'))
    
def initialize_pertrade(context):
    context.i = 0
    context.tickers = ['1216']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage.FixedSlippage(spread=0.00))
    
    # set_commission
    set_commission(equities=commission.PerTrade(cost=0.5))
    
    set_benchmark(symbol('IR0001'))
    
def initialize_pershare(context):
    context.i = 0
    context.tickers = ['1216']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage.FixedSlippage(spread=0.00))
    
    # set_commission
    set_commission(equities=commission.PerShare(cost=0.001, min_trade_cost=5.0))
    
    set_benchmark(symbol('IR0001'))
    
def initialize_Custom(context):
    context.i = 0
    context.tickers = ['1216']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    set_slippage(slippage.FixedSlippage(spread=0.00))
    
    # set_commission
    set_commission(equities=commission.Custom_TW_Commission(min_trade_cost=20,
                                                            discount = 1.0,
                                                            tax = 0.003))
    
    set_benchmark(symbol('IR0001'))
    
def handle_data(context, data):

    if context.i == 0:
        for asset in context.asset:
            order_target(asset, 1000)
    if context.i == 2:
        for asset in context.asset:
            order_target(asset, 0)
            
    record(close=data.current(context.asset, 'close'))
    context.i += 1

capital_base = 1e5

# %% [code] cell 10
closing_price = tejapi.get('TWN/APIPRCD',
                           coid=['1216'],
                           opts={'columns':['mdate','coid','close_d']},
                           mdate={'gte':start_dt,'lte':end_dt },
                           paginate=True)

perdollar = run_algorithm(start=start_dt,
                          end=end_dt,
                          initialize=initialize_perdollar,
                          handle_data=handle_data,
                          capital_base=capital_base,
                          trading_calendar=get_calendar(calendar_name),
                          bundle=bundle_name)

pertrade = run_algorithm(start=start_dt,
                         end=end_dt,
                         initialize=initialize_pertrade,
                         handle_data=handle_data,
                         capital_base=capital_base,
                         trading_calendar=get_calendar(calendar_name),
                         bundle=bundle_name)

pershare = run_algorithm(start=start_dt,
                         end=end_dt,
                         initialize=initialize_pershare,
                         handle_data=handle_data,
                         capital_base=capital_base,
                         trading_calendar=get_calendar(calendar_name),
                         bundle=bundle_name)

Custom = run_algorithm(start=start_dt,
                       end=end_dt,
                       initialize=initialize_Custom,
                       handle_data=handle_data,
                       capital_base=capital_base,
                       trading_calendar=get_calendar(calendar_name),
                       bundle=bundle_name)

# %% [markdown] cell 11
# #### Explanations
# 12/1

# %% [code] cell 12
# 收盤價
closing_price[0:2]

# %% [markdown] cell 13
# ***PerDollar***
#
# 同樣在 12/1 下單一張統一（1216）股票，如果用 PerDollar 算法，費用就是下一個交易日 12/2 的收盤價 65 * 1000 股 * 0.001 = 65。

# %% [code] cell 14
# PerDollar算法：費用65元
perdollar['orders'][1]

# %% [markdown] cell 15
# ***PerTrade***
#
# 如果是 PerOrder，就固定是預先設定好的 0.5 元。

# %% [code] cell 16
# pertrade算法：費用0.5元
pertrade['orders'][1]

# %% [markdown] cell 17
# ***PerShare***
#
# PerShare 雖然設定一股抽 0.001，但是因為 1000 股 * 0.001 = 1 小於最低費用 min_trade_cost = 5，所以費用是 5。

# %% [code] cell 18
# pershare算法：費用5元
pershare['orders'][1]

# %% [markdown] cell 19
# ***Custom_TW_Commission***

# %% [code] cell 20
# 買進：65 * 1000 股 * 0.001425 = 93
Custom['orders'][1]

# %% [code] cell 21
# 賣出：64.6 * 1000 股 * 0.001425 + 64.6 * 1000 股 * 0.003 = 93 + 194 = 287
Custom['orders'][3]

# %% [markdown] cell 22
# [Go Top](#top)
