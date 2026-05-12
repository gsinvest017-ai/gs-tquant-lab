# -*- coding: utf-8 -*-
# Auto-generated from TQ_安東尼·賣利亞反向操作策略.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import pandas as pd
import numpy as np
import tejapi
import os
import matplotlib.pyplot as plt
import datetime
plt.rcParams['font.family'] = 'Arial'

os.environ['TEJAPI_BASE'] = "your base"
os.environ['TEJAPI_KEY'] = "your key"


from zipline.sources.TEJ_Api_Data import get_universe
import TejToolAPI
from zipline.data.run_ingest import simple_ingest
from zipline.api import set_slippage, set_commission, set_benchmark,  symbol,  record, order_target_percent
from zipline.finance import commission, slippage
from zipline import run_algorithm

# %% [code] cell 1
from logbook import Logger, StderrHandler, INFO
log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('get_universe')

# %% [code] cell 2
pool = get_universe(start = '2020-01-01',
                    end = '2025-05-21',
                    mkt_bd_e = ['TSE', 'OTC', 'TIB'],  # 已上市之股票
                    stktp_e = 'Common Stock',  # 普通股
                    ) # general industry 可篩掉金融產業
# %% [code] cell 3
columns = ['close_d', 'adjfac', 'fld005', 'qfii_pct' , 'fd_pct' , 'ri'  , 'shares','per' , 'cscfo' , 'cscfi' , 'r307' , 'r19'  , 'open_d' ]
start_dt = pd.Timestamp('2020-01-01', tz = 'UTC')
end_dt = pd.Timestamp('2025-05-21', tz = "UTC")

data = TejToolAPI.get_history_data(start = start_dt,
                                   end = end_dt,
                                   ticker = pool,
                                   columns = columns,
                                   transfer_to_chinese = True)
data

# %% [code] cell 4
df = data

# %% [code] cell 5
df.columns

# %% [code] cell 6
df['調整後股價'] = df['收盤價'] * df['調整係數']
df['日期'] = pd.to_datetime(df['日期'])
df = df.sort_values(['股票代碼', '日期'])

# 計算近 52 週（252 個交易日）的最高價
df['近52週最高價'] = (
    df.groupby('股票代碼')['調整後股價']
    .transform(lambda x: x.rolling(window=252, min_periods=1).max())
)
df['股價標準'] = df['開盤價'] < (df['近52週最高價'] * 0.5)

# %% [code] cell 7
df['近6月投信最低持股率'] = (
    df.groupby('股票代碼')['投信持股率']
    .transform(lambda x: x.rolling(window=126, min_periods=1).min())
)

df['近6月外資最低持股率'] = (
    df.groupby('股票代碼')['外資持股率']
    .transform(lambda x: x.rolling(window=126, min_periods=1).min())
)

df['近6月董監最低持股率'] = (
    df.groupby('股票代碼')['董監持股％']
    .transform(lambda x: x.rolling(window=126, min_periods=1).min())
)
# Step 1: 計算六個月內最低持股比例
df['近6月董監最低持股率'] = (
    df.groupby('股票代碼')['董監持股％']
    .transform(lambda x: x.rolling(window=126, min_periods=1).min())
)
df['近6月外資最低持股率'] = (
    df.groupby('股票代碼')['外資持股率']
    .transform(lambda x: x.rolling(window=126, min_periods=1).min())
)
df['近6月投信最低持股率'] = (
    df.groupby('股票代碼')['投信持股率']
    .transform(lambda x: x.rolling(window=126, min_periods=1).min())
)

# Step 2: 各項比例變動（最新 - 最低 or 倍數）
df['董監增減比'] = df['董監持股％'] - df['近6月董監最低持股率']
df['外資倍數'] = df['外資持股率'] / df['近6月外資最低持股率']
df['投信倍數'] = df['投信持股率'] / df['近6月投信最低持股率']

# Step 3: 標準判斷欄位（T/F）
df['董監標準'] = df['董監增減比'] > 1
df['外資標準'] = df['外資倍數'] > 2
df['投信標準'] = df['投信倍數'] > 2

