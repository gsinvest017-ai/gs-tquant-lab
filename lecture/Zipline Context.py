# -*- coding: utf-8 -*-
# Auto-generated from Zipline Context.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [markdown] cell 0
# # Zipline Context 功能介紹

# %% [markdown] cell 1
# __請於閱讀本文前，預先閱讀 TSMC buy and hold strategy，以了解四大函式 (initialize, handel_data, analyze, run_algorithm) 使用方法。__
#
# 在 Zipline 程式運行中的各種數據，會記錄在context並不斷更新，所以在程式運行中，可以隨時取得即時資訊。下面介紹幾個常用項目：
#     
#     context.asset
#     contexas.account
#     context.portfolio
#     context.blotter

# %% [markdown] cell 2
# # context.asset

# %% [markdown] cell 3
# 在 initialize 的階段可以加入
#
#     context.tickers = ['1216', '2330', '2327']
#     context.asset = [symbol(ticker) for ticker in context.tickers]  
#
# 建立一個股票清單：[Equity(2 [1216]), Equity(14 [2330]), Equity(13 [2327])]，格式是 list，裡面資料型態是 zipline.asset.Assets，這樣在handle_data 階段就可以用來選取股票。

# %% [markdown] cell 4
# ## context.account

# %% [markdown] cell 5
# account 裡面的資訊，大多都是來自 context.portfolio，共計有：
#     
#     account.settled_cash = portfolio.cash 帳上現金
#     account.accrued_interest = 0.0。股票不適用。
#     account.buying_power = np.inf （無限大）。股票不適用。
#     account.equity_with_loan = portfolio.portfolio_value 投資組合總市值
#     account.total_positions_value = portfolio.portfolio_value - portfolio.cash 投資組合總市值 - 現金
#     account.total_positions_exposure = portfolio.positions_exposure sum(股數 * 當天收盤價)，long為正值，short為負值
#     account.regt_equity = portfolio.cash 現金
#     account.regt_margin = np.inf （無限大）。股票不適用。
#     account.initial_margin_requirement = 0.0 必須保證金。股票不適用。
#     account.maintenance_margin_requirement = 0.0 維持保證金。股票不適用。
#     account.available_funds = portfolio.cash 現金
#     account.excess_liquidity = portfolio.cash 現金
#     account.cushion = portfolio.cash / portfolio.portfolio_value 現金 / 投資組合總市值，後者如果是 0 則回傳 np.inf （無限大）
#     account.day_trades_remaining = 剩餘交易日，預設np.inf （無限大）。股票不適用。
#     account.net_liquidation = portfolio.portfolio_value
#     account.gross_leverage = gross_exposure / portfolio_value 後者如果是 0 則回傳 np.inf （無限大）
#     account.net_leverage = net_exposure / portfolio_value 後者如果是 0 則回傳 np.inf （無限大）
#     account.leverage = account.gross_leverage
#     
# gross_exposure算法：sum(股數 * 當天收盤價)。其中，股數不管是long或short都是正值
#
# net_exposure算法：sum(股數 * 當天收盤價)。其中，股數long為正，short為負

# %% [markdown] cell 6
# ## context.portfolio

# %% [markdown] cell 7
# portfolio裡面的資訊，有一些也同時出現在回測產出的資料中，但是有些計算方式不太一樣
#     
#     cash_flow：從開始日到當天的累計現金流，流入正流出負
#     starting_cash：起始資金，不是當天開始時的現金
#     portfolio_value：positions_value + cash 投資組合總市值
#     pnl：累計的pnl，為 portfolio_value - 起始資金
#     returns：累計return，( 1 + 每日 pnl / 每日起始 portfolio_value) 的乘積 - 1
#     cash：回測資料中的 ending_cash
#     positions：帳上的股票部位
#     start_date：整個測試的開始日
#     positions_value：跟 net_exposure 算法一樣，sum(股數 * 當天收盤價)。其中，股數long為正，short為負
#     positions_exposure：買賣股票時 value = exposure，跟上面一樣 參考~\zipline\finance\_finance_ext.pyx
#     
# context.portfolio.positions 回傳內容範例：
#
# {Equity(0 [1101]): Position({'asset': Equity(0 [1101]), 'amount': 1000, 'cost_basis': 45.56483750129291, 'last_sale_price': 45.1, 'last_sale_date': Timestamp('2018-07-25 05:30:00+0000', tz='UTC')}), Equity(14 [2330]): Position({'asset': Equity(14 [2330]), 'amount': -1000, 'cost_basis': 240.65657496810346, 'last_sale_price': 240.5, 'last_sale_date': Timestamp('2018-07-25 05:30:00+0000', tz='UTC')})}

# %% [markdown] cell 8
# ## context.blotter

# %% [markdown] cell 9
# blotter主要紀錄訂單相關的資訊
#
# 1. slippage_models 紀錄這次模擬時，股票和期貨所用的slippage model，範例：
#
#     {<class 'zipline.assets._assets.Equity'>: VolumeShareSlippage(
#     volume_limit=0.025,
#     price_impact=0.1), <class 'zipline.assets._assets.Future'>: VolatilityVolumeShare(volume_limit=0.05, eta=<varies>)}
#
#     
# 2. commissions_models 概念相同，範例：
#
#      {<class 'zipline.assets._assets.Equity'>: PerDollar(cost_per_dollar=0.001425), <class 'zipline.assets._assets.Future'>: 
#     PerContract(cost_per_contract=0.85, exchange_fee=<varies>, min_trade_cost=0)}
#
#     
# 3. open_orders：回傳字典，key是asset (例如 symbol('2327'))，對應list，list裡面是該股票的open orders：
#     
#     Order({'id': 'c201d801586349febfd88f3b97b35738', 'dt': Timestamp('2022-10-20 05:30:00+0000', tz='UTC'), 'reason': None, 
#     'created': Timestamp('2022-10-20 05:30:00+0000', tz='UTC'), 'amount': 1000, 'filled': 0, 'commission': 0, 'stop': None, 
#     'limit': None, 'stop_reached': False, 'limit_reached': False, 'sid': Equity(11 [2327]), 'status': <ORDER_STATUS.OPEN: 0>})
#     
#
# 4. orders：目前為止所有的訂單，包括open, canceled, filled，回傳格式是字典，key是order id，對應的是和上面一樣的 <class 'zipline.finance.order.Order'>
#
#
# 5. new_orders：當天創立的訂單，回傳一個清單，裡面物件和上面一樣，<class 'zipline.finance.order.Order'>
#
#
# 6. current_dt： 當日日期

# %% [markdown] cell 10
# ## context.sim_params

# %% [markdown] cell 11
# sim_params紀錄各種模擬的參數，範例：
#
#     SimulationParameters(
#     start_session=2022-12-05 00:00:00+00:00,
#     end_session=2022-12-23 00:00:00+00:00,
#     capital_base=1000000.0,
#     data_frequency=daily,
#     emission_rate=daily,
#     first_open=2022-12-05 01:01:00+00:00,
#     last_close=2022-12-23 05:30:00+00:00,
#     trading_calendar=<exchange_calendars.exchange_calendar_tejxtai.TEJ_XTAIExchangeCalendar object at 0x000001B76D7682E0>
#     )
#
# 1. start_session：開始日，UTC午夜時間
# 2. end_session：結束日，UTC午夜時間
# 3. capital_base：起始資金
# 4. data_frequency：資料頻率，目前僅支援日頻率
# 5. emission_rate：計算頻率，也是每日
# 6. first_open：第一個開始交易時間
# 7. last_close：最後一個收盤時間
# 8. trading_calendar：使用的交易日曆(TEJ_XTAI)
