import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import norm  # Nueva importación para el percentil
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

st.set_page_config(page_title="Bot Alta Convicción v2.2", layout="wide")

# ==========================================
# MOTOR DE CÁLCULO (HORIZONTE 5D + PERCENTILES)
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
            
            # Probabilidad Laplace a 5 días
            ret_5d = serie.shift(-HORIZONTE) > serie
            exitos = ret_5d.dropna().astype(int)
            p_laplace = (exitos.mean() * len(exitos) + 2) / (len(exitos) + 4)
            
            # Z-Score
            p_movil = exitos.rolling(60).mean().dropna()
            z_score = (p_laplace - p_movil.mean()) / p_movil.std()
            
            # --- NUEVA MÉTRICA: Percentil del Z-Score ---
            # Esto te da la probabilidad acumulada P(Z < z)
            z_percentil = norm.cdf(z_score)
            
            # Volatilidad
            vol = serie.pct_change().tail(20).std() * np.sqrt(252)
            
            resultados.append({
                "Ticker": t, 
                "Precio": serie.iloc[-1], 
                "Z-Score": z_score, 
                "Z-Prob (%)": z_percentil, # Para tu Excel
                "Prob 5D": p_laplace, 
                "Vol": vol
            })
        except: continue
    return pd.DataFrame(resultados)

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
st.sidebar.header("⚙️ Configuración v2.2")
efectivo_real = st.sidebar.number_input("Efectivo disponible ($)", value=737.63)
z_umbral = st.sidebar.slider("Umbral de Convicción", 1.0, 2.5, 1.65)

st.title("🤖 Bot de Alta Convicción v2.2")
st.markdown("**Análisis:** Horizonte 5-Días | **Métrica:** Probabilidad Gaussiana (Z-Prob)")

if st.button("🚀 Escanear y Generar Datos"):
    with st.spinner("Calculando percentiles y distribuciones..."):
        df_precios = descargar_datos(TICKERS)
        df_final = procesar_senales_5d(df_precios, TICKERS)
        
        df_final['Señal'] = np.where(df_final['Z-Score'] > z_umbral, "🔥 COMPRA FUERTE", 
                            np.where(df_final['Prob 5D'] > 0.60, "✅ COMPRA", 
                            np.where(df_final['Prob 5D'] < 0.40, "❌ VENTA", "➖ HOLD")))
        
        # PANEL DE DIAGNÓSTICO CON Z-PROB
        st.subheader("🕵️ Panel de Diagnóstico (Registro de Percentiles)")
        st.info("La columna 'Z-Prob (%)' indica qué tan inusual es el movimiento hoy (Percentil).")
        
        top_diagnostico = df_final.sort_values("Z-Score", ascending=False).head(10)
        st.dataframe(
            top_diagnostico[['Ticker', 'Señal', 'Z-Score', 'Z-Prob (%)', 'Prob 5D', 'Precio']].style.format({
                "Z-Score": "{:.2f}", 
                "Z-Prob (%)": "{:.2%}", # Formato porcentaje para Excel
                "Prob 5D": "{:.2%}", 
                "Precio": "${:.2f}"
            }), use_container_width=True
        )
        
        # ÓRDENES CON PONDERACIÓN
        compras = df_final[df_final['Señal'].str.contains("COMPRA")].copy()
        if not compras.empty:
            st.divider()
            st.subheader("💰 Órdenes con Freno de Seguridad")
            
            def calcular_multiplicador(z):
                if z >= 1.65: return 1.0
                if z >= 1.0: return 0.60
                return 0.25

            compras['Multiplicador'] = compras['Z-Score'].apply(calcular_multiplicador)
            compras['Inversa_Vol'] = 1 / compras['Vol']
            base_inv = (compras['Inversa_Vol'] / compras['Inversa_Vol'].sum()) * efectivo_real
            compras['Inversión $'] = base_inv * compras['Multiplicador']
            compras['Acciones (Qty)'] = (compras['Inversión $'] / compras['Precio']).apply(np.floor)
            
            st.dataframe(
                compras[['Ticker', 'Señal', 'Z-Score', 'Z-Prob (%)', 'Inversión $', 'Acciones (Qty)', 'Precio']]
                .sort_values("Z-Score", ascending=False)
                .style.format({
                    "Z-Score": "{:.2f}", 
                    "Z-Prob (%)": "{:.2%}",
                    "Inversión $": "${:.2f}", 
                    "Acciones (Qty)": "{:.0f}", 
                    "Precio": "${:.2f}"
                }), use_container_width=True
            )
            
            total_inv = compras['Inversión $'].sum()
            st.success(f"Inversión total sugerida: ${total_inv:.2f}")
        else:
            st.warning("Mercado sin anomalías detectadas.")

st.markdown("---")
st.caption("v2.2 - Registro de Percentiles para Backtesting Actuarial Activo.")
