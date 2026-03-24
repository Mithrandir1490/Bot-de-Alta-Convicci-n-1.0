import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN DE INSTITUCIONAL ---
CAPITAL_TOTAL = 5483.14
EFECTIVO_INICIAL = 737.63  # Lo que tienes hoy en GBM
Z_CONFIDENCIA = 1.70       # Filtro de alta calidad
TICKERS = [
    "NVDA","MU","META","MSFT","GOOGL","AMZN","AAPL","ASML","TSM","AVGO","PLTR","PANW","VRT","AMD","NFLX","CRM","ADBE","ORCL","CSCO",
    "JPM","BAC","GS","MS","V","MA","PYPL","AXP","BLK","VST","CEG","XOM","CVX","CCJ","SMR","SLB","MPC","PSX","LLY","NVO","UNH",
    "VRTX","MRNA","PFE","ABBV","JNJ","COST","WMT","TGT","SHOP","MELI","BKNG","SBUX","KO","GEV","GE","LMT","RTX","BA","CAT","DE",
    "AVAV","GOLD","NEM","FCX","FTNT","OKTA","S","NET","ZS","CRWD","TSLA","HOOD","COIN","MSTR"
]

st.set_page_config(page_title="Bot Alta Convicción", layout="wide")

# --- LÓGICA DE CÁLCULO ---
def get_signals():
    # Descarga vectorizada rápida
    data = yf.download(TICKERS, period="2y", interval="1d", group_by='column', auto_adjust=True)
    prices = data['Close']
    
    results = []
    for t in TICKERS:
        try:
            series = prices[t].dropna()
            ret = series.pct_change()
            # Laplace + Z-Score
            up_next = (ret.shift(-1) > 0).astype(int).iloc[:-1]
            p_win = up_next.mean()
            p_final = (p_win * len(up_next) + 2) / (len(up_next) + 4)
            
            p_hist = up_next.rolling(60).mean().dropna()
            z_score = (p_final - p_hist.mean()) / p_hist.std()
            
            # Volatilidad para tamaño de posición
            vol = ret.tail(20).std() * np.sqrt(252)
            
            results.append({
                "Ticker": t,
                "Z-Score": z_score,
                "Prob": p_final,
                "Vol": vol,
                "Precio": series.iloc[-1]
            })
        except: continue
    return pd.DataFrame(results)

# --- INTERFAZ ---
st.title("🤖 Bot de Trading: Alta Convicción")
st.subheader(f"Capital Total: ${CAPITAL_TOTAL} | Efectivo Disponible: ${EFECTIVO_INICIAL}")

if st.button("🔍 Escanear Mercado Hoy"):
    df = get_signals()
    
    # Reglas de Decisión
    def classify(row):
        if row['Z-Score'] > Z_CONFIDENCIA: return "🔥 COMPRA FUERTE"
        if row['Prob'] > 0.60: return "✅ COMPRA"
        if row['Prob'] < 0.40: return "❌ VENTA"
        return "➖ HOLD"

    df['Recomendación'] = df.apply(classify, axis=1)
    
    # Tamaño de posición ajustado por volatilidad
    # Queremos que cada trade arriesgue una cantidad similar de dólares
    df['Inversión $'] = (250 / (df['Vol'] * 5)).clip(75, 350)
    
    # --- FILTRO Y PRIORIZACIÓN ---
    buys = df[df['Recomendación'].str.contains("COMPRA")].sort_values("Z-Score", ascending=False)
    
    if not buys.empty:
        st.success(f"Se encontraron {len(buys)} oportunidades.")
        
        # Gestión de Efectivo (El Semáforo)
        buys['Acumulado $'] = buys['Inversión $'].cumsum()
        buys['Estatus Efectivo'] = np.where(buys['Acumulado $'] <= EFECTIVO_INICIAL, "🟢 ALCANZA", "🔴 SIN FONDOS")
        
        # Formato de tabla
        st.dataframe(buys[['Ticker', 'Recomendación', 'Z-Score', 'Inversión $', 'Estatus Efectivo']].style.applymap(
            lambda x: 'color: green' if x == "🟢 ALCANZA" else ('color: red' if x == "🔴 SIN FONDOS" else ''),
            subset=['Estatus Efectivo']
        ), use_container_width=True)
    else:
        st.info("Mercado en calma. No hay señales de alta convicción hoy.")

st.sidebar.markdown("""
### Reglas de Salida (Bot 1.0):
1. **Stop Loss:** Si la acción cae **-5%** desde tu compra, ¡vende!
2. **Take Profit:** Si sube **+8%**, asegura ganancias.
3. **Tiempo:** Si después de **10 días** no ha pasado nada, cierra la posición.
""")
