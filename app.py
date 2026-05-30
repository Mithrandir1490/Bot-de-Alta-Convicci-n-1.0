import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.stats import norm

# ==========================================================================
# CONFIGURACIÓN Y UNIVERSO EXPANDIDO DE ÉLITE INSTITUCIONAL (115 TICKERS)
# ==========================================================================
UNIVERSO = {
    "Semiconductores/IA": [
        "NVDA", "TSM", "AVGO", "ARM", "ASML", "MU", "AMD", "SMCI", "LRCX", 
        "AMAT", "KLAC", "MRVL", "QCOM", "TER", "ADI", "NXPI", "TXN"
    ],
    "Software/Cloud/Data": [
        "MSFT", "GOOGL", "META", "AMZN", "PLTR", "CRM", "ADBE", "SNOW", 
        "CRWD", "PANW", "ZS", "DDOG", "NOW", "TEAM", "WDAY", "SHOP", "NET"
    ],
    "Energía e Infraestructura": [
        "GEV", "VST", "CEG", "CCJ", "SMR", "BWXT", "NEE", "XOM", "CVX", 
        "TPL", "NFE", "OKE", "ET", "FANG"
    ],
    "Fintech y Consumo Digital": [
        "MELI", "NU", "SHOP", "SQ", "PYPL", "HOOD", "COIN", "MSTR", "SE", 
        "DLO", "UBER", "BABA", "PDD", "CPNG", "MELI", "AMZN"
    ],
    "Salud y BioTech": [
        "LLY", "NVO", "VKTX", "UNH", "ABBV", "HIMS", "VRTX", "REGN", "OSCR", 
        "GILD", "AMGN", "ISRG", "PFE"
    ],
    "Hard Assets (Materiales)": [
        "FCX", "SCCO", "TECK", "GOLD", "MP", "NEM", "NUE", "AA", "BHP", "RIO"
    ],
    "Defensa e Industriales": [
        "AVAV", "RKLB", "LMT", "RTX", "CAT", "DE", "GE", "ETN", "URI", 
        "GD", "NOC", "TDG", "HON", "WM"
    ],
    "Servicios y Gigantes": [
        "NFLX", "AAPL", "COST", "WMT", "JPM", "V", "MA", "TSLA", "MCO", 
        "SPGI", "ADP", "BAC", "MS", "GS", "BLK"
    ]
}

# Eliminar duplicados manteniendo el mapeo sectorial
TICKERS = list(set([t for sublist in UNIVERSO.values() for t in sublist]))

st.set_page_config(page_title="Bot Alta Convicción v3.1", layout="wide", page_icon="🎯")

# ==========================================================================
# FUNCIONES TÉCNICAS Y MOTOR DE CÓMPUTO
# ==========================================================================
@st.cache_data(ttl=3600)
def descargar_datos_con_benchmark(lista_tickers):
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
                if t not in precios.columns: continue
                serie = precios[t].dropna()
                if len(serie) < 100: continue
                
                # 1. Probabilidad Laplace (Horizonte 5D)
                ret_5d = serie.shift(-5) > serie
                exitos = ret_5d.dropna().astype(int)
                p_laplace = (exitos.mean() * len(exitos) + 2) / (len(exitos) + 4)
                
                # 2. Z-Score de Probabilidad
                p_movil = exitos.rolling(60).mean().dropna()
                z_score = (p_laplace - p_movil.mean()) / p_movil.std()
                
                # 3. Fuerza Relativa (vs SPY) - Ventana 3 meses (63 días hábiles)
                ret_ticker = serie.pct_change(63).iloc[-1]
                ret_spy = spy.pct_change(63).iloc[-1]
                fuerza_relativa = ret_ticker - ret_spy
                
                # 4. RSI Actual
                rsi_val = calcular_rsi(serie).iloc[-1]
                
                # --- SCORING MULTI-FACTORIAL (0-100) ---
                score = (norm.cdf(z_score) * 50) + (max(0, fuerza_relativa) * 100)
                if 40 < rsi_val < 70: score += 20 
                
                resultados.append({
                    "Ticker": t,
                    "Sector": sector,
                    "Precio": float(serie.iloc[-1]),
                    "Score": float(score),
                    "Z-Score": float(z_score),
                    "RSI": float(rsi_val),
                    "Alpha (vs SPY)": float(fuerza_relativa)
                })
            except:
                continue
                
    df = pd.DataFrame(resultados)
    
    # DIVERSIFICACIÓN FORZADA CON CAPPING SECTORIAL: Máximo 2 mejores por sector
    df = df.sort_values("Score", ascending=False)
    df_diverse = df.groupby("Sector").head(2).reset_index(drop=True) 
    return df_diverse

