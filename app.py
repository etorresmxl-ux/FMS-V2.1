import streamlit as st
from servicios.database import get_supabase_client
from modulos.inventarios import render_inventarios

### Configuración inicial de la página
st.set_page_config(
    page_title="Fuel Management System (FMS)",
    page_icon="⛽",
    layout="wide"
)

### Obtener la instancia centralizada de Supabase
supabase = get_supabase_client()

@st.cache_data(ttl=60)
def obtener_usuarios() -> list:
    """Consulta y retorna una lista de usuarios únicos desde la tabla estaciones_usuario en Supabase."""
    try:
        res = supabase.table("estaciones_usuario").select("usuario").execute()
        if res.data:
            usuarios = sorted(list(set([item["usuario"] for item in res.data])))
            return usuarios
    except Exception as e:
        st.error(f"Error al consultar usuarios en Supabase: {e}")
    return []

def main():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/fuel-tank.png", width=80)
        st.title("FMS-V2.1")
    
        # Obtener usuarios desde la base de datos de manera dinámica
        lista_usuarios = obtener_usuarios()
        
        if lista_usuarios:
            usuario_actual = st.selectbox("Usuario actual", options=lista_usuarios)
        else:
            usuario_actual = st.text_input("Usuario actual", value="operador_principal")
            st.warning("No se encontraron registros de usuarios en la base de datos.")
        
        st.markdown("---")
        
        # Menú de navegación nativo
        selected = st.radio(
            "Menú Principal",
            options=["Inventarios", "Ventas", "Programación"],
            index=0
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
