# -*- coding: utf-8 -*-
# Auto-generated from TQ_月營收成長率策略_simple_algo.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # TQuant Lab 交易策略開發實作-以月營收成長率為選股指標
#
# 本範例運用TQuant Lab為研究工具，以月營收成長率作為選股指標建立交易策略，並回測分析其績效表現。交易策略建立流程涵蓋以下 6 個步驟，以下依此分為 6 個章節說明。
#
# 1. 匯入套件 (Import Packages)
# 2. 將交易資料綁入zipline回測架構中 (Get History Data & Bundle)
# 3. 建構策略 (Strategy Developement)
# 4. 因子研究 (Factor Research)
# 5. 回測 (Backtest)
# 6. 策略績效分析 (Performance Analysis)

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
#
#     - https://pypi.org/project/zipline-tej/
#   
#
# - **`pyfolio:` 策略績效分析**
# - **`pandas, numpy, matplotlib, seaborn: 其他常用套件`**

# %% [code] cell 2
import os
os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
import TejToolAPI
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import alphalens
from zipline.pipeline import Pipeline
from logbook import Logger, StderrHandler, INFO

# %% [code] cell 3
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [markdown] cell 4
# ## 2. 將交易資料綁入zipline回測架構中 (Bundle)
#
# zipline 為 TQuant Lab 的回測引擎，旨要實現模擬交易策略，回測特定歷史區間內，策略是否具有獲利能力。在策略模擬回測前，需要先準備研究樣本的價量資料，並綁入(Bundle)zipline，並在完成後取出資料檢視，過程涵蓋以下3個步驟。<br>
#
# 1. 設定 bundle 所需要的參數<br>
#     - mdate, ticker, fields
# 2. 使用 !zipline ingest -b bundle_name 綁定回測資料<br>
#     - bundle_name -> ex: tquant,  fundamentals
# 3. 使用 get_bundle, get_fundamentals 檢視回測資料<br>
#
# - 價量資料 bundle:<br>
#     1. 設定參數: mdate, ticker<br>
#     
#     2. 使用 !zipline ingest -b tquant 綁定財務資料<br>
#     3. 使用 get_bundle 檢視回測資料
#
#
# - 財務資料 bundle:<br>
#     1. 設定參數: mdate, ticker, fields<br>
#     
#     2. 使用 !zipline ingest -b fundamentals 綁定財務資料<br>
#     3. 使用 get_fundamentals 檢視回測資料<br>

# %% [markdown] cell 5
# ### 2.1 使用 get_universe 取得股票 ticker
# 樣本選擇: 2020-01-01 至 2023-11-08 所有上市櫃普通股

# %% [code] cell 6
from zipline.sources.TEJ_Api_Data import get_universe
start = '2020-01-01'
end = '2023-11-08'
pool = get_universe(start, end, mkt = ['TWSE', 'OTC'], stktp_e = 'Common Stock')
pool[0:10]

# %% [markdown] cell 7
# ### 2.2 設定 bundle 參數
#
# - `os.environ['ticker']`：上市櫃全樣本(含下市櫃) 的股票代碼與加權報酬指數代碼(IR0001)
# - `os.environ['mdate']` ：設定需要價量資料的起訖日，為2020-01-01~2023-11-08
# - `os.environ['fields']` ：設定財務資料的欄位，根據後續建立因子會需要用到的欄位來設定。

# %% [code] cell 8
start = '2020-01-01'
end = '2023-11-08'

start_dt = pd.Timestamp(start, tz='utc')
end_dt = pd.Timestamp(end, tz='utc')

tickers = ' '.join(pool)

fields = ''
columns = ['開盤價','收盤價', 'roi', 'YoY_Monthly_Sales', 'eps', '外資買賣超金額_元','營業毛利率', '營業利益率',
            '稅後淨利率', '業外收支率', '營收成長率', '營業毛利成長率', '營業利益成長率', '稅後淨利成長率', '淨值成長率','Inventories', 'mktcap']

fields = ' '.join(columns)

os.environ['mdate'] = start+' '+end
os.environ['ticker'] = tickers+' IR0001'
os.environ['fields'] = fields

# %% [markdown] cell 9
# ### 2.3 綁入資料 

# %% [code] cell 10
# !zipline ingest -b tquant

# %% [code] cell 11
# !zipline ingest -b fundamentals