# ==========================================================================
# INTERFAZ DE USUARIO (UX / UI CORPORATIVA)
# ==========================================================================
st.title("🎯 Bot de Alta Convicción v3.1 — Sniper Sectorial Unificado")
st.markdown("### Estrategia de Asignación por Fuerza Relativa Normalizada y Capping Sectorial")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Gestión de Tesorería")
    efectivo = st.number_input("Capital Disponible para Despliegue ($)", value=1000.0, step=100.0)
    st.divider()
    st.info("🔮 Isengard App: Módulo de asignación blindado. Los fondos se concentran exclusivamente en anomalías de entrada, bloqueando sobrecompras.")

if st.button("🚀 Ejecutar Escaneo del Universo Expandido (115 Tickers)"):
    with st.spinner("Procesando matrices estocásticas y vectores Alpha..."):
        df_precios = descargar_datos_con_benchmark(TICKERS)
        df_final = procesar_senales_v3(df_precios)
        
        # Lógica Rigurosa de Etiquetas de Acción
        def asignar_accion(row):
            if row['Z-Score'] > 1.8 and row['RSI'] < 60:
                return "🆕 NUEVA ENTRADA"
            if row['Score'] > 75 and row['RSI'] >= 72:
                return "✅ MANTENER (No comprar más)"
            if row['Score'] > 65 and row['RSI'] < 45:
                return "➕ REFORZAR (Dip)"
            return "局 HOLD"

        df_final['Acción Sugerida'] = df_final.apply(asignar_accion, axis=1)
        
        # --- TABLA EJECUTIVA PRINCIPAL ---
        st.subheader("📊 Selección de Élite Sectorial (Capping Máximo 2 por Vector)")
        
        def style_rows(val):
            if val == "🆕 NUEVA ENTRADA": return "background-color: #f0fff4; color: #1b7f3a; font-weight: bold;"
            if val == "➕ REFORZAR (Dip)": return "background-color: #e6fffa; color: #004d40; font-weight: bold;"
            if "MANTENER" in val: return "background-color: #fff5f5; color: #b00020;"
            return "color: #4a5568;"

        styled_df = (df_final[['Ticker', 'Sector', 'Acción Sugerida', 'Score', 'Precio', 'RSI', 'Alpha (vs SPY)']]
                     .sort_values("Score", ascending=False)
                     .style.background_gradient(subset=['Score'], cmap='YlGn')
                     .map(style_rows, subset=['Acción Sugerida'])
                     .format({
                         "Score": "{:.1f}", 
                         "Precio": "${:.2f}", 
                         "RSI": "{:.1f}",
                         "Alpha (vs SPY)": "{:.2%}"
                     }))
                     
        st.dataframe(styled_df, use_container_width=True, height=500, hide_index=True)
        
        # ==========================================================================
        # 💰 GESTIÓN DE CAPITAL AUTOMATIZADA (MONEY MANAGEMENT BLINDADO)
        # ==========================================================================
        st.divider()
        st.subheader("💰 Órdenes de Ejecución de Tesorería")
        
        # Filtrar únicamente las acciones comerciales que requieren inyección de liquidez
        compras_idx = df_final['Acción Sugerida'].isin(["🆕 NUEVA ENTRADA", "➕ REFORZAR (Dip)"])
        compras = df_final[compras_idx].copy()
        
        if not compras.empty:
            # Distribución proporcional basada únicamente en la fuerza de las señales operativas activas
            compras['Peso'] = compras['Score'] / compras['Score'].sum()
            compras['Monto Invertir'] = compras['Peso'] * efectivo
            compras['Acciones (Qty)'] = (compras['Monto Invertir'] / compras['Precio']).apply(np.floor)
            compras['Porcentaje del Presupuesto'] = compras['Peso'] * 100
            
            st.success("🎯 **DISTRIBUCIÓN DE CAPITAL REFACTORIZADA (SUMA NETA = 100%):** Los fondos han sido desviados exclusivamente a zonas de descuento probabilístico.")
            
            st.table(compras[['Ticker', 'Acción Sugerida', 'Porcentaje del Presupuesto', 'Monto Invertir', 'Acciones (Qty)', 'Precio']]
                     .style.format({
                         "Porcentaje del Presupuesto": "{:.1f}%",
                         "Monto Invertir": "${:.2f}", 
                         "Precio": "${:.2f}", 
                         "Acciones (Qty)": "{:.0f}"
                     }))
        else:
            st.warning("⚠️ **ALERTA DE INACCIÓN:** El mercado cotiza extendido o en rango neutral. El 100% de los líderes sectoriales están clasificados en 'MANTENER' o 'HOLD'. Queda estrictamente prohibido abrir compras adicionales hoy para proteger el precio promedio. Mantén vivas tus posiciones previas y deja correr la tendencia.")
