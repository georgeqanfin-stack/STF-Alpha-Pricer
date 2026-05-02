# STF-Alpha-Pricer

**Commodity Trade Finance Discount Rate Engine**  
Built by **George P Babu**  
🔗 [Live App](https://stf-alpha-pricer.streamlit.app/)

---

## Overview

STF-Alpha-Pricer is a quantitative pricing engine for commodity trade finance facilities. Given a deal — invoice value, tenor, commodity, and trade corridor — it computes a fully decomposed, data-driven all-in discount rate using three independent models running on live macro and FX data.

No hardcoded spreads. Every basis point is earned from data.

---

## Pricing Equation

```
Final Rate = Base Rate (3M T-Bill)
           + Macro Risk Premium    [XGBoost — trained on 20 years of macro data]
           + FX Hedge Cost         [Lorentzian KNN — regime classifier]
           + Commodity Adjustment  [IMF 3Y annualised price volatility]
           + Tenor Adjustment
           + Profit Margin
```

---

## Architecture

### Phase 1 — Data Pipeline
- **FRED macro series**: 3M T-Bill (DGS3MO), Moody's BAA yield (DBAA), DXY dollar index, VIX, M2, Fed Funds, TED spread — 5,600+ daily rows from 2005
- **FRED FX series**: USD/INR, USD/CNY, USD/ZAR, USD/MXN — 5,500+ daily rows from 2005
- **IMF commodity prices** via FRED: Copper, Iron Ore, Brent Crude, Aluminium, Zinc — monthly from 1992
- All data cached locally as CSV. No live API dependency at runtime.

### Phase 2 — Macro Risk Engine (XGBoost)
The model predicts the credit stress spread 21 trading days ahead.

- **Target variable**: Moody's BAA corporate bond yield minus 3-month T-Bill yield — the classic investment-grade credit risk proxy
- **11 engineered features**: lagged spreads (5d, 21d, 63d), rolling spread volatility, DXY momentum (21d, 63d), VIX level and momentum, rate level and momentum, DBAA absolute level
- **Walk-forward validation**: trained on 2006–2019, tested on 2019–2025 — no data leakage
- **Performance**: Test MAE 0.62% | Test R² 0.66
- **Output**: risk premium in basis points added to the base rate

### Phase 3 — FX Oracle (Lorentzian KNN)
Classifies the current FX regime for the deal corridor and prices the hedge cost accordingly.

**Lorentzian distance metric:**
```
D = Σ ln(1 + |xᵢ - yᵢ|)
```
Unlike Euclidean distance, Lorentzian dampens the effect of extreme outliers — critical for EM currency pairs where central bank interventions create artificial spikes that would otherwise distort the regime signal.

- Rolling 252-day normalisation keeps the classifier sensitive to the current regime rather than the full historical distribution
- k=21 nearest neighbours from the trailing 252-day window
- **Regime classification**: Stable → 40 bps | Trending → 80 bps | Volatile Breakout → 160 bps

### Phase 4 — Streamlit Interface
Interactive deal pricer with live waterfall rate breakdown and market context panel.

---

## Trade Corridor to FX Pair Mapping

| Corridor | FX Pair | Rationale |
|---|---|---|
| Asia to Europe | USD/INR | INR proxy for Asian exporter settlement risk |
| Americas to Asia | USD/CNY | China dominant buyer of LatAm copper, iron ore, soy |
| Africa to Asia | USD/ZAR | South Africa dominant African commodity exporter |
| Middle East to Asia | USD/INR | India largest Middle East oil importer |
| Asia to Americas | USD/MXN | MXN proxy for Latin American commodity importer FX risk |

---

## Commodity Adjustment Methodology

Adjustments are derived from IMF Global Commodity Price series, not hardcoded. Each commodity's 3-year annualised return volatility is scaled linearly to a 0–60 bps range.

| Commodity | 3Y Annualised Vol | Adjustment |
|---|---|---|
| Crude Oil | ~31% | 60 bps |
| Iron Ore | ~20% | 21 bps |
| Zinc | ~17% | 10 bps |
| Copper | ~15% | 0 bps |
| Aluminium | ~15% | 0 bps |

---

## Real-World Calibration

Commodity trade finance spreads in practice range from SOFR + 400–600 bps for oil with sovereign counterparties to SOFR + 500–900 bps for metals in Africa corridors. STF-Alpha-Pricer outputs rates consistent with this range under current macro conditions — validated against published trade finance pricing benchmarks.

---

## Motivation

Trafigura's 2024 annual report disclosed a USD 1.1bn loss from concealed overdue debts and manipulated data in its Mongolian petroleum supply business. This project addresses the class of problem that loss represents: systematic, model-driven corridor risk pricing that makes the cost of macro stress and FX volatility explicit and auditable — replacing relationship-based judgement with a transparent, data-grounded framework.

---

## Stack

| Layer | Tools |
|---|---|
| Data | FRED API, IMF Primary Commodity Prices |
| Modelling | XGBoost, scikit-learn, NumPy, pandas |
| Interface | Streamlit, Matplotlib |
| Language | Python 3.11 |

---

## Run Locally

```bash
git clone https://github.com/georgeqanfin-stack/STF-Alpha-Pricer.git
cd STF-Alpha-Pricer
pip install -r requirements.txt
cd app
streamlit run app.py
```

---

## Data Sources

All data is publicly available. No proprietary feeds required.

- [FRED — Federal Reserve Economic Data](https://fred.stlouisfed.org/)
- [IMF Primary Commodity Prices via FRED](https://fred.stlouisfed.org/categories/32217)
- USD/INR: FRED series DEXINUS (RBI/Fed)
- USD/CNY: FRED series DEXCHUS
- USD/ZAR: FRED series DEXSFUS
- USD/MXN: FRED series DEXMXUS

---

## Live Demo

[https://stf-alpha-pricer.streamlit.app/](https://stf-alpha-pricer.streamlit.app/)
