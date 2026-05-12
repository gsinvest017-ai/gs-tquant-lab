# -*- coding: utf-8 -*-
# Auto-generated from TQ_尋找Alpha.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 尋找 Alpha
#   
#     
# ## 大綱
#
# - ### 介紹
# - ### 資料集, 投資標的與資料處理
# - ### 因子研究
# - ### 投組建立與回測

# %% [markdown] cell 1
# # 1. 介紹

# %% [markdown] cell 2
# ### 方法論
# 1. 利用single index model找出alpha（$\alpha$）大的股票。
#    - $R_ {it} = \alpha_ {i} + \beta_ {i} R_ {mt} + \epsilon_ {it}$ 
#    - $R_ {it}$ 代表資產i在t-1至t期間的簡單報酬率（ROI）.
#    - $R_ {mt}$ 代表完全分散風險的投資組合（理應用等權重加權，但這邊為了簡化以發行量加權股價報酬指數替代）在t-1至t期間的簡單報酬率（ROI）  
#    
#    
# 2. 找出本益比（PER）小的股票。
# 3. 利用alpha大且本益比小的前50檔股票，並以等權重方式建構投資組合。
# 4. 每月再平衡。
#
# ### 參考資料
# - Sharpe, William F. (1963). A Simplified Model for Portfolio Analysis. Management Science. 9 (2): 277-93.
# - Sharpe, W.F. (1964). Capital asset prices: a theory of market equilibrium under conditions of risk. The Journal of Finance, 19(3), 425-442.
# - Jensen, M. C. (1968). The Performance of Mutual Funds in the Period 1945-1964. The Journal of Finance, 23, 389-416.
# - Berkin and Swedroe (2016). Your Complete Guide to Factor-Based Investing: The Way Smart Money Invests Today. BAM ALLIANCE Press.
# - 葉怡成（2020）。台股研究室：36種投資模型操作績效總體檢！。財經傳訊出版社
# - [尋找Alpha](https://www.tejwin.com/insight/%e5%b0%8b%e6%89%bealpha/)

# %% [markdown] cell 3
# # 2. 資料集與投資標的

# %% [markdown] cell 4
# ## Imports & Settings

# %% [code] cell 5
import pandas as pd
import datetime
import tejapi
import os

# set tej_key and base
os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"

# set benchmark
benchmark=['IR0001']

# set calendar
calendar_name = 'TEJ_XTAI'

# set bundle name
bundle_name = 'tquant'

# 取得回測資料所需原始資料
start = '2005-01-01'
end = '2023-08-25'

# 由文字型態轉為Timestamp，供回測使用
tz = 'UTC'
start_dt, end_dt = pd.Timestamp(start, tz = tz), pd.Timestamp(end, tz = tz)

# 設定os.environ['mdate'] = start+' '+end，供ingest bundle使用
os.environ['mdate'] = start_dt.strftime('%Y-%m-%d')+' '+end_dt.strftime('%Y-%m-%d')

import zipline

# %% [markdown] cell 6
# ## 投資標的

# %% [markdown] cell 7
# - 資料期間設定為**2005-01-01~2023-08-25**
# - 設定`os.environ['ticker']=公司碼`，供後續**ingest bundle**用。這邊僅使用上述時間段內**曾經上市**的公司做為樣本。

# %% [code] cell 8
from zipline.sources.TEJ_Api_Data import get_universe

StockList = get_universe(start, end, mkt = ['TWSE'], stktp_e = 'Common Stock')

os.environ['ticker'] = ' '.join(StockList + benchmark)

# %% [markdown] cell 9
# ## Ingest

# %% [code] cell 10
# !zipline ingest -b tquant

# %% [markdown] cell 11
# # 3. 資料前處理

# %% [markdown] cell 12
# ## Imports & Settings

# %% [code] cell 13
import warnings
warnings.filterwarnings('ignore')

# %% [code] cell 14
from time import time
import numpy as np
from logbook import Logger, StderrHandler, INFO
import matplotlib.pyplot as plt

from zipline import run_algorithm

from zipline.utils.run_algo import  (get_transaction_detail,
                                     get_record_vars)

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
                         order_target,
                         order_target_percent,
                         sid,
                         symbols,
                         symbol,
                         get_datetime,
                         set_benchmark,
                         get_open_orders,
                         cancel_order)

from zipline.sources.TEJ_Api_Data import (get_Treasury_Return,
                                          get_Benchmark_Return)

from TejToolAPI.TejToolAPI import *

from zipline.utils.calendar_utils import get_calendar

from zipline.data import bundles
from zipline.data.data_portal import DataPortal, get_bundle

