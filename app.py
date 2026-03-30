import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import norm  # Para el cálculo del percentil
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import io

# ==========================================
# CONFIGURACIÓN Y UNIVERSO (Actualizado)
# ==========================================
# Tickers seleccionados para Alta Convicción (Líderes de Alpha y Disruptores)
TICKERS = [
    # Semiconductores e IA (Los Ganadores)
    "NVDA", "TSM", "AVGO", "ARM", "ASML", "MU", "AMAT", "KLAC", "LRCX", "AMD", "MRVL", "VRT", "SMCI",
    # Software y Cloud
    "MSFT", "GOOGL", "META", "AMZN", "PLTR", "CRM", "ADBE", "ORCL", "NOW", "SNOW", "NET", "DDOG", "CRWD", "PANW", "ZS",
    # Energía Nuclear e Infraestructura
    "GEV", "VST", "CEG", "CCJ", "SMR", "OKLO", "LEU", "BWXT", "NXE",
    # Fintech y Crecimiento Latam
    "MELI", "NU", "SHOP", "SQ", "PYPL", "HOOD", "COIN", "MSTR",
    # Salud y BioTech (GLP-1 y otros)
    "LLY", "NVO", "VKTX", "UNH", "ABBV", "MRNA", "HIMS",
    # Defensa y Aeroespacial
    "AVAV", "RKLB", "LMT", "RTX", "NOC", "LMT",
    # Gigantes Estructurales (Alpha por Escala)
    "NFLX", "AAPL", "COST", "WMT", "JPM", "V", "MA", "TSLA", "CAT", "DE"
]

st.set_page_config(page_title="Bot Alta Convicción v2.2", layout="wide")

# ==========================================
# MOTOR DE CÁLCULO (HORIZONTE 5D + PERCENTILES)
# ==========================================
@st.cache_data(ttl=3600)
def descargar_datos(lista_tickers):
    # Descarga masiva de datos para optimizar tiempo
    data = yf.download(lista_tickers, period="2y", interval="1d", group_by='column', auto_adjust=True)
    return data['Close']

def procesar_senales_5d(precios, lista_tickers):
    resultados = []
    HORIZONTE = 5
    for t in lista_tickers:
        try:
            serie = precios[t].dropna()
            if len(serie) < 100: continue
            
            # Probabilidad Laplace a 5 días (¿Estará más alto en 5 días?)
            ret_5d = serie.shift(-HORIZONTE) > serie
            exitos = ret_5d.dropna().astype(int)
            p_laplace = (exitos.mean() * len(exitos) + 2) / (len(exitos) + 4)
            
            # Z-Score (Detección de anomalías en la probabilidad)
            p_movil = exitos.rolling(60).mean().dropna()
            z_score = (p_laplace - p_movil.mean()) / p_movil.std()
            
            # --- MÉTRICA: Percentil del Z-Score (Probabilidad Gaussiana) ---
            z_percentil = norm.cdf(z_score)
            
            # Volatilidad Anualizada (Ventana 20 días)
            vol = serie.pct_change().tail(20).std() * np.sqrt(252)
            
            resultados.append({
                "Ticker": t, 
                "Precio": serie.iloc[-1], 
                "Z-Score": z_score, 
                "Z-Prob (%)": z_percentil,
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
z_umbral = st.sidebar.slider("Umbral de Convicción (Z-Score)", 1.0, 2.5, 1.65)

st.title("🤖 Bot de Alta Convicción v2.2")
st.markdown("**Estrategia:** Identificación de anomalías estadísticas positivas en horizonte de 5 días.")

if st.button("🚀 Escanear Universo Alpha"):
    with st.spinner("Calculando percentiles y distribuciones de probabilidad..."):
        df_precios = descargar_datos(TICKERS)
        df_final = procesar_senales_5d(df_precios, TICKERS)
        
        # Lógica de categorización de señales
        df_final['Señal'] = np.where(df_final['Z-Score'] > z_umbral, "🔥 COMPRA FUERTE", 
                            np.where(df_final['Prob 5D'] > 0.60, "✅ COMPRA", 
                            np.where(df_final['Prob 5D'] < 0.40, "❌ VENTA", "➖ HOLD")))
        
        # --- PANEL DE DIAGNÓSTICO ---
        st.subheader("🕵️ Panel de Diagnóstico (Registro de Percentiles)")
        st.info("La columna 'Z-Prob (%)' representa la probabilidad acumulada. Un valor cercano al 99% indica un movimiento extremadamente inusual y potente.")
        
        top_diagnostico = df_final.sort_values("Z-Score", ascending=False).head(15)
        st.dataframe(
            top_diagnostico[['Ticker', 'Señal', 'Z-Score', 'Z-Prob (%)', 'Prob 5D', 'Precio']].style.format({
                "Z-Score": "{:.2f}", 
                "Z-Prob (%)": "{:.2%}",
                "Prob 5D": "{:.2%}", 
                "Precio": "${:.2f}"
            }), use_container_width=True
        )
        
        # --- ÓRDENES CON PONDERACIÓN POR VOLATILIDAD ---
        compras = df_final[df_final['Señal'].str.contains("COMPRA")].copy()
        if not compras.empty:
            st.divider()
            st.subheader("💰 Distribución Sugerida de Capital")
            
            def calcular_multiplicador(z):
                if z >= 1.65: return 1.0     # Convicción Máxima
                if z >= 1.0: return 0.60      # Convicción Media
                return 0.25                   # Convicción Baja

            compras['Multiplicador'] = compras['Z-Score'].apply(calcular_multiplicador)
            compras['Inversa_Vol'] = 1 / compras['Vol']
            
            # Ponderación: Más capital a lo que tiene menos volatilidad y más Z-Score
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
            st.success(f"Inversión total sugerida para hoy: ${total_inv:.2f}")
        else:
            st.warning("No se detectaron activos con suficiente convicción estadística en este momento.")

st.markdown("---")
st.caption("v2.2 - Este modelo prioriza activos que se desvían positivamente de su comportamiento histórico reciente.")
