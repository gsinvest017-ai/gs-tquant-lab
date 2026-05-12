# -*- coding: utf-8 -*-
# Auto-generated from TQ_跟隨大戶策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ### **跟隨大戶的交易策略**
# 策略出處：
#
# 一般來說，三大法人、關鍵內部人或是其他千張大戶相較於散戶會擁有較多的資訊，因此較有可能挑選出潛力股或是避開地雷股。金管會為了降低資訊不對等，便要求公司或券商公布每日買賣資料，使得投資人能藉由觀察大戶們的買賣動向去分析股價的未來走勢，而這就是所謂的籌碼分析。
#
# 交易邏輯：
#
# * 買入訊號 : 當三大法人合計買超，且三大法人合計持股率低於近五日平均時，代表後續或許有一波漲勢，故給予買入訊號
#
# * 賣出訊號 : 當三大法人合計賣超，且三大法人合計持股率高於近五日平均時，代表法人可能準備出貨，故給予賣出訊號

# %% [markdown] cell 1
# ### Tejapi、Zipline、Pyfolio套件引入

# %% [code] cell 2
import tejapi
import os
os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

from zipline.pipeline import Pipeline
from zipline.pipeline.data import TWEquityPricing
from zipline.pipeline.factors import CustomFactor, AverageDollarVolume, SimpleMovingAverage, Returns
from zipline.master import get_prices, getToolData, tejquant, run_pipeline
from TejToolAPI.TejToolAPI import get_history_data

import warnings
warnings.filterwarnings('ignore')

# %% [code] cell 3
from collections import defaultdict
from time import time

import numpy as np
import pandas as pd
import pandas_datareader.data as web
from logbook import Logger, StderrHandler, INFO

import matplotlib.pyplot as plt
import seaborn as sns

from zipline import run_algorithm
from zipline.api import (attach_pipeline,
                         pipeline_output,
                         date_rules,
                         time_rules,
                         record,
                         schedule_function,
                         commission,
                         slippage,
                         set_slippage,
                         set_commission,
                         set_cancel_policy,
                         get_open_orders,
                         get_datetime,
                         cancel_order,
                         order_target,
                         order_target_value,
                         order_target_percent,
                         set_benchmark,
                         symbol)
from zipline.data import bundles
from zipline.utils.run_algo import load_extensions
from zipline.utils.calendar_utils import get_calendar
from zipline.pipeline import Pipeline, CustomFactor
from zipline.pipeline.data import Column, DataSet, tejquant
from zipline.pipeline.domain import TW_EQUITIES
from zipline.pipeline.filters import StaticAssets
from zipline.pipeline.loaders.frame import DataFrameLoader

import time
from collections import defaultdict
from zipline.sources.TEJ_Api_Data import (get_Treasury_Return,
                                          get_Benchmark_Return,
                                          )

# %% [code] cell 4
from pyfolio.utils import extract_rets_pos_txn_from_zipline
from pyfolio.plotting import show_perf_stats

sns.set_style('whitegrid')
pd.set_option('display.expand_frame_repr', False)
np.random.seed(42)

log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [markdown] cell 5
# ### TejToolAPI－三大法人持股比率&每日買賣超資料載入

# %% [markdown] cell 6
# * 股票池

# %% [code] cell 7
tickers = '1101 1102 1216 1301 1303 1326 1402 1476 1590 1605 1722 1802 2002 2105 2201 2207 \
2227 2301 2303 2308 2311 2317 2324 2325 2327 2330 2347 2353 2354 2357 2379 2382 2395 2408 \
2409 2412 2448 2454 2474 2492 2498 2603 2609 2615 2618 2633 2801 2823 2880 2881 2882 2883 \
2884 2885 2886 2887 2888 2890 2891 2892 2912 3008 3009 3034 3037 3045 3231 3474 3481 3673 \
3697 3711 4904 4938 5854 5871 5876 5880 6239 6415 6505 6669 6770 8046 8454 9904 9910'

