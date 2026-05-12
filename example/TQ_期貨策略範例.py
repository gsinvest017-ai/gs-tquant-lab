# -*- coding: utf-8 -*-
# Auto-generated from TQ_期貨策略範例.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import os
import tejapi

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'YOUR KEY'

import TejToolAPI
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
import alphalens
from zipline.data import bundles
from zipline.pipeline import Pipeline
from logbook import Logger, StderrHandler, INFO
import sys
import time
import warnings

warnings.filterwarnings('ignore')
print(sys.executable)
print(sys.version)
print(sys.prefix)

log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [code] cell 1
from zipline.api import (attach_pipeline,
                         pipeline_output,
                         record,
                         schedule_function,
                         set_slippage,
                         set_commission,
                         order_target,
                         order_target_percent,
                         set_benchmark,
                         symbol,
                         get_datetime,
                         get_open_orders,
                         cancel_order,
                         order,
                         set_max_leverage,
                         cancel_order
                         )
import zipline

from zipline.finance import commission, slippage
from zipline.finance.commission import PerDollar , NoCommission, PerTrade, PerShare, PerContract
from zipline.finance.slippage import VolumeShareSlippage, NoSlippage, FixedBasisPointsSlippage, FixedSlippage
from zipline.utils.events import date_rules, time_rules
from collections import defaultdict

from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar

from zipline.api import future_symbol,  \
    set_commission, set_slippage, schedule_function, date_rules, \
    time_rules, continuous_future, order_target
from functools import partial
from zipline.assets import Equity, Future

# %% [markdown] cell 2
# # 台指期貨-小台散戶多空比情緒指標交易策略實證研究（2018–2024）
#
# ## 研究概念與策略設計
#
# 本研究旨在實證 **小台散戶多空比情緒指標交易策略** 於台灣加權股價指數期貨（簡稱「台指期貨」）市場的獲利可行性，資料期間涵蓋 2018 年至 2024 年。
#
# 此交易策略係建立於 **散戶缺乏資訊優勢** 的假設，認為散戶因缺乏專業的金融知識與資訊優勢，往往錯估未來市場的行情走勢，導致其操作與市場趨勢常常相左。
#
# - 當市場價格上漲時，散戶錯估行情反轉下跌建立空單部位，散戶的部位與市場走勢呈現負向關係因而進場做多。
# - 當市場價格下跌時，散戶錯估行情反轉上漲建立多單部位，散戶的部位與市場走勢呈現負向關係因而多單平倉。
#
# 本擬運用**TQuant Lab**的投資研究平台，進行指數期貨資料撈取，以及逆勢交易策略建構、回測與績效分析。

# %% [markdown] cell 3
# ## 導入資料
# - 設定樣本為台指期貨(TX)、小台指期貨(MTX)
# - 設定起訖日為2018-2024年

# %% [code] cell 4
ticker1 = 'IR0001 IX0001'
ticker2 = 'TX MTX'

os.environ['ticker'] = ticker1
os.environ['future'] = ticker2
os.environ['mdate'] = '20180101 20250410'
# !zipline ingest -b tquant_future

# %% [markdown] cell 5
# ## 導入zipline 回測時需要的模組

# %% [code] cell 6
from zipline.api import (attach_pipeline,
                         pipeline_output,
                         record,
                         schedule_function,
                         set_slippage,
                         set_commission,
                         order_target,
                         order_target_percent,
                         set_benchmark,
                         symbol,
                         get_datetime,
                         get_open_orders,
                         cancel_order,
                         order,
                         set_max_leverage,
                         cancel_order
                         )
import zipline

from zipline.finance import commission, slippage
from zipline.finance.commission import PerDollar , NoCommission, PerTrade, PerShare, PerContract
from zipline.finance.slippage import VolumeShareSlippage, NoSlippage, FixedBasisPointsSlippage
from zipline.utils.events import date_rules, time_rules

from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar

from zipline.api import future_symbol,  \
    set_commission, set_slippage, schedule_function, date_rules, \
    time_rules, continuous_future, order_target

from zipline.TQresearch.futures_package import retail_long_short_ratio, get_stock_futures_universe

