# -*- coding: utf-8 -*-
# Auto-generated from DataFrameLoader.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # Pipeline DataFrameLoader - Pipeline API with Custom Data
# ---
# `DataFrameLoader` 允許將客製化的數據透過 DataFrame 導入至 pipeline 中，本範例將演示 `DataFrameLoader` 的用法。

# %% [markdown] cell 1
# ## Imports & Settings

# %% [code] cell 2
import os
import pandas as pd

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'YOUR KEY'


from zipline.pipeline import Pipeline
from zipline.pipeline.loaders import EquityPricingLoader
from zipline.pipeline.loaders.frame import DataFrameLoader
from zipline.pipeline.data import Column, DataSet, TQAltDataSet, EquityPricing
from zipline.pipeline.engine import SimplePipelineEngine
from zipline.pipeline.domain import TW_EQUITIES

from zipline.data.data_portal import bundles
from zipline.data.run_ingest import simple_ingest

from zipline.sources.TEJ_Api_Data import get_universe

from TejToolAPI.TejToolAPI import get_history_data

# %% [markdown] cell 3
# <span id="load_data"></span>
#
# ## 獲取外部資料，並進行整理

# %% [markdown] cell 4
# #### 載入先前已導入的 tquant bundle
# - 若尚未執行 tquant bundle ingest 的流程，請先執行以下 simple_ingest 程式。
# - `bundles.load` 函式負責從先前已經 ingest 的 bundle 中載入數據，使使用者能夠在 Zipline 環境中利用 `AssetFinder` 存取證券 `SID`（Security Identifier）。

# %% [code] cell 5
start = '2020-01-03'
end = '2025-02-07'

start_dt = pd.Timestamp(start, tz='utc')
end_dt = pd.Timestamp(end, tz='utc')

pool = get_universe(start, end, idx_id=['IX0002'])

#simple_ingest(name = 'tquant', tickers = pool, start_date = start , end_date = end)

# %% [code] cell 6
bundle_name = 'tquant'
bundle = bundles.load(bundle_name)

# %% [markdown] cell 7
# #### 取得證券標的（Symbols）
# 在 Zipline 中，`AssetFinder` 是一個專門負責管理資產（`Asset`）資訊的工具，提供查找和檢索證券標的的功能。以下四行程式碼分別執行：
# 1. 取得 bundle 中所有股票的 `SID`。
# 2. 透過 SID 取得對應的 `Asset` 物件。
# 3. 透過 `Asset` 物件取得交易代碼（`symbol`）。
# 4. 建立 `symbol` mapping `SID` 的對照。

# %% [code] cell 8
sids = bundle.asset_finder.equities_sids
assets = bundle.asset_finder.retrieve_all(sids)
symbols = [i.symbol for i in assets]
symbol_map = dict(zip(symbols, sids))

# %% [markdown] cell 9
# #### 利用 TEJ TOOL API 獲取資料
# 這邊取得外資買賣超張數（`Qfii_Diff_Vol`）資料作為示範。

# %% [code] cell 10
custom_data = get_history_data(
    ticker=symbols,
    columns=['Qfii_Diff_Vol'],
    start=start,
    end=end,
    transfer_to_chinese=False
)

# %% [code] cell 11
custom_data.head()

# %% [markdown] cell 12
# 整理外部資料以符合 `DataFrameLoader` 要求的格式
# - 將外部資料作轉置，一個欄位整理為一個 DataFrame。
# - 接著將外部資料的 coid 替換成 `SID`。
# - 最後將外部資料的 mdate 設定為 UTC 時區。
#
# 註：此處資料採用**不平移**的方式進行處理

# %% [code] cell 13
transform_data = (
    custom_data
    .set_index(['coid', 'mdate'])['Qfii_Diff_Vol']
    .unstack('coid')
    .rename(columns=symbol_map, errors='raise') # errors = 'raise' 會在遇到錯誤時拋出異常，避免 bundle 與 custom_data 資產不一致
    .tz_localize('UTC')
)

# %% [code] cell 14
transform_data.head()

