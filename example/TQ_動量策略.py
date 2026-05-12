# -*- coding: utf-8 -*-
# Auto-generated from TQ_動量策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ## Trading Strategy - Momentum

# %% [markdown] cell 1
# ### TQ WORKFLOW
#
# 本篇follow `TQuant量化研究分析的workflow`建構策略，步驟分為以下5步驟：
# 1. Universe Definition
# 2. Data Preprocess
# 3. Factor Research
# 4. Backtesting
# 5. Performance Analysis

# %% [code] cell 2
import tejapi
import os
os.environ['TEJAPI_KEY'] = "tour key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from zipline.pipeline import Pipeline
from zipline.pipeline.data import TWEquityPricing
from zipline.pipeline.factors import CustomFactor, AverageDollarVolume
from zipline.master import get_prices, getToolData, tejquant, run_pipeline

# %% [markdown] cell 3
# ## 1. Universe Definition
#
# 定義股票池：(1) 流動性好的股票; (2)大市值的股票

# %% [code] cell 4
os.environ['ticker'] ='1101 1102 1216 1301 1303 1326 1402 1476 1590 1605 1722 1802 2002 2105 2201 2207 2227 2301 2303 2305 2308 2311 2317 2324 2325 2327 2330 2347 2353 2354 2357 2379 2382 2395 2408 2409 2412 2448 2454 2474 2492 2498 2603 2609 2615 2618 2633 2801 2823 2880 2881 2882 2883 2884 2885 2886 2887 2888 2890 2891 2892 2912 3008 3009 3034 3037 3045 3231 3474 3481 3673 3697 3711 4904 4938 5854 5871 5876 5880 6239 6415 6505 6669 6770 8046 8454 9904 9910'    
os.environ['mdate'] ='20000101 20230701'
# !zipline ingest -b tquant

# %% [code] cell 5
# Average Dollar Volume without nanmean, so that recent IPOs are truly removed
class avgVolume(CustomFactor):
    inputs = [TWEquityPricing.close, TWEquityPricing.volume]
    window_length = 252
    
    def compute(self, today, assets, out, close, volume):
        close[np.isnan(close)] = 0
        out[:] = np.mean(close * volume, axis=0)

def universe_filters():
   
    high_volume = avgVolume(window_length=252).rank(ascending=False)
    #have_market_cap = tejquant.TQDataSet.Market_Cap_Dollars.latest.rank(ascending=False)
    #sector =  tejquant.TQDataSet.industry_c.latest    
    
    universe_filter = (high_volume<=150) #& (have_market_cap<=150)
                          
    return universe_filter

# %% [markdown] cell 6
# 查看股票池的產業分布

# %% [code] cell 7
def plot_sector_counts(sector_counts):
    
    # create bar chart of number of companies in each sector    
    from matplotlib import pyplot as plt
    plt.rc("font",family='MicroSoft YaHei',weight="bold")
    
    from matplotlib.ticker import MaxNLocator
    import matplotlib.ticker as ticker
    
    
    plt.figure(figsize=(12, 12))
    
    bar = plt.subplot2grid((5,5), (0,0), rowspan=2, colspan=5)
    pie = plt.subplot2grid((5,5), (2,0), rowspan=3, colspan=5)
    
    # Bar chart
    sector_counts.plot(
        kind='bar',        
        color='b',
        rot=90,
        grid=True,
        ax=bar,
    )
    plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    #ax_freq.set_xticklabels(xticks, rotation=90)
    #bar.set_title('Sector Exposure - Counts')
    bar.set_title('股票池產業分布家數')
    
    # Pie chart
    sector_counts.plot(
        kind='pie', 
        colormap='Set3', 
        autopct='%.2f %%',
        fontsize=12,
        ax=pie,
    )
    pie.set_ylabel('')  # This overwrites default ylabel, which is None :(
    #pie.set_title('Sector Exposure - Proportions')
    pie.set_title('股票池產業分布占比 - %')
    
    plt.tight_layout()
    
def getUniverseSector(start_date,end_date):

    prices = get_prices(start_date,end_date,'close')
    
    query_columns = ['Turnover']#'Market_Cap_Dollars','PBR_TEJ',

    fdata = getToolData(prices.columns.tolist(),query_columns,prices)

    pipe = Pipeline(columns={'sector': tejquant.TQDataSet.Industry.latest}, screen=universe_filters())

    df_sector = run_pipeline(pipe, end_date, end_date,fdata).reset_index(level=0, drop=True)

    counts = (df_sector.groupby('sector').size())
    _c =[]
    counts.index = [x.split(' ')[1]  if len(x)>0 else ' ' for x in counts.index]
    
    plot_sector_counts(counts[counts>0].sort_values(ascending=False))   
    
    
start_date = pd.Timestamp('2023-05-25', tz = 'utc')
end_date = pd.Timestamp('2023-05-25', tz = 'utc')
getUniverseSector(start_date,end_date)

# %% [markdown] cell 8
# ## 2. Data Preprocess

