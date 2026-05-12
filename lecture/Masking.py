# -*- coding: utf-8 -*-
# Auto-generated from Masking.ipynb by tools/ipynb_to_py.py
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
os.environ['TEJAPI_KEY'] = 'Your key'

os.environ['mdate'] = '20220101 20230702'
os.environ['ticker'] = tickers

# !zipline ingest -b tquant

from zipline.pipeline import Pipeline
from zipline.TQresearch.tej_pipeline import run_pipeline
from zipline.pipeline.data import TWEquityPricing
from zipline.pipeline.factors import SimpleMovingAverage, AverageDollarVolume

# %% [markdown] cell 1
# ## Masking
# 有時我們想在計算 pipeline 時忽略特定資產。在兩種常見情況下，忽略資產是很有用的：
#
# 1. 我們想要計算一個計算成本很高的因子，並且我們只關心特定資產的計算結果。一個常見的範例是計算回歸係數（透過 **built-in factors** `RollingLinearRegressionOfReturns`）。
#
#
# 2. 我們想要計算一個在不同資產之間比較的因子，但不希望針對所有資產進行比較。例如，我們可能希望使用 `Factor` 中的 `top` 方法來計算報酬率排名前 200 的資產，並忽略流動性太低的資產。
#
# 為了實現這兩個情形，所有 `Factors` 和許多 `Factor` 方法都可以傳入 mask 參數，該參數必須是一個 `Filter` ，表示計算時要考慮哪些資產。

# %% [markdown] cell 2
# ### Masking Factors
#
# 假設我們希望 pipeline 輸出具有高或低價格變動（`percent_difference`）的證券，但同時只考慮近30日成交金額超過 $ 1,000,000,000 元的證券。
#
# 為此，我們重新建立 `make_pipeline` 函數，並建立 `high_dollar_volume` 過濾器。
#
# 然後，我們可以透過將`high_dollar_volume`作為`mask`參數傳遞給`SimpleMovingAverage`，將此過濾器用作移動平均因子的`mask`。

# %% [code] cell 3
# Dollar volume factor
dollar_volume = AverageDollarVolume(inputs = [TWEquityPricing.close, TWEquityPricing.volume],window_length=30)

# High dollar volume filter
high_dollar_volume = (dollar_volume > 1000000000)

# Average close price factors
mean_close_10 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=10, mask=high_dollar_volume)
mean_close_30 = SimpleMovingAverage(inputs=[TWEquityPricing.close], window_length=30, mask=high_dollar_volume)

# Relative difference factor
percent_difference = (mean_close_10 - mean_close_30) / mean_close_30

# %% [markdown] cell 4
# 我們將 Mask 應用於 `SimpleMovingAverage`，限制平均收盤價因子的計算範圍為：滿足 `high_dollar_volume` filter 的 35 檔證券。而如果沒有 Mask 則會有 230 檔證券。
#
# 當我們結合 `mean_close_10` 和 `mean_close_30` 來計算 `percent_difference` 時，該計算是在相同的 35 個證券上進行的。

# %% [markdown] cell 5
# ### Masking Filters
#
# Masks 還可以使用不同 filters 來回傳結果，例如：`top`、`bottom`與`percentile_between`。
#
# Masks 在我們想要在建立投資組合時特別有用。例如：假設我們想要取得同時是收盤價前百分之十、開盤價前 8 名、成交值前百分之十的證券。
#
# 我們可以透過以下方法達成。

# %% [code] cell 6
# Dollar volume factor
dollar_volume = AverageDollarVolume(inputs = [TWEquityPricing.close, TWEquityPricing.volume],window_length=30)

# High dollar volume filter
high_dollar_volume = dollar_volume.percentile_between(90,100)

# Top open price filter (high dollar volume securities)
top_open_price = TWEquityPricing.open.latest.top(8, mask=high_dollar_volume)

# Top percentile close price filter (high dollar volume, top 8 open price)
high_close_price = TWEquityPricing.close.latest.percentile_between(90, 100, mask=top_open_price)

# %% [markdown] cell 7
# 讓我們將這些變數放入`make_pipeline`，接著輸出一個有著`high_close_price` filter 的空 pipeline 
#

# %% [code] cell 8
def make_pipeline():

    dollar_volume = AverageDollarVolume(inputs = [TWEquityPricing.close, TWEquityPricing.volume],window_length=30)

    high_dollar_volume = dollar_volume.percentile_between(90,100)

    top_open_price = TWEquityPricing.open.latest.top(8, mask=high_dollar_volume)

    high_close_price = TWEquityPricing.close.latest.percentile_between(90, 100, mask=top_open_price)

    return Pipeline(
        screen=high_close_price
    )

# %% [markdown] cell 9
# 執行這個 pipeline 

# %% [code] cell 10
result = run_pipeline(make_pipeline(), '2022-12-30', '2022-12-30')
print('通過過濾器的證券數: %d' % len(result))
result

# %% [markdown] cell 11
# 像上述這樣應用 masks 的方式可以視為一個 "asset funnel"。

# %% [markdown] cell 12
# ### 比較Screen與Mask
# - screen：
#   - 若使用`screen`，會在所有 pipeline factors 或 filters **計算完後**將不符合條件的資料刪除，以`high_close_price`這個 filter 為例，high_close_price=False 的公司將被刪除。
#   - 若是遇到計算量很大的 factors 時這種做法會比較沒有效率。  
#
# - mask：
#   - 若使用`mask`，會在該 factors 或 filters 計算時直接忽略 mask=False 的公司不納入計算。
#   - 這種做法不需要等到輸出結果時才進行篩選，在 factors 或 filters 計算階段就已經進行篩選。
