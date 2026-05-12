# -*- coding: utf-8 -*-
# Auto-generated from TQ_趨勢跟蹤策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ## Trading Strategy - TrendFollwing 
#
# 策略核心理念：
# - 趨勢追蹤策略是建立於當市場供需失衡時，股價通常會朝著同一方向持續移動一段時間的現象。
# - 策略旨在捕捉股價大部分的上漲與下跌段，而不試圖猜頭摸底。當價格開始沿著特定方向移動時，策略會順勢買進或放空股票，而在趨勢消失時賣出或回補股票。
# - 策略也會搭配追踪止利止損出場與持股比例配置調整，用以控制策略的波動度，保持可接受的風險。

# %% [markdown] cell 1
# ### 一. 環境設定 & import package

# %% [markdown] cell 2
# 1.1 輸入tejapi key

# %% [code] cell 3
import os
os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"

# %% [markdown] cell 4
# 1.2 import package

# %% [code] cell 5
import pandas as pd
import numpy as np
import pytz
# from datetime import datetime
import matplotlib.pyplot as plt
# import matplotlib

import zipline
from zipline.data import bundles
from zipline.utils.calendar_utils import get_calendar

from zipline.api import    *
from zipline.finance.commission import PerDollar,PerShare, PerTrade, PerContract
from zipline.finance.slippage import VolumeShareSlippage, FixedSlippage, VolatilityVolumeShare

from zipline.sources.TEJ_Api_Data import (get_Treasury_Return,
                                          get_Benchmark_Return)

from zipline.utils.run_algo import  (get_transaction_detail,
                                     get_record_vars)
import pyfolio as pf

plt.rcParams['axes.unicode_minus'] = False

# %% [markdown] cell 6
# ### 二、樣本&期間

# %% [markdown] cell 7
# 2.1 設定股票池與期間
# - 股票池：輸入81檔權值股與加權股價報酬指數(IR0001)
# - 期間：從2012-2022年

# %% [code] cell 8
# set stocklist
StockList = \
['1101', '1102', '1216', '1301', '1303', '1326', '1402', '1722', '2002', '2105', '2201', '2207', '2301',
 '2303', '2308', '2311', '2317', '2324', '2325', '2330', '2347', '2353', '2354', '2357', '2382', '2409',
 '2412', '2454', '2474', '2498', '2801', '2880', '2881', '2882', '2883', '2885', '2886', '2890', '2891',
 '2892', '2912', '3008', '3045', '3231', '3481', '3673', '3697', '4904', '5880', '6505', '2884', '4938',
 '2887', '2227', '9904', '3474', '2395', '2408', '1476', '2823', '2633', '5871', '2327', '3711', '2492',
 '5876', '9910', '2888', '6669', '2379', '6415', '3034', '1590', '8046', '2603', '2609', '2615', '8454',
 '3037', '6770', '1605', 'IR0001']

# set backtest period
start='2012-01-01'
end='2023-07-30'

start_dt, end_dt = pd.Timestamp(start, tz = pytz.utc), pd.Timestamp(end, tz = pytz.utc)

# %% [markdown] cell 9
# 2.2 樣本與期間設定輸入，並利用tejapi將開高低收量、調整股價資料綁入zipline
# - 綁入名稱為`tquant的資料庫`，並指定交易日為`台股交易日誌:TEJ_XTAI`

# %% [code] cell 10
os.environ['ticker'] = ' '.join(StockList)
os.environ['mdate'] = start+' '+end

# %% [code] cell 11
# !zipline ingest -b tquant

# %% [code] cell 12
# calendar
calendar_name='TEJ_XTAI'  
# bundle_name
bundle_name = 'tquant'

