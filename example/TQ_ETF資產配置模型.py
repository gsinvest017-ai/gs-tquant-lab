# -*- coding: utf-8 -*-
# Auto-generated from TQ_ETF資產配置模型.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # ETF 資產配置策略

# %% [markdown] cell 1
# ## 大綱
#
# - ### 介紹
# - ### 資料集、標的與資料處理
# - ### 投組建立與回測

# %% [markdown] cell 2
# # 1. 介紹(投資靈感)

# %% [markdown] cell 3
# ### 方法論
# 基於投資組合分散的目的，投資於股票型、債券型及黃金ETF。
#
# **權重配置**
# - 0050：0.5。
# - 00679B：0.25。
# - 00635U：0.25。
# - 由於00679B的上市期間晚於0050，故在上市前的部位會以0050取代；00635U的上市期間晚於0050及00679B，故在上市前的部位會以0050及00679B取代。
#
# **再平衡**
# - 月初。
#
# **滑價**
# - 使用預設模型。
#
# ### 參考資料
# Trading Evolved: Anyone can Build Killer Trading Strategies in Python pp. 135-154

# %% [markdown] cell 4
# # 2. 資料集與標的

# %% [markdown] cell 5
# ## Imports & Settings

# %% [code] cell 6
import os
import pandas as pd
import tejapi
os.environ['TEJAPI_KEY'] = 'your key'
os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'

import zipline
from zipline import run_algorithm
from zipline.api import (order_target_percent,
                         symbol,
                         schedule_function,
                         date_rules,
                         time_rules,
                         set_benchmark,
                         get_datetime)
from zipline.utils.calendar_utils import get_calendar 

from matplotlib import pyplot as plt
import pandas as pd
import empyrical as ep
from logbook import Logger, StderrHandler, INFO

import warnings
warnings.filterwarnings('ignore')

# %% [code] cell 7
# calendar
calendar_name='TEJ'

# bundle_name
bundle_name = 'tquant'

# set date
start='2005-01-01'
end='2023-08-25'


# 由文字型態轉為Timestamp，供回測使用
tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)

# 設定os.environ['mdate'] = start+' '+end，供ingest bundle使用
os.environ['mdate'] = start+' '+end

pd.set_option('display.max_rows', 80)

# 設定log顯示方式
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [code] cell 8
# 取得start當天所有ETF的公司碼
from zipline.sources.TEJ_Api_Data import get_universe
pool = get_universe(start, end, stktp_e=['ETF','Foreign ETF'])

# %% [code] cell 9
# 設定os.environ['ticker']=公司碼，供後續ingest bundle用。

os.environ['ticker'] = ' '.join(pool+['IR0001'])

# %% [markdown] cell 10
# ## Ingest

# %% [code] cell 11
# !zipline ingest -b tquant

# %% [markdown] cell 12
# ## 投資標的

# %% [code] cell 13
# set universe and weight
securities = {
                '0050': 0.5,     # 市值型：元大台灣卓越50證券投資信託基金（臺灣50指數 FTSE TWSE Taiwan 50 Index）
                '00679B': 0.25,  # 債券型：元大美國政府20年期(以上)債券證券投資信託基金（ICE美國政府20+年期債券指數 (ICE U.S.Treasury 20+ Year Bond Index）
                '00635U': 0.25   # 期貨型：元大標普高盛黃金ER指數股票型期貨信託基金（標普高盛黃金超額回報指數 S&P GSCI Gold Excess Return Index）
            }

# %% [markdown] cell 14
# # 3. 投組建立與回測

# %% [code] cell 15
# %matplotlib inline
def initialize(context):
    # Securities and target weights
    context.securities = securities   
    set_benchmark(symbol('IR0001'))
        
    # Schedule rebalance for once a month
    schedule_function(rebalance,
                      date_rules.month_start(),
                      time_rules.market_open())
    
def rebalance(context, data):
    
    can_trade_sec = []
    
#     Loop through the securities    
    for sec, weight in context.securities.items():
        try:
            sym = symbol(sec)
            # Check if we can trade
            if data.can_trade(sym):
                # construct a can trade list
                can_trade_sec.append(sec)
        except:
            log.info('"' + str(sec) + '"' + ' does not exist on bundle: ' + get_datetime().strftime('%Y-%m-%d'))
        
    total_weight = sum(value for key, value in context.securities.items() if key in can_trade_sec)

    if len(can_trade_sec)>0:
        log.info(get_datetime().strftime('%Y-%m-%d') + ' can trade sec:' + str(set(can_trade_sec)))
    
