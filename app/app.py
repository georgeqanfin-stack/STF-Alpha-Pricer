import streamlit as st
import pandas as pd
import numpy as np
import pickle
import matplotlib.pyplot as plt

st.set_page_config(page_title='STF-Alpha-Pricer', page_icon='📊', layout='wide')

def load_all():
    df = pd.read_csv('data/fred_master.csv', parse_dates=['date'], index_col='date')
    fx = pd.read_csv('data/fx_oracle_clean.csv', parse_dates=['observation_date'], index_col='observation_date')
    comm = pd.read_csv('data/commodity_adj.csv', index_col='commodity')
    corr = pd.read_csv('data/corridor_map.csv', index_col='corridor')
    return df, fx, comm, corr

def load_model():
    with open('data/xgboost_model.pkl', 'rb') as f:
        return pickle.load(f)

df, fx, comm, corr = load_all()
model = load_model()

features = ['SPREAD_LAG5','SPREAD_LAG21','SPREAD_LAG63','SPREAD_VOL21',
            'DXY_21D_CHG','DXY_63D_CHG','VIX_21D_CHG','VIX_LEVEL',
            'RATE_LEVEL','RATE_21D_CHG','DBAA_LEVEL']

# ── Sidebar ───────────────────────────────────────────────────────────────
st.sidebar.header('Deal Parameters')
invoice_value = st.sidebar.number_input('Invoice Value (USD)', min_value=100000, max_value=500000000, value=5000000, step=100000, format='%d')
tenor_days = st.sidebar.selectbox('Tenor (days)', options=[30,60,90,120,180], index=2)
commodity = st.sidebar.selectbox('Commodity', options=['Copper','Iron Ore','Crude Oil','Aluminium','Zinc'])
corridor = st.sidebar.selectbox('Trade Corridor', options=['Asia to Europe','Americas to Asia','Africa to Asia','Middle East to Asia','Asia to Americas'])

fx_code = corr.loc[corridor, 'fx_code']
fx_pair_name = corr.loc[corridor, 'fx_pair']
st.sidebar.markdown(f'<small style="color:#9CA3AF">FX pair: <b>{fx_pair_name}</b></small>', unsafe_allow_html=True)
rationale_map = {
    'Asia to Europe':      'INR proxy for Asian exporter settlement risk against EUR',
    'Americas to Asia':    'China dominant buyer of LatAm copper, iron ore and soy',
    'Africa to Asia':      'ZAR benchmark for African commodity export corridors',
    'Middle East to Asia': 'India largest Middle East oil importer; INR settlement risk',
    'Asia to Americas':    'MXN proxy for Latin American commodity importer FX risk',
}
st.sidebar.markdown(f'<small style="color:#6B7280">{rationale_map[corridor]}</small>', unsafe_allow_html=True)

profit_margin_bps = st.sidebar.slider('Profit Margin (bps)', min_value=50, max_value=300, value=150, step=25)
st.sidebar.divider()
st.sidebar.caption('Macro risk: XGBoost trained 2006-2019')
st.sidebar.caption('FX regime: Lorentzian KNN, k=21, 252-day rolling')
st.sidebar.caption('Commodity adj: IMF 3Y annualised price vol')

# ── Compute components ────────────────────────────────────────────────────
base_rate = df['DGS3MO'].dropna().iloc[-1]
base_rate_bps = base_rate * 100

latest_features = df[features].dropna().iloc[-1]
latest_date = df[features].dropna().index[-1]
predicted_spread_pct = float(model.predict(latest_features.values.reshape(1,-1))[0])
risk_premium_bps = predicted_spread_pct * 100

fx_subset = fx[fx['FX_CODE'] == fx_code]
fx_latest = fx_subset.iloc[-1]
fx_regime = fx_latest['REGIME']
fx_hedge_bps = float(fx_latest['HEDGE_COST_BPS'])
fx_spot = float(fx_latest['SPOT'])
fx_vol = float(fx_latest['VOL21'])

comm_bps = int(comm.loc[commodity, 'adj_bps'])
comm_vol = float(comm.loc[commodity, 'vol_pct'])

tenor_adj_bps = int((tenor_days - 90) / 30 * 10)

total_bps = base_rate_bps + risk_premium_bps + fx_hedge_bps + comm_bps + tenor_adj_bps + profit_margin_bps
total_rate = total_bps / 100
finance_cost_usd = invoice_value * (total_rate / 100) * (tenor_days / 365)

# ── Header ────────────────────────────────────────────────────────────────
st.title('STF-Alpha-Pricer')
st.caption('Commodity Trade Finance Discount Rate Engine  |  XGBoost Macro Risk  +  Lorentzian FX Oracle  +  IMF Commodity Volatility')
st.markdown('<p style="color:#6B7280; font-size:13px;">Built by <b>George P Babu</b></p>', unsafe_allow_html=True)
st.divider()

# ── Top metrics ───────────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric('All-in Rate', f'{total_rate:.2f}%')
c2.metric('Finance Cost', f'${finance_cost_usd:,.0f}')
c3.metric('Risk Premium', f'{risk_premium_bps:.0f} bps')
c4.metric('FX Hedge Cost', f'{fx_hedge_bps:.0f} bps', help=f'{fx_pair_name} | {fx_regime}')
c5.metric('Commodity Adj', f'{comm_bps} bps', help=f'{commodity} 3Y vol: {comm_vol:.1f}%')
st.divider()