# %% [markdown] cell 7
# ## 交易成本與交易策略設定
#
# ### 1. 交易成本設定
#
# - **券商手續費**：每次每口單邊收取 1 點（等同 200元）
# - **滑價成本（Slippage）**：每次每口單邊假設滑價為 3 點（等同600元）
#   
# ### 2. 交易策略設定
#
# 散戶小台多空比指標：運用小台指期貨全市場未平倉量分別扣除三大法人空單、多單的未平倉量而得出散戶的多單與空單部位，最後計算散戶淨多單占全市場未平倉量的比率。
#
# 買進：散戶小台多空比指標 < 0。
#
# 賣出：散戶小台多空比指標 > 0。
#
#
# - #### 進場條件：
#     - 條件1. : $ \text{Position}_{t} = 0 $
#     - 條件2. : $ \text{Retail Invest Ratio}_{t} < 0 $  
#    
#    當條件1.和條件2.同時成立時，進場做多一口台指期貨。
#
# - #### 出場條件：
#     - 條件1. : $ \text{Position}_{t} > 0 $
#     - 條件2. : $ \text{Retail Invest Ratio}_{t} > 0 $  
#       
#    
#    當條件1.和條件2.同時成立時，賣出一口台指期貨。
#
#
# - #### 到期日轉倉
#
#     於當月近月合約到期日時，以當日台指期貨近月收盤價平倉，並於隔日以新合約收盤價建倉。

# %% [markdown] cell 8
# ## 建立散戶小台多空比情緒指標

# %% [code] cell 9
df_retail_long_short_ratio = retail_long_short_ratio(root_symbol='MTX')

# %% [code] cell 10
def initialize(context):

    context.root_symbol = 'TX'
    # 設定 benchmark
    context.set_benchmark(symbol('IR0001'))
    # 交易成本
    set_commission(equities = PerDollar(cost=0.003),futures = PerContract(cost={'TX':200},exchange_fee=0))
    set_slippage(equities = NoSlippage(),futures = FixedSlippage(spread=6.0))   
    # Schedule daily trading
    context.continue_fut = continuous_future(context.root_symbol, offset=0, roll='calendar', adjustment='add')
    # Schedule daily position rolling
    schedule_function(roll_futures, date_rules.every_day(), time_rules.market_close())   
    # calculate retail_ls_ratio
    context.retail_ls_ratio = df_retail_long_short_ratio

def roll_futures(context, data):
    open_orders = get_open_orders()
    for held_contract in context.portfolio.positions:
        if held_contract in open_orders:
            continue
        days_to_auto_close = (held_contract.auto_close_date.date() - data.current_session.date()).days
        if days_to_auto_close > 10:
            continue
        # Make a continuation
        continuation = continuous_future(
            held_contract.root_symbol, offset=0, roll="calendar", adjustment="add"
        )
        continuation_contract = data.current(continuation, "contract")
        if continuation_contract != held_contract:
            pos_size = context.portfolio.positions[held_contract].amount
            order_target(held_contract, 0)
            order_target(continuation_contract, pos_size)

def handle_data(context, data):
    
    today = data.current_session#.date()    
    sentiment_index1 = context.retail_ls_ratio.loc[today]
    score = 0        
    contract = data.current(context.continue_fut, 'contract')  
    
    market_positions = len(context.portfolio.positions)
    if market_positions<=0 and sentiment_index1<score:        
        order_target(contract,1)    

    if market_positions>0 and sentiment_index1>score:
        order_target(contract,0)
        
def analyze(context=None, results=None):
    # Plot the portfolio and asset data.
    results.algorithm_period_return.plot()
    results.benchmark_period_return.plot()
    plt.grid(True)
    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()

capital_base = 1e6 
calendar_name = 'TEJ' 
start_dt = pd.Timestamp('2018-01-02', tz='utc') 
end_dt = pd.Timestamp('2025-04-10', tz='utc')

# Running a Backtest
results = run_algorithm(start=start_dt, 
                        end=end_dt, 
                        initialize=initialize, 
                        handle_data = handle_data, 
                        capital_base=capital_base, 
                        analyze = analyze,
                        data_frequency='daily', 
                        bundle='tquant_future', 
                        trading_calendar=get_calendar(calendar_name), ) 

