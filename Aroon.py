# -*- coding: utf-8 -*-
# Auto-generated from Aroon.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import os 
import pandas as pd 
import numpy as np 
import tejapi

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'your key'
os.environ['mdate'] = '20180101 20201231'
os.environ['ticker'] = 'IR0001 2317 2324 2327 2330 2347 2353 2354 2357 2379 2382 2395'

# !zipline ingest -b tquant

# %% [code] cell 1
from zipline.api import set_slippage, set_commission, set_benchmark, attach_pipeline, order, order_target, symbol, pipeline_output, record
from zipline.finance import commission, slippage
from zipline.data import bundles
from zipline import run_algorithm
from zipline.pipeline import Pipeline, CustomFactor
from zipline.pipeline.filters import StaticAssets, StaticSids
from zipline.pipeline.factors import BollingerBands, Aroon
from zipline.pipeline.data import EquityPricing

from zipline.pipeline.mixins import LatestMixin

from zipline.master import run_pipeline

# %% [code] cell 2
bundle = bundles.load('tquant')
ir0001_asset = bundle.asset_finder.lookup_symbol('IR0001',as_of_date = None)

# %% [code] cell 3

def make_pipeline():
    curr_price = EquityPricing.close.latest
    
    alroon = Aroon(inputs = [EquityPricing.low, EquityPricing.high], window_length=25, mask = curr_price < 5000)
    up, down = alroon.up, alroon.down
    

    return Pipeline(
        columns = {
            'up':  up,
            'down':  down,
            'curr_price': curr_price,

        },
        screen = ~StaticAssets([ir0001_asset])
    )

def initialize(context):
    context.last_buy_price = 0
    set_slippage(slippage.VolumeShareSlippage())
    set_commission(commission.PerShare(cost=0.00285))
    set_benchmark(symbol('IR0001'))
    attach_pipeline(make_pipeline(), 'mystrategy')
    context.last_signal_price = 0
    
def handle_data(context, data):
    out_dir = pipeline_output('mystrategy')
    for i in out_dir.index: 
        sym = i.symbol # 標的代碼
        up = out_dir.loc[i, 'up']
        down = out_dir.loc[i, 'down']
        curr_price = out_dir.loc[i, 'curr_price']

        cash_position = context.portfolio.cash
        stock_position = context.portfolio.positions[i].amount

        buy, sell = False, False

        record(
            **{
                f'price_{sym}':curr_price,
                f'up_{sym}':up,
                f'down_{sym}':down,
                f'buy_{sym}':buy,
                f'sell_{sym}':sell
            }
        )

        if stock_position == 0:
            if down < 45 and up > 80:
                order(i, 1000)
                context.last_signal_price = curr_price
                buy = True
                record(
                    **{
                        f'buy_{sym}':buy
                    }
                )              

        elif stock_position > 0:
            if (up - down) > 15 and (down < 45) and (up > 55) and (cash_position >= curr_price * 1000):
                order(i, 1000)
                context.last_signal_price = curr_price
                buy = True
                record(
                    #globals()[f'buy_{sym}'] = buy
                    **{
                        f'buy_{sym}':buy
                    }
                )

            elif (down - up > 15) and (down > 55) and (up < 45):
                order_target(i, 0)
                context.last_signal_price = 0
                sell = True
                record(
                    **{
                        f'sell_{sym}':sell
                    }
                )
            else:
                pass
        else:
            pass

def analyze(context, perf):
    pass

results = run_algorithm(
    start = pd.Timestamp('2018-01-01', tz='UTC'),
    end = pd.Timestamp('2020-12-31', tz ='UTC'),
    initialize=initialize,
    bundle='tquant',
    analyze=analyze,
    capital_base=10e6,
    handle_data = handle_data
)

results

# %% [code] cell 4
from pyfolio.utils import extract_rets_pos_txn_from_zipline

returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return

# 時區標準化
returns.index = returns.index.tz_localize(None).tz_localize('UTC')
positions.index = positions.index.tz_localize(None).tz_localize('UTC')
transactions.index = transactions.index.tz_localize(None).tz_localize('UTC')
benchmark_rets.index = benchmark_rets.index.tz_localize(None).tz_localize('UTC')

# %% [code] cell 5
returns

# %% [code] cell 6
from pyfolio.plotting import show_perf_stats
show_perf_stats(
    returns, 
    benchmark_rets, 
    positions, 
    transactions, 
    turnover_denom='portfolio_value',
    live_start_date=pd.Timestamp('2021-11-25', tz='UTC'),
    bootstrap=True,
    header_rows={'Portfolio name': "Aroon strategy"}
)

# %% [code] cell 7
from pyfolio.plotting import show_worst_drawdown_periods
show_worst_drawdown_periods(returns, top=10)

# %% [code] cell 8
from pyfolio.tears import create_interesting_times_tear_sheet
create_interesting_times_tear_sheet(returns, benchmark_rets)

# %% [code] cell 9
from pyfolio.plotting import show_and_plot_top_positions
import pyfolio
show_and_plot_top_positions(returns, positions_alloc=pyfolio.pos.get_percent_alloc(positions))

# %% [code] cell 10
from pyfolio.pos import get_percent_alloc
get_percent_alloc(positions)

# %% [code] cell 11
from pyfolio.plotting import plot_rolling_returns
plot_rolling_returns(returns,
                     benchmark_rets, 
                     live_start_date=pd.Timestamp('2021-07-03'),
                     logy=True,
                     cone_std=(1., 1.5, 2.),
                     volatility_match=True
                    )

# %% [code] cell 12
from pyfolio.plotting import plot_returns
plot_returns(returns, live_start_date=pd.Timestamp('2021-07-03'))

# %% [code] cell 13
from pyfolio.plotting import plot_rolling_beta
plot_rolling_beta(returns, 
                  factor_returns=benchmark_rets
                 )

# %% [code] cell 14
import pyfolio
pyfolio.plotting.plot_drawdown_periods(returns)

# %% [code] cell 15
pyfolio.plotting.plot_drawdown_underwater(returns)

# %% [code] cell 16
pyfolio.plotting.plot_monthly_returns_heatmap(returns)

# %% [code] cell 17
pyfolio.plotting.plot_annual_returns(returns)

# %% [code] cell 18
pyfolio.plotting.plot_monthly_returns_dist(returns)

# %% [code] cell 19
pyfolio.plotting.plot_return_quantiles(returns, live_start_date=pd.Timestamp("2018-07-02", tz='UTC'))

# %% [code] cell 20
pyfolio.plotting.plot_exposures(returns, positions)

# %% [code] cell 21
pyfolio.plotting.plot_max_median_position_concentration(positions)

# %% [code] cell 22
pyfolio.plotting.plot_holdings(returns, positions)

# %% [code] cell 23
pyfolio.plotting.plot_long_short_holdings(returns, positions)

# %% [code] cell 24
pyfolio.plotting.plot_gross_leverage(returns, positions)

# %% [code] cell 25
pyfolio.plotting.plot_turnover(returns, transactions, positions)

# %% [code] cell 26
pyfolio.plotting.plot_daily_volume(returns, transactions)

# %% [code] cell 27
pyfolio.plotting.plot_daily_turnover_hist(transactions, positions)

# %% [code] cell 28
pyfolio.tears.create_full_tear_sheet(returns=returns,
                            positions=positions,
                            transactions=transactions,
                            benchmark_rets=benchmark_rets)
