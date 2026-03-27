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
# UNIVERSO ESTRATÉGICO (110+ TICKERS)
# ==========================================
TICKERS = [
    "NVDA","MU","META","MSFT","GOOGL","AMZN","AAPL","ASML","TSM","AVGO","PLTR","PANW","VRT","AMD","NFLX","CRM","ADBE","ORCL","CSCO",
    "JPM","BAC","GS","MS","V","MA","PYPL","AXP","BLK","VST","CEG","XOM","CVX","CCJ","SMR","SLB","MPC","PSX","LLY","NVO","UNH",
    "VRTX","MRNA","PFE","ABBV","JNJ","COST","WMT","TGT","SHOP","MELI","BKNG","SBUX","KO","GEV","GE","LMT","RTX","BA","CAT","DE",
    "AVAV","GOLD","NEM","FCX","FTNT","OKTA","S","NET","ZS","CRWD","TSLA","HOOD","COIN","MSTR","DDOG","SNOW","AMAT","KLAC","LRCX"
]

st.set_page_config(page_title="Bot Alta Convicción v2.0 (5D)", layout="wide")

# ==========================================
# GENERADOR DE MANUAL PDF (ACTUALIZADO 5D)
# ==========================================
def generar_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=18, spaceAfter=20)
    h1_style = ParagraphStyle('Heading1', parent=styles['Heading1'], fontSize=14, spaceBefore=15, color=colors.darkblue)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=12, alignment=4)
    content = []
    content.append(Paragraph("Manual de Usuario: Bot de Alta Convicción v2.0", title_style))
    content.append(Paragraph("1. Filosofía de Horizonte 5-D", h1_style))
    content.append(Paragraph("Este bot no busca el rebote de mañana. Busca la <b>Convicción Semanal</b>. Calcula la probabilidad de que en 5 días hábiles el precio sea superior al actual, filtrando el ruido del 'day-trading'.", body_style))
    content.append(Paragraph("2. Reglas de Salida Estratégica", h1_style))
    data = [["Regla", "Valor", "Lógica"], ["Stop Loss", "-5.0%", "Protección Capital"], ["Take Profit", "+8.0%", "Captura de Alpha"], ["Tiempo Máx", "10 Días", "Costo Oportunidad"]]
    t = Table(data, colWidths=[1.2*inch, 1.2*inch, 2.6*inch])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.darkblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
    content.append(t)
    doc.build(content)
    buffer.seek(0)
    return buffer

# ==========================================
# CEREBRO MATEMÁTICO (HORIZONTE 5 DÍAS)
# ==========================================
@st.cache_data(ttl=3600)
def descargar_datos(lista_tickers):
    data = yf.download(lista_tickers, period="2y", interval="1d", group_by='column', auto_adjust=True)
    return data['Close']

def procesar_senales_5d(precios, lista_tickers):
    resultados = []
    HORIZONTE = 5 # Cambiamos de 1 a 5 días
    
    for t in lista_tickers:
        try:
            serie = precios[t].dropna()
            if len(serie) < 100: continue
            
            # --- LÓGICA DE ÉXITO SEMANAL ---
            # Comparamos el precio de hoy contra el de hace 5 días (históricamente)
            # Para Laplace, miramos si 'Precio en t+5' > 'Precio en t'
            ret_5d = serie.shift(-HORIZONTE) > serie
            exitos = ret_5d.dropna().astype(int)
            
            # Laplace
            p_laplace = (exitos.mean() * len(exitos) + 2) / (len(exitos) + 4)
            
            # Z-Score sobre la probabilidad móvil de 60 días
            p_movil = exitos.rolling(60).mean().dropna()
            z_score = (p_laplace - p_movil.mean()) / p_movil.std()
            
            # Volatilidad para Risk-Parity
            vol = serie.pct_change().tail(20).std() * np.sqrt(252)
            
            resultados.append({
                "Ticker": t, "Precio": serie.iloc[-1], "Z-Score": z_score, "Prob 5D": p_laplace, "Vol": vol
            })
        except: continue
    return pd.DataFrame(resultados)

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
st.sidebar.header("⚙️ Panel de Control v2.0")
efectivo_real = st.sidebar.number_input("Efectivo disponible ($)", value=737.63)
z_umbral = st.sidebar.slider("Umbral de Convicción", 1.0, 2.5, 1.65)

try:
    st.sidebar.download_button("📄 Descargar Manual 5-D", data=generar_pdf(), file_name="Manual_Bot_5D.pdf", mime="application/pdf")
except: pass

st.title("🤖 Bot de Alta Convicción v2.0")
st.markdown("**Estrategia:** Weekly Mean Reversion | **Horizonte de Probabilidad:** 5 Días")

if st.button("🚀 Escanear Convicción Semanal"):
    with st.spinner("Analizando horizontes de 5 días en 110+ activos..."):
        df_precios = descargar_datos(TICKERS)
        df_final = procesar_senales_5d(df_precios, TICKERS)
        
        # Clasificación
        df_final['Señal'] = np.where(df_final['Z-Score'] > z_umbral, "🔥 COMPRA FUERTE", 
                            np.where(df_final['Prob 5D'] > 0.60, "✅ COMPRA", 
                            np.where(df_final['Prob 5D'] < 0.40, "❌ VENTA", "➖ HOLD")))
        
        # PANEL DE DIAGNÓSTICO
        st.subheader("🕵️ Panel de Diagnóstico Semanal (Top 10)")
        top_diagnostico = df_final.sort_values("Z-Score", ascending=False).head(10)
        st.dataframe(
            top_diagnostico[['Ticker', 'Señal', 'Z-Score', 'Prob 5D', 'Precio']].style.format({
                "Z-Score": "{:.2f}", "Prob 5D": "{:.2%}", "Precio": "${:.2f}"
            }), use_container_width=True
        )
        
        # ÓRDENES
        compras = df_final[df_final['Señal'].str.contains("COMPRA")].copy()
        if not compras.empty:
            st.divider()
            st.subheader("💰 Órdenes Sugeridas (Horizonte 5D)")
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
            st.warning("⚠️ Sin señales semanales de alta convicción. El mercado no muestra memoria de rebote a 5 días.")

st.markdown("---")
st.caption(f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Modo: Horizonte 5-Días")
