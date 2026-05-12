# -*- coding: utf-8 -*-
# Auto-generated from TQ_月營收成長率策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # TQuant Lab 交易策略開發實作-以月營收成長率為選股指標
#
# 本範例運用TQuant Lab為研究工具，以月營收成長率作為選股指標建立交易策略，並回測分析其績效表現。交易策略建立流程涵蓋以下 7 個步驟，以下依此分為 7 個章節說明。
#
# 1. 匯入套件 (Import Packages)
#
# 2. 獲取歷史資料 (Get History Data) 
# 3. 將交易資料綁入zipline回測架構中 (Bundle)
# 4. 因子研究 (Factor Research)
# 5. 建構策略 (Strategy Developement)
# 6. 回測 (Backtest)
# 7. 策略績效分析 (Performance Analysis)

# %% [markdown] cell 1
# ## 1. 匯入套件 (Import Packages)
#
# 本節示範匯入TQuant Lab 的3個主要套件，分別說明相關功能、安裝方法與說明網頁。另外也匯入python常用的套件。
# - **`TejToolAPI`: 收集資料、資料清洗<br>**
#      - pip install tej-tool-api
#         - https://pypi.org/project/tej-tool-api/
#         - 設定api_key -> 參加試用 or 線上購買
#         
# - **`alphalens:` 因子研究**
#
#
# - **`zipline:` 建構指標、回測**
#     - https://pypi.org/project/zipline-tej/
#
# - **`pyfolio:` 策略績效分析**
# - **`pandas, numpy, matplotlib, seaborn: 其他常用套件`**

# %% [code] cell 2
import os
os.environ['TEJAPI_KEY'] = "Your Key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw/"
import TejToolAPI
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import alphalens
import seaborn as sns
from scipy import stats
from zipline.pipeline import Pipeline
from zipline.pipeline.data import TWEquityPricing
from zipline.pipeline.factors import CustomFactor
from zipline.pipeline.factors import Returns, AverageDollarVolume
from logbook import Logger, StderrHandler, INFO

# %% [code] cell 3
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [markdown] cell 4
# ## 2. 獲取歷史資料 Get History Data
#
# 本節示範收集建立交易策略需要的相關資料，並展示儲存和取出方法，並分3小節依序說明。
#
# ### 2.1 TejToolAPI.get_history_data
# 使用 `TejToolAPI.get_history_data` 一鍵整併市場、財務、月營收和籌碼數據。
#
# 參數使用:
# - tickers: 上市櫃全樣本(含下市櫃) <br>
# - columns:  <br>
#     - 屬性資料: 產業別
#     - 市場資料: 開盤價, 收盤價, roi<br>
#     - 籌碼資料: 外資買賣超金額_元<br>
#     - 月營收: 月營收成長率_YoY<br>
#     - 財務資料: 營業毛利率, 營業利益率, 稅後淨利率,  業外收支率, 營收成長率,
#  營業毛利成長率, 營業利益成長率, 稅後淨利成長率, 淨值成長率, eps<br>
# <br>
# - period:
#     - start: 2020-01-01
#     - end  : 2023-11-08

# %% [code] cell 5
from zipline.sources.TEJ_Api_Data import get_universe

start = '2020-01-01'
end = '2023-11-08'

start_dt = pd.Timestamp(start, tz='utc')
end_dt = pd.Timestamp(end, tz='utc')

pool = get_universe(start, end, mkt = ['TWSE', 'OTC'], stktp_e = 'Common Stock')
pool[0:10]

# %% [code] cell 6
columns = ['Industry_Eng','開盤價','收盤價', 'roi', 'YoY_Monthly_Sales', 'eps', '外資買賣超金額_元','營業毛利率', '營業利益率', '稅後淨利率', '業外收支率', '營收成長率', '營業毛利成長率', '營業利益成長率', '稅後淨利成長率', '淨值成長率','Inventories', 'mktcap']
data = TejToolAPI.get_history_data(ticker=pool, columns=columns, transfer_to_chinese=False, start = start, end = end)
data = data.sort_values(['coid','mdate'])
data

