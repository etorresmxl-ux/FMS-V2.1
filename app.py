import streamlit as st
from servicios.database import get_supabase_client
from modulos.inventarios import render_inventarios

USUARIOS_PREDEFINIDOS = ["Brenda", "Daniela", "Jazmin", "Yesenia"]

### Configuración inicial de la página
st.set_page_config(
    page_title="Fuel Management System (FMS)",
    page_icon="⛽",
    layout="wide"
)

### Obtener la instancia centralizada de Supabase
supabase = get_supabase_client()


def main():
    with st.sidebar:
        st.title("Fuel Management System")

        usuario_actual = st.selectbox(
            "Usuario:",
            options=USUARIOS_PREDEFINIDOS,
            index=0,
            key="usuario_activo_fms"
        )

        st.markdown("---")

        selected = st.radio(
            "Menú Principal",
            options=["Inventarios", "Ventas", "Programación"],
            index=0,
            key="menu_principal_fms"
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
