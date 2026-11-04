import streamlit as st
import pandas as pd
from servicios.database import get_supabase_client
from servicios.data_loader import DataLoaderService
from modulos.inventarios import render_inventarios

# Configuración inicial de la página
st.set_page_config(
    page_title="Fuel Management System (FMS)",
    page_icon="⛽",
    layout="wide"
)

# Obtener la instancia centralizada de Supabase y DataLoader
supabase = get_supabase_client()
data_loader = DataLoaderService(supabase)

def main():
    # Todo lo que se encuentre dentro de 'with st.sidebar:' aparecerá en el menú lateral
    with st.sidebar:
        st.title("Fuel Management System")
        st.markdown("---")
        
        # Cargar datos maestros centralizados en memoria con caché
        datos_maestros = data_loader.cargar_datos_maestros()
        lista_usuarios = datos_maestros.get("usuarios", ["Brenda", "Daniela", "Jazmin", "Yesenia"])
        
        # Almacenar inventarios globales en session_state para acceso rápido en la sesión
        st.session_state["df_inventarios_global"] = datos_maestros.get("inventarios", pd.DataFrame())
        
        # Selector de usuario integrado en la barra lateral
        if lista_usuarios:
            usuario_actual = st.selectbox("Usuario:", options=lista_usuarios)
        else:
            usuario_actual = st.text_input("Usuario:", value="Programador")
            st.warning("No se encontraron registros de usuarios en la base de datos.")
        
        st.markdown("---")
        
        # Catálogo de módulos / Menú Principal de navegación en la barra lateral
        selected = st.radio(
            "Menú Principal",
            options=["Inventarios", "Ventas", "Programación"],
            index=0
        )
        
        st.markdown("---")
        st.info("Sistema de Gestión de Combustibles conectado a Supabase.")

    # Enrutamiento de vistas según la selección del menú lateral
    if selected == "Inventarios":
        render_inventarios(supabase, usuario_actual, data_loader)
        
    elif selected == "Ventas":
        st.subheader("Módulo de Ventas")
        st.info("Próximamente: Registro y control histórico de ventas.")
        
    elif selected == "Programación":
        st.subheader("Módulo de Programación")
        st.info("Próximamente: Planificación de cargas y abastecimientos.")
        
if __name__ == "__main__":
    main()
