import streamlit as st
from streamlit_option_menu import option_menu
import plotly.express as px
import pandas as pd
from PIL import Image
import sqlite3
from datetime import datetime

# Configuración inicial
st.set_page_config(
    page_title="INC Ignacio Chávez",
    page_icon="❤️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- BASE DE DATOS SIMULADA ---
def crear_bd():
    conn = sqlite3.connect('inc_cardio.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS finanzas (
        mes TEXT PRIMARY KEY,
        ingresos REAL,
        gastos REAL,
        donaciones REAL
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indicadores (
        id TEXT PRIMARY KEY,
        valor REAL,
        meta REAL,
        unidad TEXT
    )''')
    
    # Datos de ejemplo
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May']
    for i, mes in enumerate(meses):
        cursor.execute('''
        INSERT OR REPLACE INTO finanzas VALUES (?, ?, ?, ?)
        ''', (mes, 12.5 + i*2, 10.8 + i*1.5, 1.2 + i*0.3))
    
    indicadores = [
        ('tasa_reingresos', 4.2, 3.5, '%'),
        ('pacientes_mes', 1280, 1400, 'pacientes'),
        ('satisfaccion', 88, 90, 'NPS'),
        ('tiempo_espera', 35, 25, 'min')
    ]
    
    for ind in indicadores:
        cursor.execute('''
        INSERT OR REPLACE INTO indicadores VALUES (?, ?, ?, ?)
        ''', ind)
    
    conn.commit()
    return conn

# --- INTERFAZ MÓVIL ---
def main():
    conn = crear_bd()
    
    # Logo y título responsivo
    logo = Image.open('escudo_COLOR.jpg')
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(logo, width=80)
    with col2:
        st.title("INC Ignacio Chávez")
    
    st.caption(f"Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Menú responsivo (se convierte en acordeón en móviles)
    selected = option_menu(
        menu_title=None,
        options=["Resumen", "Finanzas", "Clínica", "Investigación", "Alertas"],
        icons=["speedometer2", "cash-coin", "heart-pulse", "biotech", "bell"],
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important"},
            "icon": {"font-size": "14px"},
            "nav-link": {"font-size": "12px"}
        }
    )
    
    # --- CONTENIDO DINÁMICO ---
    if selected == "Resumen":
        st.header("📊 Resumen Ejecutivo", divider="red")
        
        # KPIs principales con tooltips
        cols = st.columns(2)
        finanzas = pd.read_sql('SELECT * FROM finanzas', conn)
        total_ingresos = finanzas['ingresos'].sum()
        
        with cols[0]:
            st.metric(
                label="Ingresos Totales",
                value=f"${total_ingresos:.1f}M",
                help="Acumulado anual incluyendo donaciones"
            )
            
            st.metric(
                label="Pacientes Únicos",
                value="1,280",
                help="Pacientes atendidos este mes"
            )
        
        with cols[1]:
            st.metric(
                label="Eficiencia Clínica",
                value="88%",
                help="Tasa de procedimientos exitosos"
            )
            
            st.metric(
                label="Investigación",
                value="4.8",
                help="Publicaciones indexadas este año"
            )
        
        # Gráfico interactivo con tooltip detallado
        fig = px.area(
            finanzas,
            x='mes',
            y=['ingresos', 'gastos'],
            title="Tendencia Financiera",
            labels={'value': 'Millones MXN', 'variable': ''}
        )
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>$%{y:.1f}M<extra></extra>"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected == "Finanzas":
        st.header("💵 Finanzas", divider="blue")
        
        # Datos financieros
        finanzas = pd.read_sql('SELECT * FROM finanzas', conn)
        ultimo_mes = finanzas.iloc[-1]
        
        cols = st.columns(3)
        with cols[0]:
            st.metric("Ingresos", f"${ultimo_mes['ingresos']:.1f}M")
        with cols[1]:
            st.metric("Gastos", f"${ultimo_mes['gastos']:.1f}M")
        with cols[2]:
            st.metric("Balance", f"${ultimo_mes['ingresos'] - ultimo_mes['gastos']:.1f}M")
        
        # Gráfico de donaciones con tooltip
        fig = px.bar(
            finanzas,
            x='mes',
            y='donaciones',
            title="Donaciones Mensuales",
            hover_data={'donaciones': ':.1f'}
        )
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>Donación: $%{y:.1f}M<extra></extra>",
            marker_color='#FF6B6B'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected == "Clínica":
        st.header("🏥 Indicadores Clínicos", divider="green")
        
        # Tarjetas expandibles
        with st.expander("🚑 Urgencias", expanded=True):
            cols = st.columns(2)
            with cols[0]:
                st.metric("Tiempo Espera", "35 min", "-5 min vs meta")
            with cols[1]:
                st.metric("Gravedad Promedio", "2.8", "1.3% ▲")
        
        with st.expander("❤️ Procedimientos"):
            procedimientos = pd.DataFrame({
                'Tipo': ['Angioplastia', 'ByPass', 'Cateterismo'],
                'Cantidad': [45, 28, 63],
                'Éxito': [96, 94, 98]
            })
            
            fig = px.bar(
                procedimientos,
                x='Tipo',
                y='Cantidad',
                color='Éxito',
                hover_data={'Éxito': ':.1f%'},
                title="Procedimientos Mensuales"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    elif selected == "Investigación":
        st.header("🔬 Investigación", divider="violet")
        
        proyectos = pd.DataFrame({
            'Proyecto': ['Genómica CVD', 'Hipertensión', 'Dispositivos'],
            'Presupuesto': [2.5, 1.8, 3.2],
            'Avance': [65, 40, 25]
        })
        
        # Gráfico de burbujas interactivo
        fig = px.scatter(
            proyectos,
            x='Proyecto',
            y='Avance',
            size='Presupuesto',
            color='Proyecto',
            hover_name='Proyecto',
            hover_data={'Presupuesto': '$.1fM', 'Avance': ':.0f%'},
            size_max=40
        )
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected == "Alertas":
        st.header("⚠️ Alertas Prioritarias", divider="orange")
        
        alertas = [
            {"tipo": "Inventario", "mensaje": "Stents coronarios < stock mínimo", "nivel": "Alto"},
            {"tipo": "Personal", "mensaje": "Falta especialista en arritmias", "nivel": "Medio"},
            {"tipo": "Equipo", "mensaje": "Mantenimiento pendiente: Resonador", "nivel": "Crítico"}
        ]
        
        for alerta in alertas:
            color = {
                "Alto": "#FF6B6B",
                "Medio": "#FFD166",
                "Crítico": "#EF476F"
            }.get(alerta['nivel'], "#999")
            
            st.markdown(
                f"""
                <div style="
                    border-left: 4px solid {color};
                    padding: 0.5rem;
                    margin: 0.5rem 0;
                    background: #FFF9F9;
                    border-radius: 0 8px 8px 0;
                ">
                    <b>{alerta['tipo']}</b>: {alerta['mensaje']}<br>
                    <small>Nivel: {alerta['nivel']}</small>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Footer responsivo
    st.markdown("---")
    st.caption("""
    **Sistema de Monitoreo Integral**  
    Instituto Nacional de Cardiología Ignacio Chávez  
    *Datos actualizados cada 24 horas*
    """)

if __name__ == "__main__":
    main()
