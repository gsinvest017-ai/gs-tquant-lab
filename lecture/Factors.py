# -*- coding: utf-8 -*-
# Auto-generated from Factors.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ## Factors
# Factor （因子）是一個將資產在某個時間點的特徵轉換為數字的函數
# ```
# F(asset, timestamp) -> float
# ```
# 在 Pipeline 中，Factors 是最常被使用的項目。Factors 的輸出值會是數值，輸入值會是一個以上的資料欄位與時間窗口長度。
#
# 在 Pipeline 中最簡單的 Factors 為 __built-in factors__。__Built-in factors__ 是為了執行常用計算預先建立的。作為第一個例子，讓我們創建一個 factor 來計算過去十天的平均收盤價。
#
# 我們可以使用 __Built-in factor__ 中的`SimpleMovingAverage`（指定窗口長度為10天）來計算平均價格。為了實現這個功能，我們需要匯入 __Built-in factor__ `SimpleMovingAverage` 以及 `TWEquityPricing` 資料集。

# %% [code] cell 1
import os
import pandas as pd

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'YOUR KEY'

os.environ['ticker'] = '2330 2337'
os.environ['mdate'] = '20070101 20230701'

# !zipline ingest -b tquant

from zipline.pipeline import Pipeline
from zipline.TQresearch.tej_pipeline import run_pipeline
from zipline.pipeline.data import TWEquityPricing
from zipline.pipeline.factors import SimpleMovingAverage

# %% [markdown] cell 2
# ### Creating a Factor
# 讓我們回到上一堂課（[lecture/Creating a Pipeline](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Creating%20a%20Pipeline.ipynb)）的 `make_pipeline` function。  
#
#
# 首先我們實例化一個 `SimpleMovingAverage` factor。為了創建一個 `SimpleMovingAverage` factor，我們可以對 `SimpleMovingAverage` 建構子輸入兩個參數：__inputs__（必須是內含一個 `BoundColumn` 物件的 `list` ），以及 __window_length__（為整數，代表要用過去多少天的資料計算平均價格）。  
#
#
#
# 我們會在之後更深度地討論 `BoundColumn`，目前我們只需要知道 `BoundColumn` 代表要將何種資料傳入 `Factor` 物件就好。  
#
#   
# 下方程式碼將創建一個計算過去10天平均收盤價的 `Factor`。

# %% [code] cell 3
mean_close_10 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=10)

# %% [markdown] cell 4
# 請注意，很重要的一點是，建立 factor 並不完全地等於執行計算。創建一個 factor 就像是定義一個 function。要執行一個計算，我們需要將 factor 加入 pipeline 並執行它。

# %% [markdown] cell 5
# ### Adding a Factor to a Pipeline
# 讓我們更新原本空的 pipeline ，並讓它計算我們新的移動平均因子。
#
# 首先，先在 `make_pipeline` 中實體化剛剛建立因子，讓 pipeline 知道要如何計算它。接著，我們可以藉由設定 `Pipeline` 的 `columns` 參數（`columns`為一個將欄位名稱映射到 factors、 filters 或 classifiers 的字典），讓 pipeline 知道要輸出哪些資料。。  
#
# 更新後的 `make_pipeline` 函數看起來應該像這樣：

# %% [code] cell 6
def make_pipeline():
    
    mean_close_10 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=10)
    
    return Pipeline(
        columns={
            '10_day_mean_close': mean_close_10
        }
    )

# %% [markdown] cell 7
# 再來，建立pipeline、執行，接著展示結果。
#
# 現在，在我們的 pipeline 中有一個平均收盤價的欄位（`10_day_mean_close`），並且總共有兩檔證券。請注意每一列對應著特定證券在特定日期的計算結果。
#
# pipeline 的產出結果為帶有 MultiIndex 的 DataFrame，它的第一層 __index__ 為執行計算時的日期，而第二層 __index__ 為對應證券的 `Equity` 物件。舉例來說，第一列（`2023-05-05 00:00:00+00:00`, `Equity(0 [2330])`）會是在 2023/5/5 時，證券代碼為 2330 的平均收盤價計算結果。

# %% [code] cell 8
result = run_pipeline(make_pipeline(), '2023-05-05', '2023-05-05')
result

# %% [markdown] cell 9
# 如果 pipeline 計算天數多於一天（2018-01-03~2022-12-30），輸出會看起來像這樣：

# %% [code] cell 10
result = run_pipeline(make_pipeline(), '2018-01-03', '2022-12-30')
result

# %% [markdown] cell 11
# 注意：透過 `Pipeline.add` 方法，也可以把因子加入至已經存在的 `Pipeline` 實體中。使用 `add` 看起來會像這樣：
#
# ```
# my_pipe = Pipeline()
# f1 = SomeFactor(...)
# my_pipe.add(f1, 'f1')
# ```

# %% [markdown] cell 12
# ### Latest
# `Latest` 是最常使用的 `Factors`。`Latest` 可以取得指定欄位中最近一期的資料。這個因子因為太常被使用以至於它實例化的方式與比較特別。
#
# 若要取得特定欄位最近一期的資料，最好方法是呼叫它的 `.latest` 屬性。作為示範，我們更新 `Pipeline` 以創建一個代表最近一期 __收盤價__ 的因子 ，然後把它加入 pipeline：

# %% [code] cell 13
def make_pipeline():

    mean_close_10 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=10)
    latest_close = TWEquityPricing.close.latest

    return Pipeline(
        columns={
            '10_day_mean_close': mean_close_10,
            'latest_close_price': latest_close
        }
    )

# %% [markdown] cell 14
# 現在，當我們再次執行 pipeline 時，產出的 DataFrame 會包含兩個欄位。一個欄位（`10_day_mean_close`）記錄每隻證券的10日平均收盤價，另一個（`latest_close_price`）記錄最近收盤價。

# %% [code] cell 15
result = run_pipeline(make_pipeline(), '2023-05-05', '2023-05-05')
result.head(5)

# %% [markdown] cell 16
# `.latest` 有時可以回傳 `Factors` 以外的東西。我們會在之後的課程示範其他可能回傳的資料類型。

# %% [markdown] cell 17
# ## Default Inputs
# 有些 Factors 有著不可被更改的預設輸入值。例如 `VWAP` __built-in factor__ 永遠都是從`TWEquityPricing.close` 和 `TWEquityPricing.volume` 計算而來的。當一個 Factors 永遠由同樣一個 `BoundColumns` 計算而來時，我們會說這個建構子沒有指定的 `inputs`。

# %% [code] cell 18
from zipline.pipeline.factors import VWAP
vwap = VWAP(window_length=10)

# %% [markdown] cell 19
# 其餘 __built-in factor__ 請參考：[Pipeline built-in factors.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Pipeline%20built-in%20factors.ipynb)