# %% [markdown] cell 8
# * Ingest前述的公司代碼進bundle

# %% [code] cell 9
os.environ['ticker'] = tickers
os.environ['mdate'] = "20150101 20230816"
# !zipline ingest -b tquant

# %% [markdown] cell 10
# * 載入所需的三大法人持股比例與每日合計買賣超

# %% [code] cell 11
from zipline.data import bundles
bundle_name = 'tquant'
bundle = bundles.load(bundle_name)

sids = bundle.asset_finder.equities_sids
assets = bundle.asset_finder.retrieve_all(sids)
symbols = [i.symbol for i in assets]

df = get_history_data(ticker=symbols, columns=['qfii_pct', 'fd_pct', 'dlr_pct', 'tot_ex'], start='2020-01-01', end='2023-08-15')

df = df.sort_values(['coid', 'mdate'])

df = df.assign(Total_Pct=df.Fund_Stock_Holding_Pct + df.Qfii_Stock_Holding_Pct + df.Dealer_Stock_Holding_Pct)

# %% [markdown] cell 12
# * 將三大法人資料轉成Zipline所需格式

# %% [code] cell 13
def Custom_loader(df, bundle):

    df['coid'] = df['coid'].astype(str)
        
    column = df.columns[~df.columns.isin(['coid', 'mdate'])].tolist()

    df1 = df.set_index(['coid', 'mdate'])
    symbols = df1.index.get_level_values(0).unique().astype(str).tolist()  

    assets = bundle.asset_finder.lookup_symbols(symbols, as_of_date=None)
    assets_map = {i.symbol: i for i in assets}

    baseline_data = {}

    for i in column:
        target = df1.unstack('coid')[i]
        target.columns = target.columns.map(assets_map)
        target = target.tz_localize('UTC').tz_convert('UTC')
        baseline_data.update({i: target})

    return baseline_data

# %% [code] cell 14
baseline_data = Custom_loader(df, bundle)

baseline_data.keys()

# %% [code] cell 15
class CustomDataset(DataSet):
    total_vol = Column(dtype=float)
    total_pct = Column(dtype=float)

    domain = TW_EQUITIES     
    
transform_data = {
    CustomDataset.total_vol: DataFrameLoader(CustomDataset.total_vol, baseline_data['Total_Diff_Vol']),
    CustomDataset.total_pct: DataFrameLoader(CustomDataset.total_pct, baseline_data['Total_Pct']),
                  }

transform_data

# %% [markdown] cell 16
# ### Pipeline－進出場指標計算

# %% [code] cell 17
def make_pipeline(ma_days):

    vol = CustomDataset.total_vol.latest
    pct = CustomDataset.total_pct.latest

    pct_ma = SimpleMovingAverage(inputs=[CustomDataset.total_pct], window_length=ma_days)

    longs = (pct < pct_ma) & (vol > 0)
    shorts = (pct > pct_ma) & (vol < 0)

    pipe = Pipeline(
        columns={
            'Total_volume_diff': vol,
            'Total_pct': pct,
            'Total_pct_ma':pct_ma,
            'longs': longs,
            'shorts': shorts
        },
    )
    return pipe

# %% [code] cell 18
start_dt = pd.Timestamp('2020-01-01', tz='utc')
end_dt = pd.Timestamp('2023-08-15', tz='utc')

from zipline.pipeline.loaders import EquityPricingLoader

pricing_loader = EquityPricingLoader.without_fx(bundle.equity_daily_bar_reader, bundle.adjustment_reader)
def choose_loader(column):
    if column in TWEquityPricing.columns:
        return pricing_loader
    return transform_data[column]

from zipline.pipeline.engine import SimplePipelineEngine

engine = SimplePipelineEngine(get_loader=choose_loader,
                              asset_finder=bundle.asset_finder,
                              )

data = engine.run_pipeline(make_pipeline(5), start_dt, end_dt)
data

