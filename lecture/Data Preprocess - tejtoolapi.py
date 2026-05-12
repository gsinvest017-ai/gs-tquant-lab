# -*- coding: utf-8 -*-
# Auto-generated from Data Preprocess - tejtoolapi.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # TEJTOOLAPI 資料撈取整併
# 運用 TEJTOOLAPI 整併資料。TEJTOOLAPI 主要整併股價與不同屬性的資料庫，透過輸入股票代碼 (TICKERS) 和欄位 (FIELD) 後，可將欲抓取的資料整併為以日頻率的 DataFrame。
#
# 目前可抓取的資料庫為：
# - 股價交易資訊(TWN/APIPRCD)
# - 月營收(TWN/APISALE1)
# - 會計師簽證財務資料(TWN/AINVFQ1)
# - 三大法人、融資券、當沖(TWN/APISHRACT)
# - 集保庫存(TWN/APISHRACTW)
# - 股票日交易註記資訊(TWN/APISTKATTR)
# - 交易日期表(TWN/TRADEDAY_TWSE)
# - 董監全體持股狀況(TWN/APIBSTN1)
# - 全面改選統計(TWN/APICHGSTAT)
# - 董事長與高階主管變動事件(TWN/APIDIRCHG)
# - 合併收購(TWN/APIMA)
# - 股利政策(TWN/APIMT1)
# - 資本形成(TWN/APISTK1)
# - 私募應募人與公司的關係(TWN/APISTKPRV)
# - 董監申報轉讓-轉讓(TWN/APITRANS1)
# - 董監申報轉讓-未轉讓(TWN/APITRANS2)
# - 庫藏股實施事件簿(TWN/APITRS)
#
# 主要整併方法是以交易日期表為索引整併股價與不同屬性的資料，以下示範 TEJTOOLAPI 整併股價與不同屬性資料表的所有欄位。
#
# tejtoolapi 及以上資料庫相關欄位 : 
# - [資料集](https://tquant.tejwin.com/資料集/)
# - [欄位對照表](https://view.officeapps.live.com/op/view.aspx?src=https%3A%2F%2Ftquant.tejwin.com%2Fwp-content%2Fuploads%2FTEJ-TOOL-API%25E6%25AC%2584%25E4%25BD%258D%25E5%25B0%258D%25E7%2585%25A7%25E6%25B8%2585%25E5%2596%25AE20251126.xlsx&wdOrigin=BROWSELINK)

# %% [markdown] cell 1
# ### 1. 環境設定

# %% [code] cell 2
import os
os.environ['TEJAPI_KEY'] = "your key" 
os.environ['TEJAPI_BASE'] = "https://api.tej.com.tw"

import TejToolAPI

# %% [markdown] cell 3
# ### 2. 設定 tickers

# %% [code] cell 4
tickers = ['2330','2454','2317','2882','2881']

# %% [markdown] cell 5
# ### 3. tejtoolapi 取得單獨資料庫

# %% [markdown] cell 6
# 3.1、月營收的欄位

# %% [code] cell 7
columns = [
       'Sales_Accu_LastYear', 'Sales_Accu_3M',
       'Sales_Per_Share_Accu_12M', 'YoY_Accu_Sales', 'YoY_Monthly_Sales',
       'Sales_Per_Share_Accu_3M', 'Sales_Accu_3M_LastYear', 'Sales_Monthly',
       'YoY_AccuSales_12M', 'YoY_Accu_Sales_3M', 'MoM_Monthly_Sales',
       'Sales_Accumulated', 'QoQ_Accu_Sales_3M', 'MoM_Accu_Sales_3M',
       'Sales_Monthly_LastYear', 'Outstanding_Shares_1000_Shares_Monthly_Frequency'
]

data = TejToolAPI.get_history_data(
       ticker=tickers, 
       columns=columns,
       transfer_to_chinese=False
)
data.head(5)   

# %% [markdown] cell 8
# 3.2、量化籌碼_周 - 集保庫存欄位

# %% [code] cell 9
columns = [
       'Total_Custodied_Shares_1000_Lots',
       'Custodied_Under_400_Lots_Total_Lots',
       'Custodied_Lots_Between_800_1000_Total_Lots',
       'Custodied_Larger_Than_400_Lots_Pct',
       'Custodied_Lots_Between_400_600_Total_Lots',
       'Custodied_Lots_Between_600_800_Pct', 
       'Pledged_Stock_Shares_1000_Lots',
       'Custodied_Under_400_Lots_Pct',
       'Custodied_Lots_Between_400_600_Total_Holders',
       'Custodied_Lots_Between_800_1000_Total_Holders',
       'Custodied_Under_400_Lots_Total_Holders',
       'Custodied_Lots_Between_400_600_Pct',
       'Custodied_Lots_Between_800_1000_Pct',
       'Custodied_Greater_Than_1000_Lots_Pct'
]

data = TejToolAPI.get_history_data(
       ticker=tickers, 
       columns=columns,
       transfer_to_chinese=False
)                                 
    
data.head(5)  

# %% [markdown] cell 10
# 3.3、量化籌碼_日& 交易註記 欄位