# %% [markdown] cell 15
# ## 定義自訂數據集（Custom Dataset）
# 在 Zipline 中，我們可以透過自訂數據集（Custom Dataset），將額外的欄位與 tquant bundle 數據合併，以擴充回測數據的應用範圍。
#
# 在 Zipline Pipeline 中，`DataSet` 由兩個主要部分組成：
# - 一組 Column 物件：描述數據集內可查詢的數據欄位。
# - 一個 Domain 物件：描述該數據集適用的資產（assets）和交易日曆（calendar）。
#
# ### 定義 `DataSet` 的步驟
# 1. 定義 `Column`（欄位）
#     - `Column` 代表 `DataSet` 內的數據欄位，每個 `Column` 需要指定一個 **numpy 資料型別（`np.dtype`）**，用來描述數據格式。常用的 type 如下：
#         - 使用 `float` 表示數值型（Numeric）數據。由於 NumPy 不原生支援帶有缺失值的 `int` 型別，建議對所有數值型數據使用 `float`，即使該數據概念上是整數。這樣可以利用 `NaN`（Not a Number）作為自然的缺失值，並獲得更好的數據處理能力。
#         - 使用 `object` 儲存字串類型（String）數據。
#         - 使用 `int` 表示類別型（Categorical）數據。整數型別（`int`）需要顯式指定 missing_value，例如 -1，用來標記當某個證券在特定日期沒有值時的預設值。
#         - 使用 `bool` 表示布林型（Boolean）數據。
#
#         ```python
#         # 一個簡易的範例
#         class CustomDataset(DataSet):
#             # float
#             shares_outstanding = Column(float)
#
#             # object
#             industry = Column(object)
#
#             # int
#             mch_prd = Column(int, missing_value=-1)
#
#             # bool
#             is_suspend = Column(bool)
#         ```
#
# 2. 定義 `Domain`（適用範圍）
#     - **特定 `Domain`（如 `TW_EQUITIES`）**：當數據來自特定市場時，可透過 `domain` 屬性指定適用範圍。

# %% [markdown] cell 16
# 以下範例定義了一個 `CustomDataset` 類別，它繼承自 `zipline.pipeline.DataSet`，並包含一個型別為 float 的 `zipline.pipeline.Column`，適用於 `TW_EQUITIES` domain。（註：可同時納入多個不同`Column`）

# %% [code] cell 17
class CustomDataset(DataSet):
    Qfii_Diff_Vol = Column(dtype=float)
    domain = TW_EQUITIES

# %% [markdown] cell 18
# ## 定義 Pipeline Loaders

# %% [markdown] cell 19
# 在 Zipline Pipeline 中，`PipelineLoader` 負責載入 Pipeline 所需的數據。我們可以使用 `DataFrameLoader` 來從 pandas.DataFrame 讀取數據，並讓 Pipeline 取得這些數據進行計算。
#
# 以下代碼建立一個字典 `Custom_loader`：
# - 字典的key是 `Column` 物件，該物件包含該欄位的 metadata。
# - 字典的 value 是 `DataFrameLoader` 物件，需傳入兩個參數：`column`（`Column`物件）及 `baseline`（資料）。

# %% [code] cell 20
Custom_loader= {CustomDataset.Qfii_Diff_Vol: DataFrameLoader(column=CustomDataset.Qfii_Diff_Vol, baseline=transform_data)}
Custom_loader

# %% [code] cell 21
CustomDataset.columns

# %% [markdown] cell 22
# ## 建立 Pipeline engine，並執行計算
# - 在 Zipline Pipeline 中，我們需要建立 Pipeline engine 來執行客製化數據的查詢，並將客製化欄位加入 Pipeline 以供策略開發使用。
# - 在建構 Pipeline engine 時，我們須先定義 `choose_loader` 函式：
#     - 在 Zipline Pipeline 框架中，當 Pipeline 需要數據時，它會根據 loadable term（可載入的數據項目，如 `Column`）來查找對應的 `PipelineLoader`。我們可以撰寫一個函式，根據輸入的 term 回傳適當的 `PipelineLoader` 來載入對應的數據。
#     - `choose_loader` 函式將會確認該欄位是否在 `CustomDataset.columns` 中，若 column 存在，則回傳我們前面建立的 `Custom_loader` 至 Pipeline engine。