# %% [markdown] cell 7
# ### 2.2 Store Data into DataBase
# 將資料存進資料庫

# %% [code] cell 8
import sqlite3
# 創建或連接到SQLite數據庫
conn = sqlite3.connect('your_database.db')
# 假設你的DataFrame名稱為 your_table_name，並希望將其寫入名為'table_name'的表
table_name = 'your_table_name'
data['mdate'] = data['mdate'].astype('datetime64[ns]')
data.to_sql(table_name, conn, if_exists='replace', index=False)

conn.close()

# %% [markdown] cell 9
# ### 2.3 Extract Data from Database
# 從資料庫取出資料

# %% [code] cell 10
import sqlite3
conn = sqlite3.connect('your_database.db')
table_name = 'your_table_name'
script = f'''
select * from {table_name}
'''
new_data = pd.read_sql(script, conn)
new_data

# %% [markdown] cell 11
# ## 3. 將交易資料綁入zipline回測架構中 (Bundle)
#
# zipline 為 TQuant Lab 的回測引擎，旨要實現模擬交易策略，回測特定歷史區間內，策略是否具有獲利能力。在策略模擬回測前，需要先準備研究樣本的價量資料，並綁入(Bundle)zipline，並在完成後取出資料檢視，過程涵蓋以下3個步驟。
#
# 1. 準備 zipline 回測要用的資料<br>
# 2. 使用 !zipline ingest -b tquant 綁定回測資料<br>
# 3. 使用 get_bundle 檢視回測資料<br>

# %% [markdown] cell 12
# ### 3.1 準備資料
#
# - `os.environ['ticker']`：上市櫃全樣本(含下市櫃) 的股票代碼與加權報酬指數代碼(IR0001)
# - `os.environ['mdate']` ：設定需要價量資料的起訖日，為2020-01-01~2023-11-08

# %% [code] cell 13
tickers = ' '.join(pool+['IR0001'])

os.environ['mdate'] = start+' '+end
os.environ['ticker'] = tickers

# %% [markdown] cell 14
# ### 3.2 綁入資料 

# %% [code] cell 15
# !zipline ingest -b tquant

# %% [markdown] cell 16
# ### 3.3 檢視資料
#
# 運用`get_bundle`函數取出Bundle入zipline的資料，需要設定以下4個參數。 
#
#  - `bundle_name  `: tquant
#  - `calendar_name`: TEJ
#  - `start_dt     `: 2020-01-01
#  - `end_dt       `: 2023-11-08

# %% [code] cell 17
from zipline.data.data_portal import get_bundle
from zipline.data import bundles

bundle_name = 'tquant'
bundle = bundles.load(bundle_name)


df_bundle = get_bundle(bundle_name='tquant',
                        calendar_name='TEJ',
                        start_dt=start_dt,
                        end_dt=end_dt)
df_bundle

# %% [markdown] cell 18
# ## 4. 因子研究 (Factor Research)
# 使用 alphalens 進行因子分析
# - Returns（報酬率分析）
# - Information（資訊分析）
# - Autocorrelation（自相關分析）

# %% [code] cell 19
data.mdate = pd.to_datetime(data.mdate, utc =True)
predictive_factor = data[['mdate','coid','YoY_Monthly_Sales']].set_index(['mdate','coid']).unstack('coid')
predictive_factor = predictive_factor.stack()

# %% [code] cell 20
predictive_factor

# %% [code] cell 21
df_bundle['date'] = pd.to_datetime(df_bundle['date'] , utc= True)
pricing = df_bundle[['date','symbol','open_adj']].set_index(['date','symbol']).iloc[1:].\
                                              unstack('symbol')['open_adj']
pricing = pricing.shift(-1)
pricing.head(6)

# %% [code] cell 22
factor_data = alphalens.utils.get_clean_factor_and_forward_returns(predictive_factor,
                                                                   pricing,
                                                                   quantiles=5,
                                                                   bins=None,
                                                                   )