# ── Waterfall chart ───────────────────────────────────────────────────────
st.subheader('Rate Breakdown')

comp_labels = ['Base Rate', 'Macro Risk', f'FX Hedge', f'{commodity}', f'Tenor', 'Margin', 'All-in']
comp_sublabels = ['3M T-Bill', 'XGBoost', fx_pair_name, f'{comm_vol:.1f}% vol', f'{tenor_days}d', f'{profit_margin_bps}bps', f'{total_rate:.2f}%']
comp_values = [base_rate_bps, risk_premium_bps, fx_hedge_bps, comm_bps, tenor_adj_bps, profit_margin_bps, total_bps]

bottoms = []
running = 0
for v in comp_values[:-1]:
    bottoms.append(running)
    running += v

bar_colors = ['#3B82F6','#EF4444','#F97316','#A855F7','#6B7280','#22C55E','#F59E0B']

fig, ax = plt.subplots(figsize=(12,4))
fig.patch.set_facecolor('#0E1117')
ax.set_facecolor('#0E1117')

for i,(val,bot,col) in enumerate(zip(comp_values[:-1], bottoms, bar_colors[:-1])):
    ax.bar(i, val, bottom=bot, color=col, width=0.5, zorder=3, alpha=0.92)
    ax.text(i, bot+val/2, f'{val:.0f}', ha='center', va='center', color='white', fontsize=10, fontweight='bold')
    if i < len(comp_values)-2:
        ax.plot([i+0.25, i+0.75], [bot+val, bot+val], color='#4B5563', linewidth=1, linestyle='--', zorder=2)

ax.bar(len(comp_values)-1, total_bps, color='#F59E0B', width=0.5, zorder=3, alpha=0.95)
ax.text(len(comp_values)-1, total_bps/2, f'{total_bps:.0f}', ha='center', va='center', color='white', fontsize=10, fontweight='bold')

tick_labels = [f'{l}\n{s}' for l,s in zip(comp_labels, comp_sublabels)]
ax.set_xticks(range(len(comp_labels)))
ax.set_xticklabels(tick_labels, color='#9CA3AF', fontsize=8.5)
ax.set_ylabel('Basis Points', color='#9CA3AF', fontsize=9)
ax.set_ylim(0, total_bps*1.18)
ax.tick_params(colors='#9CA3AF')
for spine in ['bottom','left']: ax.spines[spine].set_color('#374151')
for spine in ['top','right']: ax.spines[spine].set_visible(False)
ax.yaxis.grid(True, color='#1F2937', linewidth=0.8, zorder=0)
ax.set_axisbelow(True)
ax.set_title(f'All-in Rate: {total_rate:.2f}%  ({total_bps:.0f} bps)', color='white', fontsize=12, pad=12)
plt.tight_layout()
st.pyplot(fig)
plt.close()

st.divider()

# ── Market context ────────────────────────────────────────────────────────
st.subheader('Market Context')
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown('**Macro Stress**')
    hist_mean = 3.62
    stress_label = 'ELEVATED' if predicted_spread_pct > hist_mean else 'MODERATE' if predicted_spread_pct > hist_mean*0.75 else 'LOW'
    stress_color = 'red' if stress_label=='ELEVATED' else 'orange' if stress_label=='MODERATE' else 'green'
    st.write(f'Signal: :{stress_color}[**{stress_label}**]')
    st.write(f'Predicted spread: **{predicted_spread_pct:.2f}%**')
    st.write(f'Historical mean: **{hist_mean:.2f}%**')
    st.write(f'VIX: **{df["VIXCLS"].dropna().iloc[-1]:.1f}**')
    st.write(f'DXY: **{df["DTWEXBGS"].dropna().iloc[-1]:.1f}**')
    st.caption(f'As of {latest_date.date()}')

with col_b:
    st.markdown(f'**FX Oracle**')
    regime_color = {'Stable':'green','Trending':'orange','Volatile Breakout':'red','Insufficient History':'gray'}.get(fx_regime,'gray')
    st.write(f'Corridor: **{corridor}**')
    st.write(f'FX Pair: **{fx_pair_name}**')
    st.write(f'Spot: **{fx_spot:.4f}**')
    st.write(f'21D Vol: **{fx_vol:.1f}%**')
    st.write(f'Regime: :{regime_color}[**{fx_regime}**]')
    st.write(f'Hedge cost: **{fx_hedge_bps:.0f} bps**')
    st.caption('Lorentzian KNN, k=21, 252-day rolling window')

with col_c:
    st.markdown(f'**Commodity**')
    st.write(f'Selected: **{commodity}**')
    st.write(f'3Y annualised vol: **{comm_vol:.1f}%**')
    st.write(f'Vol-based adjustment: **{comm_bps} bps**')
    st.divider()
    st.markdown('**Deal Summary**')
    st.write(f'Invoice: **${invoice_value:,.0f}**')
    st.write(f'Tenor: **{tenor_days} days**')
    st.write(f'Finance cost: **${finance_cost_usd:,.0f}**')
    st.caption('Source: IMF Global Commodity Price series via FRED')

st.divider()
st.caption(f'FRED | IMF | RBI  |  Model trained 2006-2019, tested 2019-2025  |  MAE 0.62%  R2 0.66  |  As of {latest_date.date()}')