# %% [markdown] cell 19
# ### Zipline－交易策略回測
#
# * 設定固定滑價成本和交易手續費各為0.2%
#   
# * 個股進場邏輯：每天買進股票池中符合條件之個股，使用當前投組可動用現金的5%
#
# * 個股出場邏輯：若投組內個股發出賣出訊息則全數出清

# %% [code] cell 20
def initialize(context):
    
    set_slippage(slippage.FixedSlippage(spread=0.002))

    set_commission(commission.PerDollar(cost=0.002))

    context.last_month = 1e6

    schedule_function(rebalance_start, 
                      date_rules.every_day(),
                      time_rules.market_open(),
                      )
    
    schedule_function(rebalance_end, 
                      date_rules.every_day(),
                      time_rules.market_open())
    
    schedule_function(output_progress, 
                      date_rules.month_start(),
                      time_rules.market_open())


    pipeline = make_pipeline(5)
    attach_pipeline(pipeline, 'make_pipeline')

def output_progress(context, data):
    today = get_datetime().date()
    
    perf_pct = (context.portfolio.portfolio_value / context.last_month) - 1
    
    log.info(f"【{today}】投組報酬率：{perf_pct*100:.2f}%")
    
    context.last_month = context.portfolio.portfolio_value

def before_trading_start(context, data):

    context.trades = pipeline_output('make_pipeline').dropna(axis=0)

def rebalance_start(context, data):
    
    target = pd.DataFrame(context.trades)

    target = target[target['longs']]

    cash = context.portfolio.cash

    for stock in target.index:

        if data.can_trade(stock) & (cash > 0):

            order_target_value(stock, cash * 0.05)

def rebalance_end(context, data):

    target = pd.DataFrame(context.trades)

    target = target[target['shorts']]

    curr_positions = context.portfolio.positions.keys()

    for stock in curr_positions:

        if stock in target.index and data.can_trade(stock):
            
            order_target_percent(stock, 0)


def portfolio_plot(context, results):
    import matplotlib.pyplot as plt
    # import logbook
    # logbook.StderrHandler().push_application()

    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    results['benchmark_cum'] = results.benchmark_return.add(1).cumprod() * 1e6
    results[['portfolio_value', 'benchmark_cum']].plot(ax=ax1, label='Portfolio Value($)')
    ax1.set_ylabel('Portfolio value (TWD)')

    plt.legend(loc='upper left')

    plt.gcf().set_size_inches(18, 8)
    plt.show()

# %% [markdown] cell 21
# * 回測週期：2020-01-01至2023-08-15
#
# * 投組資金：1,000,000

# %% [code] cell 22
start_dt = pd.Timestamp('2020-01-01', tz='utc')
end_dt = pd.Timestamp('2023-08-15', tz='utc')

Bindex=get_Benchmark_Return(start=start_dt,
                     end=end_dt,
                     symbol='IR0001').sort_index(ascending=True).tz_convert('utc')

results = run_algorithm(start=start_dt, 
                       end=end_dt,
                       initialize=initialize,
                       before_trading_start=before_trading_start,
                       capital_base=1e6,
                       benchmark_returns=Bindex,
                       data_frequency='daily',
                       bundle='tquant',
                       custom_loader=transform_data,
                       analyze=portfolio_plot) 

# %% [markdown] cell 23
# ### Pyfolio－投組績效分析

# %% [code] cell 24
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)

perf_stats = show_perf_stats(returns=returns,
                factor_returns=results.benchmark_return,
                positions=positions,
                transactions=transactions,
                live_start_date='2023-01-01')

# %% [code] cell 25
import pyfolio as pf
returns.index = returns.index.tz_localize(None).tz_localize('UTC')
positions.index = positions.index.tz_localize(None).tz_localize('UTC')
transactions.index = transactions.index.tz_localize(None).tz_localize('UTC')
results.benchmark_return.index = results.benchmark_return.index.tz_localize(None).tz_localize('UTC')

pf.create_full_tear_sheet(returns, positions, transactions, benchmark_rets=results.benchmark_return)