# %% [code] cell 23
alphalens.tears.create_full_tear_sheet(factor_data)

# %% [markdown] cell 24
# ## 5. 建構策略 (Strategy Developement)
#
# 本章節將運用`zipline.pipeline`的相關函數來建立交易策略的買賣訊號。<br>
# 以下過程:<br> 
# **(1)** 定義 `CustomDataset` 函數: 定義策略需要的基本面變數(月營收成長率、毛利成長率、營業利益成長率、淨利成長率、產業別)。<br>
#  **(2)** 使用 `DataFrameLoader` 函數，將第二節中用`TejToolAPI`函數抓取的基本面資料寫入`CustomDataset`函數定義的變數。<br>
# **(3)** 定義 `compute_signals` 函數來設定篩選條件排除不符合條件的股票，以及門檻條件過濾出買進與賣出的股票，並轉換成買賣訊號。<br> 
# **(4)** 最後利用 `run_pipeline` 函數產出買賣訊號整合成DataFrame輸出。

# %% [markdown] cell 25
# ### 5.1 Define CustomDataset
# 創建 CustomDataset 物件 (該物件需繼承 `zipline.pipeline.data.dataset.DataSet`)。CustomDataset 定義每個欄位的資料型態，EX: int, float, str。另外也需要定義資料的地區(如本範例使用台灣地區的交易日)。
#
# - 欄位:<br>
#     - 月營收成長率_YoY: YoY_Monthly_Sales<br>
#     - 毛利成長率: Gross_Margin_Growth_Rate_A<br>
#     - 營業利益成長率: Operating_Income_Rate_percent_A<br>
#     - 淨利成長率: Net_Income_Rate_percent_A<br>
#     - 產業別: Industry<br>
# - domain (地區):<br>
#     - 透過domain可以限制該Dataset只能使用在domain相同的Pipelines中。
#     - domain中包含calendar及two-character country code兩種資訊，台灣的domain為TW_EQUITIES、country code為TW、calendar為TEJ或TEJ_XTAI。 (modified by TEJ Research Team)

# %% [code] cell 26
from zipline.pipeline.data.dataset import Column, DataSet
from zipline.pipeline.domain import TW_EQUITIES

class CustomDataset(DataSet):
    
    Market_Cap_Dollars = Column(dtype=float)
    YoY_Monthly_Sales = Column(dtype=float)
    Gross_Margin_Growth_Rate_A = Column(dtype=float)
    Operating_Income_Growth_Rate_A = Column(dtype=float)
    Net_Income_Growth_Rate_A = Column(dtype=float)
    Inventories_A = Column(dtype=float)
    Industry = Column(dtype=object)
    
    domain = TW_EQUITIES

# %% [markdown] cell 27
# ### 5.2 Transform Data Throught DataFrameLoader
# 透過 `DataFrameLoader` 將基本面資料寫入`CustomDataset` 對應的欄位。

# %% [code] cell 28
sids = bundle.asset_finder.equities_sids
assets = bundle.asset_finder.retrieve_all(sids)
symbol_mapping_sid = {i.symbol:i.sid for i in assets}

transform_data = data.set_index(['coid', 'mdate']).unstack('coid')
transform_data = transform_data.rename(columns = symbol_mapping_sid)

# %% [code] cell 29
transform_data.head(5)

# %% [code] cell 30
from zipline.pipeline.loaders.frame import DataFrameLoader

inputs=[CustomDataset.YoY_Monthly_Sales,
        CustomDataset.Gross_Margin_Growth_Rate_A,
        CustomDataset.Operating_Income_Growth_Rate_A,
        CustomDataset.Net_Income_Growth_Rate_A,
        CustomDataset.Inventories_A,
        CustomDataset.Market_Cap_Dollars
        ]
Custom_loader = {i:DataFrameLoader(column=i, baseline=transform_data[i.name]) for i in inputs}
Custom_loader

