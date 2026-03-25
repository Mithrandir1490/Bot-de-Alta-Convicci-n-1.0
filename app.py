import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DEL UNIVERSO
# ==========================================
TICKERS = [
    "NVDA","MU","META","MSFT","GOOGL","AMZN","AAPL","ASML","TSM","AVGO","PLTR","PANW","VRT","AMD","NFLX","CRM","ADBE","ORCL","CSCO",
    "JPM","BAC","GS","MS","V","MA","PYPL","AXP","BLK","VST","CEG","XOM","CVX","CCJ","SMR","SLB","MPC","PSX","LLY","NVO","UNH",
    "VRTX","MRNA","PFE","ABBV","JNJ","COST","WMT","TGT","SHOP","MELI","BKNG","SBUX","KO","GEV","GE","LMT","RTX","BA","CAT","DE",
    "AVAV","GOLD","NEM","FCX","FTNT","OKTA","S","NET","ZS","CRWD","TSLA","HOOD","COIN","MSTR","DDOG","SNOW","AMAT","KLAC","LRCX"
]

st.set_page_config(page_title="Bot Alta Convicción v1.1", layout="wide")

# ==========================================
# PANEL DE CONTROL (SIDEBAR)
# ==========================================
st.sidebar.header("⚙️ Configuración de Capital")
efectivo_real = st.sidebar.number_input("Efectivo disponible hoy ($)", min_value=10.0, value=737.63, step=10.0)
z_umbral = st.sidebar.slider("Umbral de Convicción (Z-Score)", 1.0, 2.5, 1.65)

st.sidebar.markdown("---")
st.sidebar.header("Reglas de Salida")
st.sidebar.info("""
1. **Stop Loss:** -5%
2. **Take Profit:** +8%
3. **Tiempo:** 10 días máx.
""")

# ==========================================
# MOTOR DE CÁLCULO
# ==========================================
@st.cache_data(ttl=3600)
def descargar_datos(lista_tickers):
    data = yf.download(lista_tickers, period="2y", interval="1d", group_by='column', auto_adjust=True)
    return data['Close']

def procesar_senales(precios):
    resultados = []
    for t in TICKERS:
        try:
            serie = precios[t].dropna()
            if len(serie) < 100: continue
            ret = serie.pct_change()
            exitos_hist = (ret.shift(-1) > 0).astype(int).iloc[:-1]
            p_win = exitos_hist.mean()
            p_laplace = (p_win * len(exitos_hist) + 2) / (len(exitos_hist) + 4)
            p_movil = exitos_hist.rolling(60).mean().dropna()
            z_score = (p_laplace - p_movil.mean()) / p_movil.std()
            vol = ret.tail(20).std() * np.sqrt(252)
            
            resultados.append({
                "Ticker": t, "Precio": serie.iloc[-1], "Z-Score": z_score, "Prob": p_laplace, "Volatilidad": vol
            })
        except: continue
    return pd.DataFrame(resultados)

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================
st.title("🤖 Bot de Alta Convicción v1.1")
st.markdown(f"**Estrategia:** Arbitraje Estadístico | **Distribución:** Risk-Parity Dinámico")

if st.button("🚀 Escanear y Calcular Inversión"):
    with st.spinner("Descargando datos y ajustando pesos de cartera..."):
        df_precios = descargar_datos(TICKERS)
        df_final = procesar_senales(df_precios)
        
        # Clasificación con el Z-Score del Sidebar
        df_final['Señal'] = np.where(df_final['Z-Score'] > z_umbral, "🔥 COMPRA FUERTE", 
                            np.where(df_final['Prob'] > 0.60, "✅ COMPRA", 
                            np.where(df_final['Prob'] < 0.40, "❌ VENTA", "➖ HOLD")))
        
        compras = df_final[df_final['Señal'].str.contains("COMPRA")].copy()
        
        if not compras.empty:
            # --- CÁLCULO DE LA CALCULADORA REAL ---
            # Peso basado en la inversa de la volatilidad (A menos riesgo, más dinero)
            compras['Inversa_Vol'] = 1 / compras['Volatilidad']
            suma_inversas = compras['Inversa_Vol'].sum()
            
            # Aquí ocurre la magia: Usamos el 'efectivo_real' del Sidebar
            compras['Inversión $'] = (compras['Inversa_Vol'] / suma_inversas) * efectivo_real
            
            compras = compras.sort_values("Z-Score", ascending=False)
            
            st.success(f"Se detectaron {len(compras)} señales. Capital de ${efectivo_real} distribuido.")
            
            # Mostrar Tabla con formato profesional
            st.dataframe(
                compras[['Ticker', 'Señal', 'Z-Score', 'Inversión $', 'Precio']].style.format({
                    "Z-Score": "{:.2f}", 
                    "Inversión $": "${:.2f}",
                    "Precio": "${:.2f}"
                }), use_container_width=True
            )
            
            st.info(f"💡 **Instrucción:** Para mantener el riesgo balanceado, compra exactamente las cantidades sugeridas arriba.")
        else:
            st.warning("No se encontraron señales. El capital se mantiene protegido en efectivo.")

st.markdown("---")
st.caption(f"Última corrida: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Universo: {len(TICKERS)} activos.")