#results[['starting_cash','capital_used','ending_cash','long_exposure','longs_count','portfolio_value','futures_contract','futures_price','security_price']]

# %% [markdown] cell 11
# # 台指期貨逆勢交易策略實證研究（2018–2024）
#
# ## 研究概念與策略設計
#
# 本研究旨在實證 **逆勢交易策略（Contrarian Trading Strategy）** 於台灣加權股價指數期貨（簡稱「台指期貨」）市場的獲利可行性，資料期間涵蓋 2018 年至 2024 年。
#
# 逆勢交易策略係建立於 **均值回歸（Mean Reversion）** 假設，認為市場價格在短期出現過度波動後，傾向回歸其歷史均值或合理價值。
#
# - 當價格短期內大幅上漲，可能出現過熱，後市可能下跌。
# - 當價格短期內大幅下跌，可能為過度悲觀，後市可能反彈。
#
# 本擬運用**TQuant Lab**的投資研究平台，進行指數期貨資料撈取，以及逆勢交易策略建構、回測與績效分析。

# %% [markdown] cell 12
# ## 導入資料
# - 設定樣本為台指期貨(TX)、小台指期貨(MTX)
# - 設定起訖日為2018-2024年

# %% [code] cell 13
ticker1 = 'IR0001 IX0001'
ticker2 = 'TX MTX'

os.environ['ticker'] = ticker1
os.environ['future'] = ticker2
os.environ['mdate'] = '20180101 20250410'
#!zipline ingest -b tquant_future

# %% [markdown] cell 14
# ## 導入zipline 回測時需要的模組

# %% [code] cell 15
from zipline.api import (attach_pipeline,
                         pipeline_output,
                         record,
                         schedule_function,
                         set_slippage,
                         set_commission,
                         order_target,
                         order_target_percent,
                         set_benchmark,
                         symbol,
                         get_datetime,
                         get_open_orders,
                         cancel_order,
                         order,
                         set_max_leverage,
                         cancel_order
                         )
import zipline
from zipline.finance import commission, slippage
from zipline.finance.commission import PerDollar , NoCommission, PerTrade, PerShare, PerContract 
from zipline.finance.slippage import VolumeShareSlippage, NoSlippage, FixedBasisPointsSlippage, FixedSlippage
from zipline.utils.events import date_rules, time_rules
from collections import defaultdict

from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar

from zipline.api import future_symbol,  \
    set_commission, set_slippage, schedule_function, date_rules, \
    time_rules, continuous_future, order_target
from functools import partial
from zipline.assets import Equity, Future

# These lines are for the dynamic text reporting
from IPython.display import display
import ipywidgets as widgets
# %% [markdown] cell 16
# ## 交易成本與交易策略設定
#
# ### 1. 交易成本設定
#
# - **券商手續費**：每次每口單邊收取 1 點（等同 200元）
# - **滑價成本（Slippage）**：每次每口單邊假設滑價為 3 點（等同600元）
#   
# ### 2. 交易策略設定
#
# - #### 進場條件：
#     - 條件1. : $ \text{EMA}_{20} > \text{EMA}_{40}$
#     - 條件2. : $ P_t \leq P_{t}^{\max(20)} - 3 \times \sigma_{P,20} $
#       
#    
#    當條件1.和條件2.同時成立時，視為價格大幅修正，進場做多一口台指期貨。
#
# - #### 出場條件：
#     - 條件1. : $ \text{EMA}_{20} < \text{EMA}_{40}$
#     - 條件2. : $ \text{Holding\_Period} > 20 $
#       
#    
#    當條件1.或條件2.同時成立時，賣出一口台指期貨。
#
#
# - #### 到期日轉倉
#
#     於當月近月合約到期日時，以當日台指期貨近月收盤價平倉，並於隔日以新合約收盤價建倉。

# %% [code] cell 17
out = widgets.HTML()
display(out)

"""
Model Settings
"""
vola_window = 40
slow_ma = 80
fast_ma = 40
risk_factor = 0.02
high_window = 20
days_to_hold = 20
dip_buy = -3