from zipline.pipeline import Pipeline, CustomFactor, CustomClassifier
from zipline.pipeline.data import Column, DataSet, EquityPricing
from zipline.pipeline.domain import TW_EQUITIES 
from zipline.pipeline.loaders.frame import DataFrameLoader
from zipline.pipeline.loaders import EquityPricingLoader
from zipline.pipeline.engine import SimplePipelineEngine
from zipline.finance.commission import PerDollar

import empyrical as ep

# 設定log顯示方式
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [markdown] cell 15
# ## 連結其他資料庫以創造因子

# %% [markdown] cell 16
# ### Tej-tool-api

# %% [markdown] cell 17
# 利用Tej-tool-api的`get_history_data()`方法取得其他資料。
# <br>
#
# - **Market**：市場別。
# - **ROI**：報酬率。
# - **PER_TEJ**：TEJ計算之本益比。

# %% [code] cell 18
col = ['Market',
       'ROI',
       'PER_TEJ']

df_TEJ = get_history_data(ticker = StockList+benchmark,
                          columns = col,
                          start = start_dt,
                          end = end_dt,
                          transfer_to_chinese = False)

col = list(df_TEJ.columns.drop(['mdate','coid']))

# %% [markdown] cell 19
# ## 資料轉換

# %% [code] cell 20
# 使用`loads other datasets`前先檢查外部資料與bundle的公司碼，若外部資料有bundle沒有的公司碼，`loads other datasets()`會報錯。

other_datasets_coid=list(df_TEJ.coid.unique())
bundle_coid=list(StockList+benchmark)

# 獲取存在於other_datasets_coid中但不存在於bundle_coid中的元素
diff = list(set(other_datasets_coid).difference(set(bundle_coid)))

if len(diff)>0:
    print('請確認：','外部資料有但bundle沒有的公司碼(需處理)',diff)

# %% [code] cell 21
# 用來讀取先前ingest的bundle資料，後續就可以利用 `asset_finder.lookup_symbols(symbols, as_of_date=None)`取得`sid`資訊 
bundle = bundles.load(bundle_name)


def load_other_datasets(df_data, bundle, columns):
        
    dict_data = {}    
    df_data['coid']=df_data['coid'].astype(str)    
       
    for i in columns:
        if columns!=['coid','mdate']:               
            df_data1 = df_data[['coid', 'mdate']+[i]].set_index(['coid', 'mdate'])
            symbols = df_data1.index.get_level_values(0).unique().tolist()  
            assets = bundle.asset_finder.lookup_symbols(symbols, as_of_date=None)    
            sids = pd.Index([asset.sid for asset in assets])
            symbol_map = dict(zip(symbols, sids))
            dict_data[i] = (df_data1[i]
                .unstack('coid')
                .rename(columns=symbol_map)
                .tz_localize('UTC')
                           )
            
    return dict_data

dict_data = load_other_datasets(df_TEJ, bundle, col) 

# %% [markdown] cell 22
# ## 定義客製化 Dataset

# %% [code] cell 23
class OtherDatasets(DataSet):
     
    Market = Column(dtype=object)    
    ROI = Column(dtype=float)  
    PER_TEJ = Column(dtype=float)
 
    domain = TW_EQUITIES

# %% [code] cell 24
# `_column_names`：該屬性可以用來取得`DataSet`物件下定義的所有`Column`.
OtherDatasets()._column_names

# %% [markdown] cell 25
# ## Pipeline Loaders

# %% [code] cell 26
custom_loader = {}

inputs=[
        OtherDatasets.Market,
        OtherDatasets.ROI,
        OtherDatasets.PER_TEJ,  
        ]

for i in inputs:
    custom_loader[i]=DataFrameLoader(column=i,
                                     baseline=dict_data[i.name])
custom_loader

# %% [markdown] cell 27
# ## 建立 CustomFactor

# %% [code] cell 28
from scipy.stats import linregress
from zipline.errors import IncompatibleTerms
from numpy import broadcast_arrays

from zipline.assets import Asset
from zipline.pipeline.filters import SingleAsset, StaticAssets
from zipline.pipeline.term import AssetExists
from zipline.pipeline.sentinels import NotSpecified
from zipline.utils.input_validation import (
    expect_types,
    expect_dtypes,
    expect_bounded
)
from zipline.utils.numpy_utils import (
    float64_dtype,
    int64_dtype,
    object_dtype,
)


ALLOWED_DTYPES = (float64_dtype, int64_dtype)

        
class _RollingLinearRegressionOfRoi(CustomFactor):
    
    params = ("allowed_missing_days",)
    outputs = ["alpha", "beta", "r_value", "p_value", "stderr", "count"]
    
        
    @expect_dtypes(dependent=ALLOWED_DTYPES,
                   independent=ALLOWED_DTYPES)
    @expect_types(allowed_missing_days=int,
                  regression_length=int,
                  target=Asset)
    @expect_bounded(allowed_missing_days=(3, 30),
                    regression_length=(2, None),)
    def __new__(cls,
                dependent,
                independent,
                market,
                regression_length,
                allowed_missing_days,
                target,
                mask=NotSpecified):    
        
