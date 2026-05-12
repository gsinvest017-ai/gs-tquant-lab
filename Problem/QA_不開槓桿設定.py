# -*- coding: utf-8 -*-
# Auto-generated from QA_不開槓桿設定.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ## 問題集:
#
# 1. 如何設定不以借貸方式買進股票。
#
# ## 注意:
# 前方為策略建立，解決方法請見 [5](#5), [6](#6)。

# %% [markdown] cell 1
# 策略：
#
# - 利用Fetch Tej Api取得PB（市價淨值比）資料。
#   [APIPRCD](http://10.10.10.66/columns.html?idCode=TWN/APIPRCD)
# - 當PB<1時買入1000股，PB>=1時賣出1000股。

# %% [markdown] cell 2
# # 1. Bundle

# %% [markdown] cell 3
# ## 1.1 Imports & Settings

# %% [code] cell 4
import pandas as pd
import tejapi
import time
import os

# tej_key-------------------------------------------
os.environ['TEJAPI_KEY'] = 'your key'
os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'

# date----------------------------------------------
# set date
start='2020-01-01'
end='2022-12-30'
os.environ['mdate'] = start+' '+end 

tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)
# calendar------------------------------------------
calendar_name='TEJ'  # US equities  XTAI

# bundle_name---------------------------------------
bundle_name = 'tquant'

# %% [code] cell 5
import warnings
warnings.filterwarnings('ignore')

# %% [code] cell 6
from zipline.api import  *

from zipline import run_algorithm  
from zipline.finance import commission, slippage

from zipline import run_algorithm

from zipline.utils.run_algo import  (get_transaction_detail,
                                     get_record_vars)

from zipline.sources.TEJ_Api_Data import (get_Treasury_Return,
                                          get_Benchmark_Return)


from logbook import Logger, StderrHandler, INFO, set_datetime_format
import numpy as np
from pytz import timezone
import re

# %matplotlib inline
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style('whitegrid')

from zipline.utils.calendar_utils import get_calendar
from zipline.data.data_portal import DataPortal

# %% [code] cell 7
# set_datetime_format('local') # 更改時區和時間戳記的格式
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f%z}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()

log = Logger('Algorithm')

# %% [markdown] cell 8
# ## 1.2 樣本公司清單

# %% [code] cell 9
StockList = \
['1101', '1102', '1216', '1301', '1303', '1326', '1402', '1722', '2002', '2105', '2201', '2207', '2301',
 '2303', '2308', '2311', '2317', '2324', '2325', '2330', '2347', '2353', '2354', '2357', '2382', '2409',
 '2412', '2454', '2474', '2498', '2801', '2880', '2881', '2882', '2883', '2885', '2886', '2890', '2891',
 '2892', '2912', '3008', '3045', '3231', '3481', '3673', '3697', '4904', '5880', '6505', '2884', '4938',
 '2887', '2227', '9904', '3474', '2395', '2408', '1476', '2823', '2633', '5871', '2327', '3711', '2492',
 '5876', '9910', '2888', '6669', '2379', '6415', '3034', '1590', '8046', '2603', '2609', '2615', '8454',
 '3037', '6770', '1605', 'IR0001']

coid = ' '.join(StockList)
os.environ['ticker'] = coid

# %% [markdown] cell 10
# ## 1.3 ingest

# %% [code] cell 11
# !zipline ingest -b tquant

# %% [code] cell 12
# !zipline bundles

# %% [markdown] cell 13
# # 2. 建構回測演算法

# %% [code] cell 14
commission_cost = 0.001425 + 0.003 / 2
shares = 1000

# %% [markdown] cell 15
# ### fetch_tej_api()
# - 為TEJ參考`zipline.api.fetch_csv()`開發的方法，該方法可將Tej-Tool-Api的資料經過整理後匯入`DataPortal`中，後續可以利用`data.current()`取出資料並供策略開發使用。
#
# ##### pre_func及post_func
# - pre_func：
#   - A callback function to allow preprocessing the raw data returned from Tej-Tool-Api `before dates are paresed or symbols are mapped`.
#   - 與Tej-Tool-Api撈出的資料基本相同。
# - post_func：
#   - A callback function to allow postprocessing of the data `after dates（轉成datetime格式並轉換時區）and symbols have been mapped（利用symbol查zipline.assets.Asset物件）`
# - 以下print出`pre_func`及`post_func`兩階段的資料長相供參考。

# %% [code] cell 16
def pre_func(df):
    print('pre_func')
    print(df)
    print('-----------------------------------------------') 
    return df