def report_result(context, data):
    context.months += 1
    today = zipline.api.get_datetime().date()
    # Calculate annualized return so far
    ann_ret = (
        np.power(
            context.portfolio.portfolio_value / starting_portfolio, 12 / context.months
        )
        - 1
    )
    
    # Update the text
    out.value = """{} We have traded <b>{}</b> months 
    and the annualized return is <b>{:.2%}</b>""".format(
        today, context.months, ann_ret
    )
    
def initialize(context):

    # 設定 benchmark
    context.set_benchmark(symbol('IR0001'))
    # 交易成本
    context.enable_commission = True
    context.enable_slippage = True   
    
    if context.enable_commission:
        comm_model = PerContract(cost={'TX':200},exchange_fee=0)
    else:
        comm_model = PerContract(cost=0.0,exchange_fee=0)
        
    set_commission(futures=comm_model)
    
    if context.enable_slippage:
        slippage_model = FixedSlippage(spread=6.0)
    else:
        slippage_model=FixedSlippage(spread=0.0)      
        
    set_slippage(futures=slippage_model)

    # construct continues futures
    tx1 = continuous_future('TX', offset=0, roll='calendar', adjustment='add')
    context.continue_tx1 = tx1

    context.universe = [tx1]
    context.bars_held = {market.root_symbol: 0 for market in context.universe} 
    
    # Schedule daily trading
    schedule_function(daily_trade, date_rules.every_day(), time_rules.market_close())
    
    context.months = 0  

    # Schedule monthly report output
    schedule_function(
        func=report_result,
        date_rule=date_rules.month_start(),
        time_rule=time_rules.market_open(),
    )

def roll_futures(context, data):
    
    open_orders = get_open_orders()
    # rolling positions
    for held_contract in context.portfolio.positions:
        if not isinstance(held_contract, Future):
            continue
        # don't roll positions that are set to change by core logic
        if held_contract in open_orders: 
            continue
        # Save some time by only checking rolls for
        # contracts expiring in the next week        
        days_to_auto_close = (
            held_contract.auto_close_date.date() - data.current_session.date()
        ).days
        if days_to_auto_close > 5:
            continue  
     
        # Get the current contract of the continuation
        continuation_contract = data.current( context.continue_tx1, "contract")
          
        if continuation_contract != held_contract:
            # Check how many contracts we hold
            pos_size = context.portfolio.positions[held_contract].amount         
            # Close current position
            print(f'{held_contract} 平倉出場於轉倉')
            order_target(held_contract, 0)
            # Open new position
            print(f'{continuation_contract} 買進進場於轉倉')
            order_target(continuation_contract, pos_size)


def position_size(portfolio_value, std, pv):
    target_variation = portfolio_value * risk_factor
    contract_variation = std * pv
    contracts = target_variation / contract_variation
    # Return rounded down number.
    return int(np.nan_to_num(contracts))
    
def daily_trade(context, data):
    
    hist = data.history(
        context.universe, 
        fields=['close', 'volume'], 
        frequency='1d', 
        bar_count=250,
    )    
    # Calculate the trend
    hist['trend'] = hist['close'].ewm(span=fast_ma).mean() > hist['close'].ewm(span=slow_ma).mean()

    open_pos = {pos.root_symbol: pos for pos in context.portfolio.positions}         
    
    for continuation in context.universe:
        root = continuation.root_symbol

        # Slice off history for this market
        h = hist.xs(continuation, level=1)
        # Calculate volatility
        std = h.close.diff()[-vola_window:].std()
        
        if root in open_pos: # Check open positions first.
            context.bars_held[root] += 1 # One more day held
            
            if context.bars_held[root] >= 20:
                # Held for a month, exit                
                contract = open_pos[root]
                order_target(contract,0)

            elif h['trend'].iloc[-1] == False:
                # Trend changed, exit.
                contract = open_pos[root]
                order_target(contract,0)

        else: # Check for new entries            
            if h['trend'].iloc[-1]: 
                # Calculate the pullback
                pullback = (
                    h['close'].values[-1] - np.max(h['close'].values[-high_window:])
                    ) / std                
                if pullback < dip_buy:                    
                    # Get the current contract
                    contract = data.current(continuation, 'contract')                    
                    # Calculate size
                    contracts_to_trade = position_size( \
                                           context.portfolio.portfolio_value, \
                                           std, \
                                           contract.price_multiplier)                    
                    # Trade
                    order_target(contract, contracts_to_trade)                    
                    # Reset bar count to zero
                    context.bars_held[root] = 0
    
    # # # Check if we need to roll.
    if len(open_pos) > 0:  
        roll_futures(context, data)


