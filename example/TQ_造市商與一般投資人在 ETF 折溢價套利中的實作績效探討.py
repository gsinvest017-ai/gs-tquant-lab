# -*- coding: utf-8 -*-
# Auto-generated from TQ_造市商與一般投資人在 ETF 折溢價套利中的實作績效探討.ipynb by tools/ipynb_to_py.py
# Do not edit by hand; re-run the converter to regenerate.


# %% [code] cell 0
import matplotlib.pyplot as plt
import matplotlib as mpl
import tejapi
import pandas as pd
import numpy as np
tejapi.ApiConfig.api_key = "your key"
tejapi.ApiConfig.api_base = "your base"
data_use = tejapi.get('TWN/ANAV', coid = '0050', mdate={'gte':'2010-01-01', 'lte':'2025-06-09'})
data = data_use.copy()
data['mdate'] = pd.to_datetime(data['mdate'])  # 保險起見，先確保是 datetime 格式
data['mdate'] = data['mdate'].dt.strftime('%Y-%m-%d')  # 轉成你要的字串格式
data['mdate'] = pd.to_datetime(data['mdate'])
data.to_csv(f'0050_Net_VALUE.csv')


data_use = data[['mdate', 'fld004', 'fld005', 'fld006', 'fld007']].copy()
data_use['NAV_ret'] = data_use['fld004'].pct_change().fillna(0)
data_use['MV_ret'] = data_use['fld005'].pct_change().fillna(0)


split_date = '2021-01-04'
train_data = data_use[data_use['mdate'] < pd.to_datetime(split_date)].copy()
test_data = data_use[data_use['mdate'] >= pd.to_datetime(split_date)].copy()


mean = train_data['fld007'].mean()
std = train_data['fld007'].std()


mpl.rcParams['text.color'] = 'black' 
plt.style.use('ggplot')
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(20, 16), sharex=False)


axes[0].plot(data_use['mdate'], data_use['fld004'], label = 'Net Value')
axes[0].plot(data_use['mdate'], data_use['fld005'], label = 'Market Value')
axes[0].axvline(x = pd.to_datetime(split_date), color = 'black', linestyle = '--', label = 'Split Date')
axes[0].set_title('0050 ETF NET_MARKET Value', fontsize=18)
axes[0].legend()


axes[1].bar(data_use['mdate'], data_use['fld006'])
axes[1].axvline(x = pd.to_datetime(split_date), color = 'black', linestyle = '--')
axes[1].set_title(f'Price Premium (Discount) in NTD')

# %% [code] cell 1
plt.figure(figsize = (20, 6))
plt.hist(train_data['fld007'], bins = 30, edgecolor = 'white')
plt.axvline(x = mean, label = "Mean", color = 'black', linestyle = '--')
plt.title(f'Premium (Discount) in percent Distribution')
plt.legend()
plt.show()

# %% [code] cell 2
sta = 1
test_data['signal'] = np.where(test_data['fld007'] < mean - sta * std, -1,  # fld007 太低
                              np.where(test_data['fld007'] > mean + sta * std, 1, 0))  # fld007 太高


test_data['b_ret_nav'] = np.where(test_data['signal'].shift(1) == 1, test_data['NAV_ret'],
                                 np.where(test_data['signal'].shift(1) == -1, -test_data['NAV_ret'], 0))


test_data['b_ret_mv'] = np.where(test_data['signal'].shift(1) == 1, -test_data['MV_ret'],
                                np.where(test_data['signal'].shift(1) == -1, test_data['MV_ret'], 0))


test_data['c_ret_nav'] = (1 + test_data['b_ret_nav']).cumprod() - 1
test_data['c_ret_mv'] = (1 + test_data['b_ret_mv']).cumprod() - 1


test_data['b_ret'] = test_data['b_ret_mv'] + test_data['b_ret_nav']
test_data['c_ret'] = (1 + test_data['b_ret']).cumprod() - 1