#         ndim:The dimensions of the term's output (1D or 2D).
        if independent.ndim == 2 and dependent.mask is not independent.mask:
            raise IncompatibleTerms(term_1=dependent, term_2=independent)
            
        return super(_RollingLinearRegressionOfRoi, cls).__new__(
            cls,
            inputs=[dependent, independent, market],
            window_length=regression_length,
            allowed_missing_days=allowed_missing_days,
            mask=mask,
        )
    
    @property
    def target(self):
        """Get the target of the calculation."""
        return self.inputs[1].asset   
    
    def compute(self, today, assets, out, dependent, independent, market, allowed_missing_days):
        
        alpha = out.alpha
        beta = out.beta
        r_value = out.r_value
        p_value = out.p_value
        stderr = out.stderr
        count = out.count

        def regress(y, x):
            regr_results = linregress(y=y,
                                      x=x)
            # `linregress` returns its results in the following order:
            # slope, intercept, r-value, p-value, stderr, count
            alpha[i] = regr_results[1]
            beta[i] = regr_results[0]
            r_value[i] = regr_results[2]
            p_value[i] = regr_results[3]
            stderr[i] = regr_results[4]
            count[i] = len(x)

        # If `independent` is a Slice or single column of data, broadcast it
        # out to the same shape as `dependent`, then compute column-wise. This
        # is efficient because each column of the broadcasted array only refers
        # to a single memory location.
        independent = broadcast_arrays(independent, dependent)[0]
                
        if self.target.symbol=='IR0001':
            target_market='TWSE'
        elif self.target.symbol=='IR0043':
            target_market='OTC'
            
        for i in range(len(out)):
            if np.all(market[-allowed_missing_days:,i]==np.full((allowed_missing_days,), target_market)):

                y = dependent[:, i]
                x = independent[:, i]
                
                # Remove missing values from array y
                y_cleaned = y[~np.isnan(y)]
                # Remove corresponding data from array x as well
                x_cleaned = x[~np.isnan(y)]
                   
                regress(y=y_cleaned,
                        x=x_cleaned)     
                
    def __repr__(self):
        return "{}(target={}, length={}, allowed_missing_days={})".format(
            type(self).__name__,
            self.target,
            self.window_length,
            self.params["allowed_missing_days"],
        ) 
    
class Roi(CustomFactor):
    
    window_safe = True
    inputs =  [OtherDatasets.ROI] 

    def compute(self, today, assets, out, ROI):
        out[:] = ROI[-1]


class Market(CustomClassifier):
#     CustomFactor dtype need to de float64_dtype

    dtype = object_dtype
    window_safe = True
    inputs = [OtherDatasets.Market] 

    def compute(self, today, assets, out, Market):
        out[:] = Market[-1]        

class RollingLinearRegressionOfRoi(_RollingLinearRegressionOfRoi):
    
#     Determines if a term is safe to be used as a windowed input.   
    window_safe = True
        
    def __new__(cls, regression_length, allowed_missing_days, target, mask=NotSpecified):
        # Use the `SingleAsset` filter here because it protects against
        # inputting a non-existent target asset.
        
        returns = Roi(
            window_length=regression_length,
            mask=(AssetExists() | SingleAsset(asset=target)),
        )
        
        market = Market(
            window_length=regression_length,
            mask=(AssetExists()),
        )
    
        return super(RollingLinearRegressionOfRoi, cls).__new__(
            cls,
            dependent=returns,
            independent=returns[target],
            market=market,
            regression_length=regression_length,
            allowed_missing_days=allowed_missing_days,
            target=target,
            mask=mask,
        )

# %% [markdown] cell 29
# ### Parameters
# - reg_length：以**過去63個交易日**資料計算。
# - allowed_missing_days：上市**滿3日**始計算。
# - target：為發行量加權股價報酬指數（**symbol='IR0001'**）
#
# 利用滾動回歸（Rolling regression），並以發行量加權股價報酬指數的ROI為自變數，個股的ROI為應變數，rolling window為63日得出alpha（$\alpha$）值。

# %% [code] cell 30
reg_length = 63         
allowed_missing_days = 3

# %% [markdown] cell 31
# ### Output
# - alpha_zscore：將股票利用alpha（$\alpha$）值由**低至高**進行排序（`rank`），並將排序值**標準化**（`zscore`）。
# - PER_zscore：將股票利用本益比（PER_TEJ）值由**高至低**進行排序（`rank(ascending=False)`），並將排序值**標準化**（`zscore`）。
# - signals：alpha_zscore + PER_zscore，也就是合成出來的因子。