# %% [markdown] cell 13
# ### 三、建構交易策略
# 交易策略包含：進出場規則設定、持股配置、交易頻率，以及交易費用設定
# - **進出場規則**
#     - 趨勢filter
#         - 利用指標作為過濾器，判斷股票的趨勢方向。
#         - 正向趨勢條件：短均線ema(40)>長均線ema(80)。
#         - 負向趨勢條件：短均線ema(40)<長均線ema(80)。
#     - 進場rule
#         - Long Entry:
#             - 當趨勢為正且股價突破過去50日新高時，買進股票。            
#         - Short Entry:
#             - 當趨勢為負且股價跌破過去50日新低時，放空股票。            
#     - 出場rule
#         - Long Exit:
#             - 當趨勢方向轉空，短均線ema(40)<長均線ema(80)，賣出股票。
#             - 設定買進股票後，以價格高點下方3倍標準差的價格為追蹤停利停損點，當股價低於此點賣出股票。
#         - Short Exit:
#             - 當趨勢方向轉多，短均線ema(40)>長均線ema(80)，回補股票。
#             - 設定放空股票後，以價格低點上方3倍標準差的價格為追蹤停利停損點，當股價高於此點賣出股票。
#     
# - **持股配置**
#     - 旨要利用配置與調整持股權重，使每檔股票對策略每日風險的貢獻程度大致均等。
#     - 由於不同股票其價格波動的幅度差異很大，若以等權重配置會使策略的風險高度偏斜於波動大個股票。
#     - 本範例會利用近期股價波動的標準差來衡量風險，作為調整持股配置的依據。
#     
# - **交易頻率**
#     - 交易頻率設定為日頻。每日確認交易訊號，決定買賣股票與調整持股部位。    - 
#     
# - **交易費用**
#     - 設定單次買賣股票金額的0.29%為佣金費用
#     - 設定0%為滑價成本 
#    

# %% [markdown] cell 14
# 3.1 交易策略參數設定

# %% [code] cell 15
# These lines are for the dynamic text reporting
from IPython.display import display
import ipywidgets as widgets
out = widgets.HTML()
display(out)

"""
Model Settings
"""
starting_portfolio = 10e6
risk_factor = 1
stop_distance = 3
breakout_window = 50
vola_window = 40
slow_ma = 80
fast_ma = 40

'''
cost params setting
'''
commission_pct = 0.0029
slippage_volume_limit = 1.0
slippage_impact = 0

# %% [markdown] cell 16
# 3.2 交易策略初始化設定

# %% [code] cell 17
def initialize(context):

    # trading cost setting
    set_commission(PerDollar(cost=commission_pct))
    set_slippage(VolumeShareSlippage(volume_limit=slippage_volume_limit, price_impact=slippage_impact)) 
     
    # Make a list of all continuations
    bundle_data = bundles.load('tquant')
    context.universe = bundle_data.asset_finder.retrieve_all(bundle_data.asset_finder.equities_sids)#.remove(symbol('IR0001'))   
    
    # setting benchmark
    set_benchmark(symbol('IR0001')) 
    
    # We'll use these to keep track of best position reading 
    #Used to calculate stop points.
    context.highest_in_position = {tick: 0 for tick in context.universe}  
    context.lowest_in_position = {tick: 0 for tick in context.universe}    
    
    # Schedule the daily trading
    schedule_function(daily_trade, date_rules.every_day(), time_rules.market_close())
    
    # We'll just use this for the progress output
    # during the backtest. Doesn't impact anything.
    context.months = 0    
    
    # Schedule monthly report output
    schedule_function(
        func=report_result,
        date_rule=date_rules.month_start(),
        time_rule=time_rules.market_open()
    ) 
def report_result(context, data):
    context.months += 1
    today = zipline.api.get_datetime().date()
    # Calculate annualized return so far
    ann_ret = np.power(context.portfolio.portfolio_value / starting_portfolio, 
                   12 / context.months) - 1
    
    # Update the text
    out.value = """{} We have traded {} months  and the annualized return is {:.2%}""".format(today, context.months, ann_ret)

# %% [markdown] cell 18
# 3.3 持股配置與進出場規則設定

# %% [code] cell 19
def position_size(portfolio_value, std, point_value=1):
    risk_factor = 0.01
    target_variation = portfolio_value * risk_factor
    contract_variation = std * point_value
    contracts = target_variation / contract_variation
    return int(np.nan_to_num(contracts)) 

