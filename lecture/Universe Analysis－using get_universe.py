# -*- coding: utf-8 -*-
# Auto-generated from Universe Analysis－using get_universe.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# <span id="menu"></span>
# # Universe Analysis－using get_universe
#
# 分析股票池的產業分布與成交金額

# %% [markdown] cell 1
# ## 選單
#
# 1. [分析臺灣50指數成份股公司的產業分佈](#臺灣50)
# 2. [分析臺灣中型100指數成份股公司的產業分佈](#臺灣100)
# 3. [分析臺灣高股息指數成份股公司的產業分佈](#臺灣高股息)
# 4. [分析電子工業公司的產業分佈](#電子工業)
# 5. [分析上市ETF成交金額](#上市ETF)

# %% [code] cell 2
import tejapi
import os
import numpy as np
import pandas as pd

# set tej_key and base
os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"

# set date
start = end = '2024-05-31'

from matplotlib import pyplot as plt
plt.rc("font",family='MicroSoft YaHei',weight="bold")

import TejToolAPI
from zipline.sources.TEJ_Api_Data import get_universe
from zipline.utils.calendar_utils import get_calendar

# %% [markdown] cell 3
# 利用`get_universe`取得台灣50指數成份股

# %% [code] cell 4
tw50_ = get_universe(start, end, idx_id='IX0002')

# %% [code] cell 5
tw50_ 

# %% [markdown] cell 6
# `getUniverseSector`：繪製股票池產業分佈柱狀圖與圓餅圖

# %% [code] cell 7
def plot_sector_counts(sector_counts):
    
    # create bar chart of number of companies in each sector    
    from matplotlib import pyplot as plt
    plt.rc("font",family='MicroSoft YaHei',weight="normal")
    
    from matplotlib.ticker import MaxNLocator
    import matplotlib.ticker as ticker
        
    plt.figure(figsize=(12, 15), dpi=100)
    
    bar = plt.subplot2grid((5,5), (0,0), rowspan=2, colspan=5)
    pie = plt.subplot2grid((5,5), (2,0), rowspan=3, colspan=5)
    
    # Bar chart
    sector_counts.plot(
        kind='barh',        
        color='b',
#         rot=90,
        grid=True,
        fontsize=12,
        ax=bar,
    )

    plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    bar.set_title('股票池產業分布家數')
    bar.set_xlabel('家數')     

    
    num = list(sector_counts.values)
    explode = [0.1 if x == max(num) else 0 for x in num]
    
    # Pie chart
    sector_counts.plot(
        kind='pie', 
        colormap='Set3', 
        autopct='%.1f %%', # '%.2f %%'
        fontsize=12,
        ax=pie,
        labeldistance=1.1,
        pctdistance=0.9,
        explode = explode
    ) 
    pie.set_ylabel('')      
    pie.set_title('股票池產業分布占比 - %')
    
    
    plt.tight_layout(pad=5);
    
def getUniverseSector(start_date,
                      end_date,
                      trading_calendar=get_calendar('TEJ_XTAI'),
                      **kwargs):
    
    tickers = get_universe(start_date,
                           end_date,
                           trading_calendar = trading_calendar,
                           **kwargs)
        
    df_sector = TejToolAPI.get_history_data(ticker=tickers,
                                            columns=['Industry'], transfer_to_chinese=True,
                                            start = start_date,
                                            end = end_date)   

    counts = (df_sector.groupby('主產業別_中文').size())
    _c =[]
    counts.index = [ x.split(' ')[1]  if len(x)>0 else ' ' for x in counts.index]
    
    plot_sector_counts(counts[counts>0].sort_values(ascending=False)) 

# %% [markdown] cell 8
# <span id="臺灣50"></span>
# # 分析臺灣50指數成份股公司的產業分佈
# [Return to Menu](#menu)

# %% [code] cell 9
getUniverseSector(start, end, idx_id='IX0002')

# %% [markdown] cell 10
# <span id="臺灣100"></span>
# # 分析臺灣中型100指數成份股公司的產業分佈
# [Return to Menu](#menu)

# %% [code] cell 11
getUniverseSector(start, end, idx_id='IX0003')

# %% [markdown] cell 12
# <span id="臺灣高股息"></span>
# # 分析臺灣高股息指數成份股公司的產業分佈
# [Return to Menu](#menu)

# %% [code] cell 13
getUniverseSector(start, end, idx_id='IX0006')

# %% [markdown] cell 14
# <span id="電子工業"></span>
# # 分析電子工業公司的產業分佈
# [Return to Menu](#menu)

# %% [code] cell 15
getUniverseSector(start, end, main_ind_c='M2300 電子工業')

# %% [markdown] cell 16
# <span id="上市ETF"></span>
# # 分析上市ETF成交金額
# [Return to Menu](#menu)

# %% [code] cell 17
etf = get_universe(start, end, stktp_c=['ETF', '國外ETF'], mkt=['TWSE'])

# %% [code] cell 18
df_amount = TejToolAPI.get_history_data(ticker=etf, 
                                        columns=['Value_Dollars'], 
                                        transfer_to_chinese=False,
                                        start = '2023-01-01',
                                        end = end
                                        )  

# %% [code] cell 19
df_top = (df_amount.
          set_index(['coid','mdate']).
          unstack('coid').
          rolling(30).
          mean().
          iloc[-1].
          sort_values(ascending=False)['Value_Dollars'] #['成交金額_元']
         )

# %% [code] cell 20
df_top = (df_top.to_frame().
          join(tejapi.get('TWN/APISTOCK')[['coid','stk_name']].
               set_index('coid')).
          set_index('stk_name').iloc[:,0]
         )

# %% [code] cell 21
plt.figure(figsize=(8, 12), dpi=150)
    
bar = plt.subplot2grid((5,5), (0,0), rowspan=2, colspan=5)
    
df_top.nlargest(20).plot(
        kind='barh',        
        color='b',
#         rot=90,
        grid=True,
        ax=bar
    )
   
bar.set_xlabel('TWD')
bar.set_ylabel('')
bar.set_title('上市ETF 過去30日的平均成交金額 Top20（{}）'.format(df_amount.mdate.max().strftime('%Y-%m-%d')))

# %% [markdown] cell 22
# [Return to Menu](#menu)