# %% [code] cell 32
def compute_signals():  
    
    target = bundle.asset_finder.lookup_symbol('IR0001', as_of_date=None)
        
    rlrr_TWSE = RollingLinearRegressionOfRoi(regression_length=reg_length,
                                             allowed_missing_days=allowed_missing_days,
                                             target=target)
    
    beta = rlrr_TWSE.beta
    alpha = rlrr_TWSE.alpha
    count = rlrr_TWSE.count
    
    PER_zscore = OtherDatasets.PER_TEJ.latest.rank(ascending=False, method='min').zscore()
    alpha_zscore = alpha.rank(method='min').zscore()

    return Pipeline(columns = {
        'Market':OtherDatasets.Market.latest,
        'PER_TEJ':OtherDatasets.PER_TEJ.latest,
        'beta':beta,    
        'alpha':alpha,
        'alpha_zscore':alpha_zscore,
        'PER_zscore':PER_zscore,
        'count':count,
        'signals':alpha_zscore+PER_zscore
    }, 
                   )

# %% [markdown] cell 33
# ## 建立 Pipeline

# %% [code] cell 34
## Set the dataloader and create a Pipeline engine 
pricing_loader = EquityPricingLoader.without_fx(bundle.equity_daily_bar_reader,
                                                bundle.adjustment_reader)

# %% [code] cell 35
# Define the function for the get_loader parameter
def choose_loader(column):
    if column.name in EquityPricing._column_names:
        return pricing_loader
    elif column.name in OtherDatasets._column_names:     
        return custom_loader[column]
    else:
        raise Exception('Column not available')

# %% [code] cell 36
# Create a Pipeline engine
engine = SimplePipelineEngine(get_loader = choose_loader,
                              asset_finder = bundle.asset_finder,
                              default_domain = TW_EQUITIES)

# %% [code] cell 37
# set backtest date
# CustomFactor須確保有完整63日(reg_length)資料可以計算，故將`engine.run_pipeline`的start_date往前平移，形成algo_start_dt。
algo_start_dt = pd.Timestamp('2006-01-01', tz='UTC')
algo_end_dt = end_dt

algo_start_dt, algo_end_dt

# %% [markdown] cell 38
# ## Pipeline result

# %% [code] cell 39
# run_pipeline
pipeline_result = engine.run_pipeline(compute_signals(),
                                      algo_start_dt,
                                      algo_end_dt)

# %% [code] cell 40
pipeline_result

# %% [markdown] cell 41
# ## 資料轉換

# %% [markdown] cell 42
# ### Factor

# %% [code] cell 43
# 整理因子資料
factor = pipeline_result['signals']

# %% [code] cell 44
factor

# %% [markdown] cell 45
# ### Price

# %% [code] cell 46
df_bundle = get_bundle(bundle_name=bundle_name,
                       calendar_name=calendar_name,
                       start_dt=start_dt,
                       end_dt=end_dt)
df_bundle

# %% [code] cell 47
# 整理價格資料
prices = df_bundle[df_bundle['symbol']!=benchmark[0]]   # 排掉benchmark
prices = (prices[['date','asset','open_adj']].
                  set_index(['date','asset']).
                  unstack().
                  loc[:,'open_adj'])
prices

# %% [markdown] cell 48
# # 4. 因子研究

# %% [markdown] cell 49
# ## Imports & Settings

# %% [code] cell 50
import alphalens 
from alphalens.utils import get_clean_factor_and_forward_returns
from alphalens.tears import *

# %% [markdown] cell 51
# ## Data Preprocessing for Alphalens

# %% [markdown] cell 52
# - 以下案例將持有期（`periods`）設定為1、5、22、63、126天
# - 因子利用`factor`資料中的`signal`分為10組（`quantiles`=10）。

# %% [code] cell 53
HOLDING_PERIODS = (1,5,22,63,126)
QUANTILES = 10

alphalens_data = get_clean_factor_and_forward_returns(factor=factor,
                                                      prices=prices.shift(-1),
                                                      periods=HOLDING_PERIODS,
                                                      quantiles=QUANTILES,
                                                     )

# %% [markdown] cell 54
# - 下表中的`date`為日期；`asset`為股票代碼；1D、5D、22D、63D、126D為持有期；`factor`為因子值，數字越大代表alpha越大且PER越小，預期帶來更高的報酬；`factor_quantile`為樣本分組的組別。
# - 其中alpha最大且PER最小的公司分到第10組；alpha最小且PER最大的公司分到第1組。

# %% [code] cell 55
alphalens_data