# %% [markdown] cell 12
# ### 2.4 檢視資料
#
# 運用`get_bundle`, `get_fundamentals`函數取出綁入zipline的資料，需要設定以下4個參數。 <br>
# 1. get_bundle: 
#  - `bundle_name  `: tquant
#  - `calendar_name`: TEJ
#  - `start_dt     `: 2020-01-01
#  - `end_dt       `: 2023-11-08
# 2. get_fundamentals: 
#  - `bundle_name  `: fundamentals
#  - `fields       `: 欄位名稱(預設值為全部)
#  - `start_dt     `: 2020-01-01
#  - `end_dt       `: 2023-11-08

# %% [code] cell 13
from zipline.data.data_portal import get_bundle
from zipline.data import bundles

bundle_name = 'tquant'
bundle_data = bundles.load(bundle_name)


df_bundle = get_bundle(bundle_name='tquant',
                        calendar_name='TEJ',
                        start_dt=start_dt,
                        end_dt=end_dt)
df_bundle

# %% [code] cell 14
from zipline.data.data_portal import get_fundamentals
fundamentals = get_fundamentals(bundle_name = 'fundamentals',
                                start_dt = start_dt,
                                end_dt = end_dt,
                                dataframeloaders= False
                                )
fundamentals

# %% [markdown] cell 15
# ## 3. 建構策略 (Strategy Developement)
#
# 本章節將運用`zipline.pipeline`的相關函數來建立交易策略的買賣訊號。<br>
# 原本的過程:<br> 
# **(1)** 定義 `CustomDataset` 函數: 定義策略需要的基本面變數(月營收成長率、毛利成長率、營業利益成長率、淨利成長率、產業別)。<br>
# **(2)** 使用 `DataFrameLoader` 函數，將第二節中用`TejToolAPI`函數抓取的基本面資料寫入`CustomDataset`函數定義的變數。<br>
# **(3)** 定義 `compute_signals` 函數來設定篩選條件排除不符合條件的股票，以及門檻條件過濾出買進與賣出的股票，並轉換成買賣訊號。<br> 
# **(4)** 設定 `choose_loader` 函數來指定資料欄位分別要從哪個來源抓取。<br>
# **(5)** 最後利用 `run_pipeline` 函數產出買賣訊號整合成DataFrame輸出。<br> 
#
# 使用 fundamentals bundle 後:<br>
# **(1)** 定義 `compute_signals` 函數來設定篩選條件排除不符合條件的股票，以及門檻條件過濾出買進與賣出的股票，並轉換成買賣訊號。<br> 
# **(2)** 最後利用 `run_pipeline` 函數產出買賣訊號整合成DataFrame輸出。<br>

# %% [markdown] cell 16
# ### 3.2 Create Signal
# 資料: 
# - 欄位:<br>
#     - 月營收成長率_YoY: YoY_Monthly_Sales<br>
#     - 毛利成長率: Gross_Margin_Growth_Rate_A<br>
#     - 營業利益成長率: Operating_Income_Rate_percent_A<br>
#     - 淨利成長率: Net_Income_Rate_percent_A<br>
#     - 產業別: Industry<br>
# - domain (地區):<br>
#     - 透過 domain 可以限制該 Dataset 只能使用在 domain 相同的 Pipelines 中。
#     - domain 中包含 calendar 及 two-character country code 兩種資訊，台灣的 domain 為 TW_EQUITIES、country code為TW、calendar為TEJ或TEJ_XTAI。 (modified by TEJ Research Team)<br>
#
# 利用`TQDataSet`與`TQAltDataSet`的欄位定義交易策略的篩選、過濾指標。<br>
# 以`毛利成長率>0`、`營業利益成長率>0`、`淨利成長率>0`、為篩選指標，排除不符合此條件的股票。使用`月營收成長率`作為排序指標，買進月營收排名前 30 的股票，以此作為買賣的交易訊號。

# %% [code] cell 17
from zipline.pipeline.data import TQDataSet, TQAltDataSet, EquityPricing
from zipline.pipeline.factors import DailyReturns

def compute_signals():
    # filter
    gross_margin_filter = (TQDataSet.Gross_Margin_Growth_Rate_A.latest > 0)
    operating_income_filter = (TQDataSet.Operating_Income_Growth_Rate_A.latest > 0)
    net_income_filter = (TQDataSet.Net_Income_Growth_Rate_A.latest > 0)

    mask =  gross_margin_filter\
            & net_income_filter \
            & operating_income_filter\
            
    # signals
    ret = DailyReturns()
    MS = TQAltDataSet.YoY_Monthly_Sales.latest
    signals = MS.zscore(mask = mask)
    

    return Pipeline(columns={
        'signals' : signals,
        'YoY_Monthly_Sales' : MS,
        'filters': mask,
        'longs' : signals.top(30),
        'return': ret
        },
    )