# %% [code] cell 9
start_date = pd.Timestamp('2015-01-06',tz='utc')
end_date = pd.Timestamp('2023-05-26',tz='utc') 

prices = get_prices(start_date,end_date,'close')
query_columns = ['PBR_TEJ','Turnover']
fdata = getToolData(prices.columns.tolist(),query_columns,prices)

# %% [code] cell 10
fdata.keys()

# %% [code] cell 11
prices = get_prices(pd.Timestamp('2015-01-06',tz='utc'),pd.Timestamp('2023-05-26',tz='utc'),'close')
prices

# %% [code] cell 12
fdata['PBR_TEJ']

# %% [code] cell 13
fdata['Turnover']

# %% [code] cell 14
fdata['Industry']

# %% [code] cell 15
fdata['Market_Cap_Dollars']

# %% [markdown] cell 16
# ## 3. Factor Research

# %% [markdown] cell 17
# 因子建構

# %% [code] cell 18
import scipy.stats as stats
        
def _slope(ts, x=None):
    if x is None:
        x = np.arange(len(ts))
    log_ts = np.log(ts)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, log_ts)
    
    annualized_slope = (np.power(np.exp(slope), 252) - 1) * 100
    score = annualized_slope * (r_value ** 2)
    
    return slope,score


class Momentum(CustomFactor):
    """ Conventional Momentum factor """
    inputs = [TWEquityPricing.close]   
    window_length = 252
   
    outputs = ['momentum_class', 'momentum_slope', 'momentum_rslope'] 
    
    def compute(self, today, assets, out, close):
        x = np.arange(len(close))
        slope,rslope = np.apply_along_axis(_slope, 0, close, x.T)        
        
        out.momentum_class[:] = (close[-21] - close[-252])/close[-252]
        out.momentum_slope[:] = slope
        out.momentum_rslope[:] = rslope
        

def make_pipeline():
    
    close = TWEquityPricing.close.latest
    sector = tejquant.TQDataSet.Industry.latest
    marketcap = tejquant.TQDataSet.Market_Cap_Dollars.latest
    turnover = tejquant.TQDataSet.Turnover.latest
    pb = tejquant.TQDataSet.PBR_TEJ.latest

    Momentum_c, Momentum_s, Momentum_rs = Momentum()
    Alpha = (Momentum_c + Momentum_s + Momentum_rs)  
    
    return  Pipeline(columns={'close':close,
                              'sector':sector,
                              'marketcap':marketcap,
                              'turnover':turnover,
                              'pb':pb,
                              'Momentum_c':Momentum_c,
                              'Momentum_s':Momentum_s,
                              'Momentum_rs':Momentum_rs,
                              'Alpha':Alpha,
                             },
                             screen=universe_filters()
                     )

results = run_pipeline(make_pipeline(), '2015-01-01', '2023-05-26',fdata)
results

# %% [markdown] cell 19
# 因子分析

# %% [code] cell 20
import alphalens as al

# %% [code] cell 21
periods = (1,10,22)
factor_data = al.utils.get_clean_factor_and_forward_returns(factor=results['Momentum_c'],
                                                            prices=prices,
                                                            groupby=results['sector'],                                                           
                                                            periods=periods)
al.tears.create_full_tear_sheet(factor_data, 
                                long_short=False, 
                                group_neutral=False, 
                                by_group=False)

# %% [code] cell 22
periods = (1,10,22)
factor_data = al.utils.get_clean_factor_and_forward_returns(factor=results['Momentum_s'],
                                                            prices=prices,
                                                            groupby=results['sector'],                                                           
                                                            periods=periods)
al.tears.create_full_tear_sheet(factor_data, 
                                long_short=False, 
                                group_neutral=False, 
                                by_group=False)

# %% [code] cell 23
periods = (1,10,22)
factor_data = al.utils.get_clean_factor_and_forward_returns(factor=results['Momentum_rs'],
                                                            prices=prices,
                                                            groupby=results['sector'],                                                           
                                                            periods=periods)
al.tears.create_full_tear_sheet(factor_data, 
                                long_short=False, 
                                group_neutral=False, 
                                by_group=False)

# %% [code] cell 24
periods = (1,10,22)
factor_data = al.utils.get_clean_factor_and_forward_returns(factor=results['Alpha'],
                                                            prices=prices,
                                                            groupby=results['sector'],                                                           
                                                            periods=periods)
al.tears.create_full_tear_sheet(factor_data, 
                                long_short=False, 
                                group_neutral=False, 
                                by_group=False)

# %% [markdown] cell 25
# ## 4. Backtesting 

# %% [code] cell 26
from six import viewkeys
from zipline.api import (symbol,attach_pipeline, date_rules,order_target_percent,
                         pipeline_output,record,schedule_function,set_benchmark,set_slippage,set_commission)

                   
from zipline.finance import commission, slippage
from zipline.finance.commission import PerDollar
from zipline.finance.slippage import VolumeShareSlippage     

from zipline.pipeline import Pipeline
from zipline.pipeline.factors import RSI