# %% [markdown] cell 56
# ## Analysis
#
#
# ### Returns
# 這邊預期採用**long only strategy**，並將`long_short`設定為False且後續皆會採用非demeaned的平均報酬率（觀察絕對報酬率）進行計算。
#
# #### summary
# - 在五種持有期之下，`Ann. alpha`的結果顯示因子能獲得正的超額報酬；其中，持有期為22D時超額報酬最高。以`beta`來看，在五種持有期之下，beta皆為<1，代表其與市場的關聯性較小。
# - 從平均及累積報酬來看，在任一個持有期之下，第10組報酬率皆優於其餘各組別，顯示此因子可以區分出贏家股及輸家股。
# - 因子加權的效果劣於單純做多第10組的策略，因為第10組的報酬率優於其他組，納入其他組的股票只會拉低投組報酬，因此因子加權方式在這邊並不好用。
# - 後續以持有期為22D、純做多第10組股票為基礎當作投資策略進行回測。
#
# ### Information
#
# #### summary
# - 在五種持有期之下，`IC Mean`皆為正，且IC序列的p-value皆呈現顯著，代表因子與持有期報酬間呈現顯著正相關，具預測能力。然而，在持有期為63D、126D之下`IC Mean`並達到>0.05的標準。
# - 在五種持有期之下，IC在時間序列上大多的時間點皆為正（除金融海嘯外），代表因子在不同時間段均能維持預測能力。
#
# ### Turnover
#
# #### summary
# - 在所有持有期之下top quantile（Quantile 10）的因子周轉率幾乎是最低，代表若選擇該兩組股票建構投組其隱藏成本較低。

# %% [code] cell 57
create_full_tear_sheet(alphalens_data,
                       long_short=False,
                       by_group=False)

# %% [markdown] cell 58
# ## Conclusion
# - 這是一個有效因子，可以進行後續回測，考慮持有期22天的ic值>0.03，且Top Quantile的mean return最高，所以**回測時換股頻率先訂為1個月**。
# - 考量因子加權的累積報酬率並沒有優於單純以等權重方式做多第Top Quantile組股票的累積報酬率，故**投資策略先預設購買第9組股票，並以等權重加權**。

# %% [markdown] cell 59
# # 5. Portfolio Construction and Backtest

# %% [markdown] cell 60
# 利用Alphalens分析完後確認了因子是有效的，本節就可以利用這個因子來進行回測。

# %% [markdown] cell 61
# ## Pipeline

# %% [markdown] cell 62
# 以下的pipeline與第3節的類似，且Pipeline將會輸出**每天因子計算結果**及**布林值的買賣訊號**用來進行後續回測及分析。
#
# #### `compute_signals`
#
# **具體來說，這裡的`compute_signals()`作了以下幾件事情：**
# - 利用`signal`建立布林值訊號，並命名為'longs'。其中，符合條件（`top(50)`）的股票會回傳True，其餘回傳False。
# - 利用`mask`參數排除在該時點非上市的股票。

# %% [code] cell 63
def compute_signals():

    target = bundle.asset_finder.lookup_symbol('IR0001', as_of_date=None)
        
    rlrr_TWSE = RollingLinearRegressionOfRoi(regression_length=reg_length,
                                             allowed_missing_days=allowed_missing_days,
                                             target=target)
    
    twse_filter = (OtherDatasets.Market.latest.eq('TWSE'))

    mask = StaticAssets([symbol(i) for i in StockList]) & (twse_filter)
            
    alpha = rlrr_TWSE.alpha
    PER_zscore = OtherDatasets.PER_TEJ.latest.rank(ascending=False, method='min', mask=mask).zscore()
    alpha_zscore = alpha.rank(method='min', mask=mask).zscore()
    signal = PER_zscore+alpha_zscore
    
    longs = signal.top(50, mask=mask)
    
    return Pipeline(columns = {
            'longs':longs, 
            'twse_filter':twse_filter,
            'alpha_zscore':alpha_zscore,
            'PER_zscore':PER_zscore,
            'signal':signal}
                       )

# %% [markdown] cell 64
# ## 5.2 initialize

# %% [markdown] cell 65
# - 設定再平衡日期：回測時希望**每月**調整持股，故這邊產出每月第一個交易日日期（`tradeday`），供後續回測使用。
# - 目標槓桿：0.8
# - 滑價：VolumeShareSlippage
#   - volume_limit = 0.1（每日成交量限制10%）
#   - price_impact = 0.1

# %% [code] cell 66
# 交易傭金
commission_cost = 0.001425 + 0.003 / 2
# 目標槓桿
max_lev = 0.8
# 滑價
volume_limit = 0.1
price_impact = 0.1   
# 設定再平衡日期
freq = 'MS'   # QS-JUL  MS W
_tradeday = list(pd.date_range(start=algo_start_dt, end=end_dt, freq=freq))
tradeday = [get_calendar(calendar_name).next_open(pd.Timestamp(i)).strftime('%Y-%m-%d') if \
           get_calendar(calendar_name).is_session(i)==False else i.strftime('%Y-%m-%d') for i in _tradeday]