# %% [markdown] cell 18
# ### 3.3 Run Pipeline
# 利用`run_pipeline`函數，將上一小節使用的相關欄位、定義的篩選指標、買賣的交易訊號整併，並輸出成MultiIndex(level_0=date, level_1asset)的DataFrame輸出。

# %% [code] cell 19
from zipline.TQresearch.tej_pipeline import run_pipeline
pipeline_result = run_pipeline(compute_signals(), start, end)
pipeline_result

# %% [code] cell 20
pipeline_result.loc[pipeline_result.index.get_level_values(1) == bundle_data.asset_finder.lookup_symbol('2330', None)]

# %% [code] cell 21
pipeline_result.query("longs == 1")

# %% [markdown] cell 22
# ## 4. 因子研究 (Factor Research)
# 使用 alphalens 進行因子分析
# - Returns（報酬率分析）
# - Information（資訊分析）
# - Turnover（週轉率分析）

# %% [markdown] cell 23
# ### 資料前處理
#
# alphalens的因子值使用pd.Series的格式輸入，index為時間與個股代碼，value為因子值

# %% [code] cell 24
predictive_factor = pipeline_result['YoY_Monthly_Sales']

predictive_factor

# %% [markdown] cell 25
# 用以分析因子預測好壞的報酬率使用get_prices取出

# %% [code] cell 26
from zipline.master import get_prices

pricing = get_prices(start_dt, end_dt, 'open')

pricing.tail()

# %% [markdown] cell 27
# * 輸入進get_clean_factor_and_forward_returns取得不同因子分組下的未來報酬率

# %% [code] cell 28
factor_data = alphalens.utils.get_clean_factor_and_forward_returns(predictive_factor,
                                                                   pricing,
                                                                   quantiles=5,
                                                                   bins=None,
                                                                   periods=(1,5,10,22)
                                                                   )

factor_data

# %% [markdown] cell 29
# ### Returns (報酬率分析)
#
# 觀察各個分組的平均報酬率與累積報酬率。
#   
#   * 各分組未來1D、5D、10D和22D平均報酬率
#   
#   * 各分組未來的累積報酬率

# %% [code] cell 30
mean_return_by_q, std_err_by_q = alphalens.performance.mean_return_by_quantile(factor_data, by_date=False)

# %% [code] cell 31
mean_return_by_q

# %% [markdown] cell 32
# * 轉換不同天期的未來報酬率為統一頻率（複合成長率呈現），用以直觀對比持有不同天期的結果

# %% [code] cell 33
mean_return_by_q_convertfreq=mean_return_by_q.apply(alphalens.utils.rate_of_return,
                                                    axis=0,
                                                    base_period=mean_return_by_q.columns[0])
mean_return_by_q_convertfreq

# %% [code] cell 34
alphalens.plotting.plot_quantile_returns_bar(mean_return_by_q_convertfreq)

# %% [code] cell 35
mean_return_by_q_daily, std_err = alphalens.performance.mean_return_by_quantile(factor_data, by_date=True)

alphalens.plotting.plot_cumulative_returns_by_quantile(mean_return_by_q_daily['1D'], period='1D')

# %% [markdown] cell 36
# ### Information Coefficient（資訊係數）
#
# 用以評估因子預測未來報酬率的好壞，以相關係數的概念計算，IC值介於-1 ~ 1之間，越接近1代表因子預測股價上漲的能力越好，反之越接近-1代表預測股價下跌的能力越好。
#
# *   未來1D、5D、10D和22D報酬率與因子的資訊係數
#   
# *   未來1D、5D、10D和22D資訊係數的分布圖

# %% [code] cell 37
ic = alphalens.performance.factor_information_coefficient(factor_data)

alphalens.plotting.plot_information_table(ic)

# %% [code] cell 38
alphalens.plotting.plot_ic_hist(ic)

# %% [markdown] cell 39
# ### Turnover（週轉率分析）
#
# * 因子週轉率：用以分析實際依照訊號進場後可能的週轉率問題，越高的週轉率意味著越高的交易成本。
#
# * 因子自我相關性：觀察當前因子值與前值的關聯性，若因子前後期的自我相關性過低代表投組依照因子篩選的股票越不一樣，投組本身可能太常換股導致週轉率過高。

