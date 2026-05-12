# -*- coding: utf-8 -*-
# Auto-generated from Pyfolio.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # Pyfolio
# <br>
# Pyfolio是一個用於金融投資組合績效與風險分析的 Python 庫，主要以圖表方式顯示投資策略的優劣，它與 Zipline-tej 開源回測庫完美兼容。本次實例將以布林通道交易策略為例，向您介紹 Pyfolio 所提供的強大視覺化與績效風險分析功能。

# %% [markdown] cell 1
# ### 載入所需套件與股價資料

# %% [code] cell 2
import os 
import pandas as pd 
import numpy as np 
import tejapi

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'Your_key'

os.environ['mdate'] = '20050702 20230702'
os.environ['ticker'] = 'IR0001 2330 2303 3443 2369 3414 2337 2454 2451 2388 3711 6770 1101 1701 1734 4133 2201 2206 1201'

# !zipline ingest -b tquant

# %% [markdown] cell 3
# ### 交易策略撰寫

# %% [code] cell 4
from zipline.api import set_slippage, set_commission, set_benchmark, attach_pipeline, order, order_target, symbol, pipeline_output, record
from zipline.finance import commission, slippage
from zipline.data import bundles
from zipline import run_algorithm
from zipline.pipeline import Pipeline
from zipline.pipeline.filters import StaticAssets, StaticSids
from zipline.pipeline.factors import BollingerBands
from zipline.pipeline.data import EquityPricing

bundle = bundles.load('tquant')
ir0001_asset = bundle.asset_finder.lookup_symbol('IR0001',as_of_date = None)

def make_pipeline():
    
    perf = BollingerBands(inputs=[EquityPricing.close], window_length=20, k=2)
    upper,middle,lower = perf.upper,perf.middle, perf.lower
    curr_price = EquityPricing.close.latest
     
    return Pipeline(
        columns = {
            'upper':  upper,
            'middle':  middle,
            'lower':  lower,
            'curr_price':curr_price
        },
        screen = ~StaticAssets([ir0001_asset])
    )

def initialize(context):
    context.last_buy_price = 0
    set_commission(commission.PerShare(cost=0.00285))
    set_benchmark(symbol('IR0001'))
    attach_pipeline(make_pipeline(), 'mystrategy')
    context.last_signal_price = 0
    
def handle_data(context, data):
    out_dir = pipeline_output('mystrategy')
    for i in out_dir.index: 
        sym = i.symbol # 標的代碼
        upper = out_dir.loc[i, 'upper']
        middle = out_dir.loc[i, 'middle']
        lower = out_dir.loc[i, 'lower']
        curr_price = out_dir.loc[i, 'curr_price']
        cash_position = context.portfolio.cash
        stock_position = context.portfolio.positions[i].amount
        
        buy, sell = False, False
        
        record(
            **{
                f'price_{sym}':curr_price,
                f'upper_{sym}':upper,
                f'lower_{sym}':lower,
                f'buy_{sym}':buy,
                f'sell_{sym}':sell
            }
        )
        
        if stock_position == 0:
            if (curr_price <= lower) and (cash_position >= curr_price * 1000):
                order(i, 1000)
                context.last_signal_price = curr_price
                buy = True
                record(
                    **{
                        f'buy_{sym}':buy
                    }
                )
        elif stock_position > 0:
            if (curr_price <= lower) and (curr_price <= context.last_signal_price) and (cash_position >= curr_price * 1000):
                order(i, 1000)
                context.last_signal_price = curr_price
                buy = True
                record(
                    **{
                        f'buy_{sym}':buy
                    }
                )
            elif (curr_price >= upper):
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
    start = pd.Timestamp('2008-07-02', tz='UTC'),
    end = pd.Timestamp('2022-07-02', tz ='UTC'),
    initialize=initialize,
    bundle='tquant',
    analyze=analyze,
    capital_base=5e4,
    handle_data = handle_data
)

results

