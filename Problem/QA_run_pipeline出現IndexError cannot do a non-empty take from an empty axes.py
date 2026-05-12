# -*- coding: utf-8 -*-
# Auto-generated from QA_run_pipeline出現IndexError cannot do a non-empty take from an empty axes.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # 問題集
# run_pipeline 出現 `IndexError cannot do a non-empty take from an empty axes.`
#
# # 解決方法:
# 使用 Pipeline 的 quantiles 時將 run_pipeline 的 start_date 至少設定為 bundle 的 start_date 後的下一個交易日。

# %% [markdown] cell 1
# # 環境及import設定

# %% [code] cell 2
import os
import time
import pandas as pd
import numpy as np 
from logbook import Logger, StderrHandler, INFO, WARNING

# tej_key
os.environ['TEJAPI_KEY'] = 'your key'
os.environ['TEJAPI_BASE'] = 'https://api.tej.com.tw'  

from zipline.sources.TEJ_Api_Data import get_universe

from zipline.data.run_ingest import simple_ingest

from zipline.TQresearch.tej_pipeline import run_pipeline

from zipline.pipeline import Pipeline
from zipline.pipeline.domain import TW_EQUITIES
from zipline.pipeline.data import EquityPricing

log_handler = StderrHandler(format_string='[{record.time:%Y-%m-%d %H:%M:%S.%f}]: ' +
                            '{record.level_name}: {record.func_name}: {record.message}',
                            level=INFO)
log_handler.push_application()
log = Logger('Algorithm')

# %% [code] cell 3
bundle_name = 'tquant'

# 取tejapi資料起日
start = '2024-01-02'
start_dt = pd.Timestamp(start, tz='UTC')

# 迄日
end = '2024-03-31'
end_dt= pd.Timestamp(end, tz='UTC')

# %% [markdown] cell 4
# # ingest

# %% [code] cell 5
# 設定ticker給ingest時使用
pool = get_universe(start,
                    end,
                    idx_id='IX0002'
                   )

# 價量資料（Pricing Data）
simple_ingest(name = 'tquant',
              tickers = pool+['IR0001'],
              start_date = start,
              end_date = end)

# %% [markdown] cell 6
# # 建立Pipeline

# %% [code] cell 7
my_pipe = Pipeline(domain = TW_EQUITIES)                         
my_pipe.add(EquityPricing.close.latest.quantiles(10), 'close_quartiles') 

# %% [markdown] cell 8
# # 問題

# %% [markdown] cell 9
# run_pipeline時出現錯誤`IndexError: cannot do a non-empty take from an empty axes.`。

# %% [code] cell 10
result = run_pipeline(my_pipe, start_dt, end_dt)

# %% [markdown] cell 11
# # 解法

# %% [markdown] cell 12
# 這個錯誤的原因是因為 pipeline 在 2024-01-02 計算 quantiles 時會試圖導入**前一個交易日**的資料，然而 bundle 的起始日為 2024-01-02 （參考`! zipline bundle-info`結果中的 start_date），找不到前一個交易日的資料，所以 pipeline 利用 `quantiles` 進行分群時便無法分群，進而引發錯誤。

# %% [code] cell 13
# ! zipline bundle-info

# %% [markdown] cell 14
# 將 run_pipeline 的 start_date 至少設定為 bundle 的 start_date 後的下一個交易日。
# - 以本案例來說 bundle 的 start_date 後的下一個交易日，是 2024-01-03，所以將 run_pipeline 的 start_date 設定為 2024-01-03 即可。

# %% [code] cell 15
rev_start_dt = TW_EQUITIES.next_open(start)
rev_start_dt

# %% [code] cell 16
result = run_pipeline(my_pipe, rev_start_dt, end_dt)

# %% [code] cell 17
result