# %% [code] cell 40
alphalens.tears.create_turnover_tear_sheet(factor_data)

# %% [markdown] cell 41
# ## 5. 回測（簡化版）
#
# 使用TEJ自製的簡化版Zipline回測引擎(TargetPercentPipeAlgo)，輕鬆在一行內設定所有回測參數，最少只需輸入策略pipeline即可進行回測
#
# 本次策略修改的相關參數：
#
# * 回測起迄日(start_session、end_session)：2020/01/01~2023/11/08
#   
# * 初始本金(capital_base)：1百萬
#   
# * 交易日(再平衡日)：每月十五號
#   
# * 最大槓桿：80%
#   
# * 策略pipeline：唯一必要的函式，需確保輸入進的pipeline中有longs與shorts等行，才能確定要買進與賣出之目標個股
#
# * 歷史成交量占比上限：15%，單一個股在歷史當日所能成交的最大上限，例如：台積電在11/08成交20,000張，設置15%意味著回測當時僅能成交20,000 * 0.15=3,000張
#
# * 衝擊係數：0.01，用以反映買進賣出時對股價的衝擊，完整公式：`price * (1 + price_impact * (volume_share ** 2))`

# %% [code] cell 42
from zipline.utils.calendar_utils import get_calendar 
cal = get_calendar('TEJ').all_sessions

cal = cal[cal >= '2020-01-01']

cal[-10:]

# %% [markdown] cell 43
# 自定義再平衡時間：每月15號進行再平衡，確保都有最新一期的營收公告

# %% [code] cell 44
cal = pd.DataFrame(cal).rename(columns={0:'date'})

cal['diff'] = cal['date'].transform(lambda x: x - pd.Timestamp(year=x.year, month=x.month, day=15, tz='UTC'))

cal.tail(10)

# %% [code] cell 45
tradeday = cal.groupby([cal['date'].dt.year, cal['date'].dt.month]).apply(lambda x: x[x['diff'].ge(pd.Timedelta(days=0))].head(1)).date.tolist()

tradeday = [str(i.date()) for i in tradeday]

tradeday[-5:]

