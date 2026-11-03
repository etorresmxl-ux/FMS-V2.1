import streamlit as st
import pandas as pd
from datetime import date
import database as db
from modulos import importador, inventarios, programacion
from streamlit_option_menu import option_menu

# CONFIGURACIÓN INICIAL DE LA PÁGINA
st.set_page_config(
    page_title="Sistema de Gestión de Combustible",
    page_icon="⛽",
    layout="wide"
)

# MENÚ LATERAL DE NAVEGACIÓN
with st.sidebar:
    st.image("https://img.icons8.com/color/96/gas-station.png", width=80)
    st.title("Fuel Management System")
    
    menu = option_menu(
        menu_title="Menú Principal",
        options=["Inventarios", "Proyecciones", "Programación", "Ventas", "Importador"],
        icons=["clipboard-data", "graph-up", "calendar-check", "bar-chart", "upload"],
        default_index=0,
    )

# SECCIÓN DE ENRUTAMIENTO
if menu == "Inventarios":
    inventarios.mostrar_inventarios()
elif menu == "Proyecciones":
    # Módulo de Proyecciones existente (si aplica)
    from modulos import proyecciones
    proyecciones.mostrar_proyecciones()
elif menu == "Programación":
    programacion.mostrar_programacion()
elif menu == "Ventas":
    st.header("📊 Módulo de Ventas")
    st.info("Sección en desarrollo.")
elif menu == "Importador":
    importador.mostrar_importador()