def daily_trade(context, data):    
    
    today = data.current_session.date()  
    todays_universe = context.universe
    
    hist_close = data.history(todays_universe, ['close','volume'], bar_count=slow_ma  + 1, frequency='1d')['close']
    hist_volume = data.history(todays_universe, ['close','volume'], bar_count=slow_ma  + 1, frequency='1d')['volume']    
    
    for _asset in todays_universe:
        
        h_close = hist_close.unstack()[_asset]
        h_trend = hist_close.unstack()[_asset].ewm(span=fast_ma).mean() > hist_close.unstack()[_asset].ewm(span=slow_ma).mean()
        h_volume = hist_volume.unstack()[_asset]
        h_std = hist_close.unstack().pct_change().iloc[-vola_window:].std()[_asset]*100 
        
        if _asset in context.portfolio.positions:
            
            p = context.portfolio.positions[_asset]
            stop_distance = 3               
            
            if p.amount > 0: # Position is long
                
                if context.highest_in_position[_asset] == 0: # First day holding the position
                    context.highest_in_position[_asset] = p.cost_basis
                else:
                    context.highest_in_position[_asset] = max(
                        h_close.iloc[-1], context.highest_in_position[_asset]
                    )                 
                # Calculate stop point
                stop = context.highest_in_position[_asset] - (h_std  * stop_distance)
                
                # Check if stop is hit
                if h_close.iloc[-1] < stop:
                    order_target(_asset, 0)
                    context.highest_in_position[_asset] = 0
                # Check if trend has flipped
                elif h_trend.iloc[-1] == False:        
                    order_target(_asset, 0)
                    context.highest_in_position[_asset] = 0

            elif p.amount <0: # Position is short
                
                if context.lowest_in_position[_asset] == 0: # First day holding the position
                    context.lowest_in_position[_asset] = p.cost_basis
                else:
                    context.lowest_in_position[_asset] = min(
                        h_close.iloc[-1], context.lowest_in_position[_asset]
                    )
                # Calculate stop point
                stop = context.lowest_in_position[_asset] + (h_std  * stop_distance)
                
                # Check if stop is hit
                if h_close.iloc[-1] > stop:
                    order_target(_asset, 0)
                    context.lowest_in_position[_asset] = 0
                # Check if trend has flipped
                elif h_trend.iloc[-1] == True:
                    order_target(_asset, 0)
                    context.lowest_in_position[_asset] = 0 
           
        else: # No position on
            if _asset==symbol('IR0001'): continue
                
            if h_trend.iloc[-1]: # Bull trend
                # Check if we just made a new high
                if h_close.iloc[-1] == h_close[-breakout_window:].max(): 
                
                    volume_to_trade = position_size(context.portfolio.portfolio_value, h_std)
                    order_value(_asset, volume_to_trade)                    
             
            else: # Bear trend
                # Check if we just made a new low
                if  h_close.iloc[-1] == h_close[-breakout_window:].min(): 
                    #contract = data.current(continuation, 'contract')

                    volume_to_trade = position_size(context.portfolio.portfolio_value, h_std)
                    order_value(_asset,-1* volume_to_trade)            
# %% [markdown] cell 20
# 3.4 取得Treasury資料，以第一銀行(5844)一年期定存利率作為無風險利率。

# %% [code] cell 21
treasury_returns = get_Treasury_Return(start = start_dt,
                                      end = end_dt,
                                      rate_type = 'Time_Deposit_Rate',                     
                                      term = '1y',
                                      symbol = '5844')
treasury_returns

# %% [markdown] cell 22
# 3.5 執行回測

# %% [code] cell 23
results = zipline.run_algorithm(
                start = pd.Timestamp('2018-06-01', tz='utc'), 
                end   = pd.Timestamp('2023-07-30', tz='utc'), 
                initialize=initialize,                 
                capital_base=starting_portfolio,  
                data_frequency = 'daily', 
                treasury_returns=treasury_returns,
                trading_calendar=get_calendar(calendar_name),
                bundle=bundle_name)
results.returns.cumsum().plot() 

# %% [markdown] cell 24
# ### 4.策略績效分析
# 4.1 利用pyfolio分析評估策略的風險與報酬表現

# %% [code] cell 25
import pyfolio as pf
import empyrical

bt_returns, bt_positions, bt_transactions = pf.utils.extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return

bt_returns.index = bt_returns.index.tz_localize(None).tz_localize('UTC')
bt_positions.index = bt_positions.index.tz_localize(None).tz_localize('UTC')
bt_transactions.index = bt_transactions.index.tz_localize(None).tz_localize('UTC')
benchmark_rets.index = benchmark_rets.index.tz_localize(None).tz_localize('UTC')


# Creating a Full Tear Sheet
pf.create_full_tear_sheet(bt_returns, positions=bt_positions, transactions=bt_transactions,
                          benchmark_rets=benchmark_rets,
                          #live_start_date='2022-01-01', 
                          round_trips=False)

# %% [markdown] cell 26
# 4.2 整理交易細節：positions／transactions／orders資訊

# %% [code] cell 27
positions, transactions, orders = get_transaction_detail(results)
positions

# %% [code] cell 28
transactions

# %% [code] cell 29
orders
