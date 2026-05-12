# -*- coding: utf-8 -*-
# Auto-generated from TQ_德伍．卻斯動能策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import pandas as pd
import numpy as np
import tejapi
import os
import json
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Arial'
tej_key = 'YOUR KEY HERE'  # Replace with your actual TEJ API key
tejapi.ApiConfig.api_key = tej_key
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
os.environ['TEJAPI_KEY'] = tej_key


from zipline.sources.TEJ_Api_Data import get_universe
import TejToolAPI
from zipline.data.run_ingest import simple_ingest
from zipline.api import set_slippage, set_commission, set_benchmark,  symbol,  record, order_target_percent
from zipline.finance import commission, slippage
from zipline import run_algorithm

# %% [code] cell 1
start_date = '2010-01-01'; end_date = '2025-05-27'

pool = get_universe(start = start_date,
                      end = end_date,
                      mkt_bd_e = ['TSE', 'OTC'],
                      stktp_e = ['Common Stock-Foreign','Common Stock'])

columns = ['coid', 'roi', 'mktcap', 'r505', 'r104', 'per', 'close_d', 'r316']

start_dt = pd.Timestamp(start_date, tz = 'UTC')
end_dt = pd.Timestamp(end_date, tz = "UTC")

data_use = TejToolAPI.get_history_data(start = start_dt,
                                    end = end_dt,
                                    ticker = pool + ['IR0001'],
                                    fin_type = ['Q', 'TTM'], 
                                    columns = columns,
                                    transfer_to_chinese = False)

# %% [code] cell 2
data_use['mdate'] = pd.to_datetime(data_use['mdate'])
data_use = data_use.sort_values('mdate')
data_use['avg_market_cap'] = data_use.groupby('mdate')['Market_Cap_Dollars'].transform('mean')
data_use['avg_debt_ratio'] = data_use.groupby('mdate')['Liabilities_Ratio_Q'].transform('mean')

data_use['EPS_5y_ago'] = data_use.groupby('coid')['Net_Income_Per_Share_Q'].shift(252 * 5)
data_use['EPS_CAGR_5Y'] = ((data_use['Net_Income_Per_Share_Q'] / data_use['EPS_5y_ago']) ** (1/5)) - 1


# 以 126 個交易日作為近 6 個月（可依台股調整為 120～130 天）
data_use['ret_6m'] = data_use.groupby('coid')['Close'].transform(lambda x: x / x.shift(126) - 1)

# 從 df 中抽出大盤（IR0001）的每日報酬率
market_ret = data_use[data_use['coid'] == 'IR0001'][['mdate', 'ret_6m']].rename(columns={'ret_6m': 'market_ret_6m'})

# 把 market_ret 併回所有資料（用日期對齊）
data_use = data_use.merge(market_ret, on='mdate', how='left')
data_use['RS_ratio_6m'] = data_use['ret_6m'] / data_use['market_ret_6m']
data_use['mdate_shifted'] = data_use.groupby('coid')['mdate'].shift(1)

# %% [code] cell 3
def compute_stock(date, data):
    
    df = data[data['mdate_shifted'] == pd.to_datetime(date)].reset_index(drop = True)

    set_1 = set(df[df['Market_Cap_Dollars'] >= df['avg_market_cap']]['coid'])

    set_2 = set(df[df['EPS_CAGR_5Y'] >= .1]['coid'])

    set_3 = set(df[df['Net_Income_Per_Share_TTM'] >= .15]['coid'])

    set_4 = set(df[df['Liabilities_Ratio_Q'] < df['avg_debt_ratio']]['coid'])

    set_5 = set(df[(df['PER_TWSE'] <= df['EPS_CAGR_5Y']*100 * 2.0)]['coid'])

    set_6 = set(df[(df['RS_ratio_6m'] > 1)]['coid'])

    tickers = list(set_1 & set_2 &  set_3 & set_4 & set_6 & set_5)
    print(f'set1:{len(set_1)}, set2:{len(set_2)},set3:{len(set_3)},set4:{len(set_4)},set5:{len(set_5)},set6:{len(set_6)}')

    sets = [len(set_1), len(set_2),len(set_3), len(set_4),len(set_5), len(set_6)]

    return tickers, sets

# sets = [set_1, set_2,set_3, set_4,set_5, set_6]
# %% [code] cell 4
pools = pool + ['IR0001']

start_ingest = start_date.replace('-', '')
end_ingest = end_date.replace('-', '')

print(f'開始匯入回測資料')
simple_ingest(name = 'tquant' , tickers = pools , start_date = start_ingest , end_date = end_ingest)
print(f'結束匯入回測資料')

# %% [code] cell 5
def initialize(context, re = 30):
    set_slippage(slippage.VolumeShareSlippage(volume_limit=1, price_impact=0.01))
    set_commission(commission.Custom_TW_Commission())
    set_benchmark(symbol('IR0001'))

    context.i = 0
    context.state = False
    context.order_tickers = []
    context.last_tickers = []
    context.rebalance = re
    context.set1 = 0
    context.set2 = 0
    context.set3 = 0
    context.set4 = 0
    context.set5 = 0
    context.set = 0

    context.dic = {}