# %% [markdown] cell 5
# <span id="menu"></span>
# ## Pyfolio 函式選單
#
# * [extract_rets_pos_txn_from_zipline](#extract_rets_pos_txn_from_zipline)
# * [show_perf_stats](#show_perf_stats)
# * [show_worst_drawdown_periods](#show_worst_drawdown_periods)
# * [create_interesting_times_tear_sheet](#create_interesting_times_tear_sheet)
# * [show_and_plot_top_positions](#show_and_plot_top_positions)
# * [get_percent_alloc](#get_percent_alloc)
# * [plot_rolling_returns](#plot_rolling_returns)
# * [plot_returns](#plot_returns)
# * [plot_rolling_beta](#plot_rolling_beta)
# * [plot_rolling_volatility](#plot_rolling_volatility)
# * [plot_rolling_sharpe](#plot_rolling_sharpe)
# * [plot_drawdown_periods](#plot_drawdown_periods)
# * [plot_drawdown_underwater](#plot_drawdown_underwater)
# * [plot_monthly_returns_heatmap](#plot_monthly_returns_heatmap)
# * [plot_annual_returns](#plot_annual_returns)
# * [plot_monthly_returns_dist](#plot_monthly_returns_dist)
# * [plot_return_quantiles](#plot_return_quantiles)
# * [plot_exposures](#plot_exposures)
# * [plot_max_median_position_concentration](#plot_max_median_position_concentration)
# * [plot_holdings](#plot_holdings)
# * [plot_long_short_holdings](#plot_long_short_holdings)
# * [plot_gross_leverage](#plot_gross_leverage)
# * [plot_turnover](#plot_turnover)
# * [plot_daily_volume](#plot_daily_volume)
# * [plot_daily_turnover_hist](#plot_daily_turnover_hist)
# * [plot_txn_time_hist](#plot_txn_time_hist)
# * [create_full_tear_sheet](#create_full_tear_sheet)

# %% [markdown] cell 6
# <span id="extract_rets_pos_txn_from_zipline"></span>
# ### pyfolio.utils.extract_rets_pos_txn_from_zipline
#
# 用於從 `zipline.run_algorithms()` 所輸出的資料表中，提取交易策略報酬、持有部位與交易資訊。
#
# #### Parameters:
# * backtest: pd.DataFrame<br>
#         zipline.run_algorithm() 得出的資料表。
#     
# #### Returns:
# * returns: _pd.Series_<br>
#         交易策略的每日報酬。
# * positions: _pd.DataFrame_<br>
#         交易策略的各證券與現金每日持有部位。
# * transactions : _pd.DataFrame_<br>
#         交易策略的每日交易資料，一列為一筆交易。
#         
# [Return to Menu](#menu)

# %% [code] cell 7
from pyfolio.utils import extract_rets_pos_txn_from_zipline

returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return

# 時區標準化
returns.index = returns.index.tz_localize(None).tz_localize('UTC')
positions.index = positions.index.tz_localize(None).tz_localize('UTC')
transactions.index = transactions.index.tz_localize(None).tz_localize('UTC')
benchmark_rets.index = benchmark_rets.index.tz_localize(None).tz_localize('UTC')

# %% [code] cell 8
returns.head()

# %% [code] cell 9
positions.head()

# %% [code] cell 10
transactions.head()

# %% [markdown] cell 11
# <span id="show_perf_stats"></span>
#
# ### pyfolio.plotting.show_perf_stats
#
# 顯示績效與風險指標。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * factor_returns: _pd.Series_, optional
#         計算 beta 所需的指標報酬率，通常設定為市場報酬。
# * positions: _pd.DataFrame_, optional
#         每日標的與現金部位表。
# * transactions: _pd.DataFrame_, optional
#         交易策略的交易資料，一列為一筆交易。
# * turnover_denom: _str_
#         周轉率計算方式，有 AGB 和 portfolio_value 兩種，預設為 AGB，
#         計算方法為 (買進總額 + 賣出總額絕對值) / (AGB or portfolio_value)，
#         AGB = portfolio-value - cash。
# * live_start_date: _datetime_, optional<br>
#         回測期間之後，開始 live trading 日期，相當於區分 In-sample 與 out-of sample 檢測，預設 = None，日期必須標準化。
# * bootstrap: _boolean_, optional
#         對各項指標進行拔靴法測試，預設 = False。
# * header_rows: _dict_ or _OrderedDict_, optional
#         在表格 start date yyyy-mm-dd 上額外增加列，預設為None。
#
# #### Returns: 
#    &emsp; _pd.DataFrame_
#
# [Return to Menu](#menu)

# %% [code] cell 12
from pyfolio.plotting import show_perf_stats
perf_stats = show_perf_stats(
    returns, 
    benchmark_rets, 
    positions, 
    transactions, 
    turnover_denom='portfolio_value',
    live_start_date=pd.Timestamp('2021-11-25', tz='UTC'),
    bootstrap=True,
    header_rows={'Portfolio name': "BBands strategy"}
)

