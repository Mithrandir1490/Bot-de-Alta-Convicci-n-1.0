import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DEL BOT (PARÁMETROS PRO)
# ==========================================
CAPITAL_TOTAL = 5483.14
EFECTIVO_ACTUAL = 737.63  # Tu saldo actual en GBM Trading US
Z_UMBRAL = 1.65           # Confianza estadística (90%)

# Universo de 100+ Tickers (Tech, Energía, Salud, Consumo, Metales)
TICKERS = [
    "NVDA","MU","META","MSFT","GOOGL","AMZN","AAPL","ASML","TSM","AVGO","PLTR","PANW","VRT","AMD","NFLX","CRM","ADBE","ORCL","CSCO",
    "JPM","BAC","GS","MS","V","MA","PYPL","AXP","BLK","VST","CEG","XOM","CVX","CCJ","SMR","SLB","MPC","PSX","LLY","NVO","UNH",
    "VRTX","MRNA","PFE","ABBV","JNJ","COST","WMT","TGT","SHOP","MELI","BKNG","SBUX","KO","GEV","GE","LMT","RTX","BA","CAT","DE",
    "AVAV","GOLD","NEM","FCX","FTNT","OKTA","S","NET","ZS","CRWD","TSLA","HOOD","COIN","MSTR","DDOG","SNOW","AMAT","KLAC","LRCX"
]

# Configuración de la página
st.set_page_config(page_title="Bot Alta Convicción v1.0", layout="wide")

# ==========================================
# FUNCIONES MATEMÁTICAS
# ==========================================
@st.cache_data(ttl=3600) # Guarda los datos por 1 hora para no banear la IP
def descargar_datos(lista_tickers):
    data = yf.download(lista_tickers, period="2y", interval="1d", group_by='column', auto_adjust=True)
    return data['Close']

def procesar_senales(precios):
    resultados = []
    for t in TICKERS:
        try:
            serie = precios[t].dropna()
            if len(serie) < 100: continue
            
            # Retornos y Probabilidad Laplace
            ret = serie.pct_change()
            exitos_hist = (ret.shift(-1) > 0).astype(int).iloc[:-1]
            p_win = exitos_hist.mean()
            p_laplace = (p_win * len(exitos_hist) + 2) / (len(exitos_hist) + 4)
            
            # Z-Score de la Probabilidad (Anomalía Estadística)
            p_movil = exitos_hist.rolling(60).mean().dropna()
            z_score = (p_laplace - p_movil.mean()) / p_movil.std()
            
            # Volatilidad Anualizada (para tamaño de posición)
            vol = ret.tail(20).std() * np.sqrt(252)
            
            resultados.append({
                "Ticker": t,
                "Precio": serie.iloc[-1],
                "Z-Score": z_score,
                "Prob": p_laplace,
                "Volatilidad": vol
            })
        except:
            continue
    return pd.DataFrame(resultados)

# ==========================================
# INTERFAZ DE USUARIO (UI)
# ==========================================
st.title("🤖 Bot de Alta Convicción v1.0")
st.markdown(f"**Capital de Trabajo:** ${CAPITAL_TOTAL} USD | **Efectivo en GBM:** ${EFECTIVO_ACTUAL} USD")

if st.button("🚀 Escanear Oportunidades"):
    with st.spinner("Analizando 100+ acciones..."):
        df_precios = descargar_datos(TICKERS)
        df_final = procesar_senales(df_precios)
        
        # Regla de Clasificación
        def definir_recomendacion(row):
            if row['Z-Score'] > Z_UMBRAL: return "🔥 COMPRA FUERTE"
            if row['Prob'] > 0.60: return "✅ COMPRA"
            if row['Prob'] < 0.40: return "❌ VENTA"
            return "➖ HOLD"
        
        df_final['Señal'] = df_final.apply(definir_recomendacion, axis=1)
        
        # Cálculo de Inversión Sugerida (Ajustada por Volatilidad)
        df_final['Inversión $'] = (200 / (df_final['Volatilidad'] * 5)).clip(75, 300)
        
        # Filtrar solo compras y ordenar por el mejor Z-Score
        compras = df_final[df_final['Señal'].str.contains("COMPRA")].sort_values("Z-Score", ascending=False)
        
        if not compras.empty:
            # Semáforo de Efectivo
            compras['Acumulado $'] = compras['Inversión $'].cumsum()
            compras['¿Alcanza?'] = np.where(compras['Acumulado $'] <= EFECTIVO_ACTUAL, "🟢 SÍ", "🔴 NO")
            
            st.success(f"Análisis completado. Se detectaron {len(compras)} señales.")
            
            # Mostrar Tabla Principal
            columnas_ver = ['Ticker', 'Señal', 'Z-Score', 'Prob', 'Inversión $', '¿Alcanza?']
            st.dataframe(
                compras[columnas_ver].style.format({"Z-Score": "{:.2f}", "Prob": "{:.2%}", "Inversión $": "${:.2f}"})
                .applymap(lambda x: 'color: green' if x == "🟢 SÍ" else ('color: red' if x == "🔴 NO" else ''), subset=['¿Alcanza?']),
                use_container_width=True
            )
        else:
            st.info("No hay señales de alta convicción en este momento. El mercado está en equilibrio.")

# Sidebar con recordatorios tácticos
st.sidebar.header("Reglas de Salida")
st.sidebar.info("""
1. **Stop Loss:** -5% o -7% (según volatilidad).
2. **Take Profit:** +10% o señal de VENTA del bot.
3. **Tiempo:** Máximo 10 días en cartera.
""")

st.sidebar.write("---")
st.sidebar.write(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