tradeday

# %% [code] cell 67
def initialize(context):
    """
    Called once at the start of the algorithm.
    Setup: register pipeline, schedule rebalancing, and set trading params
    """
    
    context.min_positions = 0
    context.universe = [symbol(i) for i in StockList]  
    context.trades = {}

#     再平衡日期
    context.tradeday = tradeday
    
#     交易成本    
    set_slippage(slippage.VolumeShareSlippage(volume_limit = volume_limit,
                                              price_impact = price_impact))
    set_commission(commission.PerDollar(cost=commission_cost))
    
#     benchmark  
    set_benchmark(symbol(benchmark[0]))
    
#     schedule_function
    schedule_function(func=rebalance,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_open)
    
    schedule_function(func=record_vars,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close)
    
#     pipeline
    pipeline = compute_signals()
    attach_pipeline(pipeline, 'signals')

# %% [markdown] cell 68
# ## 5.3 before_trading_start

# %% [code] cell 69
def before_trading_start(context, data):
    """
    Called every day before market open.(after initialize on the first day).
    Run factor pipeline
    """
    
    output = pipeline_output('signals')
    context.output = output

# %% [markdown] cell 70
# ## 5.4 rebalance

# %% [markdown] cell 71
# `rebalance()`為自創的函數，負責建立買賣策略、調整投資組合部位，並作為`schedule_function()`的參數。具體來說，這裡的`rebalance()`作了以下幾件事情：
#
# - 月初的時候（`context.tradeday`）：
#   - 先清掉取消上一個月未成交（完全成交）的單。
#   - 使用Pipeline產出的結果（即`context.output['longs']`）產出欲作多的清單。
#   - 生成`context.divest`變數，紀錄帳上現在有部位但在未來這期沒有要持有的股票。
#   - 透過`order_target()`方法出清`context.divest`中有記錄的股票。
#   - 透過`order_target_percent()`方法，並透過交易前一日的收盤價來計算所需購買的股數，且每檔股票的預期權重相等。

# %% [code] cell 72
def rebalance(context, data):
    """
    Execute orders according to schedule_function() date & time rules.
    """
    
    print('Current date(rebalance)＝' + str(get_datetime().date())) 
   
    context.list_longs = []
    context.divest = []
    context.month_weights = pd.Series(data={})
    
    
#     月初再平衡
    if get_datetime().strftime('%Y-%m-%d') in context.tradeday: 
        print('Current date(trade)＝' + str(get_datetime().date())) 
        
#         取消未成交的單        
        open_orders = get_open_orders()
        for asset in open_orders:
            for i in open_orders[asset]:
                cancel_order(i)                
                log.info('Cancel_order:' + \
                         " created: " + str(i.created.strftime('%Y-%m-%d')) + \
                         " asset: " + str(i.sid) + \
                         ", amount: " + str(i.amount)+ \
                         ", filled: " + str(i.filled))         

     
    #     建立買進清單   
        context.list_longs = list(set(context.output['longs'][context.output['longs']==True].index.to_list()))   

    #     建立賣出清單      
        context.divest = list(set(context.portfolio.positions.keys()) - set(context.list_longs)) 


    #     建立策略    
        context.N = len(context.list_longs)

        if context.N > context.min_positions:       
            for i in context.divest:
                order_target(i, 0)
            for i in context.list_longs:
                order_target_percent(i, 1 / context.N * max_lev)

        else:
            print('long positions=0')
   
    #     記錄每月月初權重         
        context.month_weights = context.portfolio.current_portfolio_weights      
           
    else:
        pass

#     記錄每日權重         
    context.weights = context.portfolio.current_portfolio_weights  

# %% [markdown] cell 73
# ## 5.5 紀錄資料

# %% [code] cell 74
def record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
            
    record(leverage=context.account.leverage,
           longs=context.output.longs,
           list_longs=context.list_longs,
           weights=context.weights,
           month_weights=context.month_weights,
           list_divest=context.divest,         
           twse_filter=context.output.twse_filter,
           alpha_zscore=context.output.alpha_zscore,        
           PER_zscore=context.output.PER_zscore,
           signal=context.output.signal,
           )

# %% [markdown] cell 75
# ## 5.6 自行客製化圖表

