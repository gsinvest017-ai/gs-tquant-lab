# -*- coding: utf-8 -*-
# Auto-generated from QA_處理自建因子.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# ![image.png](attachment:image.png)

# %% [markdown] cell 1
# ## 問題集:
#
# 1. 如何使用 TejToolAPI 自建因子。
# 2. 如何將因子導入 TQuant Lab 回測平台中。

# %% [code] cell 2
import tejapi
import os
os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from zipline.data import bundles
from zipline.pipeline import Pipeline
from zipline.pipeline.data import Column, DataSet,TWEquityPricing
from zipline.pipeline.domain import TW_EQUITIES
from zipline.pipeline.factors import CustomFactor
from zipline.pipeline.loaders.frame import DataFrameLoader
from zipline.pipeline.loaders import EquityPricingLoader
from zipline.pipeline.engine import SimplePipelineEngine

# %% [markdown] cell 3
# - 建立bundle與取得bundle的股票

# %% [code] cell 4
bundle_name = 'tquant'
bundle = bundles.load(bundle_name)

# %% [code] cell 5
sids = bundle.asset_finder.equities_sids
assets = bundle.asset_finder.retrieve_all(sids)
symbols = [i.symbol for i in assets]
symbols

# %% [markdown] cell 6
# - 取得交易日

# %% [code] cell 7
start = '2015-01-03'
end = '2023-05-18'

start_dt = pd.Timestamp(start, tz='utc')
end_dt = pd.Timestamp(end, tz='utc')

dateindex = bundle.equity_daily_bar_reader.sessions[bundle.equity_daily_bar_reader.sessions>=start_dt]

# %% [markdown] cell 8
# - 取得月營收資料庫所有資料，相關欄位說明參考[tejapi](http://10.10.10.66/columns.html?idCode=TWN/APISALE)

# %% [code] cell 9
sales_data = (tejapi.get('TWN/APISALE',coid=symbols,
                         mdate={'gte':start_dt,'lte':end_dt}, paginate=True)
                        .dropna(subset=["annd_s"]).drop(columns=['mdate'])
                        .rename(columns={'annd_s':'mdate'})  
                        .drop_duplicates(subset=['coid','mdate'], keep='first'))
sales_data.tail(10)

# %% [markdown] cell 10
# - 計算過去12個月多少單月營收大於0

# %% [code] cell 11
sales_data['sales_count'] = sales_data[['coid','mdate','d0003']].sort_values(by=['coid','mdate']).groupby('coid')['d0003'].rolling(12).apply(lambda x: sum(x>0)).values

# %% [code] cell 12
sales_data[['coid','mdate','d0003','sales_count']].tail(20)

# %% [markdown] cell 13
# - 建立變數`custom_data`，將加總將過去12個月月營收成長率大於0的月份數`sales_count`、累積三個月營收成長率`sales_3yoy`，存入變數。

# %% [code] cell 14
custom_data = sales_data[['mdate','coid','sales_count','r25']].rename(columns={'r25':'sales_3yoy'})
custom_data

# %% [markdown] cell 15
# - 將custom_data 轉換為pipeline需要個格式

# %% [code] cell 16
def load_other_datasets(df, bundle, column):
        
    df['coid']=df['coid'].astype(str)       

    df1 = df[['coid', 'mdate']+[column]].set_index(['coid', 'mdate'])
    symbols = df1.index.get_level_values(0).unique().tolist()  
    assets = bundle.asset_finder.lookup_symbols(symbols, as_of_date=None)
    sids = pd.Int64Index([asset.sid for asset in assets])
    symbol_map = dict(zip(symbols, sids))
            
    return  (df1
            .unstack('coid')
            .rename(columns=symbol_map)
            .tz_localize('UTC')
            .tz_convert('UTC'))[column]

# %% [code] cell 17
transform_data1 = load_other_datasets(custom_data, bundle, 'sales_count').reindex(dateindex).fillna(method='ffill')
transform_data2 = load_other_datasets(custom_data, bundle, 'sales_3yoy').reindex(dateindex).fillna(method='ffill')

# %% [markdown] cell 18
# - 建立CustomDataset並在物件底下放入兩個欄位，分別為sales_count、sales_3yoy，最後指定指定台股交易日 TW_EQUITIES
# - 指定非價格資料的loader為CustomDataset

# %% [code] cell 19
class CustomDataset(DataSet):
    sales_count = Column(dtype=float)
    sales_3yoy = Column(dtype=float)    
    domain = TW_EQUITIES  

# %% [code] cell 20
Custom_loader= {CustomDataset.sales_count: DataFrameLoader(column   = CustomDataset.sales_count,
                                                           baseline = transform_data1),
                CustomDataset.sales_3yoy: DataFrameLoader(column   = CustomDataset.sales_3yoy,
                                                          baseline = transform_data2),               
               }

# %% [markdown] cell 21
# - 建立因子 
#     - 因子1. 加總過去12個月，月營收成長率大於0的個數，並判斷大於等於6時給予因子值True，否則為False
#         - sales_yoy_bool = CustomDataset.sales_count.latest.__ge__(6)
#     - 因子2. 累積三個月營收成長率，使用外部匯入的資料
#         - sales_3yoy = CustomDataset.sales_3yoy.latest
#     - 因子3. 目前股價距離過去三年最高點的距離百分比
#         - 定義maxpercent函數
#         - maxpercent_3yr = maxpercent(inputs = [TWEquityPricing.close],window_length = 252*3 )

# %% [code] cell 22
class maxpercent(CustomFactor):

    def compute(self, today, assets, out, data):
        out[:] = data[-1]/np.max(data,axis=0)  

def make_pipeline():
    
    close = TWEquityPricing.close.latest
      
    sales_count = CustomDataset.sales_count.latest
    sales_3yoy = CustomDataset.sales_3yoy.latest
    sales_yoy_bool = CustomDataset.sales_count.latest.__ge__(6)
    maxpercent_3yr = maxpercent(inputs = [TWEquityPricing.close],window_length = 252*3 )
      
    return  Pipeline(columns={'close':close,
                              'sales_count':sales_count,
                              'sales_3yoy':sales_3yoy,
                              'sales_yoy_bool':sales_yoy_bool,
                              'maxpercent_3yr':maxpercent_3yr
                              },                             
                     )

# %% [code] cell 23
bundle_data = bundles.load(bundle_name)
pricing_loader =EquityPricingLoader.without_fx(bundle_data.equity_daily_bar_reader, bundle_data.adjustment_reader)

def choose_loader(column):
    if column in TWEquityPricing.columns:
        return pricing_loader
    return Custom_loader[column]    

# Create a Pipeline engine
engine = SimplePipelineEngine(get_loader = choose_loader,
                              asset_finder = bundle_data.asset_finder)

results = engine.run_pipeline(make_pipeline(), start_dt, end_dt)

# %% [code] cell 24
results