# %% [markdown] cell 13
# <span id="show_worst_drawdown_periods"></span>
# ### pyfolio.plotting.show_worst_drawdown_periods
#
# 顯示前 n 大的交易回落期間。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * top: _int_, optional
#         決定 n，預設為 5。
#         
# #### Returns:
#    &emsp; _pd.DataFrame_
#    
# [Return to Menu](#menu)

# %% [code] cell 14
from pyfolio.plotting import show_worst_drawdown_periods
show_worst_drawdown_periods(returns, top=10)

# %% [markdown] cell 15
# <span id="create_interesting_times_tear_sheet"></span>
#
# ### pyfolio.tears.create_interesting_times_tear_sheet
#
# 製作重大事件發生日前後的日報酬平均、最大、最小值表格，並繪製圖表視覺化。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * benchmark_rets: _pd.DataFrame_, optional
#         指標日報酬率，預設 = None。
# * periods: _dict_ or _OrderedDict_, optional
#         歷史上重大事件發生日期。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * return_fig: _boolen_, optional
#         是否繪製圖表。
#         
# [Return to Menu](#menu)

# %% [code] cell 16
from pyfolio.tears import create_interesting_times_tear_sheet
create_interesting_times_tear_sheet(returns, benchmark_rets)

# %% [markdown] cell 17
# <span id="show_and_plot_top_positions"></span>
#
# ### pyfolio.plotting.show_and_plot_top_positions
#
# 製作多單持有量前十、空單持有量前十與綜合持有量的標的持有部位比率表格，並且繪製各時間點持有比率圖。
#
# #### Parameters:
#
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * positions_alloc: _pd.DataFrame_
#         個股標的的持有部位分布。
# * show_and_plot: _int_, optional
#         1. 若為 0，僅繪圖。
#         2. 若為 1，僅製表。
#         3. 若為 2，同時製作圖與表。
# * hide_positions: _boolean_, optional
#         若為 True，隱藏標的名稱。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 18
from pyfolio.plotting import show_and_plot_top_positions
import pyfolio
show_and_plot_top_positions(returns, positions_alloc=pyfolio.pos.get_percent_alloc(positions))

# %% [markdown] cell 19
# <span id="get_percent_alloc"></span>
#
# ### pyfolio.pos.get_percent_alloc
#
# 計算每日標的與現金部位比率
#
# #### Parameters:
#
# * values: _pd.DataFrame_ 
#         標的的持有部位分布。
#
# #### Returns:
# &emsp;_pd.DataFrame_, 每日標的與現金部位比率。
#
# [Return to Menu](#menu)

# %% [code] cell 20
from pyfolio.pos import get_percent_alloc
get_percent_alloc(positions)

# %% [markdown] cell 21
# <span id="plot_rolling_returns"></span>
#
# ### pyfolio.plotting.plot_rolling_returns
#
# 繪製出累積交易策略報酬率與指標報酬率。
#
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * factor_returns: _pd.Series_, optional
#         指標報酬率，通常設定為市場報酬。
# * live_start_date: _datetime_, optional<br>
#         回測期間之後，開始 live trading 日期，相當於區分 In-sample 與 out-of sample 檢測，預設 = None，日期必須標準化。
# * logy: _boolean_, optional
#         是否使用對數報酬，預設 = False。
# * cone_std: _float_ or _tuple_, optional
#         設定 out_of_sample 時，交易策略預期報酬率的標準差區間。
#         若為 float，則設定單一標準差區間。
#         若為 tuple，則設定多個標準差區間。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * volatility_match: _boolean_, optional
#         是否將交易策略與指標的報酬率以波動度進行標準化，以便比較相同風險下的報酬差異。
# * cone_function: _function_, optional
#         用來計算 out_of_sample 期間，預測報酬率的函式。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 22
from pyfolio.plotting import plot_rolling_returns
plot_rolling_returns(returns,
                     benchmark_rets, 
                     live_start_date=pd.Timestamp('2021-07-03'),
                     logy=True,
                     cone_std=(1., 1.5, 2.),
                     volatility_match=True
                    )

# %% [markdown] cell 23
# <span id="plot_returns"></span>
#
# ### pyfolio.plotting.plot_returns
#
# 繪製每日交易策略報酬圖。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * live_start_date: _datetime_, optional
#         回測期間之後，開始 live trading 日期，相當於區分 In-sample 與 out-of sample 檢測，預設 = None，日期必須標準化。 
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 24
from pyfolio.plotting import plot_returns
plot_returns(returns, live_start_date=pd.Timestamp('2021-07-03'))