# %% [code] cell 76
def analyze(context, perf):
    
    fig = plt.figure(figsize=(16, 24), dpi=400)
    
    # First chart(累積報酬)
    ax = fig.add_subplot(811) 
    ax.set_title('Strategy Results') 
    ax.plot(perf['algorithm_period_return'], linestyle='-', 
                label='algorithm period return', linewidth=3.0)
    ax.plot(perf['benchmark_period_return'], linestyle='-', 
                label='benchmark period return', linewidth=3.0)
    ax.legend()
    ax.grid(False)
    
    # Second chart(returns)
    ax = fig.add_subplot(812, sharex=ax)       
    ax.plot(perf['returns'], linestyle='-', 
                label='returns', linewidth=3.0)
    ax.legend()
    ax.grid(False)

    # Third chart(ending_cash)->觀察是否超買
    ax = fig.add_subplot(813, sharex=ax)
    ax.plot(perf['ending_cash'], 
            label='ending_cash', linestyle='-', linewidth=3.0)
    ax.axhline(y=1,c='r',linewidth=1)
    ax.legend()
    ax.grid(False)

    # Forth chart(shorts_count)->觀察是否放空
    ax = fig.add_subplot(814, sharex=ax)
    ax.plot(perf['shorts_count'], 
            label='shorts_count', linestyle='-', linewidth=3.0)
    ax.axhline(y=0,c='r',linewidth=1)
    ax.legend()
    ax.grid(False)
    
    # Fifth chart(longs_count)
    ax = fig.add_subplot(815, sharex=ax)
    ax.plot(perf['longs_count'], 
            label='longs_count', linestyle='-', linewidth=3.0)
    ax.axhline(y=1,c='r',linewidth=1)
    ax.legend()
    ax.grid(False)    
    
    # Sixth chart(weights)->觀察每日持股權重
    ax = fig.add_subplot(816, sharex=ax)        
    weights = pd.concat([df.to_frame(d) for d, df in perf['weights'].dropna().items()],axis=1).T
    
    for i in weights.columns:
        df = weights.loc[:,i]
        ax.scatter(df.index,df.values,marker='.', s=5, c='grey', label='daily_weights')
    
    ax.legend(['daily_weights'])
    ax.grid(False)
    
    # Seventh chart(weights)->觀察月持股權重
    ax = fig.add_subplot(817, sharex=ax)        
    month_weights = pd.concat([df.to_frame(d) for d, df in perf['month_weights'].dropna().items()],axis=1).T
    
    for i in month_weights.columns:
        df = month_weights.loc[:,i]
        ax.scatter(df.index, df.values,marker='.', s=5, c='grey', label='month_weights')
        
    ax.legend(['month_weights'])
    ax.grid(False)
    fig.tight_layout()
    
    # Eighth chart(MDD)
    ax = fig.add_subplot(818, sharex=ax) 
    
    window = 252
 
    mdd = ep.stats.roll_max_drawdown(perf['returns'],
                                     window=window)
    mdd_x = mdd.sort_index().round(10).idxmin()
    mdd_y = mdd.min()

    ax.plot(mdd, 
        label='portfolio(MDD = {})'.format(round(ep.max_drawdown(perf['returns']),4)), 
        linestyle='-', 
        color='black',
        linewidth=3.0)
    
   
    benchmark_mdd = ep.stats.roll_max_drawdown(perf['benchmark_return'],
                                               window=window)
    benchmark_mdd_x = benchmark_mdd.sort_index().round(10).idxmin()
    benchmark_mdd_y = benchmark_mdd.min()

    ax.plot(benchmark_mdd, 
        label='benchmark(MDD = {})'.format(round(ep.max_drawdown(perf['benchmark_return']),4)), 
        linestyle='-.', 
        color='gray',
        linewidth=3.0)
      
    ax.set_title(label='{} days max drawdown'.format(window))
    ax.legend()
    ax.grid(False)

# %% [markdown] cell 77
# ## 5.7 Treasury

# %% [code] cell 78
# 以下使用第一銀行(5844)一年期定存利率作為無風險利率。
treasury_returns = get_Treasury_Return(start = algo_start_dt,
                                      end = end,
                                      rate_type = 'Time_Deposit_Rate',                     
                                      term = '1y',
                                      symbol = '5844')
treasury_returns

# %% [markdown] cell 79
# ## 5.8 Backtesting

# %% [code] cell 80
algo_start_dt = pd.Timestamp(tradeday[0], tz='UTC')
end = algo_end_dt

print('\n reg_length =', reg_length,
      '\n allowed_missing_days =', allowed_missing_days,
      '\n freq =',freq,
      '\n start =',algo_start_dt,
      '\n end =',algo_end_dt,
      '\n max_lev =',max_lev,
      '\n commission_cost',commission_cost,
      '\n volume_limit',volume_limit,
      '\n price_impact',price_impact,
      '\n universe',StockList)

# %% [code] cell 81
start_t = time()
results = run_algorithm(start=algo_start_dt,            
                        end=end,                          
                        initialize=initialize,
                        before_trading_start=before_trading_start,
                        analyze=analyze,
                        capital_base=1e7,
                        data_frequency='daily',
                        bundle=bundle_name,
                        treasury_returns=treasury_returns,
                        trading_calendar=get_calendar(calendar_name),
                        custom_loader=custom_loader)


