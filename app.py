import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch  # Importación crítica corregida
import io

# ==========================================
# CONFIGURACIÓN DEL UNIVERSO (110+ TICKERS)
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
    
    # Estilos personalizados para el Manual
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
    content.append(Paragraph("$\hat{p} = (k + 1) / (n + 2)$", body_style))
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
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey)
    ]))
    content.append(t)

    doc.build(content)
    buffer.seek(0)
    return buffer

# ==========================================
# MOTOR DE DATOS Y CÁLCULOS
# ==========================================
@st.cache_data(ttl=3600)
def descargar_datos(lista_tickers):
    # Descarga masiva para optimizar tiempo
    data = yf.download(lista_tickers, period="2y", interval="1d", group_by='column', auto_adjust=True)
    return data['Close']

def procesar_senales(precios, lista_tickers):
    resultados = []
    for t in lista_tickers:
        try:
            serie = precios[t].dropna()
            if len(serie) < 100: continue
            
            # Cálculo de Probabilidades
            ret = serie.pct_change()
            exitos = (ret.shift(-1) > 0).astype(int).iloc[:-1]
            p_laplace = (exitos.mean() * len(exitos) + 2) / (len(exitos) + 4)
            
            # Cálculo de Z-Score
            p_movil = exitos.rolling(60).mean().dropna()
            z_score = (p_laplace - p_movil.mean()) / p_movil.std()
            
            # Volatilidad Anualizada
            vol = ret.tail(20).std() * np.sqrt(252)
            
            resultados.append({
                "Ticker": t, 
                "Precio": serie.iloc[-1], 
                "Z-Score": z_score, 
                "Prob": p_laplace, 
                "Vol": vol
            })
        except: continue
    return pd.DataFrame(resultados)

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================

# Sidebar: Configuración e Interacción
st.sidebar.header("⚙️ Panel de Control")
efectivo_real = st.sidebar.number_input("Efectivo disponible hoy ($)", min_value=10.0, value=737.63, step=10.0)
z_umbral = st.sidebar.slider("Umbral de Convicción (Z-Score)", 1.0, 2.5, 1.65)

# Botón para descargar el PDF pedagógico
st.sidebar.markdown("---")
try:
    pdf_file = generar_pdf()
    st.sidebar.download_button(
        label="📄 Descargar Manual Pedagógico",
        data=pdf_file,
        file_name="Manual_Bot_Alta_Conviccion.pdf",
        mime="application/pdf"
    )
except Exception as e:
    st.sidebar.error(f"Error al generar PDF: {e}")

st.sidebar.markdown("---")
st.sidebar.info("Recuerda: El mercado premia la disciplina, no la velocidad.")

# Cuerpo de la App
st.title("🤖 Bot de Alta Convicción v1.2")
st.markdown(f"**Estrategia:** Arbitraje Estadístico | **Distribución:** Risk-Parity Dinámico")

if st.button("🚀 Escanear Mercado y Calcular Ejecución"):
    with st.spinner("Analizando desviaciones estándar y probabilidades..."):
        df_precios = descargar_datos(TICKERS)
        df_final = procesar_senales(df_precios, TICKERS)
        
        # Lógica de Señales
        df_final['Señal'] = np.where(df_final['Z-Score'] > z_umbral, "🔥 COMPRA FUERTE", 
                            np.where(df_final['Prob'] > 0.60, "✅ COMPRA", 
                            np.where(df_final['Prob'] < 0.40, "❌ VENTA", "➖ HOLD")))
        
        compras = df_final[df_final['Señal'].str.contains("COMPRA")].copy()
        
        if not compras.empty:
            # Ponderación por Volatilidad (Risk Parity)
            compras['Inversa_Vol'] = 1 / compras['Vol']
            suma_inversas = compras['Inversa_Vol'].sum()
            compras['Inversión $'] = (compras['Inversa_Vol'] / suma_inversas) * efectivo_real
            
            # Cálculo de cantidad de acciones (Floor para no exceder capital)
            compras['Acciones (Qty)'] = (compras['Inversión $'] / compras['Precio']).apply(np.floor)
            
            st.success(f"Se detectaron {len(compras)} señales. Capital de ${efectivo_real} distribuido.")
            
            # Mostrar Resultados
            st.dataframe(
                compras[['Ticker', 'Señal', 'Z-Score', 'Inversión $', 'Acciones (Qty)', 'Precio']]
                .sort_values("Z-Score", ascending=False)
                .style.format({
                    "Z-Score": "{:.2f}", 
                    "Inversión $": "${:.2f}", 
                    "Acciones (Qty)": "{:.0f}", 
                    "Precio": "${:.2f}"
                }),
                use_container_width=True
            )
            st.info("💡 **Instrucción:** Ejecuta las órdenes en tu broker usando la columna 'Acciones (Qty)'.")
        else:
            st.warning("No se encontraron señales de alta convicción. El capital se mantiene protegido en efectivo.")

st.markdown("---")
st.caption(f"Última actualización de motor: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