cost = (0.001425 * 2 * 0.18 + 0.001)  # ETF 交易稅為 0.001
test_data['b_ret_nav_fee'] = np.where(test_data['signal'].shift(1) == 1, test_data['NAV_ret'] - cost,
                                 np.where(test_data['signal'].shift(1) == -1, -test_data['NAV_ret']- cost, 0))


test_data['b_ret_mv_fee'] = np.where(test_data['signal'].shift(1) == 1, -test_data['MV_ret'] - cost,
                                np.where(test_data['signal'].shift(1) == -1, test_data['MV_ret']- cost, 0))


test_data['b_ret_fee'] = test_data['b_ret_mv_fee'] + test_data['b_ret_nav_fee']
test_data['c_ret_fee'] = (1 + test_data['b_ret_fee']).cumprod() - 1




plt.style.use('ggplot')
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(18, 14), sharex=False)


axes[0].plot(test_data['mdate'], test_data['c_ret'], label='Strategy (Without Cost)')
axes[0].set_title(f'0050 ETF Arbitrage Cumulative Returns')
axes[0].plot(test_data['mdate'], test_data['c_ret_fee'], label='Strategy (With Cost)')
axes[0].legend()




axes[1].bar(test_data['mdate'], test_data['fld007'], label='fld007')
axes[1].axhline(y = mean, color = 'green', label = 'Mean', linestyle = '--')
axes[1].axhline(y = mean + sta*std, color = 'green', label = 'Upper bound', linestyle = '--')
axes[1].axhline(y = mean - sta*std, color = 'green', label = 'Lower bound', linestyle = '--')
axes[1].set_title(f'Price Premium (Discount) in percent')
axes[1].legend()


axes[2].hist(test_data['signal'], bins=[-1.5, -0.5, 0.5, 1.5], edgecolor='white', align='mid', color =  '#348ABD')
axes[2].set_xticks([-1, 0, 1])
axes[2].set_xticklabels(['Short', 'Neutral', 'Long'])
axes[2].set_title('Signal Distribution')


plt.tight_layout()
plt.show()


test_data.to_csv('0050ETF_Arbitrage.csv', index=False)


plt.figure(figsize=(20, 6))
plt.plot(test_data['mdate'], test_data['c_ret_nav'], label='NAV side')
plt.plot(test_data['mdate'], test_data['c_ret_mv'], label='Market side')
plt.legend()
plt.title('Contribution from NAV and Market')
plt.show()


test_data['position'] = test_data['signal'].shift(1)
test_data['trade_id'] = (test_data['position'] != test_data['position'].shift()).cumsum()


grouped = test_data.groupby('trade_id')
trade_summary = grouped.agg({
   'b_ret': 'sum',
   'position': 'first',
   'mdate': ['first', 'last', 'count']
})
# 攤平欄位名稱
trade_summary.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in trade_summary.columns]
# 重設索引
trade_summary = trade_summary.reset_index()


plt.figure(figsize=(20, 6))
plt.hist(trade_summary['b_ret_sum'], bins=20, edgecolor='white')
plt.title("Distribution of Trade Returns")
plt.show()
trades_with_result = trade_summary[trade_summary['b_ret_sum'] != 0]
win_rate = (trades_with_result['b_ret_sum'] > 0).mean()
avg_win = trade_summary[trade_summary['b_ret_sum'] > 0]['b_ret_sum'].mean()
avg_loss = trade_summary[trade_summary['b_ret_sum'] < 0]['b_ret_sum'].mean()
profit_factor = abs(avg_win / avg_loss)


print(f"勝率（Win Rate）：{win_rate:.2%}")
print(f"平均獲利（Avg Win）：{avg_win:.5f}")
print(f"平均虧損（Avg Loss）：{avg_loss:.5f}")
print(f"報酬因子（Profit Factor）：{profit_factor:.2f}")
