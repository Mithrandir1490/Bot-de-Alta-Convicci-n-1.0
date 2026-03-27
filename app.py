import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import io

# ==========================================
# CONFIGURACIÓN Y UNIVERSO
# ==========================================
TICKERS = [
    "NVDA","MU","META","MSFT","GOOGL","AMZN","AAPL","ASML","TSM","AVGO","PLTR","PANW","VRT","AMD","NFLX","CRM","ADBE","ORCL","CSCO",
    "JPM","BAC","GS","MS","V","MA","PYPL","AXP","BLK","VST","CEG","XOM","CVX","CCJ","SMR","SLB","MPC","PSX","LLY","NVO","UNH",
    "VRTX","MRNA","PFE","ABBV","JNJ","COST","WMT","TGT","SHOP","MELI","BKNG","SBUX","KO","GEV","GE","LMT","RTX","BA","CAT","DE",
    "AVAV","GOLD","NEM","FCX","FTNT","OKTA","S","NET","ZS","CRWD","TSLA","HOOD","COIN","MSTR","DDOG","SNOW","AMAT","KLAC","LRCX"
]

st.set_page_config(page_title="Bot Alta Convicción v2.1", layout="wide")

# ==========================================
# MOTOR DE DATOS (HORIZONTE 5D)
# ==========================================
@st.cache_data(ttl=3600)
def descargar_datos(lista_tickers):
    data = yf.download(lista_tickers, period="2y", interval="1d", group_by='column', auto_adjust=True)
    return data['Close']

def procesar_senales_5d(precios, lista_tickers):
    resultados = []
    HORIZONTE = 5
    for t in lista_tickers:
        try:
            serie = precios[t].dropna()
            if len(serie) < 100: continue
            ret_5d = serie.shift(-HORIZONTE) > serie
            exitos = ret_5d.dropna().astype(int)
            p_laplace = (exitos.mean() * len(exitos) + 2) / (len(exitos) + 4)
            p_movil = exitos.rolling(60).mean().dropna()
            z_score = (p_laplace - p_movil.mean()) / p_movil.std()
            vol = serie.pct_change().tail(20).std() * np.sqrt(252)
            resultados.append({
                "Ticker": t, "Precio": serie.iloc[-1], "Z-Score": z_score, "Prob 5D": p_laplace, "Vol": vol
            })
        except: continue
    return pd.DataFrame(resultados)

# ==========================================
# INTERFAZ Y LÓGICA DE INVERSIÓN PROTEGIDA
# ==========================================
st.sidebar.header("⚙️ Configuración v2.1")
efectivo_real = st.sidebar.number_input("Efectivo disponible ($)", value=737.63)
z_umbral = st.sidebar.slider("Umbral de Convicción", 1.0, 2.5, 1.65)

st.title("🤖 Bot de Alta Convicción v2.1")
st.markdown("**Modo:** Convicción Pesada (5-Días) | **Protección de Capital:** Activa")

if st.button("🚀 Escanear y Calcular Ejecución"):
    with st.spinner("Escaneando anomalías..."):
        df_precios = descargar_datos(TICKERS)
        df_final = procesar_senales_5d(df_precios, TICKERS)
        
        # Clasificación
        df_final['Señal'] = np.where(df_final['Z-Score'] > z_umbral, "🔥 COMPRA FUERTE", 
                            np.where(df_final['Prob 5D'] > 0.60, "✅ COMPRA", 
                            np.where(df_final['Prob 5D'] < 0.40, "❌ VENTA", "➖ HOLD")))
        
        # FILTRO DE COMPRAS
        compras = df_final[df_final['Señal'].str.contains("COMPRA")].copy()
        
        if not compras.empty:
            # --- NUEVA LÓGICA DE PROTECCIÓN ---
            def calcular_multiplicador(z):
                if z >= 1.65: return 1.0    # 100% de la apuesta
                if z >= 1.0: return 0.60    # 60% de la apuesta
                return 0.25                 # 25% de la apuesta (Señales débiles como GEV)

            compras['Multiplicador'] = compras['Z-Score'].apply(calcular_multiplicador)
            
            # Reparto inicial por volatilidad
            compras['Inversa_Vol'] = 1 / compras['Vol']
            base_inv = (compras['Inversa_Vol'] / compras['Inversa_Vol'].sum()) * efectivo_real
            
            # Aplicar el freno de convicción
            compras['Inversión $'] = base_inv * compras['Multiplicador']
            compras['Acciones (Qty)'] = (compras['Inversión $'] / compras['Precio']).apply(np.floor)
            
            st.success(f"Se detectaron {len(compras)} señales con ponderación de riesgo.")
            
            # Mostrar Tabla de Ejecución
            st.dataframe(
                compras[['Ticker', 'Señal', 'Z-Score', 'Inversión $', 'Acciones (Qty)', 'Precio']]
                .sort_values("Z-Score", ascending=False)
                .style.format({"Z-Score": "{:.2f}", "Inversión $": "${:.2f}", "Acciones (Qty)": "{:.0f}", "Precio": "${:.2f}"}),
                use_container_width=True
            )
            
            # Resumen de efectivo
            total_inv = compras['Inversión $'].sum()
            st.info(f"💰 **Resumen de Operación:** Invertirás **${total_inv:.2f}** de tus **${efectivo_real:.2f}**. El resto se queda en reserva por baja convicción.")
        else:
            st.warning("No hay señales hoy.")

st.markdown("---")
st.caption("v2.1 - Ahora con protección automática de capital ante señales débiles.")