# %% [markdown] cell 31
# ### 5.3 Create Signal
# 利用`CustomDataset`的欄位定義交易策略的篩選、過濾指標。<br>
# 以`毛利成長率>0`、`營業利益率>0`、`淨利成長率>0`、為篩選指標，排除不符合此條件的股票。使用`月營收成長率`作為排序指標，買進月營收排名前 30 的股票，以此作為買賣的交易訊號。

# %% [code] cell 32
from zipline.pipeline.filters import StaticAssets

def compute_signals():
    # filter
    gross_margin_filter = (CustomDataset.Gross_Margin_Growth_Rate_A.latest > 0)
    operating_income_filter = (CustomDataset.Operating_Income_Growth_Rate_A.latest > 0)
    net_income_filter = (CustomDataset.Net_Income_Growth_Rate_A.latest > 0)
    # mv_filter = CustomDataset.Market_Cap_Dollars.latest.percentile_between(min_percentile=50, max_percentile= 100)

    mask =  gross_margin_filter\
            & net_income_filter \
            & operating_income_filter\
            # & mv_filter 
            
    # signals
    MS = CustomDataset.YoY_Monthly_Sales.latest
    signals = MS.zscore(mask = mask)
    

    return Pipeline(columns={
        'signals' : signals,
        'YoY_Monthly_Sales' : MS,
        'filters': mask,
        'longs' : signals.top(30),
        },
    )

# %% [code] cell 33
from zipline.pipeline import SimplePipelineEngine
from zipline.pipeline.data import EquityPricing
from zipline.pipeline.loaders import EquityPricingLoader
pricing_loader = EquityPricingLoader.without_fx(bundle.equity_daily_bar_reader,
                                                bundle.adjustment_reader)
def choose_loader(column):
    if column.name in EquityPricing._column_names:
        return pricing_loader
    elif column.name in CustomDataset._column_names:     
        return Custom_loader[column]
    else:
        raise Exception('Column not available')
    
engine = SimplePipelineEngine(get_loader = choose_loader,
                              asset_finder = bundle.asset_finder,
                              default_domain = TW_EQUITIES)

# %% [markdown] cell 34
# ### 5.4 Run Pipeline
# 利用`run_pipeline`函數，將上一小節使用的相關欄位、定義的篩選指標、買賣的交易訊號整併，並輸出成MultiIndex(level_0=date, level_1asset)的DataFrame輸出。

# %% [code] cell 35
pipeline_result = engine.run_pipeline(compute_signals(), start, end)
pipeline_result

# %% [code] cell 36
pipeline_result[(pipeline_result['longs']==True)]

# %% [markdown] cell 37
# ## 6. 回測 (Backtest)
# zipline 核心功能
# 1. 定義 initialize 設定
#
# 2. 定義 rebalance 條件設定
# 3. 定義 record_vars 交易過程資訊
# 4. 定義 before_trading_start
# 5. 執行回測

# %% [markdown] cell 38
# ### 6.1 Define initialize
# 屬性:
# - context.n_longs: 長部位檔數
# - context.n_shorts: 短部位檔數
# - context.min_positions: 最小持倉數
# - context.universe: 股票池(同前面定義的ticker)
# - context.tradeday: 執行交易日(未定義則為每日交易)
# - context.set_benchmark: 設定set_benchmark<br>
#
# 設定 benchmark:<br>
# context.set_benchmark(symbol('IR0001')) -> IR0001 為台灣加權報酬指數
#
# 設定交易成本:<br>
# set_commission(commission.PerDollar(cost=commission_cost))
#
# 設定滑價:<br>
# set_slippage(slippage.FixedSlippage(spread=0.00))

# %% [code] cell 39
## 設定每月交易
from zipline.utils.calendar_utils import get_calendar 
tz = 'UTC'
calendar_name='TEJ'
_tradeday = [pd.Timestamp(year=i, month=m, day=15,tz=tz) 
             for i in range(int(start_dt.strftime('%Y')), int(end_dt.strftime('%Y'))+1) for m in range(1,13)
             if pd.Timestamp(year=i, month=m, day=15,tz=tz) <= end_dt]
                              