# %% [code] cell 8
df['每股自由現金流量'] = (df['投資產生現金流量_TTM'] + df['營運產生現金流量_TTM']) / df['流通在外股數_千股']
# 本益比條件：小於 12
df['本益比條件'] = df['本益比'] < 12

# P/FCF 條件：價格 / 每股自由現金流量 < 10
df['PFCF條件'] = (df['開盤價'] / df['每股自由現金流量']) < 10

# PBR 條件：價格 / 每股淨值 < 1
df['PBR條件'] = (df['開盤價'] / df['每股淨值_Q']) < 1

# PSR 條件：價格 / 每股營收 < 1
df['PSR條件'] = (df['開盤價'] / df['近12月每股營收_元']) < 1
# %% [code] cell 9
df['基本面符合數'] = (
    (df['本益比條件'] == True).astype(int) +
    (df['PFCF條件'] == True).astype(int) +
    (df['PBR條件'] == True).astype(int) +
    (df['PSR條件'] == True).astype(int)
)

# %% [code] cell 10
df

# %% [code] cell 11
# 設定索引為 (`日期`, `股票代碼`)
df_filtered = df.set_index(['日期', '股票代碼']).sort_index()
df_filtered
# %% [code] cell 12
tickers = ' '.join(pool+['IR0001'])
start = '2020-01-01'
end = '2025-05-21'

os.environ['mdate'] = start+' '+end
os.environ['ticker'] = tickers
# !zipline ingest -b tquant

# %% [code] cell 13
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
df_filtered = df_filtered.reset_index()
df_filtered['SID'] = df_filtered['股票代碼'].map(symbol_mapping_sid)

# 刪除無法對應的股票
df_filtered5 = df_filtered.dropna(subset=['SID']).copy()
df_filtered['SID'] = df_filtered['SID'].astype(int)

# 重新設索引 (`日期`, `SID`)
data_run = df_filtered.set_index(['日期', 'SID']).sort_index()

data_run

# %% [code] cell 14
# 你原本有 '基本面符合數' 是整數
data_run = data_run.copy()

# 新增一欄表示基本面是否符合條件 (bool)
data_run['基本面符合條件'] = data_run['基本面符合數'] >= 4
# %% [code] cell 15
data_run['基本面符合條件']

# %% [code] cell 16
from zipline.pipeline import Pipeline
from zipline.pipeline.data import Column, DataSet
from zipline.pipeline.loaders.frame import DataFrameLoader
from zipline.pipeline.domain import TW_EQUITIES
from zipline.pipeline.engine import SimplePipelineEngine
import pandas as pd
from zipline.pipeline.data import EquityPricing

# 1. 假設你已有 data_run，是 MultiIndex DataFrame (日期, SID)，
# 包含以下欄位 (字串 'T' 表示符合條件，整數表示數值)
# '股價標準', '董監標準', '外資標準', '投信標準', '基本面符合數'

# 2. 轉成寬格式，index為日期，欄位為股票代碼(SID)

def prepare_bool_df(df, col):
    return (df[col] == 'T').unstack()

price_df = prepare_bool_df(data_run, '股價標準')
insider_df = prepare_bool_df(data_run, '董監標準')
foreign_df = prepare_bool_df(data_run, '外資標準')
trust_df = prepare_bool_df(data_run, '投信標準')
basic_num_df = data_run['基本面符合數'].unstack()
basic_bool_df = data_run['基本面符合條件'].unstack()
# 3. 確保時間索引是帶有 UTC 時區（Zipline Pipeline要求）
def localize_utc(df):
    if df.index.tz is None:
        return df.tz_localize('UTC')
    else:
        return df.tz_convert('UTC')

price_df = localize_utc(price_df)
insider_df = localize_utc(insider_df)
foreign_df = localize_utc(foreign_df)
trust_df = localize_utc(trust_df)
basic_num_df = localize_utc(basic_num_df)
basic_bool_df = localize_utc(basic_bool_df)

