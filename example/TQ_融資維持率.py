# -*- coding: utf-8 -*-
# Auto-generated from TQ_融資維持率.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ### 載入套件

# %% [code] cell 1
import pandas as pd
import numpy as np
import tejapi
import os
import matplotlib.pyplot as plt
import datetime
plt.rcParams['font.family'] = 'Arial'

# ------------------------------------------
os.environ['TEJAPI_BASE'] = "YOUR BASE"
os.environ['TEJAPI_KEY'] = "YOUR KEY"
# ------------------------------------------

from zipline.sources.TEJ_Api_Data import get_universe
import TejToolAPI
from zipline.data.run_ingest import simple_ingest
from zipline.api import set_slippage, set_commission, set_benchmark,  symbol,  record, order_target_percent
from zipline.finance import commission, slippage
from zipline import run_algorithm

# %% [markdown] cell 2
# ### 取得資料&整理資料

# %% [code] cell 3
columns = ['open_d', 'close_d', 'vol', 'long_t', 'lmr']
start_dt = pd.Timestamp('2018-12-01', tz = 'UTC')
end_dt = pd.Timestamp('2025-04-21', tz = "UTC")

data = TejToolAPI.get_history_data(start = start_dt,
                                   end = end_dt,
                                   ticker = ['3017'],
                                   columns = columns,
                                   
                                   transfer_to_chinese = True)
data

# %% [markdown] cell 4
# ### 將data計算並進行篩選，篩選出融資維持率跌幅前十的股票

# %% [code] cell 5
df = data.copy()

# K線判斷
df['K線'] = df.apply(lambda row: 'Red' if row['收盤價'] > row['開盤價']
                                else ('Green' if row['收盤價'] < row['開盤價'] else '十字'), axis=1)

# 計算過去10天平均成交量（分股票）
df['過去10天平均成交額'] = df.groupby('股票代碼')['成交金額_元'].transform(lambda x: x.rolling(window=10).mean())

# 成交量標準判斷
df['成交額標準'] = df.apply(lambda row: 'T' if row['成交金額_元'] > row['過去10天平均成交額'] else 'F', axis=1)

# 計算過去5天融資餘額平均（分股票）
df['過去5天融資餘額平均'] = df.groupby('股票代碼')['融資餘額'].transform(lambda x: x.rolling(window=5).mean())

# 融資餘額標準判斷
df['融資餘額標準'] = df.apply(lambda row: 'T' if row['融資餘額'] > row['過去5天融資餘額平均'] * 0.95 else 'F', axis=1)

# 計算過去10天融資維持率平均（分股票）
df['過去10天融資維持率平均'] = df.groupby('股票代碼')['融資維持率'].transform(lambda x: x.rolling(window=10).mean())

# 融資維持率標準判斷（當日維持率是否低於過去10天平均）
df['融資維持率標準'] = df.apply(lambda row: 'T' if row['融資維持率'] < row['過去10天融資維持率平均'] else 'F', axis=1)

# 計算融資維持率相對過去10天移動平均的跌幅百分比
df['融資維持率跌幅百分比'] = (df['融資維持率'] - df['過去10天融資維持率平均']) / df['過去10天融資維持率平均'] * 100

# 對每天的資料，挑出跌幅最大的前10檔標記 'long'，其餘標記 'dont'
def label_top10(group):
    # 依跌幅百分比由小到大排序（跌越多越前面）
    group = group.sort_values('融資維持率跌幅百分比')
    group['持倉標記'] = 'dont'
    # 標記前10檔
    group.iloc[:10, group.columns.get_loc('持倉標記')] = 'long'
    return group

df = df.groupby('日期').apply(label_top10)

# %% [markdown] cell 6
# ### 將資料匯入回測系統

# %% [code] cell 7
from zipline.data import bundles

# 讀取 Zipline bundle
bundle_name = 'tquant'
bundle = bundles.load(bundle_name)

# 取得 Zipline 的 SID
sids = bundle.asset_finder.equities_sids
assets = bundle.asset_finder.retrieve_all(sids)

# 建立 股票代碼 → SID 的對應表
symbol_mapping_sid = {i.symbol: i.sid for i in assets}

# 將 股票代碼 轉換為 SID
df = df.reset_index()
df['SID'] = df['股票代碼'].map(symbol_mapping_sid)