# %% [markdown] cell 25
# <span id="plot_rolling_beta"></span>
# ### pyfolio.plotting.plot_rolling_beta
#
# 繪製六個月與十二個月的移動 beta 值。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * factor_returns: _pd.Series_
#         計算 beta 所需的指標報酬率，通常設定為市場報酬。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 26
from pyfolio.plotting import plot_rolling_beta
plot_rolling_beta(returns, 
                  factor_returns=benchmark_rets
                 )

# %% [markdown] cell 27
# <span id="plot_rolling_volatility"></span>
# ### pyfolio.plotting.plot_rolling_volatility
#
# 繪製移動波動度圖表
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * factor_returns: _pd.Series_, optional
#         計算指標波動度所需的指標報酬率，通常設定為市場報酬。
# * rolling_window: _int_, optional
#         計算移動波動度所需之窗格大小。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 28
from pyfolio.plotting import plot_rolling_volatility
plot_rolling_volatility(returns,
                        factor_returns=benchmark_rets
                       )

# %% [markdown] cell 29
# <span id="plot_rolling_sharpe"></span>
#
# ### pyfolio.plotting.plot_rolling_sharpe
#
# 繪製移動波動度圖表
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * factor_returns: _pd.Series_, optional
#         計算指標夏普值所需的指標報酬率，通常設定為市場報酬。
# * rolling_window: _int_, optional
#         計算移動波動度所需之窗格大小。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 30
from pyfolio.plotting import plot_rolling_sharpe
plot_rolling_sharpe(returns,
                    factor_returns=benchmark_rets
                       )

# %% [markdown] cell 31
# <span id="plot_drawdown_periods"></span>
#
# ### pyfolio.plotting.plot_drawdown_periods
#
# 繪製前 n 大回撤期間於累積報酬圖。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * top: _int_, optional
#         決定 n，預設為 10。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 32
import pyfolio
pyfolio.plotting.plot_drawdown_periods(returns)

# %% [markdown] cell 33
# <span id="plot_drawdown_underwater"></span>
#
# ### pyfolio.plotting.plot_drawdown_underwater
#
# 繪製策略 underwater 程度。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 34
pyfolio.plotting.plot_drawdown_underwater(returns)

# %% [markdown] cell 35
# <span id="plot_monthly_returns_heatmap"></span>
#
# ### pyfolio.plotting.plot_monthly_returns_heatmap
#
# 以熱力圖繪製交易策略每月報酬。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 36
pyfolio.plotting.plot_monthly_returns_heatmap(returns)

# %% [markdown] cell 37
# <span id="plot_annual_returns"></span>
#
# ### pyfolio.plotting.plot_annual_returns
#
# 繪製交易策略每年報酬。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 38
pyfolio.plotting.plot_annual_returns(returns)

# %% [markdown] cell 39
# <span id="plot_monthly_returns_dist"></span>
# ### pyfolio.plotting.plot_monthly_returns_dist
#
# 繪製交易策略每月報酬之分布圖。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 40
pyfolio.plotting.plot_monthly_returns_dist(returns)

# %% [markdown] cell 41
# <span id="plot_return_quantiles"></span>
# ### pyfolio.plotting.plot_return_quantiles
#
# 繪製交易策略日、週、月頻率的報酬盒狀圖。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * live_start_date: _datetime_, optional
#         回測期間之後，開始 live trading 日期，相當於區分 In-sample 與 out-of sample 檢測，預設 = None，日期必須標準化。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 42
pyfolio.plotting.plot_return_quantiles(returns, live_start_date=pd.Timestamp("2018-07-02", tz='UTC'))

# %% [markdown] cell 43
# <span id="plot_exposures"></span>
# ### pyfolio.plotting.plot_exposures
#
# 繪製多空曝險部位圖。
#
#     1. Long = 多頭部位總價值/所有部位總價值
#     2. Short = 空頭部位總價值/所有部位總價值
#     3. Net = 現金部位以外總價值/所有部位總價值
#
# #### Parameters:
#
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * positions_alloc: _pd.DataFrame_
#         個股標的的持有部位分布。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 44
pyfolio.plotting.plot_exposures(returns, positions)

