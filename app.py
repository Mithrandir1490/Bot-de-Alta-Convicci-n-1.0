import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import norm

# ==========================================
# CONFIGURACIÓN Y UNIVERSO EXPANDIDO (85 TICKERS)
# ==========================================
UNIVERSO = {
    "Semiconductores/IA": ["NVDA", "TSM", "AVGO", "ARM", "ASML", "MU", "AMD", "SMCI", "LRCX", "AMAT", "KLAC", "MRVL", "QCOM", "TER"],
    "Software/Cloud": ["MSFT", "GOOGL", "META", "AMZN", "PLTR", "CRM", "ADBE", "SNOW", "CRWD", "PANW", "ZS", "WDAY", "SHOP", "DDOG"],
    "Energía e Infraestructura": ["GEV", "VST", "CEG", "CCJ", "SMR", "BWXT", "NEE", "XOM", "CVX", "TPL"],
    "Fintech y Consumo Digital": ["MELI", "NU", "SHOP", "SQ", "PYPL", "HOOD", "COIN", "MSTR", "SE", "DLO", "UBER"],
    "Salud y BioTech": ["LLY", "NVO", "VKTX", "UNH", "ABBV", "HIMS", "VRTX", "REGN", "OSCR"],
    "Hard Assets (Materiales)": ["FCX", "SCCO", "TECK", "GOLD", "MP"],
    "Defensa e Industriales": ["AVAV", "RKLB", "LMT", "RTX", "CAT", "DE", "GE", "ETN", "URI"],
    "Servicios y Gigantes": ["NFLX", "AAPL", "COST", "WMT", "JPM", "V", "MA", "TSLA", "MCO", "SPGI", "ADP"]
}

TICKERS = [t for sublist in UNIVERSO.values() for t in sublist]

st.set_page_config(page_title="Bot Alta Convicción v3.0", layout="wide", page_icon="🤖")

# ==========================================
# FUNCIONES TÉCNICAS Y CÁLCULO
# ==========================================
@st.cache_data(ttl=3600)
def descargar_datos_con_benchmark(lista_tickers):
    # Benchmark SPY para medir Fuerza Relativa (Alpha)
    todo = list(set(lista_tickers + ["SPY"]))
    data = yf.download(todo, period="2y", interval="1d", auto_adjust=True)['Close']
    return data

def calcular_rsi(serie, window=14):
    delta = serie.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def procesar_senales_v3(precios):
    resultados = []
    spy = precios["SPY"]
    
    for sector, lista in UNIVERSO.items():
        for t in lista:
            try:
                serie = precios[t].dropna()
                if len(serie) < 100: continue
                
                # 1. Probabilidad Laplace (Horizonte 5D)
                ret_5d = serie.shift(-5) > serie
                exitos = ret_5d.dropna().astype(int)
                p_laplace = (exitos.mean() * len(exitos) + 2) / (len(exitos) + 4)
                
                # 2. Z-Score de Probabilidad
                p_movil = exitos.rolling(60).mean().dropna()
                z_score = (p_laplace - p_movil.mean()) / p_movil.std()
                
                # 3. Fuerza Relativa (vs SPY) - Ventana 3 meses (63 días)
                ret_ticker = serie.pct_change(63).iloc[-1]
                ret_spy = spy.pct_change(63).iloc[-1]
                fuerza_relativa = ret_ticker - ret_spy
                
                # 4. RSI Actual
                rsi_val = calcular_rsi(serie).iloc[-1]
                
                # --- SCORING MULTI-FACTORIAL (0-100) ---
                # 50% Estadística | 30% Fuerza Relativa | 20% Momentum Saludable
                score = (norm.cdf(z_score) * 50) + (max(0, fuerza_relativa) * 100)
                if 40 < rsi_val < 70: score += 20 
                
                resultados.append({
                    "Ticker": t,
                    "Sector": sector,
                    "Precio": serie.iloc[-1],
                    "Score": score,
                    "Z-Score": z_score,
                    "RSI": rsi_val,
                    "Alpha (vs SPY)": fuerza_relativa
                })
            except: continue
            
    df = pd.DataFrame(resultados)
    
    # DIVERSIFICACIÓN FORZADA: Máximo 2 mejores por sector
    df = df.sort_values("Score", ascending=False)
    df_diverse = df.groupby("Sector").head(2) 
    
    return df_diverse

# ==========================================
# INTERFAZ DE USUARIO (UX)
# ==========================================
st.title("🤖 Bot de Alta Convicción v3.0")
st.markdown("### Estrategia: Scoring de Fuerza Relativa + Probabilidad de Laplace")

with st.sidebar:
    st.header("⚙️ Configuración")
    efectivo = st.number_input("Capital disponible ($)", value=1000.0)
    st.divider()
    st.info("Este bot selecciona automáticamente los 2 activos más fuertes de cada sector para garantizar una cartera balanceada.")

if st.button("🚀 Iniciar Escaneo Sectorial"):
    with st.spinner("Descargando precios y calculando Alphas..."):
        df_precios = descargar_datos_con_benchmark(TICKERS)
        df_final = procesar_senales_v3(df_precios)
        
        # Lógica de Etiquetas de Acción
        def asignar_accion(row):
            if row['Z-Score'] > 1.8 and row['RSI'] < 60:
                return "🆕 NUEVA ENTRADA"
            if row['Score'] > 75 and row['RSI'] >= 72:
                return "✅ MANTENER (No comprar más)"
            if row['Score'] > 65 and row['RSI'] < 45:
                return "➕ REFORZAR (Dip)"
            return "➖ HOLD"

        df_final['Acción Sugerida'] = df_final.apply(asignar_accion, axis=1)
        
        # --- TABLA PRINCIPAL ---
        st.subheader("🎯 Selección de Élite por Sector")
        st.dataframe(
            df_final[['Ticker', 'Sector', 'Acción Sugerida', 'Score', 'Precio', 'RSI', 'Alpha (vs SPY)']]
            .sort_values("Score", ascending=False)
            .style.background_gradient(subset=['Score'], cmap='RdYlGn')
            .format({
                "Score": "{:.1f}", 
                "Precio": "${:.2f}", 
                "RSI": "{:.1f}",
                "Alpha (vs SPY)": "{:.2%}"
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # --- GESTIÓN DE CAPITAL ---
        st.divider()
        st.subheader("💰 Órdenes de Ejecución")
        
        compras = df_final[df_final['Acción Sugerida'].isin(["🆕 NUEVA ENTRADA", "➕ REFORZAR"])].copy()
        
        if not compras.empty:
            compras['Peso'] = compras['Score'] / compras['Score'].sum()
            compras['Monto Invertir'] = compras['Peso'] * efectivo
            compras['Acciones (Qty)'] = (compras['Monto Invertir'] / compras['Precio']).apply(np.floor)
            
            st.success("Distribución sugerida para capital fresco:")
            st.table(compras[['Ticker', 'Acción Sugerida', 'Monto Invertir', 'Acciones (Qty)', 'Precio']]
                     .style.format({"Monto Invertir": "${:.2f}", "Precio": "${:.2f}", "Acciones (Qty)": "{:.0f}"}))
        else:
            st.warning("Hoy no hay 'Nuevas Entradas'. Si tienes posiciones en 'Mantener', deja correr la tendencia.")

st.markdown("---")
st.caption("v3.0 - Motor de Diversificación Sectorial con Capping. Protege tu capital evitando la sobre-concentración.")
