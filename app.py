import streamlit as st
from streamlit_option_menu import option_menu
from servicios.database import get_supabase_client
from modulos.inventarios import render_inventarios

# Configuración inicial de la página
st.set_page_config(
    page_title="Fuel Management System (FMS)",
    page_icon="⛽",
    layout="wide"
)

# Obtener la instancia centralizada de Supabase
supabase = get_supabase_client()

def main():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/fuel-tank.png", width=80)
        st.title("FMS-V2.1")
        
        usuario_actual = st.text_input("Usuario actual", value="operador_principal")
        
        st.markdown("---")
        
        selected = option_menu(
            menu_title="Menú Principal",
            options=["Inventarios", "Ventas", "Programación"],
            icons=["clipboard-data", "cart-check", "calendar-range"],
            menu_icon="cast",
            default_index=0,
        )
        
        st.markdown("---")
        st.info("Sistema de Gestión de Combustibles conectado a Supabase.")

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