# %% [code] cell 11
ticker = tickers
columns =[
       'Market', 'Dealer_Proprietary_Diff_Vol', 'Margin_Sale',
       'Cash_Redemption', 'Margin_Short_Balance_Amt',
       'Margin_Short_Balance_Vol', 'Dealer_Hedge_Buy_Vol',
       'Day_Trading_Volume_1000_Shares', 'SBL_Short_Returns_Vol',
       'Security_Type_English', 'Attention_Stock_Fg', 'Industry_Eng',
       'Component_Stock_of_TPEx50_Fg', 'Limit_Up_or_Down_in_Opening_Fg',
       'Limit_Up_or_Down'
]

data = TejToolAPI.get_history_data(
       ticker=tickers, 
       columns=columns,
       transfer_to_chinese=False,                                    
)                                 
    
data.head(5)  

# %% [markdown] cell 12
# 3.4、抓取財務資料參數設定
#
# `ticker`
# - 單一股票  :['2330'] 
# - 多股      :['2330','2317']
#
# `columns`
# - 欄位: columns=['r408','r409','r502']
#
# `transfer_chinese_columns`
# - 預設 transfer_chinese_columns = False
# - 測試欄位轉換成中文(transfer_chinese_columns = True)
#
# `fin_type = [A, Q, TTM]`
# - A: 表示累積
# - Q: 表示單季
# - TTM: 表示移動4季
#
# `include_self_acc`
# - 投資用財務包含自結和董事會決議數(include_self_acc = 'Y')
# - 僅投資用財務(include_self_acc = 'N')

# %% [markdown] cell 13
# 3.4.1、財務僅會計師核閱

# %% [code] cell 14
columns =[
       'Total_Operating_Income',
       'Net_Operating_Income_Loss',
       'Gross_Profit_Loss_from_Operations'
]

fin_type = ['A','Q','TTM']

data = TejToolAPI.get_history_data(ticker=tickers, columns=columns, transfer_to_chinese=False, fin_type=fin_type, include_self_acc='N')
data.head(5)

# %% [markdown] cell 15
# 3.4.2、財務包含公司自結數與會計師核閱

# %% [code] cell 16
columns =[
       'Total_Operating_Income',
       'Net_Operating_Income_Loss',
       'Gross_Profit_Loss_from_Operations'
]

fin_type = ['A','Q','TTM']

data = TejToolAPI.get_history_data(ticker=tickers, columns=columns, transfer_to_chinese=False, fin_type=fin_type, include_self_acc='Y')
data.head(5)

# %% [markdown] cell 17
# ### 4、以下範例示範運用 TejToolAPI 一鍵抓取不同資料庫的欄位與整併。
# - **股價資料庫(日頻)**
#     - 開盤價、收盤價
# - **籌碼資料庫(日頻)**
#     - 外資買賣超張數、合計買賣超張數
# - **交易註記資料庫(日頻)**
#     - 是否為注意股票、是否暫停交易、是否為臺灣50成分股、是否為處置股票、分盤間隔時間
# - **集保資料庫(周頻)**
#     - 800-1000張集保占比、800-1000張集保張數    
# - **財報資料庫(季頻)**
#     - 營業毛利成長率_Q、營業利益成長率_Q、稅後淨利率_Q	

# %% [code] cell 18
# 輸入欄位
icolumns = [
    'Open','Close',
    'Qfii_Diff_Vol','Total_Diff_Vol',
    'Custodied_Lots_Between_800_1000_Total_Lots','Custodied_Lots_Between_800_1000_Pct',
    'Attention_Stock_Fg','Disposition_Stock_Fg','Matching_Period','Suspended_Trading_Stock_Fg','Component_Stock_of_TWN50_Fg',
    'Gross_Margin_Growth_Rate','Net_Income_Rate_percent','Operating_Income_Growth_Rate'
]
# TEJTOOLAPI整併
data = TejToolAPI.get_history_data(
    ticker=tickers, 
    columns=icolumns,
    transfer_to_chinese=True, 
    fin_type = ['Q'],
    start = '2015-01-01', 
    end = '2022-12-31'
)
data.head(5)

# %% [markdown] cell 19
# 抓取股價資料庫與籌碼料庫

# %% [code] cell 20
columns = [
    'Open','High','Low','Close','Adjust_Factor','Volume_1000_Shares',
    'Qfii_Buy_Vol','Qfii_Sell_Vol','Qfii_Diff_Vol','Qfii_Buy_Amt','Qfii_Sell_Amt','Qfii_Diff_Amt'
]
data = TejToolAPI.get_history_data(
    ticker=ticker, 
    columns=columns,
    transfer_to_chinese=False, 
    start='2015-01-01',
    end='2022-12-31'
)
data.head(5)

# %% [markdown] cell 21
# 抓取財務資料(default:僅會計師核閱)

# %% [code] cell 22
columns = ['r404','r401','eps']
fin_type = ['A','Q','TTM']
data = TejToolAPI.get_history_data(ticker=tickers, columns=columns,transfer_to_chinese=True, fin_type=fin_type)
data.head(5)

# %% [markdown] cell 23
# 抓取財務資料僅會計師核閱

# %% [code] cell 24
columns = ['r404','r401','eps']
fin_type = ['A','Q','TTM']
data = TejToolAPI.get_history_data(ticker=tickers, columns=columns,transfer_to_chinese=True, fin_type=fin_type, include_self_acc='N')
data.head(5)

# %% [markdown] cell 25
# 抓取財務資料含自結數

# %% [code] cell 26
columns = ['r404','r401','eps']
fin_type = ['A','Q','TTM']
data = TejToolAPI.get_history_data(ticker=tickers, columns=columns,transfer_to_chinese=True, fin_type=fin_type)
data.head(5)
