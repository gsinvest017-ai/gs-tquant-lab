# -*- coding: utf-8 -*-
# Auto-generated from Filters.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import os 

StockList1 = ['1227', '1234', '1304', '1314', '1434', '1440', '1476', '1504', '1507', '1590', '1605', '1704', '1710', '1717', '1723', '1789',
 '1802', '1907', '2006', '2015', '2049', '2101', '2103', '2106', '2204', '2227', '2327', '2337', '2344', '2356', '2360', '2362',
 '2379', '2384', '2385', '2392', '2395', '2448', '2449', '2450', '2451', '2489', '2501', '2504', '2511', '2542', '2545', '2548',
 '2603', '2606', '2607', '2608', '2609', '2610', '2615', '2618', '2707', '2723', '2727', '2809', '2812', '2823', '2834', '2845',
 '2847', '2855', '2884', '2887', '2888', '2889', '2903', '2915', '3034', '3037', '3044', '3149', '3189', '3406', '3702', '4938',
 '4958', '5522', '5871', '6005', '6176', '6239', '6269', '6286', '8008', '8046', '8078', '8422', '9904', '9907', '9914', '9917', '9921',
 '9933', '9940', '9945', '2458', '5264', '2206', '1201', '2347', '3231', '5534', '6116', '9910', '1477', '2353', '6271', '1319',
 '1722', '2059', '3060', '3474', '3673', '2393', '2376', '2439', '3682', '1262', '2201', '2377', '3576', '2352', '2838', '8150',
 '2324', '2231', '8454', '2833', '6285', '6409', '1536', '1702', '2313', '2498', '2867', '6415', '6456', '9938', '2383', '4137', '6452',
 '1707', '1589', '2849', '6414', '8464', '2355', '2345', '3706', '2023', '2371', '1909', '2633', '3532', '9941', '2492', '3019',
 '3443', '4915', '4943', '1229', '2441', '2027', '3026', '1210', '2104', '2456', '5269', '8341', '2354', '3005', '3481', '6669',
 '2409', '3023', '6213', '2404', '3533', '6278', '6592', '3653', '3661', '3665', '2301', '3714', '2883', '2890', '6531', '1904',
 '2014', '2105', '2108', '2474', '2637', '6781', '1102', '4919', '1402', '3035', '3036', '4961', '6719', '6770', '2368', '1795',
 '6550', '6789', '3017', '1101', '1216', '1301', '1303', '1326', '2002', '2207', '2303', '2308', '2311', '2317', '2325', '2330',
 '2357', '2382', '2412', '2454', '2801', '2880', '2881', '2882', '2885', '2886', '2891', '2892', '2912', '3008', '3045', '3697',
 '4904', '5880', '6505', '2408', '3711', '5876']

tickers = " ".join(StockList1)

os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'
os.environ['TEJAPI_KEY'] = 'your_key'

os.environ['mdate'] = '20170101 20230726'
os.environ['ticker'] = tickers

# !zipline ingest -b tquant

from zipline.pipeline import Pipeline
from zipline.TQresearch.tej_pipeline import run_pipeline
from zipline.pipeline.data import TWEquityPricing
from zipline.pipeline.factors import SimpleMovingAverage

# %% [markdown] cell 1
# ## Filters
# Filters 是一個將資產在某個時間點的特徵轉換為**布林值**的函數 ：
#
# ```
# F(asset, timestamp) -> boolean
# ```
# **在 Pipeline 中，Filters 用於縮小股票池的大小**，這裡有兩種 `Filter` 常見的創建方式：使用 `Factor`／ `Classifier` 方法或使用比較運算子（comparison operators，`<`, `<=`, `!=`, `eq`, `>`, `>=`）。
#
# ### Comparison Operators
# 對 `Factors` 和 `Classifier` 使用比較運算子就可以創建 Filters。
#
# 有鑒於我們尚未介紹到 `Classifier`，我們僅使用 `Factors` 舉例，下方的範例建立了一個當最近一期收盤價大於 $20 時會返回 `True` 的 filter 。

# %% [code] cell 2
last_close_price = TWEquityPricing.close.latest
close_price_filter = last_close_price > 20

# %% [markdown] cell 3
# 而以下這個範例建立一個新的 filter，只要近 10 天收盤價平均值低於近 30 天收盤價平均值，該過濾器就會返回 True。

# %% [code] cell 4
mean_close_10 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=10)
mean_close_30 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=30)
mean_crossover_filter = mean_close_10 < mean_close_30

# %% [markdown] cell 5
# 記住，在每天中每檔證券都會擁有自己的 `True` 或 `False` 值。

# %% [markdown] cell 6
# ### Factor／Classifier Methods
# 很多種 `Factor` 和 `Classifier` 都會回傳 `Filters`。
#
# 但同樣地，由於我們尚未討論到 `Classifier`，目前我們僅使用 `Factor`（稍後我們會討論 `Classifier`）。
#
# `Factor.top(n)`會建立一個 `Filter` ，當排名在指定 `Factor` 前 `n` 名的證券，會標記為 `True` ，其餘標記為 `False`。
#
# 下面的範例建立了一個會每天將最近一期收盤價排名前30名的證券標示為`True` 的filter。