from zipline import run_algorithm
from zipline.sources.TEJ_Api_Data import (get_Treasury_Return,
                                          get_Benchmark_Return,
                                          )
import zipline
from zipline import run_algorithm
from zipline.api import get_datetime
from zipline.api import (symbol,
                         sid,
                         set_benchmark,
                         attach_pipeline,
                         pipeline_output,
                         date_rules,
                         time_rules,
                         record,
                         schedule_function,
                         commission,
                         slippage,
                         set_slippage,
                         set_commission, 
                         order,
                         order_value,
                         order_percent,
                         order_target,
                         order_target_percent,
                         order_target_value)
from zipline.data import bundles
from zipline.data.data_portal import DataPortal
from zipline.utils.calendar_utils import get_calendar
from zipline.pipeline import Pipeline
from zipline.utils.run_algo import load_extensions
from zipline.pipeline import Pipeline, CustomFactor
from zipline.pipeline.data import Column, DataSet
from zipline.pipeline.domain import US_EQUITIES,TW_EQUITIES
from zipline.pipeline.filters import StaticAssets
from zipline.pipeline.loaders.frame import DataFrameLoader

from zipline.finance.commission import PerDollar
from zipline.finance.slippage import VolumeShareSlippage, FixedSlippage

import pyfolio as pf
from pyfolio.plotting import plot_rolling_returns, plot_rolling_sharpe
from pyfolio.timeseries import forecast_cone_bootstrap

# %% [code] cell 27
from six import viewkeys
from zipline.api import (symbol,attach_pipeline, date_rules,order_target_percent,
                         pipeline_output,record,schedule_function,set_benchmark,set_slippage,set_commission)

                   
from zipline.finance import commission, slippage
from zipline.finance.commission import PerDollar
from zipline.finance.slippage import VolumeShareSlippage     

from zipline.pipeline import Pipeline
from zipline.pipeline.factors import RSI

from zipline import run_algorithm
from zipline.sources.TEJ_Api_Data import (get_Treasury_Return,
                                          get_Benchmark_Return,
                                          )

start_date = pd.Timestamp('2015-12-30',tz='utc')
end_date = pd.Timestamp('2023-05-26',tz='utc')

# Get benchmark returns
Bindex=get_Benchmark_Return(start=start_date,
                     end=end_date,
                     symbol='IR0001').sort_index(ascending=True).tz_convert ('utc')

def make_pipeline():   
    Momentum_c, Momentum_s, Momentum_rs = Momentum()
    Alpha = Momentum_c+Momentum_s+Momentum_rs
    return Pipeline(columns={'longs': Momentum_rs.top(20)},screen=universe_filters())

def initialize(context):
    set_commission(PerDollar(cost=0.002925))
    set_slippage(VolumeShareSlippage(volume_limit=1, price_impact=0))    
    attach_pipeline(make_pipeline(), 'my_pipeline')
    schedule_function(rebalance, date_rules.month_end())

def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')  
    
def rebalance(context, data):

    pipeline_data = context.pipeline_data
    all_assets = pipeline_data.index
    longs = all_assets[pipeline_data.longs]

    one_third = 1.0 / 20.0
    for asset in longs:
        order_target_percent(asset, one_third)

    portfolio_assets = longs #| shorts
    positions = context.portfolio.positions
    for asset in viewkeys(positions) - set(portfolio_assets):
        if data.can_trade(asset):
            order_target_percent(asset, 0)    

# %% [code] cell 28
results = run_algorithm(start= start_date,  
                       end=end_date,
                       initialize=initialize,
                       before_trading_start=before_trading_start,
                       capital_base=1e6,
                       benchmark_returns =Bindex,
                       data_frequency='daily',
                       bundle='tquant'
                       )

# %% [code] cell 29
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

# %% [code] cell 30
plt.figure(figsize=(10, 6))
results.returns.cumsum().plot(layout='momentum')
results.benchmark_return.cumsum().plot()
plt.grid(True)
plt.ylabel('times')
plt.xlabel('date')
plt.legend(labels=['momentum_algo','benchmark'])

# %% [markdown] cell 31
# ## 5.Performance Analysis 

# %% [code] cell 32
import pyfolio as pf
import empyrical

bt_returns, bt_positions, bt_transactions = pf.utils.extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return

pf_returns, pf_positions, pf_transactions = pf.utils.extract_rets_pos_txn_from_zipline(results)
pf_positions.index = pf_positions.index.tz_convert('utc')
benchmark_rets = results.benchmark_return

# %% [code] cell 33
# Creating a Full Tear Sheet
pf.create_full_tear_sheet(bt_returns, positions=bt_positions, transactions=bt_transactions,
                          benchmark_rets=benchmark_rets,
                          round_trips=False)

# %% [code] cell 34
pf.create_full_tear_sheet(pf_returns, 
                          positions=pf_positions, 
                          transactions=pf_transactions,
                          benchmark_rets=benchmark_rets,
                          round_trips=True)

# %% [code] cell 35
pf.create_round_trip_tear_sheet(pf_returns, pf_positions, pf_transactions);
