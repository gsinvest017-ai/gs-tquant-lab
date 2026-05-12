# -*- coding: utf-8 -*-
# Auto-generated from QA_run_pipeline的結果皆為na.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import os
import pandas as pd

# set tej_key and base
os.environ['TEJAPI_KEY'] = tej_key 
os.environ['TEJAPI_BASE'] = api_base

# set date
start = '2023-01-01'
end = '2023-01-31'    

# %% [code] cell 1
from zipline.sources.TEJ_Api_Data import get_universe

pool = get_universe(start, end, idx_id = 'IX0027')  # 取得電子類指數代碼

# %% [code] cell 2
tickers = ' '.join(pool)

os.environ['mdate'] = start+' '+end
os.environ['ticker'] = tickers

# !zipline ingest -b tquant

# %% [code] cell 3
import TejToolAPI

columns = ['Market', 'ROI', 'PER_TEJ']
data = TejToolAPI.get_history_data(start = start, 
                                   end = end,
                                   ticker=pool, 
                                   columns=columns
                                   )
data = data.sort_values(['coid','mdate'])
data

# %% [code] cell 4
from zipline.data import bundles

bundle_name = 'tquant'
bundle = bundles.load(bundle_name)

# %% [code] cell 5
from zipline.pipeline.data.dataset import Column, DataSet
from zipline.pipeline.domain import TW_EQUITIES

class OtherDatasets(DataSet):
     
    Market = Column(dtype=object)    
    ROI = Column(dtype=float)  
    PER_TEJ = Column(dtype=float)
 
    domain = TW_EQUITIES

# %% [code] cell 6
sids = bundle.asset_finder.equities_sids
assets = bundle.asset_finder.retrieve_all(sids)
symbol_mapping_sid = {i.symbol:i.sid for i in assets}
transform_data = data.set_index(['coid', 'mdate']).unstack('coid')
transform_data = transform_data.rename(columns = symbol_mapping_sid)
transform_data.index=transform_data.index.tz_localize('UTC')
transform_data

# %% [code] cell 7
from zipline.pipeline.loaders.frame import DataFrameLoader
custom_loader = {}

inputs=[
        OtherDatasets.Market,
        OtherDatasets.ROI,
        OtherDatasets.PER_TEJ,  
        ]

for i in inputs:
    custom_loader[i]=DataFrameLoader(column=i,
                                     baseline=transform_data[i.name])

custom_loader

# %% [code] cell 8
from zipline.pipeline import SimplePipelineEngine
from zipline.pipeline.data import TWEquityPricing
from zipline.pipeline.loaders import EquityPricingLoader
pricing_loader = EquityPricingLoader.without_fx(bundle.equity_daily_bar_reader,
                                                bundle.adjustment_reader)
def choose_loader(column):
    if column.name in TWEquityPricing._column_names:
        return pricing_loader
    elif column.name in OtherDatasets._column_names:     
        return custom_loader[column]
    else:
        raise Exception('Column not available')
    
engine = SimplePipelineEngine(get_loader = choose_loader,
                              asset_finder = bundle.asset_finder,
                              default_domain = TW_EQUITIES)

# %% [code] cell 9
from zipline.pipeline import Pipeline

def make_pipeline():

    return Pipeline(
        columns={
            'price': TWEquityPricing.close.latest,
            'Market': OtherDatasets.Market.latest,
            'ROI': OtherDatasets.ROI.latest,
            'PER_TEJ': OtherDatasets.PER_TEJ.latest
            }
    )

start_dt = pd.Timestamp(start, tz = 'UTC')
end_dt = pd.Timestamp(end, tz = 'UTC')

pipeline_result = engine.run_pipeline(make_pipeline(), start_dt, end_dt)
pipeline_result 