print('Duration: {:.2f}s'.format(time() - start_t))

# %% [code] cell 82
results.T

# %% [markdown] cell 83
# ## 5.9 get record vars

# %% [code] cell 84
record_vars = get_record_vars(results,['longs'])

# %% [code] cell 85
longs = record_vars['longs']
longs[longs['longs']!=False]

# %% [markdown] cell 86
# ## 5.10 positions／transactions／orders

# %% [code] cell 87
positions, transactions, orders = get_transaction_detail(results)

# %% [code] cell 88
orders

# %% [code] cell 89
transactions

# %% [code] cell 90
positions

# %% [markdown] cell 91
# # 6. Portfolio Analysis

# %% [markdown] cell 92
# `Pyfolio`是一個用於分析和評估量化投資策略的套件，其提供了一系列分析工具和可視化方法。
#
# `pyfolio.utils.extract_rets_pos_txn_from_zipline(backtest)`用於從zipline回測結果中取得投資組合報酬、每個時間點的持有部位、每次交易的詳細資訊等等，並且還可以將資料轉換為DataFrame格式，以便於進一步的資料處理和可視化。

# %% [code] cell 93
import pyfolio
returns_pf, positions_pf, transactions_pf = pyfolio.utils.extract_rets_pos_txn_from_zipline(results)

# %% [markdown] cell 94
# 紀錄投資組合每日的報酬率。

# %% [code] cell 95
returns_pf

# %% [markdown] cell 96
# 紀錄每個時間點持有部位的市值。

# %% [code] cell 97
positions_pf

# %% [markdown] cell 98
# 紀錄每次交易的詳細資訊（成交價 price、成交量 amount、成交值 txn_dollars）。

# %% [code] cell 99
transactions_pf

# %% [markdown] cell 100
# 紀錄benchmark每日的報酬率。

# %% [code] cell 101
benchmark_pf = results['benchmark_return']

# %% [code] cell 102
benchmark_pf

# %% [markdown] cell 103
# #### 修改`returns`, `positions`, `transactions`及`benchmark`的DateTimeIndex
#
# The data must have a **tz-aware DateTimeIndex set to UTC**, with a time of **0:00**, otherwise some plots won't be able to be generated.

# %% [code] cell 104
returns_pf.index = returns_pf.index.tz_localize(None).tz_localize('UTC')
positions_pf.index = positions_pf.index.tz_localize(None).tz_localize('UTC')
transactions_pf.index = transactions_pf.index.tz_localize(None).tz_localize('UTC')
benchmark_pf.index = benchmark_pf.index.tz_localize(None).tz_localize('UTC')

# %% [markdown] cell 105
# ## Full tear sheet

# %% [code] cell 106
pyfolio.tears.create_full_tear_sheet(returns = returns_pf,
                                     positions = positions_pf,
                                     benchmark_rets = benchmark_pf,
                                     transactions = transactions_pf)

# %% [markdown] cell 107
# ## Conclusion
#
# - **報酬率**
#   - 從`Cumulative returns`來看，投資組合的累積報酬在2007以後皆優於大盤。
#   - 觀察`Distribution of monthly returns`可以發現平均月報酬率>0，且整體分布呈現左偏。
#   - 從`Top 5 drawdown periods`及`Cumulative returns`來看可以發現5個比較大的大盤回檔期間投資組合報酬率也有回檔的現象，這個因子並沒有特別明顯的抗跌效果，然而最大回檔幅度略低於大盤（大盤MDD：-0.56）。  
#   
#
# - **波動率、調整後報酬及alpha／beta**  
#   - 從`Cumulative returns volatility matched to benchmark`來看，波動率調整後的累積報酬率在2007年後皆優於大盤。說明投資組合有特別明顯的的選股能力或擇時能力。
#   - 從`Rolling volatility`來看，投資組合波動性大多低於大盤。  
#   - 從`Rolling portfolio beta to benchmark_return`來看，portfolio beta多數期間<1，平均約在0.6~0.7間。  
#   - `Max drawdown`略低於大盤（portfolio：-0.52；benchmark：-0.56）。
#   - `Alpha`為0.08，>0。`Sharpe ratio`為0.95，還不錯。
#
# - **部位** 
#   - 從`Exposures`來看，可以發現股票長部位曝險皆在0.6~0.9附近，這是因為回測時我們限制股票部位只能佔投資組合的大約8成。
#   - 從`Long and short holdings`來看，可以發現帳上最多持有69檔且最少持有49檔股票的長部位，多數時候持有50檔股票左右。持股還算分散。