# 刪除無法對應的股票
df = df.dropna(subset=['SID']).copy()
df['SID'] = df['SID'].astype(int)

# 重新設索引 (`日期`, `SID`)
df = df.set_index(['日期', 'SID']).sort_index()

# %% [markdown] cell 8
# ### 透過 pipeline 查看下單日期

# %% [code] cell 9
from zipline.pipeline import Pipeline
from zipline.pipeline.data import EquityPricing
from zipline.pipeline.loaders.frame import DataFrameLoader
from zipline.pipeline.domain import TW_EQUITIES
from zipline.pipeline.engine import SimplePipelineEngine
from zipline.pipeline.data import Column, DataSet

transform_data = df.unstack('SID')
fixed_transform_data = transform_data.copy()

if fixed_transform_data.index.tz is not None:
    fixed_transform_data.index = fixed_transform_data.index.tz_convert('UTC')
else:
    fixed_transform_data.index = fixed_transform_data.index.tz_localize('UTC')

# 定義自訂數據集，將字符串類型轉換為布林型 (bool)
class CustomDataset(DataSet):
    KLine = Column(dtype='bool', missing_value=False)  # K線轉換為bool型別
    VolumeStandard = Column(dtype='bool', missing_value=False)  # 成交量標準轉換為bool型別
    FinancingBalanceStandard = Column(dtype='bool', missing_value=False)  # 融資餘額標準轉換為bool型別
    domain = TW_EQUITIES

# 建立 DataFrameLoader
Custom_loader = {
    CustomDataset.KLine: DataFrameLoader(CustomDataset.KLine, fixed_transform_data['K線'] == 'Red'),  # 轉為布林型
    CustomDataset.VolumeStandard: DataFrameLoader(CustomDataset.VolumeStandard, fixed_transform_data['成交量標準'] == 'T'),  # 轉為布林型
    CustomDataset.FinancingBalanceStandard: DataFrameLoader(CustomDataset.FinancingBalanceStandard, fixed_transform_data['融資餘額標準'] == 'T')  # 轉為布林型
}

def choose_loader(column):
    if column.name in EquityPricing._column_names:
        return pricing_loader
    elif column.name in CustomDataset._column_names:
        return Custom_loader[column]
    else:
        raise Exception('Column not available')

# Pipeline 執行引擎
engine = SimplePipelineEngine(get_loader=choose_loader,
                              asset_finder=bundle.asset_finder,
                              default_domain=TW_EQUITIES)

# 計算訊號的函數
def compute_signals():
    # 篩選出符合條件的信號
    k_line_red = CustomDataset.KLine.latest  # K線為Red (已經是布林型)
    volume_standard_t = CustomDataset.VolumeStandard.latest  # 成交量標準為T (已經是布林型)
    financing_balance_standard_t = CustomDataset.FinancingBalanceStandard.latest  # 融資餘額標準為T (已經是布林型)
   
    # 合併所有條件，符合的結果為True
    combined_signals = k_line_red & volume_standard_t & financing_balance_standard_t

    # 只取出符合條件的股票訊號
    return Pipeline(columns={
        'signals': combined_signals  # 這裡存放符合條件的訊號
    })

# 設定日期範圍
start_dt = pd.Timestamp('2018-12-01', tz='UTC')
end_dt = pd.Timestamp('2025-04-21', tz='UTC')

# 執行 Pipeline
pipeline_result = engine.run_pipeline(compute_signals(), start_dt, end_dt)

# %% [markdown] cell 10
# ### 建構initialize函數，包括設定滑價跟手續費以及再平衡週期

# %% [code] cell 11
def initialize(context):
    """環境初始化，設置交易參數。"""
    context.holdings = {}  # 記錄持倉 { asset: { entry_dt, entry_price } }
    context.stop_loss_pct = 0.10  # 停損百分比
    context.take_profit_pct = 0.40  # 停利百分比
    context.rebalance_period = 15  # 持倉期數

    # 設置手續費、滑點、基準、管道
    set_slippage(slippage.TW_Slippage(volume_limit=1.0))
    set_commission(commission.Custom_TW_Commission())
    set_benchmark(symbol('IR0001'))
    attach_pipeline(compute_signals(), 'mystrats')  # 設置信號管道

    # 每日開盤後 5 分鐘執行 handle_data
    schedule_function(
        handle_data,
        date_rules.every_day(),
        #time_rules.market_open(minutes=5),
    )

    # 每日收盤後檢查是否需要平倉
    schedule_function(
        rebalance,
        date_rules.every_day(),
        #time_rules.market_close(minutes=1),
    )
