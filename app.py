import streamlit as st
import pandas as pd
from servicios.database import get_supabase_client
from servicios.data_loader import DataLoaderService
from modulos.inventarios import render_inventarios
from modulos.programacion import render_programacion

# Configuración inicial de la página
st.set_page_config(
    page_title="Fuel Management System (FMS)",
    page_icon="⛽",
    layout="wide"
)

def main():
    # Obtener la instancia centralizada de Supabase y DataLoader
    supabase = get_supabase_client()
    data_loader = DataLoaderService(supabase)

    # Gestión de usuarios en el menú lateral
    st.sidebar.title("Configuración de Usuario")
    usuarios_disponibles = ["Brenda", "Daniela", "Jazmin", "Yesenia"]
    
    if "usuario_actual" not in st.session_state:
        st.session_state["usuario_actual"] = "Brenda"

    usuario_actual = st.sidebar.selectbox(
        "Seleccionar Usuario:",
        options=usuarios_disponibles,
        index=usuarios_disponibles.index(st.session_state["usuario_actual"]) if st.session_state["usuario_actual"] in usuarios_disponibles else 0
    )
    st.session_state["usuario_actual"] = usuario_actual

    # Menú lateral de navegación
    st.sidebar.markdown("---")
    st.sidebar.title("Navegación")
    opcion = st.sidebar.radio("Seleccionar Módulo", ["Inventarios", "Programación"])

    st.sidebar.markdown("---")
    st.sidebar.write(f"Usuario activo: **{usuario_actual}**")

    # Enrutamiento de vistas según la opción seleccionada (pasando los 3 argumentos correctos)
    if opcion == "Inventarios":
        render_inventarios(supabase, usuario_actual, data_loader)
    elif opcion == "Programación":
        render_programacion(supabase, usuario_actual, data_loader)

if __name__ == "__main__":
    main()