# %% [markdown] cell 46
# 視覺化累積報酬率與期間可動用現金

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
    ax.grid(True)
    
    # Second chart(ending_cash)->觀察是否超買
    ax = fig.add_subplot(312)
    ax.plot(perf['ending_cash'], 
            label='ending_cash', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(True)

# %% [code] cell 48
from zipline.algo.pipeline_algo import *

algo = TargetPercentPipeAlgo(
                     start_session=start_dt,
                     end_session=end_dt,
                     capital_base=1e6,                
                     tradeday=tradeday,
                     max_leverage=0.80,
                     slippage_model=slippage.VolumeShareSlippage(volume_limit=0.15, price_impact=0.01),
                     pipeline=compute_signals,
                     analyze=analyze
)

results = algo.run()

# %% [markdown] cell 49
# ## 5. 回測（完整版）
# 原版的 zipline 核心功能
# 1. 定義 initialize 設定
#
# 2. 定義 rebalance 條件設定
# 3. 定義 record_vars 交易過程資訊
# 4. 定義 before_trading_start
# 5. 執行回測

# %% [markdown] cell 50
# ### 5.1 Define initialize
# 屬性:
#
# - context.universe: 股票池(同前面定義的ticker)
# - context.tradeday: 執行交易日(未定義則為每日交易)
# - context.set_benchmark: 設定set_benchmark<br>
#
# 設定 benchmark:<br>
# context.set_benchmark(symbol('IR0001')) -> IR0001 為台灣加權報酬指數
#
# 設定交易成本:<br>
# set_commission(commission.Custom_TW_Commission(min_trade_cost=20, discount=1, tax=0.003))
# - min_trade_cost=20 最低每筆交易費用20元
# - discount=1 代表無券商折扣，若有折扣可輸入(e.g. 0.5代表手續費打五折)
# - tax=0.003 代表交易稅0.3%
#
# 設定動態滑價:<br>
# set_slippage(slippage.VolumeShareSlippage(volume_limit=0.15, price_impact=0.01))

# %% [code] cell 51
from zipline.utils.calendar_utils import get_calendar 
cal = get_calendar('TEJ').all_sessions

cal = cal[cal >= '2020-01-01']

cal = pd.DataFrame(cal).rename(columns={0:'date'})

cal['diff'] = cal['date'].transform(lambda x: x - pd.Timestamp(year=x.year, month=x.month, day=15, tz='UTC'))

tradeday = cal.groupby([cal['date'].dt.year, cal['date'].dt.month]).apply(lambda x: x[x['diff'].ge(pd.Timedelta(days=0))].head(1)).date.tolist()

# %% [code] cell 52
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

from zipline.finance import commission, slippage
from zipline.utils.events import date_rules, time_rules
from collections import defaultdict

sids = bundle_data.asset_finder.equities_sids
assets = bundle_data.asset_finder.retrieve_all(sids)

import zipline.utils.events as Events

class rebalance_event(Events.StatelessRule):
    def __init__(self):
        pass
    def should_trigger(self, dt):
        return pd.Timestamp(dt.date() , tz = 'utc') in tradeday


def initialize(context):
    """
    Called once at the start of the algorithm.
    """

    context.universe = assets
    context.tradeday = tradeday
    
    context.set_benchmark(symbol('IR0001'))
    
    #   交易成本
    set_commission(commission.Custom_TW_Commission(min_trade_cost=20, discount=1, tax=0.003))
    
    #   滑價和成交量限制
    set_slippage(slippage.VolumeShareSlippage(volume_limit=0.15, price_impact=0.01))

    #    schedule_function
    schedule_function(func=rebalance,
                      date_rule=date_rules.every_day() & rebalance_event(),
                      time_rule=time_rules.market_open)
    
    schedule_function(func=record_vars,
                      date_rule=date_rules.every_day() & rebalance_event(),
                      time_rule=time_rules.market_close)

    pipeline = compute_signals()
    attach_pipeline(pipeline, 'signals')

# %% [markdown] cell 53
# ### 5.2 Define Rebalance 定義**再平衡**條件
#
# 首先刪除尚未完成的剩餘訂單，選取買入訊號為1的個股進行下單
#
# #### 下單方式：
# ##### 1. Cancel
#
# ```python
# open_orders = get_open_orders()
# for asset in open_orders:
#     for i in open_orders[asset]:
#         cancel_order(i)   
# ```
# - 取得（`get_open_orders()`）並取消（`cancel_order(i)`）帳上所有未完全成交的訂單。
#
# ==================================================================================================================
# ##### 2. Long
# ```python
# target = context.output
#
# if len(target) != 0:
#     longs = target.query("longs == 1")
# ```
# - target來自於`context.output`，也就是前述`compute_signals()`中的df，回測時系統會接收到一份當天日期的df表格，效果類似於`pipeline_result.loc['2023-11-08']`
# - 而我們只針對其中`longs`被標記為1的個股進行下單
#   
# ==================================================================================================================
# ##### 3. Place order
# ```python
# for stock in longs.index:
#     order_target_percent(stock, 1 / len(longs) * 0.8)
#
# for stock in context.portfolio.positions:
#     if stock not in longs.index:
#         order_target(stock, 0)
# ```
# - 先針對前述可買進的股票進行下單，此處使用等權重`1 / len(longs)`的方式，0.8是限制每一筆的下單比例，從而控制投組的槓桿比
# - 最後是針對原投組裡的個股`context.portfolio.positions`，若這些個股在本次沒有發出買進訊號，則予以清倉`order_target(stock, 0)`

# %% [code] cell 54
def rebalance(context, data):
    """
    Execute orders according to schedule_function() date & time rules.
    """

    #每月中刪除尚未完成的剩餘訂單
    open_orders = get_open_orders()
    for asset in open_orders:
        for i in open_orders[asset]:
            cancel_order(i)                
            log.info('Cancel_order(month_start):' + \
                    " created: " + str(i.created.strftime('%Y-%m-%d')) + \
                        " asset: " + str(i.sid) + \
                        ", amount: " + str(i.amount)+\
                        ", filled: " + str(i.filled)) 

    #下單
    target = context.output

    if len(target) != 0:
        longs = target.query("longs == 1")

        for stock in longs.index:
            order_target_percent(stock, 1 / len(longs) * 0.8)

        for stock in context.portfolio.positions:
            if stock not in longs.index:
                order_target(stock, 0)

# %% [markdown] cell 55
# ### 5.3 Define Record variables
# 紀錄交易的中間資訊
# - context.account.leverage: 帳戶的槓桿比率

# %% [code] cell 56
def record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    record(leverage=context.account.leverage,
           close=data.current(context.universe, 'close'),
           )

# %% [markdown] cell 57
# ### 5.4 Define before_trading_start
#
# - context.output: 輸出pipeline在回測當天的df表格，結果類似於`pipeline_result.loc['2023-11-08']`

# %% [code] cell 58
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('signals')
# %% [markdown] cell 59
# * 視覺化策略與同期大盤的累積報酬曲線
# * 下方附上同期間的剩餘現金

# %% [code] cell 60
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
    ax.grid(True)
    
    # Second chart(ending_cash)->觀察是否超買
    ax = fig.add_subplot(312)
    ax.plot(perf['ending_cash'], 
            label='ending_cash', linestyle='-', linewidth=1.0)
    ax.axhline(y=1,c='r',linewidth=0.3)
    ax.legend()
    ax.grid(True)

# %% [markdown] cell 61
# ### 5.5 Run Algorithm
# 執行回測

# %% [code] cell 62
from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar

capital_base = 1e6
calendar_name = 'TEJ'

start_dt = pd.Timestamp('2020-01-01', tz='utc')

end_dt = pd.Timestamp('2023-11-08', tz='utc')
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
                        )