# %% [code] cell 7
last_close_price = TWEquityPricing.close.latest
top_close_price_filter = last_close_price.top(30)

# %% [markdown] cell 8
# ## Dollar Volume Filter
# 作為第一個範例，我們創建一個 Filter 。如果該證券過去 30 日平均交易量大於 $1, 000,000, 000 則回傳 `True` 值。
#
# 為了實現這個效果，我們首先需要創建一個 `AverageDollarVolume` factor 以計算過去 30 日平均交易量。讓我們匯入 __built-in factor__ `AverageDollarVolume`。

# %% [code] cell 9
from zipline.pipeline.factors import AverageDollarVolume

# %% [markdown] cell 10
# 接著，讓我們實例化 `AverageDollarVolume` factor。

# %% [code] cell 11
dollar_volume = AverageDollarVolume(window_length=30)

# %% [markdown] cell 12
# 在預設情況下， `AverageDollarVolume` 會使用 `TWEquityPricing.close` 與 `TWEquityPricing.volume` 作為 `inputs`，所以我們不須去定義他們。

# %% [markdown] cell 13
# 現在我們有了平均交易量 factor ，我們可以以布林值表達式創建 filter。下方程式創建了一個當證券的平均成交量 `dollar_volume` 大於 $1, 000,000, 000 時會回傳 `True` 的 filter。

# %% [code] cell 14
high_dollar_volume = (dollar_volume > 1000000000)

# %% [markdown] cell 15
# 為了知道 fitler 的實際結果，我們將它作為一個欄位加入先前課程中創立的 pipeline 中。此外，如同在 [lecture/Factors](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Factors.ipynb) 中所介紹的，我們額外加入了`percent_difference`。

# %% [code] cell 16
def make_pipeline():

    mean_close_10 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=10)
    mean_close_30 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=30)

    percent_difference = (mean_close_10 - mean_close_30) / mean_close_30
    
    dollar_volume = AverageDollarVolume(window_length=30)
    high_dollar_volume = (dollar_volume > 1000000000)

    return Pipeline(
        columns={
            'percent_difference': percent_difference,            
            'high_dollar_volume': high_dollar_volume
        }
    )

# %% [markdown] cell 17
# 如果我們執行 pipeline ，就會產出 `high_dollar_volume` 欄位，當 filter 條件成立時會回傳布林值 `True`。

# %% [code] cell 18
result = run_pipeline(make_pipeline(), '2023-03-02', '2023-06-01')
result.loc['2023-03-03']

# %% [markdown] cell 19
# ## Applying a Screen
# 在預設情況下，pipeline 每日會針對每個在 bundle 中的資產生成一筆資料。
#
# 但很多時候，我們只關注那些**符合特定條件的證券**（例如，為了能快速成交，我們可能只會關注那些每日交易量足夠大的證券）。我們可以透過 `screen` 告訴 pipeline 去忽略那些 filter 回傳的布林值為 `False` 的證券。  
#   
# 為了讓 pipeline 過濾出那些**30日平均交易量**大於 $1, 000,000, 000 的證券，我們可以簡單的將 `high_dollar_volume` filter 作為 `screen` 的參數。
#
# 現在我們的 pipeline 應該會長這樣：

# %% [code] cell 20
def make_pipeline():

    mean_close_10 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=10)
    mean_close_30 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=30)

    percent_difference = (mean_close_10 - mean_close_30) / mean_close_30
    
    dollar_volume = AverageDollarVolume(window_length=30)
    high_dollar_volume = (dollar_volume > 1000000000)

    return Pipeline(
        columns={
            'percent_difference': percent_difference
        },
        screen=high_dollar_volume
    )

# %% [markdown] cell 21
# 當我們執行程式時，pipeline 的輸出僅僅只會包含那些在特定日子滿足 `high_dollar_volume` filter 的證券。

# %% [code] cell 22
result = run_pipeline(make_pipeline(), '2023-03-02', '2023-03-03')
print('通過 filter 的證券數: %d' % len(result))
result.loc['2023-03-03']

# %% [markdown] cell 23
# ## Inverting a Filter
# `~` 運算符是用於反轉 filter 的，將所有 `True` 轉變為 `False`，反之亦然。例如，我們可以撰寫下列的 filter 去過濾出低交易量的證券。

# %% [code] cell 24
low_dollar_volume = ~high_dollar_volume

# %% [markdown] cell 25
# 這會對過去 30 天內所有平均交易量低於或等於 $1,000,000,000 的證券回傳 `True`。

# %% [markdown] cell 26
# 其餘 __built-in filters__ 請參考：[Pipeline built-in filters.ipynb](https://github.com/tejtw/TQuant-Lab/blob/main/lecture/Pipeline%20built-in%20filters.ipynb)