def analyze(context=None, results=None):
    # Plot the portfolio and asset data.
    results.algorithm_period_return.plot()
    results.benchmark_period_return.plot()
    plt.grid(True)
    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()

    
capital_base = 1e7
starting_portfolio = capital_base
calendar_name = 'TEJ'
start_dt = pd.Timestamp('2018-01-02', tz='utc')
end_dt = pd.Timestamp('2025-04-10', tz='utc')
# Running a Backtest
results = run_algorithm(start=start_dt,
                        end=end_dt,
                        initialize=initialize,
                        #handle_data = handle_data,
                        capital_base=capital_base,
                        analyze=analyze,
                        data_frequency='daily',
                        bundle='tquant_future',
                        trading_calendar=get_calendar(calendar_name),
                        )

# %% [markdown] cell 18
# # 台股個股期貨動能交易策略實證研究（2020–2024）
#
# ## 研究概念與策略設計
#
# 本研究旨在實證 **動能交易策略（Contrarian Trading Strategy）** 於台股個股期貨市場上的獲利可行性，資料期間涵蓋 2018 年至 2024 年。
#
# 動能交易策略係建立於 **趨勢持續性（trend continuation）** 假設，認為市場具有一定程度的價格慣性，未來的價格走勢可能延續過去的趨勢。
#
# - 當市場價格上漲且動能指標顯示強勢，預期價格將持續上漲，因而進場做多。
# - 當市場價格下跌且動能指標顯示疲弱，預期價格將持續下跌，因而賣出出場。
#
# 本擬運用**TQuant Lab**的投資研究平台，進行**個股期貨**資料撈取，以及動能交易策略建構、回測與績效分析。

# %% [markdown] cell 19
# ## 導入資料
# - 設定樣本有個股期貨的Pool
# - 設定起訖日為2018-2024年
# - 運用`get_stock_futures_universe`取得具有個股期貨的股票代碼和期貨代碼

# %% [code] cell 20
from zipline.TQresearch.futures_package import retail_long_short_ratio, get_stock_futures_universe

st = None
et =None
if st is None:
    st='2020-01-01'
if et is None:
    et = pd.Timestamp.now().date().isoformat()    

stk_universe, fut_universe = get_stock_futures_universe(st=st,et=et)

# %% [code] cell 21
ticker1 = ' '.join(stk_universe)+' IR0001 IX0001'
ticker2 = ' '.join(fut_universe)+' TX MTX'

os.environ['ticker'] = ticker1
os.environ['future'] = ticker2
os.environ['mdate'] = '20200101 20250410'
# !zipline ingest -b tquant_future

# %% [markdown] cell 22
# ## 導入zipline 回測時需要的模組

# %% [code] cell 23
import zipline
from zipline.finance import commission, slippage
from zipline.finance.commission import PerDollar , NoCommission, PerTrade, PerShare, PerContract 
from zipline.finance.slippage import VolumeShareSlippage, NoSlippage, FixedBasisPointsSlippage, FixedSlippage
from zipline.utils.events import date_rules, time_rules
from collections import defaultdict

from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar

from zipline.api import future_symbol,  \
    set_commission, set_slippage, schedule_function, date_rules, \
    time_rules, continuous_future, order_target
from functools import partial
from zipline.assets import Equity, Future

# These lines are for the dynamic text reporting
from IPython.display import display
import ipywidgets as widgets

from zipline.api import (attach_pipeline,
                         pipeline_output,
                         record,
                         schedule_function,
                         set_slippage,
                         set_commission,
                         order_target,
                         order_target_percent,
                         set_benchmark,
                         symbol,
                         get_datetime,
                         get_open_orders,
                         cancel_order,
                         order,
                         set_max_leverage,
                         cancel_order
                         )

