# -*- coding: utf-8 -*-
# Auto-generated from TQ_延伸量能回測策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ### **Expanded Momentum Model**
# 策略出處：
#
# 本策略源自Trading Evolved Ch12中的Expanded Momentum Model，核心理念在於找尋過去N天股價走勢穩定向上之個股，經由迴歸係數與決定係數($R^2$)給予加權分數，作為股票的主要篩選依據，接著計算該股票近K天的報酬率標準差，進行反向權重配置，意即波動太大之個股給予較小的持股比率，反之則給予較大的持股比率。
#
# * 註：為避免太多運算造成計算過久，本範例以台灣50(0050)成分股為主要股票池
#
# 交易邏輯：
#
# * 選股邏輯：
#
#         計算股票過去N天的動能分數，篩選其中最高的M檔股票作為持股標的
#
# * 配置邏輯：
#
#         以股票近K天的報酬率計算標準差，進行反向權重配置

# %% [markdown] cell 1
# ### Tejapi、Zipline、Pyfolio套件引入

# %% [code] cell 2
import tejapi
import os
os.environ['TEJAPI_KEY'] = 'your key'
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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
                         order_target_percent, 
                         order_target_value,
                         symbol, 
                         set_commission, 
                         set_slippage, 
                         schedule_function, 
                         date_rules, 
                         time_rules, 
                         get_datetime, 
                         commission,
                         slippage,)
from zipline.data import bundles
from zipline.utils.run_algo import load_extensions
from zipline.utils.calendar_utils import get_calendar
from zipline.pipeline import Pipeline, CustomFactor
from zipline.pipeline.data import Column, DataSet, tejquant
from zipline.pipeline.domain import TW_EQUITIES
from zipline.pipeline.filters import StaticAssets
from zipline.pipeline.loaders.frame import DataFrameLoader

import pyfolio as pf
from pyfolio.plotting import plot_rolling_returns, plot_rolling_sharpe
from pyfolio.timeseries import forecast_cone_bootstrap

from scipy import stats  

# %% [code] cell 4
sns.set_style('whitegrid')
pd.set_option('display.expand_frame_repr', False)
np.random.seed(42)

log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [markdown] cell 5
# #### 資料載入－Tejapi、TejToolAPI
#
# * 擷取2015/01/01至2023/07/31所有上下市櫃公司股票代碼

# %% [code] cell 6
from zipline.sources.TEJ_Api_Data import get_universe
start = '2015-01-01'
end = '2023-07-31'
pool = get_universe(start, end, mkt = ['TWSE', 'OTC'], stktp_e = ['Common Stock', 'Common Stock-Foreign'])

# %% [markdown] cell 7
# * Ingest上述公司2015-01-01至2023-07-31的股價資料進bundle

# %% [code] cell 8
os.environ['ticker'] = ' '.join(pool)

os.environ['mdate'] = '20150101 20230731'

# !zipline ingest -b tquant

# %% [markdown] cell 9
# * 使用get_history_data載入上述公司同期間之台灣50成分股標記

# %% [code] cell 10
fg0050 = get_history_data(ticker=pool, columns=['Component_Stock_of_TWN50_Fg'], start='2015-01-01', end='2023-07-31')

# %% [code] cell 11
fg0050['Component_Stock_of_TWN50_Fg'] = fg0050['Component_Stock_of_TWN50_Fg'].replace({'Y': 1, '': 0})

fg0050 = fg0050.sort_values(['coid', 'mdate'])

# %% [markdown] cell 12
# * 將載入後的資料轉換成Zipline所需格式

# %% [code] cell 13
def Custom_loader(df, bundle):

    df['coid'] = df['coid'].astype(str)
    
    column = df.columns[~df.columns.isin(['coid', 'mdate'])].tolist()

    sids = bundle.asset_finder.equities_sids
    assets = bundle.asset_finder.retrieve_all(sids)
    symbols = [i.symbol for i in assets] 

    target_symbols = df[df['coid'].isin(symbols)]['coid'].unique().tolist()

    assets = bundle.asset_finder.lookup_symbols(target_symbols, as_of_date=None)
    assets_map = {i.symbol: i for i in assets}

    baseline_data = {}

    df1 = df.set_index(['coid', 'mdate'])
    for i in column:
        target = df1.unstack('coid')[i][target_symbols]
        target.columns = target.columns.map(assets_map)
        target = target.tz_localize('UTC').tz_convert('UTC')
        baseline_data.update({i: target})

    return baseline_data

# %% [code] cell 14
bundle = bundles.load('tquant')

baseline_data = Custom_loader(fg0050, bundle)

# %% [code] cell 15
baseline_data['Component_Stock_of_TWN50_Fg']

# %% [code] cell 16
class CustomDataset(DataSet):
    fg = Column(dtype=float)

    domain = TW_EQUITIES     
    
transform_data = {CustomDataset.fg: DataFrameLoader(CustomDataset.fg, baseline_data['Component_Stock_of_TWN50_Fg'])}

transform_data

# %% [markdown] cell 17
# ### Pipeline－動能因子計算

# %% [markdown] cell 18
# * 動能分數計算

# %% [code] cell 19
def momentum_score(ts):

    x = np.arange(len(ts)) 

    log_ts = np.log(ts) 

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, log_ts)

    annualized_slope = (np.power(np.exp(slope), 252) - 1) * 100

    score = annualized_slope * (r_value ** 2)
    
    return score