tradeday= [get_calendar(calendar_name).next_open(pd.Timestamp(i)).strftime('%Y-%m-%d')
           if  get_calendar(calendar_name).is_session(i)==False
           else i.strftime('%Y-%m-%d') 
           for i in _tradeday]

tradeday

# %% [code] cell 40
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
                         get_open_orders,
                         cancel_order
                         )

from zipline.finance import commission
from zipline.utils.events import date_rules, time_rules
from collections import defaultdict
commission_cost = 0.001425 + 0.003 / 2

def initialize(context):
    """
    Called once at the start of the algorithm.
    """

    context.universe = assets
    context.tradeday = tradeday
    
    context.set_benchmark(symbol('IR0001'))
    
    context.longs = []
    context.shorts = []
    
    #   交易成本
    set_commission(commission.PerDollar(cost=commission_cost))

    #     schedule_function
    schedule_function(func=rebalance,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_open)
    
    schedule_function(func=record_vars,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close)

    pipeline = compute_signals()
    attach_pipeline(pipeline, 'signals')

# %% [markdown] cell 41
# ### 6.2 Define Rebalance 定義**再平衡**條件
#
# 若當前時點`get_datetime().strftime('%Y-%m-%d')`為預先設定之交易日（`context.tradeday`），則進行再平衡。  
#
#
# #### 下單方式：
# ##### 1. Cancel
#
# ```python
# ## Cancel
# open_orders = get_open_orders()
# for asset in open_orders:
#     for i in open_orders[asset]:
#         cancel_order(i)   
# ```
# - 取得（`get_open_orders()`）並取消（`cancel_order(i)`）帳上所有未完全成交的訂單。
#
# ##### 2. Divest
# ```python
# ## Divest
# for stock, trade in context.trades.items():
#     if not trade:
#         order_target(stock, 0)
#     else:
#         trades[trade].append(stock)
# ```
# - `stock`與`trades`：
#   - 來自於`context.trades`，而`context.trades`來自於pipeline中的`'longs'`欄位，並在`before_trading_start`階段產出。
#   - `'longs'`欄位是布林值（如5.4節）。若為True，則代表該股票是本期預計要持有的標的。
#   - 迴圈中的`stock`是標的名稱、`trades`為0或1。若為本期預計要持有的標的則`trades=1`，反之為0。
# - 若`trades=0`，代表本期**不需要**持有該檔股票，所以透過`order_target(stock, 0)`，出清帳上所有持股。
# - 若`trades=1`，代表本期**需持有**該檔股票，這邊透過`trades[trade].append(stock)`將所有要持有的股票，存入`trades`中（`trades`是一個`defaultdict(list)`）。
# <br> 
# <br>
#
# ##### 3. Long
# ```python
# ## Long Only
# context.longs = len(trades[1])
# for stock in trades[1]:
#     order_target_percent(stock, 1 / context.longs * 0.8)
# ```
#    - `trades[1]`：取出`trades=1`的股票利用迴圈方式搭配`order_target_percent`下單。
#    - 權數為`1 / context.longs * 0.8`。其中，`context.longs`為本期預計要持有的標的數目；而0.8是緩衝值，避免動用到槓桿（可以設定0~1的值）。實質上這個加權方式就是**等權重**加權。 

# %% [code] cell 42
def rebalance(context, data):
    """
    Execute orders according to schedule_function() date & time rules.
    """
    trades = defaultdict(list)
    
    
    if get_datetime().strftime('%Y-%m-%d') in context.tradeday: 
        # print(context.trades, len(context.trades))
        
        ## Cancel
        open_orders = get_open_orders()
        for asset in open_orders:
            for i in open_orders[asset]:
                cancel_order(i)                
                log.info('Cancel_order(month_start):' + \
                       " created: " + str(i.created.strftime('%Y-%m-%d')) + \
                         " asset: " + str(i.sid) + \
                         ", amount: " + str(i.amount)+\
                         ", filled: " + str(i.filled)) 
        ## Divest
        for stock, trade in context.trades.items():
            if not trade:
                order_target(stock, 0)
            else:
                trades[trade].append(stock)
        ## Long Only
        context.longs = len(trades[1])
        for stock in trades[1]:
            order_target_percent(stock, 1 / context.longs * 0.8)