# %% [markdown] cell 24
# ## 交易成本與交易策略設定
#
# ### 1. 交易成本設定
#
# - **券商手續費**：每次每口單邊收取 1 點（等同 200元）
# - **滑價成本（Slippage）**：每次每口單邊假設滑價為 3 點（等同600元）
#   
# ### 2. 交易策略設定
#
# 動能因子：運用股價對時間進行線性回歸後所得到的斜率係數。該係數反映了股價隨時間變化的趨勢方向與速度，是評估資產動能的重要指標。
#
# 買進：動能因子最強的top30檔個股期貨，且動能因子數值必須大於最低要求0。
#
# 賣出：當持倉部位的動能因子強度排名不在top30內，或當動能因子數值小於0，賣出個股期貨
#
#
# - #### 進場條件：
#     - 條件 1： $ \text{Momentum}_i > 0$
#     - 條件 2： $ \text{Rank}(\text{Momentum}_i) \in Top 30 $
#       
#    
#    當條件1.和條件2.同時成立時，進場做多一口台指期貨。
#
# - #### 出場條件：
#     - 條件 1：$ \text{Momentum}_i \leq 0$  
#     - 條件 2：$ \text{Rank}(\text{Momentum}_i) \notin \text{Top 30} $
#       
#    
#    當條件1.或條件2.同時成立時，賣出一口台指期貨。
#
#
# - #### 到期日轉倉
#
#     於當月近月合約到期日時，以當日台指期貨近月收盤價平倉，並於隔日以新合約收盤價建倉。

# %% [code] cell 25
"""
Model Settings
"""
intial_portfolio = 50000000
minimum_momentum = 0
portfolio_size = 30

def momentum_score(ts):
    """
    Input:  Price time series.
    Output: Annualized exponential regression slope,
            multiplied by the R2
    """
    # Note I: The easiest way to calculate exponential regression is to just do
    # a linear regression based on the log values
    #
    # Note II: Idea behind exponential regression: https://rpubs.com/mengxu/exponential-model

    # Make a list of consecutive numbers
    x = np.arange(len(ts))
    # Get logs
    log_ts = np.log(ts)
    # Calculate regression values
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, log_ts)
    # Annualize percent
    annualized_slope = (np.power(np.exp(slope), 252) - 1) * 100
    # Adjust for fitness
    score = annualized_slope * (r_value ** 2)
    return score

def initialize(context):
    
    # 設定 benchmark
    context.set_benchmark(symbol('IR0001'))
    # 交易成本
    context.enable_commission = False
    context.enable_slippage = False   
    
    if context.enable_commission:
        comm_model = PerContract(cost={'TX':200},exchange_fee=0)
    else:
        comm_model = PerContract(cost=0.0,exchange_fee=0)
        
    set_commission(futures=comm_model)
    
    if context.enable_slippage:
        slippage_model=FixedBasisPointsSlippage(basis_points=50, volume_limit=0.1) 
    else:
        slippage_model=FixedSlippage(spread=0.0)      
        
    set_slippage(futures=slippage_model)

    # Make a list of all the markets
    markets = [x for x in fut_universe ] # 'FFF','DFF','JFF','KFF'   if x not in ['HAF']
    
    # Make a list of all continuations
    context.universe = [
        continuous_future(market, offset=0, roll='calendar', adjustment='add')
            for market in markets
    ]
    # Schedule rebalance monthly.
    schedule_function(
        func=rebalance,
        date_rule=date_rules.month_start(),
        time_rule=time_rules.market_close(),
    )

    # Schedule daily roll check
    schedule_function(roll_futures, date_rules.every_day(), time_rules.market_close())

    
def roll_futures(context, data):

    open_orders = get_open_orders()    
    # rolling positions
    for held_contract in context.portfolio.positions:
        if not isinstance(held_contract, Future):
            continue
        # don't roll positions that are set to change by core logic
        if held_contract in open_orders: 
            continue
        # Save some time by only checking rolls for
        # contracts expiring in the next week         
        days_to_auto_close = (
            held_contract.auto_close_date.date() - data.current_session.date()
        ).days
        if days_to_auto_close > 5:
            continue  
        # Make a continuation
        continuation = continuous_future(
                held_contract.root_symbol, 
                offset=0, 
                roll='calendar',
                adjustment='add'
                )
        # Get the current contract of the continuation
        continuation_contract = data.current(continuation, 'contract')
        # print(continuation_contract)  
        if continuation_contract != held_contract:
            # Check how many contracts we hold
            pos_size = context.portfolio.positions[held_contract].amount         
            # Close current position
            print(f'{held_contract} 平倉出場於轉倉')
            order_target(held_contract, 0)

            if continuation_contract is None or np.isnan(data.current(continuation_contract,'close'))==True:
                continue
                
            # Open new position
            print(f'{continuation_contract} 買進進場於轉倉')
            order_target(continuation_contract, pos_size)