# %% [code] cell 23
# Loader for pricing
pricing_loader = EquityPricingLoader.without_fx(bundle.equity_daily_bar_reader, bundle.adjustment_reader)

# Define the function for the get_loader parameter
def choose_loader(column):
    if column in CustomDataset.columns:
        return Custom_loader[column]
    elif column.unspecialize() in EquityPricing.columns:
         return pricing_loader
    else:
        raise Exception('Column not available')

# Create a Pipeline engine
engine = SimplePipelineEngine(
    get_loader = choose_loader,
    asset_finder = bundle.asset_finder,
    default_domain = TW_EQUITIES
)

# %% [markdown] cell 24
# 現在，我們將在 make_pipeline() 函式中實例化（instantiate）我們的數據，並將其加入 Pipeline

# %% [code] cell 25
def make_pipeline():
    qfii_custom = CustomDataset.Qfii_Diff_Vol.latest
    close = EquityPricing.close.latest
    longs = qfii_custom.top(10)

    return Pipeline(
        columns={
            'qfii_custom': qfii_custom,
            'close': close,
            'longs': longs
        }
    )

# %% [markdown] cell 26
# 最後，執行 Pipeline 數據計算（從 start_date 到 end_date）
#
# **註：若要使用 CustomDataset 來執行計算，必須使用 `SimplePipelineEngine.run_pipeline`，而不能使用 `zipline.TQresearch.tej_pipeline.run_pipeline`**

# %% [code] cell 27
result = engine.run_pipeline(make_pipeline(), start_dt, end_dt)
result.head()

# %% [markdown] cell 28
# ## 利用 custom loader 進行回測
# 將先前建立的 Custom_loader 傳入 `run_algorithm` 函式的 `custom_loader` 參數中。

# %% [code] cell 29
from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar
from zipline.api import (
    attach_pipeline,
    order,
    pipeline_output,
    schedule_function,
    date_rules,
    set_slippage,
    set_commission,
    order_target,
    order_target_percent
)
from zipline.finance.commission import Custom_TW_Commission
from zipline.finance.slippage import VolumeShareSlippage
from zipline.sources.TEJ_Api_Data import get_Benchmark_Return


capital_base = 1e6
calendar_name = 'TEJ'

# Get benchmark returns
Bindex = get_Benchmark_Return(start=start_dt, end=end_dt, symbol='IR0001').sort_index(ascending=True).tz_convert('utc')

def initialize(context):
    set_commission(Custom_TW_Commission())
    set_slippage(VolumeShareSlippage())
    attach_pipeline(make_pipeline(), 'my_pipeline')
    schedule_function(rebalance, date_rules.month_end())

def before_trading_start(context, data):
    context.pipeline_data = pipeline_output('my_pipeline')

def rebalance(context, data):

    pipeline_data = context.pipeline_data
    longs = pipeline_data[pipeline_data['longs']==True].index.tolist()

    if len(longs) > 0:
        ratio = 1 / len(longs)
        for asset in longs:
            order_target_percent(asset, ratio)

        positions = context.portfolio.positions.keys()
        for asset in set(positions) - set(longs):
            order_target(asset, 0)


# Running a Backtest
results = run_algorithm(
    start=start_dt,
    end=end_dt,
    initialize=initialize,
    before_trading_start=before_trading_start,
    capital_base=capital_base,
    data_frequency='daily',
    benchmark_returns =Bindex,
    bundle=bundle_name,
    trading_calendar=get_calendar(calendar_name),
    custom_loader=Custom_loader
)

# %% [code] cell 30
results.T

# %% [markdown] cell 31
# ## 補充說明
# - DataSet
#     - 因 Zipline 為了預防使用者用到未來資料，所以內建 `DataSet`（`zipline.pipeline.data.TQAltDataSet／TQDataSet／EquityPricing／TWEquityPricing`）均會將原始資料平移一個交易日。若要自行決定平移天數，則可以透過客製化 `DataSet` 來實現，本範例即是採用不平移的方式進行處理。
# - run_pipeline
#     - 若要使用 CustomDataset 來執行 run_pipeline 計算，必須使用 `SimplePipelineEngine.run_pipeline`，而不能使用 `zipline.TQresearch.tej_pipeline.run_pipeline`