# %% [markdown] cell 43
# ### 6.3 Define Record variables
# 紀錄交易的中間資訊
# - context.account.leverage: 帳戶的槓桿比率
#
#
# - context.longs
# - context.shorts

# %% [code] cell 44
def record_vars(context, data):
    """
    Plot variables at the end of each day.
    """

    record(leverage=context.account.leverage,
           close=data.current(context.universe, 'close'),
           longs=context.longs,
           )

# %% [markdown] cell 45
# ### 6.4 Define before_trading_start
# - output: 產生 pipeline 運算後的 signals
#
#
# - context.trades: 是一個pandas.Series，將本期預計要持有的標的標示為1，反之為0。

# %% [code] cell 46
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    output = pipeline_output('signals')
    context.output = output
    context.trades = (output['longs'].astype(int)
                      .reset_index()
                      .drop_duplicates()
                      .set_index('index')
                      .squeeze())

# %% [code] cell 47
def analyze(context, perf):
    
    fig = plt.figure(figsize=(16, 12))
    
    # First chart(累計報酬)
    ax = fig.add_subplot(311) 
    ax.set_title('Strategy Results') 
    ax.plot(perf['algorithm_period_return'], linestyle='-', 
                label='algorithm period return', linewidth=3.0)
    ax.plot(perf['benchmark_period_return'], linestyle='-', 
                label='benchmark period return', linewidth=3.0)
    ax.legend()
    ax.grid(False)
    
    # Second chart(ending_cash)->觀察是否超買
    ax = fig.add_subplot(312)
    ax.plot(perf['ending_cash'], 
            label='ending_cash', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(True)

# %% [markdown] cell 48
# ### 6.5 Run Algorithm
# 執行回測

# %% [code] cell 49
from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar

capital_base = 1e6
calendar_name = 'TEJ'

# Running a Backtest
results = run_algorithm(start=start_dt,            
                        end=end_dt,                          
                        initialize=initialize,
                        before_trading_start=before_trading_start,
                        capital_base=capital_base,
                        data_frequency='daily',
                        analyze=analyze,
                        bundle=bundle_name,
                        trading_calendar=get_calendar(calendar_name),
                        custom_loader=Custom_loader)

# %% [code] cell 50
results.T

# %% [markdown] cell 51
# ## 7. 策略績效分析 (Performance Analysis)
#
# 運用`PyFolio`進行Performance Analysis 

# %% [code] cell 52
import pyfolio as pf
from pyfolio.utils import extract_rets_pos_txn_from_zipline
from pyfolio.plotting import (plot_perf_stats,
                              show_perf_stats,
                              plot_rolling_beta,
                              plot_rolling_returns,
                              plot_rolling_sharpe,
                              plot_drawdown_periods,
                              plot_drawdown_underwater)
from pyfolio.tears import *
from pyfolio.timeseries import (perf_stats,
                                extract_interesting_date_ranges,
                                sharpe_ratio,
                                sortino_ratio)

import empyrical

# %% [markdown] cell 53
# ### 7.1 Detail in Transaction
# - returns
# - positions
# - transactions

# %% [code] cell 54
returns, positions, transactions = pf.utils.extract_rets_pos_txn_from_zipline(results)

# %% [code] cell 55
positions

# %% [code] cell 56
transactions

# %% [markdown] cell 57
# ### 7.2 Performance Visualization
# - 敘述統計表
# - 累計報酬率圖表
# - 最大回檔
# - 前10大持股
# - rolling beta, volatility, sharpe ratio  

# %% [code] cell 58
pf.tears.create_full_tear_sheet(returns,
                                     positions=positions,
                                     benchmark_rets=results['benchmark_return'],
                                     transactions=transactions)