# %% [markdown] cell 45
# <span id="plot_max_median_position_concentration"></span>
# ### pyfolio.plotting.plot_max_median_position_concentration
#
# 繪製多空集中程度 (concentration) 的最大值與中位數。
#     
#     1. max_long = 多頭部位集中程度最大值
#     2. max_short = 空頭部位集中程度最大值
#     3. median_long = 多頭部位集中程度中位數
#     4. median_short = 空頭部位集中程度中位數
#
# #### Parameters:
#
# * positions_alloc: _pd.DataFrame_
#         個股標的的持有部位分布。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 46
pyfolio.plotting.plot_max_median_position_concentration(positions)

# %% [markdown] cell 47
# <span id="plot_holdings"></span>
# ### pyfolio.plotting.plot_holdings
#
# 繪製持有股數。
# 1. Daily holdings: 每日持有股數
# 2. Average daily holdings, by month: 每月日均持有數
# 3. Average daily holdings, Total: 日均持有數
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * positions: _pd.DataFrame_
#         每日標的與現金部位表。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 48
pyfolio.plotting.plot_holdings(returns, positions)

# %% [markdown] cell 49
# <span id="plot_long_short_holdings"></span>
# ### pyfolio.plotting.plot_long_short_holdings
#
# 繪製多空頭持有股數。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * positions: _pd.DataFrame_
#         每日標的與現金部位表。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 50
pyfolio.plotting.plot_long_short_holdings(returns, positions)

# %% [markdown] cell 51
# <span id="plot_gross_leverage"></span>
# ### pyfolio.plotting.plot_gross_leverage
#
# 繪製毛槓桿 (gross leverage)，gross leverage = (long exposure - short exposure)/net asset value。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * positions: _pd.DataFrame_
#         每日標的與現金部位表。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#         
# #### Returns:
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 52
pyfolio.plotting.plot_gross_leverage(returns, positions)

# %% [markdown] cell 53
# <span id="plot_turnover"></span>
#
# ### pyfolio.plotting.plot_turnover
#
# 繪製周轉率圖，周轉率計算方法請見下方 turnover_denom。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * transactions: _pd.DataFrame_
#         交易策略的交易資料，一列為一筆交易。
# * positions: _pd.DataFrame_
#         每日標的與現金部位表。
# * turnover_denom: _str_, optional
#         周轉率計算方式，有 AGB 和 portfolio_value 兩種，預設為 AGB，
#         計算方法為 (買進總額 + 賣出總額絕對值) / (AGB or portfolio_value)，
#         AGB = portfolio-value - cash。
# * legend_loc: _plt.lengend_loc_, optional
#         圖表中圖例的位置。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#
# #### Returns: 
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 54
pyfolio.plotting.plot_turnover(returns, transactions, positions)

# %% [markdown] cell 55
# <span id="plot_daily_volume"></span>
#
# ### pyfolio.plotting.plot_daily_volume
#
# 繪製每日交易量。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * transactions: _pd.DataFrame_
#         交易策略的交易資料，一列為一筆交易。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#
# #### Returns: 
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 56
pyfolio.plotting.plot_daily_volume(returns, transactions)

# %% [markdown] cell 57
# <span id="plot_daily_turnover_hist"></span>
#
# ### pyfolio.plotting.plot_daily_turnover_hist
#
# 繪製每日周轉率分布圖，周轉率計算方法請見下方 turnover_denom。
#
# #### Parameters:
#
# * transactions: _pd.DataFrame_
#         交易策略的交易資料，一列為一筆交易。
# * positions: _pd.DataFrame_
#         每日標的與現金部位表。
# * turnover_denom: _str_, optional
#         周轉率計算方式，有 AGB 和 portfolio_value 兩種，預設為 AGB，
#         計算方法為 (買進總額 + 賣出總額絕對值) / (AGB or portfolio_value)，
#         AGB = portfolio-value - cash。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#
# #### Returns: 
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 58
pyfolio.plotting.plot_daily_turnover_hist(transactions, positions)

# %% [markdown] cell 59
# <span id="plot_txn_time_hist"></span>
# ### pyfolio.plotting.plot_txn_time_hist
#
# 繪製交易時間分布圖。(僅適用於日內資料)
#
# #### Parameters:
# * transactions: _pd.DataFrame_
#         交易策略的交易資料，一列為一筆交易。
# * bin_minutes: _float_, optional
#         時間區間間隔，預設為 5 分鐘。
# * tz: _str_, optional
#         時區。
# * ax: _matplotlib.Axes_, optional
#         matplotlib 中的尺標。
#         
# #### Returns: 
# &emsp; _matplotlib.Axes_
#
# [Return to Menu](#menu)