#     Start trading
    for sec in can_trade_sec:
        sym = symbol(sec)
        weight = context.securities[sec]
        # Reset the weight
        order_target_percent(sym, weight * ((1-total_weight) * 1 / total_weight + 1))    
            
def analyze(context, perf):
    
#     longs_count
    fig, ax = plt.subplots(figsize=(18, 4))
    
    ax.plot(perf['longs_count'], 
            linestyle='-', 
            color='black',
            linewidth=3.0)

    ax.set_title(label='Longs count')
    ax.legend()
    ax.grid(True)
        
#     MDD
    fig, ax = plt.subplots(figsize=(18, 6))
 
    window = 252
 
    mdd = ep.stats.roll_max_drawdown(perf['returns'],
                                     window=window)
    mdd_x = mdd.sort_index().round(10).idxmin()
    mdd_y = mdd.min()

    ax.plot(mdd, 
        label='portfolio(MDD = {})'.format(round(ep.max_drawdown(perf['returns']),4)), 
        linestyle='-', 
        color='black',
        linewidth=3.0)
    
   
    benchmark_mdd = ep.stats.roll_max_drawdown(perf['benchmark_return'],
                                               window=window)
    benchmark_mdd_x = benchmark_mdd.sort_index().round(10).idxmin()
    benchmark_mdd_y = benchmark_mdd.min()

    ax.plot(benchmark_mdd, 
        label='benchmark(MDD = {})'.format(round(ep.max_drawdown(perf['benchmark_return']),4)), 
        linestyle='-.', 
        color='gray',
        linewidth=3.0)
        
    ax.set_title(label='{} days max drawdown'.format(window))
    ax.legend()
    ax.grid(True)
    
#     roll_sharpe_ratio
    fig, ax = plt.subplots(figsize=(18, 6))
    
    rolling_sharpe = ep.stats.roll_sharpe_ratio(perf['returns'],
                                                window=21 * 6)
    
    portfolio_mean_sharpe_ratio = rolling_sharpe.mean()
    
    
    benchmark_rolling_sharpe = ep.stats.roll_sharpe_ratio(perf['benchmark_return'],
                                                          window=21 * 6)
    
    benchmark_mean_sharpe_ratio = benchmark_rolling_sharpe.mean()
    
    ax.plot(rolling_sharpe, 
            label='portfolio(mean = {})'.format(round(portfolio_mean_sharpe_ratio,4)), 
            linestyle='-', 
            color='black',
            linewidth=3.0)
    
    ax.plot(benchmark_rolling_sharpe, 
        label='benchmark(mean = {})'.format(round(benchmark_mean_sharpe_ratio,4)), 
        linestyle='-.', 
        color='gray',
        linewidth=3.0)

    ax.axhline(0.0, color="black", linestyle="-", lw=1)
    
    ax.set_title(label='Rolling Sharpe ratio (6-month)')
    ax.legend()
    ax.grid(True)

# Fire off backtest
result = run_algorithm(start=start_dt,            
                       end=end_dt,                          
                       initialize=initialize,
                       analyze=analyze,
                       capital_base=1e7,
                       data_frequency='daily',
                       bundle=bundle_name,
                       trading_calendar=get_calendar(calendar_name))

print("Ready to analyze result.")

# %% [markdown] cell 16
# ## Pyfolio

# %% [code] cell 17
import pyfolio as pf
from pyfolio.utils import extract_rets_pos_txn_from_zipline
from pyfolio.txn import make_transaction_frame
import empyrical

# %% [code] cell 18
# Extract returns, positions, transactions and leverage from the backtest data structure returned by zipline.
# TradingAlgorithm.run().
returns, positions, transactions = extract_rets_pos_txn_from_zipline(result)

# %% [code] cell 19
benchmark_rets = result['benchmark_return']

# %% [code] cell 20
# The data must have a **tz-aware DateTimeIndex set to UTC**, with a time of **0:00**, 
# otherwise some plots won't be able to be generated.
returns.index = returns.index.tz_localize(None).tz_localize('UTC')
positions.index = positions.index.tz_localize(None).tz_localize('UTC')
transactions.index = transactions.index.tz_localize(None).tz_localize('UTC')
benchmark_rets.index = benchmark_rets.index.tz_localize(None).tz_localize('UTC')

# %% [code] cell 21
pf.tears.create_full_tear_sheet(returns=returns,
                                positions=positions,
                                transactions=transactions,
                                benchmark_rets=benchmark_rets,
                                live_start_date='20170202'
                               )