# %% [markdown] cell 20
# * 設定為0050成分股才可以計算動能分數

# %% [code] cell 21
class factor_momentum_score(CustomFactor):

    inputs = [TWEquityPricing.close, CustomDataset.fg]

    def compute(self, today, assets, out, close, fg):

        close, fg = pd.DataFrame(close), pd.DataFrame(fg)

        target_stock = fg.iloc[-1][fg.iloc[-1].eq(1)].index
        
        out[:] = [momentum_score(close[i]) if i in target_stock else np.nan for i in close]

# %% [markdown] cell 22
# * 計算週期：近20天收盤價
#
# * 篩選標準：
#   * 篩選出動能分數大於0
#   * 動能分數大於全體動能分數中位數的個股

# %% [code] cell 23
def make_pipeline():

    mom_signals = factor_momentum_score(window_length=20)

    close = TWEquityPricing.close.latest

    pipe = Pipeline(
        columns={
            'mom_score': mom_signals,
            
            'close':close,
        },
        screen=(mom_signals > 0) & (mom_signals > mom_signals.median())
    )
    return pipe

# %% [code] cell 24
start_dt = pd.Timestamp('2015-01-01', tz='utc')
end_dt = pd.Timestamp('2023-07-31', tz='utc')

from zipline.data import bundles

bundle = bundles.load('tquant')

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

pipe = make_pipeline()
data = engine.run_pipeline(pipe, start_dt, end_dt)
data.dropna(axis=0)

# %% [markdown] cell 25
# ### Zipline－策略回測
#   
# * 設定固定滑價成本和交易手續費各為0.2%
#   
# * 月初進場邏輯：每天買進股票池中符合條件之個股，使用反向波動度進行加權配置
#   
# * 月底出場邏輯：若投組內個股在月底並不在待交易清單內則出清

# %% [code] cell 26
def initialize1(context):

    set_slippage(slippage.FixedSlippage(spread=0.002))
    set_commission(commission.PerDollar(cost=0.002))
    

    schedule_function(
        func=rebalance_start,
        date_rule=date_rules.month_start(),
        time_rule=time_rules.market_open()
    )

    schedule_function(
        func=rebalance_end,
        date_rule=date_rules.month_end(),
        time_rule=time_rules.market_open()
    )
    
    pipeline = make_pipeline()
    attach_pipeline(pipeline, 'make_pipeline')

def before_trading_start(context, data):

    context.trades = pipeline_output('make_pipeline')
    
def rebalance_start(context, data):

    if len(context.trades) != 0:

        target = context.trades
        
        for stock in target.index:

            if data.can_trade(stock):
                
                hist_vol = data.history(stock, "close", 120, "1d").pct_change().rolling(20).std().iloc[-1]

                target.loc[stock, 'pos'] = 1 / hist_vol

        for stock, pos in zip(target.index, target.pos):

            if stock not in context.portfolio.positions.keys():

                order_value = (pos / target.pos.sum()) * context.portfolio.cash

                order_target_value(stock, order_value)

def rebalance_end(context, data):

    if len(context.trades) != 0:

        target = context.trades
                
        for stock in list(context.portfolio.positions.keys()):

            if stock not in target.index:

                order_target_value(stock, 0)


def portfolio_plot(context, results):
    import matplotlib.pyplot as plt
    import logbook
    logbook.StderrHandler().push_application()
    log = logbook.Logger('Algorithm')

    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    results['benchmark_cum'] = results.benchmark_return.add(1).cumprod()*1000000

    results[['portfolio_value', 'benchmark_cum']].plot(ax=ax1, label='Portfolio Value($)')

    ax1.set_ylabel('Portfolio value (TWD)')

    plt.legend(loc='upper left')

    plt.gcf().set_size_inches(18, 8)
    plt.show()

# %% [code] cell 27
start_dt = pd.Timestamp('2015-01-01', tz='utc')
end_dt = pd.Timestamp('2023-07-31', tz='utc')

from zipline.sources.TEJ_Api_Data import (get_Treasury_Return,
                                          get_Benchmark_Return,
                                          )

Bindex=get_Benchmark_Return(start=start_dt,
                     end=end_dt,
                     symbol='IR0001').sort_index(ascending=True).tz_convert('utc')

results = run_algorithm(start=start_dt,  
                       end=end_dt,
                       initialize=initialize1,
                       before_trading_start=before_trading_start,
                       capital_base=1e6,
                       benchmark_returns=Bindex,
                       data_frequency='daily',
                       bundle='tquant',
                       custom_loader=transform_data,
                       analyze=portfolio_plot) 

# %% [markdown] cell 28
# ### Pyfolio－投組績效分析

# %% [code] cell 29
from pyfolio.utils import extract_rets_pos_txn_from_zipline, print_table
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)

returns.index = returns.index.tz_localize(None).tz_localize('UTC')
positions.index = positions.index.tz_localize(None).tz_localize('UTC')
transactions.index = transactions.index.tz_localize(None).tz_localize('UTC')
results.benchmark_return.index = results.benchmark_return.index.tz_localize(None).tz_localize('UTC')

from pyfolio.plotting import show_perf_stats
perf_stats = show_perf_stats(returns=returns,
                factor_returns=results.benchmark_return,
                positions=positions,
                transactions=transactions,
                live_start_date='2022-01-01',
                )

# %% [code] cell 30
pf.create_full_tear_sheet(returns, positions, transactions, benchmark_rets=results.benchmark_return)