def rebalance(context, data):
 
    momentum_list = {}
    # Iterate markets, check for trades
    for continuation in context.universe: 
        # Get root symbol of continuation
        root = continuation.root_symbol        
        try:
            h = data.history(
                        continuation, 
                        fields=['close'], 
                        frequency='1d', 
                        bar_count=250,
                        )
            if np.all(h.close.isna()): continue
        except Exception as e:
             continue            
        
        momentum_list[root] = momentum_score(h.close.values)
        
    # Sort by momentum value.
    momentum_list = pd.Series(momentum_list)
    ranking_table = momentum_list.sort_values(ascending=False).dropna()
    """
    Sell Logic
    
    First we check if any existing position should be sold.
    * Sell if stock is no longer part of index.
    * Sell if stock has too low momentum value.
    """
    # Make dictionary of open positions
    kept_positions = {pos.root_symbol: pos 
                        for pos in context.portfolio.positions
                     }     
    for contract in context.portfolio.positions:
        if contract.root_symbol not in ranking_table.index:
            if np.isnan(data.current(contract,'close'))==True:
                order_target_percent(contract, 0.0)
                kept_positions.pop(contract.root_symbol, None)  
            continue
        if ranking_table[contract.root_symbol] < minimum_momentum:
            order_target_percent(contract, 0.0)
            kept_positions.pop(contract.root_symbol, None)
    """
    Stock Selection Logic
    
    Check how many stocks we are keeping from last month.
    Fill from top of ranking list, until we reach the
    desired total number of portfolio holdings.
    """
    replacement_stocks = portfolio_size - len(kept_positions)
    buy_list = ranking_table.loc[~ranking_table.index.isin(kept_positions.keys())][
        :replacement_stocks
    ]
    new_portfolio = pd.concat(
        (buy_list, ranking_table.loc[ranking_table.index.isin(kept_positions.keys())])
    )
    """
    Calculate inverse volatility for stocks, 
    and make target position weights.
    """
    for con_root_symbol, rank in new_portfolio.items():
        weight = 1 / (portfolio_size + 1)
        continuation = continuous_future(
                                        con_root_symbol, 
                                        offset=0, 
                                        roll='calendar',
                                        adjustment='add'
                                        )
        # Get the current contract of the continuation
        contract = data.current(continuation, 'contract')
        
        if con_root_symbol in kept_positions.keys():
            order_target_percent(kept_positions[con_root_symbol], weight)
        else:
            if ranking_table[con_root_symbol] > minimum_momentum:
                order_target_percent(contract, weight)

def analyze(context=None, results=None):
    # Plot the portfolio and asset data.
    results.algorithm_period_return.plot()
    results.benchmark_period_return.plot()
    plt.grid(True)
    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.show()
    

capital_base = 50000000 
calendar_name = 'TEJ' 
start_dt = pd.Timestamp('2020-01-02', tz='utc') 
end_dt = pd.Timestamp('2024-12-31', tz='utc')

# Running a Backtest
results = run_algorithm(start=start_dt, 
                        end=end_dt, 
                        initialize=initialize, 
                        #handle_data = handle_data, 
                        capital_base=capital_base, 
                        data_frequency='daily', 
                        bundle='tquant_future', 
                        analyze = analyze,
                        trading_calendar=get_calendar(calendar_name), ) 
# %% [code] cell 26
def analyze(context=None, results=None):
    # Plot the portfolio and asset data.
    results.algorithm_period_return.plot()
    results.benchmark_period_return.plot()
    plt.grid(True)
    # Show the plot.
    plt.gcf().set_size_inches(18, 8)
    plt.legend()
    plt.show()
analyze(results=results)