# %% [code] cell 60
pyfolio.plotting.plot_txn_time_hist(transactions, tz = 'Asia/Taipei')

# %% [markdown] cell 61
# <span id="create_full_tear_sheet"></span>
#
# ### pyfolio.tears.create_full_tear_sheet
#
# 繪製以上所有績效與風險相關圖表。
#
# #### Parameters:
# * returns: _pd.Series_
#         交易策略的日報酬率。
# * positions: _pd.DataFrame_
#         每日標的與現金部位表。
# * transactions: _pd.DataFrame_
#         交易策略的交易資料，一列為一筆交易。
# * market_data: _pd.DataFrame_, optional
#         每日市場資料，一日一行，欄位有股、交易量、價格，預設 = None。
# * benchmark_rets: _pd.Series_, optional
#         指標日報酬率，預設 = None。
# * slippage: _int_ or _float_, optional 
#         滑價，單位為basis point，需搭配 positions 和 transactions 使用，預設 = None，
# * live_start_date: _datetime_, optional
#         回測期間之後，開始 live trading 日期，相當於區分 In-sample 與 out-of sample 檢測，預設 = None，日期必須標準化。
# * sector_mappings: _dict_ or _pd.Series_, optional
#         行業分類，以股票 SID 為 key，行業為 value 的字典或 pd.Series，預設 = None。
# * round_trips: _boolean_, optional
#         交易 round trip 表格，需要搭配positions和transactions使用，預設 = False。
# * estimate_intraday: _boolean_ or _str_, optional
#         估算日內交易，預設為'infer'。
# * hide_positions: _boolean_, optional
#         隱藏股票代碼，預設為 False。
# * cone_std: _float_ or _tuple_, optional
#         設定 out_of_sample 時，交易策略預期報酬率的標準差區間。
#         若為 float，則設定單一標準差區間。
#         若為 tuple，則設定多個標準差區間。
# * bootstrap: _boolean_, optional
#         對各項指標進行拔靴法測試，預設 = False。
# * unadjusted_returns: _pd.Series_, optional
#         調整前日報酬率，預設 = None，提供後會額外繪製:
#         1. Cumulative returns given additional per-dollar slippage
#         2. Average annual returns given additional per-dollar slippage
# * turnover_denom: _str_, optional
#         周轉率計算方式，有 AGB 和 portfolio_value 兩種，預設為 AGB，
#         計算方法為 (買進總額 + 賣出總額絕對值) / (AGB or portfolio_value)，
#         AGB = portfolio-value - cash。
# * set_context: _boolean_, optional
#         設置繪圖風格。
# * header_rows: _dict_ or _OrderedDict_, optional
#         在表格 start date yyyy-mm-dd 上額外增加列，預設為 None。
# * factor_returns: _pd.DataFrame_, optional
#         風險因子所歸屬的報酬率，以日期作為指標，因子作為欄位。
#         Ex:
#                         momentum  reversal
#             2017-01-01  0.002779 -0.005453
#             2017-01-02  0.001096  0.010290       
# * factor_loadings: _pd.DataFrame_, optional
#         因子負荷量，為因子所對應的係數，以日期與標的為指標，因子為欄位。
#         Ex:
#                                momentum  reversal
#             dt         ticker
#             2017-01-01 AAPL   -1.592914  0.852830
#                        TLT     0.184864  0.895534
#                        XOM     0.993160  1.149353
#             2017-01-02 AAPL   -0.140009 -0.524952
#                        TLT    -1.066978  0.185435
#                        XOM    -1.798401  0.761549
# * pos_in_dollars: _boolean_, optional
#         若為 True，positions 內欄位單位為元 (dollar)。
#         若為 False，positions 內欄位單位為比率 (percentage)。 
# * factor_partitions: _dict_, optional
#         用於繪製報酬歸屬於因子圖。
#         Ex: 
#           {'style': ['momentum', 'size', 'value', ...],
#            'sector': ['technology', 'materials', ... ]}
#
# [Return to Menu](#menu)

# %% [code] cell 62
pyfolio.tears.create_full_tear_sheet(returns=returns,
                                     positions=positions,
                                     transactions=transactions,
                                     benchmark_rets=benchmark_rets
                                    )