def post_func(df):
    print('post_func')    
    print(df)
    return df

# %% [code] cell 17
def initialize(context):

    context.tickers = ['2880','2887','2882']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))

#     fetch_tej_api
    fetch_tej_api(
                  start=start_dt,
                  end=end_dt,
                  columns=['PBR_TWSE'],
                  symbols=context.tickers,
                  pre_func=pre_func,
                  post_func=post_func
    )
    
def handle_data(context, data):
    
    for asset in context.asset:
        if data.current(asset, 'PBR_TWSE') < 1:
            order(asset, 1000)
            
        elif data.current(asset, 'PBR_TWSE') >= 1:
            order(asset, -1000)

            
    record(close=data.current(context.asset, 'close'),
           PB=data.current(context.asset, 'PBR_TWSE'))

def analyze(context, perf):
    
    fig = plt.figure(figsize=(16, 12))
    
    # First chart(累計報酬)
    ax = fig.add_subplot(411) 
    ax.set_title('Strategy Results') 
    ax.plot(perf['algorithm_period_return'], linestyle='-', 
                label='algorithm period return', linewidth=3.0)
    ax.plot(perf['benchmark_period_return'], linestyle='-', 
                label='benchmark period return', linewidth=3.0)
    ax.legend()
    ax.grid(False)
    
    # Second chart(PBR)
    ax = fig.add_subplot(412)
    ax.set_title('PB')         
    PB = pd.concat([df.to_frame(d) for d, df in perf['PB'].dropna().items()],axis=1).T
    PB.columns = ['PB-'+ re.findall(r"\[(.+)\]", str(col))[0] for col in PB.columns]
    
    ax.plot(PB, linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend(PB.columns)
    ax.grid(False)

    # Third chart(ending_cash)->觀察是否超買
    ax = fig.add_subplot(413)
    ax.plot(perf['ending_cash'], 
            label='ending_cash', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(False)

    # Forth chart(shorts_count)->觀察是否放空
    ax = fig.add_subplot(414)
    ax.plot(perf['shorts_count'], 
            label='shorts_count', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(False)
    
capital_base = 1e7

# %% [markdown] cell 18
# # 3. 取得Treasury資料

# %% [markdown] cell 19
# 以下使用第一銀行(5844)一年期定存利率作為無風險利率。

# %% [code] cell 20
treasury_returns = get_Treasury_Return(start = start_dt,
                                      end = end_dt,
                                      rate_type = 'Time_Deposit_Rate',                     
                                      term = '1y',
                                      symbol = '5844')
treasury_returns

# %% [markdown] cell 21
# # 4. 執行回測

# %% [code] cell 22
start_t = time.time()

performance = run_algorithm(start=start_dt,
                            end=end_dt,
                            initialize=initialize,
                            handle_data=handle_data,
                            capital_base=capital_base,
                            analyze=analyze,
                            treasury_returns=treasury_returns,
                            trading_calendar=get_calendar(calendar_name),
                            bundle=bundle_name)

print('Duration: {:.2f}s'.format(time.time() - start_t))

# %% [code] cell 23
performance.T

# %% [markdown] cell 24
# # 5. 不開槓桿解法
# <a id = "5"></a>

# %% [markdown] cell 25
# ## Case1
# 上述案例中的ending_cash曾經<0（花額外的現金），且shorts_count曾經>0（有放空），有沒有辦法控制?

# %% [markdown] cell 26
# #### 超買：
# - 當Zipline做多股票且該股票成交量足夠的情形下，就算現金不足，仍會融資進行購買。
# - 若要避免超買，則需在交易前（t=0）進行試算，若股款（t=0）>帳上現金（t=0，可利用`context.portfolio.cash`取得），則不下單或減少下單數量（本例減少下單數量）。而股款須利用實際交易價格（t=1）及下單股數計算。
# - 根據Zipline交易機制：當演算法在某一天（t=0）下單時，該訂單會在下一個交易日（t=1）成交。而利用`data.current(context.asset, 'close')`取得的收盤價為t=0期的收盤價，而非實際交易價格（t=1）。
# - 若要取得真正交易價格可以透過`fetch_tej_api()`，並利用`pre_func()`將收盤價（Close）往前平移一期。
#
# #### 超賣：
# - 若賣單的絕對數量>帳上該股票數量時，Zipline會進行放空。
# - 若要避免超賣，則需先判斷交易前（t=0）帳上股數（利用`context.portfolio.positions[asset].amount`取得該asset目前帳上股數）是否足夠賣出，若不夠賣則不下單或減少下單數量（本例減少下單數量）。

# %% [code] cell 27
def pre_func_over(df):
    print('before pre_func')
    print(df)
    print('-----------------------------------------------') 
    
#     將收盤價（Close）往前平移一期
    df=df.sort_values(by=['coid','mdate'])
    df['Close_shift']=df.groupby('coid')['Close'].shift(-1)
    df.rename(columns={'PBR_TWSE':'PB'},inplace=True)
    
    print('after pre_func')
    print(df)    
    return df

# %% [code] cell 28
def initialize_over(context):

    context.tickers = ['2880','2887','2882']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    context.adj_ratio = 1
    
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))

#     fetch_tej_api
    fetch_tej_api(
                  start=start_dt,
                  end=end_dt,
                  columns=['Close','PBR_TWSE'],
                  symbols=context.tickers,
                  pre_func=pre_func_over,
#                   post_func=post_func
    )
    
def handle_data_over(context, data):
    
#     交易價格              
    transaction_price=data.current(context.asset, 'Close_shift') 
    
#     預算    
    payment=sum(transaction_price * shares * (1+commission_cost))
            
    for asset in context.asset:
        
#         PB<1
        if data.current(asset, 'PB') < 1:
            
#             PB<1且預算夠的時候，直接買             
            if context.portfolio.cash >= payment:
                    order(asset, shares)
                    
#             PB<1且預算不夠的時候，降低購買量 
            elif context.portfolio.cash < payment:
                context.adj_ratio = context.portfolio.cash / payment
                order(asset, shares * context.adj_ratio)

#         PB>=1                
        elif data.current(asset, 'PB') >= 1:
#             PB>=1且股票數量夠的時候，直接賣          
            if context.portfolio.positions[asset].amount >= shares:
                order(asset, -shares)
            
#             PB>=1且股票數量不夠的時候，將帳上所有部位清掉                 
            elif context.portfolio.positions[asset].amount < shares:
                order(asset, context.portfolio.positions[asset].amount)  

    record(close=data.current(context.asset, 'close'),
           close_shift=data.current(context.asset, 'Close_shift'),
           adj_ratio=context.adj_ratio,
           PB=data.current(asset, 'PB'),
           payment=payment)

def analyze_over(context, perf):
    
    fig = plt.figure(figsize=(16, 12))
    
    # First chart(累計報酬)
    ax = fig.add_subplot(311) 
    ax.set_title('Strategy Results') 
    ax.plot(perf['algorithm_period_return'], linestyle='-', 
                label='algorithm period return', linewidth=3.0)
    ax.plot(perf['benchmark_period_return'], linestyle='-', 
                label='benchmark period return', linewidth=3.0)
    ax.legend()
    ax.grid(False)
    
    # Second chart(ending_cash)->觀察是否超買
    ax = fig.add_subplot(312)
    ax.plot(perf['ending_cash'], 
            label='ending_cash', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(False)

    # Third chart(shorts_count)->觀察是否放空
    ax = fig.add_subplot(313)
    ax.plot(perf['shorts_count'], 
            label='shorts_count', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(False)
    
    
capital_base = 1e7

# %% [code] cell 29
start_t = time.time()

performance_over = run_algorithm(start=start_dt,
                                 end=end_dt,
                                 initialize=initialize_over,
                                 handle_data=handle_data_over,
                                 capital_base=capital_base,
                                 analyze=analyze_over,
                                 treasury_returns=treasury_returns,
                                 trading_calendar=get_calendar(calendar_name),
                                 bundle=bundle_name)

print('Duration: {:.2f}s'.format(time.time() - start_t))

# %% [code] cell 30
performance_over.T

# %% [code] cell 31
# 現金餘額<0的筆數=0，代表沒有超買
len(performance_over[performance_over['ending_cash']<0])

# %% [code] cell 32
# 放空部位>0的筆數=0，代表沒有放空
len(performance_over[performance_over['shorts_count']>0])

# %% [markdown] cell 33
# <a id = "6"></a>
#
# ## Case2

# %% [markdown] cell 34
# #### 策略
#
# - 利用Fetch Tej Api取得PB資料。
# - 選擇買入股票池中PB<1的公司並等權重配置（權數 = 1/欲買入公司數，使用`order_target_percent()`下單），PB>=1時清掉帳上部位。
#
# #### 問題
# - 根據Zipline交易機制：當演算法在某一天（t=0）下單時，該訂單會在下一個交易日（t=1）成交。因此，利用`order_target_percent()`下單時，會利用t=0期的收盤價計算下一個交易日（t=1）要購買多少股數。
# - 所以當t=1期的收盤價>t=0期的收盤價時就有可能超買，反之則會超賣。
#
# #### 超買
# - 下多單利用`order_target_percent()`：Place an order to adjust a position to a target percent of the current portfolio value. If the position doesn’t already exist, this is equivalent to placing a new order. If the position does exist, this is equivalent to placing an order for the difference between the target percent and the current percent.
# - 為了不超買，這邊將權數 * `0.9 （adj_ratio）`，形成緩衝避免買超過。
#
#
# #### 超賣
# - 下賣單利用`order_target()`：Place an order to adjust a position to a target number of shares. If the position doesn’t already exist, this is equivalent to placing a new order. If the position does exist, this is equivalent to placing an order for the difference between the target number of shares and the current number of shares.
# - 若用`order_target_percent(asset,0)`，會有超賣可能性；所以這邊利用`order_target(asset, 0)`強制將持有股數設定為0。
#
#
# #### 大部分回測時所需要的設定方法都可以從zipline.api找到，以下列僅列出有使用的api：
# `data.can_trade()`：判斷股票是否可被交易。

# %% [code] cell 35
def initialize_over2(context):

    context.tickers = ['2880','2887','2882','1101','2330']
    context.asset = [symbol(ticker) for ticker in context.tickers]      
    context.adj_ratio = 0.9
       
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerDollar(cost=commission_cost))
    set_benchmark(symbol('IR0001'))

#     fetch_tej_api
    fetch_tej_api(
                  start=start_dt,
                  end=end_dt,
                  columns=['Close','PBR_TWSE'],
                  symbols=context.tickers,
                  pre_func=pre_func_over,
#                   post_func=post_func
    )
    
def handle_data_over2(context, data):

#     建立賣出清單
    context.sell_list=[]
    for asset in context.asset:
        if (data.current(asset, 'PB') >= 1) & (data.can_trade(asset)):
            context.sell_list.append(asset)    
        
    for asset in context.sell_list:
        order_target(asset, 0)

#     建立買入清單
    context.long_list=[]
    for asset in context.asset:
        if (data.current(asset, 'PB') < 1) & (data.can_trade(asset)):
            context.long_list.append(asset)    
            
    for asset in context.long_list:
        order_target_percent(asset, 1 / len(context.long_list) * context.adj_ratio)    
        
    record(close=data.current(context.asset, 'close'),
           close_shift=data.current(context.asset, 'Close_shift'),
           long_list=context.long_list,
           len_long_list=len(context.long_list),
           sell_list=context.sell_list,
           len_sell_list=len(context.sell_list),
           PB=data.current(asset, 'PB'))

def analyze_over2(context, perf):
    
    fig = plt.figure(figsize=(16, 12))
    
    # First chart(累計報酬)
    ax = fig.add_subplot(311) 
    ax.set_title('Strategy Results') 
    ax.plot(perf['algorithm_period_return'], linestyle='-', 
                label='algorithm period return', linewidth=3.0)
    ax.plot(perf['benchmark_period_return'], linestyle='-', 
                label='benchmark period return', linewidth=3.0)
    ax.legend()
    ax.grid(False)
    
    # Second chart(ending_cash)->觀察是否超買
    ax = fig.add_subplot(312)
    ax.plot(perf['ending_cash'], 
            label='ending_cash', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(True)

    # Third chart(shorts_count)->觀察是否放空
    ax = fig.add_subplot(313)
    ax.plot(perf['shorts_count'], 
            label='shorts_count', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(True)
    
    
capital_base = 1e7

# %% [code] cell 36
start_t = time.time()

performance_over2 = run_algorithm(start=start_dt,
                                 end=end_dt,
                                 initialize=initialize_over2,
                                 handle_data=handle_data_over2,
                                 capital_base=capital_base,
                                 analyze=analyze_over2,
                                 treasury_returns=treasury_returns,
                                 trading_calendar=get_calendar(calendar_name),
                                 bundle=bundle_name)

print('Duration: {:.2f}s'.format(time.time() - start_t))

# %% [code] cell 37
performance_over2.T

# %% [code] cell 38
# 現金餘額<0的筆數=0，代表沒有超買
len(performance_over2[performance_over2['ending_cash']<0])

# %% [code] cell 39
# 放空部位>0的筆數=0，代表沒有放空
len(performance_over2[performance_over2['shorts_count']>0])