# 4. 自訂 Dataset
class CustomFactors(DataSet):
    Price_cond = Column(dtype='bool', missing_value=False)
    Insider_cond = Column(dtype='bool', missing_value=False)
    Foreign_cond = Column(dtype='bool', missing_value=False)
    Trust_cond = Column(dtype='bool', missing_value=False)
    #BasicNum_cond = Column(dtype='int64', missing_value=0)
    BasicNum_cond = Column(dtype='bool', missing_value=False)
    domain = TW_EQUITIES

# 5. 建立 Loader
loader_dict = {
    CustomFactors.Price_cond: DataFrameLoader(CustomFactors.Price_cond, price_df),
    CustomFactors.Insider_cond: DataFrameLoader(CustomFactors.Insider_cond, insider_df),
    CustomFactors.Foreign_cond: DataFrameLoader(CustomFactors.Foreign_cond, foreign_df),
    CustomFactors.Trust_cond: DataFrameLoader(CustomFactors.Trust_cond, trust_df),
    #CustomFactors.BasicNum_cond: DataFrameLoader(CustomFactors.BasicNum_cond, basic_num_df),
    CustomFactors.BasicNum_cond: DataFrameLoader(CustomFactors.BasicNum_cond, basic_bool_df)
}

# 6. 你要自行定義 pricing_loader (這裡示意 None)
pricing_loader = None

def choose_loader(column):
    if column.name in EquityPricing._column_names:
        return pricing_loader
    elif column.name in CustomFactors._column_names:
        return loader_dict[column]
    else:
        raise Exception(f"Column {column.name} not available")

# 7. 建立 Pipeline Engine
engine = SimplePipelineEngine(
    get_loader=choose_loader,
    asset_finder=bundle.asset_finder,
    default_domain=TW_EQUITIES
)

# 8. 定義條件邏輯
def compute_signals():
    price = CustomFactors.Price_cond.latest
    insider = CustomFactors.Insider_cond.latest
    foreign = CustomFactors.Foreign_cond.latest
    trust = CustomFactors.Trust_cond.latest
    #basic_num = CustomFactors.BasicNum_cond.latest

    chip_condition = insider | foreign | trust
    basic_condition = CustomFactors.BasicNum_cond.latest

    # 最終條件：股價標準 AND (三籌碼任一成立) OR (前面不成立且基本面符合數>=2)

    final_signal = (price & chip_condition) |   (basic_condition)

    return Pipeline(columns={'signals': final_signal})

# 9. 設定時間區間
start_dt = pd.Timestamp('2020-01-01', tz='UTC')
end_dt = pd.Timestamp('2025-05-21', tz='UTC')

# 10. 執行 Pipeline
pipeline_result = engine.run_pipeline(compute_signals(), start_dt, end_dt)

# 11. 印出結果
pipeline_result





# %% [code] cell 17
len(pipeline_result[pipeline_result['signals'] == True])  # 符合條件的股票數量
# %% [code] cell 18
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

# %% [code] cell 19
from zipline.api import (
    order_target_percent,order,
    pipeline_output,
    get_datetime,
    schedule_function,
    date_rules,
    time_rules,
    symbol,
)
from zipline.utils.calendar_utils import get_calendar
from zipline.api import set_slippage, set_commission, set_benchmark, attach_pipeline, slippage, commission
import pandas as pd

# ────────────── 主要函數 ──────────────

def initialize(context):
    """初始化環境設置，包含交易參數與排程。"""
    context.holdings = {}  # 用來存儲每檔股票的持倉資訊
    context.rebalance_period = 63    # 重新平衡天數
    context.stop_loss_pct = 0.1     # 停損百分比
    context.take_profit_pct = 0.2  # 停利百分比

    # 風控、手續費、Benchmark、Pipeline設定
    set_slippage(slippage.TW_Slippage(volume_limit=1.0))
    set_commission(commission.Custom_TW_Commission())
    set_benchmark(symbol('IR0001'))

    # 把 compute_signals pipeline attach 進來
    attach_pipeline(compute_signals(), 'mystrats')

    # 每日開盤後 5 分鐘執行 handle_data
    schedule_function(handle_data, date_rules.every_day(), time_rules.market_open(minutes=5))

