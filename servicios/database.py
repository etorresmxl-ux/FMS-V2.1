import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Inicializa y retorna una única instancia de la conexión a Supabase de forma segura."""
    try:
        # Intento 1: Buscar directamente en st.secrets (nivel raíz)
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

        # Intento 2: Si no están en la raíz, buscar dentro de una sección [general] o similar
        if not url or not key:
            if "SUPABASE" in st.secrets:
                url = st.secrets["SUPABASE"].get("URL") or st.secrets["SUPABASE"].get("SUPABASE_URL")
                key = st.secrets["SUPABASE"].get("KEY") or st.secrets["SUPABASE"].get("SUPABASE_KEY")

        if not url or not key:
            st.error("No se encontraron las credenciales 'SUPABASE_URL' y 'SUPABASE_KEY' en los secretos de Streamlit.")
            st.stop()
            
    except Exception as e:
        st.error(f"Error al leer los secretos de configuración: {e}")
        st.stop()
        
    return create_client(url, key)
