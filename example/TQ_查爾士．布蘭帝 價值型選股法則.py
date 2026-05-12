# -*- coding: utf-8 -*-
# Auto-generated from TQ_查爾士．布蘭帝 價值型選股法則.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import pandas as pd
import numpy as np
import tejapi
import os
import json
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Arial'
tej_key ='your tej key'
tejapi.ApiConfig.api_key = tej_key
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
os.environ['TEJAPI_KEY'] = tej_key


from zipline.sources.TEJ_Api_Data import get_universe
import TejToolAPI
from zipline.data.run_ingest import simple_ingest
from zipline.api import set_slippage, set_commission, set_benchmark,  symbol,  record, order_target_percent
from zipline.finance import commission, slippage
from zipline import run_algorithm
from scipy.optimize import minimize

# %% [code] cell 1
start_date = '2010-01-01'; end_date = '2025-04-21'

pool = get_universe(start = start_date,
                      end = end_date,
                      mkt_bd_e = ['TSE', 'OTC'],
                      stktp_e = 'Common Stock',
                      main_ind_e = 'General Industry')

columns = ['coid','bstl', 'bsse', 'fld005', 'close_d', 'per', 'pbr_tej', 'shares', 'cscfo', 'cscfi', 'cscff']

start_dt = pd.Timestamp(start_date, tz = 'UTC')
end_dt = pd.Timestamp(end_date, tz = "UTC")

data_use = TejToolAPI.get_history_data(start = start_dt,
                                    end = end_dt,
                                    ticker = pool,
                                    fin_type = 'Q', # 為累計資料
                                    columns = columns,
                                    transfer_to_chinese = False)

# %% [code] cell 2
# 確保時間格式正確
data_use['mdate'] = pd.to_datetime(data_use['mdate'])

# 計算 Total_cashflow
data_use['Total_cashflow'] = data_use['Cash_Flow_from_Operating_Activities_Q']

# 排序
data_use = data_use.sort_values(['coid', 'mdate'])

# 轉成季資料：每股公司取每季最後一筆
df_q = data_use.set_index('mdate').groupby('coid', group_keys=False).resample('Q').last().reset_index()

# 計算近四季平均本益比
df_q['PER_4Q_avg'] = df_q.groupby('coid')['PER_TWSE'].transform(lambda x: x.rolling(4, min_periods=4).mean())

# 計算近四季總現金流
df_q['Cashflow_4Q_sum'] = df_q.groupby('coid')['Total_cashflow'].transform(lambda x: x.rolling(4, min_periods=4).sum())

# 計算「股價 / 現金流」：若現金流為 0，則設為 NaN 避免除以 0
df_q['Price_to_CF'] = (df_q['Close'] * df_q['Issue_Shares_1000_Shares']) / df_q['Cashflow_4Q_sum'].replace(0, np.nan)

# 市場平均本益比 & 市場平均 Price_to_CF
df_q['Market_PER_avg'] = df_q.groupby('mdate')['PER_TWSE'].transform('mean')
df_q['Market_PCF_avg'] = df_q.groupby('mdate')['Price_to_CF'].transform('mean')

# 判斷是否低於市場平均
df_q['PER_below_market'] = df_q['PER_4Q_avg'] < df_q['Market_PER_avg']
df_q['PCF_below_market'] = df_q['Price_to_CF'] < df_q['Market_PCF_avg']

# 確保排序
data_use = data_use.sort_values(['coid', 'mdate'])
df_q = df_q.sort_values(['coid', 'mdate'])

# 用 merge_asof 把季資料合併回每日
result_list = []

for coid, df_daily_group in data_use.groupby('coid'):
    df_q_group = df_q[df_q['coid'] == coid]

    merged = pd.merge_asof(
        df_daily_group,
        df_q_group[['mdate', 'PER_below_market', 'PCF_below_market']],
        on='mdate',
        direction='backward'
    )
    result_list.append(merged)

