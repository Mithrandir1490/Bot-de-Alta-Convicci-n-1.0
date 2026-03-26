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
# UNIVERSO ESTRATÉGICO
# ==========================================
TICKERS = [
    "NVDA","MU","META","MSFT","GOOGL","AMZN","AAPL","ASML","TSM","AVGO","PLTR","PANW","VRT","AMD","NFLX","CRM","ADBE","ORCL","CSCO",
    "JPM","BAC","GS","MS","V","MA","PYPL","AXP","BLK","VST","CEG","XOM","CVX","CCJ","SMR","SLB","MPC","PSX","LLY","NVO","UNH",
    "VRTX","MRNA","PFE","ABBV","JNJ","COST","WMT","TGT","SHOP","MELI","BKNG","SBUX","KO","GEV","GE","LMT","RTX","BA","CAT","DE",
    "AVAV","GOLD","NEM","FCX","FTNT","OKTA","S","NET","ZS","CRWD","TSLA","HOOD","COIN","MSTR","DDOG","SNOW","AMAT","KLAC","LRCX"
]

st.set_page_config(page_title="Bot Alta Convicción v1.3", layout="wide")

# ==========================================
# GENERADOR DE MANUAL PDF
# ==========================================
def generar_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=18, spaceAfter=20)
    h1_style = ParagraphStyle('Heading1', parent=styles['Heading1'], fontSize=14, spaceBefore=15, color=colors.darkblue)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=12, alignment=4)
    content = []
    content.append(Paragraph("Manual de Usuario: Bot de Alta Convicción", title_style))
    content.append(Paragraph("1. ¿Cómo piensa este Bot? (Explicación Coloquial)", h1_style))
    content.append(Paragraph("<b>El Cadenero:</b> Filtra anomalías estadísticas (Z-Score).", body_style))
    content.append(Paragraph("<b>El Termómetro:</b> Mide la probabilidad de rebote (Laplace).", body_style))
    content.append(Paragraph("2. Reglas de Salida", h1_style))
    data = [["Regla", "Valor"], ["Stop Loss", "-5.0%"], ["Take Profit", "+8.0%"], ["Tiempo", "10 Días"]]
    t = Table(data, colWidths=[2*inch, 2*inch])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.darkblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
    content.append(t)
    doc.build(content)
    buffer.seek(0)
    return buffer

# ==========================================
# LÓGICA DE CÁLCULO
# ==========================================
@st.cache_data(ttl=3600)
def descargar_datos(lista_tickers):
    data = yf.download(lista_tickers, period="2y", interval="1d", group_by='column', auto_adjust=True)
    return data['Close']

def procesar_senales(precios, lista_tickers):
    resultados = []
    for t in lista_tickers:
        try:
            serie = precios[t].dropna()
            if len(serie) < 100: continue
            ret = serie.pct_change()
            exitos = (ret.shift(-1) > 0).astype(int).iloc[:-1]
            p_laplace = (exitos.mean() * len(exitos) + 2) / (len(exitos) + 4)
            p_movil = exitos.rolling(60).mean().dropna()
            z_score = (p_laplace - p_movil.mean()) / p_movil.std()
            vol = ret.tail(20).std() * np.sqrt(252)
            resultados.append({
                "Ticker": t, "Precio": serie.iloc[-1], "Z-Score": z_score, "Prob": p_laplace, "Vol": vol
            })
        except: continue
    return pd.DataFrame(resultados)

# ==========================================
# INTERFAZ (UI)
# ==========================================
st.sidebar.header("⚙️ Configuración")
efectivo_real = st.sidebar.number_input("Efectivo disponible ($)", value=737.63)
z_umbral = st.sidebar.slider("Umbral de Convicción", 1.0, 2.5, 1.65)

try:
    st.sidebar.download_button("📄 Descargar Manual", data=generar_pdf(), file_name="Manual_Bot.pdf", mime="application/pdf")
except: pass

st.title("🤖 Bot de Alta Convicción v1.3")
st.markdown("**Estrategia:** Arbitraje Estadístico | **Modo:** Diagnóstico Activo")

if st.button("🚀 Escanear Mercado"):
    with st.spinner("Analizando 110+ activos..."):
        df_precios = descargar_datos(TICKERS)
        df_final = procesar_senales(df_precios, TICKERS)
        
        # Lógica de Señales
        df_final['Señal'] = np.where(df_final['Z-Score'] > z_umbral, "🔥 COMPRA FUERTE", 
                            np.where(df_final['Prob'] > 0.60, "✅ COMPRA", 
                            np.where(df_final['Prob'] < 0.40, "❌ VENTA", "➖ HOLD")))
        
        # --- NUEVO: PANEL DE DIAGNÓSTICO ---
        st.subheader("🕵️ Panel de Diagnóstico (Top 10 por Proximidad)")
        st.info("Estas acciones son las que tienen mayor convicción hoy, aunque no todas lleguen al umbral.")
        top_diagnostico = df_final.sort_values("Z-Score", ascending=False).head(10)
        st.dataframe(
            top_diagnostico[['Ticker', 'Señal', 'Z-Score', 'Prob', 'Precio']].style.format({
                "Z-Score": "{:.2f}", "Prob": "{:.2%}", "Precio": "${:.2f}"
            }), use_container_width=True
        )
        
        # --- SECCIÓN DE EJECUCIÓN ---
        compras = df_final[df_final['Señal'].str.contains("COMPRA")].copy()
        
        if not compras.empty:
            st.divider()
            st.subheader("💰 Órdenes de Ejecución para GBM")
            compras['Inversa_Vol'] = 1 / compras['Vol']
            compras['Inversión $'] = (compras['Inversa_Vol'] / compras['Inversa_Vol'].sum()) * efectivo_real
            compras['Acciones (Qty)'] = (compras['Inversión $'] / compras['Precio']).apply(np.floor)
            
            st.dataframe(
                compras[['Ticker', 'Señal', 'Z-Score', 'Inversión $', 'Acciones (Qty)', 'Precio']]
                .sort_values("Z-Score", ascending=False)
                .style.format({"Z-Score": "{:.2f}", "Inversión $": "${:.2f}", "Acciones (Qty)": "{:.0f}", "Precio": "${:.2f}"}),
                use_container_width=True
            )
        else:
            st.warning("⚠️ Sin señales oficiales. Los Z-Scores en el Panel de Diagnóstico son menores al umbral de seguridad.")

st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