# %% [code] cell 63
results

# %% [markdown] cell 64
# ## 6. 策略績效分析 (Performance Analysis)
#
# 運用`PyFolio`進行Performance Analysis 

# %% [code] cell 65
import pyfolio as pf
from pyfolio.utils import extract_rets_pos_txn_from_zipline
from pyfolio.tears import *

# %% [markdown] cell 66
# ### 6.1 Detail in Transaction
#
# 使用extract_rets_pos_txn_from_zipline取出下列三表，用以計算後續各種衍生報表
#
# - returns (日報酬率)
#   
# - positions (每日個股價值)
#   
# - transactions (交易總表)
#
# 註：上述三表的時間index須調整為UTC，否則某些報表無法正確顯示

# %% [code] cell 67
returns, positions, transactions = pf.utils.extract_rets_pos_txn_from_zipline(results)

benchmark_ret = results['benchmark_return']

returns.index = returns.index.tz_localize(None).tz_localize('utc')
transactions.index = transactions.index.tz_localize(None).tz_localize('utc')
positions.index = positions.index.tz_localize(None).tz_localize('utc')
benchmark_ret.index = benchmark_ret.index.tz_localize(None).tz_localize('utc')

# %% [markdown] cell 68
# ### 6.2 Performance Visualization
#
# 使用create_full_tear_sheet計算出完整的績效報表，例如：
#   
# - 累計報酬率圖表
# - 最大回檔
# - 前10大持股
# - rolling beta, volatility, sharpe ratio  

# %% [code] cell 69
pf.tears.create_full_tear_sheet(returns,
                                positions=positions,
                                benchmark_rets=results['benchmark_return'],
                                transactions=transactions)

# %% [markdown] cell 70
# ### 6.3 MAE分析圖表
#
# 運用海龜投資法則中的MAE(maximum adverse excursion, 最大不利方向)和MFE(maximum favorable excursion, 最大有利方向)分析進場訊號的好壞
#
# 所需步驟：
#
# 1. _groupby_consecutive：聚合時間相差不大的交易筆數(主要用於日內交易的調整)
#    
# 2. add_closing_transactions：將投組裡尚未出清的部位結算
#    
# 3. extract_round_trips：取出每筆交易的報表
#    
# 4. cal_mae_mfe：計算MAE、MFE和BMFE等指標
#    
# 5. plot_all_mae：視覺化上述指標、策略勝率和優勢比率

# %% [code] cell 71
from pyfolio import round_trips

closing_transactions = round_trips._groupby_consecutive(transactions.drop('dt', axis=1))

closing_transactions1 = round_trips.add_closing_transactions(positions, closing_transactions)

# %% [markdown] cell 72
# 計算每筆交易的報酬率與持有時間

# %% [code] cell 73
closing_transactions1

# %% [code] cell 74
rts1 = round_trips.extract_round_trips(returns, transactions, positions, False)

# %% [markdown] cell 75
# 計算每筆交易前20天的優勢比率、MAE等指標

# %% [code] cell 76
mae = round_trips.cal_mae_mfe(rts1, 20)

mae

# %% [code] cell 77
from pyfolio import plot_all_mae

plot_all_mae(mae)