# 合併所有公司
data_final = pd.concat(result_list).sort_values(['coid', 'mdate']).reset_index(drop=True)
# %% [code] cell 3
def compute_stock(date, data):
    df = data[data['mdate'] == pd.to_datetime(date)].reset_index(drop = True)

    df['debt_equity_ratio'] = df['Total_Liabilities_Q'] / df['Total_Equity_Q']
    set_1 = set(df[df['debt_equity_ratio'] < .4]['coid'])

    Director_avg = df['Director_and_Supervisor_Holdings_Percentage'].mean()
    set_2 = set(df[df['Director_and_Supervisor_Holdings_Percentage'] > Director_avg]['coid'])

    set_3 = set(df[df['PER_below_market'] == True]['coid'])

    set_4 = set(df[df['PCF_below_market'] == True]['coid'])

    PBR_avg = df['PBR_TEJ'].mean()
    set_5 = set(df[df['PBR_TEJ'] < PBR_avg]['coid'])

    set_6 = set(df[df['PBR_TEJ'] < 1.0]['coid'])

    tickers = list(set_1 & set_2 & set_5 & set_6 & set_3 & set_4)


    return tickers

# %% [code] cell 4
pools = pool + ['IR0001']

start_ingest = start_date.replace('-', '')
end_ingest = end_date.replace('-', '')

print(f'開始匯入回測資料')
simple_ingest(name = 'tquant' , tickers = pools , start_date = start_ingest , end_date = end_ingest)
print(f'結束匯入回測資料')

# %% [code] cell 5
def initialize(context):
    set_slippage(slippage.VolumeShareSlippage(volume_limit=1, price_impact=0.01))
    set_commission(commission.Custom_TW_Commission())
    set_benchmark(symbol('IR0001'))

    context.i = 0
    context.state = False
    context.order_tickers = []
    context.last_tickers = []


def handle_data_1(context, data, rebalance = 60):
    # 避免前視偏誤，在篩選股票下一交易日下單
    if context.state == True:

        for i in context.last_tickers:
            if i not in context.order_tickers:
                order_target_percent(symbol(i), 0)


        for i in context.order_tickers:
            order_target_percent(symbol(i), 1 / len(context.order_tickers))

            curr = data.current(symbol(i), 'price')
            record(price = curr, days = context.i)

        print(f"下單日期：{data.current_dt.date()}, 擇股股票數量：{len(context.order_tickers)}, Leverage: {context.account.leverage}")


        context.last_tickers = context.order_tickers.copy()
        context.state = False

    backtest_date = data.current_dt.date()

    if context.i % rebalance == 0:
        context.state = True
        context.order_tickers = compute_stock(date = backtest_date, data = data_final)


    record(Leverage = context.account.leverage)
    if context.account.leverage > 1.2:
        print(f'{data.current_dt.date()}: Over Leverage, Leverage: {context.account.leverage}')
        for i in context.order_tickers:
            order_target_percent(symbol(i), 1 / len(context.order_tickers))

    context.i += 1
# %% [code] cell 6
def test(context, data):
    if context.i == 0:
        order_target_percent(symbol('IR0001'), 1.0)

    context.i += 1


def ana_test(context, perf):
    pass

# %% [code] cell 7
def analyze(context, perf):
        fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(18, 10), sharex=False)
        plt.style.use('ggplot')
        axes[0].plot(perf.index, perf['algorithm_period_return'], label = 'Strategy')
        axes[0].plot(perf.index, perf['benchmark_period_return'], label = 'Benchmark')
        axes[0].set_title(f"Backtest_Results")
        axes[0].legend()

        axes[1].plot(perf.index, perf['Leverage'], label = 'Leverage')
        axes[1].set_title(f"Leverage")
        axes[1].legend

        plt.tight_layout()
        plt.show()

results = run_algorithm(
            start = pd.Timestamp('2020-01-01', tz = 'utc'),
            end = pd.Timestamp('2025-04-21', tz = 'utc'),
            initialize = initialize,
            handle_data = handle_data_1,
            analyze = analyze,
            bundle = 'tquant',
            capital_base = 1e6)

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
