import streamlit as st
from streamlit_option_menu import option_menu
from supabase import create_client, Client
from modulos.inventarios import render_inventarios

# Configuración inicial de la página
st.set_page_config(
    page_title="Fuel Management System (FMS)",
    page_icon="⛽",
    layout="wide"
)

# Inicialización de la conexión a Supabase usando st.secrets
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

def main():
    # Barra lateral para navegación y sesión de usuario
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/fuel-tank.png", width=80)
        st.title("FMS-V2.1")
        
        # Simulación de autenticación de usuario (puedes adaptarlo a tu sistema de login real)
        usuario_actual = st.text_input("Usuario actual", value="operador_principal")
        
        st.markdown("---")
        
        # Menú de navegación principal con los módulos definidos
        selected = option_menu(
            menu_title="Menú Principal",
            options=["Inventarios", "Ventas", "Programación"],
            icons=["clipboard-data", "cart-check", "calendar-range"],
            menu_icon="cast",
            default_index=0,
        )
        
        st.markdown("---")
        st.info("Sistema de Gestión de Combustibles conectado a Supabase.")

    # Enrutamiento de vistas según la selección del menú
    if selected == "Inventarios":
        render_inventarios(supabase, usuario_actual)
        
    elif selected == "Ventas":
        st.subheader("Módulo de Ventas")
        st.info("Próximamente: Registro y control histórico de ventas.")
        
    elif selected == "Programación":
        st.subheader("Módulo de Programación")
        st.info("Próximamente: Planificación de cargas y abastecimientos.")

if __name__ == "__main__":
    main()
