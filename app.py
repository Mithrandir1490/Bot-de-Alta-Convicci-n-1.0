import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import io

# ==========================================
# CONFIGURACIÓN DEL UNIVERSO
# ==========================================
TICKERS = [
    "NVDA","MU","META","MSFT","GOOGL","AMZN","AAPL","ASML","TSM","AVGO","PLTR","PANW","VRT","AMD","NFLX","CRM","ADBE","ORCL","CSCO",
    "JPM","BAC","GS","MS","V","MA","PYPL","AXP","BLK","VST","CEG","XOM","CVX","CCJ","SMR","SLB","MPC","PSX","LLY","NVO","UNH",
    "VRTX","MRNA","PFE","ABBV","JNJ","COST","WMT","TGT","SHOP","MELI","BKNG","SBUX","KO","GEV","GE","LMT","RTX","BA","CAT","DE",
    "AVAV","GOLD","NEM","FCX","FTNT","OKTA","S","NET","ZS","CRWD","TSLA","HOOD","COIN","MSTR","DDOG","SNOW","AMAT","KLAC","LRCX"
]

st.set_page_config(page_title="Bot Alta Convicción v1.2", layout="wide")

# ==========================================
# FUNCIÓN GENERADORA DE PDF (PEDAGÓGICA)
# ==========================================
def generar_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Estilos
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=18, spaceAfter=20)
    h1_style = ParagraphStyle('Heading1', parent=styles['Heading1'], fontSize=14, spaceBefore=15, color=colors.darkblue)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=12, alignment=4)

    content = []
    content.append(Paragraph("Manual de Usuario: Bot de Alta Convicción", title_style))
    
    # Sección Pedagógica
    content.append(Paragraph("1. ¿Cómo piensa este Bot? (Explicación Coloquial)", h1_style))
    content.append(Spacer(1, 10))
    content.append(Paragraph("<b>El Cadenero del Club:</b> El mercado es una fiesta llena de gente, pero el bot es el cadenero más exigente. El 'Z-Score' es su lista de invitados. Si una acción no tiene una invitación estadística especial (una anomalía positiva), no entra al portafolio.", body_style))
    content.append(Spacer(1, 10))
    content.append(Paragraph("<b>El Termómetro de Agua:</b> El bot no solo ve si el precio sube. Siente la temperatura. Si el agua está tibia (poca probabilidad), no hace nada. Si está hirviendo de forma inusual (alta convicción), es cuando nos avisa para entrar.", body_style))

    # Sección Matemática
    content.append(Paragraph("2. El Modelo Matemático (Rigor Técnico)", h1_style))
    content.append(Spacer(1, 10))
    content.append(Paragraph("<b>Suavizado de Laplace:</b> Utilizamos una estimación bayesiana para evitar el ruido en muestras pequeñas, calculando la probabilidad de éxito de la siguiente forma:", body_style))
    content.append(Paragraph("P_hat = (Exitos + 1) / (Total_Ensayos + 2)", body_style))
    content.append(Spacer(1, 10))
    content.append(Paragraph("<b>Z-Score de Convicción:</b> Comparamos la probabilidad de hoy contra su propia historia de 90 días para detectar desviaciones estándar significativas.", body_style))

    # Sección Operativa
    content.append(Paragraph("3. Reglas de Salida Innegociables", h1_style))
    data = [
        ["Regla", "Parámetro", "Acción"],
        ["Stop Loss", "-5.0%", "Cierre automático para proteger capital"],
        ["Take Profit", "+8.0%", "Captura de beneficios técnica"],
        ["Time Exit", "10 Días", "Liquidación por costo de oportunidad"]
    ]
    t = Table(data, colWidths=[1.5*inch, 1.5*inch, 2.5*inch])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.darkblue),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
    content.append(t)

    doc.build(content)
    buffer.seek(0)
    return buffer

# ==========================================
# INTERFAZ Y LÓGICA
# ==========================================
st.sidebar.header("⚙️ Panel de Control")
efectivo_real = st.sidebar.number_input("Efectivo disponible ($)", value=737.63)
z_umbral = st.sidebar.slider("Umbral de Convicción", 1.0, 2.5, 1.65)

# Botón de Descarga del Manual
pdf_data = generar_pdf()
st.sidebar.download_button(label="📄 Descargar Manual Pedagógico", data=pdf_data, file_name="Manual_Bot_Alta_Conviccion.pdf", mime="application/pdf")

st.title("🤖 Bot de Alta Convicción v1.2")

if st.button("🚀 Escanear y Calcular Ejecución"):
    with st.spinner("Analizando mercado..."):
        # (Aquí va tu lógica de descarga y procesamiento anterior)
        data = yf.download(TICKERS, period="2y", interval="1d", group_by='column', auto_adjust=True)
        prices = data['Close']
        
        resultados = []
        for t in TICKERS:
            try:
                serie = prices[t].dropna()
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
        
        df = pd.DataFrame(resultados)
        df['Señal'] = np.where(df['Z-Score'] > z_umbral, "🔥 COMPRA FUERTE", 
                      np.where(df['Prob'] > 0.60, "✅ COMPRA", 
                      np.where(df['Prob'] < 0.40, "❌ VENTA", "➖ HOLD")))
        
        compras = df[df['Señal'].str.contains("COMPRA")].copy()
        
        if not compras.empty:
            # Ponderación por Volatilidad
            compras['Inversa_Vol'] = 1 / compras['Vol']
            compras['Inversión $'] = (compras['Inversa_Vol'] / compras['Inversa_Vol'].sum()) * efectivo_real
            
            # NUEVA COLUMNA: Acciones a Comprar
            compras['Acciones (Qty)'] = (compras['Inversión $'] / compras['Precio']).apply(np.floor)
            
            st.success(f"Se encontraron {len(compras)} señales.")
            st.dataframe(
                compras[['Ticker', 'Señal', 'Z-Score', 'Inversión $', 'Acciones (Qty)', 'Precio']].sort_values("Z-Score", ascending=False)
                .style.format({"Z-Score": "{:.2f}", "Inversión $": "${:.2f}", "Acciones (Qty)": "{:.0f}", "Precio": "${:.2f}"}),
                use_container_width=True
            )
        else:
            st.info("Sin señales hoy.")