def handle_data_1(context, data):
    # 避免前視偏誤，在篩選股票下一交易日下單
    if context.state == True:

        for i in context.last_tickers:
            if i not in context.order_tickers:
                order_target_percent(symbol(i), 0)


        for i in context.order_tickers:
            order_target_percent(symbol(i), 1.0 / len(context.order_tickers))
            context.dic[i] = data.current(symbol(i), 'price')

        record(p = context.dic)
        context.dic = {}

        print(f"下單日期：{data.current_dt.date()}, 擇股股票數量：{len(context.order_tickers)}, Leverage: {context.account.leverage}")
        context.last_tickers = context.order_tickers.copy()
        context.state = False

    backtest_date = data.current_dt.date()

    if context.i % context.rebalance == 0:
        context.state = True
        context.order_tickers = compute_stock(date = backtest_date, data = data_use)[0]
        context.set = compute_stock(date = backtest_date, data = data_use)[1]


    record(tickers = context.order_tickers)
    record(Leverage = context.account.leverage)
    
    if context.account.leverage > 1.2:
        print(f'{data.current_dt.date()}: Over Leverage, Leverage: {context.account.leverage}')
        for i in context.order_tickers:
            order_target_percent(symbol(i), 1 / len(context.order_tickers))

    context.i += 1
    lengths = [s for s in context.set]

    record(
        ticker_num = len(context.order_tickers),
        set1_len = lengths[0],
        set2_len = lengths[1],
        set3_len = lengths[2],
        set4_len = lengths[3],
        set5_len = lengths[4],
        set6_len = lengths[5]
    )

    

# %% [code] cell 6
def analyze(context, perf):

  plt.style.use('ggplot')

  # 第一張圖：策略績效與報酬
  fig1, axes1 = plt.subplots(nrows=2, ncols=1, figsize=(18, 10), sharex=False)

  axes1[0].plot(perf.index, perf['algorithm_period_return'], label='Strategy')
  axes1[0].plot(perf.index, perf['benchmark_period_return'], label='Benchmark')
  axes1[0].bar(perf.index, perf['algorithm_period_return'] - perf['benchmark_period_return'],
              label='Excess return', color='g', alpha=0.4)
  axes1[0].set_title("Backtest Results")
  axes1[0].legend()

  axes1[1].plot(perf.index, perf['returns'], label='Strategy')
  axes1[1].plot(perf.index, perf['benchmark_return'], label='Benchmark')
  axes1[1].set_title("Daily Returns")
  axes1[1].legend()

  plt.tight_layout()
  plt.show()

  # 第二張圖：選股結構與篩選條件
  fig2, axes2 = plt.subplots(nrows=2, ncols=1, figsize=(18, 10), sharex=False)

  axes2[0].plot(perf.index, perf['ticker_num'], label='Ticker Number')
  axes2[0].set_title("Ticker Number")
  axes2[0].legend()

  axes2[1].plot(perf.index, perf['set1_len'], label='Set1: mktcap >= ave')
  axes2[1].plot(perf.index, perf['set2_len'], label='Set2: EPS CAGR >= 10%')
  axes2[1].plot(perf.index, perf['set3_len'], label='Set3: ROE >= 15%')
  axes2[1].plot(perf.index, perf['set4_len'], label='Set4: debt ratio < ave')
  axes2[1].plot(perf.index, perf['set5_len'], label='Set5: PER <= CAGR x2')
  axes2[1].plot(perf.index, perf['set6_len'], label='Set6: RS ratio > 1')
  axes2[1].set_title("Six Conditions Filtered Count")
  axes2[1].legend(loc='upper right')

  plt.tight_layout()
  plt.show()


results = run_algorithm(
            start = pd.Timestamp('2016-01-01', tz = 'utc'),
            end = pd.Timestamp(end_date, tz = 'utc'),
            initialize = initialize,
            handle_data = handle_data_1,
            analyze = analyze,
            bundle = 'tquant',
            capital_base = 1e5)

# %% [code] cell 7
plt.plot(results['period_open'], results['ending_cash'])
plt.title('ending cash')
plt.show()

# %% [code] cell 8
import pyfolio
from pyfolio.utils import extract_rets_pos_txn_from_zipline
plt.rcParams['font.sans-serif'] = ['Arial', 'Noto Sans CJK TC', 'SimHei']  
plt.rcParams['axes.unicode_minus'] = False  
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return
pyfolio.tears.create_full_tear_sheet(returns=returns,
                                     positions=positions,
                                     transactions=transactions,
                                     benchmark_rets=benchmark_rets
                                    )

# %% [code] cell 9
def handle_data_ir0001(context, data):
    if context.i == 0:
        order_target_percent(symbol('IR0001'), 1.0)

    context.i += 1

def ana(context, perf):
    pass

results = run_algorithm(
            start = pd.Timestamp('2016-01-01', tz = 'utc'),
            end = pd.Timestamp(end_date, tz = 'utc'),
            initialize = initialize,
            handle_data = handle_data_ir0001,
            analyze = ana,
            bundle = 'tquant',
            capital_base = 1e5)


import pyfolio
from pyfolio.utils import extract_rets_pos_txn_from_zipline
plt.rcParams['font.sans-serif'] = ['Arial', 'Noto Sans CJK TC', 'SimHei']  
plt.rcParams['axes.unicode_minus'] = False  
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return

from pyfolio.plotting import show_perf_stats
perf_stats = show_perf_stats(
    returns, 
    benchmark_rets, 
    positions, 
    transactions,   
)