def handle_data(context, data):
    """根據當日信號執行下單操作，使用可用現金進行買入。"""
    out = pipeline_output('mystrats')
    if out.empty:
        return

    signals = out['signals']
    for asset, signal in signals.items():
        if signal and asset not in context.holdings:  # 若信號為 True 且未持有資產
            cash = context.portfolio.cash  # 獲取可用現金
            if cash > 0:
                price = data.history(asset, 'open', 2, '1d').iloc[1]  # 取得昨日開盤價
                if pd.isna(price) or price <= 0:  # 檢查價格是否有效
                    continue  # 若價格無效，跳過該資產
                order_value = cash * 0.1  # 使用可用現金的 10% 進行下單
                shares = int(order_value // price)  # 計算可買的股數
                if shares > 0:
                    order(asset, shares)  # 下單
                    context.holdings[asset] = {
                        'entry_dt': get_datetime(),
                        'entry_price': price,
                    }
                    print(f"Buy {asset} x{shares} @ {price:.2f} on {get_datetime().date()} (10% cash)")

        elif signal and asset in context.holdings:
            # 續抱：重置 entry_dt（表示續抱）
            context.holdings[asset]['entry_dt'] = get_datetime()

        elif asset in context.holdings:
            # 再平衡：檢查是否需要平倉
            rebalance(context, data, asset)

def rebalance(context, data, asset):
    """檢查並平倉，包含停損、停利或達到持倉期。"""
    info = context.holdings[asset]
    price = data.current(asset, 'close')
    entry_price = info['entry_price']

    # 停損條件
    if price <= entry_price * (1 - context.stop_loss_pct):
        order_target_percent(asset, 0)  # 停損，賣出資產
        context.holdings.pop(asset, None)  # 移除持倉
        print(f"Sell {asset} for stop loss @ {price:.2f} on {get_datetime().date()}")
    # 停利條件
    elif price >= entry_price * (1 + context.take_profit_pct):
        order_target_percent(asset, 0)  # 停利，賣出資產
        context.holdings.pop(asset, None)  # 移除持倉
        print(f"Sell {asset} for take profit @ {price:.2f} on {get_datetime().date()}")
    # 超過持倉期則平倉
    elif days_held(context, info['entry_dt']) >= context.rebalance_period:
        order_target_percent(asset, 0)  # 超過持倉期，平倉
        context.holdings.pop(asset, None)  # 移除持倉
        print(f"Sell {asset} for rebalance @ {price:.2f} on {get_datetime().date()}")

def days_held(context, entry_dt):
    """計算持倉天數，用於再平衡判斷。"""
    cal = get_calendar('TEJ')
    today = get_datetime().normalize()
    sessions = cal.sessions_in_range(entry_dt.normalize(), today)
    return len(sessions) - 1  # entry 當天不算

# %% [code] cell 20
from zipline import run_algorithm
from zipline.utils.calendar_utils import get_calendar
# Setup for running the algorithm
capital_base = 1e6
start = '2021-01-01'  # Example start date
end = '2025-05-21'  # Example end date

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
                        custom_loader=loader_dict)

# %% [code] cell 21
from pyfolio.utils import extract_rets_pos_txn_from_zipline
import pyfolio as pf

# 從 results 資料表中取出 returns, positions & transactions
returns, positions, transactions = extract_rets_pos_txn_from_zipline(results)
benchmark_rets = results.benchmark_return  # 取出 benchmark 的報酬率

# %% [code] cell 22
# 繪製 Pyfolio 中提供的所有圖表
pf.tears.create_full_tear_sheet(returns=returns,
                                     positions=positions,
                                     transactions=transactions,
                                     benchmark_rets=benchmark_rets
                                    )