# %% [markdown] cell 12
# ### 接著建立handle_data，依據每日的 signal 資訊進行買進、持有與平倉操作，並納入停利、停損與最大持有天數的限制。

# %% [code] cell 13
def handle_data(context, data):
    """根據當日信號執行下單操作。"""
    out = pipeline_output('mystrats')
    if out.empty:
        return

    signals = out['signals']
    for asset, signal in signals.items():
        if signal:  # 若信號為 True
            cash = context.portfolio.cash
            if cash > 0:
                price = data.history(asset, 'close', 2, '1d').iloc[1]  # 取得昨日開盤價
                order_value = cash * 0.1  # 使用可用現金的 10% 進行下單
                shares = int(order_value // price)
                if shares > 0:
                    order(asset, shares)  # 下單
                    context.holdings[asset] = {
                        'entry_dt': get_datetime(),
                        'entry_price': price,
                    }
                    print(f"Buy {asset} x{shares} @ {price:.2f} on {get_datetime().date()} (10% cash)")


def rebalance(context, data):
    """檢查並平倉，包含停損、停利或達到持倉期。"""
    assets_to_exit = []  # 用來存儲需要平倉的資產

    # 遍歷持倉中的每檔資產
    for asset, info in context.holdings.items():
        price = data.current(asset, 'close')
        entry_price = info['entry_price']
       
        # 停損條件
        if price <= entry_price * (1 - context.stop_loss_pct):
            assets_to_exit.append(asset)
            print(f"Sell {asset} for stop loss @ {price:.2f} on {get_datetime().date()}")
            continue

        # 停利條件
        elif price >= entry_price * (1 + context.take_profit_pct):
            assets_to_exit.append(asset)
            print(f"Sell {asset} for take profit @ {price:.2f} on {get_datetime().date()}")
            continue

        # 超過持倉期則平倉
        elif days_held(context, info['entry_dt']) >= context.rebalance_period:
            assets_to_exit.append(asset)
            print(f"Sell {asset} for rebalance @ {price:.2f} on {get_datetime().date()}")

    # 在遍歷完後平倉所有需要平倉的資產
    for asset in assets_to_exit:
        order_target_percent(asset, 0)
        context.holdings.pop(asset, None)
def days_held(context, entry_dt):
    """計算從 entry_dt 到今天的交易日數（不含 entry 當天）。"""
    cal = get_calendar('TEJ')
    today = get_datetime().normalize()
    sessions = cal.sessions_in_range(entry_dt.normalize(), today)
    return len(sessions) - 1

# %% [markdown] cell 14
# ### 建立analyze函數

# %% [code] cell 15
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

# %% [markdown] cell 16
# ### 建立完以上函數後就能透過zipline中的run_algorithm來執行我們的策略

# %% [code] cell 17
from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar
# Setup for running the algorithm
capital_base = 1e6
start = '2020-08-01'  # Example start date
end = '2025-04-21'  # Example end date

# Convert to pandas Timestamp
start_dt = pd.Timestamp(start, tz='UTC')
end_dt = pd.Timestamp(end, tz="UTC")

# Running the backtest
results = run_algorithm(start=start_dt,
                        end=end_dt,
                        initialize=initialize,
                        handle_data=handle_data,
                        capital_base=capital_base,
                        data_frequency='daily',
                        analyze=analyze,
                        bundle=bundle_name,  # Replace with your bundle name
                        trading_calendar=get_calendar('TEJ'),
                        custom_loader=Custom_loader
                        )

# %% [markdown] cell 18
# ### 最後我們透過pyfolio，可以將我們的績效數據更清楚展現

# %% [code] cell 19
from pyfolio.utils import extract_rets_pos_txn_from_zipline
import pyfolio as pf

# 從 results 資料表中取出 returns, positions & transactions
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return  # 取出 benchmark 的報酬率
# 繪製 Pyfolio 中提供的所有圖表
pf.tears.create_full_tear_sheet(returns=returns,
                                positions=positions,
                                transactions=transactions,
                                benchmark_rets=benchmark_rets
                                )